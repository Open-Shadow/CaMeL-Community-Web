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
    """Run automated security scan on a submitted skill package.

    Supports two modes:
    1. New skill: skill.status == SCANNING
    2. Version update: skill.status == APPROVED with a pending SCANNING version
    """
    from apps.skills.models import Skill, SkillStatus, VersionStatus
    from apps.skills.package_service import PackageService
    from apps.skills.services import ModerationService

    try:
        skill = Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return {"error": f"Skill {skill_id} not found"}

    # Determine which file to scan
    is_version_update = skill.status == SkillStatus.APPROVED
    pending_version = None

    if is_version_update:
        pending_version = skill.versions.filter(
            status=VersionStatus.SCANNING,
        ).order_by("-created_at").first()
        if not pending_version:
            return {"skipped": True, "reason": "No pending version to scan"}
        scan_file = pending_version.package_file
    elif skill.status == SkillStatus.SCANNING:
        scan_file = skill.package_file
    else:
        return {"skipped": True, "reason": f"Skill status is {skill.status}"}

    if not scan_file:
        SkillService.complete_scan(skill, passed=False, issues=["文件包缺失"])
        return {"passed": False}

    # Extract file contents for scanning
    try:
        file_contents = PackageService.extract_file_contents(scan_file)
    except Exception as e:
        SkillService.complete_scan(skill, passed=False, issues=[f"文件包解析失败：{e}"])
        return {"passed": False}

    # Run content scan
    passed, issues = ModerationService.auto_review(file_contents)

    # Metadata and version checks (generate warnings, not hard failures)
    warnings = []
    try:
        scan_file.seek(0)
        pkg_data = PackageService.process_upload(scan_file)
        version_in_pkg = pkg_data.get("version", "")
        # Check version matches what was declared
        if pending_version and version_in_pkg != pending_version.version:
            warnings.append(
                f"SKILL.md 中版本号 ({version_in_pkg}) 与提交的版本号 ({pending_version.version}) 不一致"
            )
        # Check required metadata
        if not pkg_data.get("name"):
            warnings.append("SKILL.md frontmatter 缺少 name 字段")
        if not pkg_data.get("description"):
            warnings.append("SKILL.md frontmatter 缺少 description 字段")
    except ValueError:
        # SemVer or other validation errors from process_upload are hard failures
        warnings.append("SKILL.md 元数据校验产生警告")
    except Exception:
        warnings.append("元数据提取失败，请检查 SKILL.md 格式")

    SkillService.complete_scan(
        skill, passed=passed, issues=issues, warnings=warnings if warnings else None,
    )
    return {"passed": passed, "issues": issues, "warnings": warnings}

