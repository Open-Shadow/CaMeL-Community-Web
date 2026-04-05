"""Skills business logic."""
from datetime import timedelta
from difflib import SequenceMatcher
from collections import Counter
import re
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from apps.credits.models import CreditAction
from apps.credits.services import CreditService
from apps.notifications.services import NotificationService
from apps.payments.services import PaymentError, PaymentsService, quantize_amount
from apps.search.services import SearchService
from apps.skills.models import (
    PricingModel,
    Skill,
    SkillCall,
    SkillCategory,
    SkillReview,
    SkillStatus,
    SkillUsagePreference,
    SkillVersion,
)
from django.core.cache import cache
from common.constants import MAX_SKILL_PRICE, MIN_SKILL_PRICE

User = get_user_model()


class ModerationService:
    """Very small automatic moderation layer for phase 1."""

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
            r"</?(system|assistant|developer)>",
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

    @classmethod
    def auto_review(cls, payload: dict) -> tuple[bool, list[str]]:
        issues: list[str] = []

        for field in ("name", "description", "system_prompt", "user_prompt_template"):
            text = (payload.get(field) or "").strip()
            if not text:
                continue

            if any(pattern.search(text) for pattern in cls.JAILBREAK_PATTERNS):
                issues.append(f"{field} 包含疑似越狱或绕过规则指令")
            if any(pattern.search(text) for pattern in cls.INJECTION_PATTERNS):
                issues.append(f"{field} 包含疑似 prompt injection 片段")
            if any(pattern.search(text) for pattern in cls.SENSITIVE_PATTERNS):
                issues.append(f"{field} 包含敏感或高风险内容")

        if payload.get("pricing_model") == PricingModel.PER_USE and not payload.get("price_per_use"):
            issues.append("按次付费 Skill 必须填写单次价格")

        return len(issues) == 0, issues


class SkillService:
    """Service layer for phase 1 Skill marketplace."""

    TRENDING_CACHE_KEY = "skills:trending"
    RECOMMENDATION_CACHE_KEY = "skills:recommended:user:{user_id}"
    OUTPUT_FORMATS = {"text", "json", "markdown", "code"}

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
    def _normalize_and_validate(cls, data: dict, existing: Skill | None = None) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}

        name = (payload.get("name", existing.name if existing else "") or "").strip()
        description = (
            payload.get("description", existing.description if existing else "") or ""
        ).strip()
        system_prompt = (
            payload.get("system_prompt", existing.system_prompt if existing else "") or ""
        ).strip()
        user_prompt_template = (
            payload.get(
                "user_prompt_template",
                existing.user_prompt_template if existing else "",
            )
            or ""
        ).strip()
        output_format = (
            payload.get("output_format", existing.output_format if existing else "text")
            or "text"
        ).strip()
        example_input = (
            payload.get("example_input", existing.example_input if existing else "") or ""
        ).strip()
        example_output = (
            payload.get("example_output", existing.example_output if existing else "") or ""
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
        price_per_use = payload.get(
            "price_per_use",
            existing.price_per_use if existing else None,
        )

        if not name or len(name) < 2 or len(name) > 80:
            raise ValueError("Skill 名称长度需在 2 到 80 个字符之间")
        if not description or len(description) < 10 or len(description) > 500:
            raise ValueError("Skill 简介长度需在 10 到 500 个字符之间")
        if not system_prompt or len(system_prompt) < 10:
            raise ValueError("System Prompt 至少需要 10 个字符")
        if category not in set(SkillCategory.values):
            raise ValueError("Skill 分类无效")
        if len(tags) > 10:
            raise ValueError("标签最多 10 个")
        if output_format not in cls.OUTPUT_FORMATS:
            raise ValueError("输出格式无效")
        if pricing_model not in set(PricingModel.values):
            raise ValueError("定价模式无效")

        normalized_price: Decimal | None = None
        if pricing_model == PricingModel.PER_USE:
            if price_per_use in (None, ""):
                raise ValueError("按次付费 Skill 必须填写价格")
            normalized_price = Decimal(str(price_per_use)).quantize(Decimal("0.01"))
            if normalized_price < Decimal(str(MIN_SKILL_PRICE)) or normalized_price > Decimal(
                str(MAX_SKILL_PRICE)
            ):
                raise ValueError(
                    f"单次价格需在 ${MIN_SKILL_PRICE:.2f} 到 ${MAX_SKILL_PRICE:.2f} 之间"
                )

        return {
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
            "user_prompt_template": user_prompt_template,
            "output_format": output_format,
            "example_input": example_input,
            "example_output": example_output,
            "category": category,
            "tags": tags,
            "pricing_model": pricing_model,
            "price_per_use": normalized_price,
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
        payload = cls._normalize_and_validate(data)
        skill = Skill.objects.create(
            creator=creator,
            slug=cls._create_unique_slug(payload["name"], creator.id),
            **payload,
        )
        SkillVersion.objects.create(
            skill=skill,
            version=1,
            system_prompt=skill.system_prompt,
            user_prompt_template=skill.user_prompt_template,
            change_note="初始版本",
        )
        return skill

    @classmethod
    @transaction.atomic
    def update(cls, skill: Skill, data: dict) -> Skill:
        payload = cls._normalize_and_validate(data, existing=skill)
        prompt_changed = (
            payload["system_prompt"] != skill.system_prompt
            or payload["user_prompt_template"] != skill.user_prompt_template
        )
        content_changed = any(
            getattr(skill, field) != value
            for field, value in payload.items()
        )

        for field, value in payload.items():
            setattr(skill, field, value)

        if prompt_changed:
            combined_before = f"{skill.system_prompt}\n{skill.user_prompt_template}"
            combined_after = f"{payload['system_prompt']}\n{payload['user_prompt_template']}"
            similarity = SequenceMatcher(None, combined_before, combined_after).ratio()
            is_major = similarity < 0.5
            skill.current_version += 1
            SkillVersion.objects.create(
                skill=skill,
                version=skill.current_version,
                system_prompt=payload["system_prompt"],
                user_prompt_template=payload["user_prompt_template"],
                change_note="更新 Prompt",
                is_major=is_major,
            )
            version_ids = list(skill.versions.order_by("-version").values_list("id", flat=True)[10:])
            if version_ids:
                SkillVersion.objects.filter(id__in=version_ids).delete()
            if is_major and skill.status == SkillStatus.APPROVED:
                cls.notify_major_update(skill)

        if content_changed and skill.status == SkillStatus.REJECTED:
            skill.status = SkillStatus.DRAFT
            skill.rejection_reason = ""

        skill.save()
        if skill.status == SkillStatus.APPROVED:
            SearchService.sync_skill(skill)
        return skill

    @classmethod
    @transaction.atomic
    def submit_for_review(cls, skill: Skill) -> Skill:
        if skill.status not in (SkillStatus.DRAFT, SkillStatus.REJECTED):
            raise ValueError("只有草稿或被拒绝的技能可以提交审核")

        skill.status = SkillStatus.PENDING_REVIEW
        skill.rejection_reason = ""
        skill.save(update_fields=["status", "rejection_reason"])

        payload = {
            "name": skill.name,
            "description": skill.description,
            "system_prompt": skill.system_prompt,
            "user_prompt_template": skill.user_prompt_template,
            "pricing_model": skill.pricing_model,
            "price_per_use": skill.price_per_use,
        }
        passed, issues = ModerationService.auto_review(payload)

        if passed:
            skill.status = SkillStatus.APPROVED
            skill.rejection_reason = ""
            skill.save(update_fields=["status", "rejection_reason"])
            CreditService.add_credit(skill.creator, CreditAction.PUBLISH_SKILL, str(skill.id))
            SearchService.sync_skill(skill)
        else:
            skill.status = SkillStatus.REJECTED
            skill.rejection_reason = "；".join(issues)
            skill.save(update_fields=["status", "rejection_reason"])

        return skill

    @staticmethod
    @transaction.atomic
    def call(skill: Skill, caller, input_text: str) -> SkillCall:
        if skill.status != SkillStatus.APPROVED:
            raise ValueError("该技能暂不可用")
        if not input_text.strip():
            raise ValueError("请输入调用内容")

        start = time.time()
        output_text = f"[模拟输出] 基于输入「{input_text[:80]}」的处理结果。"
        duration_ms = max(1, int((time.time() - start) * 1000))
        amount_charged = Decimal("0.00")

        if skill.pricing_model == PricingModel.PER_USE and skill.price_per_use:
            try:
                payment_result = PaymentsService.charge_skill_call(
                    caller,
                    skill.creator,
                    price=skill.price_per_use,
                    reference_id=f"skill:{skill.id}:{caller.id}:{int(time.time() * 1000)}",
                )
            except PaymentError as exc:
                raise ValueError(str(exc)) from exc
            amount_charged = quantize_amount(payment_result["charged_amount"])

        preference = SkillUsagePreference.objects.filter(skill=skill, user=caller).first()
        selected_version = skill.current_version
        if preference and not preference.auto_follow_latest and preference.locked_version:
            if skill.versions.filter(version=preference.locked_version).exists():
                selected_version = preference.locked_version

        call = SkillCall.objects.create(
            skill=skill,
            caller=caller,
            skill_version=selected_version,
            input_text=input_text.strip(),
            output_text=output_text,
            amount_charged=amount_charged,
            duration_ms=duration_ms,
        )

        skill.total_calls += 1
        skill.save(update_fields=["total_calls"])

        if skill.total_calls % 100 == 0:
            CreditService.add_credit(skill.creator, CreditAction.SKILL_CALLED, str(skill.id))

        return call

    @staticmethod
    @transaction.atomic
    def add_review(skill: Skill, reviewer, rating: int, comment: str, tags: list) -> SkillReview:
        if not (1 <= rating <= 5):
            raise ValueError("评分须在 1 到 5 之间")
        existing = SkillReview.objects.filter(skill=skill, reviewer=reviewer).first()
        first_call = SkillCall.objects.filter(skill=skill, caller=reviewer).order_by("created_at").first()
        if not existing and not first_call:
            raise ValueError("必须先实际调用过该 Skill 才能评价")
        if not existing and first_call:
            from django.utils import timezone

            if first_call.created_at < timezone.now() - timedelta(hours=24):
                raise ValueError("首次调用超过 24 小时，评价窗口已关闭")

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
        return skill.versions.order_by("-version")

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
            defaults={"locked_version": None, "auto_follow_latest": True},
        )
        return preference

    @staticmethod
    @transaction.atomic
    def update_usage_preference(skill: Skill, user, *, locked_version: int | None, auto_follow_latest: bool) -> SkillUsagePreference:
        if not auto_follow_latest:
            if locked_version is None:
                raise ValueError("锁定版本时必须指定版本号")
            if not skill.versions.filter(version=locked_version).exists():
                raise ValueError("指定版本不存在")
        preference = SkillService.get_usage_preference(skill, user)
        preference.locked_version = None if auto_follow_latest else locked_version
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
