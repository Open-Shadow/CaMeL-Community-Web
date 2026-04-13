"""Skills Pydantic schemas."""
from typing import Optional, List
from ninja import Schema


class SkillCreateInput(Schema):
    name: str
    description: str
    category: str
    tags: List[str] = []
    pricing_model: str = "FREE"
    price: Optional[float] = None
    changelog: str = ""


class SkillUpdateInput(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    pricing_model: Optional[str] = None
    price: Optional[float] = None
    changelog: str = ""


class SkillOut(Schema):
    id: int
    name: str
    slug: str
    description: str
    category: str
    tags: List[str]
    pricing_model: str
    price: Optional[float]
    status: str
    is_featured: bool
    current_version: str
    total_calls: int
    avg_rating: float
    review_count: int
    rejection_reason: str
    readme_html: str
    package_size: int
    download_count: int
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str
    has_purchased: bool = False  # only present when authenticated


class SkillCallInput(Schema):
    input_text: str


class SkillCallOut(Schema):
    output_text: str
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
    version: str
    changelog: str
    status: str
    created_at: str


class SkillTrendingOut(Schema):
    id: int
    name: str
    slug: str
    description: str
    category: str
    pricing_model: str
    price: Optional[float]
    total_calls: int
    avg_rating: float
    review_count: int
    creator_name: str


class SkillRecommendationOut(SkillTrendingOut):
    recommendation_reason: str


class SkillUsagePreferenceInput(Schema):
    locked_version: str | None = None
    auto_follow_latest: bool = True


class SkillUsagePreferenceOut(Schema):
    skill_id: int
    locked_version: str | None = None
    auto_follow_latest: bool


class SkillPurchaseInput(Schema):
    pass


class SkillPurchaseOut(Schema):
    id: int
    skill_id: int
    paid_amount: float
    payment_type: str
    created_at: str


class SkillPurchaseDetailOut(Schema):
    """Full skill info with purchase metadata for the 'My Purchased Skills' page."""
    # Skill fields
    id: int
    name: str
    slug: str
    description: str
    category: str
    tags: List[str]
    pricing_model: str
    price: Optional[float]
    status: str
    is_featured: bool
    current_version: str
    total_calls: int
    avg_rating: float
    review_count: int
    rejection_reason: str
    readme_html: str
    package_size: int
    download_count: int
    creator_id: int
    creator_name: str
    created_at: str
    updated_at: str
    # Purchase metadata
    purchase_id: int
    paid_amount: float
    payment_type: str
    purchased_at: str


class SkillReportInput(Schema):
    reason: str
    detail: str = ""


class SkillReportOut(Schema):
    id: int
    skill_id: int
    reason: str
    detail: str
    created_at: str


class MessageOut(Schema):
    message: str


class PackageFileEntry(Schema):
    path: str
    size: int
    is_dir: bool
