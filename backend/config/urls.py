from django.contrib import admin
from django.urls import path, include
from config.api import api
from apps.payments.webhooks import stripe_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api/', api.urls),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
]
