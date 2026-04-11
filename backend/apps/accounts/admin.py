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
            if "email" in form.changed_data:
                self._sync_allauth_email(obj)

    @staticmethod
    def _sync_allauth_email(user):
        """Keep allauth EmailAddress in sync after an admin email change."""
        try:
            from allauth.account.models import EmailAddress
        except ImportError:
            return
        if not user.email:
            return
        # Demote existing primary addresses BEFORE creating/updating the
        # new one — allauth enforces a single primary per user, so having
        # two primary rows simultaneously would cause an IntegrityError.
        EmailAddress.objects.filter(user=user, primary=True).exclude(
            email=user.email
        ).update(primary=False)
        # Ensure a primary, verified EmailAddress row exists for the new email.
        # Admin-set emails are treated as verified (admin explicitly chose it).
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": True},
        )
