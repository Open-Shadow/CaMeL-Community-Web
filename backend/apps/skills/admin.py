from django.contrib import admin

from apps.skills.models import Skill, SkillReview, SkillPurchase, SkillReport, SkillVersion


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "creator", "category", "status", "pricing_model", "price", "download_count", "created_at")
    list_filter = ("status", "category", "pricing_model", "is_featured")
    search_fields = ("name", "slug", "creator__email", "creator__username")
    list_editable = ("status",)
    ordering = ("-created_at",)
    readonly_fields = ("total_calls", "avg_rating", "review_count", "download_count", "package_sha256", "package_size", "created_at", "updated_at")


@admin.register(SkillReview)
class SkillReviewAdmin(admin.ModelAdmin):
    list_display = ("skill", "reviewer", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("skill__name", "reviewer__email")


@admin.register(SkillPurchase)
class SkillPurchaseAdmin(admin.ModelAdmin):
    list_display = ("skill", "user", "paid_amount", "payment_type", "created_at")
    list_filter = ("payment_type",)
    search_fields = ("skill__name", "user__email", "user__username")
    readonly_fields = ("created_at",)


@admin.register(SkillReport)
class SkillReportAdmin(admin.ModelAdmin):
    list_display = ("skill", "reporter", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("skill__name", "reporter__email")
    readonly_fields = ("created_at",)


@admin.register(SkillVersion)
class SkillVersionAdmin(admin.ModelAdmin):
    list_display = ("skill", "version", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("skill__name",)
    readonly_fields = ("package_sha256", "created_at")
