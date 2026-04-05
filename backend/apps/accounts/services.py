"""Accounts business logic — invitation system."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.cache import cache

from apps.accounts.models import Invitation

User = get_user_model()

# ── Anti-abuse constants ──
INVITE_MONTHLY_LIMIT = 20
INVITE_ACTIVE_DAYS = 7  # invitee must be active within 7 days


class InvitationService:
    """Service for invitation code management."""

    @classmethod
    def generate_code(cls, user) -> str:
        """Generate an invitation code for the user (reuse existing if unused)."""
        existing = Invitation.objects.filter(
            inviter=user, used_by__isnull=True
        ).first()
        if existing:
            return existing.code

        # Anti-abuse: monthly limit
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_count = Invitation.objects.filter(
            inviter=user, created_at__gte=month_start
        ).count()
        if month_count >= INVITE_MONTHLY_LIMIT:
            raise ValueError("本月邀请次数已达上限")

        code = get_random_string(8).upper()
        Invitation.objects.create(inviter=user, code=code)
        return code

    @classmethod
    def get_my_invitations(cls, user):
        """List all invitations by this user."""
        return Invitation.objects.filter(inviter=user).order_by("-created_at")

    @classmethod
    def get_stats(cls, user) -> dict:
        """Get invitation stats for a user."""
        invitations = Invitation.objects.filter(inviter=user)
        total = invitations.count()
        used = invitations.filter(used_by__isnull=False).count()
        return {"total_codes": total, "used_codes": used, "remaining_this_month": max(0, INVITE_MONTHLY_LIMIT - total)}

    @classmethod
    def validate_code(cls, code: str):
        """Validate an invitation code. Returns (invitation, error_msg)."""
        try:
            invitation = Invitation.objects.select_related("inviter").get(code=code)
        except Invitation.DoesNotExist:
            return None, "邀请码不存在"

        if invitation.used_by is not None:
            return None, "邀请码已被使用"

        return invitation, None

    @classmethod
    def apply_code(cls, code: str, new_user, ip_address: str = "") -> tuple[bool, str]:
        """
        Apply an invitation code during registration.
        Returns (success, error_msg).
        """
        invitation, error = cls.validate_code(code)
        if error:
            return False, error

        # Anti-abuse: IP check — max 3 invites per IP per day
        if ip_address:
            ip_key = f"invite_ip:{ip_address}"
            ip_count = cache.get(ip_key, 0)
            if ip_count >= 3:
                return False, "该网络邀请次数过多，请稍后再试"
            cache.set(ip_key, ip_count + 1, timeout=86400)

        # Self-invite check
        if invitation.inviter_id == new_user.id:
            return False, "不能使用自己的邀请码"

        # Bind
        invitation.used_by = new_user
        invitation.used_at = timezone.now()
        invitation.save(update_fields=["used_by", "used_at"])

        new_user.invited_by = invitation.inviter
        new_user.save(update_fields=["invited_by"])

        return True, ""

    @classmethod
    def check_invitee_active(cls, user) -> bool:
        """Check if invitee has been active within INVITE_ACTIVE_DAYS."""
        if not user.last_login:
            return False
        delta = timezone.now() - user.last_login
        return delta.days <= INVITE_ACTIVE_DAYS
