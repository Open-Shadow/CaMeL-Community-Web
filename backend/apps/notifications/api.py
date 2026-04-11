"""Notifications API routes."""
import json
import time

from django.http import StreamingHttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.notifications.services import NotificationService
from common.permissions import AuthBearer

router = Router(tags=["notifications"], auth=AuthBearer())


# =============================================================================
# Schemas
# =============================================================================

class NotificationOutput(Schema):
    id: int
    notification_type: str
    title: str
    content: str
    reference_id: str
    is_read: bool
    created_at: str


class NotificationListOutput(Schema):
    items: list[NotificationOutput]
    limit: int
    offset: int
    total: int
    unread_count: int


class UnreadCountOutput(Schema):
    count: int


class MarkAllReadOutput(Schema):
    message: str
    count: int


class MessageOutput(Schema):
    message: str


class NotificationStreamStatusOutput(Schema):
    status: str
    message: str


# =============================================================================
# Helpers
# =============================================================================

def serialize_notification(notification) -> dict:
    return {
        "id": notification.id,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "content": notification.content,
        "reference_id": notification.reference_id,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response=NotificationListOutput)
def list_notifications(request, limit: int = 20, offset: int = 0, unread_only: bool = False):
    """List notifications for current user with pagination metadata."""
    safe_limit = min(max(limit, 1), 50)
    safe_offset = max(offset, 0)
    notifications = NotificationService.list_for_user(
        request.auth,
        unread_only=unread_only,
        limit=safe_limit,
        offset=safe_offset,
    )
    total = NotificationService.total_for_user(request.auth, unread_only=unread_only)
    unread_count = NotificationService.unread_count(request.auth)
    return {
        "items": [serialize_notification(item) for item in notifications],
        "limit": safe_limit,
        "offset": safe_offset,
        "total": total,
        "unread_count": unread_count,
    }


@router.get("/unread-count", response=UnreadCountOutput)
def get_unread_count(request):
    """Get unread notification count."""
    return {"count": NotificationService.unread_count(request.auth)}


@router.post("/{notification_id}/read", response=NotificationOutput)
def mark_notification_read(request, notification_id: int):
    """Mark a single notification as read."""
    notification = NotificationService.mark_read(request.auth, notification_id)
    if not notification:
        raise HttpError(404, "通知不存在")
    return serialize_notification(notification)


@router.post("/read-all", response=MarkAllReadOutput)
def mark_all_notifications_read(request):
    """Mark all notifications as read."""
    count = NotificationService.mark_all_read(request.auth)
    return {"message": "已全部标记为已读", "count": count}


@router.get("/stream")
def notification_stream(request):
    """SSE endpoint for real-time notifications."""
    user = request.auth

    def event_stream():
        last_count = NotificationService.unread_count(user)
        # Send initial count
        yield f"data: {json.dumps({'type': 'count', 'count': last_count})}\n\n"

        # Limit SSE connection lifetime to avoid blocking sync workers indefinitely.
        # Clients should reconnect on close (EventSource does this automatically).
        max_iterations = 60  # 60 * 5s = 5 minutes
        for _ in range(max_iterations):
            time.sleep(5)
            current_count = NotificationService.unread_count(user)
            if current_count != last_count:
                # New notifications arrived
                new_notifications = NotificationService.list_for_user(
                    user, unread_only=True, limit=5
                )
                payload = {
                    "type": "new",
                    "count": current_count,
                    "notifications": [
                        serialize_notification(n)
                        for n in new_notifications
                    ],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_count = current_count

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@router.get("/stream-status", response=NotificationStreamStatusOutput)
def notification_stream_status(request):
    """Check SSE stream availability status."""
    return {
        "status": "available",
        "message": "SSE 实时通知流已启用。",
    }
