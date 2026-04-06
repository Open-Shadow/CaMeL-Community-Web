"""
Comprehensive tests for Notification and Search services.

Covers:
  - NotificationService: send, send_bulk, mark_read, mark_all_read,
    list_for_user, total_for_user, unread_count
  - SearchService (database fallback): search_skills, search_articles,
    sync_skill, sync_article, scoring logic, experiment bucketing
"""
import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.postgres.fields import ArrayField
from django.db.models import Lookup
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.search.services import SearchService
from apps.skills.models import Skill, SkillStatus, SkillCategory, PricingModel
from apps.workshop.models import (
    Article,
    ArticleStatus,
    ArticleDifficulty,
    ArticleType,
)


# ---------------------------------------------------------------------------
# SQLite-compatible ArrayOverlap lookup
# ---------------------------------------------------------------------------
# Django's __overlap is PostgreSQL-only.  Register a minimal SQLite fallback
# so the DB-fallback search paths work in the test suite.

class _ArrayOverlapSQLite(Lookup):
    lookup_name = "overlap"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        # In SQLite the array column is stored as a JSON text string.
        # We check whether any element from `rhs` (a JSON array) appears
        # inside the stored text via simple LIKE matching.  This is
        # intentionally simplified for test-only use.
        rhs_value = rhs_params[0] if rhs_params else "[]"
        if isinstance(rhs_value, str):
            try:
                items = json.loads(rhs_value)
            except (json.JSONDecodeError, TypeError):
                items = []
        elif isinstance(rhs_value, list):
            items = rhs_value
        else:
            items = []

        if not items:
            return "1 = 0", []

        conditions = []
        params = []
        for item in items:
            conditions.append(f"{lhs} LIKE %s")
            params.append(f"%{item}%")
        return "(" + " OR ".join(conditions) + ")", params


# Only register once -- ignore if already present.
try:
    ArrayField.register_lookup(_ArrayOverlapSQLite)
except Exception:
    pass


pytestmark = pytest.mark.django_db


# ===========================================================================
#  Helpers / Fixtures
# ===========================================================================


@pytest.fixture(autouse=True)
def _no_meilisearch(monkeypatch):
    """Force SearchService to use the database fallback by making _get_client
    always return None.  This ensures tests are deterministic regardless of
    whether a Meilisearch instance is running locally."""
    monkeypatch.setattr(SearchService, "_get_client", classmethod(lambda cls: None))

@pytest.fixture
def user_alice():
    return User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="pass1234",
        display_name="Alice",
    )


@pytest.fixture
def user_bob():
    return User.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="pass1234",
        display_name="Bob",
    )


@pytest.fixture
def user_carol():
    return User.objects.create_user(
        username="carol",
        email="carol@example.com",
        password="pass1234",
        display_name="Carol",
    )


def _make_skill(creator, *, name="Test Skill", slug=None, description="desc",
                category=SkillCategory.CODE_DEV, status=SkillStatus.APPROVED,
                tags=None, is_featured=False, total_calls=0,
                avg_rating=Decimal("0.00"), review_count=0):
    slug = slug or name.lower().replace(" ", "-")
    return Skill.objects.create(
        creator=creator,
        name=name,
        slug=slug,
        description=description,
        system_prompt="prompt",
        category=category,
        tags=tags or [],
        status=status,
        is_featured=is_featured,
        total_calls=total_calls,
        avg_rating=avg_rating,
        review_count=review_count,
    )


def _make_article(author, *, title="Test Article", slug=None, content="body",
                  difficulty=ArticleDifficulty.BEGINNER,
                  article_type=ArticleType.TUTORIAL,
                  status=ArticleStatus.PUBLISHED,
                  model_tags=None, custom_tags=None,
                  is_featured=False, net_votes=Decimal("0"),
                  total_tips=Decimal("0"), view_count=0):
    slug = slug or title.lower().replace(" ", "-")
    return Article.objects.create(
        author=author,
        title=title,
        slug=slug,
        content=content,
        difficulty=difficulty,
        article_type=article_type,
        status=status,
        model_tags=model_tags or [],
        custom_tags=custom_tags or [],
        is_featured=is_featured,
        net_votes=net_votes,
        total_tips=total_tips,
        view_count=view_count,
        published_at=timezone.now(),
    )


# ===========================================================================
#  NotificationService tests
# ===========================================================================


class TestNotificationServiceSend:
    """send() creates a single notification with correct fields."""

    def test_creates_notification(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="skill_approved",
            title="Your skill was approved",
            content="Congrats!",
            reference_id="skill-42",
        )
        assert isinstance(n, Notification)
        assert n.pk is not None
        assert n.recipient == user_alice
        assert n.notification_type == "skill_approved"
        assert n.title == "Your skill was approved"
        assert n.content == "Congrats!"
        assert n.reference_id == "skill-42"
        assert n.is_read is False

    def test_defaults_content_and_reference_id(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Hello",
        )
        assert n.content == ""
        assert n.reference_id == ""

    def test_created_at_is_set(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Hello",
        )
        assert n.created_at is not None

    def test_persisted_to_database(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Persisted",
        )
        fetched = Notification.objects.get(pk=n.pk)
        assert fetched.title == "Persisted"


class TestNotificationServiceSendBulk:
    """send_bulk() creates multiple notifications efficiently."""

    def test_creates_one_per_recipient(self, user_alice, user_bob, user_carol):
        results = NotificationService.send_bulk(
            recipients=[user_alice, user_bob, user_carol],
            notification_type="announcement",
            title="System update",
            content="Please refresh.",
            reference_id="sys-1",
        )
        assert len(results) == 3
        assert Notification.objects.count() == 3

    def test_all_share_same_type_title_content(self, user_alice, user_bob):
        results = NotificationService.send_bulk(
            recipients=[user_alice, user_bob],
            notification_type="broadcast",
            title="Shared Title",
            content="Shared Content",
        )
        for n in results:
            assert n.notification_type == "broadcast"
            assert n.title == "Shared Title"
            assert n.content == "Shared Content"
            assert n.is_read is False

    def test_empty_recipients_returns_empty_list(self):
        results = NotificationService.send_bulk(
            recipients=[],
            notification_type="test",
            title="No one",
        )
        assert results == []
        assert Notification.objects.count() == 0

    def test_each_notification_has_correct_recipient(self, user_alice, user_bob):
        results = NotificationService.send_bulk(
            recipients=[user_alice, user_bob],
            notification_type="tip",
            title="You received a tip",
        )
        recipient_ids = {n.recipient_id for n in results}
        assert recipient_ids == {user_alice.pk, user_bob.pk}


class TestNotificationServiceMarkRead:
    """mark_read() marks a single notification as read."""

    def test_marks_unread_as_read(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Unread",
        )
        result = NotificationService.mark_read(user_alice, n.pk)
        assert result is not None
        assert result.is_read is True
        n.refresh_from_db()
        assert n.is_read is True

    def test_already_read_stays_read(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Already read",
        )
        n.is_read = True
        n.save(update_fields=["is_read"])
        result = NotificationService.mark_read(user_alice, n.pk)
        assert result is not None
        assert result.is_read is True

    def test_returns_none_for_nonexistent_id(self, user_alice):
        result = NotificationService.mark_read(user_alice, 99999)
        assert result is None

    def test_cannot_mark_other_users_notification(self, user_alice, user_bob):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Alice only",
        )
        result = NotificationService.mark_read(user_bob, n.pk)
        assert result is None
        n.refresh_from_db()
        assert n.is_read is False


class TestNotificationServiceMarkAllRead:
    """mark_all_read() marks all unread notifications as read."""

    def test_marks_all_unread_for_user(self, user_alice):
        for i in range(5):
            NotificationService.send(
                recipient=user_alice,
                notification_type="info",
                title=f"Notification {i}",
            )
        count = NotificationService.mark_all_read(user_alice)
        assert count == 5
        assert Notification.objects.filter(recipient=user_alice, is_read=False).count() == 0

    def test_returns_zero_when_none_unread(self, user_alice):
        n = NotificationService.send(
            recipient=user_alice,
            notification_type="info",
            title="Already read",
        )
        n.is_read = True
        n.save(update_fields=["is_read"])
        count = NotificationService.mark_all_read(user_alice)
        assert count == 0

    def test_does_not_affect_other_users(self, user_alice, user_bob):
        NotificationService.send(recipient=user_alice, notification_type="a", title="A")
        NotificationService.send(recipient=user_bob, notification_type="b", title="B")
        NotificationService.mark_all_read(user_alice)
        assert Notification.objects.filter(recipient=user_bob, is_read=False).count() == 1

    def test_skips_already_read_notifications(self, user_alice):
        n1 = NotificationService.send(recipient=user_alice, notification_type="a", title="Read")
        n1.is_read = True
        n1.save(update_fields=["is_read"])
        NotificationService.send(recipient=user_alice, notification_type="b", title="Unread")
        count = NotificationService.mark_all_read(user_alice)
        assert count == 1


class TestNotificationServiceListForUser:
    """list_for_user() returns paginated notifications for a user."""

    def test_returns_users_notifications_only(self, user_alice, user_bob):
        NotificationService.send(recipient=user_alice, notification_type="a", title="Alice 1")
        NotificationService.send(recipient=user_bob, notification_type="b", title="Bob 1")
        results = list(NotificationService.list_for_user(user_alice))
        assert len(results) == 1
        assert results[0].title == "Alice 1"

    def test_ordered_by_created_at_desc(self, user_alice):
        n1 = NotificationService.send(recipient=user_alice, notification_type="a", title="First")
        n2 = NotificationService.send(recipient=user_alice, notification_type="b", title="Second")
        n3 = NotificationService.send(recipient=user_alice, notification_type="c", title="Third")
        results = list(NotificationService.list_for_user(user_alice))
        assert [r.pk for r in results] == [n3.pk, n2.pk, n1.pk]

    def test_unread_only_filter(self, user_alice):
        n1 = NotificationService.send(recipient=user_alice, notification_type="a", title="Read")
        n1.is_read = True
        n1.save(update_fields=["is_read"])
        NotificationService.send(recipient=user_alice, notification_type="b", title="Unread")
        results = list(NotificationService.list_for_user(user_alice, unread_only=True))
        assert len(results) == 1
        assert results[0].title == "Unread"

    def test_limit_parameter(self, user_alice):
        for i in range(10):
            NotificationService.send(recipient=user_alice, notification_type="a", title=f"N{i}")
        results = list(NotificationService.list_for_user(user_alice, limit=3))
        assert len(results) == 3

    def test_offset_parameter(self, user_alice):
        for i in range(5):
            NotificationService.send(recipient=user_alice, notification_type="a", title=f"N{i}")
        all_results = list(NotificationService.list_for_user(user_alice, limit=100))
        offset_results = list(NotificationService.list_for_user(user_alice, offset=2, limit=100))
        assert len(offset_results) == 3
        assert offset_results[0].pk == all_results[2].pk

    def test_limit_and_offset_combined(self, user_alice):
        for i in range(10):
            NotificationService.send(recipient=user_alice, notification_type="a", title=f"N{i}")
        results = list(NotificationService.list_for_user(user_alice, offset=3, limit=2))
        assert len(results) == 2

    def test_empty_when_no_notifications(self, user_alice):
        results = list(NotificationService.list_for_user(user_alice))
        assert results == []


class TestNotificationServiceTotalForUser:
    """total_for_user() returns total notification count."""

    def test_counts_all_notifications(self, user_alice):
        for i in range(7):
            NotificationService.send(recipient=user_alice, notification_type="a", title=f"N{i}")
        assert NotificationService.total_for_user(user_alice) == 7

    def test_counts_unread_only(self, user_alice):
        for i in range(5):
            n = NotificationService.send(recipient=user_alice, notification_type="a", title=f"N{i}")
            if i < 2:
                n.is_read = True
                n.save(update_fields=["is_read"])
        assert NotificationService.total_for_user(user_alice, unread_only=True) == 3

    def test_returns_zero_when_none(self, user_alice):
        assert NotificationService.total_for_user(user_alice) == 0

    def test_does_not_count_other_users(self, user_alice, user_bob):
        NotificationService.send(recipient=user_alice, notification_type="a", title="A")
        NotificationService.send(recipient=user_bob, notification_type="b", title="B")
        assert NotificationService.total_for_user(user_alice) == 1


class TestNotificationServiceUnreadCount:
    """unread_count() returns only unread notification count."""

    def test_counts_unread(self, user_alice):
        for i in range(4):
            NotificationService.send(recipient=user_alice, notification_type="a", title=f"N{i}")
        assert NotificationService.unread_count(user_alice) == 4

    def test_excludes_read(self, user_alice):
        n1 = NotificationService.send(recipient=user_alice, notification_type="a", title="Read")
        n1.is_read = True
        n1.save(update_fields=["is_read"])
        NotificationService.send(recipient=user_alice, notification_type="b", title="Unread")
        assert NotificationService.unread_count(user_alice) == 1

    def test_returns_zero_when_all_read(self, user_alice):
        n = NotificationService.send(recipient=user_alice, notification_type="a", title="Read")
        n.is_read = True
        n.save(update_fields=["is_read"])
        assert NotificationService.unread_count(user_alice) == 0

    def test_returns_zero_when_no_notifications(self, user_alice):
        assert NotificationService.unread_count(user_alice) == 0

    def test_does_not_count_other_users(self, user_alice, user_bob):
        NotificationService.send(recipient=user_alice, notification_type="a", title="Alice")
        NotificationService.send(recipient=user_bob, notification_type="b", title="Bob")
        assert NotificationService.unread_count(user_alice) == 1


# ===========================================================================
#  SearchService tests (database fallback mode)
# ===========================================================================


class TestSearchServiceSearchSkills:
    """search_skills() DB fallback: text search, category filter, scoring."""

    def test_returns_database_source_when_no_meilisearch(self, user_alice):
        _make_skill(user_alice, name="Python Helper", slug="python-helper")
        result = SearchService.search_skills(q="Python")
        assert result["source"] == "database"
        assert result["experiment_bucket"] in ("A", "B")

    def test_text_search_matches_name(self, user_alice):
        _make_skill(user_alice, name="Django REST", slug="django-rest")
        _make_skill(user_alice, name="React Native", slug="react-native")
        result = SearchService.search_skills(q="Django")
        names = [s.name for s in result["items"]]
        assert "Django REST" in names
        assert "React Native" not in names

    def test_text_search_matches_description(self, user_alice):
        _make_skill(
            user_alice, name="Generic Tool", slug="generic-tool",
            description="A tool for parsing JSON data",
        )
        _make_skill(
            user_alice, name="Other Tool", slug="other-tool",
            description="XML processor",
        )
        result = SearchService.search_skills(q="JSON")
        names = [s.name for s in result["items"]]
        assert "Generic Tool" in names
        assert "Other Tool" not in names

    def test_filters_by_category(self, user_alice):
        _make_skill(user_alice, name="Code Skill", slug="code-skill",
                     category=SkillCategory.CODE_DEV)
        _make_skill(user_alice, name="Writing Skill", slug="writing-skill",
                     category=SkillCategory.WRITING)
        result = SearchService.search_skills(category=SkillCategory.WRITING)
        names = [s.name for s in result["items"]]
        assert "Writing Skill" in names
        assert "Code Skill" not in names

    def test_filters_by_category_with_query(self, user_alice):
        _make_skill(user_alice, name="Code Python", slug="code-python",
                     category=SkillCategory.CODE_DEV, description="Python code gen")
        _make_skill(user_alice, name="Write Python", slug="write-python",
                     category=SkillCategory.WRITING, description="Python essay writer")
        result = SearchService.search_skills(q="Python", category=SkillCategory.CODE_DEV)
        names = [s.name for s in result["items"]]
        assert "Code Python" in names
        assert "Write Python" not in names

    def test_only_returns_approved_skills(self, user_alice):
        _make_skill(user_alice, name="Approved", slug="approved", status=SkillStatus.APPROVED)
        _make_skill(user_alice, name="Draft", slug="draft", status=SkillStatus.DRAFT)
        _make_skill(user_alice, name="Rejected", slug="rejected", status=SkillStatus.REJECTED)
        result = SearchService.search_skills()
        names = [s.name for s in result["items"]]
        assert "Approved" in names
        assert "Draft" not in names
        assert "Rejected" not in names

    def test_respects_limit(self, user_alice):
        for i in range(10):
            _make_skill(user_alice, name=f"Skill {i}", slug=f"skill-{i}")
        result = SearchService.search_skills(limit=3)
        assert len(result["items"]) == 3

    def test_total_matches_items_length(self, user_alice):
        for i in range(5):
            _make_skill(user_alice, name=f"Skill {i}", slug=f"skill-{i}")
        result = SearchService.search_skills()
        assert result["total"] == len(result["items"])

    def test_returns_empty_when_no_match(self, user_alice):
        _make_skill(user_alice, name="Django Tool", slug="django-tool")
        result = SearchService.search_skills(q="nonexistent_xyz_query")
        assert result["items"] == []
        assert result["total"] == 0


class TestSearchServiceSearchArticles:
    """search_articles() DB fallback: text search, filters."""

    def test_returns_database_source(self, user_alice):
        _make_article(user_alice, title="Intro to AI", slug="intro-ai")
        result = SearchService.search_articles(q="AI")
        assert result["source"] == "database"

    def test_text_search_matches_title(self, user_alice):
        _make_article(user_alice, title="Django Tutorial", slug="django-tut")
        _make_article(user_alice, title="React Guide", slug="react-guide")
        result = SearchService.search_articles(q="Django")
        titles = [a.title for a in result["items"]]
        assert "Django Tutorial" in titles
        assert "React Guide" not in titles

    def test_text_search_matches_content(self, user_alice):
        _make_article(user_alice, title="Article A", slug="article-a",
                       content="This covers machine learning basics.")
        _make_article(user_alice, title="Article B", slug="article-b",
                       content="This is about cooking recipes.")
        result = SearchService.search_articles(q="machine learning")
        titles = [a.title for a in result["items"]]
        assert "Article A" in titles
        assert "Article B" not in titles

    def test_filters_by_difficulty(self, user_alice):
        _make_article(user_alice, title="Beginner Art", slug="beg-art",
                       difficulty=ArticleDifficulty.BEGINNER)
        _make_article(user_alice, title="Advanced Art", slug="adv-art",
                       difficulty=ArticleDifficulty.ADVANCED)
        result = SearchService.search_articles(difficulty=ArticleDifficulty.BEGINNER)
        titles = [a.title for a in result["items"]]
        assert "Beginner Art" in titles
        assert "Advanced Art" not in titles

    def test_filters_by_article_type(self, user_alice):
        _make_article(user_alice, title="Tutorial Art", slug="tut-art",
                       article_type=ArticleType.TUTORIAL)
        _make_article(user_alice, title="Review Art", slug="rev-art",
                       article_type=ArticleType.REVIEW)
        result = SearchService.search_articles(article_type=ArticleType.TUTORIAL)
        titles = [a.title for a in result["items"]]
        assert "Tutorial Art" in titles
        assert "Review Art" not in titles

    def test_only_returns_published_articles(self, user_alice):
        _make_article(user_alice, title="Published", slug="pub",
                       status=ArticleStatus.PUBLISHED)
        _make_article(user_alice, title="Draft", slug="dra",
                       status=ArticleStatus.DRAFT)
        _make_article(user_alice, title="Archived", slug="arc",
                       status=ArticleStatus.ARCHIVED)
        result = SearchService.search_articles()
        titles = [a.title for a in result["items"]]
        assert "Published" in titles
        assert "Draft" not in titles
        assert "Archived" not in titles

    def test_respects_limit(self, user_alice):
        for i in range(10):
            _make_article(user_alice, title=f"Art {i}", slug=f"art-{i}")
        result = SearchService.search_articles(limit=4)
        assert len(result["items"]) == 4

    def test_returns_empty_when_no_match(self, user_alice):
        _make_article(user_alice, title="Cooking Tips", slug="cook")
        result = SearchService.search_articles(q="quantum_physics_xyz")
        assert result["items"] == []


class TestSearchServiceSync:
    """sync_skill() / sync_article() should not error without Meilisearch."""

    def test_sync_skill_returns_false_without_meilisearch(self, user_alice):
        skill = _make_skill(user_alice, name="Sync Test", slug="sync-test")
        result = SearchService.sync_skill(skill)
        assert result is False

    def test_sync_article_returns_false_without_meilisearch(self, user_alice):
        article = _make_article(user_alice, title="Sync Art", slug="sync-art")
        result = SearchService.sync_article(article)
        assert result is False

    def test_sync_all_skills_returns_false_without_meilisearch(self):
        result = SearchService.sync_all_skills()
        assert result is False

    def test_sync_all_articles_returns_false_without_meilisearch(self):
        result = SearchService.sync_all_articles()
        assert result is False

    def test_remove_article_returns_false_without_meilisearch(self):
        result = SearchService.remove_article(999)
        assert result is False

    def test_sync_does_not_raise(self, user_alice):
        """Ensure sync methods are safe to call even when Meilisearch is down."""
        skill = _make_skill(user_alice, name="Safe Sync", slug="safe-sync")
        article = _make_article(user_alice, title="Safe Art", slug="safe-art")
        # Should not raise
        SearchService.sync_skill(skill)
        SearchService.sync_article(article)
        SearchService.sync_all_skills()
        SearchService.sync_all_articles()
        SearchService.remove_article(article.pk)

    def test_optimize_index_settings_returns_false_without_meilisearch(self):
        result = SearchService.optimize_index_settings()
        assert result == {"skills": False, "articles": False}


class TestSearchServiceSkillScoring:
    """Scoring logic: featured skills rank higher, higher-rated skills rank higher."""

    def test_featured_skills_rank_higher(self, user_alice):
        regular = _make_skill(
            user_alice, name="Regular Tool", slug="regular-tool",
            total_calls=100, avg_rating=Decimal("4.50"), review_count=20,
        )
        featured = _make_skill(
            user_alice, name="Featured Tool", slug="featured-tool",
            is_featured=True, total_calls=10, avg_rating=Decimal("3.00"),
            review_count=2,
        )
        result = SearchService.search_skills(q="Tool")
        items = result["items"]
        assert len(items) == 2
        # Featured item should come first due to feature_bonus (4 points)
        assert items[0].name == "Featured Tool"

    def test_higher_rated_skills_rank_higher_in_bucket_b(self, user_alice):
        low_rated = _make_skill(
            user_alice, name="Low Rated Tool", slug="low-tool",
            total_calls=1000, avg_rating=Decimal("2.00"), review_count=100,
        )
        high_rated = _make_skill(
            user_alice, name="High Rated Tool", slug="high-tool",
            total_calls=5, avg_rating=Decimal("5.00"), review_count=2,
        )
        result = SearchService.search_skills(
            q="Tool", experiment_bucket="B",
        )
        items = result["items"]
        assert len(items) == 2
        # In bucket B, quality (avg_rating) is prioritized after relevance
        assert items[0].name == "High Rated Tool"

    def test_popular_skills_rank_higher_in_bucket_a(self, user_alice):
        unpopular = _make_skill(
            user_alice, name="Quiet Tool", slug="quiet-tool",
            total_calls=1, avg_rating=Decimal("5.00"), review_count=1,
        )
        popular = _make_skill(
            user_alice, name="Popular Tool", slug="popular-tool",
            total_calls=5000, avg_rating=Decimal("3.50"), review_count=100,
        )
        result = SearchService.search_skills(
            q="Tool", experiment_bucket="A",
        )
        items = result["items"]
        assert len(items) == 2
        # In bucket A, popularity (total_calls) is second priority after relevance
        assert items[0].name == "Popular Tool"

    def test_name_match_scores_higher_than_description_match(self, user_alice):
        desc_match = _make_skill(
            user_alice, name="Generic App", slug="generic-app",
            description="A helper for Python coding",
            total_calls=100, avg_rating=Decimal("4.00"),
        )
        name_match = _make_skill(
            user_alice, name="Python Master", slug="python-master",
            description="General purpose tool",
            total_calls=1, avg_rating=Decimal("1.00"),
        )
        result = SearchService.search_skills(q="Python")
        items = result["items"]
        assert len(items) == 2
        # "Python" in name gives +6 relevance vs +3 in description
        assert items[0].name == "Python Master"


class TestSearchServiceArticleScoring:
    """Article scoring: featured articles rank higher, net_votes matter."""

    def test_featured_articles_rank_higher(self, user_alice):
        regular = _make_article(
            user_alice, title="Regular Post", slug="regular-post",
            net_votes=Decimal("50"), view_count=1000,
        )
        featured = _make_article(
            user_alice, title="Featured Post", slug="featured-post",
            is_featured=True, net_votes=Decimal("1"), view_count=5,
        )
        result = SearchService.search_articles(q="Post")
        items = result["items"]
        assert len(items) == 2
        assert items[0].title == "Featured Post"

    def test_higher_votes_rank_higher_in_bucket_a(self, user_alice):
        low_votes = _make_article(
            user_alice, title="Low Votes Article", slug="low-votes",
            net_votes=Decimal("1"), view_count=5000,
        )
        high_votes = _make_article(
            user_alice, title="High Votes Article", slug="high-votes",
            net_votes=Decimal("100"), view_count=10,
        )
        result = SearchService.search_articles(q="Article", experiment_bucket="A")
        items = result["items"]
        assert len(items) == 2
        # Bucket A: net_votes is the second ranking factor
        assert items[0].title == "High Votes Article"

    def test_higher_views_rank_higher_in_bucket_b(self, user_alice):
        low_views = _make_article(
            user_alice, title="Low Views Article", slug="low-views",
            net_votes=Decimal("500"), view_count=1,
        )
        high_views = _make_article(
            user_alice, title="High Views Article", slug="high-views",
            net_votes=Decimal("1"), view_count=10000,
        )
        result = SearchService.search_articles(q="Article", experiment_bucket="B")
        items = result["items"]
        assert len(items) == 2
        # Bucket B: view_count is the second ranking factor
        assert items[0].title == "High Views Article"

    def test_title_match_scores_higher_than_content_match(self, user_alice):
        content_match = _make_article(
            user_alice, title="Generic Guide", slug="generic-guide",
            content="Learn about Kubernetes deployments",
            net_votes=Decimal("100"), view_count=5000,
        )
        title_match = _make_article(
            user_alice, title="Kubernetes Essentials", slug="k8s-ess",
            content="General ops guide for containers",
            net_votes=Decimal("1"), view_count=1,
        )
        result = SearchService.search_articles(q="Kubernetes")
        items = result["items"]
        assert len(items) == 2
        # "Kubernetes" in title gives +8 relevance vs +3 in content
        assert items[0].title == "Kubernetes Essentials"


class TestSearchServiceExperimentBucket:
    """assign_experiment_bucket() deterministically assigns A or B."""

    def test_deterministic_bucket(self):
        b1 = SearchService.assign_experiment_bucket("test-seed")
        b2 = SearchService.assign_experiment_bucket("test-seed")
        assert b1 == b2

    def test_returns_a_or_b(self):
        bucket = SearchService.assign_experiment_bucket("any-seed")
        assert bucket in ("A", "B")

    def test_empty_seed_returns_a(self):
        assert SearchService.assign_experiment_bucket("") == "A"

    def test_different_seeds_can_produce_different_buckets(self):
        """At least some seeds should map to A and some to B."""
        buckets = set()
        for i in range(100):
            buckets.add(SearchService.assign_experiment_bucket(f"seed-{i}"))
        assert "A" in buckets
        assert "B" in buckets

    def test_search_skills_includes_experiment_bucket_in_result(self, user_alice):
        _make_skill(user_alice, name="Test", slug="test-eb")
        result = SearchService.search_skills(q="Test", experiment_bucket="A")
        assert result["experiment_bucket"] == "A"

    def test_search_articles_includes_experiment_bucket_in_result(self, user_alice):
        _make_article(user_alice, title="Test", slug="test-eb-art")
        result = SearchService.search_articles(q="Test", experiment_bucket="B")
        assert result["experiment_bucket"] == "B"
