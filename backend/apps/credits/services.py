"""Credit service for managing user credit scores."""
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.credits.models import CreditLog, CreditAction
from common.constants import CreditLevelConfig

User = get_user_model()


class CreditService:
    """Service for managing user credit scores."""

    # Credit score changes for each action
    ACTION_SCORES = {
        CreditAction.REGISTER: 50,
        CreditAction.PUBLISH_SKILL: 10,
        CreditAction.SKILL_CALLED: 5,
        CreditAction.PUBLISH_ARTICLE: 15,
        CreditAction.ARTICLE_FEATURED: 30,
        CreditAction.BOUNTY_COMPLETED: 20,
        CreditAction.TIP_GIVEN: 5,
        CreditAction.ARBITRATION_SERVED: 25,
        CreditAction.INVITE_REGISTERED: 10,
        CreditAction.BOUNTY_TIMEOUT: -50,
        CreditAction.BOUNTY_FREEZE: -100,
    }

    @classmethod
    @transaction.atomic
    def add_credit(
        cls,
        user: User,
        action: str,
        reference_id: str = "",
        *,
        idempotency_key: str | None = None,
    ) -> int:
        """
        Add credit score to user.

        Args:
            user: User instance
            action: CreditAction value
            reference_id: Reference to related object
            idempotency_key: Stable key to avoid duplicate rewards

        Returns:
            New credit score
        """
        amount = cls.ACTION_SCORES.get(action, 0)
        if amount == 0:
            return user.credit_score

        if idempotency_key:
            existing_log = CreditLog.objects.filter(
                user=user,
                action=action,
                reference_id=idempotency_key,
            ).first()
            if existing_log:
                return existing_log.score_after

        score_before = user.credit_score
        score_after = max(0, score_before + amount)
        stored_reference = idempotency_key or reference_id

        # Update user
        user.credit_score = score_after
        user.level = cls.calculate_level(score_after)
        user.save(update_fields=['credit_score', 'level'])

        # Create log
        CreditLog.objects.create(
            user=user,
            action=action,
            amount=amount,
            score_before=score_before,
            score_after=score_after,
            reference_id=stored_reference,
        )

        return score_after

    @classmethod
    @transaction.atomic
    def deduct_credit(cls, user: User, action: str, reference_id: str = "") -> int:
        """
        Deduct credit score from user.

        Args:
            user: User instance
            action: CreditAction value
            reference_id: Reference to related object

        Returns:
            New credit score
        """
        amount = cls.ACTION_SCORES.get(action, 0)
        if amount >= 0:
            return user.credit_score

        score_before = user.credit_score
        score_after = max(0, score_before + amount)  # amount is negative

        # Update user
        user.credit_score = score_after
        user.level = cls.calculate_level(score_after)
        user.save(update_fields=['credit_score', 'level'])

        # Create log
        CreditLog.objects.create(
            user=user,
            action=action,
            amount=amount,
            score_before=score_before,
            score_after=score_after,
            reference_id=reference_id,
        )

        return score_after

    @classmethod
    @transaction.atomic
    def adjust_credit(
        cls,
        user: User,
        amount: int,
        reference_id: str = "",
        *,
        action: str = CreditAction.ADMIN_ADJUST,
    ) -> int:
        """Adjust credit by an arbitrary amount while preserving logs and level updates."""
        if amount == 0:
            return user.credit_score

        score_before = user.credit_score
        score_after = max(0, score_before + amount)

        user.credit_score = score_after
        user.level = cls.calculate_level(score_after)
        user.save(update_fields=["credit_score", "level"])

        CreditLog.objects.create(
            user=user,
            action=action,
            amount=amount,
            score_before=score_before,
            score_after=score_after,
            reference_id=reference_id,
        )

        return score_after

    # Maps CreditLevel keys to UserLevel enum values
    LEVEL_MAP = {
        "sprout": "SEED",
        "craftsman": "CRAFTSMAN",
        "expert": "EXPERT",
        "master": "MASTER",
        "grandmaster": "GRANDMASTER",
    }

    @classmethod
    def calculate_level(cls, score: int) -> str:
        level = CreditLevelConfig.get_level_by_score(score)
        return cls.LEVEL_MAP.get(level[0], "SEED")

    @classmethod
    def get_discount_rate(cls, user: User) -> float:
        """
        Get API discount rate for user.

        Args:
            user: User instance

        Returns:
            Discount rate (0.8 ~ 1.0)
        """
        return CreditLevelConfig.get_discount(user.credit_score)

    @classmethod
    def can_post_bounty(cls, user: User) -> bool:
        """Check if user can post bounty (credit score >= 50)."""
        return user.credit_score >= 50

    @classmethod
    def can_apply_bounty(cls, user: User) -> bool:
        """Check if user can apply for bounty (credit score >= 50)."""
        return user.credit_score >= 50

    @classmethod
    def can_arbitrate(cls, user: User) -> bool:
        """Check if user can participate in arbitration (credit score >= 500)."""
        return user.credit_score >= 500
