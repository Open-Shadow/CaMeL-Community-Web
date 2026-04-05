"""Celery tasks for credit system."""
from celery import shared_task
from django.core.cache import cache


@shared_task
def refresh_credit_leaderboard():
    """Refresh the credit score leaderboard cache. Run every 10 minutes via Celery Beat."""
    from apps.credits.ranking_api import _build_leaderboard, CACHE_KEY

    entries, updated_at = _build_leaderboard()
    cache.set(CACHE_KEY, {"entries": entries, "updated_at": updated_at}, 700)
    return f"Leaderboard refreshed: {len(entries)} entries"
