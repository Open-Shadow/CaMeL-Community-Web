from django.contrib import admin
from django.utils.html import format_html

from apps.workshop.models import Article, Series, Comment, Vote, Tip


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "article_type", "difficulty", "status_badge", "net_votes", "view_count", "published_at")
    list_filter = ("status", "article_type", "difficulty", "is_featured")
    search_fields = ("title", "slug", "author__email", "author__username")
    ordering = ("-created_at",)
    readonly_fields = ("net_votes", "total_tips", "view_count", "created_at", "updated_at")
    actions = ["publish_selected", "archive_selected", "feature_selected"]

    def status_badge(self, obj):
        colors = {"DRAFT": "#6b7280", "PUBLISHED": "#22c55e", "ARCHIVED": "#6366f1"}
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{c};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{s}</span>',
            c=color, s=obj.status,
        )
    status_badge.short_description = "状态"

    @admin.action(description="发布选中文章")
    def publish_selected(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status="DRAFT").update(status="PUBLISHED", published_at=timezone.now())
        self.message_user(request, f"已发布 {updated} 篇文章")

    @admin.action(description="归档选中文章")
    def archive_selected(self, request, queryset):
        updated = queryset.exclude(status="ARCHIVED").update(status="ARCHIVED")
        self.message_user(request, f"已归档 {updated} 篇文章")

    @admin.action(description="加精选中文章")
    def feature_selected(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"已加精 {updated} 篇文章")


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_completed", "created_at")
    search_fields = ("title", "author__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("article", "author", "is_pinned", "net_votes", "created_at")
    list_filter = ("is_pinned",)
    search_fields = ("article__title", "author__email", "content")
    readonly_fields = ("created_at", "updated_at")
    actions = ["pin_selected", "unpin_selected"]

    @admin.action(description="置顶选中评论")
    def pin_selected(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"已置顶 {updated} 条评论")

    @admin.action(description="取消置顶")
    def unpin_selected(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"已取消置顶 {updated} 条评论")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("article", "voter", "is_upvote", "weight", "created_at")
    list_filter = ("is_upvote",)
    search_fields = ("article__title", "voter__email")
    readonly_fields = ("created_at",)


@admin.register(Tip)
class TipAdmin(admin.ModelAdmin):
    list_display = ("article", "tipper", "recipient", "amount", "created_at")
    search_fields = ("article__title", "tipper__email", "recipient__email")
    readonly_fields = ("created_at",)
