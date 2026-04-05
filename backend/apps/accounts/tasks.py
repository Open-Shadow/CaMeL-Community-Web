"""Celery tasks for invitation rewards and email sending."""
from celery import shared_task
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task
def send_verification_email(user_id: int, token: str, frontend_url: str):
    """Send email verification link asynchronously."""
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    verify_url = f"{frontend_url}/verify-email?token={token}"
    send_mail(
        subject="验证您的 CaMeL Community 邮箱",
        message=f"请点击以下链接验证您的邮箱：\n\n{verify_url}\n\n链接有效期 3 天。",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task
def send_password_reset_email(email: str, token: str, frontend_url: str):
    """Send password reset link asynchronously."""
    from django.core.mail import send_mail
    from django.conf import settings
    reset_url = f"{frontend_url}/reset-password?token={token}"
    send_mail(
        subject="重置您的 CaMeL Community 密码",
        message=f"请点击以下链接重置密码：\n\n{reset_url}\n\n链接有效期 1 小时。",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )


@shared_task
def grant_invite_register_reward(inviter_id: int, invitee_id: int):
    """Grant immediate reward when invitee registers (inviter +10 credit, invitee +50 register credit)."""
    from apps.credits.services import CreditService
    from apps.credits.models import CreditAction
    from apps.notifications.services import NotificationService

    try:
        inviter = User.objects.get(id=inviter_id)
        invitee = User.objects.get(id=invitee_id)
    except User.DoesNotExist:
        return

    # Inviter reward
    CreditService.add_credit(inviter, CreditAction.INVITE_REGISTERED,
                             reference_id=str(invitee_id))
    NotificationService.send(
        recipient=inviter,
        notification_type="invite_reward",
        title="邀请奖励",
        content=f"您邀请的用户 {invitee.display_name or invitee.email} 已注册，+10 信用分",
        reference_id=str(invitee_id),
    )


@shared_task
def check_first_deposit_reward(invitee_id: int):
    """Check and grant first-deposit reward to inviter."""
    from apps.accounts.models import Invitation
    from apps.notifications.services import NotificationService

    try:
        invitee = User.objects.get(id=invitee_id)
    except User.DoesNotExist:
        return

    invitation = Invitation.objects.filter(used_by=invitee, first_deposit_rewarded=False).first()
    if not invitation:
        return

    inviter = invitation.inviter
    # Grant $0.50 bonus to inviter
    inviter.balance += 0.50
    inviter.save(update_fields=["balance"])

    invitation.first_deposit_rewarded = True
    invitation.save(update_fields=["first_deposit_rewarded"])

    NotificationService.send(
        recipient=inviter,
        notification_type="invite_deposit_reward",
        title="邀请首充奖励",
        content=f"您邀请的用户 {invitee.display_name or invitee.email} 已完成首充，+$0.50 奖励",
        reference_id=str(invitee.id),
    )
