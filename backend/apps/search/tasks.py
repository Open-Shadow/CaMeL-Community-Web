"""Search maintenance tasks."""
from celery import shared_task

from apps.search.services import SearchService


@shared_task
def optimize_search_indexes():
    return SearchService.optimize_index_settings()
