"""Bounties API routes."""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Body, Router
from ninja.errors import HttpError

from apps.bounties.models import Bounty
from apps.bounties.schemas import (
    AdminArbitrationDecisionInput,
    ActiveDisputeOut,
    ArbitrationAppealInput,
    ArbitrationStatementInput,
    ArbitrationVoteInput,
    BountyApplicationInput,
    BountyCommentInput,
    BountyCreateInput,
    BountyDecisionInput,
    BountyDeliverableInput,
    BountyDetailOut,
    BountyListOut,
    BountyReviewInput,
    BountySummaryOut,
    MessageOut,
)
from apps.bounties.services import BountyError, BountyService
from apps.payments.services import PaymentError
from common.permissions import AuthBearer, admin_required

router = Router(tags=["bounties"])


def _get_optional_user(request):
    """Extract authenticated user from request if present, without requiring auth."""
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import TokenError
    from django.contrib.auth import get_user_model
    User = get_user_model()
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = AccessToken(token)
        user = User.objects.get(id=payload["user_id"])
        if not user.is_active:
            return None
        return user
    except (TokenError, User.DoesNotExist, KeyError):
        return None


def _user_out(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "level": user.level,
        "credit_score": user.credit_score,
    }


def _application_out(application) -> dict:
    return {
        "id": application.id,
        "proposal": application.proposal,
        "estimated_days": application.estimated_days,
        "applicant": _user_out(application.applicant),
        "created_at": application.created_at.isoformat(),
    }


def _deliverable_out(deliverable) -> dict:
    return {
        "id": deliverable.id,
        "content": deliverable.content,
        "attachments": deliverable.attachments,
        "revision_number": deliverable.revision_number,
        "submitter": _user_out(deliverable.submitter),
        "created_at": deliverable.created_at.isoformat(),
    }


def _comment_out(comment) -> dict:
    return {
        "id": comment.id,
        "content": comment.content,
        "author": _user_out(comment.author),
        "created_at": comment.created_at.isoformat(),
    }


def _arbitration_out(arbitration) -> dict:
    if not arbitration:
        return None
    return {
        "id": arbitration.id,
        "creator_statement": arbitration.creator_statement,
        "hunter_statement": arbitration.hunter_statement,
        "result": arbitration.result,
        "hunter_ratio": float(arbitration.hunter_ratio) if arbitration.hunter_ratio is not None else None,
        "appeal_by_id": arbitration.appeal_by_id,
        "appeal_fee_paid": arbitration.appeal_fee_paid,
        "admin_final_result": arbitration.admin_final_result,
        "deadline": arbitration.deadline.isoformat() if arbitration.deadline else None,
        "resolved_at": arbitration.resolved_at.isoformat() if arbitration.resolved_at else None,
        "arbitrators": [_user_out(user) for user in arbitration.arbitrators.all()],
        "votes": [
            {
                "id": vote.id,
                "arbitrator": _user_out(vote.arbitrator),
                "vote": vote.vote,
                "hunter_ratio": float(vote.hunter_ratio) if vote.hunter_ratio is not None else None,
                "created_at": vote.created_at.isoformat(),
            }
            for vote in arbitration.votes.select_related("arbitrator").all()
        ],
    }


def _summary_out(bounty) -> dict:
    accepted_applicant = bounty.accepted_application.applicant if bounty.accepted_application_id else None
    return {
        "id": bounty.id,
        "title": bounty.title,
        "description": bounty.description,
        "attachments": bounty.attachments,
        "skill_requirements": bounty.skill_requirements,
        "bounty_type": bounty.bounty_type,
        "max_applicants": bounty.max_applicants,
        "workload_estimate": bounty.workload_estimate,
        "reward": float(bounty.reward),
        "status": bounty.status,
        "deadline": bounty.deadline.isoformat(),
        "revision_count": bounty.revision_count,
        "is_cold": bounty.is_cold,
        "application_count": getattr(bounty, "application_count", bounty.applications.count()),
        "creator": _user_out(bounty.creator),
        "accepted_applicant": _user_out(accepted_applicant) if accepted_applicant else None,
        "created_at": bounty.created_at.isoformat(),
        "updated_at": bounty.updated_at.isoformat(),
    }


def _is_bounty_participant(bounty, user) -> bool:
    """Check if user is a participant (creator, accepted applicant, or arbitrator)."""
    if user is None:
        return False
    if user.id == bounty.creator_id:
        return True
    if bounty.accepted_application_id and bounty.accepted_application.applicant_id == user.id:
        return True
    arbitration = getattr(bounty, "arbitration", None)
    if arbitration and arbitration.arbitrators.filter(id=user.id).exists():
        return True
    return False


def _detail_out(bounty, viewer=None) -> dict:
    arbitration = getattr(bounty, "arbitration", None)
    is_participant = _is_bounty_participant(bounty, viewer)
    return {
        **_summary_out(bounty),
        "applications": [_application_out(item) for item in bounty.applications.select_related("applicant").all()] if is_participant else [],
        "deliverables": [_deliverable_out(item) for item in bounty.deliverables.select_related("submitter").all()] if is_participant else [],
        "comments": [_comment_out(item) for item in bounty.comments.select_related("author").order_by("created_at")],
        "reviews": [
            {
                "id": review.id,
                "reviewer": _user_out(review.reviewer),
                "reviewee": _user_out(review.reviewee),
                "quality_rating": review.quality_rating,
                "communication_rating": review.communication_rating,
                "responsiveness_rating": review.responsiveness_rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat(),
            }
            for review in bounty.reviews.select_related("reviewer", "reviewee").all()
        ],
        "arbitration": _arbitration_out(arbitration) if is_participant else None,
    }


@router.get("", response=BountyListOut)
def list_bounties(request, q: str | None = None, status: str | None = None, bounty_type: str | None = None, limit: int = 20, offset: int = 0):
    queryset = BountyService.list_bounties(q=q, status=status, bounty_type=bounty_type)
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    items = list(queryset[safe_offset:safe_offset + safe_limit])
    return {
        "items": [_summary_out(item) for item in items],
        "total": queryset.count(),
        "limit": safe_limit,
        "offset": safe_offset,
    }


@router.get("/mine", response=BountyListOut, auth=AuthBearer())
def list_my_bounties(request, role: str = "all", limit: int = 20, offset: int = 0):
    queryset = Bounty.objects.select_related("creator", "accepted_application__applicant").annotate(application_count=Count("applications"))
    if role == "creator":
        queryset = queryset.filter(creator=request.auth)
    elif role == "hunter":
        queryset = queryset.filter(applications__applicant=request.auth).distinct()
    else:
        queryset = queryset.filter(Q(creator=request.auth) | Q(applications__applicant=request.auth)).distinct()
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    items = list(queryset.order_by("-created_at")[safe_offset:safe_offset + safe_limit])
    return {
        "items": [_summary_out(item) for item in items],
        "total": queryset.count(),
        "limit": safe_limit,
        "offset": safe_offset,
    }


@router.get("/{bounty_id}", response=BountyDetailOut)
def get_bounty(request, bounty_id: int):
    bounty = get_object_or_404(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "applications__applicant",
            "deliverables__submitter",
            "comments__author",
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ),
        id=bounty_id,
    )
    return _detail_out(bounty, viewer=_get_optional_user(request))


@router.post("", response={201: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def create_bounty(request, data: BountyCreateInput):
    try:
        bounty = BountyService.create_bounty(request.auth, data.dict())
    except (BountyError, PaymentError) as exc:
        return 400, {"message": str(exc)}
    return 201, _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/apply", response={201: MessageOut, 400: MessageOut}, auth=AuthBearer())
def apply_bounty(request, bounty_id: int, data: BountyApplicationInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator"), id=bounty_id)
    try:
        BountyService.apply(bounty, request.auth, data.proposal, data.estimated_days)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return 201, {"message": "申请已提交"}


@router.post("/{bounty_id}/accept/{application_id}", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def accept_application(request, bounty_id: int, application_id: int):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.accept_application(request.auth, bounty, application_id)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    bounty.refresh_from_db()
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related("applications__applicant").get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/reject/{application_id}", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def reject_application(request, bounty_id: int, application_id: int):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.reject_application(request.auth, bounty, application_id)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    bounty.refresh_from_db()
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "applications__applicant",
            "comments__author",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/comments", response={201: MessageOut, 400: MessageOut}, auth=AuthBearer())
def add_comment(request, bounty_id: int, data: BountyCommentInput):
    bounty = get_object_or_404(Bounty, id=bounty_id)
    try:
        BountyService.add_comment(request.auth, bounty, data.content)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return 201, {"message": "评论已发布"}


@router.post("/{bounty_id}/submit", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def submit_delivery(request, bounty_id: int, data: BountyDeliverableInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.submit_delivery(request.auth, bounty, data.content, data.attachments)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "applications__applicant",
            "deliverables__submitter",
            "comments__author",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/approve", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def approve_bounty(request, bounty_id: int):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.approve_delivery(request.auth, bounty)
    except (BountyError, PaymentError) as exc:
        return 400, {"message": str(exc)}
    return _detail_out(Bounty.objects.select_related("creator", "accepted_application__applicant").get(id=bounty.id), viewer=request.auth)


@router.post("/{bounty_id}/revision", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def request_revision(request, bounty_id: int, data: BountyDecisionInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.request_revision(request.auth, bounty, data.feedback)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related("comments__author").get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/cancel", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def cancel_bounty(request, bounty_id: int, data: BountyDecisionInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.cancel_bounty(request.auth, bounty, reason=data.feedback)
    except (BountyError, PaymentError) as exc:
        return 400, {"message": str(exc)}
    return _detail_out(Bounty.objects.select_related("creator", "accepted_application__applicant").get(id=bounty.id), viewer=request.auth)


@router.post("/{bounty_id}/dispute", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def create_dispute(request, bounty_id: int, data: ArbitrationStatementInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.create_dispute(request.auth, bounty, data.content)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/arbitration/statement", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def submit_statement(request, bounty_id: int, data: ArbitrationStatementInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.submit_statement(request.auth, bounty, data.content)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/arbitration/start", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def start_arbitration(request, bounty_id: int):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.start_arbitration(request.auth, bounty)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/arbitration/vote", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def cast_arbitration_vote(request, bounty_id: int, data: ArbitrationVoteInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.cast_vote(request.auth, bounty, data.vote, data.hunter_ratio)
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/arbitration/appeal", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def appeal_arbitration(request, bounty_id: int, data: ArbitrationAppealInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.appeal(request.auth, bounty, data.reason)
    except (BountyError, PaymentError) as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/arbitration/admin-finalize", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
@admin_required
def admin_finalize_arbitration(request, bounty_id: int, data: AdminArbitrationDecisionInput = Body(...)):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.admin_finalize(request.auth, bounty, data.result, data.hunter_ratio)
    except (BountyError, PaymentError) as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "arbitration__arbitrators",
            "arbitration__votes__arbitrator",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.post("/{bounty_id}/reviews", response={200: BountyDetailOut, 400: MessageOut}, auth=AuthBearer())
def add_bounty_review(request, bounty_id: int, data: BountyReviewInput):
    bounty = get_object_or_404(Bounty.objects.select_related("creator", "accepted_application__applicant"), id=bounty_id)
    try:
        BountyService.add_review(
            request.auth,
            bounty,
            quality_rating=data.quality_rating,
            communication_rating=data.communication_rating,
            responsiveness_rating=data.responsiveness_rating,
            comment=data.comment,
        )
    except BountyError as exc:
        return 400, {"message": str(exc)}
    return _detail_out(
        Bounty.objects.select_related("creator", "accepted_application__applicant").prefetch_related(
            "reviews__reviewer",
            "reviews__reviewee",
        ).get(id=bounty.id),
        viewer=request.auth,
    )


@router.get("/admin/arbitrations", response=list[ActiveDisputeOut], auth=AuthBearer())
def list_active_disputes(request):
    if request.auth.role not in {"MODERATOR", "ADMIN"}:
        raise HttpError(403, "需要版主权限")
    disputes = BountyService.list_active_disputes()
    return [
        {
            "id": bounty.id,
            "title": bounty.title,
            "status": bounty.status,
            "creator": _user_out(bounty.creator),
            "accepted_applicant": _user_out(bounty.accepted_application.applicant) if bounty.accepted_application_id else None,
            "arbitration": _arbitration_out(getattr(bounty, "arbitration", None)),
        }
        for bounty in disputes
    ]
