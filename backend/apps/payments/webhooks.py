"""Stripe webhook handlers."""
import stripe
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from apps.payments.services import TransactionService
from apps.notifications.services import NotificationService

User = get_user_model()


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        _handle_checkout_completed(session)

    return HttpResponse(status=200)


def _handle_checkout_completed(session: dict):
    """Process completed checkout session — credit user balance."""
    user_id = session.get("client_reference_id")
    if not user_id:
        return

    try:
        user = User.objects.get(id=int(user_id))
    except (User.DoesNotExist, ValueError):
        return

    # amount_total is in cents
    amount_cents = session.get("amount_total", 0)
    amount = Decimal(amount_cents) / 100

    payment_intent = session.get("payment_intent", "")
    session_id = session.get("id", "")

    # Dedup + deposit inside one atomic block to prevent concurrent
    # Stripe webhook retries from crediting the user twice.
    from django.db import transaction, IntegrityError
    from django.core.cache import cache
    from apps.payments.models import Transaction

    # Use session_id as a cache-based idempotency key for payment methods
    # that don't produce a payment_intent (BACS, SEPA, etc.)
    if session_id:
        dedup_cache_key = f"stripe:checkout:{session_id}"
        if not cache.add(dedup_cache_key, 1, timeout=86400):
            return  # Already processing or processed

    try:
        with transaction.atomic():
            # Lock the user row to serialize concurrent webhook processing
            locked_user = User.objects.select_for_update().get(id=user.id)

            if payment_intent and Transaction.objects.filter(
                stripe_payment_intent=payment_intent
            ).exists():
                return  # Already processed

            TransactionService.record_deposit(
                locked_user, amount, stripe_payment_intent=payment_intent
            )
    except IntegrityError:
        return  # Concurrent insert — safe to ignore

    try:
        NotificationService.send(
            recipient=user,
            notification_type="deposit",
            title="充值成功",
            content=f"${amount} 已到账",
        )
    except Exception:
        pass  # Deposit succeeded; notification failure should not trigger Stripe retry

    # Check first-deposit invite reward
    if user.invited_by_id:
        from apps.accounts.tasks import check_first_deposit_reward
        check_first_deposit_reward.delay(user.id)
