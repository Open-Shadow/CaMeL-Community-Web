"""Comprehensive tests for the payments and credits modules.

Covers:
- PaymentsService (deposit, escrow, settle, release, skill charge, appeal, tip, quantize)
- TransactionService (legacy deposit, deduct, freeze)
- CreditService (add/deduct credit, level calculation, discount rates, bounty freeze)
"""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.credits.models import CreditAction, CreditLog
from apps.credits.services import CreditService
from apps.payments.models import Transaction, TransactionType
from apps.payments.services import (
    APPEAL_FEE,
    PLATFORM_FEE_RATE,
    PaymentError,
    PaymentsService,
    TransactionService,
    quantize_amount,
)
from apps.workshop.models import Article, ArticleDifficulty, ArticleStatus, ArticleType
from common.constants import BOUNTY_FREEZE_THRESHOLD

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(
    username: str,
    *,
    balance: Decimal = Decimal("0.00"),
    frozen_balance: Decimal = Decimal("0.00"),
    credit_score: int = 0,
    level: str = "SEED",
) -> User:
    """Shortcut to create a User with specific financial/credit state."""
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="TestPass123!",
        display_name=username,
        balance=balance,
        frozen_balance=frozen_balance,
        credit_score=credit_score,
        level=level,
    )


def _create_article(author: User, *, title: str = "Test Article") -> Article:
    """Create a minimal article for tipping tests."""
    slug = f"test-{author.username}-{title.lower().replace(' ', '-')}-{Article.objects.count()}"
    return Article.objects.create(
        author=author,
        title=title,
        slug=slug,
        content="x" * 500,
        difficulty=ArticleDifficulty.BEGINNER,
        article_type=ArticleType.TUTORIAL,
        status=ArticleStatus.PUBLISHED,
        published_at=timezone.now(),
    )


# ===========================================================================
# quantize_amount
# ===========================================================================

class TestQuantizeAmount:
    def test_rounds_to_two_decimal_places(self):
        assert quantize_amount("1.005") == Decimal("1.01")  # half-up
        assert quantize_amount("1.004") == Decimal("1.00")

    def test_accepts_float(self):
        assert quantize_amount(2.5) == Decimal("2.50")

    def test_accepts_int(self):
        assert quantize_amount(3) == Decimal("3.00")

    def test_accepts_decimal(self):
        assert quantize_amount(Decimal("4.999")) == Decimal("5.00")

    def test_zero(self):
        assert quantize_amount(0) == Decimal("0.00")

    def test_negative(self):
        assert quantize_amount("-1.555") == Decimal("-1.56")


# ===========================================================================
# PaymentsService.create_deposit
# ===========================================================================

@pytest.mark.django_db
class TestCreateDeposit:
    def test_adds_to_balance_and_creates_transaction(self):
        user = _create_user("depositor", balance=Decimal("10.00"))
        result = PaymentsService.create_deposit(user, Decimal("25.50"))

        assert result == Decimal("25.50")
        user.refresh_from_db()
        assert user.balance == Decimal("35.50")

        tx = Transaction.objects.filter(
            user=user, transaction_type=TransactionType.DEPOSIT
        ).first()
        assert tx is not None
        assert tx.amount == Decimal("25.50")
        assert tx.balance_after == Decimal("35.50")

    def test_accepts_float_amount(self):
        user = _create_user("dep_float", balance=Decimal("0.00"))
        result = PaymentsService.create_deposit(user, 5.99)
        assert result == Decimal("5.99")
        user.refresh_from_db()
        assert user.balance == Decimal("5.99")

    def test_accepts_string_amount(self):
        user = _create_user("dep_str", balance=Decimal("0.00"))
        result = PaymentsService.create_deposit(user, "7.25")
        assert result == Decimal("7.25")

    def test_error_on_zero_amount(self):
        user = _create_user("dep_zero")
        with pytest.raises(PaymentError, match="充值金额必须大于 0"):
            PaymentsService.create_deposit(user, Decimal("0"))

    def test_error_on_negative_amount(self):
        user = _create_user("dep_neg")
        with pytest.raises(PaymentError, match="充值金额必须大于 0"):
            PaymentsService.create_deposit(user, Decimal("-5"))

    def test_reference_id_stored(self):
        user = _create_user("dep_ref")
        PaymentsService.create_deposit(user, Decimal("1.00"), reference_id="stripe_pi_123")

        tx = Transaction.objects.get(user=user)
        assert tx.reference_id == "stripe_pi_123"


# ===========================================================================
# PaymentsService.reserve_bounty_escrow
# ===========================================================================

@pytest.mark.django_db
class TestReserveBountyEscrow:
    def test_moves_balance_to_frozen(self):
        user = _create_user("escrow1", balance=Decimal("100.00"))
        result = PaymentsService.reserve_bounty_escrow(
            user, Decimal("30.00"), reference_id="bounty:1"
        )

        assert result == Decimal("30.00")
        user.refresh_from_db()
        assert user.balance == Decimal("70.00")
        assert user.frozen_balance == Decimal("30.00")

        tx = Transaction.objects.get(user=user)
        assert tx.transaction_type == TransactionType.BOUNTY_ESCROW
        assert tx.amount == Decimal("-30.00")

    def test_error_on_insufficient_balance(self):
        user = _create_user("escrow_broke", balance=Decimal("5.00"))
        with pytest.raises(PaymentError, match="余额不足"):
            PaymentsService.reserve_bounty_escrow(
                user, Decimal("10.00"), reference_id="bounty:2"
            )

    def test_error_on_zero_amount(self):
        user = _create_user("escrow_zero", balance=Decimal("10.00"))
        with pytest.raises(PaymentError, match="托管金额必须大于 0"):
            PaymentsService.reserve_bounty_escrow(
                user, Decimal("0"), reference_id="bounty:3"
            )

    def test_exact_balance_succeeds(self):
        user = _create_user("escrow_exact", balance=Decimal("20.00"))
        PaymentsService.reserve_bounty_escrow(
            user, Decimal("20.00"), reference_id="bounty:4"
        )
        user.refresh_from_db()
        assert user.balance == Decimal("0.00")
        assert user.frozen_balance == Decimal("20.00")


# ===========================================================================
# PaymentsService.settle_bounty_payout
# ===========================================================================

@pytest.mark.django_db
class TestSettleBountyPayout:
    def test_deducts_from_creator_frozen_adds_to_hunter(self):
        creator = _create_user("creator1", frozen_balance=Decimal("50.00"))
        hunter = _create_user("hunter1", balance=Decimal("0.00"))

        result = PaymentsService.settle_bounty_payout(
            creator, hunter, Decimal("50.00"), reference_id="bounty:10"
        )

        assert result == Decimal("50.00")
        creator.refresh_from_db()
        hunter.refresh_from_db()
        assert creator.frozen_balance == Decimal("0.00")
        assert hunter.balance == Decimal("50.00")

        # Hunter should have income transaction
        hunter_tx = hunter.transactions.filter(
            transaction_type=TransactionType.BOUNTY_INCOME
        ).first()
        assert hunter_tx is not None
        assert hunter_tx.amount == Decimal("50.00")

    def test_error_on_insufficient_frozen_balance(self):
        creator = _create_user("creator_broke", frozen_balance=Decimal("5.00"))
        hunter = _create_user("hunter_broke")
        with pytest.raises(PaymentError, match="冻结余额不足"):
            PaymentsService.settle_bounty_payout(
                creator, hunter, Decimal("10.00"), reference_id="bounty:11"
            )

    def test_zero_amount_returns_zero(self):
        creator = _create_user("creator_zero", frozen_balance=Decimal("10.00"))
        hunter = _create_user("hunter_zero")
        result = PaymentsService.settle_bounty_payout(
            creator, hunter, Decimal("0"), reference_id="bounty:12"
        )
        assert result == Decimal("0.00")


# ===========================================================================
# PaymentsService.release_bounty_to_creator
# ===========================================================================

@pytest.mark.django_db
class TestReleaseBountyToCreator:
    def test_returns_frozen_to_balance(self):
        user = _create_user(
            "release1", balance=Decimal("10.00"), frozen_balance=Decimal("40.00")
        )
        result = PaymentsService.release_bounty_to_creator(
            user, Decimal("40.00"), reference_id="bounty:20"
        )

        assert result == Decimal("40.00")
        user.refresh_from_db()
        assert user.balance == Decimal("50.00")
        assert user.frozen_balance == Decimal("0.00")

        tx = Transaction.objects.get(user=user)
        assert tx.transaction_type == TransactionType.BOUNTY_RELEASE
        assert tx.amount == Decimal("40.00")

    def test_error_on_insufficient_frozen(self):
        user = _create_user("release_broke", frozen_balance=Decimal("5.00"))
        with pytest.raises(PaymentError, match="冻结余额不足"):
            PaymentsService.release_bounty_to_creator(
                user, Decimal("10.00"), reference_id="bounty:21"
            )

    def test_zero_amount_returns_zero_no_op(self):
        user = _create_user("release_zero", frozen_balance=Decimal("10.00"))
        result = PaymentsService.release_bounty_to_creator(
            user, Decimal("0"), reference_id="bounty:22"
        )
        assert result == Decimal("0.00")
        assert Transaction.objects.filter(user=user).count() == 0


# ===========================================================================
# PaymentsService.charge_skill_call
# ===========================================================================

@pytest.mark.django_db
class TestChargeSkillCall:
    def test_deducts_from_caller_credits_creator_with_platform_fee(self):
        # credit_score=0 -> SEED -> discount=1.0
        caller = _create_user("caller1", balance=Decimal("10.00"), credit_score=0)
        creator = _create_user("skill_creator1", balance=Decimal("0.00"))

        result = PaymentsService.charge_skill_call(
            caller, creator, price=Decimal("2.00"), reference_id="skill:1:call:1"
        )

        # 1.0 discount -> charged = 2.00
        # platform fee = 2.00 * 0.15 = 0.30
        # creator income = 2.00 - 0.30 = 1.70
        assert result["charged_amount"] == Decimal("2.00")
        assert result["platform_fee"] == Decimal("0.30")
        assert result["creator_income"] == Decimal("1.70")

        caller.refresh_from_db()
        creator.refresh_from_db()
        assert caller.balance == Decimal("8.00")
        assert creator.balance == Decimal("1.70")

    def test_applies_credit_discount(self):
        # credit_score=100 -> CRAFTSMAN -> discount=0.95
        caller = _create_user("caller2", balance=Decimal("10.00"), credit_score=100)
        creator = _create_user("skill_creator2", balance=Decimal("0.00"))

        result = PaymentsService.charge_skill_call(
            caller, creator, price=Decimal("2.00"), reference_id="skill:2:call:1"
        )

        # 0.95 discount -> charged = 1.90
        # platform fee = 1.90 * 0.15 = 0.285 -> 0.29 (rounded)
        # creator income = 1.90 - 0.29 = 1.61
        assert result["charged_amount"] == Decimal("1.90")
        assert result["platform_fee"] == Decimal("0.29")  # 0.285 rounds to 0.29
        assert result["creator_income"] == Decimal("1.61")

    def test_expert_discount(self):
        # credit_score=500 -> EXPERT -> discount=0.90
        caller = _create_user("caller3", balance=Decimal("20.00"), credit_score=500)
        creator = _create_user("skill_creator3", balance=Decimal("0.00"))

        result = PaymentsService.charge_skill_call(
            caller, creator, price=Decimal("10.00"), reference_id="skill:3:call:1"
        )

        # 0.90 discount -> charged = 9.00
        assert result["charged_amount"] == Decimal("9.00")

    def test_error_on_insufficient_balance(self):
        caller = _create_user("caller_broke", balance=Decimal("0.50"), credit_score=0)
        creator = _create_user("skill_creator_broke")

        with pytest.raises(PaymentError, match="余额不足"):
            PaymentsService.charge_skill_call(
                caller, creator, price=Decimal("2.00"), reference_id="skill:4:call:1"
            )

    def test_zero_price_returns_zeros(self):
        caller = _create_user("caller_free", balance=Decimal("10.00"))
        creator = _create_user("skill_creator_free")

        result = PaymentsService.charge_skill_call(
            caller, creator, price=Decimal("0"), reference_id="skill:5:call:1"
        )
        assert result["charged_amount"] == Decimal("0.00")
        assert result["creator_income"] == Decimal("0.00")
        assert result["platform_fee"] == Decimal("0.00")

    def test_creates_two_transactions(self):
        caller = _create_user("caller_tx", balance=Decimal("10.00"), credit_score=0)
        creator = _create_user("skill_creator_tx")

        PaymentsService.charge_skill_call(
            caller, creator, price=Decimal("1.00"), reference_id="skill:6:call:1"
        )

        assert caller.transactions.filter(
            transaction_type=TransactionType.SKILL_PURCHASE
        ).count() == 1
        assert creator.transactions.filter(
            transaction_type=TransactionType.SKILL_INCOME
        ).count() == 1


# ===========================================================================
# PaymentsService.charge_appeal_fee
# ===========================================================================

@pytest.mark.django_db
class TestChargeAppealFee:
    def test_deducts_half_dollar(self):
        user = _create_user("appeal1", balance=Decimal("5.00"))
        result = PaymentsService.charge_appeal_fee(
            user, reference_id="arb:1"
        )

        assert result == APPEAL_FEE  # $0.50
        user.refresh_from_db()
        assert user.balance == Decimal("4.50")

        tx = Transaction.objects.get(user=user)
        assert tx.transaction_type == TransactionType.PLATFORM_FEE
        assert tx.amount == Decimal("-0.50")

    def test_error_on_insufficient_balance(self):
        user = _create_user("appeal_broke", balance=Decimal("0.30"))
        with pytest.raises(PaymentError, match="余额不足"):
            PaymentsService.charge_appeal_fee(user, reference_id="arb:2")

    def test_exact_balance_succeeds(self):
        user = _create_user("appeal_exact", balance=Decimal("0.50"))
        PaymentsService.charge_appeal_fee(user, reference_id="arb:3")
        user.refresh_from_db()
        assert user.balance == Decimal("0.00")


# ===========================================================================
# PaymentsService.create_tip
# ===========================================================================

@pytest.mark.django_db
class TestCreateTip:
    @patch("apps.credits.services.CreditService.add_credit", return_value=5)
    def test_transfers_amount_and_updates_article_total(self, mock_add_credit):
        tipper = _create_user("tipper1", balance=Decimal("20.00"))
        author = _create_user("author1", balance=Decimal("0.00"))
        article = _create_article(author)

        tip = PaymentsService.create_tip(tipper, article, Decimal("5.00"))

        assert tip.amount == Decimal("5.00")
        assert tip.tipper == tipper
        assert tip.recipient == author

        tipper.refresh_from_db()
        author.refresh_from_db()
        article.refresh_from_db()

        assert tipper.balance == Decimal("15.00")
        assert author.balance == Decimal("5.00")
        assert article.total_tips == Decimal("5.00")

    @patch("apps.credits.services.CreditService.add_credit", return_value=5)
    def test_creates_two_transactions(self, mock_add_credit):
        tipper = _create_user("tipper_tx", balance=Decimal("10.00"))
        author = _create_user("author_tx")
        article = _create_article(author)

        PaymentsService.create_tip(tipper, article, Decimal("3.00"))

        assert tipper.transactions.filter(
            transaction_type=TransactionType.TIP_SEND
        ).count() == 1
        assert author.transactions.filter(
            transaction_type=TransactionType.TIP_RECEIVE
        ).count() == 1

    def test_error_on_self_tip(self):
        author = _create_user("self_tipper", balance=Decimal("10.00"))
        article = _create_article(author)

        with pytest.raises(PaymentError, match="不能给自己的文章打赏"):
            PaymentsService.create_tip(author, article, Decimal("1.00"))

    def test_error_on_insufficient_balance(self):
        tipper = _create_user("tipper_broke", balance=Decimal("0.50"))
        author = _create_user("author_broke")
        article = _create_article(author)

        with pytest.raises(PaymentError, match="余额不足"):
            PaymentsService.create_tip(tipper, article, Decimal("1.00"))

    def test_error_on_zero_amount(self):
        tipper = _create_user("tipper_zero", balance=Decimal("10.00"))
        author = _create_user("author_zero")
        article = _create_article(author)

        with pytest.raises(PaymentError, match="打赏金额必须大于 0"):
            PaymentsService.create_tip(tipper, article, Decimal("0"))

    @patch("apps.credits.services.CreditService.add_credit", return_value=5)
    def test_awards_credit_for_tipping(self, mock_add_credit):
        tipper = _create_user("tipper_credit", balance=Decimal("10.00"))
        author = _create_user("author_credit")
        article = _create_article(author)

        tip = PaymentsService.create_tip(tipper, article, Decimal("2.00"))

        mock_add_credit.assert_called_once_with(
            tipper, CreditAction.TIP_GIVEN, str(tip.id)
        )

    @patch("apps.credits.services.CreditService.add_credit", return_value=5)
    def test_multiple_tips_accumulate_total(self, mock_add_credit):
        tipper = _create_user("multi_tipper", balance=Decimal("20.00"))
        author = _create_user("multi_author")
        article = _create_article(author)

        PaymentsService.create_tip(tipper, article, Decimal("3.00"))
        PaymentsService.create_tip(tipper, article, Decimal("2.00"))

        article.refresh_from_db()
        assert article.total_tips == Decimal("5.00")


# ===========================================================================
# TransactionService (legacy)
# ===========================================================================

@pytest.mark.django_db
class TestTransactionServiceRecordDeposit:
    def test_updates_balance_and_creates_transaction(self):
        user = _create_user("legacy_dep", balance=Decimal("5.00"))
        tx = TransactionService.record_deposit(user, Decimal("15.00"))

        user.refresh_from_db()
        assert user.balance == Decimal("20.00")
        assert tx.transaction_type == TransactionType.DEPOSIT
        assert tx.amount == Decimal("15.00")
        assert tx.balance_after == Decimal("20.00")

    def test_stores_stripe_payment_intent(self):
        user = _create_user("legacy_stripe")
        tx = TransactionService.record_deposit(
            user, Decimal("10.00"), stripe_payment_intent="pi_abc"
        )
        assert tx.stripe_payment_intent == "pi_abc"


@pytest.mark.django_db
class TestTransactionServiceDeduct:
    def test_reduces_balance(self):
        user = _create_user("legacy_ded", balance=Decimal("50.00"))
        tx = TransactionService.deduct(
            user, Decimal("20.00"), TransactionType.SKILL_PURCHASE, description="test"
        )

        user.refresh_from_db()
        assert user.balance == Decimal("30.00")
        assert tx.amount == Decimal("-20.00")
        assert tx.balance_after == Decimal("30.00")

    def test_insufficient_balance_raises(self):
        user = _create_user("legacy_ded_broke", balance=Decimal("5.00"))
        with pytest.raises(ValueError, match="余额不足"):
            TransactionService.deduct(
                user, Decimal("10.00"), TransactionType.SKILL_PURCHASE
            )


@pytest.mark.django_db
class TestTransactionServiceFreeze:
    def test_transfers_balance_to_frozen(self):
        user = _create_user("legacy_frz", balance=Decimal("100.00"))
        tx = TransactionService.freeze(user, Decimal("30.00"), reference_id="bounty:99")

        user.refresh_from_db()
        assert user.balance == Decimal("70.00")
        assert user.frozen_balance == Decimal("30.00")
        assert tx.transaction_type == TransactionType.BOUNTY_ESCROW
        assert tx.amount == Decimal("-30.00")

    def test_insufficient_balance_raises(self):
        user = _create_user("legacy_frz_broke", balance=Decimal("5.00"))
        with pytest.raises(ValueError, match="余额不足"):
            TransactionService.freeze(user, Decimal("10.00"))


# ===========================================================================
# CreditService.add_credit
# ===========================================================================

@pytest.mark.django_db
class TestAddCredit:
    def test_increases_score_and_creates_log(self):
        user = _create_user("credit_add", credit_score=0)
        new_score = CreditService.add_credit(
            user, CreditAction.REGISTER, "ref:1"
        )

        assert new_score == 50  # REGISTER gives +50
        user.refresh_from_db()
        assert user.credit_score == 50

        log = CreditLog.objects.get(user=user)
        assert log.action == CreditAction.REGISTER
        assert log.amount == 50
        assert log.score_before == 0
        assert log.score_after == 50

    def test_recalculates_level(self):
        user = _create_user("credit_level", credit_score=90)
        # REGISTER gives +50: 90+50=140 -> should be CRAFTSMAN
        CreditService.add_credit(user, CreditAction.REGISTER, "ref:2")

        user.refresh_from_db()
        assert user.credit_score == 140
        assert user.level == "CRAFTSMAN"

    def test_idempotency_with_same_key(self):
        user = _create_user("credit_idem", credit_score=0)
        score1 = CreditService.add_credit(
            user, CreditAction.REGISTER, "ref_ignored",
            idempotency_key="unique-key-1"
        )
        score2 = CreditService.add_credit(
            user, CreditAction.REGISTER, "ref_ignored",
            idempotency_key="unique-key-1"
        )

        assert score1 == score2
        # Only one log entry should exist
        assert CreditLog.objects.filter(user=user, action=CreditAction.REGISTER).count() == 1

    def test_unknown_action_returns_current_score(self):
        user = _create_user("credit_unknown", credit_score=42)
        score = CreditService.add_credit(user, "NONEXISTENT_ACTION", "ref:3")
        assert score == 42

    def test_score_does_not_go_below_zero(self):
        user = _create_user("credit_floor", credit_score=10)
        # BOUNTY_TIMEOUT gives -50 -> 10-50 = -40 -> clamped to 0
        score = CreditService.add_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:4")
        assert score == 0
        user.refresh_from_db()
        assert user.credit_score == 0

    def test_multiple_credits_accumulate(self):
        user = _create_user("credit_multi", credit_score=0)
        CreditService.add_credit(user, CreditAction.REGISTER, "ref:5a")  # +50
        CreditService.add_credit(user, CreditAction.PUBLISH_SKILL, "ref:5b")  # +10

        user.refresh_from_db()
        assert user.credit_score == 60


# ===========================================================================
# CreditService.deduct_credit
# ===========================================================================

@pytest.mark.django_db
class TestDeductCredit:
    @patch("apps.notifications.services.NotificationService.send")
    def test_decreases_score(self, mock_notify):
        user = _create_user("credit_ded", credit_score=200)
        new_score = CreditService.deduct_credit(
            user, CreditAction.BOUNTY_TIMEOUT, "ref:d1"
        )

        # BOUNTY_TIMEOUT = -50 -> 200-50 = 150
        assert new_score == 150
        user.refresh_from_db()
        assert user.credit_score == 150

    @patch("apps.notifications.services.NotificationService.send")
    def test_level_downgrade(self, mock_notify):
        # Start at 110 (CRAFTSMAN), deduct BOUNTY_TIMEOUT (-50) -> 60 -> still SEED boundary?
        # Actually 60 is still < 100 threshold? No, 110-50=60, SEED is 0-99
        user = _create_user("credit_down", credit_score=110, level="CRAFTSMAN")
        CreditService.deduct_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:d2")

        user.refresh_from_db()
        assert user.credit_score == 60
        assert user.level == "SEED"

    @patch("apps.notifications.services.NotificationService.send")
    def test_score_does_not_go_below_zero(self, mock_notify):
        user = _create_user("credit_ded_floor", credit_score=20)
        CreditService.deduct_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:d3")

        user.refresh_from_db()
        assert user.credit_score == 0

    def test_positive_action_is_no_op(self):
        user = _create_user("credit_ded_noop", credit_score=100)
        score = CreditService.deduct_credit(
            user, CreditAction.REGISTER, "ref:d4"
        )
        # REGISTER has +50, which is not negative, so no-op
        assert score == 100

    @patch("apps.notifications.services.NotificationService.send")
    def test_creates_log(self, mock_notify):
        user = _create_user("credit_ded_log", credit_score=200)
        CreditService.deduct_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:d5")

        log = CreditLog.objects.get(user=user)
        assert log.action == CreditAction.BOUNTY_TIMEOUT
        assert log.amount == -50
        assert log.score_before == 200
        assert log.score_after == 150


# ===========================================================================
# CreditService.calculate_level
# ===========================================================================

class TestCalculateLevel:
    """Test level calculation at exact tier boundaries."""

    def test_seed_at_zero(self):
        assert CreditService.calculate_level(0) == "SEED"

    def test_seed_at_99(self):
        assert CreditService.calculate_level(99) == "SEED"

    def test_craftsman_at_100(self):
        assert CreditService.calculate_level(100) == "CRAFTSMAN"

    def test_craftsman_at_499(self):
        assert CreditService.calculate_level(499) == "CRAFTSMAN"

    def test_expert_at_500(self):
        assert CreditService.calculate_level(500) == "EXPERT"

    def test_expert_at_1999(self):
        assert CreditService.calculate_level(1999) == "EXPERT"

    def test_master_at_2000(self):
        assert CreditService.calculate_level(2000) == "MASTER"

    def test_master_at_4999(self):
        assert CreditService.calculate_level(4999) == "MASTER"

    def test_grandmaster_at_5000(self):
        assert CreditService.calculate_level(5000) == "GRANDMASTER"

    def test_grandmaster_at_very_high(self):
        assert CreditService.calculate_level(99999) == "GRANDMASTER"


# ===========================================================================
# CreditService.get_discount_rate
# ===========================================================================

@pytest.mark.django_db
class TestGetDiscountRate:
    def test_seed_level_no_discount(self):
        user = _create_user("disc_seed", credit_score=0)
        assert CreditService.get_discount_rate(user) == 1.0

    def test_craftsman_5_percent(self):
        user = _create_user("disc_craft", credit_score=100)
        assert CreditService.get_discount_rate(user) == 0.95

    def test_expert_10_percent(self):
        user = _create_user("disc_expert", credit_score=500)
        assert CreditService.get_discount_rate(user) == 0.90

    def test_master_15_percent(self):
        user = _create_user("disc_master", credit_score=2000)
        assert CreditService.get_discount_rate(user) == 0.85

    def test_grandmaster_20_percent(self):
        user = _create_user("disc_gm", credit_score=5000)
        assert CreditService.get_discount_rate(user) == 0.80

    def test_boundary_99_is_seed(self):
        user = _create_user("disc_bound99", credit_score=99)
        assert CreditService.get_discount_rate(user) == 1.0

    def test_boundary_100_is_craftsman(self):
        user = _create_user("disc_bound100", credit_score=100)
        assert CreditService.get_discount_rate(user) == 0.95


# ===========================================================================
# CreditService.is_bounty_frozen
# ===========================================================================

@pytest.mark.django_db
class TestIsBountyFrozen:
    def test_not_frozen_when_null(self):
        user = _create_user("frz_null")
        assert CreditService.is_bounty_frozen(user) is False

    def test_frozen_when_future(self):
        user = _create_user("frz_future")
        user.bounty_freeze_until = timezone.now() + timezone.timedelta(days=1)
        user.save(update_fields=["bounty_freeze_until"])
        assert CreditService.is_bounty_frozen(user) is True

    def test_not_frozen_when_past(self):
        user = _create_user("frz_past")
        user.bounty_freeze_until = timezone.now() - timezone.timedelta(days=1)
        user.save(update_fields=["bounty_freeze_until"])
        assert CreditService.is_bounty_frozen(user) is False


# ===========================================================================
# Bounty freeze / unfreeze auto-trigger
# ===========================================================================

@pytest.mark.django_db
class TestBountyFreezeUnfreeze:
    @patch("apps.notifications.services.NotificationService.send")
    def test_auto_freeze_when_credit_drops_below_threshold(self, mock_notify):
        """When credit drops from >=30 to <30, bounty board should freeze."""
        user = _create_user("frz_auto", credit_score=50, level="SEED")
        # BOUNTY_TIMEOUT = -50 -> 50-50=0 < BOUNTY_FREEZE_THRESHOLD(30)
        CreditService.deduct_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:frz1")

        user.refresh_from_db()
        assert user.credit_score == 0
        assert user.bounty_freeze_until is not None
        assert CreditService.is_bounty_frozen(user) is True

    @patch("apps.notifications.services.NotificationService.send")
    def test_no_freeze_when_credit_stays_above_threshold(self, mock_notify):
        """Credit drops but stays >= threshold, no freeze."""
        user = _create_user("frz_no_auto", credit_score=200, level="CRAFTSMAN")
        # BOUNTY_TIMEOUT = -50 -> 200-50=150 >= 30
        CreditService.deduct_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:frz2")

        user.refresh_from_db()
        assert user.credit_score == 150
        assert user.bounty_freeze_until is None

    @patch("apps.notifications.services.NotificationService.send")
    def test_auto_unfreeze_when_credit_crosses_above_threshold(self, mock_notify):
        """When credit recovers from <30 to >=30, freeze should be lifted."""
        user = _create_user("unfrz_auto", credit_score=20, level="SEED")
        # Manually set freeze
        user.bounty_freeze_until = _dt.datetime.max.replace(tzinfo=_dt.timezone.utc)
        user.save(update_fields=["bounty_freeze_until"])
        assert CreditService.is_bounty_frozen(user) is True

        # REGISTER gives +50 -> 20+50=70 >= 30 -> should lift freeze
        CreditService.add_credit(user, CreditAction.REGISTER, "ref:unfrz1")

        user.refresh_from_db()
        assert user.credit_score == 70
        assert user.bounty_freeze_until is None
        assert CreditService.is_bounty_frozen(user) is False

    @patch("apps.notifications.services.NotificationService.send")
    def test_no_unfreeze_when_credit_stays_below_threshold(self, mock_notify):
        """Credit increases but stays below threshold, freeze stays."""
        user = _create_user("no_unfrz", credit_score=5, level="SEED")
        user.bounty_freeze_until = _dt.datetime.max.replace(tzinfo=_dt.timezone.utc)
        user.save(update_fields=["bounty_freeze_until"])

        # TIP_GIVEN gives +5 -> 5+5=10 < 30 -> no lift
        CreditService.add_credit(user, CreditAction.TIP_GIVEN, "ref:nounfrz1")

        user.refresh_from_db()
        assert user.credit_score == 10
        assert user.bounty_freeze_until is not None
        assert CreditService.is_bounty_frozen(user) is True

    @patch("apps.notifications.services.NotificationService.send")
    def test_freeze_notification_sent(self, mock_notify):
        """Verify a notification is created when freeze is applied."""
        user = _create_user("frz_notify", credit_score=40, level="SEED")
        # BOUNTY_TIMEOUT = -50 -> 40-50 = 0 (clamped) < 30 -> freeze
        CreditService.deduct_credit(user, CreditAction.BOUNTY_TIMEOUT, "ref:fn1")

        # Notification should have been sent
        mock_notify.assert_called()
        call_kwargs = mock_notify.call_args
        # The call uses keyword user= which maps to recipient
        assert "悬赏板已冻结" in str(call_kwargs)

    @patch("apps.notifications.services.NotificationService.send")
    def test_unfreeze_notification_sent(self, mock_notify):
        """Verify a notification is created when freeze is lifted."""
        user = _create_user("unfrz_notify", credit_score=20, level="SEED")
        user.bounty_freeze_until = _dt.datetime.max.replace(tzinfo=_dt.timezone.utc)
        user.save(update_fields=["bounty_freeze_until"])

        CreditService.add_credit(user, CreditAction.REGISTER, "ref:ufn1")

        mock_notify.assert_called()
        call_kwargs = mock_notify.call_args
        assert "悬赏板已解冻" in str(call_kwargs)


# ===========================================================================
# Integration: deposit -> skill call with different credit tiers
# ===========================================================================

@pytest.mark.django_db
class TestIntegrationSkillCallWithCreditTiers:
    """End-to-end: deposit money, then use skill with credit discount."""

    def test_grandmaster_gets_best_discount(self):
        caller = _create_user("gm_caller", credit_score=5000, level="GRANDMASTER")
        creator = _create_user("gm_creator")

        PaymentsService.create_deposit(caller, Decimal("100.00"))
        caller.refresh_from_db()

        result = PaymentsService.charge_skill_call(
            caller, creator, price=Decimal("10.00"), reference_id="skill:int:1"
        )

        # 0.80 discount -> 8.00 charged
        assert result["charged_amount"] == Decimal("8.00")
        caller.refresh_from_db()
        assert caller.balance == Decimal("92.00")

    def test_deposit_escrow_release_roundtrip(self):
        """Deposit -> escrow -> release back: balance should be restored."""
        user = _create_user("roundtrip")
        PaymentsService.create_deposit(user, Decimal("50.00"))
        user.refresh_from_db()

        PaymentsService.reserve_bounty_escrow(
            user, Decimal("30.00"), reference_id="bounty:int:1"
        )
        user.refresh_from_db()
        assert user.balance == Decimal("20.00")
        assert user.frozen_balance == Decimal("30.00")

        PaymentsService.release_bounty_to_creator(
            user, Decimal("30.00"), reference_id="bounty:int:1"
        )
        user.refresh_from_db()
        assert user.balance == Decimal("50.00")
        assert user.frozen_balance == Decimal("0.00")


# ===========================================================================
# CreditService.get_discounted_price
# ===========================================================================

@pytest.mark.django_db
class TestGetDiscountedPrice:
    def test_seed_no_discount(self):
        user = _create_user("price_seed", credit_score=0)
        result = CreditService.get_discounted_price(user, Decimal("10.00"))
        assert result == Decimal("10.00")

    def test_grandmaster_20_percent_off(self):
        user = _create_user("price_gm", credit_score=5000)
        result = CreditService.get_discounted_price(user, Decimal("10.00"))
        assert result == Decimal("8.00")

    def test_rounding(self):
        user = _create_user("price_round", credit_score=100)
        # 0.95 * 3.33 = 3.1635 -> 3.16
        result = CreditService.get_discounted_price(user, Decimal("3.33"))
        assert result == Decimal("3.16")
