"""Credit system API routes."""
from decimal import Decimal

from ninja import Router, Schema

from common.permissions import AuthBearer
from apps.credits.services import CreditService
from common.constants import CreditLevelConfig


router = Router(tags=["credits"], auth=AuthBearer())


# =============================================================================
# Schemas
# =============================================================================

class DiscountInfoOutput(Schema):
    level: str
    level_name: str
    level_icon: str
    credit_score: int
    discount_rate: float
    discounted_price: float | None = None


class ThresholdCheckOutput(Schema):
    allowed: bool
    reason: str
    credit_score: int
    required_score: int


class PriceCalcInput(Schema):
    base_price: float


class PriceCalcOutput(Schema):
    base_price: float
    discount_rate: float
    discounted_price: float
    level: str
    level_name: str
    savings: float


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/discount-info", response=DiscountInfoOutput)
def get_discount_info(request):
    """Get current user's credit level discount info."""
    user = request.auth
    discount = CreditService.get_discount_rate(user)
    level_info = CreditLevelConfig.get_level_by_score(user.credit_score)

    return {
        "level": user.level,
        "level_name": level_info[1],
        "level_icon": level_info[2],
        "credit_score": user.credit_score,
        "discount_rate": discount,
    }


@router.post("/calculate-price", response=PriceCalcOutput)
def calculate_discounted_price(request, data: PriceCalcInput):
    """Calculate discounted price for a Skill call based on user's credit level."""
    user = request.auth
    base = Decimal(str(data.base_price))
    discounted = CreditService.get_discounted_price(user, base)
    discount = CreditService.get_discount_rate(user)
    level_info = CreditLevelConfig.get_level_by_score(user.credit_score)

    return {
        "base_price": float(base),
        "discount_rate": discount,
        "discounted_price": float(discounted),
        "level": user.level,
        "level_name": level_info[1],
        "savings": float(base - discounted),
    }


@router.get("/check/bounty-post", response=ThresholdCheckOutput)
def check_bounty_post(request):
    """Check if current user can post a bounty."""
    user = request.auth
    allowed, reason = CreditService.check_bounty_post_threshold(user)
    return {
        "allowed": allowed,
        "reason": reason,
        "credit_score": user.credit_score,
        "required_score": 50,
    }


@router.get("/check/bounty-apply", response=ThresholdCheckOutput)
def check_bounty_apply(request):
    """Check if current user can apply for a bounty."""
    user = request.auth
    allowed, reason = CreditService.check_bounty_apply_threshold(user)
    return {
        "allowed": allowed,
        "reason": reason,
        "credit_score": user.credit_score,
        "required_score": 50,
    }


@router.get("/check/arbitration", response=ThresholdCheckOutput)
def check_arbitration(request):
    """Check if current user can participate in arbitration."""
    user = request.auth
    allowed, reason = CreditService.check_arbitration_threshold(user)
    return {
        "allowed": allowed,
        "reason": reason,
        "credit_score": user.credit_score,
        "required_score": 500,
    }
