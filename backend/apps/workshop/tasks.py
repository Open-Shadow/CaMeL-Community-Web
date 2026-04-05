"""Workshop Celery tasks for recommendations and lifecycle management."""
from celery import shared_task

from apps.workshop.services import ArticleService, SeriesService


@shared_task
def refresh_article_recommendation_cache():
    return ArticleService.refresh_recommendation_cache()


@shared_task
def detect_outdated_articles():
    return ArticleService.detect_outdated_articles()


@shared_task
def auto_archive_stale_articles():
    return ArticleService.auto_archive_stale_articles()


@shared_task
def cleanup_workshop_data():
    return ArticleService.cleanup_old_data()


@shared_task
def refresh_series_completion_rewards():
    return SeriesService.refresh_completion_rewards()
