"""Workshop API routes."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.workshop.models import Article, ArticleStatus, Comment, Series, Vote
from apps.workshop.schemas import (
    ArticleCreateInput,
    ArticleDetailOut,
    ArticleRecommendationOut,
    ArticleSummaryOut,
    ArticleUpdateInput,
    CommentVoteInput,
    CommentVoteOut,
    CommentCreateInput,
    CommentOut,
    CommentReplyOut,
    MessageOut,
    PinCommentInput,
    SeriesCreateInput,
    SeriesDetailOut,
    SeriesReorderInput,
    SeriesSummaryOut,
    SeriesUpdateInput,
    VoteInput,
    VoteOut,
)
from apps.workshop.services import ArticleService, SeriesService, TipService
from common.permissions import AuthBearer
from common.utils import build_absolute_media_url

router = Router(tags=["workshop"])
User = get_user_model()


# ─── Tip schemas (from main) ───────────────────────────────────────────────────

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


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_optional_user(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None

    token = header.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        payload = AccessToken(token)
        return User.objects.get(id=payload["user_id"])
    except (TokenError, User.DoesNotExist, KeyError):
        return None


def _author_out(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "level": user.level,
        "credit_score": user.credit_score,
    }


def _related_skill_out(skill) -> dict | None:
    if not skill:
        return None
    return {
        "id": skill.id,
        "name": skill.name,
        "category": skill.category,
        "pricing_model": skill.pricing_model,
        "price_per_use": float(skill.price_per_use) if skill.price_per_use else None,
        "total_calls": skill.total_calls,
        "avg_rating": float(skill.avg_rating),
        "creator_name": skill.creator.display_name or skill.creator.username,
    }


def _excerpt(content: str) -> str:
    import re
    from django.utils.html import strip_tags

    text = re.sub(r"\s+", " ", strip_tags(content)).strip()
    return text[:140] + ("..." if len(text) > 140 else "")


def _article_summary_out(article: Article) -> dict:
    comment_count = getattr(article, "comment_count", None)
    if comment_count is None:
        comment_count = article.comments.count()

    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "excerpt": _excerpt(article.content),
        "difficulty": article.difficulty,
        "article_type": article.article_type,
        "model_tags": article.model_tags,
        "custom_tags": article.custom_tags,
        "status": article.status,
        "is_featured": article.is_featured,
        "net_votes": float(article.net_votes),
        "total_tips": float(article.total_tips),
        "comment_count": comment_count,
        "view_count": article.view_count,
        "author": _author_out(article.author),
        "related_skill": _related_skill_out(article.related_skill),
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "published_at": article.published_at.isoformat() if article.published_at else None,
    }


def _article_detail_out(article: Article, user=None) -> dict:
    my_vote = None
    if user:
        vote = Vote.objects.filter(article=article, voter=user).first()
        if vote:
            my_vote = "UP" if vote.is_upvote else "DOWN"

    return {
        **_article_summary_out(article),
        "content": article.content,
        "is_outdated": article.is_outdated,
        "my_vote": my_vote,
    }


def _recommended_article_out(item: dict) -> dict:
    return {
        **_article_summary_out(item["article"]),
        "recommendation_reason": item["reason"],
    }


def _series_summary_out(series: Series) -> dict:
    article_count = getattr(series, "article_count", None)
    published_count = getattr(series, "published_count", None)
    if article_count is None or published_count is None:
        article_count = series.articles.count()
        published_count = series.articles.filter(status=ArticleStatus.PUBLISHED).count()
    return {
        "id": series.id,
        "title": series.title,
        "description": series.description,
        "cover_url": series.cover_url,
        "is_completed": series.is_completed,
        "completion_rewarded": series.completion_rewarded,
        "article_count": article_count,
        "published_count": published_count,
        "author": _author_out(series.author),
        "created_at": series.created_at.isoformat(),
        "updated_at": series.updated_at.isoformat(),
    }


def _series_detail_out(series: Series, user=None) -> dict:
    articles = series.articles.select_related("author", "related_skill", "related_skill__creator").annotate(
        comment_count=Count("comments")
    )
    if not user or user.id != series.author_id:
        articles = articles.filter(status=ArticleStatus.PUBLISHED)
    ordered = list(articles.order_by("series_order", "published_at", "created_at"))
    return {
        **_series_summary_out(series),
        "articles": [_article_summary_out(article) for article in ordered],
    }


def _comment_reply_out(comment: Comment) -> dict:
    user = getattr(comment, "_current_user", None)
    my_vote = None
    if user:
        comment_vote = comment.votes.filter(voter=user).first()
        if comment_vote:
            my_vote = "UP" if comment_vote.value > 0 else "DOWN"
    return {
        "id": comment.id,
        "content": comment.content,
        "net_votes": comment.net_votes,
        "is_pinned": comment.is_pinned,
        "is_collapsed": ArticleService.should_collapse_comment(comment),
        "my_vote": my_vote,
        "author": _author_out(comment.author),
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
    }


def _comment_out(comment: Comment, user=None) -> dict:
    replies = comment.replies.select_related("author").order_by("created_at")
    comment._current_user = user
    for reply in replies:
        reply._current_user = user
    return {
        **_comment_reply_out(comment),
        "replies": [_comment_reply_out(reply) for reply in replies],
    }


# ─── Tip endpoints (from main) ────────────────────────────────────────────────

@router.post("/articles/{article_id}/tip", auth=AuthBearer())
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
                avatar_url=build_absolute_media_url(
                    request, getattr(t.tipper, "avatar_url", "") or ""
                ),
            ),
            amount=float(t.amount),
            created_at=t.created_at.isoformat(),
        )
        for t in tips
    ]


@router.get("/tips/leaderboard", response=list[LeaderboardEntry])
def get_leaderboard(request, limit: int = 20):
    return [
        {
            **entry,
            "avatar_url": build_absolute_media_url(request, entry.get("avatar_url", "")),
        }
        for entry in TipService.get_leaderboard(limit)
    ]


# ─── Article endpoints (from feat-b) ──────────────────────────────────────────

@router.get("", response=list[ArticleSummaryOut])
def list_articles(
    request,
    difficulty: Optional[str] = None,
    article_type: Optional[str] = None,
    model_tag: Optional[str] = None,
    sort: str = "latest",
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    queryset = (
        Article.objects.select_related("author", "related_skill", "related_skill__creator")
        .filter(status=ArticleStatus.PUBLISHED)
        .annotate(comment_count=Count("comments"))
    )

    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)
    if article_type:
        queryset = queryset.filter(article_type=article_type)
    if model_tag:
        queryset = queryset.filter(model_tags__overlap=[model_tag])
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(content__icontains=q)
            | Q(custom_tags__overlap=[q])
            | Q(model_tags__overlap=[q])
        )

    if sort == "hot":
        queryset = queryset.order_by("-net_votes", "-view_count", "-published_at")
    elif sort == "featured":
        queryset = queryset.order_by("-is_featured", "-net_votes", "-published_at")
    else:
        queryset = queryset.order_by("-published_at", "-created_at")

    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    offset = (page - 1) * page_size
    return [_article_summary_out(article) for article in queryset[offset:offset + page_size]]


@router.get("/featured", response=list[ArticleSummaryOut])
def list_featured_articles(request, limit: int = 6):
    queryset = (
        Article.objects.select_related("author", "related_skill", "related_skill__creator")
        .filter(status=ArticleStatus.PUBLISHED, is_featured=True)
        .annotate(comment_count=Count("comments"))
        .order_by("-published_at")
    )
    articles = list(queryset[: min(max(limit, 1), 12)])
    if articles:
        return [_article_summary_out(article) for article in articles]

    fallback = (
        Article.objects.select_related("author", "related_skill", "related_skill__creator")
        .filter(status=ArticleStatus.PUBLISHED)
        .annotate(comment_count=Count("comments"))
        .order_by("-net_votes", "-published_at")[: min(max(limit, 1), 12)]
    )
    return [_article_summary_out(article) for article in fallback]


@router.get("/recommended", response=list[ArticleRecommendationOut], auth=AuthBearer())
def list_recommended_articles(request, limit: int = 8):
    return [
        _recommended_article_out(item)
        for item in ArticleService.list_recommended_articles(request.auth, limit=limit)
    ]


@router.get("/series", response=list[SeriesSummaryOut])
def list_series(request, limit: int = 12):
    queryset = (
        Series.objects.select_related("author")
        .annotate(
            article_count=Count("articles"),
            published_count=Count("articles", filter=Q(articles__status=ArticleStatus.PUBLISHED)),
        )
        .order_by("-is_completed", "-updated_at")
    )
    safe_limit = min(max(limit, 1), 50)
    return [_series_summary_out(series) for series in queryset[:safe_limit]]


@router.post("/series", response={201: SeriesDetailOut}, auth=AuthBearer())
def create_series(request, data: SeriesCreateInput):
    try:
        series = SeriesService.create(request.auth, data.dict())
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return 201, _series_detail_out(series, request.auth)


@router.get("/series/{series_id}", response=SeriesDetailOut)
def get_series(request, series_id: int):
    user = _get_optional_user(request)
    series = get_object_or_404(Series.objects.select_related("author"), id=series_id)
    return _series_detail_out(series, user)


@router.patch("/series/{series_id}", response=SeriesDetailOut, auth=AuthBearer())
def update_series(request, series_id: int, data: SeriesUpdateInput):
    series = get_object_or_404(Series, id=series_id, author=request.auth)
    try:
        series = SeriesService.update(series, data.dict())
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return _series_detail_out(series, request.auth)


@router.post("/series/{series_id}/reorder", response=SeriesDetailOut, auth=AuthBearer())
def reorder_series_articles(request, series_id: int, data: SeriesReorderInput):
    series = get_object_or_404(Series, id=series_id, author=request.auth)
    try:
        series = SeriesService.reorder_articles(series, data.article_ids)
        SeriesService.ensure_completion_reward(series)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return _series_detail_out(series, request.auth)


@router.get("/mine", response=list[ArticleSummaryOut], auth=AuthBearer())
def get_my_articles(request, status: Optional[str] = None):
    queryset = (
        Article.objects.select_related("author", "related_skill", "related_skill__creator")
        .filter(author=request.auth)
        .annotate(comment_count=Count("comments"))
        .order_by("-updated_at")
    )
    if status:
        queryset = queryset.filter(status=status)
    return [_article_summary_out(article) for article in queryset]


@router.get("/{article_id}", response=ArticleDetailOut)
def get_article(request, article_id: int):
    user = _get_optional_user(request)
    article = get_object_or_404(
        Article.objects.select_related("author", "related_skill", "related_skill__creator"),
        id=article_id,
    )

    if article.status != ArticleStatus.PUBLISHED and (not user or article.author_id != user.id):
        raise HttpError(404, "文章不存在")

    Article.objects.filter(id=article.id).update(view_count=F("view_count") + 1)
    article.refresh_from_db()
    ArticleService.record_read(article, user)
    return _article_detail_out(article, user)


@router.get("/{article_id}/related", response=list[ArticleRecommendationOut])
def list_related_articles(request, article_id: int, limit: int = 4):
    article = get_object_or_404(
        Article.objects.select_related("author", "related_skill", "related_skill__creator"),
        id=article_id,
        status=ArticleStatus.PUBLISHED,
    )
    return [_recommended_article_out(item) for item in ArticleService.list_related_articles(article, limit=limit)]


@router.get("/{article_id}/comments", response=list[CommentOut])
def list_comments(request, article_id: int):
    user = _get_optional_user(request)
    article = get_object_or_404(Article, id=article_id, status=ArticleStatus.PUBLISHED)
    comments = (
        article.comments.select_related("author")
        .filter(parent__isnull=True)
        .order_by("-is_pinned", "created_at")
    )
    return [_comment_out(comment, user) for comment in comments]


@router.post("", response={201: ArticleDetailOut}, auth=AuthBearer())
def create_article(request, data: ArticleCreateInput):
    try:
        article = ArticleService.create(request.auth, data.dict())
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return 201, _article_detail_out(article, request.auth)


@router.patch("/{article_id}", response=ArticleDetailOut, auth=AuthBearer())
def update_article(request, article_id: int, data: ArticleUpdateInput):
    article = get_object_or_404(Article, id=article_id, author=request.auth)
    try:
        article = ArticleService.update(article, data.dict())
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return _article_detail_out(article, request.auth)


@router.post("/{article_id}/publish", response=ArticleDetailOut, auth=AuthBearer())
def publish_article(request, article_id: int):
    article = get_object_or_404(Article, id=article_id, author=request.auth)
    try:
        article = ArticleService.publish(article)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return _article_detail_out(article, request.auth)


@router.delete("/{article_id}", response=MessageOut, auth=AuthBearer())
def delete_article(request, article_id: int):
    article = get_object_or_404(Article, id=article_id, author=request.auth)
    ArticleService.archive(article)
    return {"message": "文章已归档"}


@router.post("/{article_id}/vote", response=VoteOut, auth=AuthBearer())
def vote_article(request, article_id: int, data: VoteInput):
    article = get_object_or_404(Article, id=article_id, status=ArticleStatus.PUBLISHED)
    try:
        net_votes, my_vote = ArticleService.vote(article, request.auth, data.value)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return {"net_votes": float(net_votes), "my_vote": my_vote}


@router.delete("/{article_id}/vote", response=VoteOut, auth=AuthBearer())
def remove_vote(request, article_id: int):
    article = get_object_or_404(Article, id=article_id, status=ArticleStatus.PUBLISHED)
    try:
        net_votes = ArticleService.remove_vote(article, request.auth)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return {"net_votes": float(net_votes), "my_vote": None}


@router.post("/{article_id}/comments", response={201: CommentReplyOut | CommentOut}, auth=AuthBearer())
def add_comment(request, article_id: int, data: CommentCreateInput):
    article = get_object_or_404(Article, id=article_id, status=ArticleStatus.PUBLISHED)
    try:
        comment = ArticleService.add_comment(article, request.auth, data.content, data.parent_id)
    except ValueError as exc:
        raise HttpError(400, str(exc))

    comment = Comment.objects.select_related("author").get(id=comment.id)
    if comment.parent_id:
        return 201, _comment_reply_out(comment)
    return 201, _comment_out(comment, request.auth)


@router.post("/{article_id}/pin-comment", response=CommentOut, auth=AuthBearer())
def pin_comment(request, article_id: int, data: PinCommentInput):
    article = get_object_or_404(Article, id=article_id)
    try:
        comment = ArticleService.pin_comment(article, request.auth, data.comment_id)
    except ValueError as exc:
        raise HttpError(400, str(exc))

    comment = Comment.objects.select_related("author").get(id=comment.id)
    return _comment_out(comment, request.auth)


@router.post("/comments/{comment_id}/vote", response=CommentVoteOut, auth=AuthBearer())
def vote_comment(request, comment_id: int, data: CommentVoteInput):
    comment = get_object_or_404(Comment, id=comment_id)
    try:
        net_votes, my_vote = ArticleService.vote_comment(comment, request.auth, data.value)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return {
        "net_votes": net_votes,
        "my_vote": my_vote,
        "is_collapsed": ArticleService.should_collapse_comment(comment),
    }


@router.delete("/comments/{comment_id}/vote", response=CommentVoteOut, auth=AuthBearer())
def remove_comment_vote(request, comment_id: int):
    comment = get_object_or_404(Comment, id=comment_id)
    try:
        net_votes = ArticleService.remove_comment_vote(comment, request.auth)
    except ValueError as exc:
        raise HttpError(400, str(exc))
    return {
        "net_votes": net_votes,
        "my_vote": None,
        "is_collapsed": ArticleService.should_collapse_comment(comment),
    }
