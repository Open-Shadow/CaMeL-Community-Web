"""Notifications business logic."""
from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.notifications.models import Notification

User = get_user_model()


class NotificationService:
    """Service layer for in-site notifications."""

    @staticmethod
    def send(
        recipient: User,
        notification_type: str,
        title: str,
        content: str = "",
        reference_id: str = "",
    ) -> Notification:
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            content=content,
            reference_id=reference_id,
        )

    @staticmethod
    def list_for_user(user: User, *, unread_only: bool = False, limit: int = 20, offset: int = 0):
        queryset = Notification.objects.filter(recipient=user).order_by("-created_at")
        if unread_only:
            queryset = queryset.filter(is_read=False)
        return queryset[offset:offset + limit]

    @staticmethod
    def total_for_user(user: User, *, unread_only: bool = False) -> int:
        queryset = Notification.objects.filter(recipient=user)
        if unread_only:
            queryset = queryset.filter(is_read=False)
        return queryset.count()

    @staticmethod
    def unread_count(user: User) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @staticmethod
    def mark_read(user: User, notification_id: int) -> Notification | None:
        notification = Notification.objects.filter(id=notification_id, recipient=user).first()
        if not notification:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        return notification

    @staticmethod
    def mark_all_read(user: User) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
