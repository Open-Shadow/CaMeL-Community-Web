"""Payments API routes."""
from __future__ import annotations

import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.payments.services import PaymentError, PaymentsService, TransactionService
from apps.workshop.models import Article
from common.permissions import AuthBearer

router = Router(tags=["payments"], auth=AuthBearer())


# =============================================================================
# Schemas
# =============================================================================

class DepositInput(Schema):
    amount: float  # in dollars, e.g. 5.00


class CheckoutOutput(Schema):
    checkout_url: str
    session_id: str


class MessageOutput(Schema):
    message: str


class WalletOutput(Schema):
    balance: float
    frozen_balance: float
    income_total: float
    expense_total: float


class BalanceOutput(Schema):
    balance: float
    frozen_balance: float
    available: float


class TransactionOutput(Schema):
    id: int
    transaction_type: str
    amount: float
    balance_after: float
    reference_id: str
    description: str
    created_at: str


class TransactionListOutput(Schema):
    items: list[TransactionOutput]
    total: int
    limit: int
    offset: int


class IncomeSummaryOutput(Schema):
    total_income: float
    transaction_count: int


class SkillIncomeItemOutput(Schema):
    skill_id: int
    skill_name: str
    calls: int
    income: float
    avg_rating: float
    review_count: int


class SkillIncomeDashboardOutput(Schema):
    total_income: float
    total_calls: int
    skills: list[SkillIncomeItemOutput]


class TipInput(Schema):
    amount: float


class TipLeaderboardItemOutput(Schema):
    article_id: int
    article_title: str
    author_name: str
    total_tips: float


# =============================================================================
# Helpers
# =============================================================================

def _serialize_wallet(data: dict) -> dict:
    return {
        "balance": float(data["balance"]),
        "frozen_balance": float(data["frozen_balance"]),
        "income_total": float(data["income_total"]),
        "expense_total": float(data["expense_total"]),
    }


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/checkout", response={200: CheckoutOutput, 400: MessageOutput})
def create_stripe_checkout(request, data: DepositInput):
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


@router.post("/deposits", response={200: WalletOutput, 400: MessageOutput})
def create_deposit(request, data: DepositInput):
    """Create a direct deposit (e.g. after Stripe webhook confirms payment)."""
    try:
        PaymentsService.create_deposit(request.auth, data.amount, reference_id=f"manual-deposit:{request.auth.id}")
    except PaymentError as exc:
        return 400, {"message": str(exc)}
    wallet = PaymentsService.get_wallet_summary(request.auth)
    return _serialize_wallet(wallet)


@router.get("/wallet", response=WalletOutput)
def get_wallet(request):
    """Get current user wallet summary (balance, frozen, income, expense)."""
    return _serialize_wallet(PaymentsService.get_wallet_summary(request.auth))


@router.get("/balance", response=BalanceOutput)
def get_balance(request):
    """Get current user balance (simple view)."""
    return TransactionService.get_balance(request.auth)


@router.get("/transactions", response=TransactionListOutput)
def list_transactions(request, limit: int = 20, offset: int = 0):
    """List user transactions with pagination."""
    items, total = PaymentsService.list_transactions(request.auth, limit=limit, offset=offset)
    return {
        "items": [
            {
                "id": item.id,
                "transaction_type": item.transaction_type,
                "amount": float(item.amount),
                "balance_after": float(item.balance_after),
                "reference_id": item.reference_id,
                "description": item.description,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
        "total": total,
        "limit": min(max(limit, 1), 100),
        "offset": max(offset, 0),
    }


@router.get("/income-summary", response=IncomeSummaryOutput)
def get_income_summary(request):
    """Get income summary for creator dashboard."""
    return TransactionService.get_income_summary(request.auth)


@router.get("/skills/income", response=SkillIncomeDashboardOutput)
def get_skill_income_dashboard(request):
    """Get detailed skill income dashboard for creators."""
    dashboard = PaymentsService.get_skill_income_dashboard(request.auth)
    return {
        "total_income": float(dashboard["total_income"]),
        "total_calls": dashboard["total_calls"],
        "skills": [
            {
                **item,
                "income": float(item["income"]),
            }
            for item in dashboard["skills"]
        ],
    }


@router.post("/articles/{article_id}/tip", response={200: MessageOutput, 400: MessageOutput})
def tip_article(request, article_id: int, data: TipInput):
    """Tip an article author."""
    article = get_object_or_404(Article, id=article_id)
    try:
        PaymentsService.create_tip(request.auth, article, data.amount)
    except PaymentError as exc:
        return 400, {"message": str(exc)}
    return {"message": "打赏成功"}


@router.get("/tips/leaderboard", response=list[TipLeaderboardItemOutput])
def get_tip_leaderboard(request, limit: int = 10):
    """Get tip leaderboard by article."""
    return [
        {
            **item,
            "total_tips": float(item["total_tips"]),
        }
        for item in PaymentsService.get_tip_leaderboard(limit=limit)
    ]
