from django.db import models
from apps.accounts.models import CamelUser


class Notification(models.Model):
    recipient = models.ForeignKey(CamelUser, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_notification"
        indexes = [models.Index(fields=["recipient", "is_read", "created_at"])]
