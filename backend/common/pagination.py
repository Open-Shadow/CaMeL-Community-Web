from ninja import Schema
from typing import Generic, TypeVar, Optional

T = TypeVar('T')


class CursorPage(Schema, Generic[T]):
    items: list[T]
    next_cursor: Optional[str] = None
    has_more: bool = False


def paginate_queryset(qs, cursor: Optional[str], page_size: int = 20):
    """Return (items, next_cursor, has_more) using cursor-based pagination on pk."""
    if cursor:
        qs = qs.filter(pk__lt=cursor)
    items = list(qs[:page_size + 1])
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]
    next_cursor = str(items[-1].pk) if has_more else None
    return items, next_cursor, has_more
