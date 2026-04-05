import json

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Invitation
from apps.accounts.services import InvitationService
from apps.credits.models import CreditAction, CreditLog
from apps.credits.services import CreditService

User = get_user_model()


def create_user(email: str) -> User:
    return User.objects.create_user(
        username=email,
        email=email,
        password="TestPassword123!",
        display_name=email.split("@")[0],
    )


@pytest.mark.django_db
def test_register_with_invite_code_binds_relation_and_rewards(client):
    inviter = create_user("inviter@example.com")
    invitation = InvitationService.get_or_create_shareable_invitation(inviter)

    response = client.post(
        "/api/auth/register",
        data=json.dumps(
            {
                "email": "invitee@example.com",
                "password": "TestPassword123!",
                "display_name": "Invitee",
                "invite_code": invitation.code,
            }
        ),
        content_type="application/json",
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_DEVICE_ID="device-a",
    )

    assert response.status_code == 201

    invitee = User.objects.get(email="invitee@example.com")
    inviter.refresh_from_db()
    invitee.refresh_from_db()
    invitation.refresh_from_db()

    assert invitation.used_by == invitee
    assert invitee.invited_by == inviter
    assert inviter.credit_score == 10
    assert invitee.credit_score == 10
    assert CreditLog.objects.filter(action=CreditAction.INVITE_REGISTERED).count() == 2


@pytest.mark.django_db
def test_add_credit_is_idempotent_with_same_key():
    user = create_user("rewarded@example.com")

    first_score = CreditService.add_credit(
        user,
        CreditAction.INVITE_REGISTERED,
        idempotency_key="invite-registration:invitee:1",
    )
    second_score = CreditService.add_credit(
        user,
        CreditAction.INVITE_REGISTERED,
        idempotency_key="invite-registration:invitee:1",
    )

    user.refresh_from_db()

    assert first_score == 10
    assert second_score == 10
    assert user.credit_score == 10
    assert CreditLog.objects.filter(user=user, action=CreditAction.INVITE_REGISTERED).count() == 1


@pytest.mark.django_db
def test_duplicate_device_blocks_invitation_rewards():
    first_inviter = create_user("first-inviter@example.com")
    first_invitation = InvitationService.get_or_create_shareable_invitation(first_inviter)
    first_invitee = create_user("first-invitee@example.com")
    InvitationService.bind_invitation_for_registration(
        invitee=first_invitee,
        code=first_invitation.code,
        request=type(
            "Request",
            (),
            {
                "META": {"REMOTE_ADDR": "10.0.0.2"},
                "headers": {"X-Device-Id": "shared-device"},
            },
        )(),
    )

    second_inviter = create_user("second-inviter@example.com")
    second_invitation = InvitationService.get_or_create_shareable_invitation(second_inviter)

    second_invitee = create_user("second-invitee@example.com")
    result = InvitationService.bind_invitation_for_registration(
        invitee=second_invitee,
        code=second_invitation.code,
        request=type(
            "Request",
            (),
            {
                "META": {"REMOTE_ADDR": "10.0.0.3"},
                "headers": {"X-Device-Id": "shared-device"},
            },
        )(),
    )

    second_invitation.refresh_from_db()
    second_inviter.refresh_from_db()
    second_invitee.refresh_from_db()

    assert second_invitee.invited_by == second_inviter
    assert second_inviter.credit_score == 0
    assert second_invitee.credit_score == 0
    assert InvitationService.DUPLICATE_DEVICE_FLAG in second_invitation.risk_flags
    assert InvitationService.DUPLICATE_DEVICE_FLAG in result.risk_flags


@pytest.mark.django_db
def test_monthly_credit_cap_blocks_only_inviter_reward():
    inviter = create_user("capped-inviter@example.com")
    for index in range(20):
        CreditService.add_credit(
            inviter,
            CreditAction.INVITE_REGISTERED,
            idempotency_key=f"invite-registration:inviter:seed-{index}",
        )

    invitation = InvitationService.get_or_create_shareable_invitation(inviter)
    invitee = create_user("cap-invitee@example.com")
    result = InvitationService.bind_invitation_for_registration(
        invitee=invitee,
        code=invitation.code,
        request=type(
            "Request",
            (),
            {
                "META": {"REMOTE_ADDR": "10.0.0.4"},
                "headers": {"X-Device-Id": "device-cap"},
            },
        )(),
    )

    invitee.refresh_from_db()
    inviter.refresh_from_db()
    invitation.refresh_from_db()

    assert inviter.credit_score == 200
    assert invitee.credit_score == 10
    assert InvitationService.MONTHLY_CAP_FLAG in invitation.risk_flags
    assert result.inviter_rewarded is False
    assert result.invitee_rewarded is True
    assert CreditLog.objects.filter(
        user=inviter,
        action=CreditAction.INVITE_REGISTERED,
        reference_id=f"invite-registration:inviter:{invitation.id}",
    ).count() == 0
