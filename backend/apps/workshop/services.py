"""Workshop business logic."""
from __future__ import annotations

from datetime import timedelta
import re
from collections import Counter, defaultdict
from decimal import Decimal

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, Count, DecimalField, F, Sum, Value, When
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify

from apps.credits.models import CreditAction
from apps.credits.services import CreditService
from apps.notifications.models import Notification
from apps.payments.services import PaymentsService
from apps.search.services import SearchService
from apps.skills.models import Skill, SkillCall, SkillStatus
from apps.workshop.models import (
    Article,
    ArticleDifficulty,
    ArticleStatus,
    ArticleType,
    Comment,
    CommentVote,
    Series,
    Vote,
)
from apps.workshop.rules import get_article_vote_weight, should_collapse_comment


class ArticleService:
    """Service layer for phase 1 Workshop."""

    VOTE_WEIGHT_MAP = {
        "SEED": Decimal("1.0"),
        "CRAFTSMAN": Decimal("1.5"),
        "EXPERT": Decimal("2.0"),
        "MASTER": Decimal("3.0"),
        "GRANDMASTER": Decimal("5.0"),
    }
    READ_HISTORY_CACHE_KEY = "workshop:read-history:user:{user_id}"
    ARTICLE_RECOMMENDATION_CACHE_KEY = "workshop:recommended:user:{user_id}"
    CURRENT_MODEL_TAGS = {
        "gpt-5",
        "claude code",
        "claude sonnet 4",
        "claude opus 4",
        "gemini 2.5",
        "通用",
    }
    LEGACY_MODEL_PATTERNS = (
        "gpt-4",
        "gpt-3.5",
        "claude 2",
        "claude 3",
        "sonnet 3",
        "opus 3",
        "gemini 1.5",
    )

    @staticmethod
    def _clean_tags(tags: list[str] | None, limit: int) -> list[str]:
        if not tags:
            return []

        seen: set[str] = set()
        cleaned: list[str] = []
        for tag in tags:
            normalized = (tag or "").strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(normalized[:50])
            if len(cleaned) >= limit:
                break
        return cleaned

    @staticmethod
    def _sanitize_content(content: str) -> str:
        sanitized = re.sub(
            r"<\s*(script|style|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>",
            "",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        sanitized = re.sub(r"\son[a-zA-Z]+\s*=\s*(['\"]).*?\1", "", sanitized)
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()

    @classmethod
    def _validate_related_skill(cls, author, related_skill_id: int | None) -> Skill | None:
        if not related_skill_id:
            return None

        try:
            skill = Skill.objects.select_related("creator").get(id=related_skill_id)
        except Skill.DoesNotExist as exc:
            raise ValueError("关联 Skill 不存在") from exc

        if skill.status != SkillStatus.APPROVED and skill.creator_id != author.id:
            raise ValueError("只能关联已上架或自己创建的 Skill")
        return skill

    @classmethod
    def _validate(
        cls,
        author,
        data: dict,
        existing: Article | None = None,
        publishing: bool = False,
    ) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}

        title = (payload.get("title", existing.title if existing else "") or "").strip()
        content = payload.get("content", existing.content if existing else "") or ""
        difficulty = (
            payload.get("difficulty", existing.difficulty if existing else ArticleDifficulty.BEGINNER)
            or ArticleDifficulty.BEGINNER
        ).strip()
        article_type = (
            payload.get("article_type", existing.article_type if existing else ArticleType.TUTORIAL)
            or ArticleType.TUTORIAL
        ).strip()
        model_tags = cls._clean_tags(
            payload.get("model_tags", existing.model_tags if existing else []),
            limit=5,
        )
        custom_tags = cls._clean_tags(
            payload.get("custom_tags", existing.custom_tags if existing else []),
            limit=5,
        )
        related_skill = cls._validate_related_skill(
            author,
            payload.get("related_skill_id", existing.related_skill_id if existing else None),
        )
        series_id = payload.get("series_id", existing.series_id if existing else None)
        series_order = payload.get("series_order", existing.series_order if existing else None)

        if not title or len(title) < 5 or len(title) > 120:
            raise ValueError("文章标题长度需在 5 到 120 个字符之间")
        if difficulty not in set(ArticleDifficulty.values):
            raise ValueError("文章难度无效")
        if article_type not in set(ArticleType.values):
            raise ValueError("文章类型无效")
        if len(custom_tags) > 5:
            raise ValueError("自定义标签最多 5 个")

        sanitized_content = cls._sanitize_content(content)
        plain_text = re.sub(r"\s+", " ", strip_tags(sanitized_content)).strip()

        if publishing:
            if len(plain_text) < 500:
                raise ValueError("发布文章前请补充到至少 500 个字符")
            required_sections = ("问题", "方案", "效果")
            if any(section not in plain_text for section in required_sections):
                raise ValueError("文章需包含“问题 / 方案 / 效果”三个核心部分")
            if not model_tags:
                raise ValueError("发布文章前至少选择 1 个模型标签")

        return {
            "title": title,
            "content": sanitized_content,
            "difficulty": difficulty,
            "article_type": article_type,
            "model_tags": model_tags,
            "custom_tags": custom_tags,
            "related_skill": related_skill,
            "series_id": series_id,
            "series_order": series_order,
        }

    @staticmethod
    def _create_unique_slug(title: str, author_id: int) -> str:
        base_slug = slugify(title, allow_unicode=True) or f"article-{author_id}"
        slug = base_slug
        suffix = 1
        while Article.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    @classmethod
    @transaction.atomic
    def create(cls, author, data: dict) -> Article:
        payload = cls._validate(author, data)
        article = Article.objects.create(
            author=author,
            slug=cls._create_unique_slug(payload["title"], author.id),
            **payload,
        )
        if article.series_id:
            SeriesService.refresh_completion_state(article.series)
        return article

    @classmethod
    @transaction.atomic
    def update(cls, article: Article, data: dict) -> Article:
        payload = cls._validate(article.author, data, existing=article)
        title_changed = payload["title"] != article.title
        previous_series_id = article.series_id

        for field, value in payload.items():
            setattr(article, field, value)

        if title_changed:
            article.slug = cls._create_unique_slug(payload["title"], article.author_id)

        article.save()
        if previous_series_id and previous_series_id != article.series_id:
            previous_series = Series.objects.filter(id=previous_series_id).first()
            if previous_series:
                SeriesService.refresh_completion_state(previous_series)
        if article.series_id:
            SeriesService.refresh_completion_state(article.series)
        if article.status == ArticleStatus.PUBLISHED:
            SearchService.sync_article(article)
        return article

    @classmethod
    @transaction.atomic
    def publish(cls, article: Article) -> Article:
        if article.status == ArticleStatus.PUBLISHED:
            raise ValueError("文章已经发布")
        if article.status == ArticleStatus.ARCHIVED:
            raise ValueError("归档文章不能直接发布")

        payload = cls._validate(article.author, {}, existing=article, publishing=True)
        for field, value in payload.items():
            setattr(article, field, value)

        first_publish = article.published_at is None
        article.status = ArticleStatus.PUBLISHED
        article.published_at = timezone.now()
        article.save()

        if first_publish:
            CreditService.add_credit(article.author, CreditAction.PUBLISH_ARTICLE, str(article.id))
        if article.series_id:
            SeriesService.refresh_completion_state(article.series)
            SeriesService.ensure_completion_reward(article.series)
        SearchService.sync_article(article)
        return article

    @staticmethod
    @transaction.atomic
    def archive(article: Article) -> Article:
        article.status = ArticleStatus.ARCHIVED
        article.save(update_fields=["status"])
        if article.series_id:
            SeriesService.refresh_completion_state(article.series)
        SearchService.remove_article(article.id)
        return article

    @classmethod
    def record_read(cls, article: Article, user) -> None:
        if not user or not getattr(user, "id", None):
            return
        cache_key = cls.READ_HISTORY_CACHE_KEY.format(user_id=user.id)
        history: list[int] = cache.get(cache_key, [])
        updated = [article.id] + [item for item in history if item != article.id]
        cache.set(cache_key, updated[:50], timeout=30 * 24 * 3600)

    @classmethod
    def _article_reason(cls, article: Article, model_tags: Counter, custom_tags: Counter) -> str:
        matching_models = [tag for tag in article.model_tags if model_tags.get(tag.lower(), 0) > 0]
        if matching_models:
            return f"延续你最近关注的模型主题：{', '.join(matching_models[:2])}"
        matching_tags = [tag for tag in article.custom_tags if custom_tags.get(tag.lower(), 0) > 0]
        if matching_tags:
            return f"匹配你的阅读标签：{', '.join(matching_tags[:2])}"
        if article.related_skill_id:
            return "和你关注的 Skill 主题相关"
        return "基于热度、标签与阅读轨迹推荐"

    @classmethod
    def compute_recommended_articles(cls, user, *, limit: int = 8) -> list[dict]:
        safe_limit = min(max(limit, 1), 24)
        history_ids: list[int] = cache.get(cls.READ_HISTORY_CACHE_KEY.format(user_id=user.id), [])
        history_articles = list(
            Article.objects.select_related("author", "related_skill", "related_skill__creator")
            .filter(id__in=history_ids, status=ArticleStatus.PUBLISHED)
        )
        if not history_articles:
            history_articles = list(
                Article.objects.select_related("author", "related_skill", "related_skill__creator")
                .filter(status=ArticleStatus.PUBLISHED, votes__voter=user)
                .distinct()
                .order_by("-published_at")[:20]
            )

        seen_ids = {article.id for article in history_articles}
        model_counter: Counter[str] = Counter()
        custom_counter: Counter[str] = Counter()
        type_counter: Counter[str] = Counter()
        related_skill_ids: set[int] = set()

        for article in history_articles:
            type_counter[article.article_type] += 1
            related_skill_ids.update([article.related_skill_id] if article.related_skill_id else [])
            for tag in article.model_tags:
                model_counter[tag.lower()] += 1
            for tag in article.custom_tags:
                custom_counter[tag.lower()] += 1

        queryset = (
            Article.objects.select_related("author", "related_skill", "related_skill__creator")
            .filter(status=ArticleStatus.PUBLISHED)
        )
        if seen_ids:
            queryset = queryset.exclude(id__in=seen_ids)

        scored: list[tuple[Decimal, Article]] = []
        for article in queryset[:200]:
            score = Decimal("0")
            score += Decimal(sum(model_counter.get(tag.lower(), 0) for tag in article.model_tags)) * Decimal("2.5")
            score += Decimal(sum(custom_counter.get(tag.lower(), 0) for tag in article.custom_tags))
            score += Decimal(type_counter.get(article.article_type, 0)) * Decimal("1.5")
            if article.related_skill_id and article.related_skill_id in related_skill_ids:
                score += Decimal("3")
            score += Decimal("3") if article.is_featured else Decimal("0")
            score += Decimal(str(article.net_votes)) * Decimal("0.3")
            score += Decimal(min(article.view_count, 500)) / Decimal("80")
            scored.append((score, article))

        scored.sort(key=lambda item: (item[0], item[1].is_featured, item[1].view_count, item[1].id), reverse=True)
        return [
            {
                "article": article,
                "score": float(score),
                "reason": cls._article_reason(article, model_counter, custom_counter),
            }
            for score, article in scored[:safe_limit]
        ]

    @classmethod
    def list_recommended_articles(cls, user, *, limit: int = 8) -> list[dict]:
        safe_limit = min(max(limit, 1), 24)
        cache_key = cls.ARTICLE_RECOMMENDATION_CACHE_KEY.format(user_id=user.id)
        cached_ids: list[int] | None = cache.get(cache_key)
        if cached_ids:
            articles_by_id = {
                article.id: article
                for article in Article.objects.select_related("author", "related_skill", "related_skill__creator").filter(
                    id__in=cached_ids,
                    status=ArticleStatus.PUBLISHED,
                )
            }
            ordered = [articles_by_id[article_id] for article_id in cached_ids if article_id in articles_by_id][:safe_limit]
            if ordered:
                return [
                    {
                        "article": article,
                        "score": float(article.net_votes),
                        "reason": "基于你的阅读轨迹离线生成",
                    }
                    for article in ordered
                ]
        recommendations = cls.compute_recommended_articles(user, limit=safe_limit)
        cache.set(cache_key, [item["article"].id for item in recommendations], timeout=6 * 3600)
        return recommendations

    @classmethod
    def list_related_articles(cls, article: Article, *, limit: int = 4) -> list[dict]:
        safe_limit = min(max(limit, 1), 12)
        queryset = (
            Article.objects.select_related("author", "related_skill", "related_skill__creator")
            .filter(status=ArticleStatus.PUBLISHED)
            .exclude(id=article.id)
        )
        scored: list[tuple[Decimal, Article]] = []
        for candidate in queryset[:200]:
            score = Decimal("0")
            shared_model_tags = len(set(tag.lower() for tag in candidate.model_tags) & set(tag.lower() for tag in article.model_tags))
            shared_custom_tags = len(set(tag.lower() for tag in candidate.custom_tags) & set(tag.lower() for tag in article.custom_tags))
            score += Decimal(shared_model_tags) * Decimal("3")
            score += Decimal(shared_custom_tags) * Decimal("1.5")
            if article.related_skill_id and candidate.related_skill_id == article.related_skill_id:
                score += Decimal("4")
            if candidate.article_type == article.article_type:
                score += Decimal("1.5")
            score += Decimal("2") if candidate.is_featured else Decimal("0")
            score += Decimal(str(candidate.net_votes)) * Decimal("0.2")
            if score > 0:
                scored.append((score, candidate))
        scored.sort(key=lambda item: (item[0], item[1].is_featured, item[1].id), reverse=True)
        return [
            {
                "article": candidate,
                "score": float(score),
                "reason": cls._article_reason(candidate, Counter({tag.lower(): 1 for tag in article.model_tags}), Counter()),
            }
            for score, candidate in scored[:safe_limit]
        ]

    @classmethod
    def refresh_recommendation_cache(cls, limit: int = 8) -> dict[str, int]:
        active_user_ids = set()
        for key_prefix in ("votes", "comments"):
            if key_prefix == "votes":
                active_user_ids.update(Vote.objects.values_list("voter_id", flat=True).distinct()[:100])
            else:
                active_user_ids.update(Comment.objects.values_list("author_id", flat=True).distinct()[:100])
        refreshed = 0
        user_model = Article.author.field.related_model
        for user_id in active_user_ids:
            user = user_model.objects.filter(id=user_id).first()
            if not user:
                continue
            recommendations = cls.compute_recommended_articles(user, limit=limit)
            cache.set(
                cls.ARTICLE_RECOMMENDATION_CACHE_KEY.format(user_id=user_id),
                [item["article"].id for item in recommendations],
                timeout=6 * 3600,
            )
            refreshed += 1
        return {"users": refreshed}

    @classmethod
    def detect_outdated_articles(cls) -> dict[str, int]:
        now = timezone.now()
        checked = 0
        updated = 0
        articles = Article.objects.filter(status=ArticleStatus.PUBLISHED)
        for article in articles:
            checked += 1
            published_at = article.published_at or article.created_at
            normalized_tags = [tag.lower() for tag in article.model_tags]
            has_legacy_model = any(
                legacy_pattern in tag for tag in normalized_tags for legacy_pattern in cls.LEGACY_MODEL_PATTERNS
            )
            stale_unknown_model = bool(normalized_tags) and published_at <= now - timedelta(days=180) and not any(
                tag in cls.CURRENT_MODEL_TAGS for tag in normalized_tags
            )
            should_mark = has_legacy_model or stale_unknown_model
            if article.is_outdated != should_mark:
                article.is_outdated = should_mark
                article.save(update_fields=["is_outdated"])
                updated += 1
        return {"checked": checked, "updated": updated}

    @classmethod
    def auto_archive_stale_articles(cls) -> dict[str, int]:
        threshold = timezone.now() - timedelta(days=180)
        queryset = Article.objects.filter(
            status=ArticleStatus.PUBLISHED,
            updated_at__lt=threshold,
            net_votes__lt=5,
        )
        archived = 0
        for article in queryset:
            cls.archive(article)
            archived += 1
        return {"archived": archived}

    @classmethod
    def cleanup_old_data(cls) -> dict[str, int]:
        now = timezone.now()
        aggregated_calls = defaultdict(int)
        for skill_id, created_at in (
            SkillCall.objects.filter(created_at__lt=now - timedelta(days=30))
            .values_list("skill_id", "created_at")
            .iterator()
        ):
            aggregated_calls[f"{skill_id}:{created_at.strftime('%Y-%m-%d')}"] += 1
        cache.set("skills:call-daily-aggregate", dict(aggregated_calls), timeout=24 * 3600)

        deleted_notifications = Notification.objects.filter(
            is_read=True,
            created_at__lt=now - timedelta(days=90),
        ).delete()[0]
        deleted_sessions = Session.objects.filter(expire_date__lt=now).delete()[0]
        return {
            "aggregated_skill_call_days": len(aggregated_calls),
            "deleted_notifications": deleted_notifications,
            "deleted_sessions": deleted_sessions,
        }

    @classmethod
    def _recalculate_votes(cls, article: Article) -> Decimal:
        aggregates = article.votes.aggregate(
            up=Sum(
                Case(
                    When(is_upvote=True, then=F("weight")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            ),
            down=Sum(
                Case(
                    When(is_upvote=False, then=F("weight")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            ),
        )
        net_votes = (aggregates["up"] or Decimal("0")) - (aggregates["down"] or Decimal("0"))
        article.net_votes = net_votes.quantize(Decimal("0.01"))
        article.save(update_fields=["net_votes"])
        if article.status == ArticleStatus.PUBLISHED:
            SearchService.sync_article(article)
        return article.net_votes

    @classmethod
    @transaction.atomic
    def vote(cls, article: Article, voter, value: str) -> tuple[Decimal, str]:
        if article.status != ArticleStatus.PUBLISHED:
            raise ValueError("只能给已发布文章投票")
        if value not in {"UP", "DOWN"}:
            raise ValueError("投票值无效")

        vote, _created = Vote.objects.update_or_create(
            article=article,
            voter=voter,
            defaults={
                "is_upvote": value == "UP",
                "weight": get_article_vote_weight(voter.level),
            },
        )
        net_votes = cls._recalculate_votes(article)
        return net_votes, "UP" if vote.is_upvote else "DOWN"

    @classmethod
    @transaction.atomic
    def remove_vote(cls, article: Article, voter) -> Decimal:
        deleted, _details = Vote.objects.filter(article=article, voter=voter).delete()
        if not deleted:
            raise ValueError("当前没有可取消的投票")
        return cls._recalculate_votes(article)

    @staticmethod
    @transaction.atomic
    def add_comment(article: Article, author, content: str, parent_id: int | None = None) -> Comment:
        if article.status != ArticleStatus.PUBLISHED:
            raise ValueError("只能评论已发布文章")

        normalized = content.strip()
        if not normalized or len(normalized) > 500:
            raise ValueError("评论长度需在 1 到 500 个字符之间")

        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, article=article)
            except Comment.DoesNotExist as exc:
                raise ValueError("回复目标不存在") from exc
            if parent.parent_id:
                raise ValueError("当前仅支持一层回复")

        return Comment.objects.create(
            article=article,
            author=author,
            parent=parent,
            content=normalized,
        )

    @staticmethod
    @transaction.atomic
    def pin_comment(article: Article, actor, comment_id: int) -> Comment:
        if article.author_id != actor.id:
            raise ValueError("只有文章作者可以置顶评论")

        try:
            comment = Comment.objects.get(id=comment_id, article=article)
        except Comment.DoesNotExist as exc:
            raise ValueError("评论不存在") from exc

        article.comments.filter(is_pinned=True).update(is_pinned=False)
        comment.is_pinned = True
        comment.save(update_fields=["is_pinned"])
        return comment

    @staticmethod
    def _recalculate_comment_votes(comment: Comment) -> int:
        net_votes = comment.votes.aggregate(total=Sum("value"))["total"] or 0
        comment.net_votes = net_votes
        comment.save(update_fields=["net_votes"])
        return net_votes

    @classmethod
    @transaction.atomic
    def vote_comment(cls, comment: Comment, voter, value: str) -> tuple[int, str]:
        if value not in {"UP", "DOWN"}:
            raise ValueError("评论投票值无效")

        vote_value = 1 if value == "UP" else -1
        comment_vote, _created = CommentVote.objects.update_or_create(
            comment=comment,
            voter=voter,
            defaults={"value": vote_value},
        )
        net_votes = cls._recalculate_comment_votes(comment)
        return net_votes, "UP" if comment_vote.value > 0 else "DOWN"

    @classmethod
    @transaction.atomic
    def remove_comment_vote(cls, comment: Comment, voter) -> int:
        deleted, _details = CommentVote.objects.filter(comment=comment, voter=voter).delete()
        if not deleted:
            raise ValueError("当前没有可取消的评论投票")
        return cls._recalculate_comment_votes(comment)

    @staticmethod
    def should_collapse_comment(comment: Comment) -> bool:
        return should_collapse_comment(comment.net_votes)


class SeriesService:
    """Series CRUD, ordering and completion reward helpers."""

    @staticmethod
    def _validate(author, data: dict, *, existing: Series | None = None) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}
        title = (payload.get("title", existing.title if existing else "") or "").strip()
        description = (payload.get("description", existing.description if existing else "") or "").strip()
        cover_url = (payload.get("cover_url", existing.cover_url if existing else "") or "").strip()

        if not title or len(title) < 3 or len(title) > 200:
            raise ValueError("系列标题长度需在 3 到 200 个字符之间")
        if len(description) > 2000:
            raise ValueError("系列描述不能超过 2000 个字符")

        return {
            "author": author,
            "title": title,
            "description": description,
            "cover_url": cover_url,
        }

    @classmethod
    @transaction.atomic
    def create(cls, author, data: dict) -> Series:
        payload = cls._validate(author, data)
        return Series.objects.create(**payload)

    @classmethod
    @transaction.atomic
    def update(cls, series: Series, data: dict) -> Series:
        payload = cls._validate(series.author, data, existing=series)
        for field, value in payload.items():
            if field == "author":
                continue
            setattr(series, field, value)
        series.save()
        return series

    @staticmethod
    def refresh_completion_state(series: Series) -> Series:
        published_count = series.articles.filter(status=ArticleStatus.PUBLISHED).count()
        is_completed = published_count >= 3
        if series.is_completed != is_completed:
            series.is_completed = is_completed
            series.save(update_fields=["is_completed"])
        return series

    @classmethod
    @transaction.atomic
    def reorder_articles(cls, series: Series, article_ids: list[int]) -> Series:
        series_articles = {
            article.id: article
            for article in series.articles.all()
        }
        if set(article_ids) != set(series_articles):
            raise ValueError("排序列表必须完整包含该系列的全部文章")

        for index, article_id in enumerate(article_ids, start=1):
            article = series_articles[article_id]
            if article.series_order != index:
                article.series_order = index
                article.save(update_fields=["series_order"])
        return cls.refresh_completion_state(series)

    @classmethod
    @transaction.atomic
    def ensure_completion_reward(cls, series: Series) -> bool:
        series.refresh_from_db()
        cls.refresh_completion_state(series)
        if not series.is_completed or series.completion_rewarded:
            return False

        PaymentsService.create_deposit(
            series.author,
            Decimal("1.00"),
            reference_id=f"series:{series.id}:completion-reward",
        )
        CreditService.adjust_credit(
            series.author,
            30,
            reference_id=f"series:{series.id}:completion-reward",
        )
        series.completion_rewarded = True
        series.save(update_fields=["completion_rewarded"])
        return True

    @classmethod
    def refresh_completion_rewards(cls) -> dict[str, int]:
        rewarded = 0
        for series in Series.objects.prefetch_related("articles").all():
            if cls.ensure_completion_reward(series):
                rewarded += 1
        return {"rewarded": rewarded}
