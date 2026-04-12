"""Skills API routes."""
from typing import List, Optional

from ninja import Router, File, UploadedFile
from ninja.errors import HttpError
from ninja.responses import Status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from common.permissions import AuthBearer
from apps.skills.models import Skill, SkillStatus, SkillPurchase, VersionStatus
from apps.skills.schemas import (
    SkillCreateInput, SkillUpdateInput, SkillOut,
    SkillCallInput, SkillCallOut, SkillReviewInput, SkillReviewOut,
    SkillTrendingOut, SkillVersionOut,
    SkillRecommendationOut,
    SkillUsagePreferenceInput, SkillUsagePreferenceOut,
    SkillPurchaseInput, SkillPurchaseOut,
    SkillReportInput, SkillReportOut,
    MessageOut,
)
from apps.skills.services import SkillService, SkillPurchaseService, SkillReportService

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
        "price": float(skill.price) if skill.price else None,
        "status": skill.status,
        "is_featured": skill.is_featured,
        "current_version": skill.current_version,
        "total_calls": skill.total_calls,
        "avg_rating": float(skill.avg_rating),
        "review_count": skill.review_count,
        "rejection_reason": skill.rejection_reason,
        "readme_html": skill.readme_html,
        "package_size": skill.package_size,
        "download_count": skill.download_count,
        "creator_id": skill.creator_id,
        "creator_name": skill.creator.display_name or skill.creator.username,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


@router.post("", response={201: SkillOut}, auth=AuthBearer())
def create_skill(request, data: SkillCreateInput, package: UploadedFile = File(...)):
    from apps.skills.package_service import PackageService

    try:
        pkg_data = PackageService.process_upload(package)
    except ValueError as e:
        raise HttpError(400, str(e))

    merged = data.dict()
    merged.update(pkg_data)
    try:
        skill = SkillService.create(request.auth, merged)
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
            "price": float(skill.price) if skill.price else None,
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
            "price": float(item["skill"].price) if item["skill"].price else None,
            "total_calls": item["skill"].total_calls,
            "avg_rating": float(item["skill"].avg_rating),
            "review_count": item["skill"].review_count,
            "creator_name": item["skill"].creator.display_name or item["skill"].creator.username,
            "recommendation_reason": item["reason"],
        }
        for item in recommendations
    ]


@router.get("/purchased", response=List[SkillPurchaseOut], auth=AuthBearer())
def list_purchased_skills(request):
    purchases = SkillPurchase.objects.filter(user=request.auth).select_related("skill").order_by("-created_at")
    return [
        {
            "id": p.id,
            "skill_id": p.skill_id,
            "paid_amount": float(p.paid_amount),
            "payment_type": p.payment_type,
            "created_at": p.created_at.isoformat(),
        }
        for p in purchases
    ]


@router.get("/{skill_id}", response=SkillOut)
def get_skill(request, skill_id: int):
    skill = get_object_or_404(Skill.objects.select_related("creator"), id=skill_id)
    return _skill_out(skill)


@router.patch("/{skill_id}", response=SkillOut, auth=AuthBearer())
def update_skill(request, skill_id: int, data: SkillUpdateInput, package: UploadedFile = File(None)):
    skill = get_object_or_404(Skill, id=skill_id, creator=request.auth)
    merged = {k: v for k, v in data.dict().items() if v is not None}

    if package:
        from apps.skills.package_service import PackageService
        try:
            pkg_data = PackageService.process_upload(package)
        except ValueError as e:
            raise HttpError(400, str(e))
        merged.update(pkg_data)

    try:
        skill = SkillService.update(skill, merged)
    except ValueError as e:
        raise HttpError(400, str(e))
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


@router.post("/{skill_id}/purchase", response={201: SkillPurchaseOut}, auth=AuthBearer())
def purchase_skill(request, skill_id: int):
    skill = get_object_or_404(Skill.objects.select_related("creator"), id=skill_id)
    try:
        purchase = SkillPurchaseService.purchase(skill, request.auth)
    except ValueError as e:
        raise HttpError(400, str(e))
    return Status(201, {
        "id": purchase.id,
        "skill_id": purchase.skill_id,
        "paid_amount": float(purchase.paid_amount),
        "payment_type": purchase.payment_type,
        "created_at": purchase.created_at.isoformat(),
    })


@router.get("/{skill_id}/download", auth=AuthBearer())
def download_skill(request, skill_id: int):
    skill = get_object_or_404(Skill, id=skill_id)

    if not SkillPurchaseService.has_access(skill, request.auth):
        raise HttpError(403, "请先购买该 Skill")

    if not skill.package_file:
        raise HttpError(404, "Skill 文件包不存在")

    from apps.skills.package_service import PackageService
    url = PackageService.generate_download_url(skill.package_file.name)

    skill.download_count += 1
    skill.save(update_fields=["download_count"])

    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(url)


@router.post("/{skill_id}/call", response=SkillCallOut, auth=AuthBearer())
def call_skill(request, skill_id: int, data: SkillCallInput):
    skill = get_object_or_404(Skill.objects.select_related("creator"), id=skill_id)
    try:
        call = SkillService.call(skill, request.auth, data.input_text)
    except ValueError as e:
        raise HttpError(400, str(e))
    return {"output_text": call.output_text, "duration_ms": call.duration_ms}


@router.post("/{skill_id}/report", response={201: SkillReportOut}, auth=AuthBearer())
def report_skill(request, skill_id: int, data: SkillReportInput):
    skill = get_object_or_404(Skill, id=skill_id)
    try:
        report = SkillReportService.report(skill, request.auth, data.reason, data.detail)
    except ValueError as e:
        raise HttpError(400, str(e))
    return Status(201, {
        "id": report.id,
        "skill_id": report.skill_id,
        "reason": report.reason,
        "detail": report.detail,
        "created_at": report.created_at.isoformat(),
    })


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
    versions = SkillService.list_versions(skill).filter(status=VersionStatus.APPROVED)
    return [
        {
            "id": version.id,
            "version": version.version,
            "changelog": version.changelog,
            "status": version.status,
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
        "locked_version": preference.locked_version or None,
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
        "locked_version": preference.locked_version or None,
        "auto_follow_latest": preference.auto_follow_latest,
    }
