"""Payments API routes."""
import stripe
from ninja import Router, Schema
from django.conf import settings

from common.permissions import AuthBearer
from apps.payments.services import TransactionService

router = Router(tags=["payments"])


# =============================================================================
# Schemas
# =============================================================================

class DepositInput(Schema):
    amount: float  # in dollars, e.g. 5.00


class CheckoutOutput(Schema):
    checkout_url: str
    session_id: str


class BalanceOutput(Schema):
    balance: float
    frozen_balance: float
    available: float


class TransactionOutput(Schema):
    id: int
    transaction_type: str
    amount: float
    balance_after: float
    description: str
    reference_id: str
    created_at: str


class IncomeSummaryOutput(Schema):
    total_income: float
    transaction_count: int


class MessageOutput(Schema):
    message: str


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/deposit", response={200: CheckoutOutput, 400: MessageOutput},
             auth=AuthBearer())
def create_deposit(request, data: DepositInput):
    """Create Stripe Checkout session for deposit."""
    if data.amount < 1.0:
        return 400, {"message": "最低充值 $1.00"}
    if data.amount > 500.0:
        return 400, {"message": "单次最高充值 $500.00"}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    frontend_url = settings.FRONTEND_URL

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "CaMeL Community 充值"},
                    "unit_amount": int(data.amount * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            client_reference_id=str(request.auth.id),
            success_url=f"{frontend_url}/wallet?status=success",
            cancel_url=f"{frontend_url}/wallet?status=cancelled",
        )
        return 200, {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        return 400, {"message": f"支付服务错误: {str(e)}"}


@router.get("/balance", response=BalanceOutput, auth=AuthBearer())
def get_balance(request):
    """Get current user balance."""
    return TransactionService.get_balance(request.auth)


@router.get("/transactions", response=list[TransactionOutput], auth=AuthBearer())
def list_transactions(request, limit: int = 20, offset: int = 0,
                      tx_type: str = ""):
    """List user transactions."""
    txs = TransactionService.list_transactions(
        request.auth, limit=limit, offset=offset, tx_type=tx_type
    )
    return [
        {
            "id": tx.id,
            "transaction_type": tx.get_transaction_type_display(),
            "amount": float(tx.amount),
            "balance_after": float(tx.balance_after),
            "description": tx.description,
            "reference_id": tx.reference_id,
            "created_at": tx.created_at.isoformat(),
        }
        for tx in txs
    ]


@router.get("/income-summary", response=IncomeSummaryOutput, auth=AuthBearer())
def get_income_summary(request):
    """Get income summary for creator dashboard."""
    return TransactionService.get_income_summary(request.auth)
