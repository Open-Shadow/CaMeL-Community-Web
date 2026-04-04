# 04 - API 接口设计

## 4.1 API 架构

本项目采用 **Django Ninja** 作为 API 层，提供基于 Pydantic 的自动校验与 OpenAPI 文档生成。所有业务接口遵循 RESTful 风格，统一前缀 `/api/v1/`。Webhook 端点独立于版本前缀。

### 通用约定

| 项 | 约定 |
|---|------|
| 协议 | HTTPS |
| 认证 | JWT Bearer Token（django-ninja `HttpBearer`） |
| 验证 | Pydantic Schema（请求 / 响应） |
| 错误格式 | HTTP 状态码 + 统一 `ErrorResponse` JSON |
| 分页 | Cursor-based（id cursor） |
| 时间格式 | ISO 8601 |
| 金额精度 | Decimal(12,2)，字符串传输 |
| API 版本 | `/api/v1/` |

### 认证与权限装饰器

```python
from ninja import Router
from ninja.security import HttpBearer
from functools import wraps

# ── JWT 认证 ──

class AuthBearer(HttpBearer):
    def authenticate(self, request, token: str):
        """验证 JWT，成功返回 user 对象，失败返回 None（自动 401）"""
        payload = verify_jwt_token(token)
        if payload is None:
            return None
        user = User.objects.filter(id=payload["user_id"], is_active=True).first()
        return user

auth = AuthBearer()

# ── 权限装饰器 ──

def public_api(func):
    """无需认证"""
    return func

def login_required(func):
    """需要有效 JWT"""
    # 通过 Django Ninja 的 auth 参数实现，此装饰器用于语义标记
    return func

def moderator_required(func):
    """需要版主（MODERATOR）或管理员角色"""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.auth.role not in ("MODERATOR", "ADMIN"):
            return 403, ErrorResponse(code="FORBIDDEN", message="需要版主权限")
        return func(request, *args, **kwargs)
    return wrapper

def admin_required(func):
    """需要管理员（ADMIN）角色"""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.auth.role != "ADMIN":
            return 403, ErrorResponse(code="FORBIDDEN", message="需要管理员权限")
        return func(request, *args, **kwargs)
    return wrapper
```

### Router 注册

```python
# project/api.py
from ninja import NinjaAPI

api = NinjaAPI(
    title="CaMeL Community API",
    version="1.0.0",
    urls_namespace="api",
)

api.add_router("/auth/",          auth_router,      tags=["认证"])
api.add_router("/users/",         user_router,      tags=["用户"])
api.add_router("/skills/",        skill_router,     tags=["技能市场"])
api.add_router("/bounties/",      bounty_router,    tags=["悬赏任务"])
api.add_router("/articles/",      article_router,   tags=["知识工坊"])
api.add_router("/series/",        series_router,    tags=["系列文章"])
api.add_router("/payments/",      payment_router,   tags=["支付"])
api.add_router("/admin/",         admin_router,     tags=["管理后台"])
api.add_router("/search/",        search_router,    tags=["搜索"])
api.add_router("/upload/",        upload_router,    tags=["文件上传"])

# urls.py
urlpatterns = [
    path("api/v1/", api.urls),
    path("api/webhooks/stripe/", stripe_webhook_view),
]
```

---

## 4.2 用户模块 (user_router)

### 4.2.1 认证相关

基于 **django-allauth** 提供注册 / 登录能力，配合 **djangorestframework-simplejwt** 签发 JWT。

```python
from ninja import Router, Schema
from pydantic import BaseModel, Field, EmailStr

auth_router = Router()

# ── Schemas ──

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8)
    invite_code: str | None = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int  # 秒

class RefreshIn(BaseModel):
    refresh_token: str

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class VerifyEmailIn(BaseModel):
    token: str

class MessageOut(BaseModel):
    message: str

# ── Endpoints ──

@auth_router.post("/register", response={201: TokenOut, 400: ErrorResponse, 409: ErrorResponse})
def register(request, body: RegisterIn):
    """注册新用户，返回 JWT Token"""
    ...

@auth_router.post("/login", response={200: TokenOut, 401: ErrorResponse})
def login(request, body: LoginIn):
    """邮箱 + 密码登录，返回 JWT Token"""
    ...

@auth_router.post("/logout", response={200: MessageOut}, auth=auth)
def logout(request):
    """使当前 refresh_token 失效"""
    ...

@auth_router.post("/token/refresh", response={200: TokenOut, 401: ErrorResponse})
def refresh_token(request, body: RefreshIn):
    """使用 refresh_token 换取新 access_token"""
    ...

@auth_router.post("/verify-email", response={200: MessageOut, 400: ErrorResponse})
def verify_email(request, body: VerifyEmailIn):
    """邮箱验证"""
    ...

@auth_router.post("/forgot-password", response={200: MessageOut})
def forgot_password(request, body: ForgotPasswordIn):
    """发送重置密码邮件"""
    ...

@auth_router.post("/reset-password", response={200: MessageOut, 400: ErrorResponse})
def reset_password(request, body: ResetPasswordIn):
    """重置密码"""
    ...
```

### 4.2.2 用户信息

```python
from ninja import Router
from pydantic import BaseModel, Field
from typing import Optional

user_router = Router()

# ── Schemas ──

class UserProfileOut(BaseModel):
    id: str
    username: str
    display_name: str
    avatar_url: str | None
    bio: str | None
    level: str          # 信用等级：新芽 / 工匠 / 专家 / 大师 / 宗师
    credit_score: int
    stats: "UserPublicStats"

class UserPublicStats(BaseModel):
    total_skills: int
    total_articles: int
    total_bounties: int

class UserMeOut(BaseModel):
    """当前用户完整信息（含私有字段）"""
    id: str
    username: str
    display_name: str
    email: str
    avatar_url: str | None
    bio: str | None
    level: str
    credit_score: int
    balance: str          # Decimal
    frozen_balance: str   # Decimal
    role: str
    created_at: str
    stats: "UserFullStats"

class UserFullStats(BaseModel):
    total_skills: int
    total_articles: int
    total_bounties: int
    total_earnings: str   # Decimal
    credit_score: int

class UpdateProfileIn(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=50)
    bio: str | None = Field(None, max_length=500)
    avatar_url: str | None = None

class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    content: str
    is_read: bool
    created_at: str

class CursorPaginationIn(BaseModel):
    cursor: str | None = None
    limit: int = Field(20, ge=1, le=50)

class PaginatedResponse(BaseModel):
    items: list
    next_cursor: str | None

class InviteCodeOut(BaseModel):
    code: str
    total_invites: int
    successful_invites: int

class CreditHistoryOut(BaseModel):
    id: str
    change: int
    reason: str
    created_at: str

# ── Endpoints ──

@user_router.get(
    "/{username}",
    response={200: UserProfileOut, 404: ErrorResponse},
)
def get_profile(request, username: str):
    """获取用户公开信息（displayName, avatar, level, creditScore, 统计数据）"""
    ...

@user_router.get(
    "/me",
    response=UserMeOut,
    auth=auth,
)
def get_me(request):
    """获取当前用户完整信息（含 balance, email 等私有字段）"""
    ...

@user_router.patch(
    "/me",
    response={200: UserMeOut, 400: ErrorResponse},
    auth=auth,
)
def update_profile(request, body: UpdateProfileIn):
    """更新当前用户资料"""
    ...

@user_router.get(
    "/me/stats",
    response=UserFullStats,
    auth=auth,
)
def get_my_stats(request):
    """返回：totalSkills, totalArticles, totalBounties, totalEarnings, creditScore"""
    ...

@user_router.get(
    "/me/notifications",
    response=PaginatedResponse,
    auth=auth,
)
def get_notifications(request, cursor: str = None, limit: int = 20, unread_only: bool = False):
    """获取分页通知列表"""
    ...

@user_router.patch(
    "/me/notifications/{notification_id}/read",
    response={200: MessageOut, 404: ErrorResponse},
    auth=auth,
)
def mark_notification_read(request, notification_id: str):
    """标记单条通知为已读"""
    ...

@user_router.post(
    "/me/notifications/read-all",
    response=MessageOut,
    auth=auth,
)
def mark_all_notifications_read(request):
    """标记所有通知为已读"""
    ...

@user_router.get(
    "/me/invite-code",
    response=InviteCodeOut,
    auth=auth,
)
def get_invite_code(request):
    """获取用户的邀请码 + 邀请统计"""
    ...

@user_router.get(
    "/me/credit-history",
    response=PaginatedResponse,
    auth=auth,
)
def get_credit_history(request, cursor: str = None, limit: int = 20):
    """获取信用分变动历史"""
    ...
```

---

## 4.3 Skill Marketplace 模块 (skill_router)

```python
from ninja import Router, File, UploadedFile
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

skill_router = Router()

# ── Enums ──

class SkillCategory(str, Enum):
    WRITING = "writing"
    CODING = "coding"
    TRANSLATION = "translation"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    EDUCATION = "education"
    BUSINESS = "business"
    OTHER = "other"

class SkillPricingModel(str, Enum):
    FREE = "free"
    PAY_PER_USE = "pay_per_use"

class SkillStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

class SkillSortBy(str, Enum):
    NEWEST = "newest"
    TRENDING = "trending"
    RATING = "rating"
    CALLS = "calls"

class ReviewSortBy(str, Enum):
    NEWEST = "newest"
    HIGHEST = "highest"
    LOWEST = "lowest"

# ── Request Schemas ──

class SkillCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=500)
    system_prompt: str = Field(min_length=10)
    user_prompt_template: str | None = None
    output_format: str | None = None
    example_input: str | None = None
    example_output: str | None = None
    category: SkillCategory
    tags: list[str] = Field(max_length=10)
    icon_url: str | None = None
    pricing_model: SkillPricingModel = SkillPricingModel.FREE
    price_per_use: str | None = None  # Decimal as string

class SkillUpdateIn(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=80)
    description: str | None = Field(None, min_length=10, max_length=500)
    system_prompt: str | None = Field(None, min_length=10)
    user_prompt_template: str | None = None
    output_format: str | None = None
    example_input: str | None = None
    example_output: str | None = None
    category: SkillCategory | None = None
    tags: list[str] | None = Field(None, max_length=10)
    price_per_use: str | None = None
    changelog: str | None = Field(None, max_length=500)

class SkillCallIn(BaseModel):
    user_input: str
    version: int | None = None  # 不传则用最新版本

class ReviewCreateIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    tags: list[str] | None = None
    comment: str | None = Field(None, max_length=200)

class ReviewUpdateIn(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    tags: list[str] | None = None
    comment: str | None = Field(None, max_length=200)

class SkillRejectIn(BaseModel):
    reason: str = Field(min_length=10, max_length=500)

class SetFeaturedIn(BaseModel):
    is_featured: bool

# ── Response Schemas ──

class SkillSummaryOut(BaseModel):
    id: str
    name: str
    description: str
    category: SkillCategory
    tags: list[str]
    pricing_model: SkillPricingModel
    price_per_use: str | None
    avg_rating: float
    total_calls: int
    author: "SkillAuthorOut"
    created_at: str

class SkillAuthorOut(BaseModel):
    id: str
    username: str
    display_name: str
    avatar_url: str | None
    level: str

class SkillDetailOut(SkillSummaryOut):
    system_prompt: str
    user_prompt_template: str | None
    output_format: str | None
    example_input: str | None
    example_output: str | None
    icon_url: str | None
    status: SkillStatus
    version: int
    review_summary: "ReviewSummaryOut"

class ReviewSummaryOut(BaseModel):
    total_reviews: int
    avg_rating: float
    rating_distribution: dict[str, int]  # {"1": 3, "2": 5, ...}

class SkillCallOut(BaseModel):
    result: str
    tokens_used: int
    cost: str  # Decimal

class ReviewOut(BaseModel):
    id: str
    user: "SkillAuthorOut"
    rating: int
    tags: list[str] | None
    comment: str | None
    created_at: str

class VersionOut(BaseModel):
    version: int
    changelog: str | None
    created_at: str

class SkillStatsOut(BaseModel):
    total_calls: int
    total_revenue: str
    avg_rating: float
    call_trend: list[dict]       # 近 30 天调用趋势
    rating_distribution: dict[str, int]

# ── Public Endpoints ──

@skill_router.get(
    "/",
    response=PaginatedResponse,
)
def list_skills(
    request,
    cursor: str = None,
    limit: int = 20,
    category: SkillCategory = None,
    tags: str = None,              # 逗号分隔
    pricing_model: SkillPricingModel = None,
    sort_by: SkillSortBy = SkillSortBy.TRENDING,
    search: str = None,
):
    """获取分页 Skill 列表（摘要信息）"""
    ...

@skill_router.get(
    "/{skill_id}",
    response={200: SkillDetailOut, 404: ErrorResponse},
)
def get_skill(request, skill_id: str):
    """获取 Skill 完整详情（含评价摘要、版本历史、关联文章）"""
    ...

@skill_router.get(
    "/featured/",
    response=list[SkillSummaryOut],
)
def get_featured_skills(request):
    """返回 6~8 个精选 Skill"""
    ...

@skill_router.get(
    "/trending/",
    response=list[SkillSummaryOut],
)
def get_trending_skills(request, limit: int = 10):
    """返回热门 Skill（近 7 天调用量 x 评分排序）"""
    ...

@skill_router.get(
    "/{skill_id}/reviews",
    response=PaginatedResponse,
)
def get_reviews(
    request,
    skill_id: str,
    cursor: str = None,
    limit: int = 20,
    sort_by: ReviewSortBy = ReviewSortBy.NEWEST,
):
    """获取分页评价列表"""
    ...

@skill_router.get(
    "/{skill_id}/versions",
    response=list[VersionOut],
)
def get_version_history(request, skill_id: str):
    """获取版本列表（最近 10 个）"""
    ...

# ── Protected Endpoints ──

@skill_router.post(
    "/",
    response={201: SkillDetailOut, 400: ErrorResponse},
    auth=auth,
)
def create_skill(request, body: SkillCreateIn):
    """创建 Skill（草稿状态），返回 Skill 详情"""
    ...

@skill_router.post(
    "/{skill_id}/submit-review",
    response={200: MessageOut, 400: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def submit_for_review(request, skill_id: str):
    """提交审核：DRAFT -> PENDING_REVIEW"""
    ...

@skill_router.patch(
    "/{skill_id}",
    response={200: SkillDetailOut, 400: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def update_skill(request, skill_id: str, body: SkillUpdateIn):
    """更新 Skill（自动创建新版本）"""
    ...

@skill_router.post(
    "/{skill_id}/call",
    response={200: SkillCallOut, 400: ErrorResponse, 402: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def call_skill(request, skill_id: str, body: SkillCallIn):
    """调用 Skill：扣费 + 记录调用 + 返回结果"""
    ...

@skill_router.post(
    "/{skill_id}/reviews",
    response={201: ReviewOut, 400: ErrorResponse, 409: ErrorResponse},
    auth=auth,
)
def add_review(request, skill_id: str, body: ReviewCreateIn):
    """添加评价（必须调用过该 Skill）"""
    ...

@skill_router.patch(
    "/{skill_id}/reviews/mine",
    response={200: ReviewOut, 400: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def update_review(request, skill_id: str, body: ReviewUpdateIn):
    """更新我的评价"""
    ...

@skill_router.get(
    "/mine/",
    response=PaginatedResponse,
    auth=auth,
)
def get_my_skills(request, status: SkillStatus = None, cursor: str = None, limit: int = 20):
    """获取我创建的 Skill 列表"""
    ...

@skill_router.get(
    "/{skill_id}/stats",
    response={200: SkillStatsOut, 404: ErrorResponse},
    auth=auth,
)
def get_my_skill_stats(request, skill_id: str):
    """获取 Skill 详细统计（调用趋势、收入、评分分布）"""
    ...

# ── Moderator Endpoints ──

@skill_router.post(
    "/{skill_id}/approve",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@moderator_required
def approve_skill(request, skill_id: str):
    """审核通过 Skill：PENDING_REVIEW -> APPROVED"""
    ...

@skill_router.post(
    "/{skill_id}/reject",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@moderator_required
def reject_skill(request, skill_id: str, body: SkillRejectIn):
    """审核拒绝 Skill：PENDING_REVIEW -> REJECTED"""
    ...

@skill_router.post(
    "/{skill_id}/suspend",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@moderator_required
def suspend_skill(request, skill_id: str, body: SkillRejectIn):
    """下架 Skill：APPROVED -> SUSPENDED"""
    ...

@skill_router.post(
    "/{skill_id}/set-featured",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@moderator_required
def set_featured(request, skill_id: str, body: SetFeaturedIn):
    """设置 / 取消精选"""
    ...
```

---

## 4.4 Bounty Board 模块 (bounty_router)

```python
from ninja import Router
from pydantic import BaseModel, Field
from enum import Enum

bounty_router = Router()

# ── Enums ──

class BountyType(str, Enum):
    SKILL_CREATION = "skill_creation"
    DATA_LABELING = "data_labeling"
    PROMPT_ENGINEERING = "prompt_engineering"
    TESTING = "testing"
    OTHER = "other"

class BountyStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

class BountySortBy(str, Enum):
    NEWEST = "newest"
    REWARD_HIGH = "reward_high"
    REWARD_LOW = "reward_low"
    DEADLINE = "deadline"

class ArbitrationVote(str, Enum):
    HUNTER_WINS = "hunter_wins"
    CREATOR_WINS = "creator_wins"
    PARTIAL = "partial"

# ── Request Schemas ──

class BountyCreateIn(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=20)
    type: BountyType
    reward: str             # Decimal as string，最低 $1
    deadline: str           # ISO 8601 datetime
    max_hunters: int = Field(1, ge=1, le=5)
    skill_requirements: str | None = Field(None, max_length=500)
    estimated_effort: str | None = None
    attachment_urls: list[str] | None = None

class BountyApplyIn(BaseModel):
    proposal: str = Field(min_length=10, max_length=1000)

class AcceptApplicationIn(BaseModel):
    application_id: str

class SubmitDeliverableIn(BaseModel):
    content: str = Field(min_length=10)
    attachment_urls: list[str] | None = None
    skill_link: str | None = None

class RequestRevisionIn(BaseModel):
    feedback: str = Field(min_length=10, max_length=1000)

class RejectDeliverableIn(BaseModel):
    reason: str = Field(min_length=10, max_length=500)

class BountyCommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

class RateCounterpartIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    quality_rating: int | None = Field(None, ge=1, le=5)
    communication_rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=200)

class ArbitrationStatementIn(BaseModel):
    statement: str = Field(min_length=10, max_length=500)

class ArbitrationVoteIn(BaseModel):
    vote: ArbitrationVote
    partial_percent: int | None = Field(None, ge=0, le=100)

class ArbitrationAppealIn(BaseModel):
    reason: str = Field(min_length=10, max_length=500)

# ── Response Schemas ──

class BountySummaryOut(BaseModel):
    id: str
    title: str
    type: BountyType
    status: BountyStatus
    reward: str
    deadline: str
    max_hunters: int
    application_count: int
    creator: "SkillAuthorOut"
    created_at: str

class BountyDetailOut(BountySummaryOut):
    description: str
    skill_requirements: str | None
    estimated_effort: str | None
    attachment_urls: list[str] | None
    timeline: list["TimelineEventOut"]

class TimelineEventOut(BaseModel):
    event: str
    timestamp: str
    actor: str | None

class ApplicationOut(BaseModel):
    id: str
    user: "SkillAuthorOut"
    proposal: str
    status: str
    created_at: str

class CommentOut(BaseModel):
    id: str
    user: "SkillAuthorOut"
    content: str
    created_at: str

# ── Public Endpoints ──

@bounty_router.get(
    "/",
    response=PaginatedResponse,
)
def list_bounties(
    request,
    cursor: str = None,
    limit: int = 20,
    type: BountyType = None,
    status: str = None,           # "open" | "in_progress" | "completed"
    min_reward: str = None,
    max_reward: str = None,
    sort_by: BountySortBy = BountySortBy.NEWEST,
    search: str = None,
):
    """获取分页悬赏列表"""
    ...

@bounty_router.get(
    "/{bounty_id}",
    response={200: BountyDetailOut, 404: ErrorResponse},
)
def get_bounty(request, bounty_id: str):
    """获取完整悬赏详情（含申请人数、状态时间线）"""
    ...

@bounty_router.get(
    "/{bounty_id}/comments",
    response=PaginatedResponse,
)
def get_bounty_comments(request, bounty_id: str, cursor: str = None, limit: int = 20):
    """获取悬赏评论列表"""
    ...

# ── Protected Endpoints ──

@bounty_router.post(
    "/",
    response={201: BountyDetailOut, 400: ErrorResponse, 402: ErrorResponse},
    auth=auth,
)
def create_bounty(request, body: BountyCreateIn):
    """
    创建悬赏 + 冻结 $，返回悬赏详情。
    前置检查：余额 >= reward, 信用分 >= 50（发布门槛）
    """
    ...

@bounty_router.post(
    "/{bounty_id}/apply",
    response={201: ApplicationOut, 400: ErrorResponse, 409: ErrorResponse},
    auth=auth,
)
def apply_bounty(request, bounty_id: str, body: BountyApplyIn):
    """
    申请接单。
    前置检查：信用分 >= 50, 未被冻结, 超时次数 < 3
    """
    ...

@bounty_router.post(
    "/{bounty_id}/accept",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def accept_application(request, bounty_id: str, body: AcceptApplicationIn):
    """发布者确认接单者"""
    ...

@bounty_router.post(
    "/{bounty_id}/deliver",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def submit_deliverable(request, bounty_id: str, body: SubmitDeliverableIn):
    """接单者提交交付物"""
    ...

@bounty_router.post(
    "/{bounty_id}/approve",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def approve_deliverable(request, bounty_id: str):
    """发布者验收通过，触发结算"""
    ...

@bounty_router.post(
    "/{bounty_id}/request-revision",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def request_revision(request, bounty_id: str, body: RequestRevisionIn):
    """要求修改（<= 3 轮）"""
    ...

@bounty_router.post(
    "/{bounty_id}/reject",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def reject_deliverable(request, bounty_id: str, body: RejectDeliverableIn):
    """拒绝验收，进入争议流程"""
    ...

@bounty_router.post(
    "/{bounty_id}/comments",
    response={201: CommentOut, 400: ErrorResponse},
    auth=auth,
)
def add_bounty_comment(request, bounty_id: str, body: BountyCommentIn):
    """添加评论"""
    ...

@bounty_router.post(
    "/{bounty_id}/cancel",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def cancel_bounty(request, bounty_id: str):
    """取消悬赏（仅 OPEN 状态可取消），解冻 $"""
    ...

@bounty_router.post(
    "/{bounty_id}/rate",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def rate_counterpart(request, bounty_id: str, body: RateCounterpartIn):
    """双方互评"""
    ...

@bounty_router.get(
    "/mine/",
    response=PaginatedResponse,
    auth=auth,
)
def get_my_bounties(
    request,
    role: str = "creator",       # "creator" | "hunter"
    status: BountyStatus = None,
    cursor: str = None,
    limit: int = 20,
):
    """获取我的悬赏列表（按角色筛选）"""
    ...

# ── Arbitration Endpoints ──

@bounty_router.post(
    "/{bounty_id}/arbitration/statement",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def submit_arbitration_statement(request, bounty_id: str, body: ArbitrationStatementIn):
    """提交仲裁陈述"""
    ...

@bounty_router.post(
    "/arbitrations/{arbitration_id}/vote",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def vote_arbitration(request, arbitration_id: str, body: ArbitrationVoteIn):
    """仲裁员投票（需 ⚡专家 级以上）"""
    ...

@bounty_router.post(
    "/arbitrations/{arbitration_id}/appeal",
    response={200: MessageOut, 400: ErrorResponse, 402: ErrorResponse},
    auth=auth,
)
def appeal_arbitration(request, arbitration_id: str, body: ArbitrationAppealIn):
    """上诉（扣 $0.50 上诉费）"""
    ...
```

---

## 4.5 Workshop 模块 (article_router / series_router)

```python
from ninja import Router
from pydantic import BaseModel, Field
from enum import Enum

article_router = Router()
series_router = Router()

# ── Enums ──

class ArticleDifficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class ArticleContentType(str, Enum):
    TUTORIAL = "tutorial"
    EXPERIENCE = "experience"
    COMPARISON = "comparison"
    WORKFLOW = "workflow"

class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ArticleSortBy(str, Enum):
    NEWEST = "newest"
    HOTTEST = "hottest"
    FEATURED = "featured"

class VoteValue(str, Enum):
    UP = "up"
    DOWN = "down"

class TipPeriod(str, Enum):
    WEEK = "week"
    MONTH = "month"
    ALL = "all"

# ── Request Schemas ──

class ArticleCreateIn(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    content: str = Field(min_length=500, max_length=10000)  # Markdown
    difficulty: ArticleDifficulty
    content_type: ArticleContentType
    model_tags: list[str] = Field(min_length=1)
    custom_tags: list[str] | None = Field(None, max_length=5)
    linked_skill_ids: list[str] | None = None
    series_id: str | None = None
    series_order: int | None = None

class ArticleUpdateIn(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=120)
    content: str | None = Field(None, min_length=500, max_length=10000)
    difficulty: ArticleDifficulty | None = None
    content_type: ArticleContentType | None = None
    model_tags: list[str] | None = None
    custom_tags: list[str] | None = Field(None, max_length=5)
    linked_skill_ids: list[str] | None = None

class VoteIn(BaseModel):
    value: VoteValue

class CommentCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    parent_id: str | None = None  # 回复某条评论

class PinCommentIn(BaseModel):
    comment_id: str

class TipIn(BaseModel):
    amount: str  # Decimal: "0.10", "0.30", "0.50", "1.00" 或自定义

class SeriesCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(None, max_length=500)

class SeriesUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    is_complete: bool | None = None

class ReorderSeriesIn(BaseModel):
    article_ids: list[str]  # 有序 ID 列表

class SetFeaturedArticleIn(BaseModel):
    is_featured: bool

# ── Response Schemas ──

class ArticleSummaryOut(BaseModel):
    id: str
    title: str
    difficulty: ArticleDifficulty
    content_type: ArticleContentType
    model_tags: list[str]
    custom_tags: list[str] | None
    vote_score: int
    comment_count: int
    is_featured: bool
    author: "SkillAuthorOut"
    created_at: str

class ArticleDetailOut(ArticleSummaryOut):
    content: str             # Markdown
    status: ArticleStatus
    linked_skill_ids: list[str] | None
    series_id: str | None
    series_order: int | None
    my_vote: str | None      # "up" | "down" | null（需登录才有值）
    tip_total: str           # Decimal

class ArticleCommentOut(BaseModel):
    id: str
    user: "SkillAuthorOut"
    content: str
    parent_id: str | None
    is_pinned: bool
    created_at: str

class SeriesOut(BaseModel):
    id: str
    title: str
    description: str | None
    is_complete: bool
    article_count: int
    author: "SkillAuthorOut"
    created_at: str

class SeriesDetailOut(SeriesOut):
    articles: list[ArticleSummaryOut]

class TipLeaderboardItemOut(BaseModel):
    rank: int
    article: "ArticleSummaryOut"
    total_tips: str  # Decimal

# ── Public Endpoints ──

@article_router.get(
    "/",
    response=PaginatedResponse,
)
def list_articles(
    request,
    cursor: str = None,
    limit: int = 20,
    difficulty: ArticleDifficulty = None,
    content_type: ArticleContentType = None,
    model_tag: str = None,
    custom_tag: str = None,
    sort_by: ArticleSortBy = ArticleSortBy.NEWEST,
    search: str = None,
):
    """获取分页文章列表"""
    ...

@article_router.get(
    "/{article_id}",
    response={200: ArticleDetailOut, 404: ErrorResponse},
)
def get_article(request, article_id: str):
    """获取文章完整内容 + 作者信息 + 投票状态 + 关联 Skill"""
    ...

@article_router.get(
    "/featured/",
    response=list[ArticleSummaryOut],
)
def get_featured_articles(request, limit: int = 5):
    """获取精选文章列表"""
    ...

@article_router.get(
    "/{article_id}/comments",
    response=PaginatedResponse,
)
def get_article_comments(request, article_id: str, cursor: str = None, limit: int = 20):
    """获取文章评论列表"""
    ...

@article_router.get(
    "/tip-leaderboard/",
    response=list[TipLeaderboardItemOut],
)
def get_tip_leaderboard(request, period: TipPeriod = TipPeriod.WEEK):
    """获取打赏排行榜"""
    ...

# ── Protected Endpoints ──

@article_router.post(
    "/",
    response={201: ArticleDetailOut, 400: ErrorResponse},
    auth=auth,
)
def create_article(request, body: ArticleCreateIn):
    """创建文章（草稿状态）"""
    ...

@article_router.patch(
    "/{article_id}",
    response={200: ArticleDetailOut, 400: ErrorResponse, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def update_article(request, article_id: str, body: ArticleUpdateIn):
    """更新文章（重置时间衰减因子）"""
    ...

@article_router.post(
    "/{article_id}/publish",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def publish_article(request, article_id: str):
    """发布文章：DRAFT -> PUBLISHED"""
    ...

@article_router.delete(
    "/{article_id}",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def delete_article(request, article_id: str):
    """软删除文章"""
    ...

@article_router.post(
    "/{article_id}/vote",
    response={200: MessageOut, 400: ErrorResponse},
    auth=auth,
)
def vote_article(request, article_id: str, body: VoteIn):
    """投票（有用/无用），权重按信用等级"""
    ...

@article_router.delete(
    "/{article_id}/vote",
    response={200: MessageOut, 404: ErrorResponse},
    auth=auth,
)
def remove_vote(request, article_id: str):
    """取消投票"""
    ...

@article_router.post(
    "/{article_id}/comments",
    response={201: ArticleCommentOut, 400: ErrorResponse},
    auth=auth,
)
def add_comment(request, article_id: str, body: CommentCreateIn):
    """添加评论（支持回复）"""
    ...

@article_router.post(
    "/{article_id}/pin-comment",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
def pin_comment(request, article_id: str, body: PinCommentIn):
    """置顶评论（仅文章作者可操作）"""
    ...

@article_router.post(
    "/{article_id}/tip",
    response={200: MessageOut, 400: ErrorResponse, 402: ErrorResponse},
    auth=auth,
)
def tip_article(request, article_id: str, body: TipIn):
    """打赏：扣减打赏者余额 + 增加作者余额 + 信用分"""
    ...

@article_router.get(
    "/mine/",
    response=PaginatedResponse,
    auth=auth,
)
def get_my_articles(request, status: ArticleStatus = None, cursor: str = None, limit: int = 20):
    """获取我的文章列表"""
    ...

# ── Moderator Endpoints ──

@article_router.post(
    "/{article_id}/set-featured",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@moderator_required
def feature_article(request, article_id: str, body: SetFeaturedArticleIn):
    """加精：作者 +20 信用分 + $0.50"""
    ...

@article_router.post(
    "/{article_id}/archive",
    response={200: MessageOut, 403: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@moderator_required
def archive_article(request, article_id: str):
    """归档文章"""
    ...

# ═══════════════════════════════════
#  系列文章 (series_router)
# ═══════════════════════════════════

@series_router.get(
    "/{series_id}",
    response={200: SeriesDetailOut, 404: ErrorResponse},
)
def get_series(request, series_id: str):
    """获取系列信息 + 文章目录"""
    ...

@series_router.post(
    "/",
    response={201: SeriesOut, 400: ErrorResponse},
    auth=auth,
)
def create_series(request, body: SeriesCreateIn):
    """创建系列"""
    ...

@series_router.patch(
    "/{series_id}",
    response={200: SeriesOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def update_series(request, series_id: str, body: SeriesUpdateIn):
    """更新系列信息"""
    ...

@series_router.post(
    "/{series_id}/reorder",
    response={200: MessageOut, 400: ErrorResponse, 403: ErrorResponse},
    auth=auth,
)
def reorder_series_articles(request, series_id: str, body: ReorderSeriesIn):
    """重新排序系列中的文章"""
    ...
```

---

## 4.6 支付模块 (payment_router)

```python
from ninja import Router
from pydantic import BaseModel, Field
from enum import Enum

payment_router = Router()

# ── Enums ──

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    SKILL_PURCHASE = "skill_purchase"
    SKILL_EARNING = "skill_earning"
    BOUNTY_FREEZE = "bounty_freeze"
    BOUNTY_RELEASE = "bounty_release"
    BOUNTY_EARNING = "bounty_earning"
    TIP_SENT = "tip_sent"
    TIP_RECEIVED = "tip_received"
    ARBITRATION_FEE = "arbitration_fee"
    REFUND = "refund"

class EarningsPeriod(str, Enum):
    D7 = "7d"
    D30 = "30d"
    D90 = "90d"
    ALL = "all"

# ── Schemas ──

class DepositSessionIn(BaseModel):
    amount: str  # 充值金额（$）

class DepositSessionOut(BaseModel):
    session_url: str
    session_id: str

class BalanceOut(BaseModel):
    available: str   # "12.50"
    frozen: str      # "5.00"
    total: str       # "17.50"

class TransactionOut(BaseModel):
    id: str
    type: TransactionType
    amount: str
    description: str
    created_at: str

class EarningsReportOut(BaseModel):
    period: str
    total_earnings: str
    skill_earnings: str
    bounty_earnings: str
    tip_earnings: str
    daily_breakdown: list[dict]

# ── Protected Endpoints ──

@payment_router.post(
    "/deposit-session",
    response={200: DepositSessionOut, 400: ErrorResponse},
    auth=auth,
)
def create_deposit_session(request, body: DepositSessionIn):
    """创建 Stripe Checkout Session，返回 sessionUrl"""
    ...

@payment_router.get(
    "/transactions",
    response=PaginatedResponse,
    auth=auth,
)
def get_transaction_history(
    request,
    cursor: str = None,
    limit: int = 20,
    type: TransactionType = None,
):
    """获取交易记录"""
    ...

@payment_router.get(
    "/balance",
    response=BalanceOut,
    auth=auth,
)
def get_balance(request):
    """获取余额：{ available, frozen, total }"""
    ...

@payment_router.get(
    "/earnings-report",
    response=EarningsReportOut,
    auth=auth,
)
def get_earnings_report(request, period: EarningsPeriod = EarningsPeriod.D30):
    """获取收入统计（Skill 收入、悬赏收入、打赏收入分类）"""
    ...
```

### Stripe Webhook（独立于版本前缀）

```python
# POST /api/webhooks/stripe/
# 不走 Django Ninja Router，直接注册为 Django View

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe

@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    """
    处理 Stripe 回调（充值到账）。
    验证签名 → 解析事件 → 更新用户余额 + 邀请奖励。
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        # 处理充值到账逻辑（事务）
        ...

    return HttpResponse(status=200)
```

---

## 4.7 管理后台模块 (admin_router)

```python
from ninja import Router
from pydantic import BaseModel, Field
from enum import Enum

admin_router = Router()

# ── Enums ──

class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class UserLevel(str, Enum):
    SPROUT = "sprout"        # 新芽
    ARTISAN = "artisan"      # 工匠
    EXPERT = "expert"        # 专家
    MASTER = "master"        # 大师
    GRANDMASTER = "grandmaster"  # 宗师

# ── Schemas ──

class DashboardOut(BaseModel):
    total_users: int
    new_users_today: int
    total_skills: int
    total_bounties: int
    total_articles: int
    total_revenue: str         # Decimal
    pending_reviews: int
    active_disputes: int

class AdminUserOut(BaseModel):
    id: str
    username: str
    display_name: str
    email: str
    role: UserRole
    level: UserLevel
    credit_score: int
    balance: str
    is_banned: bool
    created_at: str

class UpdateUserRoleIn(BaseModel):
    role: UserRole

class BanUserIn(BaseModel):
    reason: str = Field(min_length=10)

class FinanceReportOut(BaseModel):
    period: str
    total_deposits: str
    total_fees: str
    circulation: str

class ResolveAppealIn(BaseModel):
    result: ArbitrationVote
    partial_percent: int | None = None
    reason: str

class DisputeOut(BaseModel):
    id: str
    bounty_id: str
    bounty_title: str
    creator: "SkillAuthorOut"
    hunter: "SkillAuthorOut"
    status: str
    created_at: str

# ── Admin Endpoints（所有接口需 admin 权限）──

@admin_router.get(
    "/dashboard",
    response=DashboardOut,
    auth=auth,
)
@admin_required
def get_dashboard(request):
    """
    平台概览数据：
    totalUsers, newUsersToday, totalSkills, totalBounties,
    totalArticles, totalRevenue, pendingReviews, activeDisputes
    """
    ...

# ── 用户管理 ──

@admin_router.get(
    "/users",
    response=PaginatedResponse,
    auth=auth,
)
@admin_required
def list_users(
    request,
    cursor: str = None,
    limit: int = 20,
    search: str = None,
    role: UserRole = None,
    level: UserLevel = None,
):
    """管理员查看用户列表"""
    ...

@admin_router.patch(
    "/users/{user_id}/role",
    response={200: MessageOut, 400: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@admin_required
def update_user_role(request, user_id: str, body: UpdateUserRoleIn):
    """修改用户角色"""
    ...

@admin_router.post(
    "/users/{user_id}/ban",
    response={200: MessageOut, 400: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@admin_required
def ban_user(request, user_id: str, body: BanUserIn):
    """封禁用户"""
    ...

@admin_router.post(
    "/users/{user_id}/unban",
    response={200: MessageOut, 404: ErrorResponse},
    auth=auth,
)
@admin_required
def unban_user(request, user_id: str):
    """解封用户"""
    ...

# ── Skill 审核 ──

@admin_router.get(
    "/skills/pending",
    response=PaginatedResponse,
    auth=auth,
)
@admin_required
def get_pending_skills(request, cursor: str = None, limit: int = 20):
    """获取待审核 Skill 列表"""
    ...

# ── 内容管理 ──

@admin_router.get(
    "/articles/pending-featured",
    response=list[ArticleSummaryOut],
    auth=auth,
)
@admin_required
def get_pending_featured(request):
    """获取待加精文章队列（净票数 >= 10）"""
    ...

# ── 财务 ──

@admin_router.get(
    "/finance/report",
    response=FinanceReportOut,
    auth=auth,
)
@admin_required
def get_finance_report(request, period: str = "30d"):
    """获取财务报表：充值总额、手续费收入、$ 流通量"""
    ...

# ── 争议管理 ──

@admin_router.get(
    "/disputes",
    response=list[DisputeOut],
    auth=auth,
)
@admin_required
def get_active_disputes(request):
    """获取活跃争议列表"""
    ...

@admin_router.post(
    "/disputes/{arbitration_id}/resolve",
    response={200: MessageOut, 400: ErrorResponse, 404: ErrorResponse},
    auth=auth,
)
@admin_required
def resolve_appeal(request, arbitration_id: str, body: ResolveAppealIn):
    """终审裁决"""
    ...
```

---

## 4.8 搜索模块 (search_router)

```python
from ninja import Router
from pydantic import BaseModel, Field
from enum import Enum

search_router = Router()

# ── Enums ──

class SearchType(str, Enum):
    ALL = "all"
    SKILL = "skill"
    ARTICLE = "article"
    BOUNTY = "bounty"

# ── Schemas ──

class SearchResultOut(BaseModel):
    type: str           # "skill" | "article" | "bounty"
    id: str
    title: str
    snippet: str
    score: float

class GlobalSearchOut(BaseModel):
    results: list[SearchResultOut]
    total: int

class SuggestOut(BaseModel):
    suggestions: list[str]

# ── Public Endpoints ──

@search_router.get(
    "/",
    response=GlobalSearchOut,
)
def global_search(
    request,
    q: str,
    type: SearchType = SearchType.ALL,
    limit: int = 10,
):
    """全局搜索（Meilisearch）"""
    ...

@search_router.get(
    "/suggest",
    response=SuggestOut,
)
def search_suggest(request, q: str):
    """搜索建议 / 自动补全"""
    ...
```

---

## 4.9 文件上传 (upload_router)

```python
from ninja import Router, File, UploadedFile
from pydantic import BaseModel
from enum import Enum

upload_router = Router()

# ── Enums ──

class UploadType(str, Enum):
    AVATAR = "avatar"
    ATTACHMENT = "attachment"
    SKILL_ICON = "skill_icon"

# ── Schemas ──

class UploadOut(BaseModel):
    url: str
    key: str

# ── 上传限制 ──
# avatar:     最大 2MB,  仅 jpg/png/webp
# attachment: 最大 10MB, 允许 jpg/png/pdf/zip/txt/md
# skill_icon: 最大 1MB,  仅 jpg/png/svg/webp

UPLOAD_LIMITS = {
    UploadType.AVATAR: {
        "max_size": 2 * 1024 * 1024,
        "allowed_types": {"image/jpeg", "image/png", "image/webp"},
    },
    UploadType.ATTACHMENT: {
        "max_size": 10 * 1024 * 1024,
        "allowed_types": {
            "image/jpeg", "image/png", "application/pdf",
            "application/zip", "text/plain", "text/markdown",
        },
    },
    UploadType.SKILL_ICON: {
        "max_size": 1 * 1024 * 1024,
        "allowed_types": {"image/jpeg", "image/png", "image/svg+xml", "image/webp"},
    },
}

@upload_router.post(
    "/",
    response={200: UploadOut, 400: ErrorResponse, 413: ErrorResponse},
    auth=auth,
)
def upload_file(request, file: UploadedFile = File(...), type: UploadType = UploadType.ATTACHMENT):
    """
    上传文件到 Cloudflare R2 / AWS S3。
    Content-Type: multipart/form-data

    根据 type 参数校验文件大小和 MIME 类型，通过后上传至对象存储，返回 URL 和 key。
    """
    limits = UPLOAD_LIMITS[type]
    if file.size > limits["max_size"]:
        return 413, ErrorResponse(code="FILE_TOO_LARGE", message="文件超过大小限制")
    if file.content_type not in limits["allowed_types"]:
        return 400, ErrorResponse(code="INVALID_FILE_TYPE", message="不支持的文件类型")

    # 上传至对象存储...
    url, key = upload_to_storage(file, type)
    return UploadOut(url=url, key=key)
```

---

## 4.10 错误处理规范

### 统一错误响应格式

```python
from pydantic import BaseModel
from typing import Optional

class ErrorResponse(BaseModel):
    code: str            # 错误码（大写下划线）
    message: str         # 用户可读的错误信息
    details: dict | None = None  # 开发调试信息（生产环境不返回）
```

### HTTP 状态码映射

| HTTP 状态码 | 含义 | 使用场景 |
|------------|------|---------|
| 400 Bad Request | 请求参数错误 | Pydantic 校验失败、业务规则不满足 |
| 401 Unauthorized | 未认证 | JWT 缺失或过期 |
| 402 Payment Required | 余额不足 | 扣费操作余额不够 |
| 403 Forbidden | 无权限 | 角色不满足、非资源所有者 |
| 404 Not Found | 资源不存在 | ID 查无记录 |
| 409 Conflict | 冲突 | 重复操作（已评价、已申请） |
| 413 Payload Too Large | 请求体过大 | 文件上传超限 |
| 429 Too Many Requests | 请求过频 | 触发速率限制 |
| 500 Internal Server Error | 服务器内部错误 | 未预期异常 |

### 全局异常处理

```python
from ninja import NinjaAPI
from ninja.errors import ValidationError as NinjaValidationError
from django.http import JsonResponse

api = NinjaAPI(...)

@api.exception_handler(NinjaValidationError)
def validation_error_handler(request, exc):
    return JsonResponse(
        {
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "details": exc.errors,
        },
        status=400,
    )

@api.exception_handler(Exception)
def generic_error_handler(request, exc):
    # 生产环境不暴露详情
    return JsonResponse(
        {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
        },
        status=500,
    )
```

### 常见业务错误码

```python
# 业务错误码常量（与 ErrorResponse.code 对应）
BUSINESS_ERRORS = {
    "INSUFFICIENT_BALANCE": "余额不足",
    "INSUFFICIENT_CREDIT": "信用分不足",
    "BOUNTY_FROZEN": "悬赏板功能已被冻结",
    "SKILL_NOT_APPROVED": "Skill 尚未审核通过",
    "ALREADY_REVIEWED": "已经评价过该 Skill",
    "MUST_CALL_FIRST": "必须先调用过该 Skill 才能评价",
    "BOUNTY_NOT_OPEN": "该悬赏已不接受申请",
    "MAX_REVISION_REACHED": "已达到最大修改轮次",
    "ARTICLE_TOO_SHORT": "文章字数不满足要求",
    "APPEAL_ALREADY_USED": "上诉机会已用完",
}

# 使用示例
from django.http import JsonResponse

def raise_business_error(code: str, status: int = 400) -> JsonResponse:
    return JsonResponse(
        {
            "code": code,
            "message": BUSINESS_ERRORS.get(code, "未知错误"),
        },
        status=status,
    )
```

---

## 4.11 Rate Limiting

基于 **django-ratelimit** 实现，按用户 IP（匿名）或用户 ID（已认证）进行限流。

| 端点类别 | 限制 | 窗口 | 装饰器示例 |
|---------|------|------|----------|
| 公共查询 | 60 次 | 1 分钟 | `@ratelimit(key="ip", rate="60/m")` |
| 认证操作（登录/注册） | 5 次 | 1 分钟 | `@ratelimit(key="ip", rate="5/m")` |
| 创建/修改操作 | 30 次 | 1 分钟 | `@ratelimit(key="user", rate="30/m")` |
| Skill 调用 | 100 次 | 1 分钟 | `@ratelimit(key="user", rate="100/m")` |
| 文件上传 | 10 次 | 1 分钟 | `@ratelimit(key="user", rate="10/m")` |
| 支付操作 | 5 次 | 1 分钟 | `@ratelimit(key="user", rate="5/m")` |
| 搜索 | 30 次 | 1 分钟 | `@ratelimit(key="ip", rate="30/m")` |

### 使用示例

```python
from django_ratelimit.decorators import ratelimit

@skill_router.post("/{skill_id}/call", response=..., auth=auth)
@ratelimit(key="user", rate="100/m", method="POST", block=True)
def call_skill(request, skill_id: str, body: SkillCallIn):
    ...
```

超出限制时返回 `429 Too Many Requests`：

```json
{
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "请求过于频繁，请稍后重试"
}
```

---

## 4.12 Cursor-based 分页实现

所有列表接口统一采用 Cursor-based 分页（基于 ID），避免 OFFSET 在大数据量下的性能问题。

### 通用分页 Schema

```python
from pydantic import BaseModel, Field
from typing import TypeVar, Generic

T = TypeVar("T")

class CursorPaginationIn(BaseModel):
    cursor: str | None = None
    limit: int = Field(20, ge=1, le=50)

class CursorPaginatedResponse(BaseModel):
    items: list          # 实际业务数据列表
    next_cursor: str | None   # 下一页 cursor（null 表示无更多数据）
    has_more: bool
```

### Django ORM 分页工具

```python
from django.db.models import QuerySet

def paginate_queryset(
    queryset: QuerySet,
    cursor: str | None,
    limit: int,
    order_field: str = "-created_at",
    cursor_field: str = "id",
) -> dict:
    """
    通用 Cursor-based 分页。
    返回 {"items": [...], "next_cursor": "xxx" | None, "has_more": bool}
    """
    if cursor:
        queryset = queryset.filter(**{f"{cursor_field}__lt": cursor})

    queryset = queryset.order_by(order_field)
    items = list(queryset[:limit + 1])

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = str(getattr(items[-1], cursor_field)) if has_more and items else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
```

### 使用示例

```python
@skill_router.get("/", response=CursorPaginatedResponse)
def list_skills(request, cursor: str = None, limit: int = 20, ...):
    qs = Skill.objects.filter(status=SkillStatus.APPROVED)
    # ... 应用筛选条件 ...
    result = paginate_queryset(qs, cursor=cursor, limit=limit)
    return CursorPaginatedResponse(
        items=[SkillSummaryOut.from_orm(s) for s in result["items"]],
        next_cursor=result["next_cursor"],
        has_more=result["has_more"],
    )
```

---

## 4.13 API 端点速查表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| **认证** | | | |
| POST | `/api/v1/auth/register` | Public | 注册 |
| POST | `/api/v1/auth/login` | Public | 登录 |
| POST | `/api/v1/auth/logout` | Login | 登出 |
| POST | `/api/v1/auth/token/refresh` | Public | 刷新 Token |
| POST | `/api/v1/auth/verify-email` | Public | 邮箱验证 |
| POST | `/api/v1/auth/forgot-password` | Public | 忘记密码 |
| POST | `/api/v1/auth/reset-password` | Public | 重置密码 |
| **用户** | | | |
| GET | `/api/v1/users/me` | Login | 获取当前用户信息 |
| PATCH | `/api/v1/users/me` | Login | 更新个人资料 |
| GET | `/api/v1/users/me/stats` | Login | 获取个人统计 |
| GET | `/api/v1/users/me/notifications` | Login | 获取通知列表 |
| PATCH | `/api/v1/users/me/notifications/{id}/read` | Login | 标记通知已读 |
| POST | `/api/v1/users/me/notifications/read-all` | Login | 全部标记已读 |
| GET | `/api/v1/users/me/invite-code` | Login | 获取邀请码 |
| GET | `/api/v1/users/me/credit-history` | Login | 信用分历史 |
| GET | `/api/v1/users/{username}` | Public | 查看用户主页 |
| **Skill** | | | |
| GET | `/api/v1/skills/` | Public | Skill 列表 |
| POST | `/api/v1/skills/` | Login | 创建 Skill |
| GET | `/api/v1/skills/featured/` | Public | 精选 Skill |
| GET | `/api/v1/skills/trending/` | Public | 热门 Skill |
| GET | `/api/v1/skills/mine/` | Login | 我的 Skill |
| GET | `/api/v1/skills/{id}` | Public | Skill 详情 |
| PATCH | `/api/v1/skills/{id}` | Login | 更新 Skill |
| POST | `/api/v1/skills/{id}/submit-review` | Login | 提交审核 |
| POST | `/api/v1/skills/{id}/call` | Login | 调用 Skill |
| GET | `/api/v1/skills/{id}/reviews` | Public | 评价列表 |
| POST | `/api/v1/skills/{id}/reviews` | Login | 添加评价 |
| PATCH | `/api/v1/skills/{id}/reviews/mine` | Login | 更新评价 |
| GET | `/api/v1/skills/{id}/versions` | Public | 版本历史 |
| GET | `/api/v1/skills/{id}/stats` | Login | Skill 统计 |
| POST | `/api/v1/skills/{id}/approve` | Moderator | 审核通过 |
| POST | `/api/v1/skills/{id}/reject` | Moderator | 审核拒绝 |
| POST | `/api/v1/skills/{id}/suspend` | Moderator | 下架 |
| POST | `/api/v1/skills/{id}/set-featured` | Moderator | 设置精选 |
| **Bounty** | | | |
| GET | `/api/v1/bounties/` | Public | 悬赏列表 |
| POST | `/api/v1/bounties/` | Login | 创建悬赏 |
| GET | `/api/v1/bounties/mine/` | Login | 我的悬赏 |
| GET | `/api/v1/bounties/{id}` | Public | 悬赏详情 |
| GET | `/api/v1/bounties/{id}/comments` | Public | 悬赏评论 |
| POST | `/api/v1/bounties/{id}/apply` | Login | 申请接单 |
| POST | `/api/v1/bounties/{id}/accept` | Login | 确认接单者 |
| POST | `/api/v1/bounties/{id}/deliver` | Login | 提交交付物 |
| POST | `/api/v1/bounties/{id}/approve` | Login | 验收通过 |
| POST | `/api/v1/bounties/{id}/request-revision` | Login | 要求修改 |
| POST | `/api/v1/bounties/{id}/reject` | Login | 拒绝验收 |
| POST | `/api/v1/bounties/{id}/comments` | Login | 添加评论 |
| POST | `/api/v1/bounties/{id}/cancel` | Login | 取消悬赏 |
| POST | `/api/v1/bounties/{id}/rate` | Login | 互评 |
| POST | `/api/v1/bounties/{id}/arbitration/statement` | Login | 仲裁陈述 |
| POST | `/api/v1/bounties/arbitrations/{id}/vote` | Login | 仲裁投票 |
| POST | `/api/v1/bounties/arbitrations/{id}/appeal` | Login | 上诉 |
| **Workshop** | | | |
| GET | `/api/v1/articles/` | Public | 文章列表 |
| POST | `/api/v1/articles/` | Login | 创建文章 |
| GET | `/api/v1/articles/featured/` | Public | 精选文章 |
| GET | `/api/v1/articles/tip-leaderboard/` | Public | 打赏排行 |
| GET | `/api/v1/articles/mine/` | Login | 我的文章 |
| GET | `/api/v1/articles/{id}` | Public | 文章详情 |
| PATCH | `/api/v1/articles/{id}` | Login | 更新文章 |
| DELETE | `/api/v1/articles/{id}` | Login | 删除文章 |
| POST | `/api/v1/articles/{id}/publish` | Login | 发布文章 |
| POST | `/api/v1/articles/{id}/vote` | Login | 投票 |
| DELETE | `/api/v1/articles/{id}/vote` | Login | 取消投票 |
| GET | `/api/v1/articles/{id}/comments` | Public | 评论列表 |
| POST | `/api/v1/articles/{id}/comments` | Login | 添加评论 |
| POST | `/api/v1/articles/{id}/pin-comment` | Login | 置顶评论 |
| POST | `/api/v1/articles/{id}/tip` | Login | 打赏 |
| POST | `/api/v1/articles/{id}/set-featured` | Moderator | 加精 |
| POST | `/api/v1/articles/{id}/archive` | Moderator | 归档 |
| GET | `/api/v1/series/{id}` | Public | 系列详情 |
| POST | `/api/v1/series/` | Login | 创建系列 |
| PATCH | `/api/v1/series/{id}` | Login | 更新系列 |
| POST | `/api/v1/series/{id}/reorder` | Login | 重排文章 |
| **支付** | | | |
| POST | `/api/v1/payments/deposit-session` | Login | 创建充值会话 |
| GET | `/api/v1/payments/transactions` | Login | 交易记录 |
| GET | `/api/v1/payments/balance` | Login | 查询余额 |
| GET | `/api/v1/payments/earnings-report` | Login | 收入报表 |
| POST | `/api/webhooks/stripe/` | - | Stripe 回调 |
| **管理后台** | | | |
| GET | `/api/v1/admin/dashboard` | Admin | 平台概览 |
| GET | `/api/v1/admin/users` | Admin | 用户列表 |
| PATCH | `/api/v1/admin/users/{id}/role` | Admin | 修改角色 |
| POST | `/api/v1/admin/users/{id}/ban` | Admin | 封禁用户 |
| POST | `/api/v1/admin/users/{id}/unban` | Admin | 解封用户 |
| GET | `/api/v1/admin/skills/pending` | Admin | 待审核 Skill |
| GET | `/api/v1/admin/articles/pending-featured` | Admin | 待加精文章 |
| GET | `/api/v1/admin/finance/report` | Admin | 财务报表 |
| GET | `/api/v1/admin/disputes` | Admin | 争议列表 |
| POST | `/api/v1/admin/disputes/{id}/resolve` | Admin | 终审裁决 |
| **搜索** | | | |
| GET | `/api/v1/search/?q=xxx&type=all` | Public | 全局搜索 |
| GET | `/api/v1/search/suggest?q=xxx` | Public | 搜索建议 |
| **文件上传** | | | |
| POST | `/api/v1/upload/` | Login | 上传文件 |
