from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User, sync_admin_flags


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "level", "is_active", "date_joined")
    list_filter = ("role", "level", "is_active", "is_staff")
    search_fields = ("username", "email", "display_name")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Business Fields", {
            "fields": (
                "display_name", "bio", "avatar_url", "role", "level",
                "credit_score", "balance", "frozen_balance",
            ),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {"fields": ("email",)}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            sync_admin_flags(obj)
