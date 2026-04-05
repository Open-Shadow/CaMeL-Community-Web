"""Custom account adapters for frontend-oriented auth flows."""
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    """Build frontend-facing URLs for email confirmation links."""

    def get_email_confirmation_url(self, request, emailconfirmation):
        return settings.FRONTEND_EMAIL_VERIFY_URL.format(key=emailconfirmation.key)
