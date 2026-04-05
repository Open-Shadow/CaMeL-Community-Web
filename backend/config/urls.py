from django.contrib import admin
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
