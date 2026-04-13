import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import CamelUser as User
from apps.accounts.services import AuthService


pytestmark = pytest.mark.django_db


def _create_user(email: str, *, balance: Decimal, credit_score: int = 120) -> User:
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        display_name=email.split("@")[0],
        balance=balance,
        credit_score=credit_score,
    )


def _auth_client(user: User) -> Client:
    client = Client()
    token = AuthService.get_tokens_for_user(user)["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


def test_bounty_api_happy_path_create_apply_accept_deliver_approve():
    creator = _create_user("bounty-api-creator@example.com", balance=Decimal("100.00"))
    hunter = _create_user("bounty-api-hunter@example.com", balance=Decimal("5.00"))

    creator_client = _auth_client(creator)
    hunter_client = _auth_client(hunter)

    create_payload = {
        "title": "API Flow Bounty",
        "description": "Verify full bounty api flow.",
        "attachments": ["https://example.com/spec.pdf", "https://example.com/mockup.png"],
        "skill_requirements": "熟悉 Python 与日志分析",
        "bounty_type": "GENERAL",
        "max_applicants": 3,
        "workload_estimate": "ONE_DAY",
        "reward": 20,
        "deadline": (timezone.now() + timedelta(days=7)).isoformat(),
    }
    create_response = creator_client.post(
        "/api/bounties/",
        data=json.dumps(create_payload),
        content_type="application/json",
    )
    assert create_response.status_code == 201, create_response.content.decode()
    created = create_response.json()
    bounty_id = created["id"]
    assert created["status"] == "OPEN"
    assert created["attachments"] == create_payload["attachments"]
    assert created["skill_requirements"] == create_payload["skill_requirements"]
    assert created["max_applicants"] == 3
    assert created["workload_estimate"] == "ONE_DAY"

    creator.refresh_from_db()
    assert creator.balance == Decimal("80.00")
    assert creator.frozen_balance == Decimal("20.00")

    apply_response = hunter_client.post(
        f"/api/bounties/{bounty_id}/apply",
        data=json.dumps({"proposal": "I can deliver this in 2 days", "estimated_days": 2}),
        content_type="application/json",
    )
    assert apply_response.status_code == 201, apply_response.content.decode()

    detail_response = creator_client.get(f"/api/bounties/{bounty_id}")
    assert detail_response.status_code == 200, detail_response.content.decode()
    application_id = detail_response.json()["applications"][0]["id"]

    accept_response = creator_client.post(f"/api/bounties/{bounty_id}/accept/{application_id}")
    assert accept_response.status_code == 200, accept_response.content.decode()
    assert accept_response.json()["status"] == "IN_PROGRESS"

    submit_response = hunter_client.post(
        f"/api/bounties/{bounty_id}/submit",
        data=json.dumps({"content": "Delivered all requested work."}),
        content_type="application/json",
    )
    assert submit_response.status_code == 200, submit_response.content.decode()
    assert submit_response.json()["status"] == "DELIVERED"

    approve_response = creator_client.post(f"/api/bounties/{bounty_id}/approve")
    assert approve_response.status_code == 200, approve_response.content.decode()
    approved = approve_response.json()
    assert approved["status"] == "COMPLETED"

    creator.refresh_from_db()
    hunter.refresh_from_db()
    assert creator.balance == Decimal("80.00")
    assert creator.frozen_balance == Decimal("0.00")
    assert hunter.balance == Decimal("25.00")
