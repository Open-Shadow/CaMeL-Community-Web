"""Payments business logic — shared quota (users.quota) + frozen (community_profiles)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum, Count

from apps.accounts.models import CamelUser, CommunityProfile, get_or_create_profile
from apps.credits.models import CreditAction
from apps.credits.services import CreditService
from apps.payments.models import Transaction, TransactionType
from apps.workshop.models import Article, Tip
from common.quota_service import QuotaService, QUOTA_PER_DOLLAR

PLATFORM_FEE_RATE = Decimal("0.15")
APPEAL_FEE = Decimal("0.50")


def quantize_amount(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quota_to_usd(quota: int) -> Decimal:
    return Decimal(quota) / Decimal(QUOTA_PER_DOLLAR)


class PaymentError(ValueError):
    """Raised when a balance operation cannot be completed."""


class TransactionService:
    """Legacy service for managing transactions and user balances.

    Retained for backward compatibility. For new code, prefer PaymentsService.
    """

    @classmethod
    @transaction.atomic
    def record_deposit(cls, user, amount: Decimal,
                       stripe_payment_intent: str = "") -> Transaction:
        """Record a deposit and add to user balance via QuotaService."""
        new_quota = QuotaService.add_usd(user.id, amount)
        balance_after = _quota_to_usd(new_quota)

        return Transaction.objects.create(
            user=user,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            balance_after=balance_after,
            stripe_payment_intent=stripe_payment_intent,
            description=f"充值 ${amount}",
        )

    @classmethod
    @transaction.atomic
    def deduct(cls, user, amount: Decimal, tx_type: str,
               description: str = "", reference_id: str = "") -> Transaction:
        """Deduct from user balance via QuotaService. Raises QuotaError if insufficient."""
        new_quota = QuotaService.deduct_usd(user.id, amount)
        balance_after = _quota_to_usd(new_quota)

        return Transaction.objects.create(
            user=user,
            transaction_type=tx_type,
            amount=-amount,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
        )

    @classmethod
    @transaction.atomic
    def credit(cls, user, amount: Decimal, tx_type: str,
               description: str = "", reference_id: str = "") -> Transaction:
        """Add to user balance (income) via QuotaService."""
        new_quota = QuotaService.add_usd(user.id, amount)
        balance_after = _quota_to_usd(new_quota)

        return Transaction.objects.create(
            user=user,
            transaction_type=tx_type,
            amount=amount,
            balance_after=balance_after,
            description=description,
            reference_id=reference_id,
        )

    @classmethod
    @transaction.atomic
    def freeze(cls, user, amount: Decimal, reference_id: str = "") -> Transaction:
        """Freeze balance for bounty escrow: deduct from users.quota, add to community_profiles.frozen_balance."""
        quota_units = QuotaService.usd_to_quota(amount)
        new_quota = QuotaService.deduct_quota(user.id, quota_units)
        balance_after = _quota_to_usd(new_quota)

        profile = get_or_create_profile(user)
        CommunityProfile.objects.filter(user_id=user.id).update(
            frozen_balance=profile.frozen_balance + quota_units
        )

        return Transaction.objects.create(
            user=user,
            transaction_type=TransactionType.BOUNTY_ESCROW,
            amount=-amount,
            balance_after=balance_after,
            description=f"悬赏冻结 ${amount}",
            reference_id=reference_id,
        )

    @classmethod
    @transaction.atomic
    def unfreeze(cls, user, amount: Decimal, reference_id: str = "") -> Transaction:
        """Unfreeze balance (bounty cancelled): release from frozen to users.quota."""
        quota_units = QuotaService.usd_to_quota(amount)
        profile = get_or_create_profile(user)
        if profile.frozen_balance < quota_units:
            raise PaymentError("冻结余额不足")

        CommunityProfile.objects.filter(user_id=user.id).update(
            frozen_balance=profile.frozen_balance - quota_units
        )
        new_quota = QuotaService.add_quota(user.id, quota_units)
        balance_after = _quota_to_usd(new_quota)

        return Transaction.objects.create(
            user=user,
            transaction_type=TransactionType.BOUNTY_RELEASE,
            amount=amount,
            balance_after=balance_after,
            description=f"悬赏解冻 ${amount}",
            reference_id=reference_id,
        )

    @classmethod
    def get_balance(cls, user) -> dict:
        """Get user balance info."""
        user.refresh_from_db(fields=["quota"])
        profile = get_or_create_profile(user)
        balance_usd = _quota_to_usd(user.quota)
        frozen_usd = _quota_to_usd(profile.frozen_balance)
        return {
            "balance": float(balance_usd),
            "frozen_balance": float(frozen_usd),
            "available": float(balance_usd),
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
    """Shared wallet, transaction, payout and tipping helpers.

    All balance operations go through QuotaService (atomic SQL on users.quota).
    Frozen balance is stored in community_profiles.frozen_balance.
    """

    @staticmethod
    def _create_transaction(
        user: CamelUser,
        transaction_type: str,
        amount: Decimal,
        *,
        reference_id: str = "",
        description: str = "",
        stripe_payment_intent: str = "",
        balance_after_quota: int | None = None,
    ) -> Transaction:
        if balance_after_quota is not None:
            bal = _quota_to_usd(balance_after_quota)
        else:
            user.refresh_from_db(fields=["quota"])
            bal = _quota_to_usd(user.quota)
        return Transaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=quantize_amount(amount),
            balance_after=bal,
            reference_id=reference_id,
            description=description,
            stripe_payment_intent=stripe_payment_intent,
        )

    @staticmethod
    @transaction.atomic
    def create_deposit(user: CamelUser, amount: Decimal | float | int | str, *, reference_id: str = "") -> Decimal:
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            raise PaymentError("充值金额必须大于 0")

        new_quota = QuotaService.add_usd(user.id, normalized_amount)
        PaymentsService._create_transaction(
            user,
            TransactionType.DEPOSIT,
            normalized_amount,
            reference_id=reference_id,
            description="账户充值",
            balance_after_quota=new_quota,
        )
        return normalized_amount

    @staticmethod
    def list_transactions(user: CamelUser, *, limit: int = 20, offset: int = 0):
        safe_limit = min(max(limit, 1), 100)
        safe_offset = max(offset, 0)
        queryset = user.transactions.order_by("-created_at")
        return queryset[safe_offset:safe_offset + safe_limit], queryset.count()

    @staticmethod
    def get_wallet_summary(user: CamelUser) -> dict:
        user.refresh_from_db(fields=["quota"])
        profile = get_or_create_profile(user)
        balance_usd = _quota_to_usd(user.quota)
        frozen_usd = _quota_to_usd(profile.frozen_balance)

        transactions = user.transactions.all()
        income = transactions.filter(amount__gt=0).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense = transactions.filter(amount__lt=0).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        return {
            "balance": quantize_amount(balance_usd),
            "frozen_balance": quantize_amount(frozen_usd),
            "income_total": quantize_amount(income),
            "expense_total": quantize_amount(abs(expense)),
        }

    @staticmethod
    @transaction.atomic
    def reserve_bounty_escrow(user: CamelUser, amount: Decimal | float | int | str, *, reference_id: str) -> Decimal:
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            raise PaymentError("托管金额必须大于 0")

        quota_units = QuotaService.usd_to_quota(normalized_amount)
        new_quota = QuotaService.deduct_quota(user.id, quota_units)

        profile = get_or_create_profile(user)
        CommunityProfile.objects.filter(user_id=user.id).update(
            frozen_balance=profile.frozen_balance + quota_units
        )

        PaymentsService._create_transaction(
            user,
            TransactionType.BOUNTY_ESCROW,
            -normalized_amount,
            reference_id=reference_id,
            description="悬赏托管冻结",
            balance_after_quota=new_quota,
        )
        return normalized_amount

    @staticmethod
    @transaction.atomic
    def release_bounty_to_creator(user: CamelUser, amount: Decimal | float | int | str, *, reference_id: str) -> Decimal:
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            return Decimal("0.00")

        quota_units = QuotaService.usd_to_quota(normalized_amount)
        profile = get_or_create_profile(user)
        if profile.frozen_balance < quota_units:
            raise PaymentError("冻结余额不足，无法释放")

        CommunityProfile.objects.filter(user_id=user.id).update(
            frozen_balance=profile.frozen_balance - quota_units
        )
        new_quota = QuotaService.add_quota(user.id, quota_units)

        PaymentsService._create_transaction(
            user,
            TransactionType.BOUNTY_RELEASE,
            normalized_amount,
            reference_id=reference_id,
            description="悬赏金额退回",
            balance_after_quota=new_quota,
        )
        return normalized_amount

    @staticmethod
    @transaction.atomic
    def settle_bounty_payout(
        creator: CamelUser,
        hunter: CamelUser,
        amount: Decimal | float | int | str,
        *,
        reference_id: str,
    ) -> Decimal:
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            return Decimal("0.00")

        quota_units = QuotaService.usd_to_quota(normalized_amount)
        profile = get_or_create_profile(creator)
        if profile.frozen_balance < quota_units:
            raise PaymentError("冻结余额不足，无法结算")

        # Release from creator's frozen balance and add to hunter's quota
        CommunityProfile.objects.filter(user_id=creator.id).update(
            frozen_balance=profile.frozen_balance - quota_units
        )
        hunter_new_quota = QuotaService.add_quota(hunter.id, quota_units)

        creator.refresh_from_db(fields=["quota"])
        PaymentsService._create_transaction(
            creator,
            TransactionType.BOUNTY_RELEASE,
            Decimal("0.00"),
            reference_id=reference_id,
            description="悬赏金额已结算给接单者",
        )
        PaymentsService._create_transaction(
            hunter,
            TransactionType.BOUNTY_INCOME,
            normalized_amount,
            reference_id=reference_id,
            description="悬赏收入到账",
            balance_after_quota=hunter_new_quota,
        )
        return normalized_amount

    @staticmethod
    @transaction.atomic
    def charge_skill_call(caller: CamelUser, creator: CamelUser, *, price: Decimal | float | int | str, reference_id: str) -> dict:
        normalized_price = quantize_amount(price)
        if normalized_price <= 0:
            return {
                "charged_amount": Decimal("0.00"),
                "creator_income": Decimal("0.00"),
                "platform_fee": Decimal("0.00"),
            }

        discount_rate = Decimal(str(CreditService.get_discount_rate(caller)))
        charged_amount = quantize_amount(normalized_price * discount_rate)
        platform_fee = quantize_amount(charged_amount * PLATFORM_FEE_RATE)
        creator_income = quantize_amount(charged_amount - platform_fee)

        # Deduct from caller, add to creator (net of platform fee)
        caller_quota = QuotaService.deduct_usd(caller.id, charged_amount)
        creator_quota = QuotaService.add_usd(creator.id, creator_income)

        PaymentsService._create_transaction(
            caller,
            TransactionType.SKILL_PURCHASE,
            -charged_amount,
            reference_id=reference_id,
            description="Skill 调用扣费",
            balance_after_quota=caller_quota,
        )
        PaymentsService._create_transaction(
            creator,
            TransactionType.SKILL_INCOME,
            creator_income,
            reference_id=reference_id,
            description="Skill 调用收入",
            balance_after_quota=creator_quota,
        )
        PaymentsService._create_transaction(
            caller,
            TransactionType.PLATFORM_FEE,
            -platform_fee,
            reference_id=reference_id,
            description="Skill 调用平台手续费",
            balance_after_quota=caller_quota,
        )
        return {
            "charged_amount": charged_amount,
            "creator_income": creator_income,
            "platform_fee": platform_fee,
        }

    @staticmethod
    @transaction.atomic
    def create_tip(tipper: CamelUser, article: Article, amount: Decimal | float | int | str) -> Tip:
        normalized_amount = quantize_amount(amount)
        if normalized_amount <= 0:
            raise PaymentError("打赏金额必须大于 0")
        if article.author_id == tipper.id:
            raise PaymentError("不能给自己的文章打赏")

        # Deduct from tipper, add to recipient
        tipper_quota = QuotaService.deduct_usd(tipper.id, normalized_amount)
        recipient = article.author
        recipient_quota = QuotaService.add_usd(recipient.id, normalized_amount)

        article.total_tips = quantize_amount(article.total_tips + normalized_amount)
        article.save(update_fields=["total_tips"])

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
            balance_after_quota=tipper_quota,
        )
        PaymentsService._create_transaction(
            recipient,
            TransactionType.TIP_RECEIVE,
            normalized_amount,
            reference_id=f"tip:{tip.id}",
            description=f"收到文章《{article.title}》打赏",
            balance_after_quota=recipient_quota,
        )
        CreditService.add_credit(tipper, CreditAction.TIP_GIVEN, str(tip.id))
        return tip

    @staticmethod
    def get_skill_income_dashboard(user: CamelUser) -> dict:
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
    def charge_appeal_fee(user: CamelUser, *, reference_id: str) -> Decimal:
        new_quota = QuotaService.deduct_usd(user.id, APPEAL_FEE)

        PaymentsService._create_transaction(
            user,
            TransactionType.PLATFORM_FEE,
            -APPEAL_FEE,
            reference_id=reference_id,
            description="仲裁上诉费",
            balance_after_quota=new_quota,
        )
        return APPEAL_FEE
