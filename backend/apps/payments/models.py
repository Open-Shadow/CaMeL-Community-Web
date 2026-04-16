from django.db import models
from apps.accounts.models import User


class TransactionType(models.TextChoices):
    DEPOSIT = "DEPOSIT", "充值"
    SKILL_PURCHASE = "SKILL_PURCHASE", "Skill 购买扣费"
    SKILL_INCOME = "SKILL_INCOME", "Skill 收入"
    BOUNTY_ESCROW = "BOUNTY_ESCROW", "悬赏冻结"
    BOUNTY_RELEASE = "BOUNTY_RELEASE", "悬赏解冻"
    BOUNTY_INCOME = "BOUNTY_INCOME", "悬赏收入"
    TIP_SEND = "TIP_SEND", "打赏支出"
    TIP_RECEIVE = "TIP_RECEIVE", "打赏收入"
    PLATFORM_FEE = "PLATFORM_FEE", "平台手续费"
    REFUND = "REFUND", "退款"


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=200, blank=True)
    stripe_payment_intent = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_transaction"
        indexes = [models.Index(fields=["user", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["stripe_payment_intent"],
                condition=~models.Q(stripe_payment_intent=""),
                name="unique_stripe_payment_intent",
            ),
        ]
