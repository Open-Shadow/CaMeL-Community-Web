"""User API routes."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db.models import Sum
from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.responses import Status

from apps.accounts.services import InvitationService
from apps.bounties.models import Bounty, BountyStatus
from apps.skills.models import Skill, SkillStatus
from apps.workshop.models import Article, ArticleStatus
from common.permissions import AuthBearer
from common.utils import build_absolute_media_url

User = get_user_model()
router = Router(tags=["users"], auth=AuthBearer())


class UserProfileOutput(Schema):
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
    created_at: str


class PublicUserProfileOutput(Schema):
    id: int
    username: str
    display_name: str
    bio: str
    avatar_url: str
    role: str
    level: str
    credit_score: int
    created_at: str


class UserProfileUpdateInput(Schema):
    display_name: str | None = None
    bio: str | None = None


class UserStatsOutput(Schema):
    skills_count: int
    articles_count: int
    bounties_posted: int
    bounties_completed: int
    total_earned: float
    total_spent: float


class ChangePasswordInput(Schema):
    old_password: str
    new_password: str


class MessageOutput(Schema):
    message: str


class CreditHistoryOutput(Schema):
    id: int
    action: str
    amount: int
    score_before: int
    score_after: int
    created_at: str


class CreditHistoryListOutput(Schema):
    items: list[CreditHistoryOutput]
    limit: int
    offset: int
    total: int


class ContributionOutput(Schema):
    id: int
    kind: str
    title: str
    subtitle: str
    href: str
    created_at: str


class PublicUserOverviewOutput(Schema):
    profile: PublicUserProfileOutput
    stats: UserStatsOutput
    recent_contributions: list[ContributionOutput]


class InvitedUserOutput(Schema):
    id: int
    code: str
    invitee_display_name: str
    invitee_email: str
    used_at: str
    risk_flags: list[str]


class InviteDashboardOutput(Schema):
    code: str
    share_path: str
    total_codes_generated: int
    registered_invites: int
    rewarded_invites: int
    delayed_reward_pending: int
    monthly_credit_awarded: int
    monthly_credit_remaining: int
    active_window_days: int
    recent_invites: list[InvitedUserOutput]


IMAGE_EXTENSION_MAP = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
    "GIF": "gif",
}


def serialize_private_user(request, user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": build_absolute_media_url(request, user.avatar_url),
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "balance": float(user.balance),
        "created_at": user.created_at.isoformat(),
    }


def serialize_public_user(request, user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "bio": user.bio,
        "avatar_url": build_absolute_media_url(request, user.avatar_url),
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "created_at": user.created_at.isoformat(),
    }


def decimal_to_float(value: Decimal | None) -> float:
    return float(value or Decimal("0"))


def build_user_stats(user: User, *, public: bool) -> dict:
    skills_queryset = user.skills.all()
    articles_queryset = user.articles.all()
    bounties_queryset = user.bounties.all()

    if public:
        skills_queryset = skills_queryset.filter(status=SkillStatus.APPROVED)
        articles_queryset = articles_queryset.filter(status=ArticleStatus.PUBLISHED)

    completed_bounties = Bounty.objects.filter(
        status=BountyStatus.COMPLETED,
        accepted_application__applicant=user,
    )
    total_earned = completed_bounties.aggregate(total=Sum("reward"))["total"]
    total_spent = Bounty.objects.filter(
        creator=user,
        status=BountyStatus.COMPLETED,
    ).aggregate(total=Sum("reward"))["total"]

    return {
        "skills_count": skills_queryset.count(),
        "articles_count": articles_queryset.count(),
        "bounties_posted": bounties_queryset.count(),
        "bounties_completed": completed_bounties.count(),
        "total_earned": decimal_to_float(total_earned),
        "total_spent": decimal_to_float(total_spent),
    }


def build_recent_contributions(user: User) -> list[dict]:
    items: list[dict] = []

    for skill in Skill.objects.filter(creator=user, status=SkillStatus.APPROVED).order_by("-created_at")[:3]:
        items.append(
            {
                "id": skill.id,
                "kind": "skill",
                "title": skill.name,
                "subtitle": skill.description,
                "href": f"/marketplace/{skill.id}",
                "created_at": skill.created_at.isoformat(),
                "_sort": skill.created_at,
            }
        )

    for article in Article.objects.filter(author=user, status=ArticleStatus.PUBLISHED).order_by(
        "-published_at",
        "-created_at",
    )[:3]:
        created_at = article.published_at or article.created_at
        items.append(
            {
                "id": article.id,
                "kind": "article",
                "title": article.title,
                "subtitle": article.get_article_type_display(),
                "href": f"/workshop/{article.id}",
                "created_at": created_at.isoformat(),
                "_sort": created_at,
            }
        )

    for bounty in Bounty.objects.filter(creator=user).order_by("-created_at")[:2]:
        items.append(
            {
                "id": bounty.id,
                "kind": "bounty",
                "title": bounty.title,
                "subtitle": bounty.get_status_display(),
                "href": f"/bounty/{bounty.id}",
                "created_at": bounty.created_at.isoformat(),
                "_sort": bounty.created_at,
            }
        )

    ordered = sorted(items, key=lambda item: item["_sort"], reverse=True)[:6]
    return [{key: value for key, value in item.items() if key != "_sort"} for item in ordered]


def validate_avatar_file(file: UploadedFile) -> str:
    if file.size > 5 * 1024 * 1024:
        raise HttpError(400, "头像文件不能超过 5MB")

    try:
        image = Image.open(file)
        image.verify()
        image_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise HttpError(400, "请上传有效的图片文件") from exc
    finally:
        file.seek(0)

    if image_format not in IMAGE_EXTENSION_MAP:
        raise HttpError(400, "仅支持 JPG、PNG、WEBP、GIF 图片")

    suffix = Path(file.name).suffix.lower().lstrip(".")
    return suffix or IMAGE_EXTENSION_MAP[image_format]


@router.get("/me", response=UserProfileOutput)
def get_my_profile(request):
    return serialize_private_user(request, request.auth)


@router.patch("/me", response=UserProfileOutput)
def update_my_profile(request, data: UserProfileUpdateInput):
    user = request.auth
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.bio is not None:
        user.bio = data.bio

    user.save(update_fields=["display_name", "bio", "updated_at"])
    return serialize_private_user(request, user)


@router.post("/me/avatar", response={200: UserProfileOutput, 400: MessageOutput})
def upload_avatar(
    request,
    file: UploadedFile | None = File(None),
    avatar: UploadedFile | None = File(None),
):
    user = request.auth
    uploaded_file = file or avatar
    if uploaded_file is None:
        raise HttpError(400, "请上传头像文件")

    extension = validate_avatar_file(uploaded_file)
    avatar_path = f"avatars/{user.id}/{uuid4().hex}.{extension}"
    stored_name = default_storage.save(avatar_path, uploaded_file)
    user.avatar_url = default_storage.url(stored_name)
    user.save(update_fields=["avatar_url", "updated_at"])
    return serialize_private_user(request, user)


@router.get("/me/stats", response=UserStatsOutput)
def get_my_stats(request):
    return build_user_stats(request.auth, public=False)


@router.get("/me/invite-code", response=InviteDashboardOutput)
def get_my_invite_code(request):
    return InvitationService.get_dashboard(request.auth)


@router.post("/me/password", response={200: MessageOutput, 400: MessageOutput})
def change_password(request, data: ChangePasswordInput):
    user = request.auth
    if not user.check_password(data.old_password):
        return Status(400, {"message": "当前密码错误"})

    try:
        validate_password(data.new_password, user)
    except ValidationError as exc:
        return Status(400, {"message": "密码强度不足: " + ", ".join(exc.messages)})

    user.set_password(data.new_password)
    user.save(update_fields=["password"])
    return Status(200, {"message": "密码修改成功"})


@router.get("/me/credit-history", response=CreditHistoryListOutput)
def get_my_credit_history(request, limit: int = 20, offset: int = 0):
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    queryset = request.auth.credit_logs.all().order_by("-created_at")
    logs = queryset[safe_offset:safe_offset + safe_limit]

    return {
        "items": [
            {
                "id": log.id,
                "action": log.get_action_display(),
                "amount": log.amount,
                "score_before": log.score_before,
                "score_after": log.score_after,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "limit": safe_limit,
        "offset": safe_offset,
        "total": queryset.count(),
    }


@router.get("/public/{username}/overview", response=PublicUserOverviewOutput, auth=None)
def get_public_user_overview(request, username: str):
    user = User.objects.filter(username=username).first()
    if not user:
        raise HttpError(404, "用户不存在")

    return {
        "profile": serialize_public_user(request, user),
        "stats": build_user_stats(user, public=True),
        "recent_contributions": build_recent_contributions(user),
    }


@router.get("/by-username/{username}", response={200: PublicUserProfileOutput, 404: MessageOutput}, auth=None)
def get_user_by_username(request, username: str):
    """Get public profile by username."""
    user = User.objects.filter(username=username).first()
    if not user:
        return 404, {"message": "用户不存在"}
    return 200, serialize_public_user(request, user)


@router.get("/by-username/{username}/stats", response={200: UserStatsOutput, 404: MessageOutput}, auth=None)
def get_user_stats_by_username(request, username: str):
    """Get public stats by username."""
    user = User.objects.filter(username=username).first()
    if not user:
        return 404, {"message": "用户不存在"}
    return 200, build_user_stats(user, public=True)


@router.get("/{user_id}", response=PublicUserProfileOutput, auth=None)
def get_user_profile(request, user_id: int):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise HttpError(404, "用户不存在")
    return serialize_public_user(request, user)


@router.get("/{user_id}/stats", response=UserStatsOutput, auth=None)
def get_user_stats(request, user_id: int):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise HttpError(404, "用户不存在")
    return build_user_stats(user, public=True)
