"""Accounts business logic."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import urlencode

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Invitation
from apps.credits.models import CreditAction, CreditLog
from apps.credits.services import CreditService
from common.constants import (
    INVITE_ACTIVITY_WINDOW_DAYS,
    INVITE_CODE_CHARS,
    INVITE_CODE_LENGTH,
    INVITE_MONTHLY_CREDIT_CAP,
)
from common.utils import generate_random_string

User = get_user_model()

SOCIAL_CODE_CACHE_PREFIX = "auth:social:code:"
SOCIAL_CODE_TTL_SECONDS = 300
SUPPORTED_SOCIAL_PROVIDERS = {"github", "google"}


class AuthService:
    """Shared auth helpers for email/JWT/social flows."""

    @staticmethod
    def get_tokens_for_user(user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "expires_in": 3600,
        }

    @staticmethod
    def ensure_email_address(user) -> EmailAddress:
        email_address, created = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": False},
        )
        updates = []
        if not email_address.primary:
            email_address.primary = True
            updates.append("primary")
        if created:
            return email_address
        if updates:
            email_address.save(update_fields=updates)
        return email_address

    @staticmethod
    def is_email_verified(user) -> bool:
        return EmailAddress.objects.filter(user=user, email=user.email, verified=True).exists()

    @classmethod
    def send_verification_email(cls, request, user, *, signup=False):
        email_address = cls.ensure_email_address(user)
        email_address.send_confirmation(request=request, signup=signup)

    @staticmethod
    def verify_email(request, key: str):
        confirmation = EmailConfirmationHMAC.from_key(key)
        if not confirmation:
            raise ValidationError("无效或已过期的邮箱验证链接")
        confirmation.confirm(request)
        return confirmation.email_address

    @staticmethod
    def send_password_reset_email(request, email: str):
        users = User.objects.filter(email__iexact=email, is_active=True)
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            password_reset_url = settings.FRONTEND_PASSWORD_RESET_URL.format(uid=uid, token=token)
            get_adapter(request).send_mail(
                "account/email/password_reset_key",
                user.email,
                {
                    "user": user,
                    "password_reset_url": password_reset_url,
                    "request": request,
                },
            )

    @staticmethod
    def reset_password(uid: str, token: str, new_password: str):
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError("无效的重置链接")

        if not default_token_generator.check_token(user, token):
            raise ValidationError("无效或已过期的重置链接")

        validate_password(new_password, user)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return user

    @staticmethod
    def is_social_provider_configured(provider: str) -> bool:
        provider_settings = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {})
        apps = provider_settings.get("APPS", [])
        if apps:
            app = apps[0]
            return bool(app.get("client_id") and app.get("secret"))
        return False

    @staticmethod
    def build_social_authorization_url(request, provider: str) -> str:
        if provider not in SUPPORTED_SOCIAL_PROVIDERS:
            raise ValidationError("不支持的 OAuth 提供商")

        if not AuthService.is_social_provider_configured(provider):
            raise ValidationError(f"{provider.capitalize()} OAuth 尚未配置客户端凭证")

        bridge_url = request.build_absolute_uri(reverse("accounts-social-bridge"))
        bridge_query = urlencode({"provider": provider})
        login_url = request.build_absolute_uri(f"/accounts/{provider}/login/")
        return f'{login_url}?{urlencode({"process": "login", "next": f"{bridge_url}?{bridge_query}"})}'

    @staticmethod
    def create_social_login_code(user, provider: str) -> str:
        if provider and provider not in SUPPORTED_SOCIAL_PROVIDERS:
            raise ValidationError("不支持的 OAuth 提供商")

        code = secrets.token_urlsafe(32)
        cache.set(
            f"{SOCIAL_CODE_CACHE_PREFIX}{code}",
            {"user_id": user.pk, "provider": provider},
            timeout=SOCIAL_CODE_TTL_SECONDS,
        )
        return code

    @staticmethod
    def consume_social_login_code(code: str):
        cache_key = f"{SOCIAL_CODE_CACHE_PREFIX}{code}"
        payload = cache.get(cache_key)
        if not payload:
            raise ValidationError("无效或已过期的社交登录兑换码")

        cache.delete(cache_key)
        try:
            return User.objects.get(pk=payload["user_id"], is_active=True)
        except User.DoesNotExist as exc:
            raise ValidationError("用户不存在或已停用") from exc


class InvitationError(ValueError):
    """Raised when an invitation code cannot be used."""


@dataclass
class InvitationRewardResult:
    invitee_rewarded: bool
    inviter_rewarded: bool
    risk_flags: list[str]


class InvitationService:
    """Invitation code generation, validation, rewarding and anti-abuse helpers."""

    DUPLICATE_IP_FLAG = "duplicate_ip"
    DUPLICATE_DEVICE_FLAG = "duplicate_device"
    MONTHLY_CAP_FLAG = "monthly_credit_cap"

    @classmethod
    def normalize_code(cls, code: str | None) -> str:
        return (code or "").strip().upper()

    @classmethod
    def get_or_create_shareable_invitation(cls, inviter: User) -> Invitation:
        invitation = (
            Invitation.objects.filter(inviter=inviter, used_by__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if invitation:
            return invitation
        return Invitation.objects.create(inviter=inviter, code=cls._generate_unique_code())

    @classmethod
    def validate_code(cls, code: str | None) -> Invitation:
        normalized_code = cls.normalize_code(code)
        if not normalized_code:
            raise InvitationError("邀请码不能为空")

        invitation = (
            Invitation.objects.select_related("inviter", "used_by").filter(code=normalized_code).first()
        )
        if not invitation:
            raise InvitationError("邀请码不存在")
        if invitation.used_by_id:
            raise InvitationError("邀请码已被使用")
        return invitation

    @classmethod
    @transaction.atomic
    def bind_invitation_for_registration(cls, *, invitee: User, code: str, request) -> InvitationRewardResult:
        invitation = cls._lock_invitation(code)
        if invitation.inviter_id == invitee.id:
            raise InvitationError("不能使用自己的邀请码")

        ip_hash, device_hash = cls._extract_fingerprint(request)
        risk_flags = cls._detect_risk(
            current_invitation=invitation,
            ip_hash=ip_hash,
            device_hash=device_hash,
        )

        invitation.used_by = invitee
        invitation.used_at = timezone.now()
        invitation.registration_ip_hash = ip_hash
        invitation.registration_device_hash = device_hash
        invitation.risk_flags = risk_flags
        invitation.save(
            update_fields=[
                "used_by",
                "used_at",
                "registration_ip_hash",
                "registration_device_hash",
                "risk_flags",
            ]
        )

        invitee.invited_by = invitation.inviter
        invitee.save(update_fields=["invited_by"])

        if cls._has_reward_blocking_risk(risk_flags):
            return InvitationRewardResult(
                invitee_rewarded=False,
                inviter_rewarded=False,
                risk_flags=risk_flags,
            )

        inviter_rewarded = cls._award_inviter_registration_reward(invitation)
        invitee_rewarded = cls._award_invitee_registration_reward(invitation)

        return InvitationRewardResult(
            invitee_rewarded=invitee_rewarded,
            inviter_rewarded=inviter_rewarded,
            risk_flags=risk_flags,
        )

    @classmethod
    def get_dashboard(cls, inviter: User) -> dict:
        invitation = cls.get_or_create_shareable_invitation(inviter)
        invitations = Invitation.objects.filter(inviter=inviter).select_related("used_by")
        rewarded_invites = CreditLog.objects.filter(
            user=inviter,
            action=CreditAction.INVITE_REGISTERED,
            reference_id__startswith="invite-registration:inviter:",
        ).count()
        monthly_awarded = cls._current_month_awarded_credit(inviter)

        recent_invites = [
            {
                "id": invite.id,
                "code": invite.code,
                "invitee_display_name": (
                    invite.used_by.display_name or invite.used_by.email.split("@")[0]
                    if invite.used_by
                    else ""
                ),
                "invitee_email": invite.used_by.email if invite.used_by else "",
                "used_at": invite.used_at.isoformat() if invite.used_at else "",
                "risk_flags": invite.risk_flags,
            }
            for invite in invitations.order_by("-used_at", "-created_at")[:5]
            if invite.used_by_id
        ]

        return {
            "code": invitation.code,
            "share_path": f"/register?invite={invitation.code}",
            "total_codes_generated": invitations.count(),
            "registered_invites": invitations.filter(used_by__isnull=False).count(),
            "rewarded_invites": rewarded_invites,
            "delayed_reward_pending": invitations.filter(
                used_by__isnull=False,
                first_deposit_rewarded=False,
            ).count(),
            "monthly_credit_awarded": monthly_awarded,
            "monthly_credit_remaining": max(0, INVITE_MONTHLY_CREDIT_CAP - monthly_awarded),
            "active_window_days": INVITE_ACTIVITY_WINDOW_DAYS,
            "recent_invites": recent_invites,
        }

    @classmethod
    def _generate_unique_code(cls) -> str:
        while True:
            code = generate_random_string(length=INVITE_CODE_LENGTH, chars=INVITE_CODE_CHARS)
            if not Invitation.objects.filter(code=code).exists():
                return code

    @classmethod
    def _lock_invitation(cls, code: str) -> Invitation:
        normalized_code = cls.normalize_code(code)
        if not normalized_code:
            raise InvitationError("邀请码不能为空")

        invitation = (
            Invitation.objects.select_for_update()
            .select_related("inviter", "used_by")
            .filter(code=normalized_code)
            .first()
        )
        if not invitation:
            raise InvitationError("邀请码不存在")
        if invitation.used_by_id:
            raise InvitationError("邀请码已被使用")
        return invitation

    @classmethod
    def _extract_fingerprint(cls, request) -> tuple[str, str]:
        headers = getattr(request, "headers", {})
        meta = getattr(request, "META", {})
        ip_value = meta.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or meta.get("REMOTE_ADDR", "").strip()
        device_value = headers.get("X-Device-Id", "").strip() or meta.get("HTTP_X_DEVICE_ID", "").strip()
        return cls._hash_value(ip_value), cls._hash_value(device_value)

    @classmethod
    def _hash_value(cls, value: str) -> str:
        if not value:
            return ""
        return sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def _detect_risk(cls, *, current_invitation: Invitation, ip_hash: str, device_hash: str) -> list[str]:
        risk_flags: list[str] = []

        if ip_hash and Invitation.objects.filter(
            registration_ip_hash=ip_hash,
            used_by__isnull=False,
        ).exclude(pk=current_invitation.pk).exists():
            risk_flags.append(cls.DUPLICATE_IP_FLAG)

        if device_hash and Invitation.objects.filter(
            registration_device_hash=device_hash,
            used_by__isnull=False,
        ).exclude(pk=current_invitation.pk).exists():
            risk_flags.append(cls.DUPLICATE_DEVICE_FLAG)

        return risk_flags

    @classmethod
    def _has_reward_blocking_risk(cls, risk_flags: list[str]) -> bool:
        return cls.DUPLICATE_IP_FLAG in risk_flags or cls.DUPLICATE_DEVICE_FLAG in risk_flags

    @classmethod
    def _award_inviter_registration_reward(cls, invitation: Invitation) -> bool:
        inviter = invitation.inviter
        if cls._current_month_awarded_credit(inviter) >= INVITE_MONTHLY_CREDIT_CAP:
            risk_flags = list(invitation.risk_flags)
            if cls.MONTHLY_CAP_FLAG not in risk_flags:
                risk_flags.append(cls.MONTHLY_CAP_FLAG)
                invitation.risk_flags = risk_flags
                invitation.save(update_fields=["risk_flags"])
            return False

        score_before = inviter.credit_score
        score_after = CreditService.add_credit(
            inviter,
            CreditAction.INVITE_REGISTERED,
            idempotency_key=f"invite-registration:inviter:{invitation.id}",
        )
        return score_after != score_before

    @classmethod
    def _award_invitee_registration_reward(cls, invitation: Invitation) -> bool:
        invitee = invitation.used_by
        if not invitee:
            return False

        score_before = invitee.credit_score
        score_after = CreditService.add_credit(
            invitee,
            CreditAction.INVITE_REGISTERED,
            idempotency_key=f"invite-registration:invitee:{invitation.id}",
        )
        return score_after != score_before

    @classmethod
    def _current_month_awarded_credit(cls, inviter: User) -> int:
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = CreditLog.objects.filter(
            user=inviter,
            action=CreditAction.INVITE_REGISTERED,
            created_at__gte=month_start,
            reference_id__startswith="invite-registration:inviter:",
        ).aggregate(total=Sum("amount"))["total"]
        return total or 0
