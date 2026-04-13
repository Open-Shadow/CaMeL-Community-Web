"""Search API routes."""
from ninja import Router, Schema

from apps.search.services import SearchService

router = Router()


class SearchSkillOut(Schema):
    id: int
    name: str
    slug: str
    description: str
    category: str
    tags: list[str]
    pricing_model: str
    price: float | None = None
    status: str
    is_featured: bool
    current_version: str
    rejection_reason: str
    readme_html: str
    download_count: int
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str
    total_calls: int
    avg_rating: float
    review_count: int


class SearchResponse(Schema):
    items: list[SearchSkillOut]
    source: str
    total: int
    experiment_bucket: str


class SearchArticleAuthorOut(Schema):
    id: int
    username: str
    display_name: str
    level: str
    credit_score: int


class SearchArticleRelatedSkillOut(Schema):
    id: int
    name: str
    category: str
    pricing_model: str
    price: float | None = None
    total_calls: int
    avg_rating: float
    creator_name: str


class SearchArticleOut(Schema):
    id: int
    title: str
    slug: str
    excerpt: str
    difficulty: str
    article_type: str
    model_tags: list[str]
    custom_tags: list[str]
    status: str
    is_featured: bool
    net_votes: float
    total_tips: float
    comment_count: int
    view_count: int
    created_at: str
    updated_at: str
    published_at: str | None = None
    author: SearchArticleAuthorOut
    related_skill: SearchArticleRelatedSkillOut | None = None


class SearchArticleResponse(Schema):
    items: list[SearchArticleOut]
    source: str
    total: int
    experiment_bucket: str


@router.get("/skills", response=SearchResponse)
def search_skills(request, q: str | None = None, category: str | None = None, limit: int = 20, experiment_bucket: str | None = None):
    result = SearchService.search_skills(
        q=q,
        category=category,
        limit=min(max(limit, 1), 50),
        experiment_bucket=experiment_bucket,
    )
    return {
        "items": [
            {
                "id": skill.id,
                "name": skill.name,
                "slug": skill.slug,
                "description": skill.description,
                "category": skill.category,
                "tags": skill.tags,
                "pricing_model": skill.pricing_model,
                "price": float(skill.price) if skill.price else None,
                "status": skill.status,
                "is_featured": skill.is_featured,
                "current_version": skill.current_version,
                "rejection_reason": skill.rejection_reason,
                "readme_html": skill.readme_html,
                "download_count": skill.download_count,
                "creator_id": skill.creator_id,
                "creator_name": skill.creator.display_name or skill.creator.username,
                "created_at": skill.created_at.isoformat(),
                "updated_at": skill.updated_at.isoformat(),
                "total_calls": skill.total_calls,
                "avg_rating": float(skill.avg_rating),
                "review_count": skill.review_count,
            }
            for skill in result["items"]
        ],
        "source": result["source"],
        "total": result["total"],
        "experiment_bucket": result["experiment_bucket"],
    }


@router.get("/articles", response=SearchArticleResponse)
def search_articles(
    request,
    q: str | None = None,
    difficulty: str | None = None,
    article_type: str | None = None,
    model_tag: str | None = None,
    limit: int = 20,
    experiment_bucket: str | None = None,
):
    import re
    from django.utils.html import strip_tags

    result = SearchService.search_articles(
        q=q,
        difficulty=difficulty,
        article_type=article_type,
        model_tag=model_tag,
        limit=min(max(limit, 1), 50),
        experiment_bucket=experiment_bucket,
    )

    def excerpt(content: str) -> str:
        text = re.sub(r"\s+", " ", strip_tags(content)).strip()
        return text[:140] + ("..." if len(text) > 140 else "")

    return {
        "items": [
            {
                "id": article.id,
                "title": article.title,
                "slug": article.slug,
                "excerpt": excerpt(article.content),
                "difficulty": article.difficulty,
                "article_type": article.article_type,
                "model_tags": article.model_tags,
                "custom_tags": article.custom_tags,
                "status": article.status,
                "is_featured": article.is_featured,
                "net_votes": float(article.net_votes),
                "total_tips": float(article.total_tips),
                "comment_count": article.comments.count(),
                "view_count": article.view_count,
                "created_at": article.created_at.isoformat(),
                "updated_at": article.updated_at.isoformat(),
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "author": {
                    "id": article.author.id,
                    "username": article.author.username,
                    "display_name": article.author.display_name or article.author.username,
                    "level": article.author.level,
                    "credit_score": article.author.credit_score,
                },
                "related_skill": (
                    {
                        "id": article.related_skill.id,
                        "name": article.related_skill.name,
                        "category": article.related_skill.category,
                        "pricing_model": article.related_skill.pricing_model,
                        "price": (
                            float(article.related_skill.price)
                            if article.related_skill.price
                            else None
                        ),
                        "total_calls": article.related_skill.total_calls,
                        "avg_rating": float(article.related_skill.avg_rating),
                        "creator_name": (
                            article.related_skill.creator.display_name
                            or article.related_skill.creator.username
                        ),
                    }
                    if article.related_skill
                    else None
                ),
            }
            for article in result["items"]
        ],
        "source": result["source"],
        "total": result["total"],
        "experiment_bucket": result["experiment_bucket"],
    }
