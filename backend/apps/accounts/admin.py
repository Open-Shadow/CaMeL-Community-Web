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
        if obj is not None and request is not None and obj.pk == request.user.pk:
            # Inject form-level validation to prevent self-role changes.
            # This surfaces as a field error instead of a 500 from save_model.
            original_clean_role = form.base_fields.get("role") and getattr(
                form, "clean_role", None
            )

            def _make_form_with_self_role_guard(form_class, user_pk):
                class GuardedForm(form_class):
                    def clean_role(self):
                        new_role = self.cleaned_data.get("role")
                        if self.instance.pk == user_pk and new_role != self.initial.get("role"):
                            raise ValidationError(
                                "Cannot change your own role. "
                                "Ask another administrator to make this change."
                            )
                        return new_role
                return GuardedForm

            form = _make_form_with_self_role_guard(form, request.user.pk)
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            sync_admin_flags(obj)
