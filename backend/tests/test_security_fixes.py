"""Tests for security and correctness fixes (RLCR Round 0).

Covers:
  - B1: Direct deposit rejection
  - B7: AuthBearer checks is_active
  - B8: Refresh token checks is_active
  - M3: Registration generates unique username
  - B3: Invitation reward uses Decimal
  - H6: Platform fee transaction recorded for skill calls
  - B6: Arbitration idempotency guard
  - H5: Bounty detail hides sensitive data from non-participants
"""
import json
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import AuthService

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(email="user@test.com", password="StrongPass123!", **kwargs):
    defaults = {"display_name": email.split("@")[0]}
    defaults.update(kwargs)
    return User.objects.create_user(
        username=f"u_{email.replace('@', '_').replace('.', '_')}",
        email=email,
        password=password,
        **defaults,
    )


def _auth_header(user):
    token = AuthService.get_tokens_for_user(user)["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ===========================================================================
# B1: Direct deposit rejection
# ===========================================================================


def test_direct_deposit_rejected():
    user = _create_user("depositor@test.com")
    client = Client()
    response = client.post(
        "/api/payments/deposits",
        data=json.dumps({"amount": "10.00"}),
        content_type="application/json",
        **_auth_header(user),
    )
    assert response.status_code == 400
    assert "Stripe" in response.json().get("message", "")


# ===========================================================================
# B7: AuthBearer blocks inactive users
# ===========================================================================


def test_auth_bearer_blocks_inactive_user():
    user = _create_user("inactive@test.com")
    header = _auth_header(user)  # get token while active
    user.is_active = False
    user.save(update_fields=["is_active"])

    client = Client()
    response = client.get("/api/auth/me", **header)
    assert response.status_code == 401


# ===========================================================================
# B8: Refresh token blocks inactive users
# ===========================================================================


def test_refresh_token_blocks_inactive_user():
    user = _create_user("refresh-inactive@test.com")
    tokens = AuthService.get_tokens_for_user(user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    client = Client()
    response = client.post(
        "/api/auth/refresh",
        data=json.dumps({"refresh": tokens["refresh"]}),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "停用" in response.json()["message"]


def test_refresh_token_works_for_active_user():
    user = _create_user("refresh-active@test.com")
    tokens = AuthService.get_tokens_for_user(user)

    client = Client()
    response = client.post(
        "/api/auth/refresh",
        data=json.dumps({"refresh": tokens["refresh"]}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert "access" in response.json()


# ===========================================================================
# M3: Registration generates unique (non-email) username
# ===========================================================================


def test_register_generates_unique_username():
    client = Client()
    response = client.post(
        "/api/auth/register",
        data=json.dumps({
            "email": "unique-username@test.com",
            "password": "StrongPass123!",
        }),
        content_type="application/json",
    )
    assert response.status_code == 201
    user = User.objects.get(email="unique-username@test.com")
    assert user.username.startswith("user_")
    assert "@" not in user.username


# ===========================================================================
# B3: Invitation first-deposit reward uses Decimal
# ===========================================================================


def test_invitation_first_deposit_reward_uses_decimal():
    """The first-deposit invitation reward should use Decimal('0.50'), not float."""
    from apps.accounts.tasks import check_first_deposit_reward
    from apps.accounts.models import Invitation

    inviter = _create_user("inviter@test.com", balance=Decimal("10.00"))
    invitee = _create_user("invitee@test.com")

    Invitation.objects.create(
        inviter=inviter,
        code="TESTCODE01",
        used_by=invitee,
        first_deposit_rewarded=False,
    )

    check_first_deposit_reward(invitee.id)
    inviter.refresh_from_db()
    assert isinstance(inviter.balance, Decimal)
    assert inviter.balance == Decimal("10.50")


# ===========================================================================
# H6: Platform fee transaction for skill calls
# ===========================================================================


def test_skill_call_creates_platform_fee_transaction():
    from apps.payments.services import PaymentsService
    from apps.payments.models import TransactionType

    caller = _create_user("caller@test.com", balance=Decimal("100.00"))
    creator = _create_user("creator@test.com")

    result = PaymentsService.charge_skill_call(
        caller, creator,
        price=Decimal("1.00"),
        reference_id="skill:1:call:1",
    )
    assert result["platform_fee"] > 0

    fee_tx = caller.transactions.filter(
        transaction_type=TransactionType.PLATFORM_FEE,
    ).first()
    assert fee_tx is not None
    assert fee_tx.amount < 0


# ===========================================================================
# H5: Bounty detail hides sensitive data from non-participants
# ===========================================================================


def test_bounty_detail_hides_applications_for_anonymous():
    from apps.bounties.api import _detail_out
    from apps.bounties.models import Bounty
    from django.utils import timezone
    import datetime

    creator = _create_user("bounty-creator@test.com", balance=Decimal("100.00"))
    bounty = Bounty.objects.create(
        title="Test Bounty",
        description="Test description",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="OPEN",
    )

    detail = _detail_out(bounty, viewer=None)
    assert detail["applications"] == []
    assert detail["arbitration"] is None


def test_bounty_detail_shows_data_for_creator():
    from apps.bounties.api import _detail_out
    from apps.bounties.models import Bounty
    from django.utils import timezone
    import datetime

    creator = _create_user("bounty-creator2@test.com", balance=Decimal("100.00"))
    bounty = Bounty.objects.create(
        title="Test Bounty 2",
        description="Test description",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="OPEN",
    )

    detail = _detail_out(bounty, viewer=creator)
    assert isinstance(detail["applications"], list)


# ===========================================================================
# B6: Arbitration idempotency — resolved_at alone should block re-settlement
# ===========================================================================


def test_arbitration_resolved_at_blocks_re_settlement():
    from apps.bounties.services import BountyService
    from apps.bounties.models import Bounty, Arbitration
    from django.utils import timezone
    import datetime

    creator = _create_user("arb-creator@test.com", balance=Decimal("0.00"), frozen_balance=Decimal("10.00"))
    hunter = _create_user("arb-hunter@test.com")

    bounty = Bounty.objects.create(
        title="Arb Bounty",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="DISPUTED",
    )

    arb = Arbitration.objects.create(
        bounty=bounty,
        creator_statement="Creator's case",
        hunter_statement="Hunter's case",
        resolved_at=timezone.now(),
        result="HUNTER_WIN",
        hunter_ratio=Decimal("1.000"),
    )

    # _apply_arbitration_result should no-op since resolved_at is set
    BountyService._apply_arbitration_result(arb, "HUNTER_WIN", Decimal("1.000"))
    creator.refresh_from_db()
    assert creator.frozen_balance == Decimal("10.00")
