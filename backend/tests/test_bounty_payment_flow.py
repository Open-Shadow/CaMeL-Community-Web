from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bounties.models import BountyStatus
from apps.bounties.services import BountyService
from apps.payments.models import TransactionType
from apps.payments.services import PaymentsService

User = get_user_model()


def create_user(email: str, *, balance: Decimal = Decimal("0.00"), credit_score: int = 100):
    user = User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        display_name=email.split("@")[0],
        credit_score=credit_score,
        balance=balance,
    )
    user.level = "CRAFTSMAN" if credit_score >= 100 else "SEED"
    user.save(update_fields=["level"])
    return user


@pytest.mark.django_db
def test_paid_skill_call_updates_balances_and_transactions():
    creator = create_user("creator@example.com", balance=Decimal("0.00"), credit_score=500)
    caller = create_user("caller@example.com", balance=Decimal("10.00"), credit_score=100)

    result = PaymentsService.charge_skill_call(
        caller,
        creator,
        price=Decimal("2.00"),
        reference_id="skill:1:test-call",
    )

    creator.refresh_from_db()
    caller.refresh_from_db()

    assert result["charged_amount"] == Decimal("1.90")
    assert caller.balance == Decimal("8.10")
    assert creator.balance == Decimal("1.61")
    assert caller.transactions.filter(transaction_type=TransactionType.SKILL_PURCHASE).count() == 1
    assert creator.transactions.filter(transaction_type=TransactionType.SKILL_INCOME).count() == 1


@pytest.mark.django_db
def test_bounty_service_happy_path_releases_escrow_and_rewards_hunter():
    creator = create_user("bounty-creator@example.com", balance=Decimal("50.00"), credit_score=120)
    hunter = create_user("bounty-hunter@example.com", balance=Decimal("0.00"), credit_score=120)

    bounty = BountyService.create_bounty(
        creator,
        {
            "title": "Need a prompt engineer",
            "description": "Build a reusable prompt workflow.",
            "bounty_type": "SKILL_CUSTOM",
            "reward": 10,
            "deadline": (timezone.now() + timedelta(days=3)).isoformat(),
        },
    )
    creator.refresh_from_db()
    assert creator.balance == Decimal("40.00")
    assert creator.frozen_balance == Decimal("10.00")

    application = BountyService.apply(bounty, hunter, "I can do this", 2)
    bounty = BountyService.accept_application(creator, bounty, application.id)
    BountyService.submit_delivery(hunter, bounty, "Delivered the full workflow")
    bounty.refresh_from_db()
    assert bounty.status == BountyStatus.DELIVERED

    BountyService.approve_delivery(creator, bounty)

    creator.refresh_from_db()
    hunter.refresh_from_db()
    bounty.refresh_from_db()

    assert bounty.status == BountyStatus.COMPLETED
    assert creator.frozen_balance == Decimal("0.00")
    assert hunter.balance == Decimal("10.00")
    assert hunter.transactions.filter(transaction_type=TransactionType.BOUNTY_INCOME).count() == 1


@pytest.mark.django_db
def test_arbitration_partial_vote_splits_escrow():
    creator = create_user("arb-creator@example.com", balance=Decimal("30.00"), credit_score=120)
    hunter = create_user("arb-hunter@example.com", balance=Decimal("0.00"), credit_score=120)
    experts = [
        create_user(f"expert{i}@example.com", balance=Decimal("0.00"), credit_score=600)
        for i in range(3)
    ]

    bounty = BountyService.create_bounty(
        creator,
        {
            "title": "Need arbitration",
            "description": "There will be a dispute.",
            "bounty_type": "GENERAL",
            "reward": 12,
            "deadline": (timezone.now() + timedelta(days=3)).isoformat(),
        },
    )
    application = BountyService.apply(bounty, hunter, "Taking this one", 2)
    bounty = BountyService.accept_application(creator, bounty, application.id)
    BountyService.submit_delivery(hunter, bounty, "Partial delivery")
    arbitration = BountyService.create_dispute(creator, bounty, "Delivery is incomplete")
    arbitration.deadline = timezone.now() - timedelta(minutes=1)
    arbitration.save(update_fields=["deadline"])

    arbitration = BountyService.start_arbitration(creator, bounty)
    assert arbitration.arbitrators.count() == 3

    for expert in experts:
        arbitration.arbitrators.add(expert)

    BountyService.cast_vote(experts[0], bounty, "PARTIAL", 0.5)
    BountyService.cast_vote(experts[1], bounty, "PARTIAL", 0.5)
    BountyService.cast_vote(experts[2], bounty, "PARTIAL", 0.5)

    creator.refresh_from_db()
    hunter.refresh_from_db()
    bounty.refresh_from_db()

    assert bounty.status == BountyStatus.COMPLETED
    assert creator.balance == Decimal("24.00")
    assert creator.frozen_balance == Decimal("0.00")
    assert hunter.balance == Decimal("6.00")
