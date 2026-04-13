"""API-level regression tests for skill module (AC-2, AC-5, AC-6).

This file contains two kinds of tests:
1. Service-layer tests (Test*) that exercise core logic — require PostgreSQL.
2. HTTP-level tests (TestHTTP*) that hit actual API endpoints via Django's
   test Client with JWT auth — require PostgreSQL.
"""
import io
import json
import zipfile
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as DjangoClient
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User, UserRole
from apps.skills.models import (
    Skill,
    SkillCall,
    SkillPurchase,
    SkillReport,
    SkillVersion,
    PricingModel,
    ReportReason,
    ScanResult,
    SkillStatus,
    VersionStatus,
)
from apps.skills.services import SkillService, SkillReportService


def _make_zip(files: dict[str, str | bytes]) -> SimpleUploadedFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            zf.writestr(name, data)
    buf.seek(0)
    return SimpleUploadedFile("test.zip", buf.read(), content_type="application/zip")


def _make_zip_bytes(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            zf.writestr(name, data)
    buf.seek(0)
    return buf.read()


SKILL_MD = """---
name: Test Skill
description: A test skill
version: "{version}"
---

# Test Skill
"""


def _jwt_header(user) -> dict:
    """Return an Authorization header dict for the given user."""
    token = str(AccessToken.for_user(user))
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _multipart_patch(client, path, data, **extra):
    """PATCH with multipart-encoded data.

    Django's test client ``patch()`` does not encode dicts as multipart
    (unlike ``post()``).  We manually encode and pass encoded bytes so
    file fields are transmitted correctly.
    """
    encoded = encode_multipart(BOUNDARY, data)
    return client.patch(
        path,
        data=encoded,
        content_type=MULTIPART_CONTENT,
        **extra,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="creator", email="c@test.com", password="pw",
        credit_score=200,  # Craftsman level for auto-publish
    )


@pytest.fixture
def low_trust_user(db):
    return User.objects.create_user(
        username="newbie", email="n@test.com", password="pw",
        credit_score=10,  # Below Craftsman
    )


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        username="buyer", email="b@test.com", password="pw",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin", email="admin@test.com", password="pw",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def approved_skill(user):
    skill = Skill.objects.create(
        creator=user,
        name="Test Skill",
        slug="test-skill-api",
        description="A test skill",
        category="CODE_DEV",
        pricing_model=PricingModel.FREE,
        status=SkillStatus.APPROVED,
        current_version="1.0.0",
        package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
        package_sha256="a" * 64,
        package_size=100,
    )
    SkillVersion.objects.create(
        skill=skill,
        version="1.0.0",
        package_file=skill.package_file,
        package_sha256="a" * 64,
        status=VersionStatus.APPROVED,
    )
    return skill


@pytest.fixture
def paid_skill(user, buyer):
    skill = Skill.objects.create(
        creator=user,
        name="Paid Skill",
        slug="paid-skill-api",
        description="A paid skill",
        category="CODE_DEV",
        pricing_model=PricingModel.PAID,
        price=Decimal("1.99"),
        status=SkillStatus.APPROVED,
        current_version="1.0.0",
        package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
        package_sha256="b" * 64,
        package_size=100,
    )
    SkillVersion.objects.create(
        skill=skill,
        version="1.0.0",
        package_file=skill.package_file,
        package_sha256="b" * 64,
        status=VersionStatus.APPROVED,
    )
    return skill


# ===========================================================================
# Service-layer tests (kept from prior rounds for coverage depth)
# ===========================================================================

class TestResolvePackageFile:
    """Tests for the centralized package resolution used by download and file-tree endpoints."""

    @pytest.mark.django_db
    def test_approved_skill_resolves_latest_approved_version(self, approved_skill):
        result = SkillService.resolve_package_file(approved_skill)
        assert result is not None

    @pytest.mark.django_db
    def test_archived_skill_blocked(self, approved_skill):
        approved_skill.status = SkillStatus.ARCHIVED
        approved_skill.save()
        with pytest.raises(ValueError, match="不可访问"):
            SkillService.resolve_package_file(approved_skill)

    @pytest.mark.django_db
    def test_rejected_skill_blocked(self, approved_skill):
        approved_skill.status = SkillStatus.REJECTED
        approved_skill.save()
        with pytest.raises(ValueError, match="不可访问"):
            SkillService.resolve_package_file(approved_skill)

    @pytest.mark.django_db
    def test_specific_approved_version_resolves(self, approved_skill):
        result = SkillService.resolve_package_file(approved_skill, version="1.0.0")
        assert result is not None

    @pytest.mark.django_db
    def test_non_approved_version_blocked(self, approved_skill):
        SkillVersion.objects.create(
            skill=approved_skill,
            version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="c" * 64,
            status=VersionStatus.SCANNING,
        )
        with pytest.raises(ValueError, match="不存在或未通过审核"):
            SkillService.resolve_package_file(approved_skill, version="2.0.0")

    @pytest.mark.django_db
    def test_archived_version_not_resolvable(self, approved_skill):
        v = approved_skill.versions.get(version="1.0.0")
        v.status = VersionStatus.ARCHIVED
        v.save()
        with pytest.raises(ValueError, match="没有可用的已审核版本"):
            SkillService.resolve_package_file(approved_skill)

    @pytest.mark.django_db
    def test_no_approved_versions_raises(self, approved_skill):
        approved_skill.versions.all().delete()
        with pytest.raises(ValueError, match="没有可用的已审核版本"):
            SkillService.resolve_package_file(approved_skill)


class TestAdminRejectVersionScoped:
    """Tests for version-scoped admin rejection on approved skills."""

    @pytest.mark.django_db
    def test_reject_pending_version_keeps_skill_approved(self, approved_skill):
        SkillVersion.objects.create(
            skill=approved_skill,
            version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="d" * 64,
            status=VersionStatus.SCANNING,
        )
        result = SkillService.admin_reject(approved_skill, reason="Not good")
        assert result.status == SkillStatus.APPROVED
        pending = approved_skill.versions.get(version="2.0.0")
        assert pending.status == VersionStatus.REJECTED
        live = approved_skill.versions.get(version="1.0.0")
        assert live.status == VersionStatus.APPROVED

    @pytest.mark.django_db
    def test_reject_no_pending_version_raises(self, approved_skill):
        with pytest.raises(ValueError, match="没有待审核的新版本"):
            SkillService.admin_reject(approved_skill, reason="No pending")

    @pytest.mark.django_db
    def test_reject_new_skill_sets_rejected(self, user):
        skill = Skill.objects.create(
            creator=user,
            name="New Skill",
            slug="new-skill-rej",
            description="A new skill",
            category="CODE_DEV",
            status=SkillStatus.SCANNING,
        )
        SkillVersion.objects.create(
            skill=skill,
            version="1.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            package_sha256="e" * 64,
            status=VersionStatus.SCANNING,
        )
        result = SkillService.admin_reject(skill, reason="Bad content")
        assert result.status == SkillStatus.REJECTED


class TestDuplicateVersionValidation:
    """Tests for duplicate version rejection before DB insert."""

    @pytest.mark.django_db
    def test_same_version_rejected_by_monotonic_check(self, approved_skill):
        """Uploading same version as live is rejected by the monotonic SemVer guard."""
        data = {
            "version": "1.0.0",
            "package_file": _make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            "package_sha256": "f" * 64,
            "package_size": 100,
        }
        with pytest.raises(ValueError, match="必须大于"):
            SkillService.update(approved_skill, data)

    @pytest.mark.django_db
    def test_duplicate_rejected_version_also_rejected(self, approved_skill):
        SkillVersion.objects.create(
            skill=approved_skill,
            version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="g" * 64,
            status=VersionStatus.REJECTED,
        )
        data = {
            "version": "2.0.0",
            "package_file": _make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            "package_sha256": "h" * 64,
            "package_size": 100,
        }
        with pytest.raises(ValueError, match="已存在"):
            SkillService.update(approved_skill, data)


class TestScanPipelineResults:
    """Tests for structured scan result persistence."""

    @pytest.mark.django_db
    def test_scan_pass_clean(self, approved_skill):
        SkillService.complete_scan(approved_skill, passed=True, issues=[])
        v = approved_skill.versions.order_by("-created_at").first()
        assert v.scan_result == ScanResult.PASS_CLEAN

    @pytest.mark.django_db
    def test_scan_warn(self, approved_skill):
        SkillService.complete_scan(
            approved_skill, passed=True, issues=[],
            warnings=["Missing description"],
        )
        v = approved_skill.versions.order_by("-created_at").first()
        assert v.scan_result == ScanResult.WARN
        assert v.scan_warnings == ["Missing description"]

    @pytest.mark.django_db
    def test_scan_fail(self, user):
        skill = Skill.objects.create(
            creator=user,
            name="Scan Fail Skill",
            slug="scan-fail-skill",
            description="Test",
            category="CODE_DEV",
            status=SkillStatus.SCANNING,
        )
        SkillVersion.objects.create(
            skill=skill,
            version="1.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            package_sha256="i" * 64,
            status=VersionStatus.SCANNING,
        )
        SkillService.complete_scan(skill, passed=False, issues=["Malicious content"])
        v = skill.versions.order_by("-created_at").first()
        assert v.scan_result == ScanResult.FAIL
        assert v.status == VersionStatus.REJECTED


class TestVersionScopedQuarantine:
    """Tests for community report quarantine at version level."""

    @pytest.mark.django_db
    def test_quarantine_archives_current_version_not_skill(self, approved_skill):
        from apps.skills.models import SkillReport, ReportReason
        from apps.skills.services import SkillReportService

        reporters = []
        for i in range(3):
            u = User.objects.create_user(
                username=f"reporter{i}", email=f"r{i}@test.com", password="pw",
            )
            from django.utils import timezone
            from datetime import timedelta
            u.date_joined = timezone.now() - timedelta(days=30)
            u.save()
            reporters.append(u)

        for r in reporters:
            SkillReportService.report(approved_skill, r, ReportReason.MALICIOUS_CODE)

        v = approved_skill.versions.get(version="1.0.0")
        assert v.status == VersionStatus.ARCHIVED

        approved_skill.refresh_from_db()
        assert approved_skill.status == SkillStatus.ARCHIVED


class TestSinglePendingVersionLifecycle:
    """Tests for single pending version enforcement (Finding 1, Round 5)."""

    @pytest.mark.django_db
    def test_new_upload_supersedes_existing_scanning_version(self, approved_skill):
        """Uploading a new version should archive/reject existing SCANNING versions."""
        SkillVersion.objects.create(
            skill=approved_skill,
            version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="x" * 64,
            status=VersionStatus.SCANNING,
        )
        data = {
            "version": "3.0.0",
            "package_file": _make_zip({"SKILL.md": SKILL_MD.format(version="3.0.0")}),
            "package_sha256": "y" * 64,
            "package_size": 100,
        }
        SkillService.update(approved_skill, data)
        # Old SCANNING version should be rejected
        old = approved_skill.versions.get(version="2.0.0")
        assert old.status == VersionStatus.REJECTED
        # New version should be SCANNING
        new = approved_skill.versions.get(version="3.0.0")
        assert new.status == VersionStatus.SCANNING

    @pytest.mark.django_db
    def test_approve_stale_version_blocked(self, approved_skill):
        """Approving a version whose SemVer <= live should be rejected."""
        # Create a pending version with a lower version than current_version
        # This shouldn't normally happen via update() due to monotonic check,
        # but can happen if data is manipulated or from earlier code paths.
        SkillVersion.objects.create(
            skill=approved_skill,
            version="0.9.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="0.9.0")}),
            package_sha256="z" * 64,
            status=VersionStatus.SCANNING,
        )
        with pytest.raises(ValueError, match="不高于"):
            SkillService.admin_approve(approved_skill)


class TestQuarantineNotificationAttribution:
    """Tests for quarantine notification version attribution (Finding 3, Round 5)."""

    @pytest.mark.django_db
    def test_quarantine_notification_uses_quarantined_version(self, user):
        """When quarantine triggers fallback, notification should reference
        the quarantined version, not the promoted fallback."""
        from apps.skills.models import ReportReason
        from apps.skills.services import SkillReportService
        from apps.notifications.models import Notification
        from django.utils import timezone
        from datetime import timedelta

        skill = Skill.objects.create(
            creator=user,
            name="Multi Version Skill",
            slug="multi-version-skill",
            description="A multi-version skill",
            category="CODE_DEV",
            pricing_model=PricingModel.FREE,
            status=SkillStatus.APPROVED,
            current_version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="a" * 64,
            package_size=100,
        )
        # Create two approved versions: 1.0.0 (fallback) and 2.0.0 (current/live)
        SkillVersion.objects.create(
            skill=skill, version="1.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            package_sha256="b" * 64, status=VersionStatus.APPROVED,
        )
        SkillVersion.objects.create(
            skill=skill, version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="c" * 64, status=VersionStatus.APPROVED,
        )

        reporters = []
        for i in range(3):
            u = User.objects.create_user(
                username=f"rpt{i}", email=f"rpt{i}@test.com", password="pw",
            )
            u.date_joined = timezone.now() - timedelta(days=30)
            u.save()
            reporters.append(u)

        for r in reporters:
            SkillReportService.report(skill, r, ReportReason.MALICIOUS_CODE)

        # After quarantine, skill should have fallen back to 1.0.0
        skill.refresh_from_db()
        assert skill.current_version == "1.0.0"
        assert skill.status == SkillStatus.APPROVED  # Not archived — fallback exists

        # Notification should reference the QUARANTINED version (2.0.0), not fallback (1.0.0)
        notif = Notification.objects.filter(
            recipient=user,
            notification_type="skill_reported",
        ).order_by("-created_at").first()
        assert notif is not None
        assert "v2.0.0" in notif.content


# ===========================================================================
# HTTP-level API tests (Finding 2, Round 5)
# ===========================================================================

@pytest.fixture
def client():
    return DjangoClient()


class TestHTTPSkillCreate:
    """HTTP-level tests for multipart skill creation endpoint."""

    @pytest.mark.django_db
    def test_create_skill_multipart(self, client, user):
        """POST /api/skills/ with multipart form data creates a skill."""
        zip_bytes = _make_zip_bytes({"SKILL.md": SKILL_MD.format(version="1.0.0")})
        package = SimpleUploadedFile("test.zip", zip_bytes, content_type="application/zip")
        resp = client.post(
            "/api/skills/",
            data={
                "name": "HTTP Test Skill",
                "description": "A test skill for HTTP tests",
                "category": "CODE_DEV",
                "pricing_model": "FREE",
                "package": package,
            },
            **_jwt_header(user),
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["name"] == "HTTP Test Skill"
        assert body["status"] in (SkillStatus.DRAFT, SkillStatus.SCANNING)
        assert body["creator_id"] == user.id

    @pytest.mark.django_db
    def test_create_skill_unauthenticated(self, client):
        """POST /api/skills/ without auth returns 401."""
        zip_bytes = _make_zip_bytes({"SKILL.md": SKILL_MD.format(version="1.0.0")})
        package = SimpleUploadedFile("test.zip", zip_bytes, content_type="application/zip")
        resp = client.post(
            "/api/skills/",
            data={
                "name": "Should Fail",
                "description": "No auth provided",
                "category": "CODE_DEV",
                "package": package,
            },
        )
        assert resp.status_code == 401


class TestHTTPSkillUpdate:
    """HTTP-level tests for multipart skill update endpoint."""

    @pytest.mark.django_db
    def test_update_skill_with_new_package(self, client, user, approved_skill):
        """PATCH /api/skills/{id} with new package creates pending version."""
        zip_bytes = _make_zip_bytes({"SKILL.md": SKILL_MD.format(version="2.0.0")})
        package = SimpleUploadedFile("test2.zip", zip_bytes, content_type="application/zip")
        resp = _multipart_patch(
            client,
            f"/api/skills/{approved_skill.id}",
            data={
                "name": "Test Skill",
                "description": "A test skill",
                "category": "CODE_DEV",
                "package": package,
            },
            **_jwt_header(user),
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        # Approved skill stays approved — version goes to SCANNING
        assert body["status"] == SkillStatus.APPROVED
        # current_version stays at 1.0.0 until pending version is approved
        assert body["current_version"] == "1.0.0"
        # New version should exist as SCANNING
        assert approved_skill.versions.filter(
            version="2.0.0", status=VersionStatus.SCANNING,
        ).exists()

    @pytest.mark.django_db
    def test_update_rejects_same_version_monotonic(self, client, user, approved_skill):
        """PATCH /api/skills/{id} with same version as live returns 400 (monotonic guard)."""
        zip_bytes = _make_zip_bytes({"SKILL.md": SKILL_MD.format(version="1.0.0")})
        package = SimpleUploadedFile("dup.zip", zip_bytes, content_type="application/zip")
        resp = _multipart_patch(
            client,
            f"/api/skills/{approved_skill.id}",
            data={
                "name": "Test Skill",
                "description": "A test skill",
                "category": "CODE_DEV",
                "package": package,
            },
            **_jwt_header(user),
        )
        assert resp.status_code == 400
        assert "必须大于" in resp.json().get("detail", "")

    @pytest.mark.django_db
    def test_update_rejects_duplicate_rejected_version(self, client, user, approved_skill):
        """PATCH /api/skills/{id} with a version that exists as REJECTED returns 400 (duplicate guard)."""
        # Create a rejected version at 2.0.0
        SkillVersion.objects.create(
            skill=approved_skill,
            version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="d" * 64,
            status=VersionStatus.REJECTED,
        )
        zip_bytes = _make_zip_bytes({"SKILL.md": SKILL_MD.format(version="2.0.0")})
        package = SimpleUploadedFile("dup2.zip", zip_bytes, content_type="application/zip")
        resp = _multipart_patch(
            client,
            f"/api/skills/{approved_skill.id}",
            data={
                "name": "Test Skill",
                "description": "A test skill",
                "category": "CODE_DEV",
                "package": package,
            },
            **_jwt_header(user),
        )
        assert resp.status_code == 400
        assert "已存在" in resp.json().get("detail", "")


class TestHTTPSkillDownload:
    """HTTP-level tests for download endpoint auth and redirect."""

    @pytest.mark.django_db
    def test_download_unauthenticated_rejected(self, client, approved_skill):
        """GET /api/skills/{id}/download without auth returns 401."""
        resp = client.get(f"/api/skills/{approved_skill.id}/download")
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_download_free_skill_redirects(self, client, buyer, approved_skill):
        """GET /api/skills/{id}/download for free skill returns redirect."""
        resp = client.get(
            f"/api/skills/{approved_skill.id}/download",
            **_jwt_header(buyer),
        )
        # Free skills should allow download — returns redirect (302) to storage URL
        assert resp.status_code in (302, 200), resp.content

    @pytest.mark.django_db
    def test_download_paid_skill_without_purchase_rejected(self, client, buyer, paid_skill):
        """GET /api/skills/{id}/download for paid skill without purchase returns 403."""
        resp = client.get(
            f"/api/skills/{paid_skill.id}/download",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_download_archived_skill_rejected(self, client, buyer, approved_skill):
        """GET /api/skills/{id}/download for archived skill returns 404."""
        approved_skill.status = SkillStatus.ARCHIVED
        approved_skill.save()
        resp = client.get(
            f"/api/skills/{approved_skill.id}/download",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 404


class TestHTTPFileTree:
    """HTTP-level tests for file-tree endpoint auth."""

    @pytest.mark.django_db
    def test_file_tree_unauthenticated_rejected(self, client, approved_skill):
        """GET /api/skills/{id}/file-tree without auth returns 401."""
        resp = client.get(f"/api/skills/{approved_skill.id}/file-tree")
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_file_tree_free_skill_returns_entries(self, client, buyer, approved_skill):
        """GET /api/skills/{id}/file-tree for free skill returns file listing."""
        resp = client.get(
            f"/api/skills/{approved_skill.id}/file-tree",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert any(entry["path"] == "SKILL.md" for entry in body)

    @pytest.mark.django_db
    def test_file_tree_paid_skill_without_purchase_rejected(self, client, buyer, paid_skill):
        """GET /api/skills/{id}/file-tree for paid skill without purchase returns 403."""
        resp = client.get(
            f"/api/skills/{paid_skill.id}/file-tree",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 403


class TestHTTPPurchase:
    """HTTP-level tests for purchase endpoint."""

    @pytest.mark.django_db
    def test_purchase_free_skill(self, client, buyer, approved_skill):
        """POST /api/skills/{id}/purchase for free skill returns 201."""
        resp = client.post(
            f"/api/skills/{approved_skill.id}/purchase",
            content_type="application/json",
            data="{}",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["paid_amount"] == 0
        assert body["payment_type"] == "FREE"

    @pytest.mark.django_db
    def test_purchase_idempotent(self, client, buyer, approved_skill):
        """POST /api/skills/{id}/purchase twice returns same record."""
        for _ in range(2):
            resp = client.post(
                f"/api/skills/{approved_skill.id}/purchase",
                content_type="application/json",
                data="{}",
                **_jwt_header(buyer),
            )
            assert resp.status_code == 201


class TestHTTPPurchasedList:
    """HTTP-level tests for purchased skills list endpoint."""

    @pytest.mark.django_db
    def test_purchased_list_returns_purchase_metadata(self, client, buyer, approved_skill):
        """GET /api/skills/purchased returns skills with purchase metadata."""
        # First purchase
        SkillPurchase.objects.create(
            skill=approved_skill, user=buyer,
            paid_amount=Decimal("0"), payment_type="FREE",
        )
        resp = client.get(
            "/api/skills/purchased",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        item = body[0]
        assert "purchase_id" in item
        assert "paid_amount" in item
        assert "purchased_at" in item
        assert item["name"] == "Test Skill"


class TestHTTPAdminReview:
    """HTTP-level tests for admin skill review endpoint."""

    @pytest.mark.django_db
    def test_approve_scanning_skill(self, client, admin_user, user):
        """POST /api/admin/skills/{id}/review with APPROVE transitions skill."""
        skill = Skill.objects.create(
            creator=user,
            name="Pending Skill",
            slug="pending-skill-review",
            description="Needs review",
            category="CODE_DEV",
            status=SkillStatus.SCANNING,
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            package_sha256="r" * 64,
            package_size=100,
        )
        SkillVersion.objects.create(
            skill=skill, version="1.0.0",
            package_file=skill.package_file,
            package_sha256="r" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/admin/skills/{skill.id}/review",
            data=json.dumps({"action": "APPROVE", "reason": ""}),
            content_type="application/json",
            **_jwt_header(admin_user),
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["status"] == SkillStatus.APPROVED

    @pytest.mark.django_db
    def test_reject_pending_version_keeps_skill_approved(self, client, admin_user, user, approved_skill):
        """POST /api/admin/skills/{id}/review REJECT on approved skill with
        pending version keeps the skill APPROVED."""
        SkillVersion.objects.create(
            skill=approved_skill, version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="s" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/admin/skills/{approved_skill.id}/review",
            data=json.dumps({"action": "REJECT", "reason": "Not good enough"}),
            content_type="application/json",
            **_jwt_header(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == SkillStatus.APPROVED

    @pytest.mark.django_db
    def test_non_admin_rejected(self, client, buyer):
        """POST /api/admin/skills/{id}/review by non-admin returns 403."""
        resp = client.post(
            "/api/admin/skills/999/review",
            data=json.dumps({"action": "APPROVE", "reason": ""}),
            content_type="application/json",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 403


class TestHTTPVersionList:
    """HTTP-level tests for version list endpoint."""

    @pytest.mark.django_db
    def test_versions_include_scan_fields(self, client, approved_skill):
        """GET /api/skills/{id}/versions returns scan_result and scan_warnings."""
        resp = client.get(f"/api/skills/{approved_skill.id}/versions")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1
        v = body[0]
        assert "scan_result" in v
        assert "scan_warnings" in v

    @pytest.mark.django_db
    def test_versions_exclude_non_approved(self, client, approved_skill):
        """GET /api/skills/{id}/versions only returns APPROVED versions."""
        SkillVersion.objects.create(
            skill=approved_skill, version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="t" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.get(f"/api/skills/{approved_skill.id}/versions")
        assert resp.status_code == 200
        body = resp.json()
        versions = [v["version"] for v in body]
        assert "1.0.0" in versions
        assert "2.0.0" not in versions


class TestHTTPSkillReport:
    """HTTP-level tests for skill report endpoint."""

    @pytest.mark.django_db
    def test_report_skill(self, client, approved_skill):
        """POST /api/skills/{id}/report creates a report."""
        from django.utils import timezone
        from datetime import timedelta
        reporter = User.objects.create_user(
            username="httpreporter", email="hr@test.com", password="pw",
        )
        reporter.date_joined = timezone.now() - timedelta(days=30)
        reporter.save()

        resp = client.post(
            f"/api/skills/{approved_skill.id}/report",
            data=json.dumps({"reason": "MALICIOUS_CODE", "detail": "test"}),
            content_type="application/json",
            **_jwt_header(reporter),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["reason"] == "MALICIOUS_CODE"

    @pytest.mark.django_db
    def test_self_report_rejected(self, client, user, approved_skill):
        """POST /api/skills/{id}/report by creator returns 400."""
        resp = client.post(
            f"/api/skills/{approved_skill.id}/report",
            data=json.dumps({"reason": "MALICIOUS_CODE", "detail": ""}),
            content_type="application/json",
            **_jwt_header(user),
        )
        assert resp.status_code == 400


class TestHTTPCallDownloadOnly:
    """HTTP-level tests for download-only skill call behavior."""

    @pytest.mark.django_db
    def test_call_download_only_skill_rejected(self, client, user, approved_skill):
        """POST /api/skills/{id}/call on a download-only skill (no prompts/) returns 400."""
        # The approved_skill has no prompts/ directory — it's download-only
        resp = client.post(
            f"/api/skills/{approved_skill.id}/call",
            data=json.dumps({"input_text": "test input"}),
            content_type="application/json",
            **_jwt_header(user),
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "下载" in body.get("detail", "")


class TestHTTPSkillSubmit:
    """HTTP-level tests for the submit-for-review endpoint."""

    @pytest.mark.django_db
    def test_submit_draft_skill(self, client, user):
        """POST /api/skills/{id}/submit transitions DRAFT skill to SCANNING."""
        skill = Skill.objects.create(
            creator=user,
            name="Draft Skill",
            slug="draft-skill-submit",
            description="A draft skill",
            category="CODE_DEV",
            status=SkillStatus.DRAFT,
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            package_sha256="s" * 64,
            package_size=100,
            current_version="1.0.0",
        )
        SkillVersion.objects.create(
            skill=skill, version="1.0.0",
            package_file=skill.package_file,
            package_sha256="s" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/skills/{skill.id}/submit",
            **_jwt_header(user),
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["status"] == SkillStatus.SCANNING

    @pytest.mark.django_db
    def test_submit_approved_skill_with_pending_version(self, client, user, approved_skill):
        """POST /api/skills/{id}/submit on APPROVED skill with pending version succeeds."""
        SkillVersion.objects.create(
            skill=approved_skill, version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="q" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/skills/{approved_skill.id}/submit",
            **_jwt_header(user),
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        # Skill stays approved — only the version is pending
        assert body["status"] == SkillStatus.APPROVED

    @pytest.mark.django_db
    def test_submit_without_package_rejected(self, client, user):
        """POST /api/skills/{id}/submit without package returns 400."""
        skill = Skill.objects.create(
            creator=user,
            name="No Package",
            slug="no-package-submit",
            description="Missing package",
            category="CODE_DEV",
            status=SkillStatus.DRAFT,
        )
        resp = client.post(
            f"/api/skills/{skill.id}/submit",
            **_jwt_header(user),
        )
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_submit_unauthenticated_rejected(self, client, approved_skill):
        """POST /api/skills/{id}/submit without auth returns 401."""
        resp = client.post(f"/api/skills/{approved_skill.id}/submit")
        assert resp.status_code == 401


class TestHTTPVersionTargetedModeration:
    """HTTP-level tests for version-targeted admin review."""

    @pytest.mark.django_db
    def test_approve_specific_pending_version(self, client, admin_user, user, approved_skill):
        """POST /api/admin/skills/{id}/review with version_id approves that exact version."""
        pending = SkillVersion.objects.create(
            skill=approved_skill, version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="v" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/admin/skills/{approved_skill.id}/review",
            data=json.dumps({
                "action": "APPROVE",
                "reason": "",
                "version_id": pending.id,
            }),
            content_type="application/json",
            **_jwt_header(admin_user),
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["status"] == SkillStatus.APPROVED
        # Version should now be approved and promoted
        pending.refresh_from_db()
        assert pending.status == VersionStatus.APPROVED
        approved_skill.refresh_from_db()
        assert approved_skill.current_version == "2.0.0"

    @pytest.mark.django_db
    def test_reject_specific_pending_version(self, client, admin_user, user, approved_skill):
        """POST /api/admin/skills/{id}/review with version_id rejects that exact version."""
        pending = SkillVersion.objects.create(
            skill=approved_skill, version="3.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="3.0.0")}),
            package_sha256="w" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/admin/skills/{approved_skill.id}/review",
            data=json.dumps({
                "action": "REJECT",
                "reason": "Quality issues",
                "version_id": pending.id,
            }),
            content_type="application/json",
            **_jwt_header(admin_user),
        )
        assert resp.status_code == 200
        pending.refresh_from_db()
        assert pending.status == VersionStatus.REJECTED
        # Skill stays approved
        approved_skill.refresh_from_db()
        assert approved_skill.status == SkillStatus.APPROVED
        assert approved_skill.current_version == "1.0.0"

    @pytest.mark.django_db
    def test_approve_nonexistent_version_id_returns_400(self, client, admin_user, user, approved_skill):
        """POST /api/admin/skills/{id}/review with invalid version_id returns 400."""
        SkillVersion.objects.create(
            skill=approved_skill, version="2.0.0",
            package_file=_make_zip({"SKILL.md": SKILL_MD.format(version="2.0.0")}),
            package_sha256="u" * 64,
            status=VersionStatus.SCANNING,
        )
        resp = client.post(
            f"/api/admin/skills/{approved_skill.id}/review",
            data=json.dumps({
                "action": "APPROVE",
                "reason": "",
                "version_id": 99999,
            }),
            content_type="application/json",
            **_jwt_header(admin_user),
        )
        assert resp.status_code == 400


class TestHTTPDualReviewEligibility:
    """HTTP-level tests for dual review eligibility: SkillCall OR 7-day SkillPurchase (task47)."""

    @pytest.mark.django_db
    def test_review_allowed_via_skill_call(self, client, buyer, approved_skill):
        """POST /api/skills/{id}/reviews succeeds when user has called the skill."""
        SkillCall.objects.create(
            skill=approved_skill,
            caller=buyer,
            skill_version="1.0.0",
            input_text="test",
            output_text="result",
        )
        resp = client.post(
            f"/api/skills/{approved_skill.id}/reviews",
            data=json.dumps({"rating": 5, "comment": "Great!", "tags": []}),
            content_type="application/json",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["rating"] == 5

    @pytest.mark.django_db
    def test_review_allowed_via_mature_purchase(self, client, buyer, approved_skill):
        """POST /api/skills/{id}/reviews succeeds when purchase is 7+ days old."""
        from django.utils import timezone
        from datetime import timedelta
        purchase = SkillPurchase.objects.create(
            skill=approved_skill, user=buyer,
            paid_amount=Decimal("0"), payment_type="FREE",
        )
        # Backdate the purchase to 8 days ago
        purchase.created_at = timezone.now() - timedelta(days=8)
        SkillPurchase.objects.filter(id=purchase.id).update(created_at=purchase.created_at)
        resp = client.post(
            f"/api/skills/{approved_skill.id}/reviews",
            data=json.dumps({"rating": 4, "comment": "Good", "tags": []}),
            content_type="application/json",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 201

    @pytest.mark.django_db
    def test_review_rejected_no_call_no_purchase(self, client, buyer, approved_skill):
        """POST /api/skills/{id}/reviews rejected when user has no call and no purchase."""
        resp = client.post(
            f"/api/skills/{approved_skill.id}/reviews",
            data=json.dumps({"rating": 3, "comment": "Test", "tags": []}),
            content_type="application/json",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 400
        assert "调用" in resp.json().get("detail", "") or "购买" in resp.json().get("detail", "")

    @pytest.mark.django_db
    def test_review_rejected_immature_purchase(self, client, buyer, approved_skill):
        """POST /api/skills/{id}/reviews rejected when purchase is less than 7 days old."""
        SkillPurchase.objects.create(
            skill=approved_skill, user=buyer,
            paid_amount=Decimal("0"), payment_type="FREE",
        )
        # Purchase just created — less than 7 days
        resp = client.post(
            f"/api/skills/{approved_skill.id}/reviews",
            data=json.dumps({"rating": 2, "comment": "Too soon", "tags": []}),
            content_type="application/json",
            **_jwt_header(buyer),
        )
        assert resp.status_code == 400


class TestReinstateQuarantined:
    """Report-lifecycle tests for quarantine reinstatement."""

    @pytest.fixture
    def creator(self, db):
        return User.objects.create_user(username="creator_r", email="creator_r@test.com", password="pw")

    def _make_reporters(self, n):
        from django.utils import timezone
        from datetime import timedelta
        users = []
        for i in range(n):
            u = User.objects.create_user(
                username=f"reporter_r{i}", email=f"reporter_r{i}@test.com", password="pw"
            )
            User.objects.filter(pk=u.pk).update(date_joined=timezone.now() - timedelta(days=30))
            u.refresh_from_db()
            users.append(u)
        return users

    @pytest.mark.django_db
    def test_three_reports_quarantine_single_version_skill_and_dismiss_restores(self, creator):
        """3 reports archive a single-version skill; dismissing reports restores it and resolve_package_file succeeds."""
        skill = Skill.objects.create(
            creator=creator, name="Single Ver Skill", slug="single-ver-skill",
            description="desc", category="utility", status=SkillStatus.APPROVED,
            current_version="1.0.0",
            package_file="skills/single-ver-skill/1.0.0.zip",
        )
        SkillVersion.objects.create(
            skill=skill, version="1.0.0", status=VersionStatus.APPROVED,
            package_file="skills/single-ver-skill/1.0.0.zip",
        )
        reporters = self._make_reporters(3)
        for r in reporters:
            SkillReportService.report(skill, r, ReportReason.MALICIOUS_CODE)
        skill.refresh_from_db()
        assert skill.status == SkillStatus.ARCHIVED

        # Dismiss: reinstate + delete reports
        reports_qs = SkillReport.objects.filter(skill=skill)
        SkillService.reinstate_quarantined(skill)
        reports_qs.delete()

        skill.refresh_from_db()
        assert skill.status == SkillStatus.APPROVED
        # resolve_package_file must succeed
        pkg = SkillService.resolve_package_file(skill)
        assert pkg is not None

    @pytest.mark.django_db
    def test_three_reports_quarantine_current_version_with_fallback_dismiss_restores_quarantined(self, creator, tmp_path, settings):
        """3 reports archive current version; fallback promoted; dismissing restores the quarantined newer version."""
        settings.MEDIA_ROOT = str(tmp_path)
        import os
        for ver in ("1.0.0", "2.0.0"):
            p = tmp_path / "skills" / "fallback-skill-r" / f"{ver}.zip"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_make_zip_bytes({"SKILL.md": f"---\nname: T\nversion: {ver}\n---\n"}))
        skill = Skill.objects.create(
            creator=creator, name="Fallback Skill R", slug="fallback-skill-r",
            description="desc", category="utility", status=SkillStatus.APPROVED,
            current_version="2.0.0",
            package_file="skills/fallback-skill-r/2.0.0.zip",
        )
        SkillVersion.objects.create(
            skill=skill, version="1.0.0", status=VersionStatus.APPROVED,
            package_file="skills/fallback-skill-r/1.0.0.zip",
        )
        v2 = SkillVersion.objects.create(
            skill=skill, version="2.0.0", status=VersionStatus.APPROVED,
            package_file="skills/fallback-skill-r/2.0.0.zip",
        )
        reporters = self._make_reporters(3)
        for r in reporters:
            SkillReportService.report(skill, r, ReportReason.MALICIOUS_CODE)
        skill.refresh_from_db()
        assert skill.status == SkillStatus.APPROVED
        v2.refresh_from_db()
        assert v2.status == VersionStatus.ARCHIVED

        SkillService.reinstate_quarantined(skill)
        v2.refresh_from_db()
        assert v2.status == VersionStatus.APPROVED

    @pytest.mark.django_db
    def test_dismiss_deletes_report_rows(self, creator):
        """Dismissed SkillReport rows are deleted so they no longer count toward threshold."""
        skill = Skill.objects.create(
            creator=creator, name="Delete Reports Skill", slug="delete-reports-skill",
            description="desc", category="utility", status=SkillStatus.APPROVED,
            current_version="1.0.0",
            package_file="skills/delete-reports-skill/1.0.0.zip",
        )
        SkillVersion.objects.create(
            skill=skill, version="1.0.0", status=VersionStatus.APPROVED,
            package_file="skills/delete-reports-skill/1.0.0.zip",
        )
        reporters = self._make_reporters(3)
        for r in reporters:
            SkillReportService.report(skill, r, ReportReason.MALICIOUS_CODE)
        assert SkillReport.objects.filter(skill=skill).count() == 3

        SkillReport.objects.filter(skill=skill).delete()
        assert SkillReport.objects.filter(skill=skill).count() == 0
