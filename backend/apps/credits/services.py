"""Credit service for managing user credit scores."""
from decimal import Decimal

from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.credits.models import CreditLog, CreditAction
from common.constants import CreditLevelConfig, BOUNTY_FREEZE_THRESHOLD

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

        user = User.objects.select_for_update().get(id=user.id)
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

        # Check if bounty freeze should be lifted
        if score_before < BOUNTY_FREEZE_THRESHOLD <= score_after:
            cls._lift_bounty_freeze(user)

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

        user = User.objects.select_for_update().get(id=user.id)
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

        # Auto-freeze bounty board if credit drops below threshold
        if score_before >= BOUNTY_FREEZE_THRESHOLD > score_after:
            cls._apply_bounty_freeze(user)

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

        user = User.objects.select_for_update().get(id=user.id)
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
    def get_discounted_price(cls, user: User, base_price: Decimal) -> Decimal:
        """
        Calculate discounted price for a Skill call based on user's credit level.

        Args:
            user: User instance
            base_price: Original price of the Skill

        Returns:
            Discounted price (rounded to 2 decimal places)
        """
        discount = Decimal(str(cls.get_discount_rate(user)))
        return (base_price * discount).quantize(Decimal("0.01"))

    @classmethod
    @transaction.atomic
    def admin_adjust(cls, user: User, amount: int, reference_id: str = "") -> int:
        """Admin manual credit adjustment. Supports arbitrary positive/negative amounts."""
        user = User.objects.select_for_update().get(id=user.id)
        score_before = user.credit_score
        score_after = max(0, score_before + amount)

        user.credit_score = score_after
        user.level = cls.calculate_level(score_after)
        user.save(update_fields=['credit_score', 'level'])

        CreditLog.objects.create(
            user=user,
            action=CreditAction.ADMIN_ADJUST,
            amount=amount,
            score_before=score_before,
            score_after=score_after,
            reference_id=reference_id,
        )

        # Check freeze/unfreeze
        if amount > 0 and score_before < BOUNTY_FREEZE_THRESHOLD <= score_after:
            cls._lift_bounty_freeze(user)
        elif amount < 0 and score_before >= BOUNTY_FREEZE_THRESHOLD > score_after:
            cls._apply_bounty_freeze(user)

        return score_after

    @classmethod
    def can_post_bounty(cls, user: User) -> bool:
        """Check if user can post bounty (credit score >= 50)."""
        if user.credit_score < 50:
            return False
        return not cls.is_bounty_frozen(user)

    @classmethod
    def can_apply_bounty(cls, user: User) -> bool:
        """Check if user can apply for bounty (credit score >= 50)."""
        if user.credit_score < 50:
            return False
        return not cls.is_bounty_frozen(user)

    @classmethod
    def can_arbitrate(cls, user: User) -> bool:
        """Check if user can participate in arbitration (credit score >= 500)."""
        return user.credit_score >= 500

    # =========================================================================
    # P3-CREDIT-002: Credit threshold checks
    # =========================================================================

    @classmethod
    def check_bounty_post_threshold(cls, user: User) -> tuple[bool, str]:
        """
        Check if user meets credit threshold to post a bounty.
        Returns (allowed, reason).
        """
        if cls.is_bounty_frozen(user):
            return False, "悬赏板已冻结，信用分不足 30，请通过社区活动恢复信用分"
        if user.credit_score < 50:
            return False, f"发布悬赏需要信用分 ≥ 50，当前 {user.credit_score} 分"
        return True, ""

    @classmethod
    def check_bounty_apply_threshold(cls, user: User) -> tuple[bool, str]:
        """
        Check if user meets credit threshold to apply for a bounty.
        Returns (allowed, reason).
        """
        if cls.is_bounty_frozen(user):
            return False, "悬赏板已冻结，信用分不足 30，请通过社区活动恢复信用分"
        if user.credit_score < 50:
            return False, f"接单悬赏需要信用分 ≥ 50，当前 {user.credit_score} 分"
        return True, ""

    @classmethod
    def check_arbitration_threshold(cls, user: User) -> tuple[bool, str]:
        """
        Check if user meets credit threshold for arbitration.
        Returns (allowed, reason).
        """
        if user.credit_score < 500:
            return False, f"参与仲裁需要信用分 ≥ 500（⚡ 专家级），当前 {user.credit_score} 分"
        return True, ""

    # =========================================================================
    # P3-CREDIT-004: Bounty board freeze logic
    # =========================================================================

    @classmethod
    def is_bounty_frozen(cls, user: User) -> bool:
        """Check if user's bounty board access is frozen."""
        if user.bounty_freeze_until is None:
            return False
        return timezone.now() < user.bounty_freeze_until

    @classmethod
    @transaction.atomic
    def _apply_bounty_freeze(cls, user: User) -> None:
        """
        Freeze user's bounty board access when credit drops below threshold.
        Freeze lasts until credit is restored above threshold.
        """
        # Set freeze with no expiry — only lifted when credit recovers
        import datetime as _dt
        user.bounty_freeze_until = _dt.datetime.max.replace(
            tzinfo=_dt.timezone.utc
        )
        user.save(update_fields=["bounty_freeze_until"])

        from apps.notifications.services import NotificationService
        NotificationService.send(
            recipient=user,
            notification_type="SYSTEM",
            title="悬赏板已冻结",
            content=f"您的信用分已降至 {user.credit_score}（低于 {BOUNTY_FREEZE_THRESHOLD}），"
                    "悬赏板功能已被冻结。请通过发布文章、参与社区活动等方式恢复信用分。",
        )

    @classmethod
    @transaction.atomic
    def _lift_bounty_freeze(cls, user: User) -> None:
        """Lift bounty board freeze when credit recovers above threshold."""
        if user.bounty_freeze_until is not None:
            user.bounty_freeze_until = None
            user.save(update_fields=["bounty_freeze_until"])

            from apps.notifications.services import NotificationService
            NotificationService.send(
                recipient=user,
                notification_type="SYSTEM",
                title="悬赏板已解冻",
                content=f"您的信用分已恢复至 {user.credit_score}（≥ {BOUNTY_FREEZE_THRESHOLD}），"
                        "悬赏板功能已恢复正常。",
            )
