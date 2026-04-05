from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bounties.services import BountyService

User = get_user_model()


def create_user(email: str, *, role: str = "USER", balance: Decimal = Decimal("0.00"), credit_score: int = 120):
    user = User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        display_name=email.split("@")[0],
        role=role,
        balance=balance,
        credit_score=credit_score,
    )
    user.level = "EXPERT" if credit_score >= 500 else "CRAFTSMAN"
    user.save(update_fields=["level"])
    return user


@pytest.mark.django_db
def test_completed_bounty_supports_mutual_reviews():
    creator = create_user("review-creator@example.com", balance=Decimal("20.00"))
    hunter = create_user("review-hunter@example.com")

    bounty = BountyService.create_bounty(
        creator,
        {
            "title": "Review target",
            "description": "Need final review flow",
            "bounty_type": "GENERAL",
            "reward": 5,
            "deadline": (timezone.now() + timedelta(days=2)).isoformat(),
        },
    )
    application = BountyService.apply(bounty, hunter, "I can deliver", 1)
    bounty = BountyService.accept_application(creator, bounty, application.id)
    BountyService.submit_delivery(hunter, bounty, "Final deliverable")
    BountyService.approve_delivery(creator, bounty)
    bounty.refresh_from_db()

    first = BountyService.add_review(
        creator,
        bounty,
        quality_rating=5,
        communication_rating=4,
        responsiveness_rating=5,
        comment="交付稳定",
    )
    second = BountyService.add_review(
        hunter,
        bounty,
        quality_rating=5,
        communication_rating=5,
        responsiveness_rating=4,
        comment="需求清晰",
    )

    assert first.reviewee_id == hunter.id
    assert second.reviewee_id == creator.id
    assert bounty.reviews.count() == 2


@pytest.mark.django_db
def test_active_disputes_only_return_disputed_or_arbitrating_cases():
    moderator = create_user("moderator@example.com", role="MODERATOR", credit_score=800)
    creator = create_user("dispute-creator@example.com", balance=Decimal("20.00"))
    hunter = create_user("dispute-hunter@example.com")

    bounty = BountyService.create_bounty(
        creator,
        {
            "title": "Need arbitration listing",
            "description": "List only active dispute cases",
            "bounty_type": "GENERAL",
            "reward": 5,
            "deadline": (timezone.now() + timedelta(days=2)).isoformat(),
        },
    )
    application = BountyService.apply(bounty, hunter, "I can deliver", 1)
    bounty = BountyService.accept_application(creator, bounty, application.id)
    BountyService.submit_delivery(hunter, bounty, "Partial delivery")
    BountyService.create_dispute(creator, bounty, "Need arbitration")

    disputes = list(BountyService.list_active_disputes())

    assert disputes
    assert disputes[0].id == bounty.id
    assert disputes[0].status in {"DISPUTED", "ARBITRATING"}
    assert moderator.role == "MODERATOR"
