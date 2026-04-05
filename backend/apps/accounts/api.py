"""Authentication API routes using django-allauth and JWT."""
from ninja import Router, Schema
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from common.permissions import AuthBearer

User = get_user_model()
router = Router(tags=["auth"])


# =============================================================================
# Schemas
# =============================================================================

class RegisterInput(Schema):
    email: str
    password: str
    display_name: str = ""
    invite_code: str = ""


class LoginInput(Schema):
    email: str
    password: str


class TokenOutput(Schema):
    access: str
    refresh: str
    expires_in: int  # seconds


class UserOutput(Schema):
    id: int
    email: str
    display_name: str
    avatar_url: str
    role: str
    level: str
    credit_score: int


class MessageOutput(Schema):
    message: str


class RefreshInput(Schema):
    refresh: str


class OAuthCallbackInput(Schema):
    code: str
    provider: str  # "github" or "google"


class ForgotPasswordInput(Schema):
    email: str


class ResetPasswordInput(Schema):
    token: str
    new_password: str


class VerifyEmailInput(Schema):
    token: str


# =============================================================================
# Helper Functions
# =============================================================================

def get_tokens_for_user(user):
    """Generate JWT tokens for user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'expires_in': 3600,  # 60 minutes
    }


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/register", response={201: TokenOutput, 400: MessageOutput})
def register(request, data: RegisterInput):
    """Register a new user with email and password."""
    # Check if email exists
    if User.objects.filter(email=data.email).exists():
        return 400, {"message": "该邮箱已被注册"}

    # Validate password
    try:
        validate_password(data.password)
    except ValidationError as e:
        return 400, {"message": "密码强度不足: " + ", ".join(e.messages)}

    # Create user (inactive until email verified)
    from django.core.cache import cache
    user = User.objects.create_user(
        username=data.email,
        email=data.email,
        password=data.password,
        display_name=data.display_name or data.email.split('@')[0],
        is_active=False,
    )

    # Handle invitation code
    if data.invite_code:
        from apps.accounts.services import InvitationService
        ip = request.META.get("REMOTE_ADDR", "")
        success, error = InvitationService.apply_code(data.invite_code, user, ip_address=ip)
        if success:
            from apps.accounts.tasks import grant_invite_register_reward
            grant_invite_register_reward.delay(user.invited_by_id, user.id)

    # Send verification email (async)
    token = get_random_string(64)
    cache.set(f"email_verify:{token}", user.id, timeout=3 * 24 * 3600)
    from apps.accounts.tasks import send_verification_email
    send_verification_email.delay(user.id, token, settings.FRONTEND_URL)

    tokens = get_tokens_for_user(user)
    return 201, tokens


@router.post("/login", response={200: TokenOutput, 401: MessageOutput})
def login(request, data: LoginInput):
    """Login with email and password."""
    try:
        user = User.objects.get(email=data.email)
    except User.DoesNotExist:
        return 401, {"message": "邮箱或密码错误"}

    if not user.check_password(data.password):
        return 401, {"message": "邮箱或密码错误"}

    if not user.is_active:
        return 401, {"message": "请先验证您的邮箱"}

    tokens = get_tokens_for_user(user)
    return 200, tokens


@router.post("/refresh", response={200: TokenOutput, 401: MessageOutput})
def refresh_token(request, data: RefreshInput):
    """Refresh access token using refresh token."""
    try:
        refresh = RefreshToken(data.refresh)
        return 200, {
            'refresh': data.refresh,
            'access': str(refresh.access_token),
            'expires_in': 3600,
        }
    except TokenError:
        return 401, {"message": "无效的刷新令牌"}


@router.post("/logout", response={200: MessageOutput})
def logout(request, data: RefreshInput):
    """Logout by blacklisting the refresh token."""
    try:
        refresh = RefreshToken(data.refresh)
        refresh.blacklist()
        return 200, {"message": "登出成功"}
    except TokenError:
        return 200, {"message": "登出成功"}


@router.get("/me", response=UserOutput, auth=AuthBearer())
def get_me(request):
    """Get current user info."""
    user = request.auth
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
    }


# =============================================================================
# OAuth
# =============================================================================

@router.get("/oauth/{provider}/url", response={200: dict, 400: MessageOutput})
def get_oauth_url(request, provider: str):
    """Get OAuth authorization URL for GitHub or Google."""
    from allauth.socialaccount.providers.github.provider import GitHubProvider
    from allauth.socialaccount.providers.google.provider import GoogleProvider

    base_url = settings.FRONTEND_URL
    callback_url = f"{base_url}/auth/callback/{provider}"

    if provider == "github":
        client_id = settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['client_id']
        url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={callback_url}&scope=user:email"
    elif provider == "google":
        client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}&redirect_uri={callback_url}"
            f"&response_type=code&scope=openid+email+profile"
        )
    else:
        return 400, {"message": "不支持的 OAuth 提供商"}

    return 200, {"url": url}


@router.post("/oauth/callback", response={200: TokenOutput, 400: MessageOutput})
def oauth_callback(request, data: OAuthCallbackInput):
    """Exchange OAuth code for JWT tokens."""
    import requests as http_requests

    frontend_url = settings.FRONTEND_URL
    callback_url = f"{frontend_url}/auth/callback/{data.provider}"

    if data.provider == "github":
        # Exchange code for access token
        resp = http_requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['client_id'],
                "client_secret": settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['secret'],
                "code": data.code,
                "redirect_uri": callback_url,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return 400, {"message": "GitHub OAuth 失败"}

        # Get user info
        user_resp = http_requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"},
            timeout=10,
        )
        gh_user = user_resp.json()

        # Get primary email
        email_resp = http_requests.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"token {access_token}"},
            timeout=10,
        )
        emails = email_resp.json()
        primary_email = next(
            (e["email"] for e in emails if e.get("primary") and e.get("verified")),
            gh_user.get("email"),
        )
        if not primary_email:
            return 400, {"message": "无法获取 GitHub 邮箱"}

        display_name = gh_user.get("name") or gh_user.get("login", "")
        avatar_url = gh_user.get("avatar_url", "")

    elif data.provider == "google":
        # Exchange code for tokens
        resp = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'],
                "client_secret": settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret'],
                "code": data.code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url,
            },
            timeout=10,
        )
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return 400, {"message": "Google OAuth 失败"}

        # Get user info
        user_resp = http_requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        g_user = user_resp.json()
        primary_email = g_user.get("email")
        if not primary_email:
            return 400, {"message": "无法获取 Google 邮箱"}

        display_name = g_user.get("name", "")
        avatar_url = g_user.get("picture", "")
    else:
        return 400, {"message": "不支持的 OAuth 提供商"}

    # Get or create user
    user, created = User.objects.get_or_create(
        email=primary_email,
        defaults={
            "username": primary_email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "is_active": True,
        },
    )
    if created and avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url
        user.save(update_fields=["avatar_url"])

    tokens = get_tokens_for_user(user)
    return 200, tokens


# =============================================================================
# Email Verification
# =============================================================================

@router.post("/verify-email", response={200: MessageOutput, 400: MessageOutput})
def verify_email(request, data: VerifyEmailInput):
    """Verify email address using token."""
    from django.core.cache import cache

    user_id = cache.get(f"email_verify:{data.token}")
    if not user_id:
        return 400, {"message": "验证链接无效或已过期"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 400, {"message": "用户不存在"}

    user.is_active = True
    user.save(update_fields=["is_active"])
    cache.delete(f"email_verify:{data.token}")
    return 200, {"message": "邮箱验证成功"}


@router.post("/resend-verification", response={200: MessageOutput, 400: MessageOutput})
def resend_verification(request, data: ForgotPasswordInput):
    """Resend email verification link."""
    from django.core.cache import cache

    try:
        user = User.objects.get(email=data.email)
    except User.DoesNotExist:
        # Don't reveal if email exists
        return 200, {"message": "如果该邮箱已注册，验证邮件已发送"}

    if user.is_active:
        return 400, {"message": "该邮箱已验证"}

    token = get_random_string(64)
    cache.set(f"email_verify:{token}", user.id, timeout=3 * 24 * 3600)

    from apps.accounts.tasks import send_verification_email
    send_verification_email.delay(user.id, token, settings.FRONTEND_URL)
    return 200, {"message": "如果该邮箱已注册，验证邮件已发送"}


# =============================================================================
# Password Reset
# =============================================================================

@router.post("/forgot-password", response={200: MessageOutput})
def forgot_password(request, data: ForgotPasswordInput):
    """Send password reset email."""
    from django.core.cache import cache

    try:
        user = User.objects.get(email=data.email)
    except User.DoesNotExist:
        return 200, {"message": "如果该邮箱已注册，重置邮件已发送"}

    token = get_random_string(64)
    cache.set(f"pwd_reset:{token}", user.id, timeout=3600)  # 1 hour

    from apps.accounts.tasks import send_password_reset_email
    send_password_reset_email.delay(user.email, token, settings.FRONTEND_URL)
    return 200, {"message": "如果该邮箱已注册，重置邮件已发送"}


@router.post("/reset-password", response={200: MessageOutput, 400: MessageOutput})
def reset_password(request, data: ResetPasswordInput):
    """Reset password using token from email."""
    from django.core.cache import cache

    user_id = cache.get(f"pwd_reset:{data.token}")
    if not user_id:
        return 400, {"message": "重置链接无效或已过期"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 400, {"message": "用户不存在"}

    try:
        validate_password(data.new_password, user)
    except ValidationError as e:
        return 400, {"message": "密码强度不足: " + ", ".join(e.messages)}

    user.set_password(data.new_password)
    user.save(update_fields=["password"])
    cache.delete(f"pwd_reset:{data.token}")
    return 200, {"message": "密码重置成功"}
