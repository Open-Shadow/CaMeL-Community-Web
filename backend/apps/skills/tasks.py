"""Skills Celery tasks (hot ranking updates, scan pipeline, etc.)."""
from celery import shared_task

from apps.skills.services import SkillService


@shared_task
def refresh_skill_trending_cache():
    return SkillService.refresh_trending_cache()


@shared_task
def refresh_skill_recommendation_cache():
    return SkillService.refresh_recommendation_cache()


@shared_task
def run_skill_scan(skill_id: int):
    """Run automated security scan on a submitted skill package."""
    from apps.skills.models import Skill, SkillStatus
    from apps.skills.package_service import PackageService
    from apps.skills.services import ModerationService

    try:
        skill = Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return {"error": f"Skill {skill_id} not found"}

    if skill.status != SkillStatus.SCANNING:
        return {"skipped": True, "reason": f"Skill status is {skill.status}"}

    if not skill.package_file:
        SkillService.complete_scan(skill, passed=False, issues=["文件包缺失"])
        return {"passed": False}

    try:
        file_contents = PackageService.extract_file_contents(skill.package_file)
    except Exception as e:
        SkillService.complete_scan(skill, passed=False, issues=[f"文件包解析失败：{e}"])
        return {"passed": False}

    passed, issues = ModerationService.auto_review(file_contents)
    SkillService.complete_scan(skill, passed=passed, issues=issues)
    return {"passed": passed, "issues": issues}

