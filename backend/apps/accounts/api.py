"""Authentication API routes using django-allauth and JWT."""
from ninja import Router, Schema
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
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

    # Create user
    user = User.objects.create_user(
        username=data.email,  # Use email as username
        email=data.email,
        password=data.password,
        display_name=data.display_name or data.email.split('@')[0],
    )

    # Generate tokens
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
