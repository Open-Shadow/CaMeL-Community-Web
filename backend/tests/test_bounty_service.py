"""Comprehensive tests for BountyService business logic."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bounties.models import (
    Arbitration,
    ArbitrationVote,
    Bounty,
    BountyApplication,
    BountyComment,
    BountyDeliverable,
    BountyReview,
    BountyStatus,
)
from apps.bounties.services import BountyError, BountyService
from apps.credits.models import CreditLog
from apps.payments.models import TransactionType
from apps.payments.services import PaymentError

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _unique_email(prefix: str = "user") -> str:
    """Generate a unique email to avoid username collisions."""
    global _counter
    _counter += 1
    return f"{prefix}-{_counter}@test.com"


def make_user(
    *,
    balance: Decimal = Decimal("100.00"),
    credit_score: int = 100,
    role: str = "USER",
) -> User:
    email = _unique_email()
    user = User.objects.create_user(
        username=email,
        email=email,
        password="TestPass123!",
        display_name=email.split("@")[0],
        credit_score=credit_score,
        balance=balance,
        role=role,
    )
    # Ensure level is consistent with credit_score
    from apps.credits.services import CreditService

    user.level = CreditService.calculate_level(credit_score)
    user.save(update_fields=["level"])
    return user


def _future_deadline(days: int = 7) -> str:
    return (timezone.now() + timedelta(days=days)).isoformat()


def _past_deadline() -> str:
    return (timezone.now() - timedelta(hours=1)).isoformat()


def _default_bounty_data(**overrides) -> dict:
    defaults = {
        "title": "Test Bounty",
        "description": "A test bounty description.",
        "bounty_type": "GENERAL",
        "reward": 5.00,
        "deadline": _future_deadline(),
    }
    defaults.update(overrides)
    return defaults


def _create_bounty_and_accept(
    creator: User,
    hunter: User,
    reward: float = 5.00,
) -> tuple[Bounty, BountyApplication]:
    """Helper: create bounty, apply, and accept -- returns (bounty, application)."""
    bounty = BountyService.create_bounty(creator, _default_bounty_data(reward=reward))
    app = BountyService.apply(bounty, hunter, "I'll do it", 3)
    bounty = BountyService.accept_application(creator, bounty, app.id)
    return bounty, app


def _deliver_bounty(hunter: User, bounty: Bounty) -> BountyDeliverable:
    return BountyService.submit_delivery(hunter, bounty, "Here is my delivery")


# ===========================================================================
# 1. Bounty Lifecycle
# ===========================================================================


class TestCreateBounty:
    """Tests for BountyService.create_bounty()."""

    @pytest.mark.django_db
    def test_valid_creation(self):
        creator = make_user(balance=Decimal("50.00"))
        data = _default_bounty_data(reward=5.00)
        bounty = BountyService.create_bounty(creator, data)

        assert bounty.pk is not None
        assert bounty.title == "Test Bounty"
        assert bounty.status == BountyStatus.OPEN
        assert bounty.reward == Decimal("5.00")
        assert bounty.creator_id == creator.id

        # Escrow freeze check
        creator.refresh_from_db()
        assert creator.balance == Decimal("45.00")
        assert creator.frozen_balance == Decimal("5.00")

    @pytest.mark.django_db
    def test_reward_too_low(self):
        creator = make_user(balance=Decimal("50.00"))
        data = _default_bounty_data(reward=0.50)

        with pytest.raises(BountyError, match="悬赏金额至少为"):
            BountyService.create_bounty(creator, data)

    @pytest.mark.django_db
    def test_invalid_bounty_type(self):
        creator = make_user(balance=Decimal("50.00"))
        data = _default_bounty_data(bounty_type="INVALID_TYPE")

        with pytest.raises(BountyError, match="悬赏类型无效"):
            BountyService.create_bounty(creator, data)

    @pytest.mark.django_db
    def test_insufficient_balance(self):
        creator = make_user(balance=Decimal("1.00"))
        data = _default_bounty_data(reward=5.00)

        with pytest.raises(PaymentError, match="余额不足"):
            BountyService.create_bounty(creator, data)

    @pytest.mark.django_db
    def test_low_credit_score(self):
        creator = make_user(balance=Decimal("50.00"), credit_score=10)
        data = _default_bounty_data(reward=5.00)

        with pytest.raises(BountyError, match="信用分不足"):
            BountyService.create_bounty(creator, data)

    @pytest.mark.django_db
    def test_deadline_in_past(self):
        creator = make_user(balance=Decimal("50.00"))
        data = _default_bounty_data(deadline=_past_deadline())

        with pytest.raises(BountyError, match="截止时间必须晚于当前时间"):
            BountyService.create_bounty(creator, data)

    @pytest.mark.django_db
    def test_invalid_deadline_format(self):
        creator = make_user(balance=Decimal("50.00"))
        data = _default_bounty_data(deadline="not-a-date")

        with pytest.raises(BountyError, match="截止时间格式无效"):
            BountyService.create_bounty(creator, data)

    @pytest.mark.django_db
    def test_title_and_description_stripped(self):
        creator = make_user(balance=Decimal("50.00"))
        data = _default_bounty_data(title="  Spaced Title  ", description="  desc  ")
        bounty = BountyService.create_bounty(creator, data)

        assert bounty.title == "Spaced Title"
        assert bounty.description == "desc"


class TestApply:
    """Tests for BountyService.apply()."""

    @pytest.mark.django_db
    def test_valid_application(self):
        creator = make_user(balance=Decimal("50.00"))
        applicant = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        app = BountyService.apply(bounty, applicant, "My proposal", 5)

        assert app.pk is not None
        assert app.bounty_id == bounty.id
        assert app.applicant_id == applicant.id
        assert app.proposal == "My proposal"
        assert app.estimated_days == 5

    @pytest.mark.django_db
    def test_self_apply_error(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="不能申请自己发布的悬赏"):
            BountyService.apply(bounty, creator, "Self apply", 3)

    @pytest.mark.django_db
    def test_duplicate_application_updates(self):
        creator = make_user(balance=Decimal("50.00"))
        applicant = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        app1 = BountyService.apply(bounty, applicant, "First proposal", 5)
        app2 = BountyService.apply(bounty, applicant, "Updated proposal", 7)

        # Same row, updated in-place
        assert app1.id == app2.id
        app2.refresh_from_db()
        assert app2.proposal == "Updated proposal"
        assert app2.estimated_days == 7
        assert BountyApplication.objects.filter(bounty=bounty, applicant=applicant).count() == 1

    @pytest.mark.django_db
    def test_max_applicants_limit_enforced(self):
        creator = make_user(balance=Decimal("50.00"))
        first_applicant = make_user()
        second_applicant = make_user()
        bounty = BountyService.create_bounty(
            creator,
            _default_bounty_data(max_applicants=1),
        )

        BountyService.apply(bounty, first_applicant, "First proposal", 2)

        with pytest.raises(BountyError, match="最大申请人数"):
            BountyService.apply(bounty, second_applicant, "Second proposal", 2)

    @pytest.mark.django_db
    def test_low_credit_error(self):
        creator = make_user(balance=Decimal("50.00"))
        applicant = make_user(credit_score=10)
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="信用分不足"):
            BountyService.apply(bounty, applicant, "Proposal", 3)

    @pytest.mark.django_db
    def test_apply_to_non_open_bounty(self):
        creator = make_user(balance=Decimal("50.00"))
        applicant = make_user()
        hunter = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        app = BountyService.apply(bounty, hunter, "I'll take it", 3)
        BountyService.accept_application(creator, bounty, app.id)

        with pytest.raises(BountyError, match="当前悬赏不可申请"):
            BountyService.apply(bounty, applicant, "Late apply", 3)

    @pytest.mark.django_db
    def test_estimated_days_zero(self):
        creator = make_user(balance=Decimal("50.00"))
        applicant = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="预计天数必须大于 0"):
            BountyService.apply(bounty, applicant, "Proposal", 0)

    @pytest.mark.django_db
    def test_apply_expired_bounty(self):
        creator = make_user(balance=Decimal("50.00"))
        applicant = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        # Force deadline to the past
        bounty.deadline = timezone.now() - timedelta(hours=1)
        bounty.save(update_fields=["deadline"])

        with pytest.raises(BountyError, match="悬赏已截止"):
            BountyService.apply(bounty, applicant, "Too late", 3)


class TestAcceptApplication:
    """Tests for BountyService.accept_application()."""

    @pytest.mark.django_db
    def test_sets_status_in_progress(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        app = BountyService.apply(bounty, hunter, "Proposal", 3)

        bounty = BountyService.accept_application(creator, bounty, app.id)

        assert bounty.status == BountyStatus.IN_PROGRESS
        assert bounty.accepted_application_id == app.id

    @pytest.mark.django_db
    def test_non_creator_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        stranger = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        app = BountyService.apply(bounty, hunter, "Proposal", 3)

        with pytest.raises(BountyError, match="只有发布者可以选择接单者"):
            BountyService.accept_application(stranger, bounty, app.id)

    @pytest.mark.django_db
    def test_invalid_application_id(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="申请不存在"):
            BountyService.accept_application(creator, bounty, 99999)

    @pytest.mark.django_db
    def test_accept_when_not_open(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, app = _create_bounty_and_accept(creator, hunter)

        another_applicant = make_user()
        # Bounty is now IN_PROGRESS; create a new application manually
        new_app = BountyApplication.objects.create(
            bounty=bounty, applicant=another_applicant, proposal="p", estimated_days=1
        )

        with pytest.raises(BountyError, match="当前状态下不能选择接单者"):
            BountyService.accept_application(creator, bounty, new_app.id)


class TestSubmitDelivery:
    """Tests for BountyService.submit_delivery()."""

    @pytest.mark.django_db
    def test_valid_submission(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        deliverable = BountyService.submit_delivery(hunter, bounty, "My delivery")

        assert deliverable.pk is not None
        assert deliverable.content == "My delivery"
        assert deliverable.revision_number == 1
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DELIVERED

    @pytest.mark.django_db
    def test_non_hunter_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        stranger = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        with pytest.raises(BountyError, match="只有被接受的接单者可以提交交付"):
            BountyService.submit_delivery(stranger, bounty, "Imposter delivery")

    @pytest.mark.django_db
    def test_creator_cannot_submit(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        with pytest.raises(BountyError, match="只有被接受的接单者可以提交交付"):
            BountyService.submit_delivery(creator, bounty, "Creator delivery")

    @pytest.mark.django_db
    def test_wrong_status_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        # Bounty is OPEN -- cannot deliver without being accepted
        with pytest.raises(BountyError, match="只有被接受的接单者可以提交交付"):
            BountyService.submit_delivery(hunter, bounty, "Bad timing")

    @pytest.mark.django_db
    def test_empty_content_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        with pytest.raises(BountyError, match="交付内容不能为空"):
            BountyService.submit_delivery(hunter, bounty, "   ")

    @pytest.mark.django_db
    def test_delivery_with_attachments(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        deliverable = BountyService.submit_delivery(
            hunter, bounty, "Delivery with files", attachments=["file1.txt", "file2.pdf"]
        )

        assert deliverable.attachments == ["file1.txt", "file2.pdf"]


class TestRequestRevision:
    """Tests for BountyService.request_revision()."""

    @pytest.mark.django_db
    def test_increments_revision_count(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        bounty = BountyService.request_revision(creator, bounty, "Please fix X")
        assert bounty.revision_count == 1
        assert bounty.status == BountyStatus.REVISION

        # feedback comment created
        comment = BountyComment.objects.filter(bounty=bounty).last()
        assert "修改意见" in comment.content

    @pytest.mark.django_db
    def test_max_3_revisions_limit(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        for i in range(3):
            _deliver_bounty(hunter, bounty)
            bounty.refresh_from_db()
            bounty = BountyService.request_revision(creator, bounty, f"Fix #{i + 1}")

        # 4th revision should fail
        _deliver_bounty(hunter, bounty)
        bounty.refresh_from_db()
        with pytest.raises(BountyError, match="最多只能要求 3 轮修改"):
            BountyService.request_revision(creator, bounty, "Too many")

    @pytest.mark.django_db
    def test_non_creator_cannot_request(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        with pytest.raises(BountyError, match="只有发布者可以要求修改"):
            BountyService.request_revision(hunter, bounty, "Not allowed")

    @pytest.mark.django_db
    def test_wrong_status_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        # Status is IN_PROGRESS, not DELIVERED
        with pytest.raises(BountyError, match="当前状态下不能要求修改"):
            BountyService.request_revision(creator, bounty, "Not delivered yet")

    @pytest.mark.django_db
    def test_resubmit_after_revision(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        bounty = BountyService.request_revision(creator, bounty, "Fix it")

        # Hunter can resubmit when status is REVISION
        deliverable = BountyService.submit_delivery(hunter, bounty, "Fixed version")
        assert deliverable.revision_number == 2
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DELIVERED


class TestApproveDelivery:
    """Tests for BountyService.approve_delivery()."""

    @pytest.mark.django_db
    def test_completes_bounty_and_settles_payment(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter, reward=10.00)
        _deliver_bounty(hunter, bounty)

        bounty = BountyService.approve_delivery(creator, bounty)

        creator.refresh_from_db()
        hunter.refresh_from_db()
        bounty.refresh_from_db()

        assert bounty.status == BountyStatus.COMPLETED
        assert creator.frozen_balance == Decimal("0.00")
        assert hunter.balance == Decimal("10.00")

    @pytest.mark.django_db
    def test_credits_hunter(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"), credit_score=100)
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        BountyService.approve_delivery(creator, bounty)

        hunter.refresh_from_db()
        # CreditService.add_credit awards 20 for BOUNTY_COMPLETED
        assert hunter.credit_score == 120

    @pytest.mark.django_db
    def test_transactions_created(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter, reward=5.00)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)

        assert hunter.transactions.filter(transaction_type=TransactionType.BOUNTY_INCOME).count() == 1

    @pytest.mark.django_db
    def test_non_creator_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        with pytest.raises(BountyError, match="只有发布者可以验收通过"):
            BountyService.approve_delivery(hunter, bounty)

    @pytest.mark.django_db
    def test_wrong_status_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        # Status is IN_PROGRESS, not DELIVERED
        with pytest.raises(BountyError, match="当前状态下不能验收"):
            BountyService.approve_delivery(creator, bounty)


class TestCancelBounty:
    """Tests for BountyService.cancel_bounty()."""

    @pytest.mark.django_db
    def test_releases_escrow(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data(reward=10.00))
        creator.refresh_from_db()
        assert creator.balance == Decimal("40.00")
        assert creator.frozen_balance == Decimal("10.00")

        bounty = BountyService.cancel_bounty(creator, bounty, reason="Changed my mind")

        creator.refresh_from_db()
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.CANCELLED
        assert creator.balance == Decimal("50.00")
        assert creator.frozen_balance == Decimal("0.00")

    @pytest.mark.django_db
    def test_reason_comment_created(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        BountyService.cancel_bounty(creator, bounty, reason="No longer needed")

        comment = BountyComment.objects.filter(bounty=bounty).last()
        assert comment is not None
        assert "取消原因" in comment.content

    @pytest.mark.django_db
    def test_cancel_in_progress(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)

        bounty = BountyService.cancel_bounty(creator, bounty)
        assert bounty.status == BountyStatus.CANCELLED

    @pytest.mark.django_db
    def test_cannot_cancel_completed(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        with pytest.raises(BountyError, match="当前状态下不能取消悬赏"):
            BountyService.cancel_bounty(creator, bounty)

    @pytest.mark.django_db
    def test_non_creator_error(self):
        creator = make_user(balance=Decimal("50.00"))
        stranger = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="只有发布者可以取消悬赏"):
            BountyService.cancel_bounty(stranger, bounty)


# ===========================================================================
# 2. Arbitration Flow
# ===========================================================================


def _setup_disputed_bounty() -> tuple[User, User, Bounty, Arbitration]:
    """Helper: create a bounty, accept, deliver, then dispute it."""
    creator = make_user(balance=Decimal("50.00"))
    hunter = make_user(balance=Decimal("5.00"))
    bounty, _ = _create_bounty_and_accept(creator, hunter, reward=10.00)
    _deliver_bounty(hunter, bounty)
    arbitration = BountyService.create_dispute(creator, bounty, "Work is incomplete")
    return creator, hunter, bounty, arbitration


def _create_arbitrators(count: int = 3, credit_score: int = 600) -> list[User]:
    return [make_user(credit_score=credit_score) for _ in range(count)]


class TestCreateDispute:
    """Tests for BountyService.create_dispute()."""

    @pytest.mark.django_db
    def test_starts_dispute(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        arb = BountyService.create_dispute(creator, bounty, "Not satisfied")

        assert arb.pk is not None
        assert arb.creator_statement == "Not satisfied"
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DISPUTED

    @pytest.mark.django_db
    def test_sets_24h_deadline(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        now = timezone.now()
        arb = BountyService.create_dispute(creator, bounty, "Issue")

        assert arb.deadline is not None
        # Deadline should be ~24h from now
        delta = arb.deadline - now
        assert timedelta(hours=23, minutes=59) < delta < timedelta(hours=24, minutes=1)

    @pytest.mark.django_db
    def test_hunter_can_dispute(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        # Force status to REVISION for hunter dispute
        bounty.status = BountyStatus.REVISION
        bounty.save(update_fields=["status"])

        arb = BountyService.create_dispute(hunter, bounty, "Creator is unfair")
        assert arb.hunter_statement == "Creator is unfair"

    @pytest.mark.django_db
    def test_wrong_status_error(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        # Bounty is OPEN
        with pytest.raises(BountyError, match="当前状态下不能发起争议"):
            BountyService.create_dispute(creator, bounty, "Dispute")

    @pytest.mark.django_db
    def test_stranger_cannot_dispute(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        stranger = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)

        with pytest.raises(BountyError, match="只有交易双方可以发起争议"):
            BountyService.create_dispute(stranger, bounty, "None of my business")


class TestSubmitStatement:
    """Tests for BountyService.submit_statement()."""

    @pytest.mark.django_db
    def test_creator_statement(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()

        arb = BountyService.submit_statement(creator, bounty, "My updated statement")
        assert arb.creator_statement == "My updated statement"

    @pytest.mark.django_db
    def test_hunter_statement(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()

        arb = BountyService.submit_statement(hunter, bounty, "Hunter rebuttal")
        assert arb.hunter_statement == "Hunter rebuttal"

    @pytest.mark.django_db
    def test_stranger_cannot_submit(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        stranger = make_user()

        with pytest.raises(BountyError, match="只有交易双方可以提交陈述"):
            BountyService.submit_statement(stranger, bounty, "Intruder statement")

    @pytest.mark.django_db
    def test_no_arbitration_error(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="当前悬赏没有争议案例"):
            BountyService.submit_statement(creator, bounty, "No dispute exists")


class TestStartArbitration:
    """Tests for BountyService.start_arbitration()."""

    @pytest.mark.django_db
    def test_selects_3_arbitrators(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        experts = _create_arbitrators(5, credit_score=600)

        # Expire cooling period
        arb.deadline = timezone.now() - timedelta(minutes=1)
        arb.save(update_fields=["deadline"])

        arb = BountyService.start_arbitration(creator, bounty)

        assert arb.arbitrators.count() == 3
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.ARBITRATING

    @pytest.mark.django_db
    def test_excludes_creator_and_hunter(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        # Give creator and hunter high credit so they'd qualify as arbitrators
        creator.credit_score = 600
        creator.save(update_fields=["credit_score"])
        hunter.credit_score = 600
        hunter.save(update_fields=["credit_score"])
        experts = _create_arbitrators(3, credit_score=600)

        arb.deadline = timezone.now() - timedelta(minutes=1)
        arb.save(update_fields=["deadline"])

        arb = BountyService.start_arbitration(creator, bounty)

        arbitrator_ids = set(arb.arbitrators.values_list("id", flat=True))
        assert creator.id not in arbitrator_ids
        assert hunter.id not in arbitrator_ids

    @pytest.mark.django_db
    def test_cooling_period_check(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        _create_arbitrators(3)

        # Deadline is in the future (cooling period not expired)
        with pytest.raises(BountyError, match="冷静期尚未结束"):
            BountyService.start_arbitration(creator, bounty)

    @pytest.mark.django_db
    def test_no_arbitration_error(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError):
            BountyService.start_arbitration(creator, bounty)

    @pytest.mark.django_db
    def test_fewer_than_3_qualified_candidates(self):
        """When fewer than 3 users have credit >= 500, only available ones are selected."""
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        experts = _create_arbitrators(2, credit_score=600)

        arb.deadline = timezone.now() - timedelta(minutes=1)
        arb.save(update_fields=["deadline"])

        arb = BountyService.start_arbitration(creator, bounty)
        # Only 2 candidates available
        assert arb.arbitrators.count() == 2


class TestCastVote:
    """Tests for BountyService.cast_vote()."""

    def _setup_voting(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        experts = _create_arbitrators(3, credit_score=600)
        arb.deadline = timezone.now() - timedelta(minutes=1)
        arb.save(update_fields=["deadline"])
        arb = BountyService.start_arbitration(creator, bounty)
        # Replace auto-selected arbitrators with our known ones
        arb.arbitrators.set(experts)
        return creator, hunter, bounty, arb, experts

    @pytest.mark.django_db
    def test_valid_vote(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()

        BountyService.cast_vote(experts[0], bounty, "HUNTER_WIN")

        assert ArbitrationVote.objects.filter(
            arbitration=arb, arbitrator=experts[0], vote="HUNTER_WIN"
        ).exists()

    @pytest.mark.django_db
    def test_non_arbitrator_error(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()
        stranger = make_user()

        with pytest.raises(BountyError, match="当前用户不是该仲裁案陪审员"):
            BountyService.cast_vote(stranger, bounty, "HUNTER_WIN")

    @pytest.mark.django_db
    def test_invalid_vote_value(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()

        with pytest.raises(BountyError, match="仲裁投票结果无效"):
            BountyService.cast_vote(experts[0], bounty, "INVALID")

    @pytest.mark.django_db
    def test_finalization_when_all_vote_hunter_win(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()

        BountyService.cast_vote(experts[0], bounty, "HUNTER_WIN")
        BountyService.cast_vote(experts[1], bounty, "HUNTER_WIN")
        BountyService.cast_vote(experts[2], bounty, "HUNTER_WIN")

        bounty.refresh_from_db()
        hunter.refresh_from_db()
        creator.refresh_from_db()
        arb.refresh_from_db()

        assert bounty.status == BountyStatus.COMPLETED
        assert arb.resolved_at is not None
        assert arb.result == "HUNTER_WIN"
        assert hunter.balance > Decimal("0.00")

    @pytest.mark.django_db
    def test_finalization_creator_win(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()

        BountyService.cast_vote(experts[0], bounty, "CREATOR_WIN")
        BountyService.cast_vote(experts[1], bounty, "CREATOR_WIN")
        BountyService.cast_vote(experts[2], bounty, "CREATOR_WIN")

        bounty.refresh_from_db()
        creator.refresh_from_db()
        arb.refresh_from_db()

        assert bounty.status == BountyStatus.CANCELLED
        assert arb.result == "CREATOR_WIN"
        # Escrow refunded to creator
        assert creator.frozen_balance == Decimal("0.00")

    @pytest.mark.django_db
    def test_finalization_partial(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()

        BountyService.cast_vote(experts[0], bounty, "PARTIAL", 0.6)
        BountyService.cast_vote(experts[1], bounty, "PARTIAL", 0.6)
        BountyService.cast_vote(experts[2], bounty, "PARTIAL", 0.6)

        bounty.refresh_from_db()
        hunter.refresh_from_db()
        creator.refresh_from_db()
        arb.refresh_from_db()

        assert bounty.status == BountyStatus.COMPLETED
        assert arb.result == "PARTIAL"
        # Hunter started with 5.00 (from _setup_disputed_bounty) + 6.00 payout
        assert hunter.balance == Decimal("11.00")
        assert creator.frozen_balance == Decimal("0.00")

    @pytest.mark.django_db
    def test_arbitrators_receive_credit(self):
        creator, hunter, bounty, arb, experts = self._setup_voting()
        initial_scores = [e.credit_score for e in experts]

        BountyService.cast_vote(experts[0], bounty, "HUNTER_WIN")
        BountyService.cast_vote(experts[1], bounty, "HUNTER_WIN")
        BountyService.cast_vote(experts[2], bounty, "HUNTER_WIN")

        for i, expert in enumerate(experts):
            expert.refresh_from_db()
            # ARBITRATION_SERVED awards 25 credit
            assert expert.credit_score == initial_scores[i] + 25

    @pytest.mark.django_db
    def test_not_in_arbitrating_status(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        experts = _create_arbitrators(3)
        # Bounty is DISPUTED, not ARBITRATING
        with pytest.raises(BountyError, match="当前还未进入仲裁投票阶段"):
            BountyService.cast_vote(experts[0], bounty, "HUNTER_WIN")

    @pytest.mark.django_db
    def test_vote_update_allowed(self):
        """Arbitrator can change their vote before finalization."""
        creator, hunter, bounty, arb, experts = self._setup_voting()

        BountyService.cast_vote(experts[0], bounty, "HUNTER_WIN")
        BountyService.cast_vote(experts[0], bounty, "CREATOR_WIN")

        vote = ArbitrationVote.objects.get(arbitration=arb, arbitrator=experts[0])
        assert vote.vote == "CREATOR_WIN"


class TestAppeal:
    """Tests for BountyService.appeal()."""

    def _setup_resolved_arbitration(self):
        creator, hunter, bounty, arb, experts = TestCastVote()._setup_voting()
        BountyService.cast_vote(experts[0], bounty, "CREATOR_WIN")
        BountyService.cast_vote(experts[1], bounty, "CREATOR_WIN")
        BountyService.cast_vote(experts[2], bounty, "CREATOR_WIN")
        arb.refresh_from_db()
        bounty.refresh_from_db()
        return creator, hunter, bounty, arb, experts

    @pytest.mark.django_db
    def test_charges_fee(self):
        creator, hunter, bounty, arb, experts = self._setup_resolved_arbitration()
        hunter_balance_before = hunter.balance

        arb = BountyService.appeal(hunter, bounty, "I disagree")

        hunter.refresh_from_db()
        assert arb.appeal_by_id == hunter.id
        assert arb.appeal_fee_paid is True
        assert hunter.balance == hunter_balance_before - Decimal("0.50")

    @pytest.mark.django_db
    def test_appeal_reason_appended(self):
        creator, hunter, bounty, arb, experts = self._setup_resolved_arbitration()

        arb = BountyService.appeal(hunter, bounty, "This is unfair")

        arb.refresh_from_db()
        assert "上诉理由" in arb.hunter_statement

    @pytest.mark.django_db
    def test_error_if_not_resolved(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()

        with pytest.raises(BountyError, match="当前案件尚未形成可上诉结果"):
            BountyService.appeal(creator, bounty, "Premature appeal")

    @pytest.mark.django_db
    def test_insufficient_balance_for_fee(self):
        creator, hunter, bounty, arb, experts = self._setup_resolved_arbitration()
        # Drain hunter's balance
        hunter.balance = Decimal("0.00")
        hunter.save(update_fields=["balance"])

        with pytest.raises(PaymentError, match="余额不足"):
            BountyService.appeal(hunter, bounty, "Can't pay")


class TestAdminFinalize:
    """Tests for BountyService.admin_finalize()."""

    @pytest.mark.django_db
    def test_admin_override(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        admin = make_user(role="ADMIN")

        arb = BountyService.admin_finalize(admin, bounty, "HUNTER_WIN", 1.0)

        bounty.refresh_from_db()
        arb.refresh_from_db()

        assert arb.admin_final_result == "HUNTER_WIN"
        assert arb.resolved_at is not None
        assert bounty.status == BountyStatus.COMPLETED

    @pytest.mark.django_db
    def test_non_admin_error(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        regular_user = make_user()

        with pytest.raises(BountyError, match="需要管理员权限"):
            BountyService.admin_finalize(regular_user, bounty, "HUNTER_WIN")

    @pytest.mark.django_db
    def test_admin_partial_split(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        admin = make_user(role="ADMIN")

        arb = BountyService.admin_finalize(admin, bounty, "PARTIAL", 0.4)

        hunter.refresh_from_db()
        creator.refresh_from_db()
        bounty.refresh_from_db()

        assert bounty.status == BountyStatus.COMPLETED
        assert hunter.balance == Decimal("9.00")  # initial 5.00 + 4.00 (40% of 10)

    @pytest.mark.django_db
    def test_admin_creator_win(self):
        creator, hunter, bounty, arb = _setup_disputed_bounty()
        admin = make_user(role="ADMIN")

        arb = BountyService.admin_finalize(admin, bounty, "CREATOR_WIN", 0.0)

        creator.refresh_from_db()
        bounty.refresh_from_db()

        assert bounty.status == BountyStatus.CANCELLED
        # Full refund to creator (from frozen to balance)
        assert creator.frozen_balance == Decimal("0.00")
        assert creator.balance == Decimal("50.00")  # original 50 - 10 escrow + 10 refund

    @pytest.mark.django_db
    def test_no_arbitration_case(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())
        admin = make_user(role="ADMIN")

        with pytest.raises(BountyError, match="当前案件不存在"):
            BountyService.admin_finalize(admin, bounty, "HUNTER_WIN")


# ===========================================================================
# 3. Reviews
# ===========================================================================


class TestAddReview:
    """Tests for BountyService.add_review()."""

    @pytest.mark.django_db
    def test_creator_reviews_hunter(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        review = BountyService.add_review(
            creator,
            bounty,
            quality_rating=5,
            communication_rating=4,
            responsiveness_rating=3,
            comment="Great work!",
        )

        assert review.pk is not None
        assert review.reviewer_id == creator.id
        assert review.reviewee_id == hunter.id
        assert review.quality_rating == 5
        assert review.communication_rating == 4
        assert review.responsiveness_rating == 3
        assert review.comment == "Great work!"

    @pytest.mark.django_db
    def test_hunter_reviews_creator(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        review = BountyService.add_review(
            hunter,
            bounty,
            quality_rating=4,
            communication_rating=4,
            responsiveness_rating=4,
        )

        assert review.reviewer_id == hunter.id
        assert review.reviewee_id == creator.id

    @pytest.mark.django_db
    def test_mutual_reviews(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        BountyService.add_review(creator, bounty, quality_rating=5, communication_rating=5, responsiveness_rating=5)
        BountyService.add_review(hunter, bounty, quality_rating=4, communication_rating=4, responsiveness_rating=4)

        assert BountyReview.objects.filter(bounty=bounty).count() == 2

    @pytest.mark.django_db
    def test_not_completed_error(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        # Bounty is IN_PROGRESS, not COMPLETED

        with pytest.raises(BountyError, match="只有已结束的悬赏才可互评"):
            BountyService.add_review(
                creator, bounty, quality_rating=5, communication_rating=5, responsiveness_rating=5
            )

    @pytest.mark.django_db
    def test_stranger_cannot_review(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        stranger = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        with pytest.raises(BountyError, match="只有交易双方可以互评"):
            BountyService.add_review(
                stranger, bounty, quality_rating=5, communication_rating=5, responsiveness_rating=5
            )

    @pytest.mark.django_db
    def test_rating_out_of_range(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        with pytest.raises(BountyError, match="评分须在 1 到 5 之间"):
            BountyService.add_review(
                creator, bounty, quality_rating=6, communication_rating=4, responsiveness_rating=3
            )

        with pytest.raises(BountyError, match="评分须在 1 到 5 之间"):
            BountyService.add_review(
                creator, bounty, quality_rating=5, communication_rating=0, responsiveness_rating=3
            )

    @pytest.mark.django_db
    def test_update_existing_review(self):
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user(balance=Decimal("0.00"))
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        _deliver_bounty(hunter, bounty)
        BountyService.approve_delivery(creator, bounty)
        bounty.refresh_from_db()

        r1 = BountyService.add_review(
            creator, bounty, quality_rating=3, communication_rating=3, responsiveness_rating=3
        )
        r2 = BountyService.add_review(
            creator, bounty, quality_rating=5, communication_rating=5, responsiveness_rating=5
        )

        assert r1.id == r2.id
        r2.refresh_from_db()
        assert r2.quality_rating == 5

    @pytest.mark.django_db
    def test_review_on_cancelled_bounty(self):
        """Reviews are allowed on cancelled bounties that had a hunter."""
        creator = make_user(balance=Decimal("50.00"))
        hunter = make_user()
        bounty, _ = _create_bounty_and_accept(creator, hunter)
        BountyService.cancel_bounty(creator, bounty)
        bounty.refresh_from_db()

        review = BountyService.add_review(
            creator, bounty, quality_rating=2, communication_rating=2, responsiveness_rating=2
        )
        assert review.pk is not None


# ===========================================================================
# 4. Comments
# ===========================================================================


class TestAddComment:
    """Tests for BountyService.add_comment()."""

    @pytest.mark.django_db
    def test_valid_comment(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        comment = BountyService.add_comment(creator, bounty, "This is a comment")

        assert comment.pk is not None
        assert comment.content == "This is a comment"
        assert comment.author_id == creator.id
        assert comment.bounty_id == bounty.id

    @pytest.mark.django_db
    def test_empty_content_error(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="评论内容不能为空"):
            BountyService.add_comment(creator, bounty, "")

    @pytest.mark.django_db
    def test_whitespace_only_error(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        with pytest.raises(BountyError, match="评论内容不能为空"):
            BountyService.add_comment(creator, bounty, "   \n\t  ")

    @pytest.mark.django_db
    def test_content_stripped(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        comment = BountyService.add_comment(creator, bounty, "  Hello world  ")
        assert comment.content == "Hello world"

    @pytest.mark.django_db
    def test_content_truncated_to_1000(self):
        creator = make_user(balance=Decimal("50.00"))
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        long_content = "x" * 1500
        comment = BountyService.add_comment(creator, bounty, long_content)
        assert len(comment.content) == 1000

    @pytest.mark.django_db
    def test_any_user_can_comment(self):
        creator = make_user(balance=Decimal("50.00"))
        other_user = make_user()
        bounty = BountyService.create_bounty(creator, _default_bounty_data())

        comment = BountyService.add_comment(other_user, bounty, "Interested!")
        assert comment.author_id == other_user.id


# ===========================================================================
# 5. Full lifecycle integration test
# ===========================================================================


class TestFullLifecycle:
    """End-to-end lifecycle scenarios."""

    @pytest.mark.django_db
    def test_happy_path_create_to_complete(self):
        """Creator posts bounty -> hunter applies -> accepted -> delivers -> approved."""
        creator = make_user(balance=Decimal("100.00"), credit_score=200)
        hunter = make_user(balance=Decimal("0.00"), credit_score=100)

        # Create
        bounty = BountyService.create_bounty(
            creator, _default_bounty_data(reward=20.00)
        )
        creator.refresh_from_db()
        assert creator.balance == Decimal("80.00")
        assert creator.frozen_balance == Decimal("20.00")

        # Apply
        app = BountyService.apply(bounty, hunter, "I can deliver this", 5)
        assert app.pk is not None

        # Accept
        bounty = BountyService.accept_application(creator, bounty, app.id)
        assert bounty.status == BountyStatus.IN_PROGRESS

        # Deliver
        deliverable = BountyService.submit_delivery(hunter, bounty, "Complete work")
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DELIVERED

        # Revision cycle
        bounty = BountyService.request_revision(creator, bounty, "Small fix needed")
        assert bounty.status == BountyStatus.REVISION

        deliverable2 = BountyService.submit_delivery(hunter, bounty, "Fixed version")
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DELIVERED
        assert deliverable2.revision_number == 2

        # Approve
        bounty = BountyService.approve_delivery(creator, bounty)
        creator.refresh_from_db()
        hunter.refresh_from_db()
        bounty.refresh_from_db()

        assert bounty.status == BountyStatus.COMPLETED
        assert creator.frozen_balance == Decimal("0.00")
        assert hunter.balance == Decimal("20.00")

        # Reviews
        BountyService.add_review(
            creator, bounty, quality_rating=5, communication_rating=5, responsiveness_rating=5
        )
        BountyService.add_review(
            hunter, bounty, quality_rating=4, communication_rating=4, responsiveness_rating=4
        )
        assert BountyReview.objects.filter(bounty=bounty).count() == 2

    @pytest.mark.django_db
    def test_dispute_to_arbitration_to_resolution(self):
        """Full dispute flow: dispute -> statements -> arbitration -> vote resolution."""
        creator = make_user(balance=Decimal("100.00"), credit_score=200)
        hunter = make_user(balance=Decimal("5.00"), credit_score=100)
        experts = _create_arbitrators(3, credit_score=600)

        # Setup: create, accept, deliver
        bounty, _ = _create_bounty_and_accept(creator, hunter, reward=20.00)
        _deliver_bounty(hunter, bounty)

        # Dispute
        arb = BountyService.create_dispute(creator, bounty, "Not satisfied")
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.DISPUTED

        # Submit statements
        BountyService.submit_statement(hunter, bounty, "I delivered everything")
        arb.refresh_from_db()
        assert arb.hunter_statement == "I delivered everything"

        # Expire cooling period and start arbitration
        arb.deadline = timezone.now() - timedelta(minutes=1)
        arb.save(update_fields=["deadline"])
        arb = BountyService.start_arbitration(creator, bounty)
        arb.arbitrators.set(experts)
        bounty.refresh_from_db()
        assert bounty.status == BountyStatus.ARBITRATING

        # Votes: creator wins
        BountyService.cast_vote(experts[0], bounty, "CREATOR_WIN")
        BountyService.cast_vote(experts[1], bounty, "CREATOR_WIN")
        BountyService.cast_vote(experts[2], bounty, "CREATOR_WIN")

        arb.refresh_from_db()
        bounty.refresh_from_db()
        assert arb.resolved_at is not None
        assert arb.result == "CREATOR_WIN"
        assert bounty.status == BountyStatus.CANCELLED

        # Escrow refunded to creator
        creator.refresh_from_db()
        assert creator.frozen_balance == Decimal("0.00")
        assert creator.balance == Decimal("100.00")  # full refund

        # Hunter appeals
        arb = BountyService.appeal(hunter, bounty, "This is unfair")
        assert arb.appeal_fee_paid is True
        hunter.refresh_from_db()
        assert hunter.balance == Decimal("4.50")  # 5.00 - 0.50 appeal fee

    @pytest.mark.django_db
    def test_admin_finalize_before_vote(self):
        """Admin finalizes a dispute directly without waiting for votes."""
        creator = make_user(balance=Decimal("100.00"), credit_score=200)
        hunter = make_user(balance=Decimal("0.00"), credit_score=100)
        admin = make_user(role="ADMIN", credit_score=200)

        bounty, _ = _create_bounty_and_accept(creator, hunter, reward=20.00)
        _deliver_bounty(hunter, bounty)

        arb = BountyService.create_dispute(creator, bounty, "Issue with delivery")
        bounty.refresh_from_db()

        # Admin steps in directly
        arb = BountyService.admin_finalize(admin, bounty, "PARTIAL", 0.5)

        bounty.refresh_from_db()
        hunter.refresh_from_db()
        creator.refresh_from_db()

        assert arb.admin_final_result == "PARTIAL"
        assert arb.resolved_at is not None
        assert bounty.status == BountyStatus.COMPLETED
        assert hunter.balance == Decimal("10.00")  # 50% of 20.00
        assert creator.frozen_balance == Decimal("0.00")
