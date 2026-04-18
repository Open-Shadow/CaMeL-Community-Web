from django.contrib import admin
from django.utils.html import format_html

from apps.bounties.models import (
    Bounty, BountyApplication, BountyDeliverable,
    BountyComment, BountyReview, Arbitration,
)


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "bounty_type", "status_badge", "reward", "deadline", "created_at")
    list_filter = ("status", "bounty_type")
    search_fields = ("title", "creator__email", "creator__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "revision_count")
    actions = ["cancel_selected"]

    def status_badge(self, obj):
        colors = {
            "OPEN": "#22c55e", "IN_PROGRESS": "#3b82f6", "COMPLETED": "#6366f1",
            "CANCELLED": "#6b7280", "DISPUTED": "#f59e0b", "ARBITRATING": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{c};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{s}</span>',
            c=color, s=obj.status,
        )
    status_badge.short_description = "状态"

    @admin.action(description="取消选中的悬赏")
    def cancel_selected(self, request, queryset):
        updated = queryset.exclude(status__in=["COMPLETED", "CANCELLED"]).update(status="CANCELLED")
        self.message_user(request, f"已取消 {updated} 个悬赏")


@admin.register(BountyApplication)
class BountyApplicationAdmin(admin.ModelAdmin):
    list_display = ("bounty", "applicant", "estimated_days", "created_at")
    search_fields = ("bounty__title", "applicant__email")
    readonly_fields = ("created_at",)


@admin.register(BountyDeliverable)
class BountyDeliverableAdmin(admin.ModelAdmin):
    list_display = ("bounty", "submitter", "revision_number", "created_at")
    search_fields = ("bounty__title", "submitter__email")
    readonly_fields = ("created_at",)


@admin.register(BountyComment)
class BountyCommentAdmin(admin.ModelAdmin):
    list_display = ("bounty", "author", "created_at")
    search_fields = ("bounty__title", "author__email")
    readonly_fields = ("created_at",)


@admin.register(BountyReview)
class BountyReviewAdmin(admin.ModelAdmin):
    list_display = ("bounty", "reviewer", "reviewee", "quality_rating", "communication_rating", "created_at")
    search_fields = ("bounty__title", "reviewer__email", "reviewee__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Arbitration)
class ArbitrationAdmin(admin.ModelAdmin):
    list_display = ("bounty", "result", "deadline", "created_at", "resolved_at")
    list_filter = ("result",)
    search_fields = ("bounty__title",)
    readonly_fields = ("created_at", "resolved_at")
