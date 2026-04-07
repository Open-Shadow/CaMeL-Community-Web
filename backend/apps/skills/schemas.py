"""Skills Pydantic schemas."""
from typing import Optional, List
from ninja import Schema


class SkillCreateInput(Schema):
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str = ""
    output_format: str = "text"
    example_input: str = ""
    example_output: str = ""
    category: str
    tags: List[str] = []
    pricing_model: str = "FREE"
    price_per_use: Optional[float] = None


class SkillUpdateInput(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    pricing_model: Optional[str] = None
    price_per_use: Optional[float] = None


class SkillOut(Schema):
    id: int
    name: str
    slug: str
    description: str
    system_prompt: str
    user_prompt_template: str
    output_format: str
    example_input: str
    example_output: str
    category: str
    tags: List[str]
    pricing_model: str
    price_per_use: Optional[float]
    status: str
    is_featured: bool
    current_version: int
    total_calls: int
    avg_rating: float
    review_count: int
    rejection_reason: str
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str


class SkillCallInput(Schema):
    input_text: str


class SkillCallOut(Schema):
    output_text: str
    amount_charged: float
    duration_ms: Optional[int]


class SkillReviewInput(Schema):
    rating: int
    comment: str = ""
    tags: List[str] = []


class SkillReviewOut(Schema):
    id: int
    rating: int
    comment: str
    tags: List[str]
    reviewer_id: int
    reviewer_name: str
    created_at: str


class SkillVersionOut(Schema):
    id: int
    version: int
    system_prompt: str
    user_prompt_template: str
    change_note: str
    is_major: bool
    created_at: str


class SkillTrendingOut(Schema):
    id: int
    name: str
    slug: str
    description: str
    category: str
    pricing_model: str
    price_per_use: Optional[float]
    total_calls: int
    avg_rating: float
    review_count: int
    creator_name: str


class SkillRecommendationOut(SkillTrendingOut):
    recommendation_reason: str


class SkillUsagePreferenceInput(Schema):
    locked_version: int | None = None
    auto_follow_latest: bool = True


class SkillUsagePreferenceOut(Schema):
    skill_id: int
    locked_version: int | None = None
    auto_follow_latest: bool


class MessageOut(Schema):
    message: str
