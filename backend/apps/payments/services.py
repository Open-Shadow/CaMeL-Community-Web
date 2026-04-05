"""Payments business logic — TransactionService."""
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.payments.models import Transaction, TransactionType

User = get_user_model()


class TransactionService:
    """Service for managing transactions and user balances."""

    @classmethod
    @transaction.atomic
    def record_deposit(cls, user, amount: Decimal,
                       stripe_payment_intent: str = "") -> Transaction:
        """Record a deposit and add to user balance."""
        user = User.objects.select_for_update().get(id=user.id)
        user.balance += amount
        user.save(update_fields=["balance"])

        return Transaction.objects.create(
            user=user,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            balance_after=user.balance,
            stripe_payment_intent=stripe_payment_intent,
            description=f"充值 ${amount}",
        )

    @classmethod
    @transaction.atomic
    def deduct(cls, user, amount: Decimal, tx_type: str,
               description: str = "", reference_id: str = "") -> Transaction:
        """Deduct from user balance. Raises ValueError if insufficient."""
        user = User.objects.select_for_update().get(id=user.id)
        if user.balance < amount:
            raise ValueError("余额不足")

        user.balance -= amount
        user.save(update_fields=["balance"])

        return Transaction.objects.create(
            user=user,
            transaction_type=tx_type,
            amount=-amount,
            balance_after=user.balance,
            description=description,
            reference_id=reference_id,
        )

    @classmethod
    @transaction.atomic
    def credit(cls, user, amount: Decimal, tx_type: str,
               description: str = "", reference_id: str = "") -> Transaction:
        """Add to user balance (income)."""
        user = User.objects.select_for_update().get(id=user.id)
        user.balance += amount
        user.save(update_fields=["balance"])

        return Transaction.objects.create(
            user=user,
            transaction_type=tx_type,
            amount=amount,
            balance_after=user.balance,
            description=description,
            reference_id=reference_id,
        )

    @classmethod
    @transaction.atomic
    def freeze(cls, user, amount: Decimal, reference_id: str = "") -> Transaction:
        """Freeze balance for bounty escrow."""
        user = User.objects.select_for_update().get(id=user.id)
        if user.balance < amount:
            raise ValueError("余额不足")

        user.balance -= amount
        user.frozen_balance += amount
        user.save(update_fields=["balance", "frozen_balance"])

        return Transaction.objects.create(
            user=user,
            transaction_type=TransactionType.BOUNTY_ESCROW,
            amount=-amount,
            balance_after=user.balance,
            description=f"悬赏冻结 ${amount}",
            reference_id=reference_id,
        )

    @classmethod
    @transaction.atomic
    def unfreeze(cls, user, amount: Decimal, reference_id: str = "") -> Transaction:
        """Unfreeze balance (bounty cancelled)."""
        user = User.objects.select_for_update().get(id=user.id)
        user.frozen_balance -= amount
        user.balance += amount
        user.save(update_fields=["balance", "frozen_balance"])

        return Transaction.objects.create(
            user=user,
            transaction_type=TransactionType.BOUNTY_RELEASE,
            amount=amount,
            balance_after=user.balance,
            description=f"悬赏解冻 ${amount}",
            reference_id=reference_id,
        )

    @classmethod
    def get_balance(cls, user) -> dict:
        """Get user balance info."""
        return {
            "balance": float(user.balance),
            "frozen_balance": float(user.frozen_balance),
            "available": float(user.balance),
        }

    @classmethod
    def list_transactions(cls, user, limit: int = 20, offset: int = 0,
                          tx_type: str = ""):
        """List user transactions."""
        qs = Transaction.objects.filter(user=user)
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)
        return qs.order_by("-created_at")[offset:offset + limit]

    @classmethod
    def get_income_summary(cls, user) -> dict:
        """Get income summary for creator dashboard."""
        from django.db.models import Sum, Count

        income_types = [
            TransactionType.SKILL_INCOME,
            TransactionType.BOUNTY_INCOME,
            TransactionType.TIP_RECEIVE,
        ]
        qs = Transaction.objects.filter(user=user, transaction_type__in=income_types)

        total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        count = qs.aggregate(count=Count("id"))["count"] or 0

        return {
            "total_income": float(total),
            "transaction_count": count,
        }
