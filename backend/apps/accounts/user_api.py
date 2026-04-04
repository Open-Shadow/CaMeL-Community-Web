"""User API routes."""
from ninja import Router, Schema, File
from ninja.files import UploadedFile
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from common.permissions import AuthBearer
from apps.credits.services import CreditService

User = get_user_model()
router = Router(tags=["users"], auth=AuthBearer())


# =============================================================================
# Schemas
# =============================================================================

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


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/me", response=UserProfileOutput)
def get_my_profile(request):
    """Get current user profile."""
    user = request.auth
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "balance": float(user.balance),
        "created_at": user.created_at.isoformat(),
    }


@router.patch("/me", response=UserProfileOutput)
def update_my_profile(request, data: UserProfileUpdateInput):
    """Update current user profile."""
    user = request.auth

    if data.display_name is not None:
        user.display_name = data.display_name
    if data.bio is not None:
        user.bio = data.bio

    user.save()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "balance": float(user.balance),
        "created_at": user.created_at.isoformat(),
    }


@router.post("/me/avatar", response=UserProfileOutput)
def upload_avatar(request, file: UploadedFile = File(...)):
    """Upload user avatar."""
    user = request.auth

    # TODO: Implement actual file upload to S3/R2
    # For now, just store a placeholder
    user.avatar_url = f"/media/avatars/{user.id}_{file.name}"
    user.save()

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "balance": float(user.balance),
        "created_at": user.created_at.isoformat(),
    }


@router.get("/me/stats", response=UserStatsOutput)
def get_my_stats(request):
    """Get current user statistics."""
    user = request.auth

    # Count related objects
    skills_count = user.skills.count() if hasattr(user, 'skills') else 0
    articles_count = user.articles.count() if hasattr(user, 'articles') else 0
    bounties_posted = user.bounties.count() if hasattr(user, 'bounties') else 0
    bounties_completed = 0  # TODO: Implement

    return {
        "skills_count": skills_count,
        "articles_count": articles_count,
        "bounties_posted": bounties_posted,
        "bounties_completed": bounties_completed,
        "total_earned": 0.0,  # TODO: Calculate from transactions
        "total_spent": 0.0,
    }


@router.post("/me/password", response={200: MessageOutput, 400: MessageOutput})
def change_password(request, data: ChangePasswordInput):
    """Change user password."""
    user = request.auth

    # Verify old password
    if not user.check_password(data.old_password):
        return 400, {"message": "当前密码错误"}

    # Validate new password
    try:
        validate_password(data.new_password, user)
    except ValidationError as e:
        return 400, {"message": "密码强度不足: " + ", ".join(e.messages)}

    user.set_password(data.new_password)
    user.save()

    return 200, {"message": "密码修改成功"}


@router.get("/{user_id}", response=UserProfileOutput)
def get_user_profile(request, user_id: int):
    """Get public profile of a user."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"message": "用户不存在"}

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "level": user.level,
        "credit_score": user.credit_score,
        "balance": 0.0,  # Hide actual balance for privacy
        "created_at": user.created_at.isoformat(),
    }


@router.get("/{user_id}/stats", response=UserStatsOutput)
def get_user_stats(request, user_id: int):
    """Get public statistics of a user."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"message": "用户不存在"}

    skills_count = user.skills.count() if hasattr(user, 'skills') else 0
    articles_count = user.articles.count() if hasattr(user, 'articles') else 0
    bounties_posted = user.bounties.count() if hasattr(user, 'bounties') else 0

    return {
        "skills_count": skills_count,
        "articles_count": articles_count,
        "bounties_posted": bounties_posted,
        "bounties_completed": 0,
        "total_earned": 0.0,
        "total_spent": 0.0,
    }


@router.get("/me/credit-history", response=list[CreditHistoryOutput])
def get_my_credit_history(request, limit: int = 20, offset: int = 0):
    """Get current user credit score history."""
    user = request.auth
    logs = user.credit_logs.all().order_by('-created_at')[offset:offset+limit]

    return [
        {
            "id": log.id,
            "action": log.get_action_display(),
            "amount": log.amount,
            "score_before": log.score_before,
            "score_after": log.score_after,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
