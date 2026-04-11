"""Tests for the admin account system.

Covers:
  - AC-1: create_admin management command
  - AC-1.1: --from-env mode
  - AC-2: createsuperuser sets role=ADMIN
  - AC-3: Role/flag sync on promotion/demotion
  - AC-4: Case-insensitive email uniqueness
  - AC-6: AUTH_PASSWORD_VALIDATORS
  - AC-7: Django Admin UserAdmin registration
  - AC-8: Drift repair (tested via model assertions)
"""
import json
import os
from io import StringIO
from unittest import mock

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client

from apps.accounts.models import User, UserRole, sync_admin_flags
from apps.accounts.services import AuthService

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(email="user@test.com", password="StrongPass123!", **kwargs):
    defaults = {"display_name": email.split("@")[0]}
    defaults.update(kwargs)
    return User.objects.create_user(
        username=f"u_{email.replace('@', '_').replace('.', '_')}",
        email=email,
        password=password,
        **defaults,
    )


def _auth_header(user):
    token = AuthService.get_tokens_for_user(user)["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ===========================================================================
# AC-1: create_admin command — create new admin
# ===========================================================================


def test_create_admin_new_user():
    """create_admin with new email creates admin user."""
    out = StringIO()
    call_command(
        "create_admin",
        email="admin@new.com",
        password="ValidPass123!",
        stdout=out,
    )
    user = User.objects.get(email="admin@new.com")
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
    assert "created" in out.getvalue().lower()


def test_create_admin_elevate_existing():
    """create_admin elevates existing non-admin user without changing password."""
    user = _create_user("existing@test.com", "OriginalPass123!")
    assert user.role == UserRole.USER

    out = StringIO()
    call_command(
        "create_admin",
        email="existing@test.com",
        password="NotUsed123!",
        stdout=out,
    )
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    # Password should NOT have changed (no --set-password)
    assert user.check_password("OriginalPass123!")


def test_create_admin_elevate_with_set_password():
    """create_admin --set-password resets the password."""
    user = _create_user("setpw@test.com", "OriginalPass123!")
    out = StringIO()
    call_command(
        "create_admin",
        email="setpw@test.com",
        password="NewPassword123!",
        set_password=True,
        stdout=out,
    )
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.check_password("NewPassword123!")


def test_create_admin_idempotent():
    """Running create_admin twice on same email is idempotent."""
    out1 = StringIO()
    call_command(
        "create_admin",
        email="idempotent@test.com",
        password="ValidPass123!",
        stdout=out1,
    )
    out2 = StringIO()
    call_command(
        "create_admin",
        email="idempotent@test.com",
        password="ValidPass123!",
        stdout=out2,
    )
    assert User.objects.filter(email="idempotent@test.com").count() == 1
    user = User.objects.get(email="idempotent@test.com")
    assert user.role == UserRole.ADMIN


def test_create_admin_weak_password_rejected():
    """create_admin rejects passwords that fail Django validators."""
    with pytest.raises(CommandError, match="Password validation failed"):
        call_command(
            "create_admin",
            email="weakpw@test.com",
            password="12345678",
            stdout=StringIO(),
        )


def test_create_admin_no_email_fails():
    """create_admin without --email fails."""
    with pytest.raises(CommandError, match="--email is required"):
        call_command("create_admin", stdout=StringIO())


def test_create_admin_non_interactive_no_password_fails():
    """In non-interactive mode, missing --password fails."""
    with pytest.raises(CommandError, match="No password provided"):
        call_command(
            "create_admin",
            email="nopass@test.com",
            stdout=StringIO(),
        )


def test_create_admin_email_normalized_to_lowercase():
    """create_admin normalizes email to lowercase."""
    call_command(
        "create_admin",
        email="Admin@UPPER.com",
        password="ValidPass123!",
        stdout=StringIO(),
    )
    assert User.objects.filter(email="admin@upper.com").exists()
    assert not User.objects.filter(email="Admin@UPPER.com").exists()


# ===========================================================================
# AC-1.1: --from-env mode
# ===========================================================================


def test_create_admin_from_env_both_vars():
    """--from-env with both env vars creates admin."""
    with mock.patch.dict(os.environ, {
        "ADMIN_EMAIL": "envadmin@test.com",
        "ADMIN_PASSWORD": "ValidPass123!",
    }):
        out = StringIO()
        call_command("create_admin", from_env=True, stdout=out)

    user = User.objects.get(email="envadmin@test.com")
    assert user.role == UserRole.ADMIN


def test_create_admin_from_env_only_email_skips():
    """--from-env with only ADMIN_EMAIL warns and skips."""
    with mock.patch.dict(os.environ, {"ADMIN_EMAIL": "only@test.com"}, clear=False):
        # Remove ADMIN_PASSWORD if present
        env = os.environ.copy()
        env.pop("ADMIN_PASSWORD", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit):
                call_command(
                    "create_admin",
                    from_env=True,
                    stdout=StringIO(),
                    stderr=StringIO(),
                )
    assert not User.objects.filter(email="only@test.com").exists()


def test_create_admin_from_env_neither_var_skips():
    """--from-env with no env vars skips silently."""
    env = os.environ.copy()
    env.pop("ADMIN_EMAIL", None)
    env.pop("ADMIN_PASSWORD", None)
    with mock.patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit):
            call_command(
                "create_admin",
                from_env=True,
                stdout=StringIO(),
            )
    # No admin user created
    assert User.objects.filter(role=UserRole.ADMIN).count() == 0


# ===========================================================================
# AC-2: createsuperuser sets role=ADMIN
# ===========================================================================


def test_create_superuser_sets_admin_role():
    """User.objects.create_superuser() automatically sets role=ADMIN."""
    user = User.objects.create_superuser(
        username="superadmin",
        email="super@test.com",
        password="ValidPass123!",
    )
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True


def test_create_user_does_not_set_admin_role():
    """User.objects.create_user() does NOT set role=ADMIN."""
    user = User.objects.create_user(
        username="regular",
        email="regular@test.com",
        password="ValidPass123!",
    )
    assert user.role == UserRole.USER


# ===========================================================================
# AC-3: Role/flag synchronization
# ===========================================================================


def test_sync_admin_flags_promote_to_admin():
    """sync_admin_flags sets is_staff and is_superuser when role=ADMIN."""
    user = _create_user("sync_promo@test.com")
    user.role = UserRole.ADMIN
    user.save(update_fields=["role"])
    sync_admin_flags(user)

    user.refresh_from_db()
    assert user.is_staff is True
    assert user.is_superuser is True


def test_sync_admin_flags_demote_from_admin():
    """sync_admin_flags clears is_staff and is_superuser when role!=ADMIN."""
    user = _create_user("sync_demote@test.com")
    user.role = UserRole.ADMIN
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["role", "is_staff", "is_superuser"])

    user.role = UserRole.USER
    user.save(update_fields=["role"])
    sync_admin_flags(user)

    user.refresh_from_db()
    assert user.is_staff is False
    assert user.is_superuser is False


def test_role_change_via_admin_api_syncs_flags():
    """PATCH /api/admin/users/{id}/role syncs Django auth flags."""
    admin = _create_user("api_admin@test.com")
    admin.role = UserRole.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["role", "is_staff", "is_superuser"])

    target = _create_user("api_target@test.com")
    client = Client()

    # Promote target to ADMIN via API
    resp = client.patch(
        f"/api/admin/users/{target.id}/role",
        data=json.dumps({"role": "ADMIN"}),
        content_type="application/json",
        **_auth_header(admin),
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.role == UserRole.ADMIN
    assert target.is_staff is True
    assert target.is_superuser is True

    # Demote target back to USER
    resp = client.patch(
        f"/api/admin/users/{target.id}/role",
        data=json.dumps({"role": "USER"}),
        content_type="application/json",
        **_auth_header(admin),
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.role == UserRole.USER
    assert target.is_staff is False
    assert target.is_superuser is False


def test_demoted_admin_cannot_access_admin_endpoint():
    """After demotion, user gets 403 on admin-only endpoints."""
    admin = _create_user("demoted_admin@test.com")
    admin.role = UserRole.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["role", "is_staff", "is_superuser"])

    # Demote
    admin.role = UserRole.USER
    admin.save(update_fields=["role"])
    sync_admin_flags(admin)

    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(admin),
    )
    assert resp.status_code == 403


# ===========================================================================
# AC-4: Case-insensitive email uniqueness
# ===========================================================================


def test_email_stored_lowercase():
    """User email is normalized to lowercase on save."""
    user = _create_user("MixedCase@Example.COM")
    user.refresh_from_db()
    assert user.email == "mixedcase@example.com"


def test_duplicate_email_different_case_rejected():
    """Creating a user with case-variant of existing email fails."""
    _create_user("unique@test.com")
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="u_dup",
            email="UNIQUE@TEST.COM",
            password="ValidPass123!",
        )


# ===========================================================================
# AC-6: AUTH_PASSWORD_VALIDATORS
# ===========================================================================


def test_common_password_rejected():
    """Common passwords are rejected by validators."""
    with pytest.raises(ValidationError):
        validate_password("password")


def test_short_password_rejected():
    """Passwords shorter than 8 chars are rejected."""
    with pytest.raises(ValidationError):
        validate_password("ab")


def test_numeric_password_rejected():
    """Purely numeric passwords are rejected."""
    with pytest.raises(ValidationError):
        validate_password("12345678901234")


def test_strong_password_accepted():
    """Strong passwords pass validation."""
    validate_password("MyStr0ng!Pass42")


# ===========================================================================
# AC-7: Django Admin User registration
# ===========================================================================


def test_admin_site_accessible_by_staff():
    """An is_staff user can access Django admin."""
    user = _create_user("staff@test.com")
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    client = Client()
    client.force_login(user)
    resp = client.get("/admin/")
    assert resp.status_code == 200


def test_admin_site_blocked_for_non_staff():
    """A non-staff user is redirected from Django admin."""
    user = _create_user("nonstaff@test.com")
    client = Client()
    client.force_login(user)
    resp = client.get("/admin/")
    assert resp.status_code == 302  # Redirect to login


# ===========================================================================
# AC-8: Drift repair (model-level assertions)
# ===========================================================================


def test_superuser_without_admin_role_can_be_synced():
    """A user with is_superuser=True but role=USER can be synced."""
    user = _create_user("drifted@test.com")
    # Simulate drift: manually set is_superuser without role
    User.objects.filter(id=user.id).update(is_superuser=True)
    user.refresh_from_db()
    assert user.is_superuser is True
    assert user.role == UserRole.USER

    # Sync should fix it
    user.role = UserRole.ADMIN
    user.save(update_fields=["role"])
    sync_admin_flags(user)
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.is_superuser is True
    assert user.is_staff is True


# ===========================================================================
# Permission matrix: admin access to finance report
# ===========================================================================


def test_admin_can_access_finance_report():
    """Admin user can access GET /api/admin/finance/report."""
    admin = _create_user("finance_admin@test.com")
    admin.role = UserRole.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["role", "is_staff", "is_superuser"])

    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(admin),
    )
    assert resp.status_code == 200


def test_normal_user_blocked_from_finance_report():
    """Normal user gets 403 on admin-only endpoints."""
    user = _create_user("blocked@test.com")
    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(user),
    )
    assert resp.status_code == 403


# ===========================================================================
# Regression: create_superuser forces ADMIN even with explicit override
# ===========================================================================


def test_create_superuser_forces_admin_role_even_when_overridden():
    """create_superuser ignores explicit role=USER — always sets ADMIN."""
    user = User.objects.create_superuser(
        username="forced_admin",
        email="forced@test.com",
        password="ValidPass123!",
        role=UserRole.USER,  # caller tries to override
    )
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True


# ===========================================================================
# Historical migration tests: scratch SQLite DB + MigrationExecutor
# ===========================================================================


def _run_migration_test(pre_migrate_target, post_migrate_target, setup_fn, assert_fn):
    """Run a historical-schema migration test on a scratch SQLite database.

    1. Creates a temporary SQLite file
    2. Migrates to pre_migrate_target
    3. Calls setup_fn(connection) to insert test data
    4. Migrates to post_migrate_target
    5. Calls assert_fn(connection) to verify results
    6. Cleans up
    """
    import tempfile
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor
    from django.test.utils import override_settings

    # Create a temp SQLite file for the scratch database
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp_path = tmp.name
    tmp.close()

    scratch_db = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": tmp_path,
            "TEST": {"NAME": tmp_path},
        }
    }

    try:
        with override_settings(DATABASES=scratch_db):
            # Close any existing default connection so Django picks up new settings
            connections["default"].close()
            del connections["default"]
            conn = connections["default"]

            # Migrate to the pre-migration state (all dependencies + target)
            executor = MigrationExecutor(conn)
            executor.migrate(pre_migrate_target)
            executor.loader.build_graph()

            # Insert test data
            setup_fn(conn)

            # Migrate forward to the post-migration state
            executor = MigrationExecutor(conn)
            executor.migrate(post_migrate_target)

            # Assert results
            assert_fn(conn)

            conn.close()
    finally:
        # Restore the real test database connection
        connections["default"].close()
        del connections["default"]
        import os
        os.unlink(tmp_path)


@pytest.mark.django_db(transaction=True)
def test_migration_0003_resolves_legacy_duplicate_emails():
    """Historical migration test: 0002→0003 deactivates case-variant
    duplicate emails and applies the unique constraint."""

    def setup(conn):
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO accounts_user "
                "(password, is_superuser, username, first_name, last_name, "
                "email, is_staff, is_active, date_joined, "
                "display_name, bio, avatar_url, role, level, "
                "credit_score, balance, frozen_balance, created_at, updated_at) "
                "VALUES "
                "('hash1', 0, 'user_upper', '', '', "
                "'User@Example.COM', 0, 1, '2026-01-01 00:00:00', "
                "'', '', '', 'USER', 'SEED', 0, 0, 0, "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
            cursor.execute(
                "INSERT INTO accounts_user "
                "(password, is_superuser, username, first_name, last_name, "
                "email, is_staff, is_active, date_joined, "
                "display_name, bio, avatar_url, role, level, "
                "credit_score, balance, frozen_balance, created_at, updated_at) "
                "VALUES "
                "('hash2', 0, 'user_lower', '', '', "
                "'user@example.com', 0, 1, '2026-01-02 00:00:00', "
                "'', '', '', 'USER', 'SEED', 0, 0, 0, "
                "'2026-01-02 00:00:00', '2026-01-02 00:00:00')"
            )

    def assertions(conn):
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, email, is_active FROM accounts_user "
                "WHERE username IN ('user_upper', 'user_lower') "
                "ORDER BY is_active DESC"
            )
            rows = cursor.fetchall()

        active_rows = [r for r in rows if r[2]]
        inactive_rows = [r for r in rows if not r[2]]

        # One row keeps canonical lowercase email, the other is deactivated
        assert len(active_rows) == 1
        assert active_rows[0][1] == "user@example.com"
        assert len(inactive_rows) == 1
        # Deactivated row has renamed email
        assert inactive_rows[0][1] != "user@example.com"

        # The constraint now rejects a new case-variant duplicate
        with pytest.raises(IntegrityError):
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO accounts_user "
                    "(password, is_superuser, username, first_name, last_name, "
                    "email, is_staff, is_active, date_joined, "
                    "display_name, bio, avatar_url, role, level, "
                    "credit_score, balance, frozen_balance, created_at, updated_at) "
                    "VALUES "
                    "('hash3', 0, 'user_dup', '', '', "
                    "'USER@example.com', 0, 1, '2026-01-03 00:00:00', "
                    "'', '', '', 'USER', 'SEED', 0, 0, 0, "
                    "'2026-01-03 00:00:00', '2026-01-03 00:00:00')"
                )

    _run_migration_test(
        pre_migrate_target=[("accounts", "0002_invitation_risk_fields")],
        post_migrate_target=[("accounts", "0003_add_email_uniqueness_and_manager")],
        setup_fn=setup,
        assert_fn=assertions,
    )


@pytest.mark.django_db(transaction=True)
def test_migration_0003_repairs_both_drift_directions():
    """Historical migration test: 0002→0003 repairs both privilege drift paths:
    - is_superuser=True, role=USER → role=ADMIN, is_staff=True, is_superuser=True
    - role=ADMIN, is_superuser=False → role=ADMIN, is_staff=True, is_superuser=True
    """

    def setup(conn):
        with conn.cursor() as cursor:
            # Drift shape 1: is_superuser=True but role=USER
            cursor.execute(
                "INSERT INTO accounts_user "
                "(password, is_superuser, username, first_name, last_name, "
                "email, is_staff, is_active, date_joined, "
                "display_name, bio, avatar_url, role, level, "
                "credit_score, balance, frozen_balance, created_at, updated_at) "
                "VALUES "
                "('hash1', 1, 'drift_su_no_role', '', '', "
                "'drift1@test.com', 0, 1, '2026-01-01 00:00:00', "
                "'', '', '', 'USER', 'SEED', 0, 0, 0, "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
            # Drift shape 2: role=ADMIN but is_superuser=False
            cursor.execute(
                "INSERT INTO accounts_user "
                "(password, is_superuser, username, first_name, last_name, "
                "email, is_staff, is_active, date_joined, "
                "display_name, bio, avatar_url, role, level, "
                "credit_score, balance, frozen_balance, created_at, updated_at) "
                "VALUES "
                "('hash2', 0, 'drift_role_no_su', '', '', "
                "'drift2@test.com', 0, 1, '2026-01-01 00:00:00', "
                "'', '', '', 'ADMIN', 'SEED', 0, 0, 0, "
                "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )

    def assertions(conn):
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, role, is_staff, is_superuser FROM accounts_user "
                "WHERE username IN ('drift_su_no_role', 'drift_role_no_su') "
                "ORDER BY username"
            )
            rows = cursor.fetchall()

        assert len(rows) == 2

        # drift_role_no_su: role=ADMIN, is_superuser=False → should now have all flags
        role_no_su = [r for r in rows if r[0] == "drift_role_no_su"][0]
        assert role_no_su[1] == "ADMIN"
        assert role_no_su[2] == 1  # is_staff
        assert role_no_su[3] == 1  # is_superuser

        # drift_su_no_role: is_superuser=True, role=USER → should now be ADMIN
        su_no_role = [r for r in rows if r[0] == "drift_su_no_role"][0]
        assert su_no_role[1] == "ADMIN"
        assert su_no_role[2] == 1  # is_staff
        assert su_no_role[3] == 1  # is_superuser

    _run_migration_test(
        pre_migrate_target=[("accounts", "0002_invitation_risk_fields")],
        post_migrate_target=[("accounts", "0003_add_email_uniqueness_and_manager")],
        setup_fn=setup,
        assert_fn=assertions,
    )


# ===========================================================================
# Regression: create_admin race-safety (concurrent bootstrap)
# ===========================================================================


@pytest.mark.django_db(transaction=True)
def test_create_admin_race_loser_converges_instead_of_error():
    """When a concurrent process creates the same email between
    count==0 and create_user, the loser converges on the existing
    row instead of raising CommandError.

    Simulates the race deterministically:
    - Pre-creates the user (the "race winner")
    - Patches the initial filter().count() to return 0 (loser sees no row)
    - Patches _create_new to raise IntegrityError (loser's insert collides)
    - The recovery branch (lines 66-69) re-fetches and elevates the real user
    """
    from apps.accounts.management.commands.create_admin import Command

    # The "race winner" has already committed this user
    user = User.objects.create_user(
        username="race_winner",
        email="racewin@test.com",
        password="ValidPass123!",
        display_name="race",
    )
    assert user.role == UserRole.USER  # starts as regular user

    original_filter = User.objects.select_for_update().filter

    call_count = {"n": 0}

    def fake_filter(**kwargs):
        """First call returns empty queryset (simulating race window),
        subsequent calls return real results."""
        call_count["n"] += 1
        qs = User.objects.filter(**kwargs)
        if call_count["n"] == 1:
            # Loser's initial check sees no user
            return qs.none()
        return User.objects.select_for_update().filter(**kwargs)

    with mock.patch.object(
        Command, "_create_new",
        side_effect=IntegrityError("UNIQUE constraint failed: unique_email_ci"),
    ), mock.patch(
        "apps.accounts.management.commands.create_admin.User.objects",
        wraps=User.objects,
    ) as mock_objects:
        # Override the chained select_for_update().filter() for the first call
        real_sfu = User.objects.select_for_update

        def patched_sfu():
            sfu_qs = real_sfu()
            original_sfu_filter = sfu_qs.filter

            def sfu_filter(**kwargs):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return User.objects.none()
                return original_sfu_filter(**kwargs)

            sfu_qs.filter = sfu_filter
            return sfu_qs

        mock_objects.select_for_update = patched_sfu

        out = StringIO()
        call_command(
            "create_admin",
            email="racewin@test.com",
            password="ValidPass123!",
            stdout=out,
        )

    # The recovery path should have elevated the race winner's row
    user.refresh_from_db()
    assert user.role == UserRole.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    assert User.objects.filter(email="racewin@test.com").count() == 1


# ===========================================================================
# AC-1 E2E: create_admin → JWT → admin endpoint access
# ===========================================================================


def test_create_admin_user_can_authenticate_and_access_admin_endpoint():
    """A user created via create_admin can authenticate via JWT
    and access GET /api/admin/finance/report (200)."""
    call_command(
        "create_admin",
        email="e2e_admin@test.com",
        password="ValidPass123!",
        stdout=StringIO(),
    )
    user = User.objects.get(email="e2e_admin@test.com")

    client = Client()
    resp = client.get(
        "/api/admin/finance/report",
        **_auth_header(user),
    )
    assert resp.status_code == 200


# ===========================================================================
# AC-7: Django Admin changelist and detail views
# ===========================================================================


def test_admin_user_changelist_accessible_and_shows_columns():
    """Django admin User changelist is accessible and contains
    the registered list_display columns."""
    admin_user = _create_user("changelist_admin@test.com")
    admin_user.role = UserRole.ADMIN
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save(update_fields=["role", "is_staff", "is_superuser"])

    client = Client()
    client.force_login(admin_user)
    resp = client.get("/admin/accounts/user/")
    assert resp.status_code == 200
    content = resp.content.decode()
    # Verify list_display columns are present
    for column in ("username", "email", "role", "level", "is_active", "date_joined"):
        assert column in content.lower() or column.replace("_", " ") in content.lower(), (
            f"Column '{column}' not found in changelist"
        )


def test_admin_user_detail_view_accessible():
    """Django admin User detail (change) view is accessible and
    contains the business fields fieldset."""
    admin_user = _create_user("detail_admin@test.com")
    admin_user.role = UserRole.ADMIN
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save(update_fields=["role", "is_staff", "is_superuser"])

    target_user = _create_user("detail_target@test.com")

    client = Client()
    client.force_login(admin_user)
    resp = client.get(f"/admin/accounts/user/{target_user.id}/change/")
    assert resp.status_code == 200
    content = resp.content.decode()
    # Verify the Business Fields fieldset is present
    assert "Business Fields" in content
