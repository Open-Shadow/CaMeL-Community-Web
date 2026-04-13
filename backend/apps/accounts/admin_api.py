"""Admin API routes for user management and platform dashboard."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from ninja import Router, Schema

from common.permissions import AuthBearer, admin_required, moderator_required, ROLE_ADMIN
from apps.accounts.models import CamelUser as User, CommunityProfile, get_or_create_profile
from apps.payments.models import Transaction, TransactionType
from apps.skills.models import Skill, SkillStatus
from apps.skills.services import SkillService
from apps.workshop.models import Article
from apps.bounties.models import Bounty
from common.quota_service import QUOTA_PER_DOLLAR
from common.utils import build_absolute_media_url


router = Router(tags=["admin"], auth=AuthBearer())

ROLE_LABELS = {1: "普通用户", 5: "社区版主", 10: "管理员", 100: "超级管理员"}


def _quota_to_usd(quota: int) -> float:
    return float(Decimal(quota) / Decimal(QUOTA_PER_DOLLAR))


# =============================================================================
# Schemas
# =============================================================================

class DashboardOutput(Schema):
    total_users: int
    new_users_today: int
    new_users_7d: int
    total_skills: int
    total_articles: int
    total_bounties: int
    total_deposits: float
    total_fees: float
    active_users_7d: int


class UserListOutput(Schema):
    id: int
    username: str
    email: str
    display_name: str
    role: int
    level: str
    credit_score: int
    balance: float
    frozen_balance: float
    is_active: bool
    last_login: str | None


class UserListResponse(Schema):
    users: list[UserListOutput]
    total: int
    page: int
    page_size: int


class RoleUpdateInput(Schema):
    role: int


class BanInput(Schema):
    reason: str = ""


class CreditAdjustInput(Schema):
    amount: int
    reason: str = "管理员调整"


class MessageOutput(Schema):
    message: str


class FinanceReportOutput(Schema):
    total_deposits: float
    total_fees: float
    total_circulation: float
    total_frozen: float
    deposits_7d: float
    fees_7d: float
    deposits_30d: float
    fees_30d: float
    daily_deposits: list[dict]
    daily_fees: list[dict]


class UserDetailOutput(Schema):
    id: int
    username: str
    email: str
    display_name: str
    bio: str
    avatar_url: str
    role: int
    level: str
    credit_score: int
    balance: float
    frozen_balance: float
    is_active: bool
    last_login: str | None
    skills_count: int
    articles_count: int
    transactions_count: int
    invitees_count: int


class SkillReviewQueueItemOutput(Schema):
    id: int
    name: str
    description: str
    category: str
    tags: list[str]
    pricing_model: str
    price_per_use: float | None
    status: str
    is_featured: bool
    rejection_reason: str
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str


class SkillReviewQueueOutput(Schema):
    items: list[SkillReviewQueueItemOutput]
    total: int
    page: int
    page_size: int


class SkillReviewInput(Schema):
    action: str  # APPROVE | REJECT
    reason: str = ""


class SkillFeaturedInput(Schema):
    is_featured: bool


# =============================================================================
# Helpers
# =============================================================================

def _user_list_item(u: User) -> dict:
    profile = get_or_create_profile(u)
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role,
        "level": u.community_level,
        "credit_score": u.credit_score,
        "balance": _quota_to_usd(u.quota),
        "frozen_balance": _quota_to_usd(profile.frozen_balance),
        "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
    }


# =============================================================================
# Dashboard API
# =============================================================================

@router.get("/dashboard", response=DashboardOutput)
@moderator_required
def get_dashboard(request):
    """Platform overview dashboard data."""
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    total_users = User.objects.count()
    active_users_7d = User.objects.filter(last_login__gte=seven_days_ago).count()

    total_skills = Skill.objects.count()
    total_articles = Article.objects.count()
    total_bounties = Bounty.objects.count()

    total_deposits = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_fees = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return {
        "total_users": total_users,
        "new_users_today": 0,
        "new_users_7d": 0,
        "total_skills": total_skills,
        "total_articles": total_articles,
        "total_bounties": total_bounties,
        "total_deposits": float(total_deposits),
        "total_fees": float(abs(total_fees)),
        "active_users_7d": active_users_7d,
    }


# =============================================================================
# User Management API
# =============================================================================

@router.get("/users", response=UserListResponse)
@moderator_required
def list_users(request, page: int = 1, page_size: int = 20,
               search: str = "", role: str = "", level: str = "",
               sort: str = "-id"):
    """List users with search and filters."""
    qs = User.objects.all()

    if search:
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(display_name__icontains=search)
        )
    if role:
        try:
            qs = qs.filter(role=int(role))
        except ValueError:
            pass
    if level:
        qs = qs.filter(community_level=level)

    valid_sorts = ["id", "-id", "credit_score", "-credit_score",
                   "quota", "-quota", "username", "-username"]
    if sort not in valid_sorts:
        sort = "-id"

    total = qs.count()
    offset = (page - 1) * page_size
    users = qs.order_by(sort)[offset:offset + page_size]

    return {
        "users": [_user_list_item(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}", response={200: UserDetailOutput, 404: MessageOutput})
@moderator_required
def get_user_detail(request, user_id: int):
    """Get detailed user info for admin."""
    try:
        u = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, {"message": "用户不存在"}

    profile = get_or_create_profile(u)

    return 200, {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "display_name": u.display_name,
        "bio": profile.bio,
        "avatar_url": build_absolute_media_url(request, profile.avatar_url),
        "role": u.role,
        "level": u.community_level,
        "credit_score": u.credit_score,
        "balance": _quota_to_usd(u.quota),
        "frozen_balance": _quota_to_usd(profile.frozen_balance),
        "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "skills_count": Skill.objects.filter(creator=u).count(),
        "articles_count": Article.objects.filter(author=u).count(),
        "transactions_count": Transaction.objects.filter(user=u).count(),
        "invitees_count": u.invitees.count() if hasattr(u, 'invitees') else 0,
    }


@router.patch("/users/{user_id}/role", response={200: MessageOutput, 404: MessageOutput})
@admin_required
def update_user_role(request, user_id: int, data: RoleUpdateInput):
    """Update user role. Admin only. Valid roles: 1=common, 5=moderator, 10=admin."""
    if data.role not in ROLE_LABELS:
        return 404, {"message": f"无效角色: {data.role}，有效值: {list(ROLE_LABELS.keys())}"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, {"message": "用户不存在"}

    if user.id == request.auth.id:
        return 404, {"message": "不能修改自己的角色"}

    if data.role >= request.auth.role and request.auth.role < 100:
        return 404, {"message": "不能设置等于或高于自己的角色"}

    old_label = ROLE_LABELS.get(user.role, str(user.role))
    new_label = ROLE_LABELS.get(data.role, str(data.role))
    user.role = data.role
    user.save(update_fields=["role"])
    return 200, {"message": f"用户 {user.username} 角色已从 {old_label} 更改为 {new_label}"}


@router.post("/users/{user_id}/ban", response={200: MessageOutput, 404: MessageOutput})
@admin_required
def ban_user(request, user_id: int, data: BanInput):
    """Ban a user. Admin only."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, {"message": "用户不存在"}

    if user.id == request.auth.id:
        return 404, {"message": "不能封禁自己"}

    if user.role >= ROLE_ADMIN:
        return 404, {"message": "不能封禁管理员"}

    user.status = 2  # Go: UserStatusDisabled = 2
    user.save(update_fields=["status"])

    from apps.notifications.services import NotificationService
    NotificationService.send(
        recipient=user,
        notification_type="SYSTEM",
        title="账号已被封禁",
        content=f"您的账号已被管理员封禁。原因：{data.reason or '违反社区规范'}",
    )

    return 200, {"message": f"用户 {user.username} 已被封禁"}


@router.post("/users/{user_id}/unban", response={200: MessageOutput, 404: MessageOutput})
@admin_required
def unban_user(request, user_id: int):
    """Unban a user. Admin only."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, {"message": "用户不存在"}

    user.status = 1  # Go: UserStatusEnabled = 1
    user.save(update_fields=["status"])

    return 200, {"message": f"用户 {user.username} 已解封"}


@router.post("/users/{user_id}/credit-adjust",
             response={200: MessageOutput, 404: MessageOutput})
@admin_required
def adjust_user_credit(request, user_id: int, data: CreditAdjustInput):
    """Manually adjust user credit score. Admin only."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, {"message": "用户不存在"}

    from apps.credits.services import CreditService

    new_score = CreditService.admin_adjust(
        user, data.amount,
        reference_id=f"admin:{request.auth.id}:{data.reason}"
    )

    return 200, {"message": f"信用分已调整，当前 {new_score} 分"}


# =============================================================================
# Skill Review API
# =============================================================================

def _skill_queue_item_out(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "tags": skill.tags,
        "pricing_model": skill.pricing_model,
        "price_per_use": float(skill.price_per_use) if skill.price_per_use is not None else None,
        "status": skill.status,
        "is_featured": skill.is_featured,
        "rejection_reason": skill.rejection_reason,
        "creator_id": skill.creator_id,
        "creator_name": skill.creator.display_name or skill.creator.username,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


@router.get("/skills/review-queue", response=SkillReviewQueueOutput)
@moderator_required
def list_skill_review_queue(
    request,
    status: str = "pending",
    q: str = "",
    page: int = 1,
    page_size: int = 20,
):
    queryset = Skill.objects.select_related("creator")
    if status == "pending":
        queryset = queryset.filter(status=SkillStatus.PENDING_REVIEW)
    elif status == "rejected":
        queryset = queryset.filter(status=SkillStatus.REJECTED)
    elif status == "approved":
        queryset = queryset.filter(status=SkillStatus.APPROVED)
    elif status == "all":
        pass
    else:
        queryset = queryset.filter(status=SkillStatus.PENDING_REVIEW)

    if q:
        queryset = queryset.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(creator__username__icontains=q)
            | Q(creator__display_name__icontains=q)
        )

    total = queryset.count()
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    offset = (safe_page - 1) * safe_page_size
    items = queryset.order_by("-updated_at")[offset:offset + safe_page_size]

    return {
        "items": [_skill_queue_item_out(skill) for skill in items],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


@router.post("/skills/{skill_id}/review", response={200: SkillReviewQueueItemOutput, 400: MessageOutput, 404: MessageOutput})
@moderator_required
def review_skill(request, skill_id: int, data: SkillReviewInput):
    try:
        skill = Skill.objects.select_related("creator").get(id=skill_id)
    except Skill.DoesNotExist:
        return 404, {"message": "Skill 不存在"}

    action = data.action.strip().upper()
    if action not in {"APPROVE", "REJECT"}:
        return 400, {"message": "审核动作无效"}
    if action == "REJECT" and not data.reason.strip():
        return 400, {"message": "拒绝时请填写原因"}

    try:
        skill = SkillService.review(
            skill,
            request.auth,
            approve=(action == "APPROVE"),
            reason=data.reason,
        )
    except ValueError as exc:
        return 400, {"message": str(exc)}

    return 200, _skill_queue_item_out(skill)


@router.post("/skills/{skill_id}/featured", response={200: SkillReviewQueueItemOutput, 400: MessageOutput, 404: MessageOutput})
@moderator_required
def set_skill_featured(request, skill_id: int, data: SkillFeaturedInput):
    try:
        skill = Skill.objects.select_related("creator").get(id=skill_id)
    except Skill.DoesNotExist:
        return 404, {"message": "Skill 不存在"}

    try:
        updated = SkillService.set_featured(skill, is_featured=data.is_featured)
    except ValueError as exc:
        return 400, {"message": str(exc)}
    return 200, _skill_queue_item_out(updated)


# =============================================================================
# Finance Report API
# =============================================================================

@router.get("/finance/report", response=FinanceReportOutput)
@admin_required
def get_finance_report(request):
    """Financial overview with trends."""
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    total_deposits = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_fees = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Total circulation from users.quota
    total_quota = User.objects.aggregate(total=Sum("quota"))["total"] or 0
    total_frozen = CommunityProfile.objects.aggregate(
        total=Sum("frozen_balance"))["total"] or 0

    deposits_7d = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT,
        created_at__gte=seven_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    fees_7d = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE,
        created_at__gte=seven_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    deposits_30d = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT,
        created_at__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    fees_30d = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE,
        created_at__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    from django.db.models.functions import TruncDate

    daily_deposits_qs = (
        Transaction.objects.filter(
            transaction_type=TransactionType.DEPOSIT,
            created_at__gte=thirty_days_ago,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("date")
    )
    daily_deposits = [
        {"date": d["date"].isoformat(), "total": float(d["total"]), "count": d["count"]}
        for d in daily_deposits_qs
    ]

    daily_fees_qs = (
        Transaction.objects.filter(
            transaction_type=TransactionType.PLATFORM_FEE,
            created_at__gte=thirty_days_ago,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("date")
    )
    daily_fees = [
        {"date": d["date"].isoformat(), "total": float(abs(d["total"])), "count": d["count"]}
        for d in daily_fees_qs
    ]

    return {
        "total_deposits": float(total_deposits),
        "total_fees": float(abs(total_fees)),
        "total_circulation": _quota_to_usd(total_quota),
        "total_frozen": _quota_to_usd(total_frozen),
        "deposits_7d": float(deposits_7d),
        "fees_7d": float(abs(fees_7d)),
        "deposits_30d": float(deposits_30d),
        "fees_30d": float(abs(fees_30d)),
        "daily_deposits": daily_deposits,
        "daily_fees": daily_fees,
    }
