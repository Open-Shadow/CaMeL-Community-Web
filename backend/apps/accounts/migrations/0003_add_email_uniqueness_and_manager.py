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

    # --- Step 1: Normalize emails to lowercase ---
    from django.db.models.functions import Lower
    User.objects.update(email=Lower("email"))

    # --- Step 2: Detect and resolve case-insensitive duplicates ---
    from django.db.models import Count
    dupes = (
        User.objects.values("email")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    for entry in dupes:
        email = entry["email"]
        # Keep the most recently active; deactivate the rest
        from django.db.models import F
        users = User.objects.filter(email=email).order_by(
            F("last_login").desc(nulls_last=True), "-date_joined",
        )
        keeper = users.first()
        for user in users[1:]:
            # Deactivate and mark email to avoid constraint violation
            user.is_active = False
            user.email = f"deactivated_{user.id}_{email}"
            user.save(update_fields=["is_active", "email"])

    # --- Step 3: Repair privilege drift ---
    # is_superuser=True but role!=ADMIN -> set role=ADMIN, is_staff=True
    User.objects.filter(is_superuser=True).exclude(role="ADMIN").update(
        role="ADMIN", is_staff=True
    )
    # role=ADMIN but is_superuser=False -> set is_superuser=True, is_staff=True
    User.objects.filter(role="ADMIN", is_superuser=False).update(
        is_superuser=True, is_staff=True
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
