"""Management command to create or elevate an admin account."""
import os
import sys
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from apps.accounts.models import UserRole, sync_admin_flags

User = get_user_model()


class Command(BaseCommand):
    help = "Create a new admin account or elevate an existing user to admin."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="Admin email address")
        parser.add_argument("--password", type=str, help="Admin password")
        parser.add_argument(
            "--set-password",
            action="store_true",
            help="Reset password when elevating an existing user",
        )
        parser.add_argument(
            "--from-env",
            action="store_true",
            help="Read ADMIN_EMAIL and ADMIN_PASSWORD from environment variables",
        )

    def handle(self, *args, **options):
        email, password = self._resolve_credentials(options)

        email = email.strip().lower()
        if not email:
            raise CommandError("Email cannot be empty.")

        with transaction.atomic():
            existing = User.objects.select_for_update().filter(email=email)
            count = existing.count()

            if count > 1:
                raise CommandError(
                    f"Multiple users found with email '{email}'. "
                    "Please resolve duplicates manually."
                )

            if count == 1:
                user = existing.get()
                self._elevate_existing(user, password, options["set_password"])
                return

        # No existing user — try to create. If a concurrent process
        # already inserted the same email, catch the IntegrityError
        # and fall through to the existing-user path.
        try:
            with transaction.atomic():
                self._create_new(email, password)
                return
        except IntegrityError:
            pass

        # Race loser: the row now exists — elevate it.
        with transaction.atomic():
            user = User.objects.select_for_update().get(email=email)
            self._elevate_existing(user, password, options["set_password"])

    def _resolve_credentials(self, options):
        """Resolve email and password from CLI args or environment."""
        if options["from_env"]:
            email = os.environ.get("ADMIN_EMAIL", "")
            password = os.environ.get("ADMIN_PASSWORD", "")

            if not email and not password:
                self.stdout.write("ADMIN_EMAIL and ADMIN_PASSWORD not set, skipping.")
                sys.exit(0)

            if not email or not password:
                self.stderr.write(
                    self.style.WARNING(
                        "WARNING: Only one of ADMIN_EMAIL/ADMIN_PASSWORD is set, "
                        "skipping admin bootstrap."
                    )
                )
                sys.exit(0)

            return email, password

        email = options.get("email")
        if not email:
            raise CommandError("--email is required (or use --from-env).")

        password = options.get("password")
        if not password:
            if not sys.stdin.isatty():
                raise CommandError(
                    "No password provided and stdin is not interactive. "
                    "Use --password or --from-env."
                )
            import getpass

            password = getpass.getpass("Admin password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                raise CommandError("Passwords do not match.")

        return email, password

    def _validate_password(self, password, user=None):
        """Run Django password validators."""
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            raise CommandError(
                "Password validation failed:\n" + "\n".join(e.messages)
            )

    def _create_new(self, email, password):
        """Create a new admin user."""
        self._validate_password(password)

        username = f"admin_{uuid.uuid4().hex[:12]}"
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        user.role = UserRole.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(update_fields=["role", "is_staff", "is_superuser", "is_active"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin account created: {email} (username: {username})"
            )
        )

    def _elevate_existing(self, user, password, set_password):
        """Elevate an existing user to admin."""
        was_admin = user.role == UserRole.ADMIN

        if set_password:
            self._validate_password(password, user=user)
            user.set_password(password)

        user.role = UserRole.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True

        fields = ["role", "is_staff", "is_superuser", "is_active"]
        if set_password:
            fields.append("password")
        user.save(update_fields=fields)

        if was_admin:
            msg = f"User {user.email} is already admin (no changes)."
            if set_password:
                msg = f"Admin {user.email} password has been reset."
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            msg = f"User {user.email} elevated to admin."
            if set_password:
                msg += " Password has been reset."
            self.stdout.write(self.style.SUCCESS(msg))
