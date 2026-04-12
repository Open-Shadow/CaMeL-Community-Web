from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.accounts.models import User


class SkillStatus(models.TextChoices):
    DRAFT = "DRAFT", "草稿"
    SCANNING = "SCANNING", "扫描中"
    APPROVED = "APPROVED", "已上架"
    REJECTED = "REJECTED", "已拒绝"
    ARCHIVED = "ARCHIVED", "已归档"


class SkillCategory(models.TextChoices):
    CODE_DEV = "CODE_DEV", "代码开发"
    WRITING = "WRITING", "文案写作"
    DATA_ANALYTICS = "DATA_ANALYTICS", "数据分析"
    ACADEMIC = "ACADEMIC", "学术研究"
    TRANSLATION = "TRANSLATION", "翻译本地化"
    CREATIVE = "CREATIVE", "创意设计"
    AGENT = "AGENT", "Agent 工具"
    PRODUCTIVITY = "PRODUCTIVITY", "办公效率"
    MISC = "MISC", "其他"


class PricingModel(models.TextChoices):
    FREE = "FREE", "免费"
    PAID = "PAID", "付费"


class VersionStatus(models.TextChoices):
    SCANNING = "SCANNING", "扫描中"
    APPROVED = "APPROVED", "已通过"
    REJECTED = "REJECTED", "已拒绝"
    ARCHIVED = "ARCHIVED", "已归档"


class ReportReason(models.TextChoices):
    MALICIOUS_CODE = "MALICIOUS_CODE", "恶意代码"
    FALSE_DESCRIPTION = "FALSE_DESCRIPTION", "虚假描述"
    COPYRIGHT = "COPYRIGHT", "侵权"
    OTHER = "OTHER", "其他"


class Skill(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=30, choices=SkillCategory.choices)
    tags = ArrayField(models.CharField(max_length=50), default=list, size=10)
    pricing_model = models.CharField(max_length=10, choices=PricingModel.choices, default=PricingModel.FREE)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SkillStatus.choices, default=SkillStatus.DRAFT)
    is_featured = models.BooleanField(default=False)
    current_version = models.IntegerField(default=1)
    total_calls = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
    # Package fields
    package_file = models.FileField(upload_to="skill_packages/%Y/%m/", blank=True)
    package_sha256 = models.CharField(max_length=64, blank=True)
    package_size = models.IntegerField(default=0)
    readme_html = models.TextField(blank=True)
    download_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skills_skill"
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["creator", "status"]),
        ]


class SkillVersion(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=20)
    package_file = models.FileField(upload_to="skill_packages/%Y/%m/")
    package_sha256 = models.CharField(max_length=64)
    changelog = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=VersionStatus.choices, default=VersionStatus.SCANNING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_version"
        unique_together = ("skill", "version")


class SkillCall(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="calls")
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_calls")
    skill_version = models.CharField(max_length=20)
    input_text = models.TextField()
    output_text = models.TextField(blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_call"
        indexes = [models.Index(fields=["skill", "created_at"])]


class SkillReview(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_reviews")
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    tags = ArrayField(models.CharField(max_length=30), default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skills_skill_review"
        unique_together = ("skill", "reviewer")


class SkillUsagePreference(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="usage_preferences")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_usage_preferences")
    locked_version = models.CharField(max_length=20, blank=True, default="")
    auto_follow_latest = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skills_skill_usage_preference"
        unique_together = ("skill", "user")


class SkillPurchase(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="purchases")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_purchases")
    paid_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=10)  # FREE | MONEY
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_purchase"
        unique_together = ("skill", "user")


class SkillReport(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_reports")
    reason = models.CharField(max_length=30, choices=ReportReason.choices)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_report"
        unique_together = ("skill", "reporter")
