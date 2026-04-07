from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from apps.accounts.views import social_login_bridge, social_login_error
from config.api import api
from apps.payments.webhooks import stripe_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/social/bridge/', social_login_bridge, name='accounts-social-bridge'),
    path('accounts/social/error/', social_login_error, name='accounts-social-error'),
    path('api/', api.urls),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
]

# Serve user-uploaded files in local development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
