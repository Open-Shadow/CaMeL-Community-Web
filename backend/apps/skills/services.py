"""Skills business logic."""
import time
from django.db import transaction
from django.utils.text import slugify
from django.db.models import Avg

from apps.skills.models import Skill, SkillCall, SkillReview, SkillStatus
from apps.credits.services import CreditService
from apps.credits.models import CreditAction


class SkillService:

    @staticmethod
    @transaction.atomic
    def create(creator, data: dict) -> Skill:
        base_slug = slugify(data["name"], allow_unicode=True) or f"skill-{creator.id}"
        slug = base_slug
        n = 1
        while Skill.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{n}"
            n += 1
        skill = Skill.objects.create(creator=creator, slug=slug, **data)
        return skill

    @staticmethod
    @transaction.atomic
    def update(skill: Skill, data: dict) -> Skill:
        for k, v in data.items():
            if v is not None:
                setattr(skill, k, v)
        skill.save()
        return skill

    @staticmethod
    @transaction.atomic
    def submit_for_review(skill: Skill) -> Skill:
        if skill.status != SkillStatus.DRAFT:
            raise ValueError("只有草稿状态的技能可以提交审核")
        skill.status = SkillStatus.PENDING_REVIEW
        skill.save(update_fields=["status"])
        return skill

    @staticmethod
    @transaction.atomic
    def call(skill: Skill, caller, input_text: str) -> SkillCall:
        if skill.status != SkillStatus.APPROVED:
            raise ValueError("该技能暂不可用")
        start = time.time()
        # Simulate LLM call (placeholder)
        output_text = f"[模拟输出] 基于输入「{input_text[:50]}」的处理结果。"
        duration_ms = int((time.time() - start) * 1000)

        amount = float(skill.price_per_use or 0)
        if amount > 0:
            discount = CreditService.get_discount_rate(caller)
            amount = round(amount * discount, 4)
            if caller.balance < amount:
                raise ValueError("余额不足")
            caller.balance -= amount
            caller.save(update_fields=["balance"])

        call = SkillCall.objects.create(
            skill=skill,
            caller=caller,
            skill_version=skill.current_version,
            input_text=input_text,
            output_text=output_text,
            amount_charged=amount,
            duration_ms=duration_ms,
        )
        Skill.objects.filter(pk=skill.pk).update(total_calls=skill.total_calls + 1)
        CreditService.add_credit(caller, CreditAction.SKILL_CALLED, str(skill.id))
        return call

    @staticmethod
    @transaction.atomic
    def add_review(skill: Skill, reviewer, rating: int, comment: str, tags: list) -> SkillReview:
        if not (1 <= rating <= 5):
            raise ValueError("评分须在1~5之间")
        review, created = SkillReview.objects.update_or_create(
            skill=skill, reviewer=reviewer,
            defaults={"rating": rating, "comment": comment, "tags": tags},
        )
        avg = SkillReview.objects.filter(skill=skill).aggregate(a=Avg("rating"))["a"] or 0
        Skill.objects.filter(pk=skill.pk).update(
            avg_rating=round(avg, 2),
            review_count=SkillReview.objects.filter(skill=skill).count(),
        )
        return review
