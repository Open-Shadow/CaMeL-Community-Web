from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    USER = "USER", "普通用户"
    MODERATOR = "MODERATOR", "版主"
    ADMIN = "ADMIN", "管理员"


class UserLevel(models.TextChoices):
    SEED = "SEED", "🌱 新芽"
    CRAFTSMAN = "CRAFTSMAN", "🔧 工匠"
    EXPERT = "EXPERT", "⚡ 专家"
    MASTER = "MASTER", "🏆 大师"
    GRANDMASTER = "GRANDMASTER", "👑 宗师"


class User(AbstractUser):
    """扩展 Django 内置 User，增加业务字段"""

    display_name = models.CharField(max_length=50, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar_url = models.URLField(blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    level = models.CharField(max_length=20, choices=UserLevel.choices, default=UserLevel.SEED)
    credit_score = models.IntegerField(default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frozen_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bounty_freeze_until = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="invitees"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user"


class Invitation(models.Model):
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invitations")
    code = models.CharField(max_length=20, unique=True)
    used_by = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_invitation"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    first_deposit_rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_invitation"
