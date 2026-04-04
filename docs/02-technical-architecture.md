# 02 - 技术架构设计

## 2.1 技术栈总览

| 层级 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|---------|
| **后端框架** | Django + Django Ninja | 5.2 / 1.x | 成熟稳定，团队熟悉，Django Ninja 提供类型安全 REST API |
| **后端语言** | Python | 3.12+ | 丰富生态，AI 领域主流语言 |
| **前端框架** | React + Vite | 18.x / 6.x | 社区最大，shadcn/ui 原生支持 |
| **前端语言** | TypeScript | 5.x | 类型安全，大型项目必备 |
| **UI 库** | Tailwind CSS + shadcn/ui | 4.x / latest | 原子化 CSS + 高质量组件库 |
| **状态管理** | Zustand + TanStack Query | latest | 轻量级 client state + server state |
| **API 层** | Django Ninja (REST) | 1.x | 自动生成 OpenAPI，Pydantic 验证 |
| **ORM** | Django ORM | 5.2 | 内置迁移系统，事务支持完善 |
| **数据库** | PostgreSQL | 16.x | 关系型，事务支持（$ 结算必须） |
| **缓存** | Redis (django-redis) | 7.x | 热榜、限流、排行榜、Celery broker |
| **搜索** | Meilisearch | 1.x | 轻量全文搜索，中文分词支持 |
| **对象存储** | Cloudflare R2 / AWS S3 | - | 文件附件、头像 (django-storages) |
| **认证** | django-allauth + simplejwt | latest | OAuth + JWT 认证 |
| **邮件** | Resend / Django email | - | 开发者友好邮件服务 |
| **任务队列** | Celery + Redis | 5.x | 异步任务（审核、结算、排行榜刷新） |
| **监控** | Sentry + PostHog | - | 后端错误追踪 + 前端产品分析 |
| **部署** | Vercel (前端) + Docker (后端) | - | 前后端分离部署 |

---

## 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     客户端 (Browser)                              │
│  React 18 SPA (Vite + React Router v7)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Marketplace│ │  Bounty  │ │ Workshop │ │  Admin   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API (JWT Bearer)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                Django Backend (API Server)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Django Ninja  │ │ Auth         │ │ Middleware   │             │
│  │ API Router   │ │ (allauth+JWT)│ │  ├─ CORS     │             │
│  │  ├─ accounts │ │              │ │  ├─ rateLimit│             │
│  │  ├─ skills   │ │              │ │  └─ logging  │             │
│  │  ├─ bounties │ │              │ │              │             │
│  │  ├─ workshop │ │              │ │              │             │
│  │  ├─ payments │ │              │ │              │             │
│  │  └─ admin    │ │              │ │              │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  ┌──────────────┐                                                │
│  │ Celery Worker│ ← 异步任务（审核、结算、排行榜、超时检测）        │
│  └──────────────┘                                                │
└───┬──────────────┬──────────────┬──────────────┬────────────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│PostgreSQL│  │  Redis   │  │Meilisearch│  │ Object Store │
│(Django   │  │(django-  │  │          │  │ (R2 / S3)    │
│  ORM)    │  │  redis)  │  │          │  │              │
│          │  │          │  │          │  │              │
│- Users   │  │- Cache   │  │- Skills  │  │- Avatars     │
│- Skills  │  │- Rankings│  │- Articles│  │- Attachments │
│- Bounties│  │- RateLimit│ │- Bounties│  │- Skill Icons │
│- Articles│  │- Celery  │  │          │  │              │
│- Payments│  │  Broker  │  │          │  │              │
└────────┘  └──────────┘  └──────────┘  └──────────────┘
```

---

## 2.3 项目目录结构

### 2.3.1 后端（Django）

```
camel-backend/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
│
├── config/                        # Django 项目配置
│   ├── settings/
│   │   ├── base.py                # 公共配置
│   │   ├── development.py         # 开发环境
│   │   └── production.py          # 生产环境
│   ├── urls.py                    # 根路由
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/                          # Django 应用
│   ├── accounts/                  # 用户与认证
│   │   ├── models.py              # User, Invitation
│   │   ├── api.py                 # Django Ninja 路由
│   │   ├── schemas.py             # Pydantic 输入/输出 Schema
│   │   ├── services.py            # 业务逻辑
│   │   └── tasks.py               # Celery 任务
│   │
│   ├── skills/                    # Skill Marketplace
│   │   ├── models.py              # Skill, SkillVersion, SkillReview, SkillCall
│   │   ├── api.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── tasks.py               # 审核任务
│   │
│   ├── bounties/                  # 悬赏任务板
│   │   ├── models.py              # Bounty, BountyApplication, BountyDeliverable, Arbitration
│   │   ├── api.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── tasks.py               # 超时检测、结算
│   │
│   ├── workshop/                  # 知识工坊
│   │   ├── models.py              # Article, Series, Comment, Vote, Tip
│   │   ├── api.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── tasks.py               # 排行榜刷新
│   │
│   ├── payments/                  # 支付与交易
│   │   ├── models.py              # Transaction
│   │   ├── api.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   └── webhooks.py            # Stripe Webhook
│   │
│   ├── credits/                   # 信用分系统
│   │   ├── models.py              # CreditLog
│   │   ├── services.py
│   │   └── tasks.py
│   │
│   └── notifications/             # 通知系统
│       ├── models.py              # Notification
│       ├── api.py
│       └── services.py
│
├── common/                        # 公共工具
│   ├── permissions.py             # 权限装饰器
│   ├── pagination.py              # Cursor 分页
│   ├── exceptions.py              # 统一异常处理
│   └── storage.py                 # django-storages 配置
│
└── celery_app.py                  # Celery 入口
```

### 2.3.2 前端（React + Vite）

```
camel-frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── .env.example
│
├── src/
│   ├── main.tsx                   # 应用入口
│   ├── App.tsx                    # 路由根组件
│   │
│   ├── pages/                     # 页面组件（对应路由）
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── ForgotPasswordPage.tsx
│   │   ├── marketplace/
│   │   │   ├── MarketplacePage.tsx
│   │   │   ├── SkillDetailPage.tsx
│   │   │   ├── CreateSkillPage.tsx
│   │   │   └── MySkillsPage.tsx
│   │   ├── bounty/
│   │   │   ├── BountyListPage.tsx
│   │   │   ├── BountyDetailPage.tsx
│   │   │   ├── CreateBountyPage.tsx
│   │   │   └── MyBountiesPage.tsx
│   │   ├── workshop/
│   │   │   ├── WorkshopPage.tsx
│   │   │   ├── ArticleDetailPage.tsx
│   │   │   ├── WriteArticlePage.tsx
│   │   │   └── SeriesPage.tsx
│   │   ├── profile/
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── WalletPage.tsx
│   │   └── admin/
│   │       ├── DashboardPage.tsx
│   │       ├── SkillReviewPage.tsx
│   │       ├── UsersPage.tsx
│   │       └── FinancePage.tsx
│   │
│   ├── components/                # 可复用组件
│   │   ├── ui/                    # shadcn/ui 基础组件
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── skill/
│   │   ├── bounty/
│   │   ├── workshop/
│   │   ├── user/
│   │   └── shared/
│   │
│   ├── hooks/                     # 自定义 Hooks
│   │   ├── useAuth.ts
│   │   ├── useCredit.ts
│   │   └── useInfiniteScroll.ts
│   │
│   ├── api/                       # API 客户端（TanStack Query）
│   │   ├── client.ts              # axios 实例 + JWT 拦截器
│   │   ├── skills.ts
│   │   ├── bounties.ts
│   │   ├── workshop.ts
│   │   ├── accounts.ts
│   │   └── payments.ts
│   │
│   ├── stores/                    # Zustand 状态
│   │   ├── auth.store.ts
│   │   └── ui.store.ts
│   │
│   └── types/                     # TypeScript 类型（与后端 Schema 对齐）
│       ├── skill.ts
│       ├── bounty.ts
│       ├── workshop.ts
│       └── enums.ts
│
└── public/
    ├── logo.svg
    └── og-image.png
```

---

## 2.4 核心架构决策

### 2.4.1 SEO 策略

本项目采用 React SPA 架构，SEO 策略如下：

```
页面类型          SEO 需求    方案
─────────────────────────────────────────────────────
首页 / 热榜       高          react-snap 预渲染静态 HTML
Skill 详情        高          prerender.io / SSR 服务
Workshop 文章     高          prerender.io / SSR 服务
Bounty 列表       中          基础 meta 标签
个人中心 / 管理   无          纯 CSR，无需处理
```

- 短期：使用 `react-snap` 在构建时预渲染关键页面
- 中期：接入 `prerender.io` 对爬虫返回预渲染 HTML
- 长期：如 SEO 成为核心需求，可将 Workshop 模块迁移至 Next.js 独立部署

### 2.4.2 认证方案

```
登录方式：
├── Email + Password（主要，django-allauth）
├── GitHub OAuth（开发者群体）
├── Google OAuth（通用）
└── 邮箱验证码登录

Token 流程：
1. 用户登录 → 后端返回 access_token (15min) + refresh_token (30天)
2. 前端存储于 httpOnly Cookie 或 localStorage
3. 每次请求携带 Authorization: Bearer <access_token>
4. access_token 过期 → 前端自动用 refresh_token 换新 token
5. refresh_token 过期 → 跳转登录页
```

### 2.4.3 API 设计原则

```python
# Django Ninja 权限装饰器分层
@router.get("/public")           # 无需认证（浏览、搜索）
@router.get("/protected",
    auth=JWTAuth())              # 需要登录（创建、编辑）
@router.get("/moderator",
    auth=ModeratorAuth())        # 需要版主及以上
@router.get("/admin",
    auth=AdminAuth())            # 需要管理员

# 请求处理链
Request → CORS → RateLimit → JWTAuth → Pydantic Validation → Handler → Response
```

### 2.4.4 安全策略

| 安全措施 | 实现方式 |
|----------|---------|
| XSS 防护 | React 默认转义 + DOMPurify（Markdown 渲染） |
| CSRF 防护 | Django CSRF middleware（表单）+ JWT（API） |
| SQL 注入 | Django ORM 参数化查询 |
| CORS | django-cors-headers，白名单前端域名 |
| Rate Limiting | django-ratelimit + Redis 滑动窗口 |
| 输入验证 | Pydantic Schema（后端）+ Zod（前端） |
| Prompt 注入检测 | 关键词扫描 + 模式匹配（ModerationService） |
| 文件上传安全 | 类型白名单 + 大小限制（django-storages） |
| 敏感操作 | 二次确认 + 操作日志 |

### 2.4.5 缓存策略

```
后端 Redis 缓存（django-redis）：
├── 热榜数据           → TTL 60s，每分钟 Celery 刷新
├── Skill 详情         → TTL 300s，写入时失效
├── 搜索热词           → TTL 3600s
├── 信用分排行榜       → TTL 300s，Sorted Set
├── 限流计数器         → 滑动窗口
└── 分布式锁           → 结算操作（select_for_update）

前端 TanStack Query 缓存：
├── staleTime: 60s     → 列表数据
├── staleTime: 300s    → 详情数据
├── staleTime: 0       → 用户余额、通知等实时数据
└── 乐观更新           → 投票、点赞等交互
```

---

## 2.5 第三方服务集成

| 服务 | 用途 | 备选方案 |
|------|------|---------|
| Vercel | 前端 React SPA 部署 | Cloudflare Pages |
| Railway / Render | 后端 Django 容器部署 | Fly.io, AWS ECS |
| Neon / Supabase | PostgreSQL 托管 | AWS RDS |
| Redis Cloud | Redis 托管 | Upstash |
| Meilisearch Cloud | 搜索服务 | Typesense Cloud |
| Cloudflare R2 | 对象存储 | AWS S3 |
| Stripe | 支付 | LemonSqueezy |
| Resend | 邮件发送 | SendGrid |
| Sentry | 错误监控（sentry-sdk[django]） | - |
| PostHog | 前端产品分析 | Mixpanel |

---

## 2.6 环境配置

### 2.6.1 后端 `.env`

```env
# camel-backend/.env

# ─── Django ───
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:5173

# ─── Database ───
DATABASE_URL=postgresql://camel:camel_dev@localhost:5432/camel_community

# ─── Redis ───
REDIS_URL=redis://localhost:6379/0

# ─── Auth (OAuth) ───
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ─── JWT ───
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=30

# ─── Storage ───
USE_S3=False
S3_ENDPOINT=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=camel-community

# ─── Payment ───
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# ─── Email ───
RESEND_API_KEY=
DEFAULT_FROM_EMAIL=noreply@camelcommunity.com

# ─── Search ───
MEILISEARCH_HOST=http://localhost:7700
MEILISEARCH_API_KEY=

# ─── Monitoring ───
SENTRY_DSN=
```

### 2.6.2 前端 `.env`

```env
# camel-frontend/.env

VITE_API_BASE_URL=http://localhost:8000/api
VITE_STRIPE_PUBLISHABLE_KEY=
VITE_POSTHOG_KEY=
VITE_SENTRY_DSN=
```
