"""Tests for the admin account system.

Covers:
  - AC-1: create_admin management command
  - AC-1.1: --from-env mode
  - AC-2: createsuperuser sets role=ADMIN
  - AC-3: Role/flag sync on promotion/demotion
  - AC-4: Case-insensitive email uniqueness
  - AC-6: AUTH_PASSWORD_VALIDATORS
  - AC-7: Django Admin UserAdmin registration
  - AC-8: Drift repair (tested via model assertions)
"""
import json
import os
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import Client

from apps.accounts.models import User, UserRole, sync_admin_flags
from apps.accounts.services import AuthService

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(email="user@test.com", password="StrongPass123!", **kwargs):
    defaults = {"display_name": email.split("@")[0]}
    defaults.update(kwargs)
    return User.objects.create_user(
        username=f"u_{email.replace('@', '_').replace('.', '_')}",
        email=email,
        password=password,
        **defaults,
    )


def _auth_header(user):
    token = AuthService.get_tokens_for_user(user)["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ===========================================================================
# AC-1: create_admin command — create new admin
# ===========================================================================


def test_create_admin_new_user():
    """create_admin with new email creates admin user."""
    out = StringIO()
    call_command(
        "create_admin",
        email="admin@new.com",
        password="ValidPass123!",
        stdout=out,
    )
    user = User.objects.get(email="admin@new.com")
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
    assert "created" in out.getvalue().lower()


def test_create_admin_elevate_existing():
    """create_admin elevates existing non-admin user without changing password."""
    user = _create_user("existing@test.com", "OriginalPass123!")
    assert user.role == UserRole.USER

    out = StringIO()
    call_command(
        "create_admin",
        email="existing@test.com",
        password="NotUsed123!",
        stdout=out,
    )
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    # Password should NOT have changed (no --set-password)
    assert user.check_password("OriginalPass123!")


def test_create_admin_elevate_with_set_password():
    """create_admin --set-password resets the password."""
    user = _create_user("setpw@test.com", "OriginalPass123!")
    out = StringIO()
    call_command(
        "create_admin",
        email="setpw@test.com",
        password="NewPassword123!",
        set_password=True,
        stdout=out,
    )
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.check_password("NewPassword123!")


def test_create_admin_idempotent():
    """Running create_admin twice on same email is idempotent."""
    out1 = StringIO()
    call_command(
        "create_admin",
        email="idempotent@test.com",
        password="ValidPass123!",
        stdout=out1,
    )
    out2 = StringIO()
    call_command(
        "create_admin",
        email="idempotent@test.com",
        password="ValidPass123!",
        stdout=out2,
    )
    assert User.objects.filter(email="idempotent@test.com").count() == 1
    user = User.objects.get(email="idempotent@test.com")
    assert user.role == UserRole.ADMIN


def test_create_admin_weak_password_rejected():
    """create_admin rejects passwords that fail Django validators."""
    with pytest.raises(CommandError, match="Password validation failed"):
        call_command(
            "create_admin",
            email="weakpw@test.com",
            password="12345678",
            stdout=StringIO(),
        )


def test_create_admin_no_email_fails():
    """create_admin without --email fails."""
    with pytest.raises(CommandError, match="--email is required"):
        call_command("create_admin", stdout=StringIO())


def test_create_admin_non_interactive_no_password_fails():
    """In non-interactive mode, missing --password fails."""
    with pytest.raises(CommandError, match="No password provided"):
        call_command(
            "create_admin",
            email="nopass@test.com",
            stdout=StringIO(),
        )


def test_create_admin_email_normalized_to_lowercase():
    """create_admin normalizes email to lowercase."""
    call_command(
        "create_admin",
        email="Admin@UPPER.com",
        password="ValidPass123!",
        stdout=StringIO(),
    )
    assert User.objects.filter(email="admin@upper.com").exists()
    assert not User.objects.filter(email="Admin@UPPER.com").exists()


# ===========================================================================
# AC-1.1: --from-env mode
# ===========================================================================


def test_create_admin_from_env_both_vars():
    """--from-env with both env vars creates admin."""
    with mock.patch.dict(os.environ, {
        "ADMIN_EMAIL": "envadmin@test.com",
        "ADMIN_PASSWORD": "ValidPass123!",
    }):
        out = StringIO()
        call_command("create_admin", from_env=True, stdout=out)

    user = User.objects.get(email="envadmin@test.com")
    assert user.role == UserRole.ADMIN


def test_create_admin_from_env_only_email_skips():
    """--from-env with only ADMIN_EMAIL warns and skips."""
    with mock.patch.dict(os.environ, {"ADMIN_EMAIL": "only@test.com"}, clear=False):
        # Remove ADMIN_PASSWORD if present
        env = os.environ.copy()
        env.pop("ADMIN_PASSWORD", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit):
                call_command(
                    "create_admin",
                    from_env=True,
                    stdout=StringIO(),
                    stderr=StringIO(),
                )
    assert not User.objects.filter(email="only@test.com").exists()


def test_create_admin_from_env_neither_var_skips():
    """--from-env with no env vars skips silently."""
    env = os.environ.copy()
    env.pop("ADMIN_EMAIL", None)
    env.pop("ADMIN_PASSWORD", None)
    with mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit):
            call_command(
                "create_admin",
                from_env=True,
                stdout=StringIO(),
            )
    # No admin user created
    assert User.objects.filter(role=UserRole.ADMIN).count() == 0


# ===========================================================================
# AC-2: createsuperuser sets role=ADMIN
# ===========================================================================


def test_create_superuser_sets_admin_role():
    """User.objects.create_superuser() automatically sets role=ADMIN."""
    user = User.objects.create_superuser(
        username="superadmin",
        email="super@test.com",
        password="ValidPass123!",
    )
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True


def test_create_user_does_not_set_admin_role():
    """User.objects.create_user() does NOT set role=ADMIN."""
    user = User.objects.create_user(
        username="regular",
        email="regular@test.com",
        password="ValidPass123!",
    )
    assert user.role == UserRole.USER


# ===========================================================================
# AC-3: Role/flag synchronization
# ===========================================================================


def test_sync_admin_flags_promote_to_admin():
    """sync_admin_flags sets is_staff and is_superuser when role=ADMIN."""
    user = _create_user("sync_promo@test.com")
    user.role = UserRole.ADMIN
    user.save(update_fields=["role"])
    sync_admin_flags(user)

    user.refresh_from_db()
    assert user.is_staff is True
    assert user.is_superuser is True


def test_sync_admin_flags_demote_from_admin():
    """sync_admin_flags clears is_staff and is_superuser when role!=ADMIN."""
    user = _create_user("sync_demote@test.com")
    user.role = UserRole.ADMIN
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["role", "is_staff", "is_superuser"])

    user.role = UserRole.USER
    user.save(update_fields=["role"])
    sync_admin_flags(user)

    user.refresh_from_db()
    assert user.is_staff is False
    assert user.is_superuser is False


def test_role_change_via_admin_api_syncs_flags():
    """PATCH /api/admin/users/{id}/role syncs Django auth flags."""
    admin = _create_user("api_admin@test.com")
    admin.role = UserRole.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["role", "is_staff", "is_superuser"])

    target = _create_user("api_target@test.com")
    client = Client()

    # Promote target to ADMIN via API
    resp = client.patch(
        f"/api/admin/users/{target.id}/role",
        data=json.dumps({"role": "ADMIN"}),
        content_type="application/json",
        **_auth_header(admin),
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.role == UserRole.ADMIN
    assert target.is_staff is True
    assert target.is_superuser is True

    # Demote target back to USER
    resp = client.patch(
        f"/api/admin/users/{target.id}/role",
        data=json.dumps({"role": "USER"}),
        content_type="application/json",
        **_auth_header(admin),
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.role == UserRole.USER
    assert target.is_staff is False
    assert target.is_superuser is False


def test_demoted_admin_cannot_access_admin_endpoint():
    """After demotion, user gets 403 on admin-only endpoints."""
    admin = _create_user("demoted_admin@test.com")
    admin.role = UserRole.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["role", "is_staff", "is_superuser"])

    # Demote
    admin.role = UserRole.USER
    admin.save(update_fields=["role"])
    sync_admin_flags(admin)

    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(admin),
    )
    assert resp.status_code == 403


# ===========================================================================
# AC-4: Case-insensitive email uniqueness
# ===========================================================================


def test_email_stored_lowercase():
    """User email is normalized to lowercase on save."""
    user = _create_user("MixedCase@Example.COM")
    user.refresh_from_db()
    assert user.email == "mixedcase@example.com"


def test_duplicate_email_different_case_rejected():
    """Creating a user with case-variant of existing email fails."""
    _create_user("unique@test.com")
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="u_dup",
            email="UNIQUE@TEST.COM",
            password="ValidPass123!",
        )


# ===========================================================================
# AC-6: AUTH_PASSWORD_VALIDATORS
# ===========================================================================


def test_common_password_rejected():
    """Common passwords are rejected by validators."""
    with pytest.raises(ValidationError):
        validate_password("password")


def test_short_password_rejected():
    """Passwords shorter than 8 chars are rejected."""
    with pytest.raises(ValidationError):
        validate_password("ab")


def test_numeric_password_rejected():
    """Purely numeric passwords are rejected."""
    with pytest.raises(ValidationError):
        validate_password("12345678901234")


def test_strong_password_accepted():
    """Strong passwords pass validation."""
    validate_password("MyStr0ng!Pass42")


# ===========================================================================
# AC-7: Django Admin User registration
# ===========================================================================


def test_admin_site_accessible_by_staff():
    """An is_staff user can access Django admin."""
    user = _create_user("staff@test.com")
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    client = Client()
    client.force_login(user)
    resp = client.get("/admin/")
    assert resp.status_code == 200


def test_admin_site_blocked_for_non_staff():
    """A non-staff user is redirected from Django admin."""
    user = _create_user("nonstaff@test.com")
    client = Client()
    client.force_login(user)
    resp = client.get("/admin/")
    assert resp.status_code == 302  # Redirect to login


# ===========================================================================
# AC-8: Drift repair (model-level assertions)
# ===========================================================================


def test_superuser_without_admin_role_can_be_synced():
    """A user with is_superuser=True but role=USER can be synced."""
    user = _create_user("drifted@test.com")
    # Simulate drift: manually set is_superuser without role
    User.objects.filter(id=user.id).update(is_superuser=True)
    user.refresh_from_db()
    assert user.is_superuser is True
    assert user.role == UserRole.USER

    # Sync should fix it
    user.role = UserRole.ADMIN
    user.save(update_fields=["role"])
    sync_admin_flags(user)
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.is_superuser is True
    assert user.is_staff is True


# ===========================================================================
# Permission matrix: admin access to finance report
# ===========================================================================


def test_admin_can_access_finance_report():
    """Admin user can access GET /api/admin/finance/report."""
    admin = _create_user("finance_admin@test.com")
    admin.role = UserRole.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["role", "is_staff", "is_superuser"])

    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(admin),
    )
    assert resp.status_code == 200


def test_normal_user_blocked_from_finance_report():
    """Normal user gets 403 on admin-only endpoints."""
    user = _create_user("blocked@test.com")
    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(user),
    )
    assert resp.status_code == 403


# ===========================================================================
# Regression: create_superuser forces ADMIN even with explicit override
# ===========================================================================


def test_create_superuser_forces_admin_role_even_when_overridden():
    """create_superuser ignores explicit role=USER — always sets ADMIN."""
    user = User.objects.create_superuser(
        username="forced_admin",
        email="forced@test.com",
        password="ValidPass123!",
        role=UserRole.USER,  # caller tries to override
    )
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True


# ===========================================================================
# Migration logic: data cleanup (0003 RunPython function)
# ===========================================================================


def test_migration_logic_normalizes_emails_and_resolves_duplicates():
    """The migration cleanup function normalizes emails to lowercase.

    Note: case-variant duplicate resolution cannot be tested in the test DB
    because the unique_email_ci constraint is already applied (all migrations
    run before tests). This test verifies the normalization path by inserting
    a mixed-case email and confirming it gets lowercased.
    The duplicate-deactivation code path is a safety net for production
    migrations where the constraint hasn't been applied yet.
    """
    import importlib
    mod = importlib.import_module(
        "apps.accounts.migrations.0003_add_email_uniqueness_and_manager"
    )
    normalize_emails_and_repair_drift = mod.normalize_emails_and_repair_drift
    from django.apps import apps

    # Create a user with mixed-case email via raw SQL.
    # SQLite stores the literal string but the unique index uses LOWER().
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO accounts_user "
            "(password, is_superuser, username, first_name, last_name, "
            "email, is_staff, is_active, date_joined, "
            "display_name, bio, avatar_url, role, level, "
            "credit_score, balance, frozen_balance, created_at, updated_at) "
            "VALUES "
            "('hash1', 0, 'mig_mixed', '', '', "
            "'MixedCase@MigTest.COM', 0, 1, '2026-01-01 00:00:00', "
            "'', '', '', 'USER', 'SEED', 0, 0, 0, "
            "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )

    # Run the migration's RunPython function
    normalize_emails_and_repair_drift(apps, None)

    # Verify email was normalized to lowercase
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT email FROM accounts_user WHERE username = 'mig_mixed'"
        )
        row = cursor.fetchone()

    assert row[0] == "mixedcase@migtest.com"


def test_migration_logic_repairs_privilege_drift():
    """The migration cleanup function syncs is_superuser=True users to ADMIN role."""
    import importlib
    mod = importlib.import_module(
        "apps.accounts.migrations.0003_add_email_uniqueness_and_manager"
    )
    normalize_emails_and_repair_drift = mod.normalize_emails_and_repair_drift
    from django.apps import apps

    # Create a drifted user: is_superuser=True but role=USER
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO accounts_user "
            "(password, is_superuser, username, first_name, last_name, "
            "email, is_staff, is_active, date_joined, "
            "display_name, bio, avatar_url, role, level, "
            "credit_score, balance, frozen_balance, created_at, updated_at) "
            "VALUES "
            "('hash', 1, 'mig_drifted', '', '', "
            "'mig_drifted@test.com', 0, 1, '2026-01-01 00:00:00', "
            "'', '', '', 'USER', 'SEED', 0, 0, 0, "
            "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )

    normalize_emails_and_repair_drift(apps, None)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT role, is_staff, is_superuser FROM accounts_user "
            "WHERE username = 'mig_drifted'"
        )
        row = cursor.fetchone()

    assert row[0] == "ADMIN"
    assert row[1] == 1  # is_staff
    assert row[2] == 1  # is_superuser
