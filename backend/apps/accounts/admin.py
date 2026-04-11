from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


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
