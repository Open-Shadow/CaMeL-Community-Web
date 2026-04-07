from datetime import timedelta
from decimal import Decimal
import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from apps.notifications.models import Notification
from apps.skills.models import PricingModel, Skill, SkillCall, SkillStatus
from apps.skills.services import SkillService
from apps.workshop.models import Article, ArticleStatus, ArticleType, Series
from apps.workshop.services import ArticleService, SeriesService

User = get_user_model()


def create_user(email: str, *, credit_score: int = 100, balance: Decimal = Decimal("0.00")):
    user = User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        display_name=email.split("@")[0],
        credit_score=credit_score,
        balance=balance,
    )
    user.level = "EXPERT" if credit_score >= 500 else "CRAFTSMAN" if credit_score >= 100 else "SEED"
    user.save(update_fields=["level"])
    return user


def create_skill(creator, name: str, *, category: str = "AGENT", tags: list[str] | None = None):
    return Skill.objects.create(
        creator=creator,
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=f"{name} description",
        system_prompt=f"{name} system prompt",
        category=category,
        tags=tags or [],
        pricing_model=PricingModel.FREE,
        status=SkillStatus.APPROVED,
        avg_rating=Decimal("4.50"),
        review_count=5,
        total_calls=20,
    )


def create_article(
    author,
    title: str,
    *,
    model_tags: list[str] | None = None,
    custom_tags: list[str] | None = None,
    related_skill=None,
    series=None,
    series_order: int | None = None,
):
    article = Article.objects.create(
        author=author,
        series=series,
        series_order=series_order,
        related_skill=related_skill,
        title=title,
        slug=title.lower().replace(" ", "-"),
        content="问题 " * 200 + "方案 " * 200 + "效果 " * 200,
        difficulty="INTERMEDIATE",
        article_type=ArticleType.TUTORIAL,
        model_tags=model_tags or ["GPT-5"],
        custom_tags=custom_tags or ["prompt"],
        status=ArticleStatus.PUBLISHED,
        net_votes=Decimal("8.00"),
        published_at=timezone.now() - timedelta(days=1),
    )
    return article


pytestmark = pytest.mark.django_db


def auth_client(user) -> Client:
    from apps.accounts.services import AuthService

    client = Client()
    token = AuthService.get_tokens_for_user(user)["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


def test_skill_recommendations_prioritize_matching_call_history():
    user = create_user("caller@example.com")
    creator = create_user("creator@example.com")

    called_skill = create_skill(creator, "Prompt Operator", category="AGENT", tags=["prompt", "workflow"])
    recommended_skill = create_skill(creator, "Workflow Copilot", category="AGENT", tags=["workflow", "automation"])
    create_skill(creator, "Data Cleaner", category="DATA_ANALYTICS", tags=["sql"])

    SkillCall.objects.create(
        skill=called_skill,
        caller=user,
        skill_version=1,
        input_text="optimize workflow",
        output_text="done",
    )

    recommendations = SkillService.compute_recommended_skills(user, limit=3)

    assert recommendations
    assert recommendations[0]["skill"].id == recommended_skill.id
    assert "标签" in recommendations[0]["reason"] or "分类" in recommendations[0]["reason"]


def test_article_recommendations_and_related_articles_follow_read_history():
    user = create_user("reader@example.com")
    author = create_user("author@example.com")
    shared_skill = create_skill(author, "Prompt Chain", tags=["prompt", "gpt-5"])

    viewed = create_article(author, "Prompt Primer", related_skill=shared_skill, model_tags=["GPT-5"], custom_tags=["prompt"])
    matching = create_article(author, "Prompt Patterns", related_skill=shared_skill, model_tags=["GPT-5"], custom_tags=["prompt", "chain"])
    other = create_article(author, "SQL Notes", model_tags=["通用"], custom_tags=["sql"])

    ArticleService.record_read(viewed, user)
    recommendations = ArticleService.compute_recommended_articles(user, limit=3)
    related = ArticleService.list_related_articles(viewed, limit=3)

    assert recommendations[0]["article"].id == matching.id
    assert related[0]["article"].id == matching.id
    assert all(item["article"].id != other.id for item in related[:1])


def test_series_completion_reward_is_granted_once():
    author = create_user("series-author@example.com", credit_score=0, balance=Decimal("0.00"))
    series = SeriesService.create(author, {"title": "Prompt Ops", "description": "series"})

    for index in range(1, 4):
        create_article(author, f"Series Article {index}", series=series, series_order=index)

    series.refresh_from_db()
    SeriesService.refresh_completion_state(series)

    rewarded = SeriesService.ensure_completion_reward(series)
    author.refresh_from_db()
    series.refresh_from_db()

    assert rewarded is True
    assert series.is_completed is True
    assert series.completion_rewarded is True
    assert author.balance == Decimal("1.00")
    assert author.credit_score == 30
    assert SeriesService.ensure_completion_reward(series) is False


def test_lifecycle_tasks_mark_outdated_archive_and_cleanup_data():
    author = create_user("lifecycle-author@example.com")
    old_article = create_article(author, "Legacy GPT-4 Guide", model_tags=["GPT-4"], custom_tags=["legacy"])
    Article.objects.filter(id=old_article.id).update(
        published_at=timezone.now() - timedelta(days=240),
        updated_at=timezone.now() - timedelta(days=240),
        net_votes=Decimal("1.00"),
    )

    notification = Notification.objects.create(
        recipient=author,
        notification_type="TEST",
        title="old",
        content="cleanup me",
        is_read=True,
    )
    Notification.objects.filter(id=notification.id).update(created_at=timezone.now() - timedelta(days=120))
    Session.objects.create(
        session_key="expired-session",
        session_data="e30=",
        expire_date=timezone.now() - timedelta(days=1),
    )

    outdated_result = ArticleService.detect_outdated_articles()
    archive_result = ArticleService.auto_archive_stale_articles()
    cleanup_result = ArticleService.cleanup_old_data()

    old_article.refresh_from_db()
    assert outdated_result["updated"] >= 1
    assert archive_result["archived"] >= 1
    assert old_article.is_outdated is True
    assert old_article.status == ArticleStatus.ARCHIVED
    assert cleanup_result["deleted_sessions"] >= 1


def test_phase4_api_endpoints_expose_recommendations_and_series():
    user = create_user("api-user@example.com")
    author = create_user("api-author@example.com")
    skill = create_skill(author, "API Skill", tags=["prompt", "workflow"])
    SkillCall.objects.create(
        skill=skill,
        caller=user,
        skill_version=1,
        input_text="history",
        output_text="done",
    )
    create_skill(author, "API Skill Match", tags=["workflow", "agent"])

    series = SeriesService.create(author, {"title": "API Series", "description": "desc"})
    create_article(author, "API Article 1", series=series, series_order=1)
    create_article(author, "API Article 2", series=series, series_order=2)
    create_article(author, "API Article 3", series=series, series_order=3)

    client = auth_client(user)

    rec_response = client.get("/api/skills/recommended")
    series_response = client.get("/api/workshop/series")
    detail_response = client.get(f"/api/workshop/series/{series.id}")

    assert rec_response.status_code == 200
    assert len(rec_response.json()) >= 1
    assert series_response.status_code == 200
    assert series_response.json()[0]["title"] == "API Series"
    assert detail_response.status_code == 200
    assert len(detail_response.json()["articles"]) == 3


def test_workshop_create_draft_api_endpoint_works():
    user = create_user("draft-author@example.com")
    client = auth_client(user)

    payload = {
        "title": "Draft From API",
        "content": "这是一个草稿内容",
        "difficulty": "BEGINNER",
        "article_type": "TUTORIAL",
        "model_tags": ["Claude Code"],
        "custom_tags": ["mcp"],
    }

    response = client.post(
        "/api/workshop/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["status"] == ArticleStatus.DRAFT
    assert Article.objects.filter(
        id=body["id"],
        author=user,
        status=ArticleStatus.DRAFT,
    ).exists()
