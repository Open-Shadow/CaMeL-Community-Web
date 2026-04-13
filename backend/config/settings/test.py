"""Test settings - uses SQLite to avoid PostgreSQL dependency."""
import json

from config.settings.base import *  # noqa

# Override SECRET_KEY for tests
SECRET_KEY = 'test-secret-key-for-testing-only'

# Use SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable postgres-specific features
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django.contrib.postgres']

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Run Celery tasks synchronously in tests (no Redis broker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

from django.contrib.postgres.fields import ArrayField  # noqa: E402


def _sqlite_array_db_type(self, connection):
    return "text"


ArrayField.db_type = _sqlite_array_db_type
ArrayField.cast_db_type = _sqlite_array_db_type


def _sqlite_array_placeholder(self, value, compiler, connection):
    return "%s"


ArrayField.get_placeholder = _sqlite_array_placeholder


def _sqlite_array_get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _sqlite_array_from_db_value(self, value, expression, connection):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


ArrayField.get_db_prep_value = _sqlite_array_get_db_prep_value
ArrayField.from_db_value = _sqlite_array_from_db_value
ArrayField.to_python = lambda self, value: _sqlite_array_from_db_value(self, value, None, None)
