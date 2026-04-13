from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            data = AccessToken(token)
            user = User.objects.get(id=data['user_id'])
            if not user.is_active:
                return None
            return user
        except (TokenError, User.DoesNotExist):
            return None


# Go role values: 1=common, 10=admin, 100=root
ROLE_COMMON = 1
ROLE_COMMUNITY_MODERATOR = 5
ROLE_ADMIN = 10
ROLE_ROOT = 100


def public_api(func):
    """No authentication required."""
    return func


def login_required(func):
    """Requires JWT login. Apply as ninja router auth=AuthBearer()."""
    return func


def moderator_required(func):
    """Requires moderator role or above (role >= 5)."""
    from functools import wraps
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'auth', None)
        if not user or user.role < ROLE_COMMUNITY_MODERATOR:
            raise HttpError(403, "需要版主权限")
        return func(request, *args, **kwargs)
    return wrapper


def admin_required(func):
    """Requires admin role (role >= 10)."""
    from functools import wraps
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'auth', None)
        if not user or user.role < ROLE_ADMIN:
            raise HttpError(403, "需要管理员权限")
        return func(request, *args, **kwargs)
    return wrapper
