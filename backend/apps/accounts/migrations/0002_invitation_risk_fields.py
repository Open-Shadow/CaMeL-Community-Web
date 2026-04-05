from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="registration_device_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="invitation",
            name="registration_ip_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="invitation",
            name="risk_flags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
