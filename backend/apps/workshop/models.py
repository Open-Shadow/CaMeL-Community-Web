from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.accounts.models import User
from apps.skills.models import Skill


class ArticleStatus(models.TextChoices):
    DRAFT = "DRAFT", "草稿"
    PUBLISHED = "PUBLISHED", "已发布"
    ARCHIVED = "ARCHIVED", "已归档"


class ArticleDifficulty(models.TextChoices):
    BEGINNER = "BEGINNER", "入门"
    INTERMEDIATE = "INTERMEDIATE", "进阶"
    ADVANCED = "ADVANCED", "高级"


class ArticleType(models.TextChoices):
    TUTORIAL = "TUTORIAL", "教程"
    CASE_STUDY = "CASE_STUDY", "案例"
    PITFALL = "PITFALL", "踩坑记录"
    REVIEW = "REVIEW", "评测"
    DISCUSSION = "DISCUSSION", "讨论"


class Series(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="series")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    is_completed = models.BooleanField(default=False)
    completion_rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workshop_series"


class Article(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    series_order = models.IntegerField(null=True, blank=True)
    related_skill = models.ForeignKey(Skill, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    content = models.TextField()
    difficulty = models.CharField(max_length=20, choices=ArticleDifficulty.choices)
    article_type = models.CharField(max_length=20, choices=ArticleType.choices)
    model_tags = ArrayField(models.CharField(max_length=50), default=list)
    custom_tags = ArrayField(models.CharField(max_length=50), default=list, size=5)
    status = models.CharField(max_length=20, choices=ArticleStatus.choices, default=ArticleStatus.DRAFT)
    is_featured = models.BooleanField(default=False)
    net_votes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_tips = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    view_count = models.IntegerField(default=0)
    is_outdated = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workshop_article"
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["author", "status"]),
        ]


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    content = models.TextField(max_length=500)
    is_pinned = models.BooleanField(default=False)
    net_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workshop_comment"


class Vote(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="votes")
    is_upvote = models.BooleanField()
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workshop_vote"
        unique_together = ("article", "voter")


class Tip(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="tips")
    tipper = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tips_given")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tips_received")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workshop_tip"
