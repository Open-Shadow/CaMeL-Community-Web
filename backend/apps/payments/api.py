"""Payments API routes."""
from __future__ import annotations

from ninja import Router, Schema
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404

from apps.payments.services import PaymentError, PaymentsService
from apps.workshop.models import Article
from common.permissions import AuthBearer

router = Router(tags=["payments"], auth=AuthBearer())


class DepositInput(Schema):
    amount: float


class MessageOutput(Schema):
    message: str


class WalletOutput(Schema):
    balance: float
    frozen_balance: float
    income_total: float
    expense_total: float


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


def _serialize_wallet(data: dict) -> dict:
    return {
        "balance": float(data["balance"]),
        "frozen_balance": float(data["frozen_balance"]),
        "income_total": float(data["income_total"]),
        "expense_total": float(data["expense_total"]),
    }


@router.post("/deposits", response={200: WalletOutput, 400: MessageOutput})
def create_deposit(request, data: DepositInput):
    try:
        PaymentsService.create_deposit(request.auth, data.amount, reference_id=f"manual-deposit:{request.auth.id}")
    except PaymentError as exc:
        return 400, {"message": str(exc)}
    wallet = PaymentsService.get_wallet_summary(request.auth)
    return _serialize_wallet(wallet)


@router.get("/wallet", response=WalletOutput)
def get_wallet(request):
    return _serialize_wallet(PaymentsService.get_wallet_summary(request.auth))


@router.get("/transactions", response=TransactionListOutput)
def list_transactions(request, limit: int = 20, offset: int = 0):
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


@router.get("/skills/income", response=SkillIncomeDashboardOutput)
def get_skill_income_dashboard(request):
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
    article = get_object_or_404(Article, id=article_id)
    try:
        PaymentsService.create_tip(request.auth, article, data.amount)
    except PaymentError as exc:
        return 400, {"message": str(exc)}
    return {"message": "打赏成功"}


@router.get("/tips/leaderboard", response=list[TipLeaderboardItemOutput])
def get_tip_leaderboard(request, limit: int = 10):
    return [
        {
            **item,
            "total_tips": float(item["total_tips"]),
        }
        for item in PaymentsService.get_tip_leaderboard(limit=limit)
    ]
