"""Notifications API routes."""
import json
import time
from ninja import Router, Schema
from django.http import StreamingHttpResponse

from common.permissions import AuthBearer
from apps.notifications.services import NotificationService

router = Router(tags=["notifications"])


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


class UnreadCountOutput(Schema):
    count: int


class MessageOutput(Schema):
    message: str


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/", response=list[NotificationOutput], auth=AuthBearer())
def list_notifications(request, unread_only: bool = False,
                       limit: int = 20, offset: int = 0):
    """List notifications for current user."""
    notifications = NotificationService.list_for_user(
        request.auth, unread_only=unread_only, limit=limit, offset=offset
    )
    return [
        {
            "id": n.id,
            "notification_type": n.notification_type,
            "title": n.title,
            "content": n.content,
            "reference_id": n.reference_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.get("/unread-count", response=UnreadCountOutput, auth=AuthBearer())
def get_unread_count(request):
    """Get unread notification count."""
    return {"count": NotificationService.unread_count(request.auth)}


@router.post("/{notification_id}/read", response={200: MessageOutput, 404: MessageOutput},
             auth=AuthBearer())
def mark_as_read(request, notification_id: int):
    """Mark a single notification as read."""
    if NotificationService.mark_read(notification_id, request.auth):
        return 200, {"message": "已标记为已读"}
    return 404, {"message": "通知不存在或已读"}


@router.post("/read-all", response=MessageOutput, auth=AuthBearer())
def mark_all_as_read(request):
    """Mark all notifications as read."""
    count = NotificationService.mark_all_read(request.auth)
    return {"message": f"已将 {count} 条通知标为已读"}


@router.get("/stream", auth=AuthBearer())
def notification_stream(request):
    """SSE endpoint for real-time notifications."""
    user = request.auth

    def event_stream():
        last_count = NotificationService.unread_count(user)
        # Send initial count
        yield f"data: {json.dumps({'type': 'count', 'count': last_count})}\n\n"

        while True:
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
                        {
                            "id": n.id,
                            "notification_type": n.notification_type,
                            "title": n.title,
                            "content": n.content,
                            "created_at": n.created_at.isoformat(),
                        }
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
