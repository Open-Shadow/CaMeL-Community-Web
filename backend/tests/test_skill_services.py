"""Tests for SkillPurchaseService and SkillReportService."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.skills.models import (
    Skill,
    SkillPurchase,
    SkillReport,
    PricingModel,
    ReportReason,
    SkillStatus,
)
from apps.skills.services import SkillPurchaseService, SkillReportService


@pytest.fixture
def creator(db):
    u = User.objects.create_user(username="creator", email="c@test.com", password="pw")
    u.balance = Decimal("100.00")
    u.save(update_fields=["balance"])
    return u


@pytest.fixture
def buyer(db):
    u = User.objects.create_user(username="buyer", email="b@test.com", password="pw")
    u.balance = Decimal("100.00")
    u.date_joined = timezone.now() - timedelta(days=30)
    u.save(update_fields=["balance", "date_joined"])
    return u


@pytest.fixture
def free_skill(creator):
    return Skill.objects.create(
        creator=creator,
        name="Free Skill",
        slug="free-skill",
        description="A free skill",
        category="CODE_DEV",
        pricing_model=PricingModel.FREE,
        status=SkillStatus.APPROVED,
    )


@pytest.fixture
def paid_skill(creator):
    return Skill.objects.create(
        creator=creator,
        name="Paid Skill",
        slug="paid-skill",
        description="A paid skill",
        category="CODE_DEV",
        pricing_model=PricingModel.PAID,
        price=Decimal("2.00"),
        status=SkillStatus.APPROVED,
    )


class TestSkillPurchaseService:
    def test_purchase_free_skill(self, free_skill, buyer):
        purchase = SkillPurchaseService.purchase(free_skill, buyer)
        assert purchase.paid_amount == Decimal("0")
        assert purchase.payment_type == "FREE"

    def test_purchase_idempotent(self, free_skill, buyer):
        p1 = SkillPurchaseService.purchase(free_skill, buyer)
        p2 = SkillPurchaseService.purchase(free_skill, buyer)
        assert p1.id == p2.id

    def test_purchase_paid_skill_deducts_balance(self, paid_skill, buyer):
        purchase = SkillPurchaseService.purchase(paid_skill, buyer)
        assert purchase.paid_amount == Decimal("2.00")
        assert purchase.payment_type == "MONEY"

        buyer.refresh_from_db()
        assert buyer.balance == Decimal("98.00")

    def test_purchase_paid_skill_credits_creator(self, paid_skill, buyer, creator):
        SkillPurchaseService.purchase(paid_skill, buyer)

        creator.refresh_from_db()
        # Creator gets price minus 15% platform fee
        # 2.00 * 0.85 = 1.70
        assert creator.balance == Decimal("101.70")

    def test_purchase_insufficient_balance(self, paid_skill, buyer):
        buyer.balance = Decimal("0.50")
        buyer.save(update_fields=["balance"])

        with pytest.raises(Exception, match="余额不足"):
            SkillPurchaseService.purchase(paid_skill, buyer)

    def test_purchase_draft_skill_rejected(self, creator, buyer):
        draft = Skill.objects.create(
            creator=creator, name="Draft", slug="draft-skill",
            description="draft", category="CODE_DEV",
            pricing_model=PricingModel.FREE, status=SkillStatus.DRAFT,
        )
        with pytest.raises(ValueError, match="暂不可购买"):
            SkillPurchaseService.purchase(draft, buyer)

    def test_creator_gets_free_access(self, paid_skill, creator):
        purchase = SkillPurchaseService.purchase(paid_skill, creator)
        assert purchase.paid_amount == Decimal("0")
        assert purchase.payment_type == "FREE"

    def test_has_access_free_skill(self, free_skill, buyer):
        assert SkillPurchaseService.has_access(free_skill, buyer) is True

    def test_has_access_paid_not_purchased(self, paid_skill, buyer):
        assert SkillPurchaseService.has_access(paid_skill, buyer) is False

    def test_has_access_paid_purchased(self, paid_skill, buyer):
        SkillPurchaseService.purchase(paid_skill, buyer)
        assert SkillPurchaseService.has_access(paid_skill, buyer) is True

    def test_has_access_creator(self, paid_skill, creator):
        assert SkillPurchaseService.has_access(paid_skill, creator) is True


class TestSkillReportService:
    def test_report_basic(self, free_skill, buyer):
        report = SkillReportService.report(
            free_skill, buyer, ReportReason.MALICIOUS_CODE, "suspicious code",
        )
        assert report.reason == ReportReason.MALICIOUS_CODE
        assert report.detail == "suspicious code"

    def test_cannot_report_own_skill(self, free_skill, creator):
        with pytest.raises(ValueError, match="不能举报自己"):
            SkillReportService.report(free_skill, creator, ReportReason.MALICIOUS_CODE)

    def test_account_age_check(self, free_skill, db):
        new_user = User.objects.create_user(
            username="newbie", email="n@test.com", password="pw",
        )
        # date_joined is auto_now_add, so it's "now" — should fail the age check
        with pytest.raises(ValueError, match="天才能举报"):
            SkillReportService.report(free_skill, new_user, ReportReason.MALICIOUS_CODE)

    def test_auto_quarantine_on_threshold(self, free_skill, db):
        reporters = []
        for i in range(3):
            u = User.objects.create_user(
                username=f"reporter{i}", email=f"r{i}@test.com", password="pw",
            )
            u.date_joined = timezone.now() - timedelta(days=30)
            u.save(update_fields=["date_joined"])
            reporters.append(u)

        for u in reporters:
            SkillReportService.report(free_skill, u, ReportReason.MALICIOUS_CODE)

        free_skill.refresh_from_db()
        assert free_skill.status == SkillStatus.ARCHIVED

    def test_idempotent_report(self, free_skill, buyer):
        r1 = SkillReportService.report(free_skill, buyer, ReportReason.MALICIOUS_CODE)
        r2 = SkillReportService.report(free_skill, buyer, ReportReason.FALSE_DESCRIPTION)
        assert r1.id == r2.id  # get_or_create returns existing
