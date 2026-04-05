"""Search service with Meilisearch-first and database fallback behavior."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from django.conf import settings
from django.db.models import Count, Q, QuerySet

from apps.skills.models import Skill, SkillStatus
from apps.workshop.models import Article, ArticleStatus

try:
    import meilisearch
except ImportError:  # pragma: no cover - optional at import time
    meilisearch = None


class SearchService:
    SKILL_INDEX = "skills"
    ARTICLE_INDEX = "articles"
    EXPERIMENT_A = "A"
    EXPERIMENT_B = "B"

    @classmethod
    def _skill_queryset(cls) -> QuerySet[Skill]:
        return Skill.objects.select_related("creator").filter(status=SkillStatus.APPROVED)

    @classmethod
    def _article_queryset(cls) -> QuerySet[Article]:
        return Article.objects.select_related("author", "related_skill", "related_skill__creator").filter(
            status=ArticleStatus.PUBLISHED
        )

    @classmethod
    def _skill_to_document(cls, skill: Skill) -> dict[str, Any]:
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "category": skill.category,
            "tags": skill.tags,
            "creator_name": skill.creator.display_name or skill.creator.username,
            "total_calls": skill.total_calls,
            "avg_rating": float(skill.avg_rating),
            "review_count": skill.review_count,
            "created_at": skill.created_at.isoformat(),
        }

    @classmethod
    def _article_to_document(cls, article: Article) -> dict[str, Any]:
        return {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "difficulty": article.difficulty,
            "article_type": article.article_type,
            "model_tags": article.model_tags,
            "custom_tags": article.custom_tags,
            "author_name": article.author.display_name or article.author.username,
            "is_featured": article.is_featured,
            "net_votes": float(article.net_votes),
            "total_tips": float(article.total_tips),
            "view_count": article.view_count,
            "published_at": article.published_at.isoformat() if article.published_at else None,
        }

    @classmethod
    def _get_client(cls):
        if meilisearch is None:
            return None

        try:
            return meilisearch.Client(settings.MEILISEARCH_URL, settings.MEILISEARCH_KEY)
        except Exception:
            return None

    @staticmethod
    def assign_experiment_bucket(seed: str) -> str:
        if not seed:
            return SearchService.EXPERIMENT_A
        digest = sha256(seed.encode("utf-8")).hexdigest()
        return SearchService.EXPERIMENT_A if int(digest[:2], 16) % 2 == 0 else SearchService.EXPERIMENT_B

    @classmethod
    def optimize_index_settings(cls) -> dict[str, bool]:
        client = cls._get_client()
        if not client:
            return {"skills": False, "articles": False}

        result = {"skills": False, "articles": False}
        try:
            skills_index = client.index(cls.SKILL_INDEX)
            skills_index.update_searchable_attributes(["name", "description", "tags", "creator_name"])
            skills_index.update_filterable_attributes(["category"])
            skills_index.update_sortable_attributes(["total_calls", "avg_rating", "created_at"])
            skills_index.update_ranking_rules(
                ["words", "typo", "proximity", "attribute", "sort", "exactness"]
            )
            result["skills"] = True
        except Exception:
            pass

        try:
            articles_index = client.index(cls.ARTICLE_INDEX)
            articles_index.update_searchable_attributes(
                ["title", "content", "custom_tags", "model_tags", "author_name"]
            )
            articles_index.update_filterable_attributes(["difficulty", "article_type", "model_tags"])
            articles_index.update_sortable_attributes(["net_votes", "view_count", "published_at"])
            articles_index.update_ranking_rules(
                ["words", "typo", "proximity", "attribute", "sort", "exactness"]
            )
            result["articles"] = True
        except Exception:
            pass
        return result

    @staticmethod
    def _skill_score(skill: Skill, *, q: str | None, bucket: str) -> tuple[int, int, float, int]:
        query = (q or "").strip().lower()
        relevance = 0
        if query:
            if query in skill.name.lower():
                relevance += 6
            if query in skill.description.lower():
                relevance += 3
            relevance += sum(2 for tag in skill.tags if query in tag.lower())
        feature_bonus = 4 if skill.is_featured else 0
        popularity = skill.total_calls
        quality = float(skill.avg_rating)
        if bucket == SearchService.EXPERIMENT_B:
            return (relevance + feature_bonus, int(quality * 100), quality, popularity)
        return (relevance + feature_bonus, popularity, quality, skill.review_count)

    @staticmethod
    def _article_score(article: Article, *, q: str | None, bucket: str) -> tuple[int, float, int, int]:
        query = (q or "").strip().lower()
        relevance = 0
        if query:
            if query in article.title.lower():
                relevance += 8
            if query in article.content.lower():
                relevance += 3
            relevance += sum(2 for tag in article.custom_tags if query in tag.lower())
            relevance += sum(2 for tag in article.model_tags if query in tag.lower())
        feature_bonus = 4 if article.is_featured else 0
        net_votes = float(article.net_votes)
        view_count = article.view_count
        if bucket == SearchService.EXPERIMENT_B:
            return (relevance + feature_bonus, view_count, net_votes, article.comment_count if hasattr(article, "comment_count") else 0)
        return (relevance + feature_bonus, net_votes, view_count, article.comment_count if hasattr(article, "comment_count") else 0)

    @classmethod
    def sync_skill(cls, skill: Skill) -> bool:
        client = cls._get_client()
        if not client:
            return False

        try:
            index = client.index(cls.SKILL_INDEX)
            index.add_documents([cls._skill_to_document(skill)], primary_key="id")
            return True
        except Exception:
            return False

    @classmethod
    def sync_all_skills(cls) -> bool:
        client = cls._get_client()
        if not client:
            return False

        try:
            index = client.index(cls.SKILL_INDEX)
            documents = [cls._skill_to_document(skill) for skill in cls._skill_queryset()]
            if documents:
                index.add_documents(documents, primary_key="id")
            return True
        except Exception:
            return False

    @classmethod
    def sync_article(cls, article: Article) -> bool:
        client = cls._get_client()
        if not client:
            return False

        try:
            index = client.index(cls.ARTICLE_INDEX)
            index.add_documents([cls._article_to_document(article)], primary_key="id")
            return True
        except Exception:
            return False

    @classmethod
    def sync_all_articles(cls) -> bool:
        client = cls._get_client()
        if not client:
            return False

        try:
            index = client.index(cls.ARTICLE_INDEX)
            documents = [cls._article_to_document(article) for article in cls._article_queryset()]
            if documents:
                index.add_documents(documents, primary_key="id")
            return True
        except Exception:
            return False

    @classmethod
    def remove_article(cls, article_id: int) -> bool:
        client = cls._get_client()
        if not client:
            return False

        try:
            index = client.index(cls.ARTICLE_INDEX)
            index.delete_document(article_id)
            return True
        except Exception:
            return False

    @classmethod
    def _search_skills_db(
        cls,
        q: str | None = None,
        category: str | None = None,
        limit: int = 20,
        experiment_bucket: str = EXPERIMENT_A,
    ) -> list[Skill]:
        queryset = cls._skill_queryset()
        if category:
            queryset = queryset.filter(category=category)
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(tags__overlap=[q])
            )
        skills = list(queryset[:200])
        skills.sort(key=lambda skill: cls._skill_score(skill, q=q, bucket=experiment_bucket), reverse=True)
        return skills[:limit]

    @classmethod
    def search_skills(
        cls,
        q: str | None = None,
        category: str | None = None,
        limit: int = 20,
        experiment_bucket: str | None = None,
    ) -> dict[str, Any]:
        bucket = experiment_bucket or cls.assign_experiment_bucket(f"skills:{q}:{category}")
        client = cls._get_client()
        if client:
            try:
                cls.optimize_index_settings()
                index = client.index(cls.SKILL_INDEX)
                filter_expr = f'category = "{category}"' if category else None
                result = index.search(
                    q or "",
                    {
                        "limit": limit,
                        "filter": filter_expr,
                        "sort": ["avg_rating:desc"] if bucket == cls.EXPERIMENT_B else ["total_calls:desc"],
                    },
                )
                ids = [item["id"] for item in result.get("hits", [])]
                if ids:
                    skills_by_id = {
                        skill.id: skill
                        for skill in cls._skill_queryset().filter(id__in=ids)
                    }
                    ordered = [skills_by_id[skill_id] for skill_id in ids if skill_id in skills_by_id]
                else:
                    ordered = []
                return {
                    "items": ordered,
                    "source": "meilisearch",
                    "total": result.get("estimatedTotalHits", len(ordered)),
                    "experiment_bucket": bucket,
                }
            except Exception:
                pass

        fallback = cls._search_skills_db(q=q, category=category, limit=limit, experiment_bucket=bucket)
        return {
            "items": fallback,
            "source": "database",
            "total": len(fallback),
            "experiment_bucket": bucket,
        }

    @classmethod
    def _search_articles_db(
        cls,
        q: str | None = None,
        difficulty: str | None = None,
        article_type: str | None = None,
        model_tag: str | None = None,
        limit: int = 20,
        experiment_bucket: str = EXPERIMENT_A,
    ) -> list[Article]:
        queryset = cls._article_queryset()
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
        queryset = queryset.annotate(comment_count=Count("comments"))
        articles = list(queryset[:200])
        articles.sort(key=lambda article: cls._article_score(article, q=q, bucket=experiment_bucket), reverse=True)
        return articles[:limit]

    @classmethod
    def search_articles(
        cls,
        q: str | None = None,
        difficulty: str | None = None,
        article_type: str | None = None,
        model_tag: str | None = None,
        limit: int = 20,
        experiment_bucket: str | None = None,
    ) -> dict[str, Any]:
        bucket = experiment_bucket or cls.assign_experiment_bucket(
            f"articles:{q}:{difficulty}:{article_type}:{model_tag}"
        )
        client = cls._get_client()
        if client:
            try:
                cls.optimize_index_settings()
                index = client.index(cls.ARTICLE_INDEX)
                filters = []
                if difficulty:
                    filters.append(f'difficulty = "{difficulty}"')
                if article_type:
                    filters.append(f'article_type = "{article_type}"')
                if model_tag:
                    filters.append(f'model_tags = "{model_tag}"')

                result = index.search(
                    q or "",
                    {
                        "limit": limit,
                        "filter": filters or None,
                        "sort": ["view_count:desc", "published_at:desc"] if bucket == cls.EXPERIMENT_B else ["net_votes:desc", "published_at:desc"],
                    },
                )
                ids = [item["id"] for item in result.get("hits", [])]
                if ids:
                    articles_by_id = {
                        article.id: article
                        for article in cls._article_queryset().filter(id__in=ids)
                    }
                    ordered = [articles_by_id[article_id] for article_id in ids if article_id in articles_by_id]
                else:
                    ordered = []
                return {
                    "items": ordered,
                    "source": "meilisearch",
                    "total": result.get("estimatedTotalHits", len(ordered)),
                    "experiment_bucket": bucket,
                }
            except Exception:
                pass

        fallback = cls._search_articles_db(
            q=q,
            difficulty=difficulty,
            article_type=article_type,
            model_tag=model_tag,
            limit=limit,
            experiment_bucket=bucket,
        )
        return {
            "items": fallback,
            "source": "database",
            "total": len(fallback),
            "experiment_bucket": bucket,
        }
