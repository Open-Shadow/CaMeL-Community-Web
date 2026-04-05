"""Pure workshop voting and collapse rules."""
from decimal import Decimal


ARTICLE_COLLAPSE_THRESHOLD = Decimal("-5")
COMMENT_COLLAPSE_THRESHOLD = -3

ARTICLE_VOTE_WEIGHTS = {
    "SEED": Decimal("1.0"),
    "CRAFTSMAN": Decimal("1.5"),
    "EXPERT": Decimal("2.0"),
    "MASTER": Decimal("3.0"),
    "GRANDMASTER": Decimal("5.0"),
}


def get_article_vote_weight(level: str) -> Decimal:
    return ARTICLE_VOTE_WEIGHTS.get(level, Decimal("1.0"))


def should_collapse_article(net_votes: Decimal | float | int) -> bool:
    return Decimal(str(net_votes)) < ARTICLE_COLLAPSE_THRESHOLD


def should_collapse_comment(net_votes: int) -> bool:
    return net_votes <= COMMENT_COLLAPSE_THRESHOLD
