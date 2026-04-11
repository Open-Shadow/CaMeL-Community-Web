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
        if obj is not None and obj.email and "email" in form.base_fields:
            # Prevent clearing email on users who already have one —
            # this app authenticates by email, so blanking it locks them out.
            # Legacy blank-email users are not affected (they have no email
            # to protect).
            form.base_fields["email"].required = True
        if obj is not None and request is not None and obj.pk == request.user.pk:
            # Inject form-level validation to prevent self-role changes
            # and self-deactivation.  This surfaces as field errors
            # instead of a silent lockout.

            def _make_form_with_self_edit_guard(form_class, user_pk):
                class GuardedForm(form_class):
                    def clean_role(self):
                        new_role = self.cleaned_data.get("role")
                        if self.instance.pk == user_pk and new_role != self.initial.get("role"):
                            raise ValidationError(
                                "Cannot change your own role. "
                                "Ask another administrator to make this change."
                            )
                        return new_role

                    def clean_is_active(self):
                        new_active = self.cleaned_data.get("is_active")
                        if self.instance.pk == user_pk and not new_active:
                            raise ValidationError(
                                "Cannot deactivate your own account. "
                                "Ask another administrator to make this change."
                            )
                        return new_active
                return GuardedForm

            form = _make_form_with_self_edit_guard(form, request.user.pk)
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            sync_admin_flags(obj)
            if "email" in form.changed_data:
                self._sync_allauth_email(obj)
        else:
            # New user created via admin add form — create allauth row
            if obj.email:
                self._sync_allauth_email(obj)

    @staticmethod
    def _sync_allauth_email(user):
        """Keep allauth EmailAddress in sync after an admin email change."""
        try:
            from allauth.account.models import EmailAddress
        except ImportError:
            return
        if not user.email:
            # Email was cleared — release all allauth addresses so the old
            # verified row doesn't reserve the address via unique_verified_email.
            EmailAddress.objects.filter(user=user).update(
                primary=False, verified=False
            )
            return
        # Demote and unverify ALL other EmailAddress rows for this user
        # BEFORE creating/updating the new one. This covers both the old
        # primary and any verified secondary addresses (e.g. from social
        # login), releasing them from allauth's unique_verified_email
        # constraint so the old addresses can be used by other users.
        EmailAddress.objects.filter(user=user).exclude(
            email=user.email
        ).update(primary=False, verified=False)
        # Clear any conflicting verified row on OTHER users for the new
        # email, so update_or_create doesn't hit unique_verified_email.
        EmailAddress.objects.filter(email=user.email, verified=True).exclude(
            user=user
        ).update(verified=False)
        # Ensure a primary, verified EmailAddress row exists for the new email.
        # Admin-set emails are treated as verified (admin explicitly chose it).
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True, "verified": True},
        )
