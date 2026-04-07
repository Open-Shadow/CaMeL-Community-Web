"""Credit ranking API routes."""
from ninja import Router, Schema
from django.core.cache import cache

from common.permissions import AuthBearer
from common.utils import build_absolute_media_url
from apps.credits.services import CreditService


router = Router(tags=["rankings"])


# =============================================================================
# Schemas
# =============================================================================

class LeaderboardEntry(Schema):
    rank: int
    user_id: int
    username: str
    display_name: str
    avatar_url: str
    level: str
    credit_score: int


class LeaderboardOutput(Schema):
    entries: list[LeaderboardEntry]
    updated_at: str | None
    my_rank: int | None = None
    my_score: int | None = None


# =============================================================================
# API Endpoints
# =============================================================================

CACHE_KEY = "credit_leaderboard_top50"


@router.get("/credit", response=LeaderboardOutput)
def get_credit_leaderboard(request):
    """Get top 50 users by credit score. Uses cache, updated periodically."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Try cache first
    cached = cache.get(CACHE_KEY)
    if cached:
        entries = cached["entries"]
        updated_at = cached["updated_at"]
    else:
        # Fallback: query directly
        entries, updated_at = _build_leaderboard()
        cache.set(CACHE_KEY, {"entries": entries, "updated_at": updated_at}, 600)

    entries = [
        {
            **entry,
            "avatar_url": build_absolute_media_url(request, entry.get("avatar_url", "")),
        }
        for entry in entries
    ]

    # Check if request has auth
    my_rank = None
    my_score = None
    user = getattr(request, "auth", None)
    if user:
        my_score = user.credit_score
        # Find user in leaderboard
        for entry in entries:
            if entry["user_id"] == user.id:
                my_rank = entry["rank"]
                break
        # If not in top 50, calculate rank
        if my_rank is None:
            my_rank = User.objects.filter(
                credit_score__gt=user.credit_score
            ).count() + 1

    return {
        "entries": entries,
        "updated_at": updated_at,
        "my_rank": my_rank,
        "my_score": my_score,
    }


def _build_leaderboard():
    """Build the credit leaderboard from database."""
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    User = get_user_model()

    top_users = (
        User.objects
        .filter(is_active=True, credit_score__gt=0)
        .order_by("-credit_score", "date_joined")[:50]
    )

    entries = []
    for rank, u in enumerate(top_users, 1):
        entries.append({
            "rank": rank,
            "user_id": u.id,
            "username": u.username,
            "display_name": u.display_name or u.username,
            "avatar_url": u.avatar_url,
            "level": u.level,
            "credit_score": u.credit_score,
        })

    updated_at = timezone.now().isoformat()
    return entries, updated_at
