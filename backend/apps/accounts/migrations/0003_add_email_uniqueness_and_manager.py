import apps.accounts.models
import django.db.models.functions.text
from django.db import migrations, models


def normalize_emails_and_repair_drift(apps, schema_editor):
    """Data cleanup that MUST run before the unique constraint is applied.

    1. Normalize all emails to lowercase.
    2. Detect case-insensitive duplicates and deactivate the older accounts,
       keeping the most-recently-active one.
    3. Repair privilege drift between role and is_superuser/is_staff.
    """
    User = apps.get_model("accounts", "User")

    # --- Step 1: Normalize user emails (strip whitespace + lowercase) ---
    from django.db.models.functions import Lower, Trim
    User.objects.update(email=Lower(Trim("email")))

    # --- Step 2: Detect and resolve case-insensitive duplicates ---
    from django.db.models import Count, F
    dupes = (
        User.objects.exclude(email="")
        .values("email")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )

    # Resolve allauth EmailAddress model once (may not be installed)
    try:
        EmailAddress = apps.get_model("account", "EmailAddress")
    except LookupError:
        EmailAddress = None

    for entry in dupes:
        email = entry["email"]
        # Keep the most recently active; deactivate the rest
        users = User.objects.filter(email=email).order_by(
            "-is_active",
            F("last_login").desc(nulls_last=True), "-date_joined",
        )
        keeper = users.first()
        for user in users[1:]:
            # Delete allauth EmailAddress rows for the duplicated email only
            # (preserve any unrelated secondary addresses the user may have).
            if EmailAddress is not None:
                EmailAddress.objects.filter(user_id=user.id, email=email).delete()
            # Deactivate and mark email to avoid constraint violation.
            # Truncate to 254 chars (Django's email max_length).
            new_email = f"deactivated_{user.id}_{email}"
            user.is_active = False
            user.email = new_email[:254]
            user.save(update_fields=["is_active", "email"])

    # --- Step 2b: Normalize allauth EmailAddress emails AFTER duplicates ---
    # Must run after duplicate cleanup so that lowering doesn't collide
    # with allauth's own uniqueness constraints on case-variant rows.
    if EmailAddress is not None:
        # First, deduplicate EmailAddress rows that would collide after
        # normalization.  For each (user, normalized_email) group with
        # multiple rows, keep the primary/verified/oldest one and delete
        # the rest.
        ea_dupes = (
            EmailAddress.objects
            .annotate(norm_email=Lower(Trim("email")))
            .values("user_id", "norm_email")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
        )
        for group in ea_dupes:
            # Find all rows for this user whose normalized email matches.
            # We annotate again so we can filter by the computed value.
            rows = (
                EmailAddress.objects
                .filter(user_id=group["user_id"])
                .annotate(norm_email=Lower(Trim("email")))
                .filter(norm_email=group["norm_email"])
                .order_by("-primary", "-verified", "id")
            )
            keeper_id = rows.values_list("id", flat=True).first()
            if keeper_id is not None:
                # Delete via a fresh queryset (can't .delete() on annotated qs)
                EmailAddress.objects.filter(
                    user_id=group["user_id"],
                    id__in=list(rows.exclude(id=keeper_id).values_list("id", flat=True)),
                ).delete()

        # Now safe to bulk-normalize
        EmailAddress.objects.update(email=Lower(Trim("email")))

    # --- Step 3: Repair privilege drift ---
    # is_superuser=True but role!=ADMIN -> set role=ADMIN, is_staff=True
    User.objects.filter(is_superuser=True).exclude(role="ADMIN").update(
        role="ADMIN", is_staff=True
    )
    # role=ADMIN but is_superuser=False -> set is_superuser=True, is_staff=True
    User.objects.filter(role="ADMIN", is_superuser=False).update(
        is_superuser=True, is_staff=True
    )
    # is_staff=True but role!=ADMIN -> clear is_staff (no admin access for non-admins)
    User.objects.filter(is_staff=True).exclude(role="ADMIN").update(
        is_staff=False
    )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_invitation_risk_fields'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # 1. Update manager (no schema change, safe to apply first)
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', apps.accounts.models.CamelUserManager()),
            ],
        ),
        # 2. Data cleanup BEFORE constraint
        migrations.RunPython(normalize_emails_and_repair_drift, reverse_noop),
        # 3. Now safe to add the unique constraint
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower('email'),
                name='unique_email_ci',
                condition=~models.Q(email=""),
            ),
        ),
    ]
