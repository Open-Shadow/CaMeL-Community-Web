"""Workshop Pydantic schemas."""
from ninja import Schema


class ArticleCreateInput(Schema):
    title: str
    content: str
    difficulty: str
    article_type: str
    model_tags: list[str]
    custom_tags: list[str] = []
    related_skill_id: int | None = None
    series_id: int | None = None
    series_order: int | None = None


class ArticleUpdateInput(Schema):
    title: str | None = None
    content: str | None = None
    difficulty: str | None = None
    article_type: str | None = None
    model_tags: list[str] | None = None
    custom_tags: list[str] | None = None
    related_skill_id: int | None = None
    series_id: int | None = None
    series_order: int | None = None


class SeriesCreateInput(Schema):
    title: str
    description: str = ""
    cover_url: str = ""


class SeriesUpdateInput(Schema):
    title: str | None = None
    description: str | None = None
    cover_url: str | None = None


class SeriesReorderInput(Schema):
    article_ids: list[int]


class VoteInput(Schema):
    value: str


class VoteOut(Schema):
    net_votes: float
    my_vote: str | None = None


class CommentVoteInput(Schema):
    value: str


class CommentVoteOut(Schema):
    net_votes: int
    my_vote: str | None = None
    is_collapsed: bool


class CommentCreateInput(Schema):
    content: str
    parent_id: int | None = None


class PinCommentInput(Schema):
    comment_id: int


class ArticleAuthorOut(Schema):
    id: int
    username: str
    display_name: str
    level: str
    credit_score: int


class RelatedSkillOut(Schema):
    id: int
    name: str
    category: str
    pricing_model: str
    price_per_use: float | None = None
    total_calls: int
    avg_rating: float
    creator_name: str


class CommentReplyOut(Schema):
    id: int
    content: str
    net_votes: int
    is_pinned: bool
    is_collapsed: bool
    my_vote: str | None = None
    author: ArticleAuthorOut
    created_at: str
    updated_at: str


class CommentOut(Schema):
    id: int
    content: str
    net_votes: int
    is_pinned: bool
    is_collapsed: bool
    my_vote: str | None = None
    author: ArticleAuthorOut
    created_at: str
    updated_at: str
    replies: list[CommentReplyOut]


class ArticleSummaryOut(Schema):
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
    author: ArticleAuthorOut
    related_skill: RelatedSkillOut | None = None
    created_at: str
    updated_at: str
    published_at: str | None = None


class ArticleDetailOut(ArticleSummaryOut):
    content: str
    is_outdated: bool
    my_vote: str | None = None


class ArticleRecommendationOut(ArticleSummaryOut):
    recommendation_reason: str


class SeriesSummaryOut(Schema):
    id: int
    title: str
    description: str
    cover_url: str
    is_completed: bool
    completion_rewarded: bool
    article_count: int
    published_count: int
    author: ArticleAuthorOut
    created_at: str
    updated_at: str


class SeriesDetailOut(SeriesSummaryOut):
    articles: list[ArticleSummaryOut]


class MessageOut(Schema):
    message: str
