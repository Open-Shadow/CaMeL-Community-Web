from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.contrib.auth import get_user_model

User = get_user_model()

# Sentinel: Django Ninja rejects any falsey return from auth callbacks as 401.
# OptionalAuthBearer returns this truthy sentinel when no token is present,
# then the view receives request.auth = _ANONYMOUS and treats it as None.
_ANONYMOUS = object()


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


class OptionalAuthBearer(HttpBearer):
    """Like AuthBearer but doesn't reject unauthenticated requests.

    Sets request.auth to the user if a valid token is present, or _ANONYMOUS otherwise.
    Views should use `get_optional_user(request)` to resolve to User | None.
    """

    def authenticate(self, request, token):
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            data = AccessToken(token)
            user = User.objects.get(id=data['user_id'])
            if not user.is_active:
                return None  # 401 — known but inactive user
            return user
        except (TokenError, User.DoesNotExist):
            return None  # 401 — invalid/expired token triggers frontend refresh

    def __call__(self, request):
        headers = request.headers
        auth_value = headers.get("Authorization", "")
        if not auth_value:
            return _ANONYMOUS  # No token at all → anonymous access
        parts = auth_value.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return _ANONYMOUS  # Malformed header without bearer → treat as anonymous
        return self.authenticate(request, parts[1])


def get_optional_user(request):
    """Resolve request.auth from OptionalAuthBearer to User | None."""
    auth = getattr(request, "auth", None)
    if auth is _ANONYMOUS or auth is None:
        return None
    return auth


def public_api(func):
    """No authentication required."""
    return func


def login_required(func):
    """Requires JWT login.

    Enforces that request.auth is a valid user object (not None / _ANONYMOUS).
    Still apply auth=AuthBearer() on the router for Django Ninja to parse
    the Authorization header.
    """
    from functools import wraps
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'auth', None)
        if not user or user is _ANONYMOUS:
            raise HttpError(401, "需要登录")
        return func(request, *args, **kwargs)
    return wrapper


def moderator_required(func):
    """Requires moderator role or above."""
    from functools import wraps
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'auth', None)
        if not user or user.role not in ('MODERATOR', 'ADMIN'):
            raise HttpError(403, "需要版主权限")
        return func(request, *args, **kwargs)
    return wrapper


def admin_required(func):
    """Requires admin role."""
    from functools import wraps
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'auth', None)
        if not user or user.role != 'ADMIN':
            raise HttpError(403, "需要管理员权限")
        return func(request, *args, **kwargs)
    return wrapper
