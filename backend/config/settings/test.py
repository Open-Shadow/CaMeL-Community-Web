"""Test settings - uses SQLite to avoid PostgreSQL dependency."""
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
