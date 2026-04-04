# 03 - 数据库设计

## 3.1 ER 关系概览

```
User ─┬─< Skill          (一个用户创建多个 Skill)
      ├─< SkillReview     (一个用户发表多个评价)
      ├─< SkillCall       (一个用户调用多个 Skill)
      ├─< Bounty          (一个用户发布多个悬赏)
      ├─< BountyApplication (一个用户申请多个悬赏)
      ├─< BountyDeliverable (一个用户提交多个交付物)
      ├─< Article         (一个用户发表多篇文章)
      ├─< Comment          (一个用户发表多条评论)
      ├─< Vote             (一个用户投多票)
      ├─< Tip              (一个用户多次打赏)
      ├─< Transaction      (一个用户多笔交易)
      ├─< CreditLog        (一个用户多条信用分记录)
      ├─< Notification     (一个用户多条通知)
      └─< Invitation       (一个用户邀请多人)

Skill ─┬─< SkillVersion   (一个 Skill 多个版本)
       ├─< SkillReview    (一个 Skill 多个评价)
       └─< SkillCall      (一个 Skill 多次调用)

Bounty ─┬─< BountyApplication (一个悬赏多个申请)
        ├─< BountyDeliverable (一个悬赏多个交付物)
        ├─< BountyComment     (一个悬赏多条评论)
        └─< Arbitration       (一个悬赏可能一次仲裁)

Article ─┬─< Comment      (一篇文章多条评论)
         ├─< Vote          (一篇文章多票)
         └─< Tip           (一篇文章多次打赏)

Series ──< Article         (一个系列多篇文章)
```

---

## 3.2 Django ORM Models 完整定义

> 所有 Models 使用 Django ORM，枚举使用 `TextChoices`，时间字段使用 `auto_now_add` / `auto_now`。

### 3.2.1 枚举类型

```python
# apps/accounts/models.py
from django.db import models

class UserRole(models.TextChoices):
    USER = "USER", "普通用户"
    MODERATOR = "MODERATOR", "版主"
    ADMIN = "ADMIN", "管理员"

class UserLevel(models.TextChoices):
    SEED = "SEED", "🌱 新芽"
    CRAFTSMAN = "CRAFTSMAN", "🔧 工匠"
    EXPERT = "EXPERT", "⚡ 专家"
    MASTER = "MASTER", "🏆 大师"
    GRANDMASTER = "GRANDMASTER", "👑 宗师"

# apps/skills/models.py
class SkillStatus(models.TextChoices):
    DRAFT = "DRAFT", "草稿"
    PENDING_REVIEW = "PENDING_REVIEW", "待审核"
    APPROVED = "APPROVED", "已上架"
    REJECTED = "REJECTED", "已拒绝"
    ARCHIVED = "ARCHIVED", "已归档"

class SkillCategory(models.TextChoices):
    CODE_DEV = "CODE_DEV", "代码开发"
    WRITING = "WRITING", "文案写作"
    DATA_ANALYTICS = "DATA_ANALYTICS", "数据分析"
    ACADEMIC = "ACADEMIC", "学术研究"
    TRANSLATION = "TRANSLATION", "翻译本地化"
    CREATIVE = "CREATIVE", "创意设计"
    AGENT = "AGENT", "Agent 工具"
    PRODUCTIVITY = "PRODUCTIVITY", "办公效率"
    MISC = "MISC", "其他"

class PricingModel(models.TextChoices):
    FREE = "FREE", "免费"
    PER_USE = "PER_USE", "按次付费"

# apps/bounties/models.py
class BountyStatus(models.TextChoices):
    OPEN = "OPEN", "开放"
    IN_PROGRESS = "IN_PROGRESS", "进行中"
    DELIVERED = "DELIVERED", "已交付"
    IN_REVIEW = "IN_REVIEW", "审核中"
    REVISION = "REVISION", "需修改"
    COMPLETED = "COMPLETED", "已完成"
    DISPUTED = "DISPUTED", "争议中"
    ARBITRATING = "ARBITRATING", "仲裁中"
    CANCELLED = "CANCELLED", "已取消"

class BountyType(models.TextChoices):
    SKILL_CUSTOM = "SKILL_CUSTOM", "Skill 定制"
    DATA_PROCESSING = "DATA_PROCESSING", "数据处理"
    CONTENT_CREATION = "CONTENT_CREATION", "内容创作"
    BUG_FIX = "BUG_FIX", "问题修复"
    GENERAL = "GENERAL", "通用任务"

# apps/workshop/models.py
class ArticleStatus(models.TextChoices):
    DRAFT = "DRAFT", "草稿"
    PUBLISHED = "PUBLISHED", "已发布"
    ARCHIVED = "ARCHIVED", "已归档"

class ArticleDifficulty(models.TextChoices):
    BEGINNER = "BEGINNER", "入门"
    INTERMEDIATE = "INTERMEDIATE", "进阶"
    ADVANCED = "ADVANCED", "高级"

class ArticleType(models.TextChoices):
    TUTORIAL = "TUTORIAL", "教程"
    CASE_STUDY = "CASE_STUDY", "案例"
    PITFALL = "PITFALL", "踩坑记录"
    REVIEW = "REVIEW", "评测"
    DISCUSSION = "DISCUSSION", "讨论"

# apps/payments/models.py
class TransactionType(models.TextChoices):
    DEPOSIT = "DEPOSIT", "充值"
    SKILL_PURCHASE = "SKILL_PURCHASE", "Skill 调用扣费"
    SKILL_INCOME = "SKILL_INCOME", "Skill 收入"
    BOUNTY_ESCROW = "BOUNTY_ESCROW", "悬赏冻结"
    BOUNTY_RELEASE = "BOUNTY_RELEASE", "悬赏解冻"
    BOUNTY_INCOME = "BOUNTY_INCOME", "悬赏收入"
    TIP_SEND = "TIP_SEND", "打赏支出"
    TIP_RECEIVE = "TIP_RECEIVE", "打赏收入"
    PLATFORM_FEE = "PLATFORM_FEE", "平台手续费"
    REFUND = "REFUND", "退款"

# apps/credits/models.py
class CreditAction(models.TextChoices):
    REGISTER = "REGISTER", "注册奖励"
    PUBLISH_SKILL = "PUBLISH_SKILL", "发布 Skill"
    SKILL_CALLED = "SKILL_CALLED", "Skill 被调用"
    PUBLISH_ARTICLE = "PUBLISH_ARTICLE", "发布文章"
    ARTICLE_FEATURED = "ARTICLE_FEATURED", "文章加精"
    BOUNTY_COMPLETED = "BOUNTY_COMPLETED", "完成悬赏"
    TIP_GIVEN = "TIP_GIVEN", "打赏他人"
    ARBITRATION_SERVED = "ARBITRATION_SERVED", "参与仲裁"
    INVITE_REGISTERED = "INVITE_REGISTERED", "邀请注册"
    BOUNTY_TIMEOUT = "BOUNTY_TIMEOUT", "悬赏超时惩罚"
    BOUNTY_FREEZE = "BOUNTY_FREEZE", "悬赏板冻结"
    ADMIN_ADJUST = "ADMIN_ADJUST", "管理员调整"
```

---

### 3.2.2 用户模型

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.postgres.fields import ArrayField


class User(AbstractUser):
    """扩展 Django 内置 User，增加业务字段"""
    display_name = models.CharField(max_length=50, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar_url = models.URLField(blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    level = models.CharField(max_length=20, choices=UserLevel.choices, default=UserLevel.SEED)
    credit_score = models.IntegerField(default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frozen_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bounty_freeze_until = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="invitees"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user"


class Invitation(models.Model):
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invitations")
    code = models.CharField(max_length=20, unique=True)
    used_by = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="used_invitation"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    first_deposit_rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_invitation"
```

---

### 3.2.3 Skill 模型

```python
# apps/skills/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.accounts.models import User


class Skill(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=500)
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(blank=True)
    output_format = models.CharField(
        max_length=20,
        choices=[("text", "文本"), ("json", "JSON"), ("markdown", "Markdown"), ("code", "代码")],
        default="text",
    )
    example_input = models.TextField(blank=True)
    example_output = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=SkillCategory.choices)
    tags = ArrayField(models.CharField(max_length=50), default=list, size=10)
    pricing_model = models.CharField(max_length=10, choices=PricingModel.choices, default=PricingModel.FREE)
    price_per_use = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SkillStatus.choices, default=SkillStatus.DRAFT)
    is_featured = models.BooleanField(default=False)
    current_version = models.IntegerField(default=1)
    total_calls = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skills_skill"
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["creator", "status"]),
        ]


class SkillVersion(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="versions")
    version = models.IntegerField()
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(blank=True)
    change_note = models.CharField(max_length=200, blank=True)
    is_major = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_version"
        unique_together = ("skill", "version")


class SkillCall(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="calls")
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_calls")
    skill_version = models.IntegerField()
    input_text = models.TextField()
    output_text = models.TextField(blank=True)
    amount_charged = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_skill_call"
        indexes = [models.Index(fields=["skill", "created_at"])]


class SkillReview(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_reviews")
    rating = models.IntegerField()  # 1-5
    comment = models.TextField(blank=True)
    tags = ArrayField(models.CharField(max_length=30), default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skills_skill_review"
        unique_together = ("skill", "reviewer")
```

---

### 3.2.4 Bounty 模型

```python
# apps/bounties/models.py
from django.db import models
from apps.accounts.models import User


class Bounty(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bounties")
    title = models.CharField(max_length=200)
    description = models.TextField()
    bounty_type = models.CharField(max_length=30, choices=BountyType.choices)
    reward = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=BountyStatus.choices, default=BountyStatus.OPEN)
    deadline = models.DateTimeField()
    accepted_application = models.OneToOneField(
        "BountyApplication", null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_bounty"
    )
    revision_count = models.IntegerField(default=0)
    is_cold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bounties_bounty"
        indexes = [models.Index(fields=["status", "created_at"])]


class BountyApplication(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bounty_applications")
    proposal = models.TextField()
    estimated_days = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_bounty_application"
        unique_together = ("bounty", "applicant")


class BountyDeliverable(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="deliverables")
    submitter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deliverables")
    content = models.TextField()
    attachments = models.JSONField(default=list)
    revision_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_bounty_deliverable"


class BountyComment(models.Model):
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bounty_comments")
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_bounty_comment"


class Arbitration(models.Model):
    bounty = models.OneToOneField(Bounty, on_delete=models.CASCADE, related_name="arbitration")
    creator_statement = models.TextField(blank=True)
    hunter_statement = models.TextField(blank=True)
    arbitrators = models.ManyToManyField(User, related_name="arbitration_cases", blank=True)
    result = models.CharField(
        max_length=20,
        choices=[("HUNTER_WIN", "接单者胜"), ("CREATOR_WIN", "发布者胜"), ("PARTIAL", "部分完成")],
        blank=True,
    )
    hunter_ratio = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    appeal_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="appeals"
    )
    appeal_fee_paid = models.BooleanField(default=False)
    admin_final_result = models.CharField(max_length=20, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bounties_arbitration"


class ArbitrationVote(models.Model):
    arbitration = models.ForeignKey(Arbitration, on_delete=models.CASCADE, related_name="votes")
    arbitrator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="arbitration_votes")
    vote = models.CharField(
        max_length=20,
        choices=[("HUNTER_WIN", "接单者胜"), ("CREATOR_WIN", "发布者胜"), ("PARTIAL", "部分完成")],
    )
    hunter_ratio = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bounties_arbitration_vote"
        unique_together = ("arbitration", "arbitrator")
```

---

### 3.2.5 Workshop 模型

```python
# apps/workshop/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.accounts.models import User
from apps.skills.models import Skill


class Series(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="series")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    is_completed = models.BooleanField(default=False)
    completion_rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workshop_series"


class Article(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    series_order = models.IntegerField(null=True, blank=True)
    related_skill = models.ForeignKey(Skill, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    content = models.TextField()
    difficulty = models.CharField(max_length=20, choices=ArticleDifficulty.choices)
    article_type = models.CharField(max_length=20, choices=ArticleType.choices)
    model_tags = ArrayField(models.CharField(max_length=50), default=list)
    custom_tags = ArrayField(models.CharField(max_length=50), default=list, size=5)
    status = models.CharField(max_length=20, choices=ArticleStatus.choices, default=ArticleStatus.DRAFT)
    is_featured = models.BooleanField(default=False)
    net_votes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_tips = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    view_count = models.IntegerField(default=0)
    is_outdated = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workshop_article"
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["author", "status"]),
        ]


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    content = models.TextField(max_length=500)
    is_pinned = models.BooleanField(default=False)
    net_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workshop_comment"


class Vote(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="votes")
    is_upvote = models.BooleanField()
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workshop_vote"
        unique_together = ("article", "voter")


class Tip(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="tips")
    tipper = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tips_given")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tips_received")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workshop_tip"
```

---

### 3.2.6 支付与信用分模型

```python
# apps/payments/models.py
from django.db import models
from apps.accounts.models import User


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # 正=收入, 负=支出
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(max_length=100, blank=True)  # 关联业务 ID
    description = models.CharField(max_length=200, blank=True)
    stripe_payment_intent = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_transaction"
        indexes = [models.Index(fields=["user", "created_at"])]


# apps/credits/models.py
class CreditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="credit_logs")
    action = models.CharField(max_length=30, choices=CreditAction.choices)
    amount = models.IntegerField()  # 正=增加, 负=扣减
    score_before = models.IntegerField()
    score_after = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credits_credit_log"
        indexes = [models.Index(fields=["user", "created_at"])]
```

---

### 3.2.7 通知模型

```python
# apps/notifications/models.py
from django.db import models
from apps.accounts.models import User


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_notification"
        indexes = [models.Index(fields=["recipient", "is_read", "created_at"])]
```

---

## 3.3 数据库索引策略

```python
# 关键查询索引（已在 Meta.indexes 中定义）

# skills_skill
# - (status, category)       → 市场列表筛选
# - (creator, status)        → 我的 Skill 列表

# workshop_article
# - (status, published_at)   → 文章列表排序
# - (author, status)         → 我的文章列表

# bounties_bounty
# - (status, created_at)     → 悬赏列表排序

# payments_transaction
# - (user, created_at)       → 交易记录查询

# credits_credit_log
# - (user, created_at)       → 信用分历史

# notifications_notification
# - (recipient, is_read, created_at) → 未读通知查询
```

---

## 3.4 事务关键操作

以下操作必须使用 `transaction.atomic()` + `select_for_update()`：

```python
from django.db import transaction

# Skill 付费调用
with transaction.atomic():
    user = User.objects.select_for_update().get(pk=user_id)
    # 扣费 → 分成 → 记录 Transaction → 更新 Skill.total_calls

# 悬赏发布（冻结余额）
with transaction.atomic():
    user = User.objects.select_for_update().get(pk=user_id)
    # balance -= reward; frozen_balance += reward; 记录 Transaction

# 悬赏结算
with transaction.atomic():
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    # frozen_balance -= reward; hunter.balance += net; 记录 Transaction; 更新信用分

# 打赏
with transaction.atomic():
    tipper = User.objects.select_for_update().get(pk=tipper_id)
    # balance -= amount; author.balance += amount; 记录 Tip + Transaction; 信用分 +2/dollar
```

---

## 3.5 迁移管理

```bash
# 创建迁移
python manage.py makemigrations

# 应用迁移（开发）
python manage.py migrate

# 应用迁移（生产，CI/CD 自动执行）
python manage.py migrate --run-syncdb

# 填充种子数据
python manage.py seed
```

**迁移规范**：
- 每次迁移有明确的描述名称（`makemigrations --name`）
- 破坏性变更（删列、改类型）分多次迁移执行
- 生产环境禁止使用 `migrate --fake` 跳过迁移
- 保留所有迁移历史，不合并删除
