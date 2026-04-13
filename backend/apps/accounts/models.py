from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import PermissionsMixin
from django.db import models


# ---------------------------------------------------------------------------
# Reference enums (for Community business logic display only)
# ---------------------------------------------------------------------------

class UserRole(models.TextChoices):
    """Community-side role labels.  The actual authority lives in CamelUser.role (int)."""
    USER = "USER", "普通用户"
    MODERATOR = "MODERATOR", "版主"
    ADMIN = "ADMIN", "管理员"


class UserLevel(models.TextChoices):
    """Community credit-level labels (display only)."""
    SEED = "SEED", "🌱 新芽"
    CRAFTSMAN = "CRAFTSMAN", "🔧 工匠"
    EXPERT = "EXPERT", "⚡ 专家"
    MASTER = "MASTER", "🏆 大师"
    GRANDMASTER = "GRANDMASTER", "👑 宗师"


# ---------------------------------------------------------------------------
# Custom manager
# ---------------------------------------------------------------------------

class CamelUserManager(BaseUserManager):
    """Manager for the unmanaged CamelUser model (Go ``users`` table)."""

    def create_user(self, username, email, password=None, **extra):
        if not username:
            raise ValueError("username is required")
        if not email:
            raise ValueError("email is required")
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            status=1,
            **extra,
        )
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra):
        extra["role"] = 100
        return self.create_user(username, email, password, **extra)


# ---------------------------------------------------------------------------
# CamelUser — unmanaged model mapping to Go's ``users`` table
# ---------------------------------------------------------------------------

QUOTA_PER_DOLLAR = Decimal(500_000)


class CamelUser(AbstractBaseUser, PermissionsMixin):
    """
    Read/write proxy for the Go-managed ``users`` table.

    ``managed = False`` means Django will never create or alter this table.
    """

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=128)
    display_name = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=50)
    status = models.IntegerField(default=1)
    role = models.IntegerField(default=1)
    quota = models.IntegerField(default=0)
    used_quota = models.IntegerField(default=0)
    credit_score = models.IntegerField(default=0)
    community_level = models.CharField(max_length=20, default="SEED")
    aff_code = models.CharField(max_length=32, blank=True)
    inviter_id = models.IntegerField(null=True, blank=True)
    group = models.CharField(max_length=64, default="default")
    deleted_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = CamelUserManager()

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self):
        return self.username

    # ---- properties expected by Django auth / admin ----

    @property
    def is_active(self):
        return self.status == 1

    @property
    def is_staff(self):
        return self.role >= 10

    @property
    def is_superuser(self):
        return self.role >= 100

    @is_superuser.setter
    def is_superuser(self, value):
        # PermissionsMixin tries to set this; silently ignore since Go owns the role column.
        pass

    # ---- community helpers ----

    @property
    def level(self):
        return self.community_level

    @property
    def balance_usd(self) -> Decimal:
        return Decimal(self.quota) / QUOTA_PER_DOLLAR


# ---------------------------------------------------------------------------
# CommunityProfile — managed model for community-specific data
# ---------------------------------------------------------------------------

class CommunityProfile(models.Model):
    """Extra community data that lives alongside the Go ``users`` row."""

    user = models.OneToOneField(
        CamelUser,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="community_profile",
        db_column="user_id",
    )
    bio = models.TextField(max_length=500, blank=True)
    avatar_url = models.URLField(blank=True)
    frozen_balance = models.IntegerField(default=0)  # quota units
    bounty_freeze_until = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        CamelUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "community_profiles"

    def __str__(self):
        return f"CommunityProfile(user={self.user_id})"


# ---------------------------------------------------------------------------
# Invitation
# ---------------------------------------------------------------------------

class Invitation(models.Model):
    inviter = models.ForeignKey(CamelUser, on_delete=models.CASCADE, related_name="invitations")
    code = models.CharField(max_length=20, unique=True)
    used_by = models.OneToOneField(
        CamelUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_invitation"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    first_deposit_rewarded = models.BooleanField(default=False)
    registration_ip_hash = models.CharField(max_length=64, blank=True, db_index=True)
    registration_device_hash = models.CharField(max_length=64, blank=True, db_index=True)
    risk_flags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_invitation"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_or_create_profile(user: CamelUser) -> CommunityProfile:
    """Return the user's CommunityProfile, creating one if it does not exist."""
    profile, _ = CommunityProfile.objects.get_or_create(user=user)
    return profile
