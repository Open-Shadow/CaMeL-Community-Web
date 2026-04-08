import json
import re

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.test import Client
from django.test.client import RequestFactory
from django.test.utils import override_settings

from apps.accounts.models import User
from apps.accounts.services import AuthService
from apps.credits.models import CreditAction, CreditLog


pytestmark = pytest.mark.django_db


def test_register_sends_email_verification():
    client = Client()

    response = client.post(
        '/api/auth/register',
        data=json.dumps(
            {
                'email': 'newuser@example.com',
                'password': 'StrongPass123!',
                'display_name': 'New User',
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 201
    payload = response.json()
    assert 'access' in payload
    assert 'refresh' in payload
    assert len(mail.outbox) == 1

    email_address = EmailAddress.objects.get(email='newuser@example.com')
    assert email_address.primary is True
    assert email_address.verified is False
    assert 'verify-email?key=' in mail.outbox[0].body


def test_register_awards_initial_credit_score():
    client = Client()

    response = client.post(
        '/api/auth/register',
        data=json.dumps(
            {
                'email': 'credit-init@example.com',
                'password': 'StrongPass123!',
                'display_name': 'Credit Init',
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 201
    user = User.objects.get(email='credit-init@example.com')
    assert user.credit_score == 50
    assert CreditLog.objects.filter(user=user, action=CreditAction.REGISTER).count() == 1


def test_verify_email_marks_email_as_verified():
    client = Client()
    request = RequestFactory().get('/api/auth/register')
    user = User.objects.create_user(
        username='verify@example.com',
        email='verify@example.com',
        password='StrongPass123!',
        display_name='Verify User',
    )
    AuthService.send_verification_email(request, user)

    message = mail.outbox[0].body
    match = re.search(r'key=([A-Za-z0-9:\-_.]+)', message)
    assert match is not None

    response = client.post(
        '/api/auth/verify-email',
        data=json.dumps({'key': match.group(1)}),
        content_type='application/json',
    )

    assert response.status_code == 200
    assert EmailAddress.objects.get(email='verify@example.com').verified is True


def test_forgot_password_and_reset_password_flow():
    client = Client()
    User.objects.create_user(
        username='reset@example.com',
        email='reset@example.com',
        password='OldPassword123!',
        display_name='Reset User',
    )

    forgot_response = client.post(
        '/api/auth/forgot-password',
        data=json.dumps({'email': 'reset@example.com'}),
        content_type='application/json',
    )

    assert forgot_response.status_code == 200
    assert len(mail.outbox) == 1

    message = mail.outbox[0].body
    uid_match = re.search(r'uid=([^&\s]+)', message)
    token_match = re.search(r'token=([^&\s]+)', message)
    if not uid_match or not token_match:
        path_match = re.search(r'/reset-password/([^/\s]+)/([^/\s]+)', message)
        assert path_match is not None
        uid = path_match.group(1)
        token = path_match.group(2)
    else:
        uid = uid_match.group(1)
        token = token_match.group(1)

    reset_response = client.post(
        '/api/auth/reset-password',
        data=json.dumps(
            {
                'uid': uid,
                'token': token,
                'new_password': 'NewPassword123!',
            }
        ),
        content_type='application/json',
    )

    assert reset_response.status_code == 200
    user = User.objects.get(email='reset@example.com')
    assert user.check_password('NewPassword123!') is True


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        'github': {
            'SCOPE': ['user:email'],
            'APPS': [{'client_id': 'github-client', 'secret': 'github-secret', 'key': ''}],
        },
        'google': {'SCOPE': ['profile', 'email']},
    }
)
def test_social_authorize_returns_provider_login_url():
    client = Client()

    response = client.get('/api/auth/social/github/authorize')

    assert response.status_code == 200
    payload = response.json()
    assert '/accounts/github/login/' in payload['authorization_url']
    assert 'process=login' in payload['authorization_url']
    assert payload['provider'] == 'github'


def test_social_exchange_returns_jwt_tokens():
    client = Client()
    user = User.objects.create_user(
        username='social@example.com',
        email='social@example.com',
        password='StrongPass123!',
        display_name='Social User',
    )
    code = AuthService.create_social_login_code(user, 'github')

    response = client.post(
        '/api/auth/social/exchange',
        data=json.dumps({'code': code}),
        content_type='application/json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert 'access' in payload
    assert 'refresh' in payload


def test_auth_me_returns_absolute_avatar_url():
    user = User.objects.create_user(
        username='avatar-me@example.com',
        email='avatar-me@example.com',
        password='StrongPass123!',
        display_name='Avatar Me',
        avatar_url='/media/avatars/1/test.png',
    )
    token = AuthService.get_tokens_for_user(user)['access']
    client = Client()

    response = client.get('/api/auth/me', HTTP_AUTHORIZATION=f'Bearer {token}')

    assert response.status_code == 200
    assert response.json()['avatar_url'].startswith('http://testserver/media/avatars/')
