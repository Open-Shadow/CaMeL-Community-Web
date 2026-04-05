from decimal import Decimal

from apps.workshop.rules import (
    ARTICLE_COLLAPSE_THRESHOLD,
    COMMENT_COLLAPSE_THRESHOLD,
    get_article_vote_weight,
    should_collapse_article,
    should_collapse_comment,
)


def test_article_vote_weight_defaults_to_seed():
    assert get_article_vote_weight("UNKNOWN") == Decimal("1.0")


def test_article_vote_weight_uses_credit_level():
    assert get_article_vote_weight("SEED") == Decimal("1.0")
    assert get_article_vote_weight("CRAFTSMAN") == Decimal("1.5")
    assert get_article_vote_weight("EXPERT") == Decimal("2.0")
    assert get_article_vote_weight("MASTER") == Decimal("3.0")
    assert get_article_vote_weight("GRANDMASTER") == Decimal("5.0")


def test_article_collapse_threshold():
    assert ARTICLE_COLLAPSE_THRESHOLD == Decimal("-5")
    assert not should_collapse_article(Decimal("-5"))
    assert should_collapse_article(Decimal("-5.01"))


def test_comment_collapse_threshold():
    assert COMMENT_COLLAPSE_THRESHOLD == -3
    assert not should_collapse_comment(-2)
    assert should_collapse_comment(-3)
