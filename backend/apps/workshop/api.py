"""Workshop API routes."""
from decimal import Decimal
from ninja import Router, Schema
from ninja.pagination import paginate
from common.permissions import login_required
from apps.workshop.services import TipService

router = Router()


class TipIn(Schema):
    amount: Decimal


class TipperOut(Schema):
    id: int
    display_name: str = ""
    avatar_url: str = ""


class TipOut(Schema):
    id: int
    tipper: TipperOut
    amount: float
    created_at: str


class LeaderboardEntry(Schema):
    rank: int
    user_id: int
    display_name: str
    avatar_url: str
    total_tips: float


@router.post("/articles/{article_id}/tip", auth=login_required)
def send_tip(request, article_id: int, payload: TipIn):
    tip = TipService.send_tip(request.auth, article_id, payload.amount)
    return {"id": tip.id, "amount": float(tip.amount)}


@router.get("/articles/{article_id}/tips", response=list[TipOut])
def get_article_tips(request, article_id: int, limit: int = 20):
    tips = TipService.get_article_tips(article_id, limit)
    return [
        TipOut(
            id=t.id,
            tipper=TipperOut(
                id=t.tipper.id,
                display_name=t.tipper.display_name or t.tipper.email,
                avatar_url=getattr(t.tipper, "avatar_url", "") or "",
            ),
            amount=float(t.amount),
            created_at=t.created_at.isoformat(),
        )
        for t in tips
    ]


@router.get("/tips/leaderboard", response=list[LeaderboardEntry])
def get_leaderboard(request, limit: int = 20):
    return TipService.get_leaderboard(limit)
