"""Notifications business logic."""
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification

User = get_user_model()


class NotificationService:
    """Service for creating and managing notifications."""

    @classmethod
    def send(cls, recipient, notification_type: str, title: str,
             content: str = "", reference_id: str = "") -> Notification:
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            content=content,
            reference_id=reference_id,
        )

    @classmethod
    def send_bulk(cls, recipients, notification_type: str, title: str,
                  content: str = "", reference_id: str = ""):
        notifications = [
            Notification(
                recipient=r,
                notification_type=notification_type,
                title=title,
                content=content,
                reference_id=reference_id,
            )
            for r in recipients
        ]
        return Notification.objects.bulk_create(notifications)

    @classmethod
    def list_for_user(cls, user, unread_only: bool = False,
                      limit: int = 20, offset: int = 0):
        qs = Notification.objects.filter(recipient=user)
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs.order_by("-created_at")[offset:offset + limit]

    @classmethod
    def unread_count(cls, user) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @classmethod
    def mark_read(cls, notification_id: int, user) -> bool:
        updated = Notification.objects.filter(
            id=notification_id, recipient=user, is_read=False
        ).update(is_read=True)
        return updated > 0

    @classmethod
    def mark_all_read(cls, user) -> int:
        return Notification.objects.filter(
            recipient=user, is_read=False
        ).update(is_read=True)
