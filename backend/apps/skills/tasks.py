"""Skills Celery tasks (hot ranking updates, etc.)."""
from celery import shared_task

from apps.skills.services import SkillService


@shared_task
def refresh_skill_trending_cache():
    return SkillService.refresh_trending_cache()


@shared_task
def refresh_skill_recommendation_cache():
    return SkillService.refresh_recommendation_cache()
