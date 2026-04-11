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


# ===========================================================================
# Appeal → admin_finalize lifecycle
# ===========================================================================


def test_appeal_then_admin_finalize_completes_bounty():
    """After community arbitration settles and a party appeals,
    admin_finalize must record admin_final_result and restore
    bounty to the correct terminal status without moving funds again."""
    from apps.bounties.services import BountyService
    from apps.bounties.models import Bounty, Arbitration
    from django.utils import timezone
    import datetime

    creator = _create_user("appeal-creator@test.com", balance=Decimal("0.00"), frozen_balance=Decimal("10.00"))
    hunter = _create_user("appeal-hunter@test.com", balance=Decimal("10.00"))
    admin = _create_user("appeal-admin@test.com", role="ADMIN")

    bounty = Bounty.objects.create(
        title="Appeal Bounty",
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
        appeal_by=creator,
        appeal_fee_paid=True,
    )

    result_arb = BountyService.admin_finalize(admin, bounty, "HUNTER_WIN")
    assert result_arb.admin_final_result == "HUNTER_WIN"

    bounty.refresh_from_db()
    assert bounty.status == "COMPLETED"

    # Verify no fund movement — balances unchanged
    creator.refresh_from_db()
    hunter.refresh_from_db()
    assert creator.frozen_balance == Decimal("10.00")
    assert hunter.balance == Decimal("10.00")


def test_appeal_admin_finalize_cancelled_when_zero_ratio():
    """When original settlement gave hunter_ratio=0 (creator wins),
    admin_finalize should set bounty to CANCELLED."""
    from apps.bounties.services import BountyService
    from apps.bounties.models import Bounty, Arbitration
    from django.utils import timezone
    import datetime

    creator = _create_user("appeal-c2@test.com", balance=Decimal("10.00"))
    hunter = _create_user("appeal-h2@test.com", balance=Decimal("0.00"))
    admin = _create_user("appeal-a2@test.com", role="ADMIN")

    bounty = Bounty.objects.create(
        title="Appeal Bounty 2",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="DISPUTED",
    )

    Arbitration.objects.create(
        bounty=bounty,
        creator_statement="Creator's case",
        hunter_statement="Hunter's case",
        resolved_at=timezone.now(),
        result="CREATOR_WIN",
        hunter_ratio=Decimal("0.000"),
        appeal_by=hunter,
        appeal_fee_paid=True,
    )

    BountyService.admin_finalize(admin, bounty, "CREATOR_WIN")
    bounty.refresh_from_db()
    assert bounty.status == "CANCELLED"


# ===========================================================================
# start_arbitration rejects already-resolved appealed cases
# ===========================================================================


def test_start_arbitration_rejects_resolved_case():
    """start_arbitration must reject requests when resolved_at is set."""
    from apps.bounties.services import BountyService, BountyError
    from apps.bounties.models import Bounty, Arbitration, BountyApplication
    from django.utils import timezone
    import datetime

    creator = _create_user("start-arb-c@test.com", balance=Decimal("10.00"))
    hunter = _create_user("start-arb-h@test.com")

    bounty = Bounty.objects.create(
        title="Resolved Bounty",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="DISPUTED",
    )
    app = BountyApplication.objects.create(
        bounty=bounty, applicant=hunter, proposal="I can do it", estimated_days=1,
    )
    bounty.accepted_application = app
    bounty.save(update_fields=["accepted_application"])

    Arbitration.objects.create(
        bounty=bounty,
        creator_statement="Creator's case",
        hunter_statement="Hunter's case",
        resolved_at=timezone.now(),
        result="HUNTER_WIN",
        hunter_ratio=Decimal("1.000"),
    )

    with pytest.raises(BountyError, match="已有结果"):
        BountyService.start_arbitration(creator, bounty)


# ===========================================================================
# Workshop _get_optional_user ignores inactive user stale token
# ===========================================================================


def test_workshop_optional_user_ignores_inactive():
    """Workshop _get_optional_user should return None for inactive users."""
    from apps.workshop.api import _get_optional_user

    user = _create_user("workshop-inactive@test.com")
    token = AuthService.get_tokens_for_user(user)["access"]

    user.is_active = False
    user.save(update_fields=["is_active"])

    class FakeRequest:
        headers = {"Authorization": f"Bearer {token}"}

    result = _get_optional_user(FakeRequest())
    assert result is None


# ===========================================================================
# H3: GET bounty endpoints don't call process_automations
# ===========================================================================


def test_bounty_list_does_not_call_process_automations():
    """GET /api/bounties/ must not trigger process_automations side-effect."""
    from unittest.mock import patch

    client = Client()
    with patch("apps.bounties.services.BountyService.process_automations") as mock_pa:
        response = client.get("/api/bounties/")
        assert response.status_code == 200
        mock_pa.assert_not_called()


def test_bounty_detail_does_not_call_process_automations():
    """GET /api/bounties/{id} must not trigger process_automations."""
    from unittest.mock import patch
    from apps.bounties.models import Bounty
    from django.utils import timezone
    import datetime

    creator = _create_user("pa-detail-c@test.com", balance=Decimal("100.00"))
    bounty = Bounty.objects.create(
        title="PA Detail Bounty",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="OPEN",
    )

    client = Client()
    with patch("apps.bounties.services.BountyService.process_automations") as mock_pa:
        response = client.get(f"/api/bounties/{bounty.id}")
        assert response.status_code == 200
        mock_pa.assert_not_called()


# ===========================================================================
# Logout blacklist: blacklisted refresh token cannot be reused
# ===========================================================================


def test_blacklisted_refresh_token_cannot_refresh():
    """After logout (blacklist), the same refresh token must be rejected."""
    user = _create_user("logout-bl@test.com")
    tokens = AuthService.get_tokens_for_user(user)

    client = Client()
    # Logout — blacklist the refresh token
    response = client.post(
        "/api/auth/logout",
        data=json.dumps({"refresh": tokens["refresh"]}),
        content_type="application/json",
    )
    assert response.status_code == 200

    # Try to use the blacklisted refresh token
    response = client.post(
        "/api/auth/refresh",
        data=json.dumps({"refresh": tokens["refresh"]}),
        content_type="application/json",
    )
    assert response.status_code == 401


# ===========================================================================
# Appealed admin_finalize rejects contradictory result
# ===========================================================================


def test_admin_finalize_rejects_contradictory_result_on_appeal():
    """After community arbitration settled as HUNTER_WIN, admin cannot
    finalize with CREATOR_WIN — that would create inconsistent metadata
    since funds already moved per the original settlement."""
    from apps.bounties.services import BountyService, BountyError
    from apps.bounties.models import Bounty, Arbitration
    from django.utils import timezone
    import datetime

    creator = _create_user("contra-creator@test.com", balance=Decimal("0.00"), frozen_balance=Decimal("10.00"))
    hunter = _create_user("contra-hunter@test.com", balance=Decimal("10.00"))
    admin = _create_user("contra-admin@test.com", role="ADMIN")

    bounty = Bounty.objects.create(
        title="Contradictory Bounty",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="DISPUTED",
    )

    Arbitration.objects.create(
        bounty=bounty,
        creator_statement="Creator's case",
        hunter_statement="Hunter's case",
        resolved_at=timezone.now(),
        result="HUNTER_WIN",
        hunter_ratio=Decimal("1.000"),
        appeal_by=creator,
        appeal_fee_paid=True,
    )

    with pytest.raises(BountyError, match="无法改判"):
        BountyService.admin_finalize(admin, bounty, "CREATOR_WIN")

    # Verify bounty status unchanged (still DISPUTED, not incorrectly set)
    bounty.refresh_from_db()
    assert bounty.status == "DISPUTED"


def test_admin_finalize_rejects_contradictory_partial_ratio():
    """After community arbitration settled as PARTIAL with ratio 0.400,
    admin cannot finalize with a different ratio (e.g. 0.900).
    Funds were already distributed at the original ratio."""
    from apps.bounties.services import BountyService, BountyError
    from apps.bounties.models import Bounty, Arbitration
    from django.utils import timezone
    import datetime

    creator = _create_user("partial-c@test.com", balance=Decimal("0.00"), frozen_balance=Decimal("10.00"))
    hunter = _create_user("partial-h@test.com", balance=Decimal("4.00"))
    admin = _create_user("partial-admin@test.com", role="ADMIN")

    bounty = Bounty.objects.create(
        title="Partial Bounty",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="DISPUTED",
    )

    Arbitration.objects.create(
        bounty=bounty,
        creator_statement="Creator's case",
        hunter_statement="Hunter's case",
        resolved_at=timezone.now(),
        result="PARTIAL",
        hunter_ratio=Decimal("0.400"),
        appeal_by=creator,
        appeal_fee_paid=True,
    )

    with pytest.raises(BountyError, match="无法变更"):
        BountyService.admin_finalize(admin, bounty, "PARTIAL", hunter_ratio=0.9)

    bounty.refresh_from_db()
    assert bounty.status == "DISPUTED"


def test_admin_finalize_accepts_matching_partial_ratio():
    """After community arbitration settled as PARTIAL with ratio 0.400,
    admin can confirm by finalizing with the same ratio.
    Bounty should be restored to COMPLETED without moving funds."""
    from apps.bounties.services import BountyService
    from apps.bounties.models import Bounty, Arbitration
    from django.utils import timezone
    import datetime

    creator = _create_user("partial-ok-c@test.com", balance=Decimal("0.00"), frozen_balance=Decimal("6.00"))
    hunter = _create_user("partial-ok-h@test.com", balance=Decimal("4.00"))
    admin = _create_user("partial-ok-admin@test.com", role="ADMIN")

    bounty = Bounty.objects.create(
        title="Partial OK Bounty",
        description="Test",
        creator=creator,
        reward=Decimal("10.00"),
        bounty_type="GENERAL",
        deadline=timezone.now() + datetime.timedelta(days=7),
        status="DISPUTED",
    )

    Arbitration.objects.create(
        bounty=bounty,
        creator_statement="Creator's case",
        hunter_statement="Hunter's case",
        resolved_at=timezone.now(),
        result="PARTIAL",
        hunter_ratio=Decimal("0.400"),
        appeal_by=creator,
        appeal_fee_paid=True,
    )

    result_arb = BountyService.admin_finalize(admin, bounty, "PARTIAL", hunter_ratio=0.4)
    assert result_arb.admin_final_result == "PARTIAL"

    bounty.refresh_from_db()
    assert bounty.status == "COMPLETED"

    # Verify no fund movement
    creator.refresh_from_db()
    hunter.refresh_from_db()
    assert creator.frozen_balance == Decimal("6.00")
    assert hunter.balance == Decimal("4.00")


# ===========================================================================
# Workshop: inactive user stale token denied draft article access (API-level)
# ===========================================================================


def test_workshop_inactive_user_cannot_access_draft_article():
    """An inactive user's stale token must not grant access to their own
    unpublished draft article via the workshop GET endpoint."""
    from apps.workshop.models import Article

    author = _create_user("draft-author@test.com")
    token = AuthService.get_tokens_for_user(author)["access"]

    article = Article.objects.create(
        title="My Draft Article",
        content="This is a draft that should not be visible.",
        author=author,
        status="DRAFT",
    )

    # Deactivate user after creating draft and getting token
    author.is_active = False
    author.save(update_fields=["is_active"])

    client = Client()
    response = client.get(
        f"/api/workshop/{article.id}",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    # Should be 404 because _get_optional_user returns None for inactive,
    # so the user is treated as anonymous, and anonymous can't see drafts
    assert response.status_code == 404
