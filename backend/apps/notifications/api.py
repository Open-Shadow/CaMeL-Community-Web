"""Notifications API routes."""
import json

from django.http import StreamingHttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.notifications.services import NotificationService
from common.permissions import AuthBearer

router = Router(tags=["notifications"], auth=AuthBearer())


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


class MarkAllReadOutput(Schema):
    message: str
    count: int


class NotificationStreamStatusOutput(Schema):
    status: str
    message: str


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


@router.get("", response=NotificationListOutput)
def list_notifications(request, limit: int = 20, offset: int = 0, unread_only: bool = False):
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


@router.get("/unread-count", response=dict[str, int])
def get_unread_count(request):
    return {"count": NotificationService.unread_count(request.auth)}


@router.post("/{notification_id}/read", response=NotificationOutput)
def mark_notification_read(request, notification_id: int):
    notification = NotificationService.mark_read(request.auth, notification_id)
    if not notification:
        raise HttpError(404, "通知不存在")
    return serialize_notification(notification)


@router.post("/read-all", response=MarkAllReadOutput)
def mark_all_notifications_read(request):
    count = NotificationService.mark_all_read(request.auth)
    return {"message": "已全部标记为已读", "count": count}


@router.get("/stream")
def notification_stream(request):
    payload = {
        "status": "placeholder",
        "message": "SSE 连接占位已提供，当前仍建议以前端轮询刷新为主。",
        "unread_count": NotificationService.unread_count(request.auth),
    }

    def event_stream():
        yield f"event: status\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@router.get("/stream-status", response=NotificationStreamStatusOutput)
def notification_stream_status(request):
    return {
        "status": "placeholder",
        "message": "SSE 已预留接口，当前为单次状态流占位实现。",
    }
