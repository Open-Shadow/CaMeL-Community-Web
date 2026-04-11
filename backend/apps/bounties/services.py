"""Bounties business logic."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.bounties.models import (
    Arbitration,
    ArbitrationVote,
    Bounty,
    BountyApplication,
    BountyComment,
    BountyDeliverable,
    BountyReview,
    BountyStatus,
    BountyType,
    WorkloadEstimate,
)
from apps.credits.models import CreditAction, CreditLog
from apps.credits.services import CreditService
from apps.payments.services import PaymentError, PaymentsService, quantize_amount


class BountyError(ValueError):
    """Raised when a bounty transition is invalid."""


class BountyService:
    """Bounty marketplace and arbitration business logic."""

    MAX_ATTACHMENTS = 5
    MAX_ATTACHMENT_URL_LENGTH = 500
    MAX_SKILL_REQUIREMENT_LENGTH = 2000
    MAX_APPLICANTS = 20

    @staticmethod
    def _parse_deadline(deadline: str):
        parsed = parse_datetime(deadline)
        if not parsed:
            raise BountyError("截止时间格式无效")
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        if parsed <= timezone.now():
            raise BountyError("截止时间必须晚于当前时间")
        return parsed

    @staticmethod
    def _assert_bounty_available_for_apply(bounty: Bounty):
        if bounty.status != BountyStatus.OPEN:
            raise BountyError("当前悬赏不可申请")
        if bounty.deadline <= timezone.now():
            raise BountyError("悬赏已截止")

    @staticmethod
    def _accepted_user(bounty: Bounty):
        if not bounty.accepted_application_id:
            return None
        return bounty.accepted_application.applicant

    @classmethod
    def process_automations(cls):
        now = timezone.now()

        cold_queryset = Bounty.objects.filter(
            status=BountyStatus.OPEN,
            is_cold=False,
            created_at__lte=now - timedelta(hours=72),
        ).annotate(application_count=Count("applications"))
        for bounty in cold_queryset:
            if bounty.application_count == 0:
                bounty.is_cold = True
                bounty.save(update_fields=["is_cold"])

        overdue_queryset = Bounty.objects.filter(
            status__in=[BountyStatus.IN_PROGRESS, BountyStatus.REVISION],
            deadline__lt=now,
            accepted_application__isnull=False,
        ).select_related("accepted_application__applicant")
        for bounty in overdue_queryset:
            applicant = bounty.accepted_application.applicant
            if not CreditLog.objects.filter(
                user=applicant,
                action=CreditAction.BOUNTY_TIMEOUT,
                reference_id=f"bounty-timeout:{bounty.id}",
            ).exists():
                CreditService.deduct_credit(applicant, CreditAction.BOUNTY_TIMEOUT, f"bounty-timeout:{bounty.id}")
            bounty.accepted_application = None
            bounty.status = BountyStatus.OPEN
            bounty.save(update_fields=["accepted_application", "status"])

        review_queryset = Bounty.objects.filter(
            status__in=[BountyStatus.DELIVERED, BountyStatus.IN_REVIEW],
        )
        for bounty in review_queryset:
            latest_delivery = bounty.deliverables.order_by("-created_at").first()
            if latest_delivery and latest_delivery.created_at <= now - timedelta(days=7):
                cls.approve_delivery(bounty.creator, bounty)

    @classmethod
    @transaction.atomic
    def create_bounty(cls, creator, data: dict) -> Bounty:
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        if not title:
            raise BountyError("悬赏标题不能为空")
        if not description:
            raise BountyError("悬赏描述不能为空")

        reward = quantize_amount(data["reward"])
        if reward < Decimal("1.00"):
            raise BountyError("悬赏金额至少为 $1.00")
        if data["bounty_type"] not in set(BountyType.values):
            raise BountyError("悬赏类型无效")
        if not CreditService.can_post_bounty(creator):
            raise BountyError("当前信用分不足，暂不能发布悬赏")

        deadline = cls._parse_deadline(data["deadline"])
        max_applicants = int(data.get("max_applicants") or 1)
        if max_applicants < 1 or max_applicants > cls.MAX_APPLICANTS:
            raise BountyError(f"最大申请人数需在 1 到 {cls.MAX_APPLICANTS} 之间")

        workload_estimate = (data.get("workload_estimate") or "").strip()
        if workload_estimate and workload_estimate not in set(WorkloadEstimate.values):
            raise BountyError("预计工作量无效")

        raw_attachments = data.get("attachments") or []
        if not isinstance(raw_attachments, list):
            raise BountyError("附件格式无效")
        attachments: list[str] = []
        for item in raw_attachments:
            value = str(item).strip()
            if not value:
                continue
            attachments.append(value[: cls.MAX_ATTACHMENT_URL_LENGTH])
        if len(attachments) > cls.MAX_ATTACHMENTS:
            raise BountyError(f"附件最多上传 {cls.MAX_ATTACHMENTS} 个")

        skill_requirements = (data.get("skill_requirements") or "").strip()
        if len(skill_requirements) > cls.MAX_SKILL_REQUIREMENT_LENGTH:
            raise BountyError("技能要求内容过长")

        PaymentsService.reserve_bounty_escrow(creator, reward, reference_id=f"bounty:{creator.id}:{title}")

        bounty = Bounty.objects.create(
            creator=creator,
            title=title,
            description=description,
            attachments=attachments,
            skill_requirements=skill_requirements,
            bounty_type=data["bounty_type"],
            max_applicants=max_applicants,
            workload_estimate=workload_estimate,
            reward=reward,
            deadline=deadline,
        )
        return bounty

    @classmethod
    def list_bounties(cls, *, q: str | None = None, status: str | None = None, bounty_type: str | None = None):
        queryset = Bounty.objects.select_related("creator", "accepted_application__applicant").annotate(
            application_count=Count("applications")
        )
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status:
            queryset = queryset.filter(status=status)
        if bounty_type:
            queryset = queryset.filter(bounty_type=bounty_type)
        return queryset.order_by("-created_at")

    @classmethod
    @transaction.atomic
    def apply(cls, bounty: Bounty, applicant, proposal: str, estimated_days: int) -> BountyApplication:
        cls._assert_bounty_available_for_apply(bounty)
        if bounty.creator_id == applicant.id:
            raise BountyError("不能申请自己发布的悬赏")
        if not CreditService.can_apply_bounty(applicant):
            raise BountyError("当前信用分不足，暂不能接单")
        if estimated_days <= 0:
            raise BountyError("预计天数必须大于 0")

        existing = BountyApplication.objects.filter(bounty=bounty, applicant=applicant).first()
        if not existing and bounty.applications.count() >= bounty.max_applicants:
            raise BountyError("该悬赏已达到最大申请人数")

        application, created = BountyApplication.objects.get_or_create(
            bounty=bounty,
            applicant=applicant,
            defaults={
                "proposal": proposal.strip(),
                "estimated_days": estimated_days,
            },
        )
        if not created:
            application.proposal = proposal.strip()
            application.estimated_days = estimated_days
            application.save(update_fields=["proposal", "estimated_days"])
        return application

    @classmethod
    @transaction.atomic
    def accept_application(cls, actor, bounty: Bounty, application_id: int) -> Bounty:
        if bounty.creator_id != actor.id:
            raise BountyError("只有发布者可以选择接单者")
        if bounty.status != BountyStatus.OPEN:
            raise BountyError("当前状态下不能选择接单者")

        application = BountyApplication.objects.filter(id=application_id, bounty=bounty).select_related("applicant").first()
        if not application:
            raise BountyError("申请不存在")

        bounty.accepted_application = application
        bounty.status = BountyStatus.IN_PROGRESS
        bounty.save(update_fields=["accepted_application", "status"])
        return bounty

    @classmethod
    @transaction.atomic
    def add_comment(cls, actor, bounty: Bounty, content: str) -> BountyComment:
        normalized = content.strip()
        if not normalized:
            raise BountyError("评论内容不能为空")
        return BountyComment.objects.create(bounty=bounty, author=actor, content=normalized[:1000])

    @classmethod
    @transaction.atomic
    def submit_delivery(cls, actor, bounty: Bounty, content: str, attachments: list[str] | None = None) -> BountyDeliverable:
        accepted_user = cls._accepted_user(bounty)
        if not accepted_user or accepted_user.id != actor.id:
            raise BountyError("只有被接受的接单者可以提交交付")
        if bounty.status not in [BountyStatus.IN_PROGRESS, BountyStatus.REVISION]:
            raise BountyError("当前状态下不能提交交付")
        normalized = content.strip()
        if not normalized:
            raise BountyError("交付内容不能为空")

        deliverable = BountyDeliverable.objects.create(
            bounty=bounty,
            submitter=actor,
            content=normalized,
            attachments=attachments or [],
            revision_number=bounty.revision_count + 1,
        )
        bounty.status = BountyStatus.DELIVERED
        bounty.save(update_fields=["status"])
        return deliverable

    @classmethod
    @transaction.atomic
    def request_revision(cls, actor, bounty: Bounty, feedback: str) -> Bounty:
        if bounty.creator_id != actor.id:
            raise BountyError("只有发布者可以要求修改")
        if bounty.status not in [BountyStatus.DELIVERED, BountyStatus.IN_REVIEW]:
            raise BountyError("当前状态下不能要求修改")
        if bounty.revision_count >= 3:
            raise BountyError("最多只能要求 3 轮修改")

        bounty.revision_count += 1
        bounty.status = BountyStatus.REVISION
        bounty.save(update_fields=["revision_count", "status"])
        if feedback.strip():
            BountyComment.objects.create(bounty=bounty, author=actor, content=f"修改意见：{feedback.strip()[:980]}")
        return bounty

    @classmethod
    @transaction.atomic
    def approve_delivery(cls, actor, bounty: Bounty) -> Bounty:
        if bounty.creator_id != actor.id:
            raise BountyError("只有发布者可以验收通过")
        if bounty.status not in [BountyStatus.DELIVERED, BountyStatus.IN_REVIEW]:
            raise BountyError("当前状态下不能验收")
        if not bounty.accepted_application_id:
            raise BountyError("当前悬赏没有有效接单者")

        applicant = bounty.accepted_application.applicant
        PaymentsService.settle_bounty_payout(
            bounty.creator,
            applicant,
            bounty.reward,
            reference_id=f"bounty:{bounty.id}:complete",
        )
        CreditService.add_credit(applicant, CreditAction.BOUNTY_COMPLETED, str(bounty.id))
        bounty.status = BountyStatus.COMPLETED
        bounty.save(update_fields=["status"])
        return bounty

    @classmethod
    @transaction.atomic
    def cancel_bounty(cls, actor, bounty: Bounty, *, reason: str = "") -> Bounty:
        if bounty.creator_id != actor.id:
            raise BountyError("只有发布者可以取消悬赏")
        if bounty.status not in [BountyStatus.OPEN, BountyStatus.IN_PROGRESS]:
            raise BountyError("当前状态下不能取消悬赏")

        if bounty.creator.frozen_balance > 0:
            PaymentsService.release_bounty_to_creator(
                bounty.creator,
                bounty.reward,
                reference_id=f"bounty:{bounty.id}:cancel",
            )
        bounty.status = BountyStatus.CANCELLED
        bounty.save(update_fields=["status"])
        if reason.strip():
            BountyComment.objects.create(bounty=bounty, author=actor, content=f"取消原因：{reason.strip()[:980]}")
        return bounty

    @classmethod
    @transaction.atomic
    def create_dispute(cls, actor, bounty: Bounty, content: str) -> Arbitration:
        accepted_user = cls._accepted_user(bounty)
        if bounty.status not in [BountyStatus.DELIVERED, BountyStatus.IN_REVIEW, BountyStatus.REVISION]:
            raise BountyError("当前状态下不能发起争议")
        if actor.id not in {bounty.creator_id, accepted_user.id if accepted_user else None}:
            raise BountyError("只有交易双方可以发起争议")

        arbitration, _created = Arbitration.objects.get_or_create(bounty=bounty)
        if actor.id == bounty.creator_id:
            arbitration.creator_statement = content.strip()
        elif accepted_user:
            arbitration.hunter_statement = content.strip()
        arbitration.deadline = timezone.now() + timedelta(hours=24)
        arbitration.save()

        bounty.status = BountyStatus.DISPUTED
        bounty.save(update_fields=["status"])
        return arbitration

    @classmethod
    @transaction.atomic
    def submit_statement(cls, actor, bounty: Bounty, content: str) -> Arbitration:
        accepted_user = cls._accepted_user(bounty)
        arbitration = Arbitration.objects.filter(bounty=bounty).first()
        if not arbitration:
            raise BountyError("当前悬赏没有争议案例")
        if actor.id == bounty.creator_id:
            arbitration.creator_statement = content.strip()
        elif accepted_user and actor.id == accepted_user.id:
            arbitration.hunter_statement = content.strip()
        else:
            raise BountyError("只有交易双方可以提交陈述")
        arbitration.save()
        return arbitration

    @classmethod
    @transaction.atomic
    def start_arbitration(cls, actor, bounty: Bounty) -> Arbitration:
        accepted_user = cls._accepted_user(bounty)
        if actor.id not in {bounty.creator_id, accepted_user.id if accepted_user else None}:
            raise BountyError("只有交易双方可以启动仲裁")
        if bounty.status != BountyStatus.DISPUTED:
            raise BountyError("只有争议中的悬赏才能启动仲裁")
        arbitration = Arbitration.objects.filter(bounty=bounty).first()
        if not arbitration:
            raise BountyError("当前悬赏没有争议案例")
        if arbitration.resolved_at:
            raise BountyError("该仲裁已有结果，如有异议请通过上诉流程处理")
        if arbitration.deadline and arbitration.deadline > timezone.now():
            raise BountyError("冷静期尚未结束")

        accepted_user = cls._accepted_user(bounty)
        exclude_ids = [bounty.creator_id]
        if accepted_user:
            exclude_ids.append(accepted_user.id)

        candidates = (
            bounty.creator.__class__.objects.filter(credit_score__gte=500)
            .exclude(id__in=exclude_ids)
            .order_by("-credit_score", "id")[:3]
        )
        arbitration.arbitrators.set(candidates)
        arbitration.save()
        bounty.status = BountyStatus.ARBITRATING
        bounty.save(update_fields=["status"])
        return arbitration

    @classmethod
    @transaction.atomic
    def cast_vote(cls, actor, bounty: Bounty, vote: str, hunter_ratio: float | None = None) -> Arbitration:
        arbitration = Arbitration.objects.prefetch_related("arbitrators").filter(bounty=bounty).first()
        if not arbitration:
            raise BountyError("当前悬赏没有仲裁案例")
        if bounty.status != BountyStatus.ARBITRATING:
            raise BountyError("当前还未进入仲裁投票阶段")
        if actor.id not in set(arbitration.arbitrators.values_list("id", flat=True)):
            raise BountyError("当前用户不是该仲裁案陪审员")
        if vote not in {"HUNTER_WIN", "CREATOR_WIN", "PARTIAL"}:
            raise BountyError("仲裁投票结果无效")

        ArbitrationVote.objects.update_or_create(
            arbitration=arbitration,
            arbitrator=actor,
            defaults={
                "vote": vote,
                "hunter_ratio": hunter_ratio if vote == "PARTIAL" else None,
            },
        )
        cls._try_finalize_arbitration(arbitration)
        return arbitration

    @classmethod
    @transaction.atomic
    def appeal(cls, actor, bounty: Bounty, reason: str = "") -> Arbitration:
        arbitration = Arbitration.objects.filter(bounty=bounty).first()
        if not arbitration or not arbitration.resolved_at:
            raise BountyError("当前案件尚未形成可上诉结果")
        accepted_user = cls._accepted_user(bounty)
        if actor.id not in {bounty.creator_id, accepted_user.id if accepted_user else None}:
            raise BountyError("只有交易双方可以上诉")
        PaymentsService.charge_appeal_fee(actor, reference_id=f"arbitration:{arbitration.id}:appeal")
        arbitration.appeal_by = actor
        arbitration.appeal_fee_paid = True
        if reason.strip():
            if actor.id == bounty.creator_id:
                arbitration.creator_statement = f"{arbitration.creator_statement}\n\n上诉理由：{reason.strip()}".strip()
            else:
                arbitration.hunter_statement = f"{arbitration.hunter_statement}\n\n上诉理由：{reason.strip()}".strip()
        arbitration.save()
        # Set bounty back to DISPUTED so admin dispute list picks it up
        bounty.status = BountyStatus.DISPUTED
        bounty.save(update_fields=["status"])
        return arbitration

    @classmethod
    @transaction.atomic
    def admin_finalize(cls, actor, bounty: Bounty, result: str, hunter_ratio: float | None = None) -> Arbitration:
        if actor.role != "ADMIN":
            raise BountyError("需要管理员权限")
        arbitration = Arbitration.objects.filter(bounty=bounty).first()
        if not arbitration:
            raise BountyError("当前案件不存在")

        if arbitration.resolved_at:
            # Appealed case: community arbitration already settled (money moved).
            # Admin must confirm the existing settlement — contradictory results
            # would create inconsistent metadata since funds cannot be re-moved.
            if result not in {"HUNTER_WIN", "CREATOR_WIN", "PARTIAL"}:
                raise BountyError("仲裁结果无效")
            if result != arbitration.result:
                raise BountyError(
                    f"仲裁资金已按 {arbitration.result} 结果分配，"
                    f"无法改判为 {result}，如需变更请先撤销原结算"
                )
            arbitration.admin_final_result = result
            arbitration.save(update_fields=["admin_final_result"])
            # Restore bounty to correct terminal status based on the
            # original settlement ratio (funds already distributed).
            ratio = arbitration.hunter_ratio or Decimal("0")
            bounty.status = BountyStatus.COMPLETED if ratio > 0 else BountyStatus.CANCELLED
            bounty.save(update_fields=["status"])
        else:
            # First-time admin resolution (no prior community settlement).
            cls._apply_arbitration_result(arbitration, result, hunter_ratio)
            arbitration.admin_final_result = result
            arbitration.save(update_fields=["admin_final_result"])

        return arbitration

    @classmethod
    @transaction.atomic
    def add_review(
        cls,
        actor,
        bounty: Bounty,
        *,
        quality_rating: int,
        communication_rating: int,
        responsiveness_rating: int,
        comment: str = "",
    ) -> BountyReview:
        if bounty.status not in [BountyStatus.COMPLETED, BountyStatus.CANCELLED]:
            raise BountyError("只有已结束的悬赏才可互评")
        accepted_user = cls._accepted_user(bounty)
        if not accepted_user:
            raise BountyError("当前悬赏没有接单者，无法互评")
        if actor.id == bounty.creator_id:
            reviewee = accepted_user
        elif actor.id == accepted_user.id:
            reviewee = bounty.creator
        else:
            raise BountyError("只有交易双方可以互评")

        ratings = [quality_rating, communication_rating, responsiveness_rating]
        if any(rating < 1 or rating > 5 for rating in ratings):
            raise BountyError("评分须在 1 到 5 之间")

        review, _created = BountyReview.objects.update_or_create(
            bounty=bounty,
            reviewer=actor,
            reviewee=reviewee,
            defaults={
                "quality_rating": quality_rating,
                "communication_rating": communication_rating,
                "responsiveness_rating": responsiveness_rating,
                "comment": comment.strip(),
            },
        )
        return review

    @classmethod
    def list_active_disputes(cls):
        return (
            Bounty.objects.select_related("creator", "accepted_application__applicant")
            .prefetch_related("arbitration__arbitrators", "arbitration__votes__arbitrator")
            .filter(status__in=[BountyStatus.DISPUTED, BountyStatus.ARBITRATING])
            .order_by("-updated_at")
        )

    @classmethod
    def _try_finalize_arbitration(cls, arbitration: Arbitration):
        total_arbitrators = arbitration.arbitrators.count()
        votes = list(arbitration.votes.all())
        if not votes or len(votes) < max(1, total_arbitrators):
            return

        vote_counts: dict[str, int] = {}
        for item in votes:
            vote_counts[item.vote] = vote_counts.get(item.vote, 0) + 1

        result = max(vote_counts.items(), key=lambda item: (item[1], item[0]))[0]
        if result == "HUNTER_WIN":
            ratio = Decimal("1.00")
        elif result == "CREATOR_WIN":
            ratio = Decimal("0.00")
        else:
            partial_ratios = [quantize_amount(item.hunter_ratio or 0.5) for item in votes if item.vote == "PARTIAL"]
            ratio = partial_ratios[len(partial_ratios) // 2] if partial_ratios else Decimal("0.50")

        cls._apply_arbitration_result(arbitration, result, float(ratio))

    @classmethod
    def _apply_arbitration_result(cls, arbitration: Arbitration, result: str, hunter_ratio: float | None = None):
        if arbitration.resolved_at:
            return
        bounty = arbitration.bounty
        accepted_user = cls._accepted_user(bounty)
        if not accepted_user:
            raise BountyError("当前悬赏没有接单者，无法结算仲裁")

        ratio = quantize_amount(hunter_ratio or 0)
        ratio = min(max(ratio, Decimal("0.00")), Decimal("1.00"))
        payout = quantize_amount(bounty.reward * ratio)
        refund = quantize_amount(bounty.reward - payout)

        if payout > 0:
            PaymentsService.settle_bounty_payout(
                bounty.creator,
                accepted_user,
                payout,
                reference_id=f"arbitration:{arbitration.id}:payout",
            )
        if refund > 0:
            PaymentsService.release_bounty_to_creator(
                bounty.creator,
                refund,
                reference_id=f"arbitration:{arbitration.id}:refund",
            )

        for arbitrator in arbitration.arbitrators.all():
            CreditService.add_credit(
                arbitrator,
                CreditAction.ARBITRATION_SERVED,
                f"arbitration:{arbitration.id}:arbitrator:{arbitrator.id}",
            )

        arbitration.result = result
        arbitration.hunter_ratio = ratio
        arbitration.resolved_at = timezone.now()
        arbitration.save(update_fields=["result", "hunter_ratio", "resolved_at"])

        bounty.status = BountyStatus.COMPLETED if payout > 0 else BountyStatus.CANCELLED
        bounty.save(update_fields=["status"])
