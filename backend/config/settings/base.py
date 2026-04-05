from celery.schedules import crontab
from decouple import config, Csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.postgres',
    # Third-party
    'ninja',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.mfa',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
    'rest_framework_simplejwt',
    'django_extensions',
    'storages',
    # Local apps
    'apps.accounts',
    'apps.skills',
    'apps.bounties',
    'apps.workshop',
    'apps.payments',
    'apps.credits',
    'apps.notifications',
    'apps.search',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='camel_db'),
        'USER': config('DB_USER', default='camel'),
        'PASSWORD': config('DB_PASSWORD', default='camel'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

AUTH_USER_MODEL = 'accounts.User'

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_ADAPTER = 'apps.accounts.adapters.AccountAdapter'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_SCHEDULE = {
    'refresh-skill-trending-cache': {
        'task': 'apps.skills.tasks.refresh_skill_trending_cache',
        'schedule': crontab(minute='0', hour='*/1'),
    },
    'refresh-skill-recommendation-cache': {
        'task': 'apps.skills.tasks.refresh_skill_recommendation_cache',
        'schedule': crontab(minute='15', hour='*/3'),
    },
    'refresh-article-recommendation-cache': {
        'task': 'apps.workshop.tasks.refresh_article_recommendation_cache',
        'schedule': crontab(minute='30', hour='*/3'),
    },
    'detect-outdated-articles': {
        'task': 'apps.workshop.tasks.detect_outdated_articles',
        'schedule': crontab(minute='0', hour='4'),
    },
    'auto-archive-stale-articles': {
        'task': 'apps.workshop.tasks.auto_archive_stale_articles',
        'schedule': crontab(minute='20', hour='4'),
    },
    'refresh-series-completion-rewards': {
        'task': 'apps.workshop.tasks.refresh_series_completion_rewards',
        'schedule': crontab(minute='40', hour='4'),
    },
    'cleanup-workshop-data': {
        'task': 'apps.workshop.tasks.cleanup_workshop_data',
        'schedule': crontab(minute='0', hour='5'),
    },
    'optimize-search-indexes': {
        'task': 'apps.search.tasks.optimize_search_indexes',
        'schedule': crontab(minute='10', hour='5'),
    },
}

# JWT
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Meilisearch
MEILISEARCH_URL = config('MEILISEARCH_URL', default='http://localhost:7700')
MEILISEARCH_KEY = config('MEILISEARCH_KEY', default='masterKey')

# Stripe
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# Sentry
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN)

# Email
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@camel.local')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)

# Frontend auth URLs
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')
FRONTEND_EMAIL_VERIFY_URL = config(
    'FRONTEND_EMAIL_VERIFY_URL',
    default=f'{FRONTEND_URL}/verify-email?key={{key}}',
)
FRONTEND_PASSWORD_RESET_URL = config(
    'FRONTEND_PASSWORD_RESET_URL',
    default=f'{FRONTEND_URL}/reset-password?uid={{uid}}&token={{token}}',
)
FRONTEND_SOCIAL_CALLBACK_URL = config(
    'FRONTEND_SOCIAL_CALLBACK_URL',
    default=f'{FRONTEND_URL}/auth/social/callback',
)

# OAuth
GITHUB_CLIENT_ID = config('GITHUB_CLIENT_ID', default='')
GITHUB_CLIENT_SECRET = config('GITHUB_CLIENT_SECRET', default='')
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': ['user:email'],
    },
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    },
}

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['github']['APPS'] = [
        {
            'client_id': GITHUB_CLIENT_ID,
            'secret': GITHUB_CLIENT_SECRET,
            'key': '',
        }
    ]

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APPS'] = [
        {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': '',
        }
    ]
