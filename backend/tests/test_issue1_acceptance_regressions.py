import json
from datetime import timedelta
from decimal import Decimal

import pytest
from allauth.account.models import EmailAddress
from django.core.cache import cache
from django.test import Client as DjangoClient
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Invitation, User, UserRole
from apps.bounties.models import Arbitration, Bounty, BountyApplication
from apps.workshop.models import Article, ArticleDifficulty, ArticleStatus, ArticleType
from apps.workshop.services import TipService


@pytest.fixture
def client():
    return DjangoClient()


def _jwt_header(user) -> dict:
    token = str(AccessToken.for_user(user))
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _mark_email_verified(user: User) -> None:
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={"primary": True, "verified": True},
    )


@pytest.mark.django_db
def test_register_requires_email_verification_before_login(client):
    email = "issue1-auth@example.test"
    password = "StrongPass123!"

    register_resp = client.post(
        "/api/auth/register",
        data=json.dumps(
            {
                "email": email,
                "password": password,
                "display_name": "Issue1 Auth",
            }
        ),
        content_type="application/json",
    )
    assert register_resp.status_code == 201, register_resp.content
    register_body = register_resp.json()
    assert "message" in register_body
    assert "access" not in register_body
    assert "refresh" not in register_body

    login_resp = client.post(
        "/api/auth/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )
    assert login_resp.status_code == 401
    assert "验证" in login_resp.json()["message"]

    user = User.objects.get(email=email)
    _mark_email_verified(user)

    verified_login_resp = client.post(
        "/api/auth/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )
    assert verified_login_resp.status_code == 200, verified_login_resp.content
    verified_login_body = verified_login_resp.json()
    assert "access" in verified_login_body
    assert "refresh" in verified_login_body


@pytest.mark.django_db
def test_legacy_invitation_endpoints_and_invite_registration_work(client):
    inviter = User.objects.create_user(
        username="inviter",
        email="inviter@example.test",
        password="pw",
        display_name="Inviter",
    )

    generate_resp = client.post(
        "/api/invitations/generate",
        **_jwt_header(inviter),
    )
    assert generate_resp.status_code == 200, generate_resp.content
    code = generate_resp.json()["code"]

    stats_resp = client.get(
        "/api/invitations/stats",
        **_jwt_header(inviter),
    )
    assert stats_resp.status_code == 200, stats_resp.content
    stats_body = stats_resp.json()
    assert stats_body["total_codes"] == 1
    assert stats_body["used_codes"] == 0

    list_resp = client.get(
        "/api/invitations/list",
        **_jwt_header(inviter),
    )
    assert list_resp.status_code == 200, list_resp.content
    invitations = list_resp.json()
    assert len(invitations) == 1
    assert invitations[0]["code"] == code

    register_resp = client.post(
        "/api/auth/register",
        data=json.dumps(
            {
                "email": "invitee@example.test",
                "password": "InvitePass123!",
                "display_name": "Invitee",
                "invite_code": code,
            }
        ),
        content_type="application/json",
    )
    assert register_resp.status_code == 201, register_resp.content
    invitee = User.objects.get(email="invitee@example.test")
    assert invitee.invited_by_id == inviter.id

    invitation = Invitation.objects.get(code=code)
    assert invitation.used_by_id == invitee.id

    used_list_resp = client.get(
        "/api/invitations/list",
        **_jwt_header(inviter),
    )
    assert used_list_resp.status_code == 200
    used_invitations = used_list_resp.json()
    assert used_invitations[0]["used_by_name"] == "Invitee"


@pytest.mark.django_db
def test_openapi_schema_and_admin_finalize_no_longer_500(client):
    openapi_resp = client.get("/api/openapi.json")
    assert openapi_resp.status_code == 200, openapi_resp.content
    assert "arbitration/admin-finalize" in openapi_resp.content.decode()

    admin_user = User.objects.create_user(
        username="issue1admin",
        email="issue1admin@example.test",
        password="pw",
        role=UserRole.ADMIN,
    )
    finalize_resp = client.post(
        "/api/bounties/999999/arbitration/admin-finalize",
        data=json.dumps({"result": "CREATOR_WIN", "hunter_ratio": 0}),
        content_type="application/json",
        **_jwt_header(admin_user),
    )
    assert finalize_resp.status_code == 404


@pytest.mark.django_db
def test_tip_leaderboard_cache_is_invalidated_after_new_tip(client):
    cache.set(
        "tip_leaderboard",
        [{"rank": 1, "user_id": 999, "display_name": "stale", "avatar_url": "", "total_tips": 99.0}],
        timeout=3600,
    )

    author = User.objects.create_user(
        username="tipauthor",
        email="tipauthor@example.test",
        password="pw",
        display_name="Tip Author",
    )
    tipper = User.objects.create_user(
        username="tipper",
        email="tipper@example.test",
        password="pw",
        display_name="Tipper",
        balance=Decimal("10.00"),
    )
    article = Article.objects.create(
        author=author,
        title="Tip Cache Test",
        slug="tip-cache-test",
        content="<p>content</p>",
        difficulty=ArticleDifficulty.BEGINNER,
        article_type=ArticleType.TUTORIAL,
        status=ArticleStatus.PUBLISHED,
        published_at=timezone.now(),
    )

    TipService.send_tip(tipper, article.id, Decimal("0.50"))

    leaderboard = TipService.get_leaderboard()
    assert leaderboard[0]["user_id"] == author.id
    assert leaderboard[0]["total_tips"] == 0.5


@pytest.mark.django_db
def test_bounty_creator_can_reject_application(client):
    creator = User.objects.create_user(
        username="bountycreator",
        email="bountycreator@example.test",
        password="pw",
        display_name="Bounty Creator",
    )
    applicant = User.objects.create_user(
        username="bountyapplicant",
        email="bountyapplicant@example.test",
        password="pw",
        display_name="Bounty Applicant",
    )
    bounty = Bounty.objects.create(
        creator=creator,
        title="Reject Application Bounty",
        description="Test rejecting applications",
        bounty_type="GENERAL",
        max_applicants=3,
        workload_estimate="ONE_DAY",
        reward=Decimal("1.00"),
        deadline=timezone.now() + timedelta(days=7),
    )
    application = BountyApplication.objects.create(
        bounty=bounty,
        applicant=applicant,
        proposal="please accept",
        estimated_days=2,
    )

    resp = client.post(
        f"/api/bounties/{bounty.id}/reject/{application.id}",
        **_jwt_header(creator),
    )

    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["applications"] == []
    assert any("已拒绝" in comment["content"] for comment in body["comments"])
    assert not BountyApplication.objects.filter(id=application.id).exists()


@pytest.mark.django_db
def test_admin_finalize_hunter_win_defaults_to_full_payout(client):
    creator = User.objects.create_user(
        username="arbcreator",
        email="arbcreator@example.test",
        password="pw",
        display_name="Arb Creator",
        frozen_balance=Decimal("1.00"),
    )
    hunter = User.objects.create_user(
        username="arbhunter",
        email="arbhunter@example.test",
        password="pw",
        display_name="Arb Hunter",
        balance=Decimal("0.00"),
    )
    admin_user = User.objects.create_user(
        username="arbadmin",
        email="arbadmin@example.test",
        password="pw",
        role=UserRole.ADMIN,
    )
    bounty = Bounty.objects.create(
        creator=creator,
        title="Admin Finalize Ratio Test",
        description="Test admin finalize default ratio",
        bounty_type="GENERAL",
        max_applicants=1,
        workload_estimate="ONE_DAY",
        reward=Decimal("1.00"),
        deadline=timezone.now() + timedelta(days=7),
    )
    application = BountyApplication.objects.create(
        bounty=bounty,
        applicant=hunter,
        proposal="hunter proposal",
        estimated_days=1,
    )
    bounty.accepted_application = application
    bounty.status = "ARBITRATING"
    bounty.save(update_fields=["accepted_application", "status"])
    Arbitration.objects.create(bounty=bounty)

    resp = client.post(
        f"/api/bounties/{bounty.id}/arbitration/admin-finalize",
        data=json.dumps({"result": "HUNTER_WIN"}),
        content_type="application/json",
        **_jwt_header(admin_user),
    )

    assert resp.status_code == 200, resp.content
    bounty.refresh_from_db()
    creator.refresh_from_db()
    hunter.refresh_from_db()
    arbitration = bounty.arbitration
    assert bounty.status == "COMPLETED"
    assert arbitration.result == "HUNTER_WIN"
    assert float(arbitration.hunter_ratio) == 1.0
    assert creator.frozen_balance == Decimal("0.00")
    assert hunter.balance == Decimal("1.00")
