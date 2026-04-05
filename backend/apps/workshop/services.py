"""Workshop business logic — TipService."""
from decimal import Decimal
from django.db import transaction
from django.core.cache import cache

from apps.workshop.models import Tip, Article
from apps.payments.models import TransactionType
from apps.payments.services import TransactionService
from apps.credits.services import CreditService
from apps.credits.models import CreditAction
from apps.notifications.services import NotificationService

PLATFORM_FEE_RATE = Decimal("0.05")  # 5% platform fee


class TipService:

    @classmethod
    @transaction.atomic
    def send_tip(cls, tipper, article_id: int, amount: Decimal) -> Tip:
        """Send a tip: deduct from tipper, credit recipient, record tip."""
        if amount < Decimal("0.01"):
            raise ValueError("打赏金额不能低于 $0.01")

        try:
            article = Article.objects.select_related("author").get(
                id=article_id, status="PUBLISHED"
            )
        except Article.DoesNotExist:
            raise ValueError("文章不存在")

        recipient = article.author
        if tipper.id == recipient.id:
            raise ValueError("不能打赏自己的文章")

        fee = (amount * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
        recipient_amount = amount - fee

        # Deduct from tipper
        TransactionService.deduct(
            tipper, amount, TransactionType.TIP_SEND,
            description=f"打赏《{article.title[:30]}》",
            reference_id=str(article_id),
        )

        # Credit recipient
        TransactionService.credit(
            recipient, recipient_amount, TransactionType.TIP_RECEIVE,
            description=f"收到打赏《{article.title[:30]}》",
            reference_id=str(article_id),
        )

        # Update article total_tips
        Article.objects.filter(id=article_id).update(
            total_tips=article.total_tips + amount
        )

        # Credit score for tipper
        CreditService.add_credit(tipper, CreditAction.TIP_GIVEN,
                                 reference_id=str(article_id))

        # Notify recipient
        NotificationService.send(
            recipient=recipient,
            notification_type="tip_received",
            title="收到打赏",
            content=f"{tipper.display_name or tipper.email} 打赏了您的文章《{article.title[:30]}》${amount}",
            reference_id=str(article_id),
        )

        return Tip.objects.create(
            article=article,
            tipper=tipper,
            recipient=recipient,
            amount=amount,
        )

    @classmethod
    def get_article_tips(cls, article_id: int, limit: int = 20):
        return (
            Tip.objects.filter(article_id=article_id)
            .select_related("tipper")
            .order_by("-created_at")[:limit]
        )

    @classmethod
    def get_leaderboard(cls, limit: int = 20) -> list:
        """Top recipients by total tips received (Redis cached, weekly refresh)."""
        cache_key = "tip_leaderboard"
        cached = cache.get(cache_key)
        if cached:
            return cached

        from django.db.models import Sum
        from django.contrib.auth import get_user_model
        User = get_user_model()

        results = (
            Tip.objects.values("recipient_id")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:limit]
        )

        user_ids = [r["recipient_id"] for r in results]
        users = {u.id: u for u in User.objects.filter(id__in=user_ids)}

        leaderboard = [
            {
                "rank": i + 1,
                "user_id": r["recipient_id"],
                "display_name": users[r["recipient_id"]].display_name or users[r["recipient_id"]].email,
                "avatar_url": users[r["recipient_id"]].avatar_url,
                "total_tips": float(r["total"]),
            }
            for i, r in enumerate(results)
            if r["recipient_id"] in users
        ]

        cache.set(cache_key, leaderboard, timeout=7 * 24 * 3600)
        return leaderboard
