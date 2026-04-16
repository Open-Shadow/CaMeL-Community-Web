"""Payments business logic."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import F, Sum, Count

from apps.accounts.models import User
from apps.credits.models import CreditAction
from apps.credits.services import CreditService
from apps.payments.models import Transaction, TransactionType
from apps.workshop.models import Article, Tip

PLATFORM_FEE_RATE = Decimal("0.15")
APPEAL_FEE = Decimal("0.50")


def quantize_amount(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PaymentError(ValueError):
    """Raised when a balance operation cannot be completed."""


class TransactionService:
    """Legacy service for managing transactions and user balances.

    Retained for backward compatibility. For new code, prefer PaymentsService.
    """

    @classmethod
    @transaction.atomic
    def record_deposit(cls, user, amount: Decimal,
                       stripe_payment_intent: str = "",
                       reference_id: str = "") -> Transaction:
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
            reference_id=reference_id,
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


class PaymentsService:
    """Shared wallet, transaction, payout and tipping helpers."""

    @staticmethod
    def _create_transaction(
        user: User,
        transaction_type: str,
        amount: Decimal,
        *,
        reference_id: str = "",
        description: str = "",
        stripe_payment_intent: str = "",
    ) -> Transaction:
        return Transaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=quantize_amount(amount),
            balance_after=user.balance,
            reference_id=reference_id,
            description=description,
            stripe_payment_intent=stripe_payment_intent,
        )

    @staticmethod
    @transaction.atomic
    def create_deposit(user: User, amount: Decimal | float | int | str, *, reference_id: str = "") -> Decimal:
        user = User.objects.select_for_update().get(id=user.id)
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            raise PaymentError("充值金额必须大于 0")

        user.balance = quantize_amount(user.balance + normalized_amount)
        user.save(update_fields=["balance"])
        PaymentsService._create_transaction(
            user,
            TransactionType.DEPOSIT,
            normalized_amount,
            reference_id=reference_id,
            description="账户充值",
        )
        return normalized_amount

    @staticmethod
    def list_transactions(user: User, *, limit: int = 20, offset: int = 0):
        safe_limit = min(max(limit, 1), 100)
        safe_offset = max(offset, 0)
        queryset = user.transactions.order_by("-created_at")
        return queryset[safe_offset:safe_offset + safe_limit], queryset.count()

    @staticmethod
    def get_wallet_summary(user: User) -> dict:
        transactions = user.transactions.all()
        income = transactions.filter(amount__gt=0).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense = transactions.filter(amount__lt=0).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        return {
            "balance": quantize_amount(user.balance),
            "frozen_balance": quantize_amount(user.frozen_balance),
            "income_total": quantize_amount(income),
            "expense_total": quantize_amount(abs(expense)),
        }

    @staticmethod
    @transaction.atomic
    def reserve_bounty_escrow(user: User, amount: Decimal | float | int | str, *, reference_id: str) -> Decimal:
        user = User.objects.select_for_update().get(id=user.id)
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            raise PaymentError("托管金额必须大于 0")
        if user.balance < normalized_amount:
            raise PaymentError("余额不足，无法托管悬赏金额")

        user.balance = quantize_amount(user.balance - normalized_amount)
        user.frozen_balance = quantize_amount(user.frozen_balance + normalized_amount)
        user.save(update_fields=["balance", "frozen_balance"])
        PaymentsService._create_transaction(
            user,
            TransactionType.BOUNTY_ESCROW,
            -normalized_amount,
            reference_id=reference_id,
            description="悬赏托管冻结",
        )
        return normalized_amount

    @staticmethod
    @transaction.atomic
    def release_bounty_to_creator(user: User, amount: Decimal | float | int | str, *, reference_id: str) -> Decimal:
        user = User.objects.select_for_update().get(id=user.id)
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            return Decimal("0.00")
        if user.frozen_balance < normalized_amount:
            raise PaymentError("冻结余额不足，无法释放")

        user.frozen_balance = quantize_amount(user.frozen_balance - normalized_amount)
        user.balance = quantize_amount(user.balance + normalized_amount)
        user.save(update_fields=["balance", "frozen_balance"])
        PaymentsService._create_transaction(
            user,
            TransactionType.BOUNTY_RELEASE,
            normalized_amount,
            reference_id=reference_id,
            description="悬赏金额退回",
        )
        return normalized_amount

    @staticmethod
    @transaction.atomic
    def settle_bounty_payout(
        creator: User,
        hunter: User,
        amount: Decimal | float | int | str,
        *,
        reference_id: str,
    ) -> Decimal:
        creator = User.objects.select_for_update().get(id=creator.id)
        hunter = User.objects.select_for_update().get(id=hunter.id)
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            return Decimal("0.00")
        if creator.frozen_balance < normalized_amount:
            raise PaymentError("冻结余额不足，无法结算")

        creator.frozen_balance = quantize_amount(creator.frozen_balance - normalized_amount)
        creator.save(update_fields=["frozen_balance"])

        hunter.balance = quantize_amount(hunter.balance + normalized_amount)
        hunter.save(update_fields=["balance"])

        PaymentsService._create_transaction(
            creator,
            TransactionType.BOUNTY_RELEASE,
            -normalized_amount,
            reference_id=reference_id,
            description="悬赏金额已结算给接单者",
        )
        PaymentsService._create_transaction(
            hunter,
            TransactionType.BOUNTY_INCOME,
            normalized_amount,
            reference_id=reference_id,
            description="悬赏收入到账",
        )
        return normalized_amount

    @staticmethod
    @transaction.atomic
    def charge_skill_call(caller: User, creator: User, *, price: Decimal | float | int | str, reference_id: str) -> dict:
        caller = User.objects.select_for_update().get(id=caller.id)
        creator = User.objects.select_for_update().get(id=creator.id)
        normalized_price = quantize_amount(price)
        if normalized_price <= 0:
            return {
                "charged_amount": Decimal("0.00"),
                "creator_income": Decimal("0.00"),
                "platform_fee": Decimal("0.00"),
            }

        discount_rate = Decimal(str(CreditService.get_discount_rate(caller)))
        charged_amount = quantize_amount(normalized_price * discount_rate)
        if caller.balance < charged_amount:
            raise PaymentError("余额不足，请先充值")

        platform_fee = quantize_amount(charged_amount * PLATFORM_FEE_RATE)
        creator_income = quantize_amount(charged_amount - platform_fee)

        caller.balance = quantize_amount(caller.balance - charged_amount)
        caller.save(update_fields=["balance"])

        creator.balance = quantize_amount(creator.balance + creator_income)
        creator.save(update_fields=["balance"])

        PaymentsService._create_transaction(
            caller,
            TransactionType.SKILL_PURCHASE,
            -charged_amount,
            reference_id=reference_id,
            description="Skill 调用扣费",
        )
        PaymentsService._create_transaction(
            creator,
            TransactionType.SKILL_INCOME,
            creator_income,
            reference_id=reference_id,
            description="Skill 调用收入",
        )
        PaymentsService._create_transaction(
            caller,
            TransactionType.PLATFORM_FEE,
            -platform_fee,
            reference_id=reference_id,
            description="Skill 调用平台手续费",
        )
        return {
            "charged_amount": charged_amount,
            "creator_income": creator_income,
            "platform_fee": platform_fee,
        }

    @staticmethod
    @transaction.atomic
    def create_tip(tipper: User, article: Article, amount: Decimal | float | int | str) -> Tip:
        tipper = User.objects.select_for_update().get(id=tipper.id)
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            raise PaymentError("打赏金额必须大于 0")
        if article.author_id == tipper.id:
            raise PaymentError("不能给自己的文章打赏")
        if tipper.balance < normalized_amount:
            raise PaymentError("余额不足，无法完成打赏")

        recipient = User.objects.select_for_update().get(id=article.author_id)
        tipper.balance = quantize_amount(tipper.balance - normalized_amount)
        tipper.save(update_fields=["balance"])

        recipient.balance = quantize_amount(recipient.balance + normalized_amount)
        recipient.save(update_fields=["balance"])

        Article.objects.filter(id=article.id).update(
            total_tips=F("total_tips") + normalized_amount
        )

        tip = Tip.objects.create(
            article=article,
            tipper=tipper,
            recipient=recipient,
            amount=normalized_amount,
        )

        PaymentsService._create_transaction(
            tipper,
            TransactionType.TIP_SEND,
            -normalized_amount,
            reference_id=f"tip:{tip.id}",
            description=f"打赏文章《{article.title}》",
        )
        PaymentsService._create_transaction(
            recipient,
            TransactionType.TIP_RECEIVE,
            normalized_amount,
            reference_id=f"tip:{tip.id}",
            description=f"收到文章《{article.title}》打赏",
        )
        CreditService.add_credit(tipper, CreditAction.TIP_GIVEN, str(tip.id))
        return tip

    @staticmethod
    def get_skill_income_dashboard(user: User) -> dict:
        skill_items = []
        total_income = Decimal("0")
        total_calls = 0

        for skill in user.skills.all().order_by("-total_calls", "-updated_at"):
            income = (
                user.transactions.filter(
                    transaction_type=TransactionType.SKILL_INCOME,
                    reference_id__startswith=f"skill:{skill.id}:",
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )
            total_income += income
            total_calls += skill.total_calls
            skill_items.append(
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "calls": skill.total_calls,
                    "income": quantize_amount(income),
                    "avg_rating": float(skill.avg_rating),
                    "review_count": skill.review_count,
                }
            )

        return {
            "total_income": quantize_amount(total_income),
            "total_calls": total_calls,
            "skills": skill_items,
        }

    @staticmethod
    def get_tip_leaderboard(limit: int = 10) -> list[dict]:
        safe_limit = min(max(limit, 1), 50)
        articles = (
            Article.objects.filter(total_tips__gt=0)
            .select_related("author")
            .order_by("-total_tips", "-published_at", "-created_at")[:safe_limit]
        )
        return [
            {
                "article_id": article.id,
                "article_title": article.title,
                "author_name": article.author.display_name or article.author.username,
                "total_tips": quantize_amount(article.total_tips),
            }
            for article in articles
        ]

    @staticmethod
    @transaction.atomic
    def charge_appeal_fee(user: User, *, reference_id: str) -> Decimal:
        user = User.objects.select_for_update().get(id=user.id)
        if user.balance < APPEAL_FEE:
            raise PaymentError("余额不足，无法支付上诉费")

        user.balance = quantize_amount(user.balance - APPEAL_FEE)
        user.save(update_fields=["balance"])
        PaymentsService._create_transaction(
            user,
            TransactionType.PLATFORM_FEE,
            -APPEAL_FEE,
            reference_id=reference_id,
            description="仲裁上诉费",
        )
        return APPEAL_FEE
