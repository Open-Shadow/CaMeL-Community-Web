from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.accounts.models import CamelUser


class SkillStatus(models.TextChoices):
    DRAFT = "DRAFT", "草稿"
    PENDING_REVIEW = "PENDING_REVIEW", "待审核"
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
    PER_USE = "PER_USE", "按次付费"


class Skill(models.Model):
    creator = models.ForeignKey(CamelUser, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=500)
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(blank=True)
    output_format = models.CharField(
        max_length=20,
        choices=[("text", "文本"), ("json", "JSON"), ("markdown", "Markdown"), ("code", "代码")],
        default="text",
    )
    example_input = models.TextField(blank=True)
    example_output = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=SkillCategory.choices)
    tags = ArrayField(models.CharField(max_length=50), default=list, size=10)
    pricing_model = models.CharField(max_length=10, choices=PricingModel.choices, default=PricingModel.FREE)
    price_per_use = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SkillStatus.choices, default=SkillStatus.DRAFT)
    is_featured = models.BooleanField(default=False)
    current_version = models.IntegerField(default=1)
    total_calls = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
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
    version = models.IntegerField()
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(blank=True)
    change_note = models.CharField(max_length=200, blank=True)
    is_major = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_version"
        unique_together = ("skill", "version")


class SkillCall(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="calls")
    caller = models.ForeignKey(CamelUser, on_delete=models.CASCADE, related_name="skill_calls")
    skill_version = models.IntegerField()
    input_text = models.TextField()
    output_text = models.TextField(blank=True)
    amount_charged = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_call"
        indexes = [models.Index(fields=["skill", "created_at"])]


class SkillReview(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(CamelUser, on_delete=models.CASCADE, related_name="skill_reviews")
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
    user = models.ForeignKey(CamelUser, on_delete=models.CASCADE, related_name="skill_usage_preferences")
    locked_version = models.IntegerField(null=True, blank=True)
    auto_follow_latest = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skills_skill_usage_preference"
        unique_together = ("skill", "user")
