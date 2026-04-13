"""Tests for the transformed Skill module data model (AC-1)."""
import pytest
from decimal import Decimal
from django.db import IntegrityError

from apps.accounts.models import User
from apps.skills.models import (
    Skill,
    SkillCall,
    SkillPurchase,
    SkillReport,
    SkillVersion,
    PricingModel,
    ReportReason,
    SkillStatus,
    VersionStatus,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(username="creator", email="c@test.com", password="pw")


@pytest.fixture
def buyer(db):
    return User.objects.create_user(username="buyer", email="b@test.com", password="pw")


@pytest.fixture
def skill(user):
    return Skill.objects.create(
        creator=user,
        name="Test Skill",
        slug="test-skill",
        description="A test skill",
        category="CODE_DEV",
        pricing_model=PricingModel.FREE,
        status=SkillStatus.APPROVED,
    )


@pytest.fixture
def paid_skill(user):
    return Skill.objects.create(
        creator=user,
        name="Paid Skill",
        slug="paid-skill",
        description="A paid skill",
        category="CODE_DEV",
        pricing_model=PricingModel.PAID,
        price=Decimal("1.99"),
        status=SkillStatus.APPROVED,
    )


# --- AC-1: Model fields ---


class TestSkillModelFields:
    def test_has_package_fields(self, skill):
        assert hasattr(skill, "package_file")
        assert hasattr(skill, "package_sha256")
        assert hasattr(skill, "package_size")
        assert hasattr(skill, "readme_html")
        assert hasattr(skill, "download_count")

    def test_pricing_model_free(self, skill):
        assert skill.pricing_model == PricingModel.FREE

    def test_pricing_model_paid(self, paid_skill):
        assert paid_skill.pricing_model == PricingModel.PAID

    def test_no_old_prompt_fields(self, skill):
        assert not hasattr(skill, "system_prompt")
        assert not hasattr(skill, "user_prompt_template")
        assert not hasattr(skill, "output_format")
        assert not hasattr(skill, "example_input")
        assert not hasattr(skill, "example_output")

    def test_status_choices(self, db):
        valid = {e.value for e in SkillStatus}
        assert "DRAFT" in valid
        assert "SCANNING" in valid
        assert "APPROVED" in valid
        assert "REJECTED" in valid
        assert "ARCHIVED" in valid
        assert "PENDING_REVIEW" not in valid

    def test_pricing_model_no_per_use(self, db):
        valid = {e.value for e in PricingModel}
        assert "FREE" in valid
        assert "PAID" in valid
        assert "PER_USE" not in valid


class TestSkillVersionModel:
    def test_version_fields(self, skill):
        sv = SkillVersion.objects.create(
            skill=skill,
            version="1.0.0",
            package_file="test.zip",
            package_sha256="a" * 64,
            changelog="Initial release",
            status=VersionStatus.SCANNING,
        )
        assert sv.version == "1.0.0"
        assert sv.changelog == "Initial release"
        assert sv.status == VersionStatus.SCANNING
        assert sv.package_sha256 == "a" * 64

    def test_no_old_version_fields(self, skill):
        sv = SkillVersion.objects.create(
            skill=skill,
            version="1.0.0",
            package_file="test.zip",
            package_sha256="a" * 64,
        )
        assert not hasattr(sv, "system_prompt")
        assert not hasattr(sv, "user_prompt_template")
        assert not hasattr(sv, "change_note")
        assert not hasattr(sv, "is_major")

    def test_version_scoped_status(self, skill):
        v1 = SkillVersion.objects.create(
            skill=skill, version="1.0.0", package_file="v1.zip",
            package_sha256="a" * 64, status=VersionStatus.APPROVED,
        )
        v2 = SkillVersion.objects.create(
            skill=skill, version="2.0.0", package_file="v2.zip",
            package_sha256="b" * 64, status=VersionStatus.SCANNING,
        )
        assert v1.status == VersionStatus.APPROVED
        assert v2.status == VersionStatus.SCANNING


class TestSkillCallModel:
    def test_no_amount_charged(self, skill, buyer):
        call = SkillCall.objects.create(
            skill=skill, caller=buyer, skill_version="1", input_text="hello",
        )
        assert not hasattr(call, "amount_charged")


class TestSkillPurchaseModel:
    def test_purchase_fields(self, skill, buyer):
        purchase = SkillPurchase.objects.create(
            skill=skill, user=buyer, paid_amount=Decimal("0"), payment_type="FREE",
        )
        assert purchase.paid_amount == Decimal("0")
        assert purchase.payment_type == "FREE"

    def test_unique_together(self, skill, buyer):
        SkillPurchase.objects.create(
            skill=skill, user=buyer, paid_amount=0, payment_type="FREE",
        )
        with pytest.raises(IntegrityError):
            SkillPurchase.objects.create(
                skill=skill, user=buyer, paid_amount=0, payment_type="FREE",
            )


class TestSkillReportModel:
    def test_report_fields(self, skill, buyer):
        report = SkillReport.objects.create(
            skill=skill, reporter=buyer,
            reason=ReportReason.MALICIOUS_CODE, detail="suspicious",
        )
        assert report.reason == ReportReason.MALICIOUS_CODE
        assert report.detail == "suspicious"

    def test_unique_together(self, skill, buyer):
        SkillReport.objects.create(
            skill=skill, reporter=buyer,
            reason=ReportReason.MALICIOUS_CODE,
        )
        with pytest.raises(IntegrityError):
            SkillReport.objects.create(
                skill=skill, reporter=buyer,
                reason=ReportReason.FALSE_DESCRIPTION,
            )
