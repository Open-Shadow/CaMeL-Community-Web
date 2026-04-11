from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError

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

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and "email" in form.base_fields:
            form.base_fields["email"].required = True
        return form

    def save_model(self, request, obj, form, change):
        if change and request and obj.pk == request.user.pk:
            if "role" in form.changed_data:
                raise ValidationError(
                    "Cannot change your own role. "
                    "Ask another administrator to make this change."
                )
        super().save_model(request, obj, form, change)
        if change:
            sync_admin_flags(obj)
