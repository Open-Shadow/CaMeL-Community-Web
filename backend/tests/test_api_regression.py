"""API-level regression tests for skill module (AC-2, AC-5, AC-6).

These tests exercise the service-layer code paths that API endpoints depend on.
They require a running PostgreSQL database.
"""
import io
import zipfile
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.skills.models import (
    Skill,
    SkillPurchase,
    SkillVersion,
    PricingModel,
    ScanResult,
    SkillStatus,
    VersionStatus,
)
from apps.skills.services import SkillService


def _make_zip(files: dict[str, str | bytes]) -> SimpleUploadedFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            zf.writestr(name, data)
    buf.seek(0)
    return SimpleUploadedFile("test.zip", buf.read(), content_type="application/zip")


SKILL_MD = """---
name: Test Skill
description: A test skill
version: "{version}"
---

# Test Skill
"""


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


# --- resolve_package_file tests (download/file-tree gating) ---

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


# --- Version-scoped admin_reject tests ---

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
        # Live version still approved
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


# --- Duplicate version validation tests ---

class TestDuplicateVersionValidation:
    """Tests for duplicate version rejection before DB insert."""

    @pytest.mark.django_db
    def test_duplicate_version_rejected(self, approved_skill):
        data = {
            "version": "1.0.0",
            "package_file": _make_zip({"SKILL.md": SKILL_MD.format(version="1.0.0")}),
            "package_sha256": "f" * 64,
            "package_size": 100,
        }
        with pytest.raises(ValueError, match="已存在"):
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


# --- Scan pipeline PASS/WARN/FAIL tests ---

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


# --- Version-scoped quarantine tests ---

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
            # Set join date to > 7 days ago
            from django.utils import timezone
            from datetime import timedelta
            u.date_joined = timezone.now() - timedelta(days=30)
            u.save()
            reporters.append(u)

        for r in reporters:
            SkillReportService.report(approved_skill, r, ReportReason.MALICIOUS_CODE)

        # The current version should be archived
        v = approved_skill.versions.get(version="1.0.0")
        assert v.status == VersionStatus.ARCHIVED

        # Since there are no other approved versions, the skill itself should be archived
        approved_skill.refresh_from_db()
        assert approved_skill.status == SkillStatus.ARCHIVED
