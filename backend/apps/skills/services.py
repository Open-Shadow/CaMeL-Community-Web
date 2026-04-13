"""Skills business logic."""
from datetime import timedelta
from collections import Counter
from io import BytesIO
import re
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.credits.models import CreditAction
from apps.credits.services import CreditService
from apps.notifications.services import NotificationService
from apps.payments.services import PaymentError, PaymentsService, quantize_amount, PLATFORM_FEE_RATE
from apps.search.services import SearchService
from apps.skills.models import (
    PricingModel,
    ScanResult,
    Skill,
    SkillCall,
    SkillCategory,
    SkillPurchase,
    SkillReport,
    SkillReview,
    SkillStatus,
    SkillUsagePreference,
    SkillVersion,
    VersionStatus,
    ReportReason,
)
from django.core.cache import cache
from common.constants import (
    MAX_SKILL_PRICE,
    MIN_SKILL_PRICE,
    REPORT_QUARANTINE_THRESHOLD,
    REPORT_ACCOUNT_AGE_DAYS,
    REPORT_DAILY_LIMIT,
    REVIEW_PURCHASE_AGE_DAYS,
    CreditLevelConfig,
)

User = get_user_model()


class ModerationService:
    """Automated security scanning for skill packages."""

    JAILBREAK_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"ignore (all )?(previous|above) instructions",
            r"disregard (all )?(previous|above) instructions",
            r"reveal (the )?(system|developer) prompt",
            r"bypass (all )?(rules|guardrails|restrictions)",
        ]
    ]
    INJECTION_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"<\/?(system|assistant|developer)>",
            r"role:\s*(system|assistant|developer)",
            r"BEGIN_(SYSTEM|PROMPT)",
        ]
    ]
    SENSITIVE_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"\bcredit card\b",
            r"\bsocial security\b",
            r"\bssh private key\b",
            r"\bmalware\b",
        ]
    ]
    SCRIPT_DANGER_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"curl\s.*\|\s*(ba)?sh",
            r"wget\s.*\|\s*(ba)?sh",
            r"\.(ssh|aws|env)\b",
            r"crontab\s",
            r"systemctl\s",
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"base64\s.*decode",
            r"pickle\.loads?\(",
        ]
    ]

    @classmethod
    def scan_text_content(cls, text: str) -> list[str]:
        """Scan a text string for dangerous patterns."""
        issues: list[str] = []
        if not text:
            return issues
        if any(p.search(text) for p in cls.JAILBREAK_PATTERNS):
            issues.append("包含疑似越狱或绕过规则指令")
        if any(p.search(text) for p in cls.INJECTION_PATTERNS):
            issues.append("包含疑似 prompt injection 片段")
        if any(p.search(text) for p in cls.SENSITIVE_PATTERNS):
            issues.append("包含敏感或高风险内容")
        return issues

    @classmethod
    def scan_script_content(cls, text: str) -> list[str]:
        """Scan script content for dangerous patterns."""
        issues: list[str] = []
        if not text:
            return issues
        if any(p.search(text) for p in cls.SCRIPT_DANGER_PATTERNS):
            issues.append("脚本包含潜在危险操作")
        return issues

    @classmethod
    def auto_review(cls, file_contents: dict[str, str]) -> tuple[bool, list[str]]:
        """Run automated review on extracted package file contents.

        Args:
            file_contents: dict mapping relative file paths to their text content.

        Returns:
            (passed, issues) tuple.
        """
        issues: list[str] = []

        for path, content in file_contents.items():
            lower_path = path.lower()
            if lower_path.endswith((".txt", ".md")):
                for issue in cls.scan_text_content(content):
                    issues.append(f"{path}: {issue}")
            if lower_path.endswith((".py", ".sh", ".bash", ".js", ".ts")):
                for issue in cls.scan_script_content(content):
                    issues.append(f"{path}: {issue}")

        return len(issues) == 0, issues


class SkillService:
    """Service layer for the package-based Skill marketplace."""

    TRENDING_CACHE_KEY = "skills:trending"
    RECOMMENDATION_CACHE_KEY = "skills:recommended:user:{user_id}"

    @classmethod
    def _clean_tags(cls, tags: list[str] | None) -> list[str]:
        if not tags:
            return []

        seen: set[str] = set()
        cleaned: list[str] = []
        for tag in tags:
            normalized = tag.strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(normalized[:50])
        return cleaned

    @classmethod
    def _validate_metadata(cls, data: dict, existing: Skill | None = None) -> dict:
        """Validate and normalize skill metadata (non-package fields)."""
        payload = {key: value for key, value in data.items() if value is not None}

        name = (payload.get("name", existing.name if existing else "") or "").strip()
        description = (
            payload.get("description", existing.description if existing else "") or ""
        ).strip()
        category = (
            payload.get("category", existing.category if existing else "") or ""
        ).strip()
        tags = cls._clean_tags(
            payload.get("tags", existing.tags if existing else []),
        )
        pricing_model = (
            payload.get(
                "pricing_model",
                existing.pricing_model if existing else PricingModel.FREE,
            )
            or PricingModel.FREE
        ).strip()
        price = payload.get(
            "price",
            existing.price if existing else None,
        )

        if not name or len(name) < 2 or len(name) > 80:
            raise ValueError("Skill 名称长度需在 2 到 80 个字符之间")
        if not description or len(description) < 10 or len(description) > 500:
            raise ValueError("Skill 简介长度需在 10 到 500 个字符之间")
        if category not in set(SkillCategory.values):
            raise ValueError("Skill 分类无效")
        if len(tags) > 10:
            raise ValueError("标签最多 10 个")
        if pricing_model not in set(PricingModel.values):
            raise ValueError("定价模式无效")

        normalized_price: Decimal | None = None
        if pricing_model == PricingModel.PAID:
            if price in (None, ""):
                raise ValueError("付费 Skill 必须填写价格")
            normalized_price = Decimal(str(price)).quantize(Decimal("0.01"))
            if normalized_price < Decimal(str(MIN_SKILL_PRICE)) or normalized_price > Decimal(
                str(MAX_SKILL_PRICE)
            ):
                raise ValueError(
                    f"价格需在 ${MIN_SKILL_PRICE:.2f} 到 ${MAX_SKILL_PRICE:.2f} 之间"
                )

        return {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags,
            "pricing_model": pricing_model,
            "price": normalized_price,
        }

    @staticmethod
    def _create_unique_slug(name: str, creator_id: int) -> str:
        base_slug = slugify(name, allow_unicode=True) or f"skill-{creator_id}"
        slug = base_slug
        suffix = 1
        while Skill.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    @classmethod
    @transaction.atomic
    def create(cls, creator, data: dict) -> Skill:
        """Create a new skill with package data.

        data must include 'package_file', 'package_sha256', 'package_size',
        'readme_html', and 'version' (SemVer string) in addition to metadata.
        """
        payload = cls._validate_metadata(data)
        version_str = data.get("version", "1.0.0")
        skill = Skill.objects.create(
            creator=creator,
            slug=cls._create_unique_slug(payload["name"], creator.id),
            package_file=data["package_file"],
            package_sha256=data["package_sha256"],
            package_size=data["package_size"],
            readme_html=data.get("readme_html", ""),
            current_version=version_str,
            **payload,
        )
        SkillVersion.objects.create(
            skill=skill,
            version=version_str,
            package_file=data["package_file"],
            package_sha256=data["package_sha256"],
            changelog=data.get("changelog", "初始版本"),
            status=VersionStatus.SCANNING,
        )
        return skill

    @classmethod
    @transaction.atomic
    def update(cls, skill: Skill, data: dict) -> Skill:
        """Update skill metadata and optionally upload a new version.

        For approved skills with a new package, the upload goes to a pending
        SkillVersion without changing the live Skill pointers. The creator must
        submit the new version for scan/review before it goes live.
        """
        payload = cls._validate_metadata(data, existing=skill)
        has_new_package = "package_file" in data and data["package_file"]

        content_changed = any(
            getattr(skill, field) != value
            for field, value in payload.items()
        )

        for field, value in payload.items():
            setattr(skill, field, value)

        if has_new_package:
            new_version = data.get("version")
            if not new_version:
                raise ValueError("新版本文件包必须包含版本号")

            # Enforce monotonic version progression against latest approved
            from apps.skills.package_service import PackageService
            new_tuple = PackageService.parse_semver_tuple(new_version)
            latest_approved = skill.versions.filter(
                status=VersionStatus.APPROVED,
            ).order_by("-created_at").first()
            if latest_approved:
                try:
                    latest_tuple = PackageService.parse_semver_tuple(latest_approved.version)
                    if new_tuple <= latest_tuple:
                        raise ValueError(
                            f"新版本 {new_version} 必须大于最新已审核版本 {latest_approved.version}"
                        )
                except ValueError as e:
                    if "必须大于" in str(e):
                        raise
                    # Skip unparseable old version

            # Reject duplicate version strings (any status)
            if skill.versions.filter(version=new_version).exists():
                raise ValueError(
                    f"版本 {new_version} 已存在，请使用更高的版本号"
                )

            # Supersede any existing SCANNING versions for approved skills
            # to enforce a single pending version lifecycle.
            if skill.status == SkillStatus.APPROVED:
                skill.versions.filter(
                    status=VersionStatus.SCANNING,
                ).update(status=VersionStatus.REJECTED)

            new_sv = SkillVersion.objects.create(
                skill=skill,
                version=new_version,
                package_file=data["package_file"],
                package_sha256=data["package_sha256"],
                changelog=data.get("changelog", "更新版本"),
                status=VersionStatus.SCANNING,
            )

            if skill.status != SkillStatus.APPROVED:
                # For non-approved skills, update the live pointers immediately
                # (they aren't public yet anyway).
                skill.package_file = data["package_file"]
                skill.package_sha256 = data["package_sha256"]
                skill.package_size = data["package_size"]
                skill.readme_html = data.get("readme_html", skill.readme_html)
                skill.current_version = new_version
            # For approved skills, live pointers stay unchanged until the new
            # version passes scan/admin review (see promote_version).

            # Trim old versions beyond the 10 most recent
            version_ids = list(
                skill.versions.order_by("-created_at").values_list("id", flat=True)[10:]
            )
            if version_ids:
                SkillVersion.objects.filter(id__in=version_ids).delete()

        if content_changed and skill.status == SkillStatus.REJECTED:
            skill.status = SkillStatus.DRAFT
            skill.rejection_reason = ""

        skill.save()
        if skill.status == SkillStatus.APPROVED:
            SearchService.sync_skill(skill)
        return skill

    @staticmethod
    @transaction.atomic
    def archive(skill: Skill) -> Skill:
        if skill.status == SkillStatus.ARCHIVED:
            raise ValueError("Skill 已处于下架状态")

        skill.status = SkillStatus.ARCHIVED
        skill.save(update_fields=["status", "updated_at"])
        SearchService.remove_skill(skill.id)
        cache.delete(SkillService.TRENDING_CACHE_KEY)
        return skill

    @staticmethod
    @transaction.atomic
    def restore(skill: Skill) -> Skill:
        if skill.status != SkillStatus.ARCHIVED:
            raise ValueError("只有已下架的 Skill 才能恢复")

        skill.status = SkillStatus.DRAFT
        skill.save(update_fields=["status", "updated_at"])
        return skill

    @staticmethod
    @transaction.atomic
    def reinstate_quarantined(skill: Skill) -> Skill:
        """Restore a quarantined skill to APPROVED availability.

        Two cases:
        1. Skill is ARCHIVED (full quarantine): find latest approved version,
           promote it as current_version, restore skill to APPROVED.
        2. Skill is APPROVED but has an ARCHIVED version that was quarantined
           (fallback-promoted case): reinstate that version to APPROVED and
           re-promote it if it's newer than current_version.
        """
        if skill.status == SkillStatus.ARCHIVED:
            # Find the version to reinstate: prefer already-approved, else restore
            # the most recently archived one (the quarantine victim).
            live_version = skill.versions.filter(
                status=VersionStatus.APPROVED
            ).order_by("-created_at").first()
            if not live_version:
                live_version = skill.versions.filter(
                    status=VersionStatus.ARCHIVED
                ).order_by("-created_at").first()
                if live_version:
                    live_version.status = VersionStatus.APPROVED
                    live_version.save(update_fields=["status"])
            if live_version:
                skill.current_version = live_version.version
                skill.package_file = live_version.package_file
            skill.status = SkillStatus.APPROVED
            skill.save(update_fields=["status", "current_version", "package_file", "updated_at"])
            SearchService.sync_skill(skill)
            cache.delete(SkillService.TRENDING_CACHE_KEY)
            return skill

        # Fallback case: skill is APPROVED, reinstate the most recently archived version
        quarantined = skill.versions.filter(
            status=VersionStatus.ARCHIVED
        ).order_by("-created_at").first()
        if quarantined:
            quarantined.status = VersionStatus.APPROVED
            quarantined.save(update_fields=["status"])
            # Re-promote if it's newer than current live version
            from packaging.version import Version as PkgVersion
            try:
                if not skill.current_version or PkgVersion(quarantined.version) > PkgVersion(skill.current_version):
                    skill.current_version = quarantined.version
                    skill.package_file = quarantined.package_file
                    skill.save(update_fields=["current_version", "package_file", "updated_at"])
            except Exception:
                pass
        return skill

    @staticmethod
    @transaction.atomic
    def delete(skill: Skill):
        skill_id = skill.id
        skill.delete()
        SearchService.remove_skill(skill_id)
        cache.delete(SkillService.TRENDING_CACHE_KEY)

    @classmethod
    @transaction.atomic
    def submit_for_review(cls, skill: Skill) -> Skill:
        """Submit skill for automated scanning.

        For DRAFT/REJECTED skills: transitions the whole skill to SCANNING.
        For APPROVED skills: submits the latest pending version for scan
        without changing the skill's live status.
        """
        if skill.status == SkillStatus.APPROVED:
            # Submit a pending version for review without affecting the live skill
            pending = skill.versions.filter(
                status=VersionStatus.SCANNING,
            ).order_by("-created_at").first()
            if not pending:
                raise ValueError("没有待审核的新版本")

            NotificationService.send(
                recipient=skill.creator,
                notification_type="skill_submitted",
                title="新版本已提交扫描",
                content=f"「{skill.name}」v{pending.version} 正在进行自动安全扫描。",
                reference_id=str(skill.id),
            )
            from apps.skills.tasks import run_skill_scan
            run_skill_scan.delay(skill.id)
            return skill

        if skill.status not in (SkillStatus.DRAFT, SkillStatus.REJECTED):
            raise ValueError("只有草稿或被拒绝的技能可以提交审核")

        if not skill.package_file:
            raise ValueError("请先上传 Skill 文件包")

        skill.status = SkillStatus.SCANNING
        skill.rejection_reason = ""
        skill.save(update_fields=["status", "rejection_reason"])

        # Mark latest version as scanning
        latest_version = skill.versions.order_by("-created_at").first()
        if latest_version and latest_version.status != VersionStatus.APPROVED:
            latest_version.status = VersionStatus.SCANNING
            latest_version.save(update_fields=["status"])

        NotificationService.send(
            recipient=skill.creator,
            notification_type="skill_submitted",
            title="Skill 已提交扫描",
            content=f"「{skill.name}」正在进行自动安全扫描。",
            reference_id=str(skill.id),
        )

        # Trigger async security scan
        from apps.skills.tasks import run_skill_scan
        run_skill_scan.delay(skill.id)

        return skill

    @classmethod
    @transaction.atomic
    def complete_scan(cls, skill: Skill, *, passed: bool, issues: list[str], warnings: list[str] | None = None) -> Skill:
        """Called after async scan completes."""
        latest_version = skill.versions.order_by("-created_at").first()
        is_version_update = skill.status == SkillStatus.APPROVED

        # Determine structured scan result
        if not passed:
            scan_result = ScanResult.FAIL
        elif warnings:
            scan_result = ScanResult.WARN
        else:
            scan_result = ScanResult.PASS_CLEAN

        # Persist scan result and warnings on the version
        if latest_version:
            latest_version.scan_result = scan_result
            latest_version.scan_warnings = warnings or []

        if not passed:
            if is_version_update:
                # Version-scoped failure: reject the version, keep skill approved
                if latest_version:
                    latest_version.status = VersionStatus.REJECTED
                    latest_version.save(update_fields=["status", "scan_result", "scan_warnings"])
                NotificationService.send(
                    recipient=skill.creator,
                    notification_type="skill_reviewed",
                    title="新版本扫描未通过",
                    content=f"「{skill.name}」v{latest_version.version if latest_version else '?'} 存在风险项：{'；'.join(issues)}",
                    reference_id=str(skill.id),
                )
            else:
                skill.status = SkillStatus.REJECTED
                skill.rejection_reason = "；".join(issues)
                skill.save(update_fields=["status", "rejection_reason"])
                if latest_version:
                    latest_version.status = VersionStatus.REJECTED
                    latest_version.save(update_fields=["status", "scan_result", "scan_warnings"])
                NotificationService.send(
                    recipient=skill.creator,
                    notification_type="skill_reviewed",
                    title="Skill 扫描未通过",
                    content=f"「{skill.name}」存在风险项：{skill.rejection_reason}",
                    reference_id=str(skill.id),
                )
            return skill

        # Check trust level for auto-publish
        creator_score = skill.creator.credit_score
        is_trusted = creator_score >= CreditLevelConfig.CRAFTSMAN_MIN

        if is_trusted:
            if latest_version:
                latest_version.status = VersionStatus.APPROVED
                latest_version.save(update_fields=["status", "scan_result", "scan_warnings"])
            if is_version_update:
                # Promote the approved version to live pointers
                cls._promote_version(skill, latest_version)
                NotificationService.send(
                    recipient=skill.creator,
                    notification_type="skill_reviewed",
                    title="新版本已自动上架",
                    content=f"「{skill.name}」v{latest_version.version if latest_version else '?'} 扫描通过，已自动上架。",
                    reference_id=str(skill.id),
                )
            else:
                skill.status = SkillStatus.APPROVED
                skill.rejection_reason = ""
                skill.save(update_fields=["status", "rejection_reason", "updated_at"])
                SearchService.sync_skill(skill)
                CreditService.add_credit(skill.creator, CreditAction.PUBLISH_SKILL, str(skill.id))
                NotificationService.send(
                    recipient=skill.creator,
                    notification_type="skill_reviewed",
                    title="Skill 已自动上架",
                    content=f"「{skill.name}」扫描通过，已自动上架。",
                    reference_id=str(skill.id),
                )
        else:
            if latest_version:
                latest_version.save(update_fields=["scan_result", "scan_warnings"])
            # Low-trust users: keep pending, needs admin approval
            msg = "新版本扫描通过，等待人工审核" if is_version_update else "Skill 扫描通过，等待人工审核"
            NotificationService.send(
                recipient=skill.creator,
                notification_type="skill_submitted",
                title=msg,
                content=f"「{skill.name}」扫描通过，正在等待管理员审核。",
                reference_id=str(skill.id),
            )

        return skill

    @staticmethod
    def resolve_package_file(skill: Skill, version: str | None = None):
        """Resolve the downloadable package file for a skill.

        Blocks archived/quarantined skills. Resolves through an APPROVED
        SkillVersion — never falls back to skill.package_file blindly.

        Returns the file field of the resolved version.
        Raises ValueError on any access violation.
        """
        if skill.status in (SkillStatus.ARCHIVED, SkillStatus.REJECTED):
            raise ValueError("该 Skill 当前不可访问")

        if version:
            version_obj = skill.versions.filter(
                version=version, status=VersionStatus.APPROVED,
            ).first()
            if not version_obj:
                raise ValueError("指定版本不存在或未通过审核")
        else:
            version_obj = skill.versions.filter(
                status=VersionStatus.APPROVED,
            ).order_by("-created_at").first()

        if not version_obj:
            raise ValueError("没有可用的已审核版本")

        if not version_obj.package_file:
            raise ValueError("指定版本文件包不存在")

        return version_obj.package_file

    @staticmethod
    def _promote_version(skill: Skill, version_obj) -> None:
        """Promote an approved version to be the live Skill pointers."""
        if not version_obj:
            return
        skill.package_file = version_obj.package_file
        skill.package_sha256 = version_obj.package_sha256
        skill.package_size = version_obj.package_file.size if version_obj.package_file else 0
        skill.current_version = version_obj.version
        # Re-render readme from the new package if possible
        try:
            from apps.skills.package_service import PackageService
            result = PackageService.process_upload(version_obj.package_file)
            skill.readme_html = result.get("readme_html", skill.readme_html)
        except Exception:
            pass
        skill.save()

    @classmethod
    @transaction.atomic
    def admin_approve(cls, skill: Skill, version_id: int | None = None) -> Skill:
        """Admin approves a skill or a pending version of an already-approved skill."""
        if skill.status == SkillStatus.APPROVED:
            # Version-scoped approval: target explicit version or fallback to latest
            if version_id:
                pending = skill.versions.filter(
                    id=version_id, status=VersionStatus.SCANNING,
                ).first()
                if not pending:
                    raise ValueError("指定版本不存在或不在待审核状态")
            else:
                pending = skill.versions.filter(
                    status=VersionStatus.SCANNING,
                ).order_by("-created_at").first()
            if not pending:
                raise ValueError("没有待审核的新版本")

            # Guard against SemVer rollback: pending version must be > current live
            from apps.skills.package_service import PackageService
            try:
                pending_tuple = PackageService.parse_semver_tuple(pending.version)
                live_tuple = PackageService.parse_semver_tuple(skill.current_version)
                if pending_tuple <= live_tuple:
                    raise ValueError(
                        f"待审核版本 {pending.version} 不高于当前版本 {skill.current_version}，无法上架"
                    )
            except ValueError as e:
                if "不高于" in str(e) or "无法上架" in str(e):
                    raise
                # Skip comparison if either version string is unparseable

            pending.status = VersionStatus.APPROVED
            pending.save(update_fields=["status"])
            cls._promote_version(skill, pending)
            NotificationService.send(
                recipient=skill.creator,
                notification_type="skill_reviewed",
                title="新版本审核通过",
                content=f"「{skill.name}」v{pending.version} 已通过审核并上架。",
                reference_id=str(skill.id),
            )
            return skill

        if skill.status != SkillStatus.SCANNING:
            raise ValueError("当前 Skill 不在扫描/待审核状态")

        skill.status = SkillStatus.APPROVED
        skill.rejection_reason = ""
        skill.save(update_fields=["status", "rejection_reason", "updated_at"])
        latest_version = skill.versions.order_by("-created_at").first()
        if latest_version:
            latest_version.status = VersionStatus.APPROVED
            latest_version.save(update_fields=["status"])
        SearchService.sync_skill(skill)
        CreditService.add_credit(skill.creator, CreditAction.PUBLISH_SKILL, str(skill.id))
        NotificationService.send(
            recipient=skill.creator,
            notification_type="skill_reviewed",
            title="Skill 审核通过",
            content=f"「{skill.name}」已通过审核并上架。",
            reference_id=str(skill.id),
        )
        return skill

    @staticmethod
    @transaction.atomic
    def admin_reject(skill: Skill, reason: str = "", version_id: int | None = None) -> Skill:
        """Admin rejects a skill or a pending version of an already-approved skill."""
        if skill.status not in (SkillStatus.SCANNING, SkillStatus.APPROVED):
            raise ValueError("当前 Skill 无法被拒绝")

        review_reason = reason.strip() or "未通过人工审核，请根据规范调整后重新提交。"

        if skill.status == SkillStatus.APPROVED:
            # Version-scoped rejection: target explicit version or fallback to latest
            if version_id:
                pending = skill.versions.filter(
                    id=version_id, status=VersionStatus.SCANNING,
                ).first()
                if not pending:
                    raise ValueError("指定版本不存在或不在待审核状态")
            else:
                pending = skill.versions.filter(
                    status=VersionStatus.SCANNING,
                ).order_by("-created_at").first()
            if not pending:
                raise ValueError("没有待审核的新版本")
            pending.status = VersionStatus.REJECTED
            pending.save(update_fields=["status"])
            NotificationService.send(
                recipient=skill.creator,
                notification_type="skill_reviewed",
                title="新版本审核未通过",
                content=f"「{skill.name}」v{pending.version} 未通过审核：{review_reason}",
                reference_id=str(skill.id),
            )
            return skill

        # New skill rejection (SCANNING → REJECTED)
        skill.status = SkillStatus.REJECTED
        skill.rejection_reason = review_reason
        skill.save(update_fields=["status", "rejection_reason", "updated_at"])
        latest_version = skill.versions.order_by("-created_at").first()
        if latest_version:
            latest_version.status = VersionStatus.REJECTED
            latest_version.save(update_fields=["status"])
        SearchService.remove_skill(skill.id)
        NotificationService.send(
            recipient=skill.creator,
            notification_type="skill_reviewed",
            title="Skill 审核未通过",
            content=f"「{skill.name}」未通过审核：{review_reason}",
            reference_id=str(skill.id),
        )
        return skill

    @classmethod
    @transaction.atomic
    def review(cls, skill: Skill, reviewer, *, approve: bool, reason: str = "", version_id: int | None = None) -> Skill:
        """Admin/moderator review action — approve or reject."""
        if approve:
            return cls.admin_approve(skill, version_id=version_id)
        return cls.admin_reject(skill, reason, version_id=version_id)

    @staticmethod
    @transaction.atomic
    def set_featured(skill: Skill, *, is_featured: bool) -> Skill:
        if is_featured and skill.status != SkillStatus.APPROVED:
            raise ValueError("只有已上架的 Skill 才能设为精选")
        skill.is_featured = bool(is_featured)
        skill.save(update_fields=["is_featured", "updated_at"])
        cache.delete(SkillService.TRENDING_CACHE_KEY)
        return skill

    @classmethod
    @transaction.atomic
    def call(cls, skill: Skill, caller, input_text: str) -> SkillCall:
        if skill.status != SkillStatus.APPROVED:
            raise ValueError("该技能暂不可用")
        if not input_text.strip():
            raise ValueError("请输入调用内容")

        # Check purchase for paid skills
        if skill.pricing_model == PricingModel.PAID and skill.creator_id != caller.id:
            if not SkillPurchase.objects.filter(skill=skill, user=caller).exists():
                raise ValueError("请先购买该 Skill")

        # Determine which version to use — always resolve to an APPROVED version
        preference = SkillUsagePreference.objects.filter(skill=skill, user=caller).first()

        selected_version_obj = None
        if preference and not preference.auto_follow_latest and preference.locked_version:
            selected_version_obj = skill.versions.filter(
                version=preference.locked_version,
                status=VersionStatus.APPROVED,
            ).first()

        if not selected_version_obj:
            # Default: latest approved version
            selected_version_obj = skill.versions.filter(
                status=VersionStatus.APPROVED,
            ).order_by("-created_at").first()

        if not selected_version_obj:
            raise ValueError("该技能暂无可用版本")

        selected_version_str = selected_version_obj.version

        # Check version is not security-archived (belt-and-suspenders, filter above excludes it)
        if selected_version_obj.status == VersionStatus.ARCHIVED:
            raise ValueError("该版本已因安全原因被封禁，无法调用")

        start = time.time()

        # Try to read prompts from package — use version-specific file if available
        package = selected_version_obj.package_file if selected_version_obj else skill.package_file
        output_text = cls._execute_from_package(
            package, input_text, selected_version_obj,
        )

        duration_ms = max(1, int((time.time() - start) * 1000))

        call = SkillCall.objects.create(
            skill=skill,
            caller=caller,
            skill_version=selected_version_str,
            input_text=input_text.strip(),
            output_text=output_text,
            duration_ms=duration_ms,
        )

        skill.total_calls += 1
        skill.save(update_fields=["total_calls"])

        if skill.total_calls % 100 == 0:
            CreditService.add_credit(skill.creator, CreditAction.SKILL_CALLED, str(skill.id))

        return call

    @classmethod
    def _execute_from_package(
        cls, package_file, user_input: str, version_obj,
    ) -> str:
        """Read prompt templates from package and execute on-platform.

        Raises ValueError if the package has no prompts/ directory (download-only skill).
        """
        if not package_file:
            raise ValueError("未找到文件包，该 Skill 仅支持下载使用")

        try:
            import zipfile
            from io import BytesIO

            content = package_file.read() if hasattr(package_file, 'read') else package_file
            if hasattr(package_file, 'seek'):
                package_file.seek(0)

            file_contents: dict[str, str] = {}
            with zipfile.ZipFile(BytesIO(content if isinstance(content, bytes) else content.read())) as zf:
                for name in zf.namelist():
                    if name.startswith("prompts/") and name.endswith((".txt", ".md")):
                        file_contents[name] = zf.read(name).decode("utf-8", errors="replace")

            system_prompt = file_contents.get("prompts/system.txt") or file_contents.get("prompts/system.md", "")
            user_template = file_contents.get("prompts/user_template.txt") or file_contents.get("prompts/user_template.md", "")

            if not system_prompt and not user_template:
                raise ValueError("该 Skill 仅支持下载使用，不包含可执行 Prompt 模板")

            # Apply user input to template
            if user_template:
                rendered = user_template.replace("{{input}}", user_input).replace("{{INPUT}}", user_input).replace("{$input}", user_input)
            else:
                rendered = user_input

            return f"[基于 Prompt 模板执行] {rendered[:200]}"

        except zipfile.BadZipFile:
            raise ValueError("文件包解析失败")
        except ValueError:
            raise
        except Exception:
            raise ValueError("文件包解析失败")

    @staticmethod
    @transaction.atomic
    def add_review(skill: Skill, reviewer, rating: int, comment: str, tags: list) -> SkillReview:
        if not (1 <= rating <= 5):
            raise ValueError("评分须在 1 到 5 之间")

        existing = SkillReview.objects.filter(skill=skill, reviewer=reviewer).first()

        # Dual review eligibility: SkillCall OR 7-day SkillPurchase
        has_call = SkillCall.objects.filter(skill=skill, caller=reviewer).exists()
        purchase = SkillPurchase.objects.filter(skill=skill, user=reviewer).first()
        has_mature_purchase = (
            purchase is not None
            and purchase.created_at <= timezone.now() - timedelta(days=REVIEW_PURCHASE_AGE_DAYS)
        )

        if not existing and not has_call and not has_mature_purchase:
            raise ValueError("需要调用过该 Skill 或购买满 7 天后才能评价")

        review, _created = SkillReview.objects.update_or_create(
            skill=skill,
            reviewer=reviewer,
            defaults={
                "rating": rating,
                "comment": comment.strip(),
                "tags": [tag.strip() for tag in tags if tag.strip()],
            },
        )
        ratings = list(SkillReview.objects.filter(skill=skill).values_list("rating", flat=True))
        ratings.sort()
        trim = int(len(ratings) * 0.05)
        trimmed = ratings[trim: len(ratings) - trim] if trim and len(ratings) > trim * 2 else ratings
        avg = sum(trimmed) / len(trimmed) if trimmed else 0
        skill.avg_rating = round(avg, 2)
        skill.review_count = len(ratings)
        skill.save(update_fields=["avg_rating", "review_count"])
        return review

    @staticmethod
    def list_versions(skill: Skill):
        return skill.versions.order_by("-created_at")

    @staticmethod
    def list_trending(limit: int = 10):
        safe_limit = min(max(limit, 1), 50)
        cached_ids: list[int] | None = cache.get(SkillService.TRENDING_CACHE_KEY)
        if cached_ids:
            skills_by_id = {
                skill.id: skill
                for skill in Skill.objects.select_related("creator").filter(id__in=cached_ids, status=SkillStatus.APPROVED)
            }
            ordered = [skills_by_id[skill_id] for skill_id in cached_ids if skill_id in skills_by_id]
            if ordered:
                return ordered[:safe_limit]

        skills = list(
            Skill.objects.select_related("creator").filter(status=SkillStatus.APPROVED).order_by(
                "-is_featured",
                "-total_calls",
                "-avg_rating",
                "-updated_at",
            )[:safe_limit]
        )
        cache.set(SkillService.TRENDING_CACHE_KEY, [skill.id for skill in skills], timeout=3600)
        return skills

    @staticmethod
    def refresh_trending_cache(limit: int = 20) -> list[int]:
        safe_limit = min(max(limit, 1), 50)
        skill_ids = list(
            Skill.objects.filter(status=SkillStatus.APPROVED)
            .order_by("-is_featured", "-total_calls", "-avg_rating", "-updated_at")
            .values_list("id", flat=True)[:safe_limit]
        )
        cache.set(SkillService.TRENDING_CACHE_KEY, skill_ids, timeout=3600)
        return skill_ids

    @staticmethod
    def _build_recommendation_reason(skill: Skill, categories: Counter, tags: Counter) -> str:
        overlap_tags = [tag for tag in skill.tags if tags.get(tag.lower(), 0) > 0]
        if overlap_tags:
            return f"匹配你常用的标签：{', '.join(overlap_tags[:2])}"
        if categories.get(skill.category, 0) > 0:
            return "匹配你近期常用的 Skill 分类"
        if skill.is_featured:
            return "精选 Skill，适合继续探索"
        return "基于社区热度与评分推荐"

    @classmethod
    def compute_recommended_skills(cls, user, *, limit: int = 8) -> list[dict]:
        safe_limit = min(max(limit, 1), 24)
        history = list(
            SkillCall.objects.select_related("skill")
            .filter(caller=user)
            .order_by("-created_at")[:80]
        )
        seen_skill_ids = {call.skill_id for call in history}
        category_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        creator_counter: Counter[int] = Counter()

        for call in history:
            category_counter[call.skill.category] += 1
            creator_counter[call.skill.creator_id] += 1
            for tag in call.skill.tags:
                tag_counter[tag.lower()] += 1

        candidates = (
            Skill.objects.select_related("creator")
            .filter(status=SkillStatus.APPROVED)
            .exclude(creator=user)
        )
        if seen_skill_ids:
            candidates = candidates.exclude(id__in=seen_skill_ids)

        scored: list[tuple[Decimal, Skill]] = []
        for skill in candidates[:200]:
            score = Decimal("0")
            score += Decimal(category_counter.get(skill.category, 0)) * Decimal("3")
            score += Decimal(sum(tag_counter.get(tag.lower(), 0) for tag in skill.tags)) * Decimal("1.2")
            score += Decimal("4") if skill.is_featured else Decimal("0")
            score += Decimal(str(skill.avg_rating)) * Decimal("1.5")
            score += Decimal(min(skill.total_calls, 200)) / Decimal("40")
            if creator_counter.get(skill.creator_id, 0):
                score += Decimal("1.5")
            scored.append((score, skill))

        scored.sort(key=lambda item: (item[0], item[1].is_featured, item[1].total_calls, item[1].id), reverse=True)
        results = []
        for score, skill in scored[:safe_limit]:
            results.append(
                {
                    "skill": skill,
                    "score": float(score),
                    "reason": cls._build_recommendation_reason(skill, category_counter, tag_counter),
                }
            )
        return results

    @classmethod
    def list_recommended(cls, user, *, limit: int = 8) -> list[dict]:
        safe_limit = min(max(limit, 1), 24)
        cache_key = cls.RECOMMENDATION_CACHE_KEY.format(user_id=user.id)
        cached_ids: list[int] | None = cache.get(cache_key)
        if cached_ids:
            skills_by_id = {
                skill.id: skill
                for skill in Skill.objects.select_related("creator").filter(id__in=cached_ids, status=SkillStatus.APPROVED)
            }
            ordered = [skills_by_id[skill_id] for skill_id in cached_ids if skill_id in skills_by_id][:safe_limit]
            if ordered:
                return [
                    {
                        "skill": skill,
                        "score": float(skill.avg_rating),
                        "reason": "基于你的近期调用历史离线生成",
                    }
                    for skill in ordered
                ]

        computed = cls.compute_recommended_skills(user, limit=safe_limit)
        cache.set(cache_key, [item["skill"].id for item in computed], timeout=6 * 3600)
        return computed

    @classmethod
    def refresh_recommendation_cache(cls, limit: int = 8) -> dict[str, int]:
        active_user_ids = list(
            SkillCall.objects.order_by("-created_at").values_list("caller_id", flat=True).distinct()[:100]
        )
        refreshed = 0
        for user_id in active_user_ids:
            recommendations = cls.compute_recommended_skills(
                User.objects.get(id=user_id),
                limit=limit,
            )
            cache.set(
                cls.RECOMMENDATION_CACHE_KEY.format(user_id=user_id),
                [item["skill"].id for item in recommendations],
                timeout=6 * 3600,
            )
            refreshed += 1
        return {"users": refreshed}

    @staticmethod
    def get_usage_preference(skill: Skill, user) -> SkillUsagePreference:
        preference, _created = SkillUsagePreference.objects.get_or_create(
            skill=skill,
            user=user,
            defaults={"locked_version": "", "auto_follow_latest": True},
        )
        return preference

    @staticmethod
    @transaction.atomic
    def update_usage_preference(skill: Skill, user, *, locked_version: str | None, auto_follow_latest: bool) -> SkillUsagePreference:
        if not auto_follow_latest:
            if not locked_version:
                raise ValueError("锁定版本时必须指定版本号")
            if not skill.versions.filter(version=locked_version).exists():
                raise ValueError("指定版本不存在")
        preference = SkillService.get_usage_preference(skill, user)
        preference.locked_version = "" if auto_follow_latest else (locked_version or "")
        preference.auto_follow_latest = auto_follow_latest
        preference.save(update_fields=["locked_version", "auto_follow_latest", "updated_at"])
        return preference

    @staticmethod
    def notify_major_update(skill: Skill):
        caller_ids = (
            SkillCall.objects.filter(skill=skill)
            .exclude(caller_id=skill.creator_id)
            .values_list("caller_id", flat=True)
            .distinct()
        )
        for caller_id in caller_ids:
            NotificationService.send(
                recipient=skill.creator.__class__.objects.get(id=caller_id),
                notification_type="SKILL_MAJOR_UPDATE",
                title=f"{skill.name} 发布重大更新",
                content=f"你使用过的 Skill《{skill.name}》已更新到 v{skill.current_version}。",
                reference_id=f"skill:{skill.id}:version:{skill.current_version}",
            )


class SkillPurchaseService:
    """Handle skill purchase and entitlement."""

    @staticmethod
    @transaction.atomic
    def purchase(skill: Skill, buyer) -> SkillPurchase:
        if skill.status != SkillStatus.APPROVED:
            raise ValueError("该 Skill 暂不可购买")

        # Idempotent: return existing purchase
        existing = SkillPurchase.objects.filter(skill=skill, user=buyer).first()
        if existing:
            return existing

        # Creator auto-gets free access
        if skill.creator_id == buyer.id:
            return SkillPurchase.objects.create(
                skill=skill, user=buyer, paid_amount=Decimal("0"), payment_type="FREE",
            )

        if skill.pricing_model == PricingModel.FREE:
            return SkillPurchase.objects.create(
                skill=skill, user=buyer, paid_amount=Decimal("0"), payment_type="FREE",
            )

        # PAID skill
        price = skill.price
        if not price or price <= 0:
            raise ValueError("Skill 价格配置异常")

        normalized_price = quantize_amount(price)

        buyer_locked = User.objects.select_for_update().get(id=buyer.id)
        if buyer_locked.balance < normalized_price:
            raise PaymentError("余额不足，请先充值")

        platform_fee = quantize_amount(normalized_price * PLATFORM_FEE_RATE)
        creator_income = quantize_amount(normalized_price - platform_fee)

        buyer_locked.balance = quantize_amount(buyer_locked.balance - normalized_price)
        buyer_locked.save(update_fields=["balance"])

        creator = User.objects.select_for_update().get(id=skill.creator_id)
        creator.balance = quantize_amount(creator.balance + creator_income)
        creator.save(update_fields=["balance"])

        purchase = SkillPurchase.objects.create(
            skill=skill, user=buyer_locked, paid_amount=normalized_price, payment_type="MONEY",
        )

        from apps.payments.models import TransactionType
        PaymentsService._create_transaction(
            buyer_locked,
            TransactionType.SKILL_PURCHASE,
            -normalized_price,
            reference_id=f"skill_purchase:{purchase.id}",
            description=f"购买 Skill「{skill.name}」",
        )
        PaymentsService._create_transaction(
            creator,
            TransactionType.SKILL_INCOME,
            creator_income,
            reference_id=f"skill_purchase:{purchase.id}",
            description=f"Skill「{skill.name}」销售收入",
        )

        return purchase

    @staticmethod
    def has_access(skill: Skill, user) -> bool:
        """Check if user has access (purchased or creator)."""
        if skill.creator_id == user.id:
            return True
        if skill.pricing_model == PricingModel.FREE:
            return True
        return SkillPurchase.objects.filter(skill=skill, user=user).exists()


class SkillReportService:
    """Handle community reporting and quarantine."""

    @staticmethod
    @transaction.atomic
    def report(skill: Skill, reporter, reason: str, detail: str = "") -> SkillReport:
        if skill.creator_id == reporter.id:
            raise ValueError("不能举报自己的 Skill")

        # Account age check
        if reporter.date_joined > timezone.now() - timedelta(days=REPORT_ACCOUNT_AGE_DAYS):
            raise ValueError(f"账号注册需满 {REPORT_ACCOUNT_AGE_DAYS} 天才能举报")

        # Daily limit
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = SkillReport.objects.filter(
            reporter=reporter, created_at__gte=today_start,
        ).count()
        if daily_count >= REPORT_DAILY_LIMIT:
            raise ValueError(f"每日举报上限 {REPORT_DAILY_LIMIT} 次")

        if reason not in set(ReportReason.values):
            raise ValueError("举报理由无效")

        report, created = SkillReport.objects.get_or_create(
            skill=skill,
            reporter=reporter,
            defaults={"reason": reason, "detail": detail.strip()},
        )

        if created:
            total_reports = SkillReport.objects.filter(skill=skill).count()
            if total_reports >= REPORT_QUARANTINE_THRESHOLD and skill.status == SkillStatus.APPROVED:
                # Version-scoped quarantine: archive only the current live version,
                # keep older safe approved versions accessible to entitled users.
                quarantined_version_str = skill.current_version
                current_version = skill.versions.filter(
                    version=skill.current_version,
                    status=VersionStatus.APPROVED,
                ).first()
                if current_version:
                    current_version.status = VersionStatus.ARCHIVED
                    current_version.save(update_fields=["status"])

                # Check if any other approved versions remain
                fallback = skill.versions.filter(
                    status=VersionStatus.APPROVED,
                ).order_by("-created_at").first()
                if fallback:
                    # Promote the latest safe version to live pointers
                    SkillService._promote_version(skill, fallback)
                else:
                    # No safe versions left — archive the whole skill
                    skill.status = SkillStatus.ARCHIVED
                    skill.save(update_fields=["status", "updated_at"])
                    SearchService.remove_skill(skill.id)

                NotificationService.send(
                    recipient=skill.creator,
                    notification_type="skill_reported",
                    title="Skill 版本已被隔离",
                    content=f"「{skill.name}」v{quarantined_version_str} 因多次举报已被隔离，等待管理员审核。",
                    reference_id=str(skill.id),
                )

        return report
