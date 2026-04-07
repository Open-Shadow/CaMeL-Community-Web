"""Skills API routes."""
from typing import List, Optional

from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from common.permissions import AuthBearer
from apps.skills.models import Skill, SkillStatus
from apps.skills.schemas import (
    SkillCreateInput, SkillUpdateInput, SkillOut,
    SkillCallInput, SkillCallOut, SkillReviewInput, SkillReviewOut,
    SkillTrendingOut, SkillVersionOut,
    SkillRecommendationOut,
    SkillUsagePreferenceInput, SkillUsagePreferenceOut,
    MessageOut,
)
from apps.skills.services import SkillService

router = Router(tags=["skills"])


def _skill_out(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "slug": skill.slug,
        "description": skill.description,
        "system_prompt": skill.system_prompt,
        "user_prompt_template": skill.user_prompt_template,
        "output_format": skill.output_format,
        "example_input": skill.example_input,
        "example_output": skill.example_output,
        "category": skill.category,
        "tags": skill.tags,
        "pricing_model": skill.pricing_model,
        "price_per_use": float(skill.price_per_use) if skill.price_per_use else None,
        "status": skill.status,
        "is_featured": skill.is_featured,
        "current_version": skill.current_version,
        "total_calls": skill.total_calls,
        "avg_rating": float(skill.avg_rating),
        "review_count": skill.review_count,
        "rejection_reason": skill.rejection_reason,
        "creator_id": skill.creator_id,
        "creator_name": skill.creator.display_name or skill.creator.username,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


@router.post("", response={201: SkillOut}, auth=AuthBearer())
def create_skill(request, data: SkillCreateInput):
    try:
        skill = SkillService.create(request.auth, data.dict())
    except ValueError as e:
        raise HttpError(400, str(e))
    return Status(201, _skill_out(skill))


@router.get("", response=List[SkillOut])
def list_skills(request, category: Optional[str] = None, q: Optional[str] = None,
                status: str = SkillStatus.APPROVED, sort: str = "latest",
                page: int = 1, page_size: int = 20):
    qs = Skill.objects.select_related("creator").filter(status=SkillStatus.APPROVED)
    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(tags__overlap=[q])
        )

    if sort == "rating":
        qs = qs.order_by("-avg_rating", "-review_count", "-created_at")
    elif sort == "calls":
        qs = qs.order_by("-total_calls", "-avg_rating", "-created_at")
    elif sort == "featured":
        qs = qs.order_by("-is_featured", "-created_at")
    else:
        qs = qs.order_by("-created_at")

    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    offset = (page - 1) * page_size
    return [_skill_out(s) for s in qs[offset:offset + page_size]]


@router.get("/mine", response=List[SkillOut], auth=AuthBearer())
def get_my_skills(request):
    qs = Skill.objects.select_related("creator").filter(creator=request.auth)
    return [_skill_out(s) for s in qs]


@router.get("/trending/list", response=List[SkillTrendingOut])
def list_trending_skills(request, limit: int = 10):
    skills = SkillService.list_trending(limit=limit)
    return [
        {
            "id": skill.id,
            "name": skill.name,
            "slug": skill.slug,
            "description": skill.description,
            "category": skill.category,
            "pricing_model": skill.pricing_model,
            "price_per_use": float(skill.price_per_use) if skill.price_per_use else None,
            "total_calls": skill.total_calls,
            "avg_rating": float(skill.avg_rating),
            "review_count": skill.review_count,
            "creator_name": skill.creator.display_name or skill.creator.username,
        }
        for skill in skills
    ]


@router.get("/recommended", response=List[SkillRecommendationOut], auth=AuthBearer())
def list_recommended_skills(request, limit: int = 8):
    recommendations = SkillService.list_recommended(request.auth, limit=limit)
    return [
        {
            "id": item["skill"].id,
            "name": item["skill"].name,
            "slug": item["skill"].slug,
            "description": item["skill"].description,
            "category": item["skill"].category,
            "pricing_model": item["skill"].pricing_model,
            "price_per_use": float(item["skill"].price_per_use) if item["skill"].price_per_use else None,
            "total_calls": item["skill"].total_calls,
            "avg_rating": float(item["skill"].avg_rating),
            "review_count": item["skill"].review_count,
            "creator_name": item["skill"].creator.display_name or item["skill"].creator.username,
            "recommendation_reason": item["reason"],
        }
        for item in recommendations
    ]


@router.get("/{skill_id}", response=SkillOut)
def get_skill(request, skill_id: int):
    skill = get_object_or_404(Skill.objects.select_related("creator"), id=skill_id)
    return _skill_out(skill)


@router.patch("/{skill_id}", response=SkillOut, auth=AuthBearer())
def update_skill(request, skill_id: int, data: SkillUpdateInput):
    skill = get_object_or_404(Skill, id=skill_id, creator=request.auth)
    skill = SkillService.update(skill, {k: v for k, v in data.dict().items() if v is not None})
    return _skill_out(skill)


@router.post("/{skill_id}/submit", response=SkillOut, auth=AuthBearer())
def submit_skill(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id, creator=request.auth)
    try:
        skill = SkillService.submit_for_review(skill)
    except ValueError as e:
        raise HttpError(400, str(e))
    return _skill_out(skill)


@router.post("/{skill_id}/archive", response=SkillOut, auth=AuthBearer())
def archive_skill(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id, creator=request.auth)
    try:
        skill = SkillService.archive(skill)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return _skill_out(skill)


@router.post("/{skill_id}/restore", response=SkillOut, auth=AuthBearer())
def restore_skill(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id, creator=request.auth)
    try:
        skill = SkillService.restore(skill)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return _skill_out(skill)


@router.delete("/{skill_id}", response=MessageOut, auth=AuthBearer())
def delete_skill(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id, creator=request.auth)
    SkillService.delete(skill)
    return {"message": "Skill 已删除"}


@router.post("/{skill_id}/call", response=SkillCallOut, auth=AuthBearer())
def call_skill(request, skill_id: int, data: SkillCallInput):
    skill = get_object_or_404(Skill.objects.select_related("creator"), id=skill_id)
    try:
        call = SkillService.call(skill, request.auth, data.input_text)
    except ValueError as e:
        raise HttpError(400, str(e))
    return {"output_text": call.output_text, "amount_charged": float(call.amount_charged), "duration_ms": call.duration_ms}


@router.post("/{skill_id}/reviews", response={201: SkillReviewOut}, auth=AuthBearer())
def add_review(request, skill_id: int, data: SkillReviewInput):
    skill = get_object_or_404(Skill, id=skill_id)
    try:
        review = SkillService.add_review(skill, request.auth, data.rating, data.comment, data.tags)
    except ValueError as e:
        raise HttpError(400, str(e))
    return Status(201, {
        "id": review.id, "rating": review.rating, "comment": review.comment,
        "tags": review.tags, "reviewer_id": review.reviewer_id,
        "reviewer_name": review.reviewer.display_name or review.reviewer.username,
        "created_at": review.created_at.isoformat(),
    })


@router.get("/{skill_id}/reviews", response=List[SkillReviewOut])
def list_reviews(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id)
    reviews = skill.reviews.select_related("reviewer").order_by("-created_at")
    return [{
        "id": r.id, "rating": r.rating, "comment": r.comment,
        "tags": r.tags, "reviewer_id": r.reviewer_id,
        "reviewer_name": r.reviewer.display_name or r.reviewer.username,
        "created_at": r.created_at.isoformat(),
    } for r in reviews]


@router.get("/{skill_id}/versions", response=List[SkillVersionOut])
def list_versions(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id)
    versions = SkillService.list_versions(skill)
    return [
        {
            "id": version.id,
            "version": version.version,
            "system_prompt": version.system_prompt,
            "user_prompt_template": version.user_prompt_template,
            "change_note": version.change_note,
            "is_major": version.is_major,
            "created_at": version.created_at.isoformat(),
        }
        for version in versions
    ]


@router.get("/{skill_id}/usage-preference", response=SkillUsagePreferenceOut, auth=AuthBearer())
def get_usage_preference(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id)
    preference = SkillService.get_usage_preference(skill, request.auth)
    return {
        "skill_id": skill.id,
        "locked_version": preference.locked_version,
        "auto_follow_latest": preference.auto_follow_latest,
    }


@router.post("/{skill_id}/usage-preference", response=SkillUsagePreferenceOut, auth=AuthBearer())
def update_usage_preference(request, skill_id: int, data: SkillUsagePreferenceInput):
    skill = get_object_or_404(Skill, id=skill_id)
    try:
        preference = SkillService.update_usage_preference(
            skill,
            request.auth,
            locked_version=data.locked_version,
            auto_follow_latest=data.auto_follow_latest,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return {
        "skill_id": skill.id,
        "locked_version": preference.locked_version,
        "auto_follow_latest": preference.auto_follow_latest,
    }
