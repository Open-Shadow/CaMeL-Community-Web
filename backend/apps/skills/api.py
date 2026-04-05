"""Skills API routes."""
from typing import List, Optional
from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404

from common.permissions import AuthBearer
from apps.skills.models import Skill, SkillStatus
from apps.skills.schemas import (
    SkillCreateInput, SkillUpdateInput, SkillOut,
    SkillCallInput, SkillCallOut, SkillReviewInput, SkillReviewOut,
)
from apps.skills.services import SkillService

router = Router(tags=["skills"])


def _skill_out(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "slug": skill.slug,
        "description": skill.description,
        "category": skill.category,
        "tags": skill.tags,
        "pricing_model": skill.pricing_model,
        "price_per_use": float(skill.price_per_use) if skill.price_per_use else None,
        "status": skill.status,
        "is_featured": skill.is_featured,
        "total_calls": skill.total_calls,
        "avg_rating": float(skill.avg_rating),
        "review_count": skill.review_count,
        "creator_id": skill.creator_id,
        "creator_name": skill.creator.display_name or skill.creator.username,
        "created_at": skill.created_at.isoformat(),
    }


@router.post("", response={201: SkillOut}, auth=AuthBearer())
def create_skill(request, data: SkillCreateInput):
    skill = SkillService.create(request.auth, data.dict())
    return 201, _skill_out(skill)


@router.get("", response=List[SkillOut])
def list_skills(request, category: Optional[str] = None, q: Optional[str] = None,
                status: str = SkillStatus.APPROVED, page: int = 1, page_size: int = 20):
    qs = Skill.objects.select_related("creator").filter(status=status)
    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(name__icontains=q)
    offset = (page - 1) * page_size
    return [_skill_out(s) for s in qs[offset:offset + page_size]]


@router.get("/mine", response=List[SkillOut], auth=AuthBearer())
def get_my_skills(request):
    qs = Skill.objects.select_related("creator").filter(creator=request.auth)
    return [_skill_out(s) for s in qs]


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
    return 201, {
        "id": review.id, "rating": review.rating, "comment": review.comment,
        "tags": review.tags, "reviewer_id": review.reviewer_id,
        "reviewer_name": review.reviewer.display_name or review.reviewer.username,
        "created_at": review.created_at.isoformat(),
    }


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
