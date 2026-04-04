from django.db import models
from apps.accounts.models import User


class BountyStatus(models.TextChoices):
    OPEN = "OPEN", "开放"
    IN_PROGRESS = "IN_PROGRESS", "进行中"
    DELIVERED = "DELIVERED", "已交付"
    IN_REVIEW = "IN_REVIEW", "审核中"
    REVISION = "REVISION", "需修改"
    COMPLETED = "COMPLETED", "已完成"
    DISPUTED = "DISPUTED", "争议中"
    ARBITRATING = "ARBITRATING", "仲裁中"
    CANCELLED = "CANCELLED", "已取消"


class BountyType(models.TextChoices):
    SKILL_CUSTOM = "SKILL_CUSTOM", "Skill 定制"
    DATA_PROCESSING = "DATA_PROCESSING", "数据处理"
    CONTENT_CREATION = "CONTENT_CREATION", "内容创作"
    BUG_FIX = "BUG_FIX", "问题修复"
    GENERAL = "GENERAL", "通用任务"


class Bounty(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bounties")
    title = models.CharField(max_length=200)
    description = models.TextField()
    bounty_type = models.CharField(max_length=30, choices=BountyType.choices)
    reward = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=BountyStatus.choices, default=BountyStatus.OPEN)
    deadline = models.DateTimeField()
    accepted_application = models.OneToOneField(
        "BountyApplication", null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_bounty"
    )
    revision_count = models.IntegerField(default=0)
    is_cold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bounties_bounty"
        indexes = [models.Index(fields=["status", "created_at"])]


class BountyApplication(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bounty_applications")
    proposal = models.TextField()
    estimated_days = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_bounty_application"
        unique_together = ("bounty", "applicant")


class BountyDeliverable(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="deliverables")
    submitter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deliverables")
    content = models.TextField()
    attachments = models.JSONField(default=list)
    revision_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_bounty_deliverable"


class BountyComment(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bounty_comments")
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_bounty_comment"


class Arbitration(models.Model):
    bounty = models.OneToOneField(Bounty, on_delete=models.CASCADE, related_name="arbitration")
    creator_statement = models.TextField(blank=True)
    hunter_statement = models.TextField(blank=True)
    arbitrators = models.ManyToManyField(User, related_name="arbitration_cases", blank=True)
    result = models.CharField(
        max_length=20,
        choices=[("HUNTER_WIN", "接单者胜"), ("CREATOR_WIN", "发布者胜"), ("PARTIAL", "部分完成")],
        blank=True,
    )
    hunter_ratio = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    appeal_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="appeals"
    )
    appeal_fee_paid = models.BooleanField(default=False)
    admin_final_result = models.CharField(max_length=20, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bounties_arbitration"


class ArbitrationVote(models.Model):
    arbitration = models.ForeignKey(Arbitration, on_delete=models.CASCADE, related_name="votes")
    arbitrator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="arbitration_votes")
    vote = models.CharField(
        max_length=20,
        choices=[("HUNTER_WIN", "接单者胜"), ("CREATOR_WIN", "发布者胜"), ("PARTIAL", "部分完成")],
    )
    hunter_ratio = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_arbitration_vote"
        unique_together = ("arbitration", "arbitrator")
