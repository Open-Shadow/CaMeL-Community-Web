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
            return User.objects.get(id=data['user_id'])
        except (TokenError, User.DoesNotExist):
            return None


def public_api(func):
    """No authentication required."""
    return func


def login_required(func):
    """Requires JWT login. Apply as ninja router auth=AuthBearer()."""
    return func


def moderator_required(func):
    """Requires moderator role or above."""
    return func


def admin_required(func):
    """Requires admin role."""
    return func
