"""Test settings for local regression runs against the standard Postgres stack."""

from config.settings.base import *  # noqa

# Override SECRET_KEY for tests
SECRET_KEY = 'test-secret-key-for-testing-only'

# Disable cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
AUTH_EMAIL_SEND_ASYNC = False

# Run Celery tasks synchronously in tests (no Redis broker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
