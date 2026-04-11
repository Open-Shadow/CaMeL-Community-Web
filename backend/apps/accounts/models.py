from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
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


class CamelUserManager(DjangoUserManager):
    """Custom manager that ensures create_superuser sets role=ADMIN."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = UserRole.ADMIN
        return super().create_superuser(username, email, password, **extra_fields)


def sync_admin_flags(user):
    """Synchronize Django auth flags with business-layer role.

    ADMIN role gets is_staff=True, is_superuser=True.
    All other roles get is_staff=False, is_superuser=False.
    """
    if user.role == UserRole.ADMIN:
        user.is_staff = True
        user.is_superuser = True
    else:
        user.is_staff = False
        user.is_superuser = False
    user.save(update_fields=["is_staff", "is_superuser"])


class User(AbstractUser):
    """扩展 Django 内置 User，增加业务字段"""

    objects = CamelUserManager()

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
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("email"),
                name="unique_email_ci",
                condition=~models.Q(email=""),
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Invitation(models.Model):
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invitations")
    code = models.CharField(max_length=20, unique=True)
    used_by = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_invitation"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    first_deposit_rewarded = models.BooleanField(default=False)
    registration_ip_hash = models.CharField(max_length=64, blank=True, db_index=True)
    registration_device_hash = models.CharField(max_length=64, blank=True, db_index=True)
    risk_flags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_invitation"
