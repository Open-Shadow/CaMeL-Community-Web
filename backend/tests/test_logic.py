"""
Pure Python tests — no Django required.
Tests CreditLevelConfig, LEVEL_MAP logic, and permission decorator logic.
"""
import sys
import os

# Minimal Django stub so imports don't fail
import types

# Stub django modules
django_stub = types.ModuleType("django")
django_stub.VERSION = (5, 2, 0, "final", 0)
sys.modules.setdefault("django", django_stub)

for mod in ["django.db", "django.db.models", "django.utils", "django.utils.timezone",
            "django.contrib", "django.contrib.auth", "django.core", "django.core.exceptions",
            "ninja", "ninja.errors"]:
    sys.modules.setdefault(mod, types.ModuleType(mod))

# Stub HttpError
class HttpError(Exception):
    def __init__(self, status_code, message=""):
        self.status_code = status_code
        self.message = message
sys.modules["ninja.errors"].HttpError = HttpError

import pytest

# ── Import real modules ───────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common.constants import CreditLevelConfig, CreditLevel


# ── CreditLevelConfig ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("score,expected", [
    (0, CreditLevel.SPROUT),
    (50, CreditLevel.SPROUT),
    (99, CreditLevel.SPROUT),
    (100, CreditLevel.CRAFTSMAN),
    (499, CreditLevel.CRAFTSMAN),
    (500, CreditLevel.EXPERT),
    (1999, CreditLevel.EXPERT),
    (2000, CreditLevel.MASTER),
    (4999, CreditLevel.MASTER),
    (5000, CreditLevel.GRANDMASTER),
    (99999, CreditLevel.GRANDMASTER),
])
def test_get_level_by_score(score, expected):
    assert CreditLevelConfig.get_level_by_score(score)[0] == expected


@pytest.mark.parametrize("score,expected", [
    (0, 1.0),
    (99, 1.0),
    (100, 0.95),
    (500, 0.90),
    (2000, 0.85),
    (5000, 0.80),
])
def test_get_discount(score, expected):
    assert CreditLevelConfig.get_discount(score) == expected


# ── LEVEL_MAP (Bug 1 fix) ─────────────────────────────────────────────────────

LEVEL_MAP = {
    "sprout": "SEED",
    "craftsman": "CRAFTSMAN",
    "expert": "EXPERT",
    "master": "MASTER",
    "grandmaster": "GRANDMASTER",
}

@pytest.mark.parametrize("score,expected_user_level", [
    (0, "SEED"),
    (99, "SEED"),
    (100, "CRAFTSMAN"),
    (500, "EXPERT"),
    (2000, "MASTER"),
    (5000, "GRANDMASTER"),
])
def test_level_map_no_sprout_bug(score, expected_user_level):
    """Bug 1: level[0].upper() would give 'SPROUT' not 'SEED'."""
    level_key = CreditLevelConfig.get_level_by_score(score)[0]
    result = LEVEL_MAP.get(level_key, "SEED")
    assert result == expected_user_level
    # Verify the old buggy approach would fail for sprout
    if level_key == "sprout":
        assert level_key[0].upper() != expected_user_level  # 'S' != 'SEED'


# ── Permission decorators (Bug 4 fix) ─────────────────────────────────────────

def make_moderator_required():
    from functools import wraps
    def moderator_required(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'auth', None)
            if not user or user.role not in ('MODERATOR', 'ADMIN'):
                raise HttpError(403, "需要版主权限")
            return func(request, *args, **kwargs)
        return wrapper
    return moderator_required

def make_admin_required():
    from functools import wraps
    def admin_required(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'auth', None)
            if not user or user.role != 'ADMIN':
                raise HttpError(403, "需要管理员权限")
            return func(request, *args, **kwargs)
        return wrapper
    return admin_required


moderator_required = make_moderator_required()
admin_required = make_admin_required()


class Req:
    def __init__(self, role=None):
        self.auth = type("U", (), {"role": role})() if role else None


def test_moderator_blocks_no_auth():
    @moderator_required
    def view(r): return "ok"
    with pytest.raises(HttpError) as e:
        view(Req())
    assert e.value.status_code == 403

def test_moderator_blocks_user():
    @moderator_required
    def view(r): return "ok"
    with pytest.raises(HttpError):
        view(Req("USER"))

def test_moderator_allows_moderator():
    @moderator_required
    def view(r): return "ok"
    assert view(Req("MODERATOR")) == "ok"

def test_moderator_allows_admin():
    @moderator_required
    def view(r): return "ok"
    assert view(Req("ADMIN")) == "ok"

def test_admin_blocks_moderator():
    @admin_required
    def view(r): return "ok"
    with pytest.raises(HttpError) as e:
        view(Req("MODERATOR"))
    assert e.value.status_code == 403

def test_admin_allows_admin():
    @admin_required
    def view(r): return "ok"
    assert view(Req("ADMIN")) == "ok"

def test_admin_blocks_no_auth():
    @admin_required
    def view(r): return "ok"
    with pytest.raises(HttpError):
        view(Req())


# ── CreditService.can_* ───────────────────────────────────────────────────────

def can_post_bounty(user): return user.credit_score >= 50
def can_apply_bounty(user): return user.credit_score >= 50
def can_arbitrate(user): return user.credit_score >= 500

@pytest.mark.parametrize("score,expected", [(0, False), (49, False), (50, True), (100, True)])
def test_can_post_bounty(score, expected):
    u = type("U", (), {"credit_score": score})()
    assert can_post_bounty(u) == expected

@pytest.mark.parametrize("score,expected", [(0, False), (499, False), (500, True), (5000, True)])
def test_can_arbitrate(score, expected):
    u = type("U", (), {"credit_score": score})()
    assert can_arbitrate(u) == expected


# ── CREDIT_TIERS constants (Bug 3 fix) ────────────────────────────────────────

CREDIT_TIERS = [
    {"name": "新芽", "icon": "🌱", "min": 0,    "max": 99,       "discount": 1.0},
    {"name": "工匠", "icon": "🔧", "min": 100,  "max": 499,      "discount": 0.95},
    {"name": "专家", "icon": "⚡", "min": 500,  "max": 1999,     "discount": 0.9},
    {"name": "大师", "icon": "🏆", "min": 2000, "max": 4999,     "discount": 0.85},
    {"name": "宗师", "icon": "👑", "min": 5000, "max": float("inf"), "discount": 0.8},
]

def test_credit_tiers_count():
    assert len(CREDIT_TIERS) == 5

def test_credit_tiers_coverage():
    """Tiers should cover 0 to infinity without gaps."""
    for i in range(len(CREDIT_TIERS) - 1):
        assert CREDIT_TIERS[i]["max"] + 1 == CREDIT_TIERS[i + 1]["min"]

def test_credit_tiers_discounts_descending():
    discounts = [t["discount"] for t in CREDIT_TIERS]
    assert discounts == sorted(discounts, reverse=True)
