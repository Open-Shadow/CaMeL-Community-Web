"""Browser-based auth views used by allauth social login redirects."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.accounts.services import AuthService


def _append_query_params(url: str, **params: str):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({key: value for key, value in params.items() if value})
    return urlunsplit(parts._replace(query=urlencode(query)))


@login_required
def social_login_bridge(request):
    """Exchange a successful allauth session login for a one-time JWT code."""
    provider = request.GET.get('provider', '')
    code = AuthService.create_social_login_code(request.user, provider)
    auth_logout(request)
    redirect_url = _append_query_params(
        settings.FRONTEND_SOCIAL_CALLBACK_URL,
        code=code,
        provider=provider,
    )
    return redirect(redirect_url)


def social_login_error(request):
    """Redirect social auth failures back to the SPA callback page."""
    redirect_url = _append_query_params(
        settings.FRONTEND_SOCIAL_CALLBACK_URL,
        error=request.GET.get('error', 'social_login_failed'),
        provider=request.GET.get('provider', ''),
    )
    return redirect(redirect_url)
