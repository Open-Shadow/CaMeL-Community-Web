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

    # Prevent duplicate processing — skip empty payment_intent to avoid
    # matching all transactions with blank stripe_payment_intent field.
    from apps.payments.models import Transaction
    if payment_intent and Transaction.objects.filter(stripe_payment_intent=payment_intent).exists():
        return

    TransactionService.record_deposit(
        user, amount, stripe_payment_intent=payment_intent
    )

    NotificationService.send(
        recipient=user,
        notification_type="deposit",
        title="充值成功",
        content=f"${amount} 已到账",
    )

    # Check first-deposit invite reward
    if user.invited_by_id:
        from apps.accounts.tasks import check_first_deposit_reward
        check_first_deposit_reward.delay(user.id)
