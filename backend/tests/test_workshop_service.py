"""Comprehensive tests for workshop services: Article, Series, Tip, voting, comments."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User, UserLevel
from apps.credits.models import CreditLog
from apps.payments.models import Transaction
from apps.workshop.models import (
    Article,
    ArticleDifficulty,
    ArticleStatus,
    ArticleType,
    Comment,
    CommentVote,
    Series,
    Tip,
    Vote,
)
from apps.workshop.services import ArticleService, SeriesService, TipService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _long_content(extra: str = "") -> str:
    """Return content that satisfies the 500-char + required-sections rule."""
    base = (
        "问题：用户在使用 GPT 模型时经常遇到幻觉问题，这导致生成的文本不可靠。"
        "方案：我们设计了一套多轮验证提示词框架，通过交叉引用外部知识库来减少幻觉。"
        "效果：经过测试，幻觉率从 40% 下降至 8%，用户满意度提升了 60%。"
    )
    padding = "这是一些额外的填充文字用来确保文章内容超过五百个字符的最低要求。" * 15
    return base + padding + extra


def _make_user(
    username: str,
    *,
    balance: Decimal = Decimal("0.00"),
    level: str = UserLevel.SEED,
    credit_score: int = 0,
) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="testpass123",
    )
    user.balance = balance
    user.level = level
    user.credit_score = credit_score
    user.save(update_fields=["balance", "level", "credit_score"])
    return user


_SENTINEL = object()


def _make_article(
    author: User,
    *,
    title: str = "测试文章标题示例",
    content: str | None = None,
    status: str = ArticleStatus.DRAFT,
    model_tags: list[str] | object = _SENTINEL,
) -> Article:
    """Create an article via the ORM directly (bypass validation)."""
    resolved_tags = ["gpt-5"] if model_tags is _SENTINEL else model_tags
    return Article.objects.create(
        author=author,
        title=title,
        slug=ArticleService._create_unique_slug(title, author.id),
        content=content or _long_content(),
        difficulty=ArticleDifficulty.BEGINNER,
        article_type=ArticleType.TUTORIAL,
        model_tags=resolved_tags,
        custom_tags=[],
        status=status,
        published_at=timezone.now() if status == ArticleStatus.PUBLISHED else None,
    )


# ---------------------------------------------------------------------------
# Article CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArticleCreate:
    """ArticleService.create()"""

    def test_valid_creation(self):
        user = _make_user("author1")
        article = ArticleService.create(user, {
            "title": "测试文章：入门指南",
            "content": "一些初始内容",
            "difficulty": ArticleDifficulty.BEGINNER,
            "article_type": ArticleType.TUTORIAL,
            "model_tags": ["gpt-5"],
        })
        assert article.pk is not None
        assert article.author == user
        assert article.title == "测试文章：入门指南"
        assert article.status == ArticleStatus.DRAFT

    def test_slug_generated(self):
        user = _make_user("author2")
        article = ArticleService.create(user, {
            "title": "Slug 生成测试标题",
            "content": "内容",
            "model_tags": ["gpt-5"],
        })
        assert article.slug  # non-empty slug
        assert Article.objects.filter(slug=article.slug).count() == 1

    def test_slug_uniqueness(self):
        user = _make_user("author3")
        a1 = ArticleService.create(user, {
            "title": "重复标题测试示例",
            "content": "内容一",
            "model_tags": ["gpt-5"],
        })
        a2 = ArticleService.create(user, {
            "title": "重复标题测试示例",
            "content": "内容二",
            "model_tags": ["gpt-5"],
        })
        assert a1.slug != a2.slug

    def test_title_too_short_raises(self):
        user = _make_user("author4")
        with pytest.raises(ValueError, match="标题长度"):
            ArticleService.create(user, {
                "title": "短",
                "content": "内容",
                "model_tags": ["gpt-5"],
            })

    def test_title_too_long_raises(self):
        user = _make_user("author5")
        with pytest.raises(ValueError, match="标题长度"):
            ArticleService.create(user, {
                "title": "长" * 121,
                "content": "内容",
                "model_tags": ["gpt-5"],
            })

    def test_invalid_difficulty_raises(self):
        user = _make_user("author6")
        with pytest.raises(ValueError, match="难度无效"):
            ArticleService.create(user, {
                "title": "有效标题测试文章",
                "content": "内容",
                "difficulty": "IMPOSSIBLE",
                "model_tags": ["gpt-5"],
            })

    def test_invalid_article_type_raises(self):
        user = _make_user("author7")
        with pytest.raises(ValueError, match="类型无效"):
            ArticleService.create(user, {
                "title": "有效标题测试文章",
                "content": "内容",
                "article_type": "INVALID_TYPE",
                "model_tags": ["gpt-5"],
            })


@pytest.mark.django_db
class TestArticleUpdate:
    """ArticleService.update()"""

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_field_updates(self, _mock_sync):
        user = _make_user("upd_author")
        article = _make_article(user)
        updated = ArticleService.update(article, {
            "content": "更新后的内容",
            "difficulty": ArticleDifficulty.ADVANCED,
        })
        assert updated.content == "更新后的内容"
        assert updated.difficulty == ArticleDifficulty.ADVANCED

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_slug_regenerated_on_title_change(self, _mock_sync):
        user = _make_user("upd_author2")
        article = _make_article(user, title="原始标题测试用例")
        old_slug = article.slug
        updated = ArticleService.update(article, {"title": "全新标题测试用例"})
        assert updated.title == "全新标题测试用例"
        assert updated.slug != old_slug

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_slug_not_changed_when_title_same(self, _mock_sync):
        user = _make_user("upd_author3")
        article = _make_article(user, title="保持不变的标题")
        old_slug = article.slug
        updated = ArticleService.update(article, {"content": "只改内容"})
        assert updated.slug == old_slug


# ---------------------------------------------------------------------------
# Article Publish
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArticlePublish:
    """ArticleService.publish()"""

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    @patch("apps.workshop.services.CreditService.add_credit", return_value=15)
    def test_publish_success(self, _mock_credit, _mock_sync):
        user = _make_user("pub_author")
        article = _make_article(user, model_tags=["gpt-5"])
        result = ArticleService.publish(article)
        assert result.status == ArticleStatus.PUBLISHED
        assert result.published_at is not None
        _mock_credit.assert_called_once()

    def test_publish_already_published_raises(self):
        user = _make_user("pub_author2")
        article = _make_article(user, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="已经发布"):
            ArticleService.publish(article)

    def test_publish_archived_raises(self):
        user = _make_user("pub_author3")
        article = _make_article(user, status=ArticleStatus.ARCHIVED)
        with pytest.raises(ValueError, match="归档文章不能直接发布"):
            ArticleService.publish(article)

    def test_publish_too_short_raises(self):
        user = _make_user("pub_author4")
        article = _make_article(user, content="短内容不足五百字")
        with pytest.raises(ValueError, match="至少 500 个字符"):
            ArticleService.publish(article)

    def test_publish_missing_sections_raises(self):
        user = _make_user("pub_author5")
        # Content that is >= 500 chars but missing the required sections
        filler = "这是一段没有包含必要段落的长文本。" * 40
        article = _make_article(user, content=filler)
        with pytest.raises(ValueError, match="问题 / 方案 / 效果"):
            ArticleService.publish(article)

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    @patch("apps.workshop.services.CreditService.add_credit", return_value=15)
    def test_publish_no_model_tags_raises(self, _mock_credit, _mock_sync):
        user = _make_user("pub_author6")
        article = _make_article(user, model_tags=[])
        with pytest.raises(ValueError, match="至少选择 1 个模型标签"):
            ArticleService.publish(article)


# ---------------------------------------------------------------------------
# Article Archive
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArticleArchive:
    """ArticleService.archive()"""

    @patch("apps.workshop.services.SearchService.remove_article", return_value=False)
    def test_archive_changes_status(self, _mock_remove):
        user = _make_user("arc_author")
        article = _make_article(user, status=ArticleStatus.PUBLISHED)
        result = ArticleService.archive(article)
        assert result.status == ArticleStatus.ARCHIVED
        _mock_remove.assert_called_once_with(article.id)


# ---------------------------------------------------------------------------
# Article Voting
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArticleVoting:
    """ArticleService.vote() / remove_vote()"""

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_create_upvote(self, _mock_sync):
        author = _make_user("vote_author")
        voter = _make_user("voter1")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        net, direction = ArticleService.vote(article, voter, "UP")
        assert direction == "UP"
        assert net == Decimal("1.00")  # SEED weight = 1.0
        assert Vote.objects.filter(article=article, voter=voter).exists()

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_create_downvote(self, _mock_sync):
        author = _make_user("vote_author2")
        voter = _make_user("voter2")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        net, direction = ArticleService.vote(article, voter, "DOWN")
        assert direction == "DOWN"
        assert net == Decimal("-1.00")

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_change_vote(self, _mock_sync):
        author = _make_user("vote_author3")
        voter = _make_user("voter3")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        ArticleService.vote(article, voter, "UP")
        net, direction = ArticleService.vote(article, voter, "DOWN")
        assert direction == "DOWN"
        assert net == Decimal("-1.00")
        # Should still be a single vote record
        assert Vote.objects.filter(article=article, voter=voter).count() == 1

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_weighted_voting(self, _mock_sync):
        """Higher-level users have greater vote weight."""
        author = _make_user("vote_author4")
        expert_voter = _make_user("expert_voter", level=UserLevel.EXPERT)
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        net, _ = ArticleService.vote(article, expert_voter, "UP")
        assert net == Decimal("2.00")  # EXPERT weight = 2.0

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_grandmaster_weight(self, _mock_sync):
        author = _make_user("vote_author5")
        gm_voter = _make_user("gm_voter", level=UserLevel.GRANDMASTER)
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        net, _ = ArticleService.vote(article, gm_voter, "UP")
        assert net == Decimal("5.00")

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_net_votes_recalculation_multiple_voters(self, _mock_sync):
        author = _make_user("vote_author6")
        v1 = _make_user("multi_voter1", level=UserLevel.SEED)
        v2 = _make_user("multi_voter2", level=UserLevel.CRAFTSMAN)
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        ArticleService.vote(article, v1, "UP")    # +1.0
        ArticleService.vote(article, v2, "DOWN")  # -1.5
        article.refresh_from_db()
        assert article.net_votes == Decimal("-0.50")

    def test_vote_on_draft_raises(self):
        author = _make_user("vote_author7")
        voter = _make_user("voter7")
        article = _make_article(author, status=ArticleStatus.DRAFT)
        with pytest.raises(ValueError, match="只能给已发布文章投票"):
            ArticleService.vote(article, voter, "UP")

    def test_vote_invalid_value_raises(self):
        author = _make_user("vote_author8")
        voter = _make_user("voter8")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="投票值无效"):
            ArticleService.vote(article, voter, "SIDEWAYS")

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_remove_vote(self, _mock_sync):
        author = _make_user("vote_author9")
        voter = _make_user("voter9")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        ArticleService.vote(article, voter, "UP")
        net = ArticleService.remove_vote(article, voter)
        assert net == Decimal("0.00")
        assert not Vote.objects.filter(article=article, voter=voter).exists()

    def test_remove_vote_none_exists_raises(self):
        author = _make_user("vote_author10")
        voter = _make_user("voter10")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="没有可取消的投票"):
            ArticleService.remove_vote(article, voter)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComments:
    """ArticleService.add_comment(), pin_comment(), vote_comment()"""

    def test_add_comment_to_published_article(self):
        author = _make_user("cmt_author")
        commenter = _make_user("commenter1")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        comment = ArticleService.add_comment(article, commenter, "好文章！")
        assert comment.pk is not None
        assert comment.content == "好文章！"
        assert comment.article == article
        assert comment.parent is None

    def test_reply_to_comment(self):
        author = _make_user("cmt_author2")
        commenter = _make_user("commenter2")
        replier = _make_user("replier1")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        parent = ArticleService.add_comment(article, commenter, "一级评论")
        reply = ArticleService.add_comment(article, replier, "回复内容", parent_id=parent.id)
        assert reply.parent == parent
        assert reply.article == article

    def test_deeper_nesting_raises(self):
        author = _make_user("cmt_author3")
        c1 = _make_user("commenter3a")
        c2 = _make_user("commenter3b")
        c3 = _make_user("commenter3c")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        parent = ArticleService.add_comment(article, c1, "一级评论")
        reply = ArticleService.add_comment(article, c2, "二级回复", parent_id=parent.id)
        with pytest.raises(ValueError, match="仅支持一层回复"):
            ArticleService.add_comment(article, c3, "三级嵌套", parent_id=reply.id)

    def test_comment_on_draft_raises(self):
        author = _make_user("cmt_author4")
        commenter = _make_user("commenter4")
        article = _make_article(author, status=ArticleStatus.DRAFT)
        with pytest.raises(ValueError, match="只能评论已发布文章"):
            ArticleService.add_comment(article, commenter, "不该成功")

    def test_comment_empty_raises(self):
        author = _make_user("cmt_author5")
        commenter = _make_user("commenter5")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="评论长度"):
            ArticleService.add_comment(article, commenter, "   ")

    def test_comment_too_long_raises(self):
        author = _make_user("cmt_author6")
        commenter = _make_user("commenter6")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="评论长度"):
            ArticleService.add_comment(article, commenter, "字" * 501)

    def test_reply_target_not_found_raises(self):
        author = _make_user("cmt_author7")
        commenter = _make_user("commenter7")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="回复目标不存在"):
            ArticleService.add_comment(article, commenter, "回复", parent_id=99999)


@pytest.mark.django_db
class TestPinComment:
    """ArticleService.pin_comment()"""

    def test_author_can_pin(self):
        author = _make_user("pin_author")
        commenter = _make_user("pin_commenter")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        comment = ArticleService.add_comment(article, commenter, "精华评论")
        pinned = ArticleService.pin_comment(article, author, comment.id)
        assert pinned.is_pinned is True

    def test_non_author_cannot_pin(self):
        author = _make_user("pin_author2")
        other = _make_user("pin_other")
        commenter = _make_user("pin_commenter2")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        comment = ArticleService.add_comment(article, commenter, "评论")
        with pytest.raises(ValueError, match="只有文章作者可以置顶"):
            ArticleService.pin_comment(article, other, comment.id)

    def test_pinning_unpins_previous(self):
        author = _make_user("pin_author3")
        c1 = _make_user("pin_c1")
        c2 = _make_user("pin_c2")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        comment1 = ArticleService.add_comment(article, c1, "第一条评论")
        comment2 = ArticleService.add_comment(article, c2, "第二条评论")

        ArticleService.pin_comment(article, author, comment1.id)
        ArticleService.pin_comment(article, author, comment2.id)

        comment1.refresh_from_db()
        comment2.refresh_from_db()
        assert comment1.is_pinned is False
        assert comment2.is_pinned is True

    def test_pin_nonexistent_comment_raises(self):
        author = _make_user("pin_author4")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="评论不存在"):
            ArticleService.pin_comment(article, author, 99999)


@pytest.mark.django_db
class TestCommentVoting:
    """ArticleService.vote_comment() / remove_comment_vote()"""

    def test_upvote_comment(self):
        author = _make_user("cv_author")
        commenter = _make_user("cv_commenter")
        voter = _make_user("cv_voter")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "好评论")

        net, direction = ArticleService.vote_comment(comment, voter, "UP")
        assert direction == "UP"
        assert net == 1

    def test_downvote_comment(self):
        author = _make_user("cv_author2")
        commenter = _make_user("cv_commenter2")
        voter = _make_user("cv_voter2")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "差评论")

        net, direction = ArticleService.vote_comment(comment, voter, "DOWN")
        assert direction == "DOWN"
        assert net == -1

    def test_change_comment_vote(self):
        author = _make_user("cv_author3")
        commenter = _make_user("cv_commenter3")
        voter = _make_user("cv_voter3")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "评论")

        ArticleService.vote_comment(comment, voter, "UP")
        net, direction = ArticleService.vote_comment(comment, voter, "DOWN")
        assert direction == "DOWN"
        assert net == -1
        assert CommentVote.objects.filter(comment=comment, voter=voter).count() == 1

    def test_multiple_voters_net_votes(self):
        author = _make_user("cv_author4")
        commenter = _make_user("cv_commenter4")
        v1 = _make_user("cv_voter4a")
        v2 = _make_user("cv_voter4b")
        v3 = _make_user("cv_voter4c")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "评论")

        ArticleService.vote_comment(comment, v1, "UP")    # +1
        ArticleService.vote_comment(comment, v2, "UP")    # +1
        ArticleService.vote_comment(comment, v3, "DOWN")  # -1
        comment.refresh_from_db()
        assert comment.net_votes == 1

    def test_invalid_comment_vote_value_raises(self):
        author = _make_user("cv_author5")
        commenter = _make_user("cv_commenter5")
        voter = _make_user("cv_voter5")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "评论")
        with pytest.raises(ValueError, match="评论投票值无效"):
            ArticleService.vote_comment(comment, voter, "NEUTRAL")

    def test_remove_comment_vote(self):
        author = _make_user("cv_author6")
        commenter = _make_user("cv_commenter6")
        voter = _make_user("cv_voter6")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "评论")

        ArticleService.vote_comment(comment, voter, "UP")
        net = ArticleService.remove_comment_vote(comment, voter)
        assert net == 0
        assert not CommentVote.objects.filter(comment=comment, voter=voter).exists()

    def test_remove_comment_vote_none_exists_raises(self):
        author = _make_user("cv_author7")
        commenter = _make_user("cv_commenter7")
        voter = _make_user("cv_voter7")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        comment = ArticleService.add_comment(article, commenter, "评论")
        with pytest.raises(ValueError, match="没有可取消的评论投票"):
            ArticleService.remove_comment_vote(comment, voter)


# ---------------------------------------------------------------------------
# TipService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTipService:
    """TipService.send_tip()"""

    @patch("apps.workshop.services.NotificationService.send")
    @patch("apps.workshop.services.CreditService.add_credit", return_value=5)
    def test_send_tip_success(self, _mock_credit, _mock_notify):
        author = _make_user("tip_author", balance=Decimal("0.00"))
        tipper = _make_user("tipper1", balance=Decimal("10.00"))
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        tip = TipService.send_tip(tipper, article.id, Decimal("1.00"))
        assert tip.pk is not None
        assert tip.amount == Decimal("1.00")
        assert tip.tipper == tipper
        assert tip.recipient == author

        # 5% fee: tipper pays 1.00, author receives 0.95
        tipper.refresh_from_db()
        author.refresh_from_db()
        assert tipper.balance == Decimal("9.00")
        assert author.balance == Decimal("0.95")

        # Article total_tips updated
        article.refresh_from_db()
        assert article.total_tips == Decimal("1.00")

    def test_self_tip_raises(self):
        author = _make_user("tip_self_author", balance=Decimal("10.00"))
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="不能打赏自己"):
            TipService.send_tip(author, article.id, Decimal("1.00"))

    def test_insufficient_balance_raises(self):
        author = _make_user("tip_author2")
        tipper = _make_user("tipper2", balance=Decimal("0.50"))
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="余额不足"):
            TipService.send_tip(tipper, article.id, Decimal("1.00"))

    def test_tip_amount_too_small_raises(self):
        author = _make_user("tip_author3")
        tipper = _make_user("tipper3", balance=Decimal("10.00"))
        article = _make_article(author, status=ArticleStatus.PUBLISHED)
        with pytest.raises(ValueError, match="不能低于"):
            TipService.send_tip(tipper, article.id, Decimal("0.001"))

    def test_tip_nonexistent_article_raises(self):
        tipper = _make_user("tipper4", balance=Decimal("10.00"))
        with pytest.raises(ValueError, match="文章不存在"):
            TipService.send_tip(tipper, 99999, Decimal("1.00"))

    def test_tip_draft_article_raises(self):
        author = _make_user("tip_author4")
        tipper = _make_user("tipper5", balance=Decimal("10.00"))
        article = _make_article(author, status=ArticleStatus.DRAFT)
        with pytest.raises(ValueError, match="文章不存在"):
            TipService.send_tip(tipper, article.id, Decimal("1.00"))

    @patch("apps.workshop.services.NotificationService.send")
    @patch("apps.workshop.services.CreditService.add_credit", return_value=5)
    def test_tip_fee_calculation(self, _mock_credit, _mock_notify):
        """5% platform fee is deducted from recipient amount."""
        author = _make_user("tip_author5", balance=Decimal("0.00"))
        tipper = _make_user("tipper6", balance=Decimal("100.00"))
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        TipService.send_tip(tipper, article.id, Decimal("2.00"))

        tipper.refresh_from_db()
        author.refresh_from_db()
        # fee = 2.00 * 0.05 = 0.10; recipient gets 1.90
        assert tipper.balance == Decimal("98.00")
        assert author.balance == Decimal("1.90")


# ---------------------------------------------------------------------------
# SeriesService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSeriesCreate:
    """SeriesService.create()"""

    def test_valid_creation(self):
        author = _make_user("series_author")
        series = SeriesService.create(author, {
            "title": "入门系列教程",
            "description": "面向初学者的完整学习路径",
        })
        assert series.pk is not None
        assert series.title == "入门系列教程"
        assert series.author == author
        assert series.is_completed is False
        assert series.completion_rewarded is False

    def test_title_too_short_raises(self):
        author = _make_user("series_author2")
        with pytest.raises(ValueError, match="标题长度"):
            SeriesService.create(author, {"title": "AB"})

    def test_title_too_long_raises(self):
        author = _make_user("series_author3")
        with pytest.raises(ValueError, match="标题长度"):
            SeriesService.create(author, {"title": "X" * 201})


@pytest.mark.django_db
class TestSeriesReorder:
    """SeriesService.reorder_articles()"""

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_reorder_success(self, _mock_sync):
        author = _make_user("reorder_author")
        series = SeriesService.create(author, {"title": "排序测试系列"})

        a1 = _make_article(author, title="系列文章一号测试")
        a2 = _make_article(author, title="系列文章二号测试")
        a1.series = series
        a1.series_order = 1
        a1.save(update_fields=["series_id", "series_order"])
        a2.series = series
        a2.series_order = 2
        a2.save(update_fields=["series_id", "series_order"])

        SeriesService.reorder_articles(series, [a2.id, a1.id])
        a1.refresh_from_db()
        a2.refresh_from_db()
        assert a2.series_order == 1
        assert a1.series_order == 2

    def test_reorder_incomplete_list_raises(self):
        author = _make_user("reorder_author2")
        series = SeriesService.create(author, {"title": "排序测试系列二"})

        a1 = _make_article(author, title="系列文章测试标题")
        a1.series = series
        a1.series_order = 1
        a1.save(update_fields=["series_id", "series_order"])

        with pytest.raises(ValueError, match="排序列表必须完整包含"):
            SeriesService.reorder_articles(series, [])


@pytest.mark.django_db
class TestSeriesCompletionReward:
    """SeriesService.ensure_completion_reward()"""

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    @patch("apps.workshop.services.CreditService.add_credit", return_value=15)
    def test_reward_granted_with_three_published(self, _mock_credit, _mock_sync):
        author = _make_user("reward_author")
        series = SeriesService.create(author, {"title": "奖励测试系列标题"})

        # Create 3 published articles in the series
        for i in range(3):
            a = _make_article(
                author,
                title=f"系列奖励文章第{i+1}篇",
                status=ArticleStatus.PUBLISHED,
            )
            a.series = series
            a.series_order = i + 1
            a.save(update_fields=["series_id", "series_order"])

        with patch("apps.workshop.services.PaymentsService.create_deposit") as mock_deposit, \
             patch("apps.workshop.services.CreditService.adjust_credit") as mock_adjust:
            result = SeriesService.ensure_completion_reward(series)

        assert result is True
        series.refresh_from_db()
        assert series.is_completed is True
        assert series.completion_rewarded is True
        mock_deposit.assert_called_once_with(
            author, Decimal("1.00"),
            reference_id=f"series:{series.id}:completion-reward",
        )
        mock_adjust.assert_called_once_with(
            author, 30,
            reference_id=f"series:{series.id}:completion-reward",
        )

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_reward_not_granted_fewer_than_three(self, _mock_sync):
        author = _make_user("reward_author2")
        series = SeriesService.create(author, {"title": "不完整系列标题"})

        # Only 2 published articles
        for i in range(2):
            a = _make_article(
                author,
                title=f"不完整系列文章{i+1}",
                status=ArticleStatus.PUBLISHED,
            )
            a.series = series
            a.series_order = i + 1
            a.save(update_fields=["series_id", "series_order"])

        result = SeriesService.ensure_completion_reward(series)
        assert result is False
        series.refresh_from_db()
        assert series.completion_rewarded is False

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    @patch("apps.workshop.services.CreditService.add_credit", return_value=15)
    def test_reward_only_once(self, _mock_credit, _mock_sync):
        author = _make_user("reward_author3")
        series = SeriesService.create(author, {"title": "一次性奖励系列"})

        for i in range(3):
            a = _make_article(
                author,
                title=f"一次性奖励文章{i+1}",
                status=ArticleStatus.PUBLISHED,
            )
            a.series = series
            a.series_order = i + 1
            a.save(update_fields=["series_id", "series_order"])

        with patch("apps.workshop.services.PaymentsService.create_deposit"), \
             patch("apps.workshop.services.CreditService.adjust_credit"):
            first = SeriesService.ensure_completion_reward(series)
            second = SeriesService.ensure_completion_reward(series)

        assert first is True
        assert second is False


# ---------------------------------------------------------------------------
# Edge cases and integration-style scenarios
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestArticleServiceIntegration:
    """Cross-cutting scenarios across multiple service methods."""

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    @patch("apps.workshop.services.SearchService.remove_article", return_value=False)
    @patch("apps.workshop.services.CreditService.add_credit", return_value=15)
    def test_create_publish_archive_lifecycle(self, _mock_credit, _mock_remove, _mock_sync):
        user = _make_user("lifecycle_author")
        article = ArticleService.create(user, {
            "title": "生命周期测试文章",
            "content": _long_content(),
            "model_tags": ["gpt-5"],
        })
        assert article.status == ArticleStatus.DRAFT

        published = ArticleService.publish(article)
        assert published.status == ArticleStatus.PUBLISHED

        archived = ArticleService.archive(published)
        assert archived.status == ArticleStatus.ARCHIVED

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_content_sanitization_strips_script(self, _mock_sync):
        user = _make_user("sanitize_author")
        article = ArticleService.create(user, {
            "title": "安全测试文章标题",
            "content": '<p>安全内容</p><script>alert("xss")</script>',
            "model_tags": ["gpt-5"],
        })
        assert "<script>" not in article.content
        assert "安全内容" in article.content

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_custom_tags_limited_to_five(self, _mock_sync):
        user = _make_user("tags_author")
        article = ArticleService.create(user, {
            "title": "标签数量测试文章",
            "content": "内容",
            "model_tags": ["gpt-5"],
            "custom_tags": ["a", "b", "c", "d", "e"],
        })
        assert len(article.custom_tags) <= 5

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_custom_tags_over_five_silently_truncated(self, _mock_sync):
        """_clean_tags truncates to limit=5, so 6 unique tags become 5."""
        user = _make_user("tags_author2")
        article = ArticleService.create(user, {
            "title": "标签过多测试文章标题",
            "content": "内容",
            "model_tags": ["gpt-5"],
            "custom_tags": ["tag-a", "tag-b", "tag-c", "tag-d", "tag-e", "tag-f"],
        })
        assert len(article.custom_tags) == 5

    def test_should_collapse_comment_integration(self):
        """Verify should_collapse_comment delegate works."""
        author = _make_user("collapse_author")
        commenter = _make_user("collapse_commenter")
        article = _make_article(author, status=ArticleStatus.PUBLISHED)

        comment = ArticleService.add_comment(article, commenter, "测试评论")
        comment.net_votes = -2
        comment.save(update_fields=["net_votes"])
        assert ArticleService.should_collapse_comment(comment) is False

        comment.net_votes = -3
        comment.save(update_fields=["net_votes"])
        assert ArticleService.should_collapse_comment(comment) is True

    @patch("apps.workshop.services.SearchService.sync_article", return_value=False)
    def test_duplicate_tags_deduplicated(self, _mock_sync):
        user = _make_user("dedup_author")
        article = ArticleService.create(user, {
            "title": "去重标签测试文章",
            "content": "内容",
            "model_tags": ["gpt-5", "GPT-5", "gpt-5"],
            "custom_tags": ["tag", "TAG", "tag"],
        })
        assert len(article.model_tags) == 1
        assert len(article.custom_tags) == 1
