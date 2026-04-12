from django.contrib import admin

from apps.skills.models import Skill, SkillReview


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "creator", "category", "status", "pricing_model", "price_per_use", "created_at")
    list_filter = ("status", "category", "pricing_model", "is_featured")
    search_fields = ("name", "slug", "creator__email", "creator__username")
    list_editable = ("status",)
    ordering = ("-created_at",)
    readonly_fields = ("total_calls", "avg_rating", "review_count", "created_at", "updated_at")


@admin.register(SkillReview)
class SkillReviewAdmin(admin.ModelAdmin):
    list_display = ("skill", "reviewer", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("skill__name", "reviewer__email")
