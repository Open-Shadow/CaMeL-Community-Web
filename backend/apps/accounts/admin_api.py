"""Admin API routes for user management and platform dashboard."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from ninja import Router, Schema

from common.permissions import AuthBearer, admin_required, moderator_required
from apps.accounts.models import User, UserRole, sync_admin_flags
from apps.payments.models import Transaction, TransactionType
from apps.skills.models import Skill, SkillStatus, VersionStatus
from apps.skills.services import SkillService
from apps.workshop.models import Article
from apps.bounties.models import Bounty
from apps.credits.models import CreditLog
from common.utils import build_absolute_media_url


router = Router(tags=["admin"], auth=AuthBearer())


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
    role: str
    level: str
    credit_score: int
    balance: float
    frozen_balance: float
    is_active: bool
    date_joined: str
    last_login: str | None


class UserListResponse(Schema):
    users: list[UserListOutput]
    total: int
    page: int
    page_size: int


class RoleUpdateInput(Schema):
    role: str


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
    role: str
    level: str
    credit_score: int
    balance: float
    frozen_balance: float
    is_active: bool
    date_joined: str
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
    price: float | None
    status: str
    is_featured: bool
    rejection_reason: str
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str
    # Version-update review context (present when an approved skill has a pending version)
    pending_version: str | None = None
    pending_version_id: int | None = None
    pending_version_changelog: str | None = None


class SkillReviewQueueOutput(Schema):
    items: list[SkillReviewQueueItemOutput]
    total: int
    page: int
    page_size: int


class SkillReviewInput(Schema):
    action: str  # APPROVE | REJECT
    reason: str = ""
    version_id: int | None = None  # Optional explicit version target


class SkillFeaturedInput(Schema):
    is_featured: bool


# =============================================================================
# Dashboard API
# =============================================================================

@router.get("/dashboard", response=DashboardOutput)
@moderator_required
def get_dashboard(request):
    """Platform overview dashboard data."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    total_users = User.objects.count()
    new_users_today = User.objects.filter(date_joined__gte=today_start).count()
    new_users_7d = User.objects.filter(date_joined__gte=seven_days_ago).count()
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
        "new_users_today": new_users_today,
        "new_users_7d": new_users_7d,
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
               sort: str = "-date_joined"):
    """List users with search and filters."""
    qs = User.objects.all()

    if search:
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(display_name__icontains=search)
        )
    if role:
        qs = qs.filter(role=role)
    if level:
        qs = qs.filter(level=level)

    # Validate sort field
    valid_sorts = ["date_joined", "-date_joined", "credit_score", "-credit_score",
                   "balance", "-balance", "username", "-username"]
    if sort not in valid_sorts:
        sort = "-date_joined"

    total = qs.count()
    offset = (page - 1) * page_size
    users = qs.order_by(sort)[offset:offset + page_size]

    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "level": u.level,
                "credit_score": u.credit_score,
                "balance": float(u.balance),
                "frozen_balance": float(u.frozen_balance),
                "is_active": u.is_active,
                "date_joined": u.date_joined.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
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

    return 200, {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "display_name": u.display_name,
        "bio": u.bio,
        "avatar_url": build_absolute_media_url(request, u.avatar_url),
        "role": u.role,
        "level": u.level,
        "credit_score": u.credit_score,
        "balance": float(u.balance),
        "frozen_balance": float(u.frozen_balance),
        "is_active": u.is_active,
        "date_joined": u.date_joined.isoformat(),
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "skills_count": Skill.objects.filter(creator=u).count(),
        "articles_count": Article.objects.filter(author=u).count(),
        "transactions_count": Transaction.objects.filter(user=u).count(),
        "invitees_count": u.invitees.count(),
    }


@router.patch("/users/{user_id}/role", response={200: MessageOutput, 404: MessageOutput})
@admin_required
def update_user_role(request, user_id: int, data: RoleUpdateInput):
    """Update user role. Admin only."""
    if data.role not in [r.value for r in UserRole]:
        return 404, {"message": f"无效角色: {data.role}"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return 404, {"message": "用户不存在"}

    if user.id == request.auth.id:
        return 404, {"message": "不能修改自己的角色"}

    old_role = user.role
    user.role = data.role
    user.save(update_fields=["role"])
    sync_admin_flags(user)

    return 200, {"message": f"用户 {user.username} 角色已从 {old_role} 更改为 {data.role}"}


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

    if user.role == "ADMIN":
        return 404, {"message": "不能封禁管理员"}

    user.is_active = False
    user.save(update_fields=["is_active"])

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

    user.is_active = True
    user.save(update_fields=["is_active"])

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
    out = {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "tags": skill.tags,
        "pricing_model": skill.pricing_model,
        "price": float(skill.price) if skill.price is not None else None,
        "status": skill.status,
        "is_featured": skill.is_featured,
        "rejection_reason": skill.rejection_reason,
        "creator_id": skill.creator_id,
        "creator_name": skill.creator.display_name or skill.creator.username,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }
    # Attach pending version metadata for approved skills with pending updates
    if skill.status == SkillStatus.APPROVED:
        pending = skill.versions.filter(
            status=VersionStatus.SCANNING,
        ).order_by("-created_at").first()
        if pending:
            out["pending_version"] = pending.version
            out["pending_version_id"] = pending.id
            out["pending_version_changelog"] = pending.changelog
    return out


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
        # Include both new skills in SCANNING and approved skills with pending version updates
        queryset = queryset.filter(
            Q(status=SkillStatus.SCANNING)
            | Q(status=SkillStatus.APPROVED, versions__status=VersionStatus.SCANNING)
        ).distinct()
    elif status == "rejected":
        queryset = queryset.filter(status=SkillStatus.REJECTED)
    elif status == "approved":
        queryset = queryset.filter(status=SkillStatus.APPROVED)
    elif status == "all":
        pass
    else:
        queryset = queryset.filter(status=SkillStatus.SCANNING)

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
            version_id=data.version_id,
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

    # Totals
    total_deposits = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_fees = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_circulation = User.objects.aggregate(
        total=Sum("balance"))["total"] or Decimal("0")
    total_frozen = User.objects.aggregate(
        total=Sum("frozen_balance"))["total"] or Decimal("0")

    # 7-day
    deposits_7d = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT,
        created_at__gte=seven_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    fees_7d = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE,
        created_at__gte=seven_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # 30-day
    deposits_30d = Transaction.objects.filter(
        transaction_type=TransactionType.DEPOSIT,
        created_at__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    fees_30d = Transaction.objects.filter(
        transaction_type=TransactionType.PLATFORM_FEE,
        created_at__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Daily breakdown (last 30 days)
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
        "total_circulation": float(total_circulation),
        "total_frozen": float(total_frozen),
        "deposits_7d": float(deposits_7d),
        "fees_7d": float(abs(fees_7d)),
        "deposits_30d": float(deposits_30d),
        "fees_30d": float(abs(fees_30d)),
        "daily_deposits": daily_deposits,
        "daily_fees": daily_fees,
    }
