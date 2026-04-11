"""Authentication API routes using django-allauth and JWT."""
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja import Router, Schema
from ninja.responses import Status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.services import AuthService, InvitationError, InvitationService
from apps.credits.models import CreditAction
from apps.credits.services import CreditService
from common.permissions import AuthBearer
from common.utils import build_absolute_media_url

User = get_user_model()
router = Router(tags=["auth"])


# =============================================================================
# Schemas
# =============================================================================

class RegisterInput(Schema):
    email: str
    password: str
    display_name: str = ""
    invite_code: str | None = None


class LoginInput(Schema):
    email: str
    password: str


class TokenOutput(Schema):
    access: str
    refresh: str
    expires_in: int  # seconds


class UserOutput(Schema):
    id: int
    username: str
    email: str
    display_name: str
    avatar_url: str
    role: str
    level: str
    credit_score: int
    email_verified: bool


class MessageOutput(Schema):
    message: str


class RefreshInput(Schema):
    refresh: str


class VerifyEmailInput(Schema):
    key: str


class ForgotPasswordInput(Schema):
    email: str


class ResetPasswordInput(Schema):
    uid: str
    token: str
    new_password: str


class SocialAuthorizeOutput(Schema):
    provider: str
    authorization_url: str
    callback_url: str


class SocialExchangeInput(Schema):
    code: str


class InviteValidationOutput(Schema):
    code: str
    inviter_display_name: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

def get_tokens_for_user(user):
    """Generate JWT tokens for user."""
    return AuthService.get_tokens_for_user(user)


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/register", response={201: TokenOutput, 400: MessageOutput})
def register(request, data: RegisterInput):
    """Register a new user with email and password."""
    normalized_email = data.email.strip().lower()
    if User.objects.filter(email__iexact=normalized_email).exists():
        return Status(400, {"message": "该邮箱已被注册"})

    # Validate password with a temporary user for similarity checking
    temp_user = User(
        username=f"user_placeholder",
        email=normalized_email,
        display_name=data.display_name or normalized_email.split("@")[0],
    )
    try:
        validate_password(data.password, user=temp_user)
    except ValidationError as e:
        return Status(400, {"message": "密码强度不足: " + ", ".join(e.messages)})

    try:
        with transaction.atomic():
            if data.invite_code:
                InvitationService.validate_code(data.invite_code)

            user = User.objects.create_user(
                username=f"user_{uuid.uuid4().hex[:12]}",
                email=normalized_email,
                password=data.password,
                display_name=data.display_name or normalized_email.split("@")[0],
            )

            if data.invite_code:
                InvitationService.bind_invitation_for_registration(
                    invitee=user,
                    code=data.invite_code,
                    request=request,
                )

            # Ensure every newly registered account gets baseline credit,
            # so first-time users can access gated marketplace flows.
            CreditService.add_credit(
                user,
                CreditAction.REGISTER,
                reference_id=f"register:{user.id}",
                idempotency_key=f"register:{user.id}",
            )
    except InvitationError as exc:
        return Status(400, {"message": str(exc)})
    except IntegrityError:
        return Status(400, {"message": "该邮箱已被注册"})

    AuthService.send_verification_email(request, user, signup=True)

    tokens = get_tokens_for_user(user)
    return Status(201, tokens)


@router.get("/invite-codes/{code}/validate", response={200: InviteValidationOutput, 404: MessageOutput})
def validate_invite_code(request, code: str):
    """Validate an invitation code before registration."""
    try:
        invitation = InvitationService.validate_code(code)
    except InvitationError as exc:
        return Status(404, {"message": str(exc)})

    inviter_name = invitation.inviter.display_name or invitation.inviter.email.split("@")[0]
    return Status(200, {
        "code": invitation.code,
        "inviter_display_name": inviter_name,
        "message": f"邀请码可用，邀请人：{inviter_name}",
    })


@router.post("/login", response={200: TokenOutput, 401: MessageOutput})
def login(request, data: LoginInput):
    """Login with email and password."""
    try:
        user = User.objects.get(email__iexact=data.email.strip().lower(), is_active=True)
    except User.DoesNotExist:
        return Status(401, {"message": "邮箱或密码错误"})

    if not user.check_password(data.password):
        return Status(401, {"message": "邮箱或密码错误"})

    if not user.is_active:
        return 401, {"message": "请先验证您的邮箱"}

    tokens = get_tokens_for_user(user)
    return Status(200, tokens)


@router.post("/refresh", response={200: TokenOutput, 401: MessageOutput})
def refresh_token(request, data: RefreshInput):
    """Refresh access token using refresh token."""
    try:
        refresh = RefreshToken(data.refresh)
        user = User.objects.get(id=refresh['user_id'])
        if not user.is_active:
            return Status(401, {"message": "账号已被停用"})
        return Status(200, {
            'refresh': data.refresh,
            'access': str(refresh.access_token),
            'expires_in': 3600,
        })
    except (TokenError, User.DoesNotExist):
        return Status(401, {"message": "无效的刷新令牌"})


@router.post("/logout", response={200: MessageOutput})
def logout(request, data: RefreshInput):
    """Logout by blacklisting the refresh token."""
    try:
        refresh = RefreshToken(data.refresh)
        refresh.blacklist()
        return Status(200, {"message": "登出成功"})
    except TokenError:
        return Status(200, {"message": "登出成功"})


@router.get("/me", response=UserOutput, auth=AuthBearer())
def get_me(request):
    """Get current user info."""
    user = request.auth
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": build_absolute_media_url(request, user.avatar_url),
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "email_verified": AuthService.is_email_verified(user),
    }


# =============================================================================
# Email Verification
# =============================================================================

@router.post("/verify-email", response={200: MessageOutput, 400: MessageOutput})
def verify_email(request, data: VerifyEmailInput):
    try:
        AuthService.verify_email(request, data.key)
    except ValidationError as exc:
        return Status(400, {"message": exc.messages[0]})
    return Status(200, {"message": "邮箱验证成功"})


# =============================================================================
# Password Reset
# =============================================================================

@router.post("/forgot-password", response=MessageOutput)
def forgot_password(request, data: ForgotPasswordInput):
    AuthService.send_password_reset_email(request, data.email.strip().lower())
    return {"message": "如果该邮箱已注册，我们已发送重置密码邮件"}


@router.post("/reset-password", response={200: MessageOutput, 400: MessageOutput})
def reset_password(request, data: ResetPasswordInput):
    try:
        AuthService.reset_password(data.uid, data.token, data.new_password)
    except ValidationError as exc:
        return Status(400, {"message": exc.messages[0]})
    return Status(200, {"message": "密码重置成功"})


# =============================================================================
# Social / OAuth
# =============================================================================

@router.get("/social/{provider}/authorize", response={200: SocialAuthorizeOutput, 400: MessageOutput})
def social_authorize(request, provider: str):
    try:
        authorization_url = AuthService.build_social_authorization_url(request, provider.lower())
    except ValidationError as exc:
        return Status(400, {"message": exc.messages[0]})

    return Status(200, {
        "provider": provider.lower(),
        "authorization_url": authorization_url,
        "callback_url": settings.FRONTEND_SOCIAL_CALLBACK_URL,
    })


@router.post("/social/exchange", response={200: TokenOutput, 400: MessageOutput})
def social_exchange(request, data: SocialExchangeInput):
    try:
        user = AuthService.consume_social_login_code(data.code)
    except ValidationError as exc:
        return Status(400, {"message": exc.messages[0]})
    return Status(200, get_tokens_for_user(user))
