from django.db import migrations


def repair_privilege_drift(apps, schema_editor):
    """Sync role and Django auth flags for drifted accounts.

    - is_superuser=True but role!=ADMIN -> set role=ADMIN, is_staff=True
    - role=ADMIN but is_superuser=False -> set is_superuser=True, is_staff=True
    - Normalize all emails to lowercase
    """
    User = apps.get_model("accounts", "User")

    # Fix superusers without ADMIN role
    User.objects.filter(is_superuser=True).exclude(role="ADMIN").update(
        role="ADMIN", is_staff=True
    )

    # Fix ADMIN users without superuser flag
    User.objects.filter(role="ADMIN", is_superuser=False).update(
        is_superuser=True, is_staff=True
    )

    # Normalize emails to lowercase
    from django.db.models.functions import Lower
    User.objects.update(email=Lower("email"))


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_email_uniqueness_and_manager'),
    ]

    operations = [
        migrations.RunPython(repair_privilege_drift, reverse_noop),
    ]
