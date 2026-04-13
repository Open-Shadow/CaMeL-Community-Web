import json
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import CamelUser as User
from apps.accounts.services import AuthService
from apps.skills.models import Skill, SkillStatus
from apps.skills.services import SkillService


pytestmark = pytest.mark.django_db


def _create_user(email: str, *, balance: Decimal = Decimal("0.00")) -> User:
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        display_name=email.split("@")[0],
        balance=balance,
        credit_score=100,
    )


def _auth_client(user: User) -> Client:
    client = Client()
    token = AuthService.get_tokens_for_user(user)["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


def test_skill_create_submit_call_review_flow():
    creator = _create_user("creator-flow@example.com")
    caller = _create_user("caller-flow@example.com", balance=Decimal("20.00"))
    moderator = _create_user("moderator-flow@example.com")
    moderator.role = "MODERATOR"
    moderator.save(update_fields=["role"])

    creator_client = _auth_client(creator)
    caller_client = _auth_client(caller)
    moderator_client = _auth_client(moderator)

    payload = {
        "name": "Flow Skill",
        "description": "A valid skill description for api flow test",
        "system_prompt": "You are a helpful assistant for integration flow testing.",
        "user_prompt_template": "",
        "output_format": "text",
        "example_input": "hello",
        "example_output": "world",
        "category": "CODE_DEV",
        "tags": ["flow", "api"],
        "pricing_model": "FREE",
        "price_per_use": None,
    }

    create_response = creator_client.post(
        "/api/skills/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert create_response.status_code == 201, create_response.content.decode()
    created = create_response.json()
    assert created["name"] == payload["name"]
    assert created["status"] == "DRAFT"
    assert isinstance(created["avg_rating"], float)
    assert created["creator_name"] == creator.display_name
    assert created["created_at"]
    assert created["updated_at"]

    skill_id = created["id"]
    submit_response = creator_client.post(f"/api/skills/{skill_id}/submit")
    assert submit_response.status_code == 200, submit_response.content.decode()
    submitted = submit_response.json()
    assert submitted["status"] == SkillStatus.PENDING_REVIEW

    review_response = moderator_client.post(
        f"/api/admin/skills/{skill_id}/review",
        data=json.dumps({"action": "APPROVE", "reason": ""}),
        content_type="application/json",
    )
    assert review_response.status_code == 200, review_response.content.decode()
    assert review_response.json()["status"] == SkillStatus.APPROVED

    call_response = caller_client.post(
        f"/api/skills/{skill_id}/call",
        data=json.dumps({"input_text": "run once"}),
        content_type="application/json",
    )
    assert call_response.status_code == 200, call_response.content.decode()
    call_payload = call_response.json()
    assert "output_text" in call_payload
    assert "amount_charged" in call_payload

    review_response = caller_client.post(
        f"/api/skills/{skill_id}/reviews",
        data=json.dumps({"rating": 5, "comment": "works great", "tags": ["helpful"]}),
        content_type="application/json",
    )
    assert review_response.status_code == 201, review_response.content.decode()
    review_payload = review_response.json()
    assert review_payload["rating"] == 5
    assert review_payload["reviewer_name"] == caller.display_name

    list_response = caller_client.get(f"/api/skills/{skill_id}/reviews")
    assert list_response.status_code == 200
    reviews = list_response.json()
    assert len(reviews) == 1
    assert reviews[0]["comment"] == "works great"


def test_skill_usage_preference_api_flow():
    creator = _create_user("creator-pref@example.com")
    user = _create_user("user-pref@example.com")
    client = _auth_client(user)

    skill = SkillService.create(
        creator,
        {
            "name": "Preference Skill",
            "description": "Description for preference flow validation",
            "system_prompt": "You are a versioned assistant for preference testing.",
            "user_prompt_template": "",
            "output_format": "text",
            "example_input": "",
            "example_output": "",
            "category": "AGENT",
            "tags": ["pref"],
            "pricing_model": "FREE",
            "price_per_use": None,
        },
    )
    skill.status = SkillStatus.APPROVED
    skill.save(update_fields=["status"])

    get_response = client.get(f"/api/skills/{skill.id}/usage-preference")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["auto_follow_latest"] is True
    assert get_payload["locked_version"] is None

    update_response = client.post(
        f"/api/skills/{skill.id}/usage-preference",
        data=json.dumps({"locked_version": 1, "auto_follow_latest": False}),
        content_type="application/json",
    )
    assert update_response.status_code == 200, update_response.content.decode()
    updated_payload = update_response.json()
    assert updated_payload["auto_follow_latest"] is False
    assert updated_payload["locked_version"] == 1

    skill_obj = Skill.objects.get(id=skill.id)
    assert skill_obj.current_version == 1


def test_owner_can_archive_restore_and_delete_skill():
    owner = _create_user("owner-ops@example.com")
    moderator = _create_user("moderator-ops@example.com")
    moderator.role = "MODERATOR"
    moderator.save(update_fields=["role"])
    client = _auth_client(owner)
    moderator_client = _auth_client(moderator)

    create_response = client.post(
        "/api/skills/",
        data=json.dumps(
            {
                "name": "Owner Ops Skill",
                "description": "A skill used to verify owner management actions",
                "system_prompt": "You are a helper for owner operations testing.",
                "category": "CODE_DEV",
                "tags": ["ops"],
                "pricing_model": "FREE",
                "price_per_use": None,
            }
        ),
        content_type="application/json",
    )
    assert create_response.status_code == 201, create_response.content.decode()
    skill_id = create_response.json()["id"]

    submit_response = client.post(f"/api/skills/{skill_id}/submit")
    assert submit_response.status_code == 200, submit_response.content.decode()
    assert submit_response.json()["status"] == SkillStatus.PENDING_REVIEW

    review_response = moderator_client.post(
        f"/api/admin/skills/{skill_id}/review",
        data=json.dumps({"action": "APPROVE"}),
        content_type="application/json",
    )
    assert review_response.status_code == 200, review_response.content.decode()
    assert review_response.json()["status"] == SkillStatus.APPROVED

    archive_response = client.post(f"/api/skills/{skill_id}/archive")
    assert archive_response.status_code == 200, archive_response.content.decode()
    assert archive_response.json()["status"] == SkillStatus.ARCHIVED

    restore_response = client.post(f"/api/skills/{skill_id}/restore")
    assert restore_response.status_code == 200, restore_response.content.decode()
    assert restore_response.json()["status"] == SkillStatus.DRAFT

    delete_response = client.delete(f"/api/skills/{skill_id}")
    assert delete_response.status_code == 200, delete_response.content.decode()
    assert delete_response.json()["message"] == "Skill 已删除"
    assert Skill.objects.filter(id=skill_id).count() == 0


def test_non_owner_cannot_delete_skill():
    owner = _create_user("owner-delete@example.com")
    other = _create_user("other-delete@example.com")

    skill = SkillService.create(
        owner,
        {
            "name": "Ownership Skill",
            "description": "Verify non-owner should not be able to delete this skill",
            "system_prompt": "You are an ownership verification helper.",
            "category": "AGENT",
            "tags": ["ownership"],
            "pricing_model": "FREE",
            "price_per_use": None,
        },
    )

    other_client = _auth_client(other)
    response = other_client.delete(f"/api/skills/{skill.id}")
    assert response.status_code == 404
    assert Skill.objects.filter(id=skill.id).exists()
