from django.contrib import admin
from django.utils.html import format_html

from apps.skills.models import Skill, SkillReview, SkillPurchase, SkillReport, SkillVersion, SkillCall


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "creator", "category", "status_badge", "pricing_model", "price", "download_count", "created_at")
    list_filter = ("status", "category", "pricing_model", "is_featured")
    search_fields = ("name", "slug", "creator__email", "creator__username")
    ordering = ("-created_at",)
    readonly_fields = (
        "total_calls", "avg_rating", "review_count", "download_count",
        "package_sha256", "package_size", "created_at", "updated_at",
        "readme_html_preview",
    )
    actions = ["admin_approve_selected", "admin_reject_selected", "confirm_archive_selected", "reinstate_selected"]

    fieldsets = [
        ("基本信息", {
            "fields": ("creator", "name", "slug", "description", "category", "tags"),
        }),
        ("定价", {
            "fields": ("pricing_model", "price"),
        }),
        ("状态", {
            "fields": ("status", "is_featured", "rejection_reason"),
        }),
        ("统计", {
            "fields": ("current_version", "total_calls", "avg_rating", "review_count", "download_count"),
        }),
        ("文件包", {
            "fields": ("package_file", "package_sha256", "package_size", "readme_html_preview"),
        }),
        ("时间", {
            "fields": ("created_at", "updated_at"),
        }),
    ]

    def status_badge(self, obj):
        colors = {
            "DRAFT": "#6b7280",
            "SCANNING": "#f59e0b",
            "APPROVED": "#22c55e",
            "REJECTED": "#ef4444",
            "ARCHIVED": "#6366f1",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{c};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{s}</span>',
            c=color, s=obj.status,
        )
    status_badge.short_description = "状态"

    def readme_html_preview(self, obj):
        if not obj.readme_html:
            return "-"
        from django.utils.safestring import mark_safe
        return mark_safe(obj.readme_html[:500] + ("..." if len(obj.readme_html) > 500 else ""))
    readme_html_preview.short_description = "README 预览"

    @admin.action(description="通过审核（立即上架）")
    def admin_approve_selected(self, request, queryset):
        from apps.skills.services import SkillService
        updated = 0
        for skill in queryset.filter(status="SCANNING"):
            SkillService.admin_approve(skill)
            updated += 1
        self.message_user(request, f"已通过 {updated} 个 Skill 的审核")

    @admin.action(description="拒绝审核")
    def admin_reject_selected(self, request, queryset):
        from apps.skills.services import SkillService
        updated = 0
        for skill in queryset.filter(status__in=["SCANNING", "APPROVED"]):
            SkillService.admin_reject(skill, "管理员审核拒绝")
            updated += 1
        self.message_user(request, f"已拒绝 {updated} 个 Skill")

    @admin.action(description="确认下架（安全封禁）")
    def confirm_archive_selected(self, request, queryset):
        from apps.skills.services import SkillService
        updated = 0
        for skill in queryset.filter(status__in=["APPROVED", "ARCHIVED"]):
            SkillService.archive(skill)
            updated += 1
        self.message_user(request, f"已确认下架 {updated} 个 Skill")

    @admin.action(description="恢复上架")
    def reinstate_selected(self, request, queryset):
        from apps.skills.services import SkillService
        updated = 0
        for skill in queryset.filter(status="ARCHIVED"):
            SkillService.reinstate_quarantined(skill)
            updated += 1
        self.message_user(request, f"已恢复 {updated} 个 Skill")


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
    actions = ["dismiss_reports_selected"]

    @admin.action(description="驳回举报（解除隔离）")
    def dismiss_reports_selected(self, request, queryset):
        from apps.skills.services import SkillService
        from apps.skills.models import VersionStatus
        seen = set()
        for report in queryset.select_related("skill"):
            skill = report.skill
            if skill.id not in seen:
                if skill.status == "ARCHIVED" or skill.versions.filter(status=VersionStatus.ARCHIVED).exists():
                    SkillService.reinstate_quarantined(skill)
                seen.add(skill.id)
        deleted, _ = queryset.delete()
        self.message_user(request, f"已驳回 {deleted} 条举报并解除隔离")


@admin.register(SkillVersion)
class SkillVersionAdmin(admin.ModelAdmin):
    list_display = ("skill", "version", "status_badge", "scan_result_badge", "package_sha256_short", "created_at")
    list_filter = ("status", "scan_result")
    search_fields = ("skill__name", "version")
    readonly_fields = ("package_sha256", "scan_result", "scan_warnings", "created_at")
    actions = ["archive_version_selected", "reinstate_version_selected"]

    fieldsets = [
        (None, {
            "fields": ("skill", "version", "status", "package_file", "package_sha256", "changelog"),
        }),
        ("扫描结果", {
            "fields": ("scan_result", "scan_warnings"),
        }),
        ("时间", {
            "fields": ("created_at",),
        }),
    ]

    def status_badge(self, obj):
        colors = {
            "SCANNING": "#f59e0b",
            "APPROVED": "#22c55e",
            "REJECTED": "#ef4444",
            "ARCHIVED": "#6366f1",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{c};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{s}</span>',
            c=color, s=obj.status,
        )
    status_badge.short_description = "状态"

    def scan_result_badge(self, obj):
        if not obj.scan_result:
            return "-"
        colors = {"PASS": "#22c55e", "WARN": "#f59e0b", "FAIL": "#ef4444"}
        color = colors.get(obj.scan_result, "#6b7280")
        return format_html(
            '<span style="background:{c};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{s}</span>',
            c=color, s=obj.scan_result,
        )
    scan_result_badge.short_description = "扫描结果"

    def package_sha256_short(self, obj):
        return obj.package_sha256[:12] + "..."
    package_sha256_short.short_description = "SHA256"

    @admin.action(description="封禁版本（安全原因）")
    def archive_version_selected(self, request, queryset):
        updated = queryset.exclude(status="ARCHIVED").update(status="ARCHIVED")
        self.message_user(request, f"已封禁 {updated} 个版本")

    @admin.action(description="解除封禁")
    def reinstate_version_selected(self, request, queryset):
        updated = queryset.filter(status="ARCHIVED").update(status="APPROVED")
        self.message_user(request, f"已解除 {updated} 个版本的封禁")


@admin.register(SkillCall)
class SkillCallAdmin(admin.ModelAdmin):
    list_display = ("skill", "caller", "skill_version", "duration_ms", "created_at")
    list_filter = ("skill",)
    search_fields = ("skill__name", "caller__email")
    readonly_fields = ("created_at",)
