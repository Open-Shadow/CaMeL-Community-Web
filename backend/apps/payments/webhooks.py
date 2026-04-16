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
    from apps.payments.models import Transaction

    try:
        with transaction.atomic():
            # Lock the user row to serialize concurrent webhook processing
            locked_user = User.objects.select_for_update().get(id=user.id)

            if payment_intent and Transaction.objects.filter(
                stripe_payment_intent=payment_intent
            ).exists():
                return  # Already processed

            # For payment methods without a payment_intent (BACS, SEPA, etc.),
            # deduplicate by session_id stored as reference_id.
            if not payment_intent and session_id and Transaction.objects.filter(
                reference_id=f"stripe_session:{session_id}"
            ).exists():
                return  # Already processed

            ref_id = f"stripe_session:{session_id}" if session_id else ""
            TransactionService.record_deposit(
                locked_user, amount,
                stripe_payment_intent=payment_intent,
                reference_id=ref_id,
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
