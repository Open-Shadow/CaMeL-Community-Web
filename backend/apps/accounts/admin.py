from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import CamelUser


@admin.register(CamelUser)
class CamelUserAdmin(BaseUserAdmin):
    """Minimal Django admin for the unmanaged CamelUser (Go ``users`` table)."""

    list_display = ("username", "email", "role", "community_level", "status")
    list_filter = ("role", "status", "community_level")
    search_fields = ("username", "email", "display_name")
    ordering = ("-id",)

    # Override fieldsets entirely — BaseUserAdmin references fields that
    # don't exist on CamelUser (first_name, last_name, date_joined, etc.)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Profile", {"fields": ("display_name", "email")}),
        ("Permissions", {"fields": ("role", "status")}),
        ("Community", {"fields": ("community_level", "credit_score", "quota", "used_quota")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2"),
        }),
    )

    # CamelUser is unmanaged — the admin is mostly read-only / for inspection.
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
