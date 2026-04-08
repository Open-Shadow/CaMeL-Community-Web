import json
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import AuthService
from apps.skills.models import SkillStatus
from apps.skills.services import SkillService


pytestmark = pytest.mark.django_db


def _create_user(email: str, *, role: str = "USER") -> User:
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        display_name=email.split("@")[0],
        balance=Decimal("100.00"),
        credit_score=100,
        role=role,
    )


def _auth_client(user: User) -> Client:
    client = Client()
    token = AuthService.get_tokens_for_user(user)["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


def _create_pending_skill(creator: User):
    skill = SkillService.create(
        creator,
        {
            "name": "Admin Review Skill",
            "description": "Skill used for moderator review api tests.",
            "system_prompt": "You are a helper for admin review endpoint tests.",
            "category": "AGENT",
            "tags": ["admin", "review"],
            "pricing_model": "FREE",
            "price_per_use": None,
        },
    )
    submitted = SkillService.submit_for_review(skill)
    assert submitted.status == SkillStatus.PENDING_REVIEW
    return submitted


def test_moderator_can_list_and_approve_pending_skill():
    creator = _create_user("creator-admin-review@example.com")
    moderator = _create_user("moderator-admin-review@example.com", role="MODERATOR")
    skill = _create_pending_skill(creator)

    moderator_client = _auth_client(moderator)

    queue_response = moderator_client.get("/api/admin/skills/review-queue", {"status": "pending"})
    assert queue_response.status_code == 200, queue_response.content.decode()
    payload = queue_response.json()
    assert payload["total"] >= 1
    assert any(item["id"] == skill.id for item in payload["items"])

    approve_response = moderator_client.post(
        f"/api/admin/skills/{skill.id}/review",
        data=json.dumps({"action": "APPROVE"}),
        content_type="application/json",
    )
    assert approve_response.status_code == 200, approve_response.content.decode()
    assert approve_response.json()["status"] == SkillStatus.APPROVED


def test_reject_requires_reason():
    creator = _create_user("creator-admin-reject@example.com")
    moderator = _create_user("moderator-admin-reject@example.com", role="MODERATOR")
    skill = _create_pending_skill(creator)

    moderator_client = _auth_client(moderator)
    reject_response = moderator_client.post(
        f"/api/admin/skills/{skill.id}/review",
        data=json.dumps({"action": "REJECT", "reason": ""}),
        content_type="application/json",
    )
    assert reject_response.status_code == 400
    assert "拒绝时请填写原因" in reject_response.json()["message"]


def test_cannot_feature_skill_before_approval():
    creator = _create_user("creator-admin-feature-pending@example.com")
    moderator = _create_user("moderator-admin-feature-pending@example.com", role="MODERATOR")
    skill = _create_pending_skill(creator)

    moderator_client = _auth_client(moderator)
    response = moderator_client.post(
        f"/api/admin/skills/{skill.id}/featured",
        data=json.dumps({"is_featured": True}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "已上架" in response.json()["message"]


def test_regular_user_cannot_access_review_queue():
    creator = _create_user("creator-admin-forbidden@example.com")
    _create_pending_skill(creator)
    regular = _create_user("regular-admin-forbidden@example.com", role="USER")

    regular_client = _auth_client(regular)
    response = regular_client.get("/api/admin/skills/review-queue")
    assert response.status_code == 403
