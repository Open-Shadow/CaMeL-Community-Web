# CLAUDE.md

> 本文件为 Claude Code 提供项目上下文，确保跨会话一致性。
>
> **工作进度记录**:
> - [docs/00-session-bootstrap.md](docs/00-session-bootstrap.md) - 新会话启动说明（推荐第一个读）
> - [work.md](work.md) - 已完成的工作摘要和下一步计划
> - [docs/07-development-tasks.md](docs/07-development-tasks.md) - 详细任务列表，含完成状态（✅ 完成 / 🔶 部分完成 / ❌ 未完成）

## 新会话启动（必须）

每次新对话建议先执行以下流程：

1. 阅读 [docs/00-session-bootstrap.md](docs/00-session-bootstrap.md)
2. 阅读 [docs/07-development-tasks.md](docs/07-development-tasks.md)
3. 阅读 [docs/10-merge-handoff.md](docs/10-merge-handoff.md)
4. 阅读 [work.md](work.md)

快速校验命令（可选但强烈建议）：

```bash
git status --short
cd backend && SECRET_KEY=test uv run pytest -q
cd .. && corepack pnpm -C frontend build
```

### 当前关键现实（防止误读旧文档）

- 任务总数按 `docs/07` 为 `117`（非旧版本的 105）。
- API 实际挂载前缀是 `/api/`（不是 `/api/v1/`）。
- 支付充值前后端接口命名仍有不一致，属于“部分完成”状态。
- 邀请链路中“7天活跃校验 / 首月消费奖励”尚未完整落地。
- 管理后台、排行榜、PWA、SEO 仍有未完成项（详见 `docs/07` 的 `❌` 任务）。

## 项目概述

**CaMeL Community** 是一个面向 AI 用户的社区平台，集成三大核心模块：

| 模块 | 定位 | 核心功能 |
|------|------|---------|
| **Skill Marketplace** | 技能市场 | Prompt/Skill 的创建、审核、交易、调用 |
| **Bounty Board** | 悬赏任务板 | 需求发布、接单、交付、验收、仲裁 |
| **Workshop** | 知识工坊 | 结构化教程/经验文章、投票、打赏、加精 |

### 经济系统

采用 **$ 额度 + 信用分** 双轴体系（无双 Token）：

- **$ 额度**：可充值、可消费、可赚取，所见即所得
- **信用分**：不可充值/转让，通过社区行为积累，用于解锁特权和 API 倍率折扣

### 信用等级体系

| 等级 | 图标 | 分数范围 | API 折扣 |
|------|------|---------|---------|
| 新芽 | 🌱 | 0~99 | 1.0x |
| 工匠 | 🔧 | 100~499 | 0.95x |
| 专家 | ⚡ | 500~1999 | 0.90x |
| 大师 | 🏆 | 2000~4999 | 0.85x |
| 宗师 | 👑 | 5000+ | 0.80x |

---

## 架构概述

本项目采用 **前后端分离** 架构，包含两个独立代码库：

| 端 | 技术栈 | 仓库目录 |
|----|--------|---------|
| **后端** | Django 5.2 + Django Ninja + Celery | `backend/` |
| **前端** | React 18 + Vite 6 + TypeScript | `frontend/` |

---

## 技术栈

```
后端:
  框架:       Django 5.2 + Django Ninja (REST API)
  语言:       Python 3.12+
  ORM:        Django ORM
  数据库:     PostgreSQL 16
  缓存:       Redis (Upstash / django-redis)
  搜索:       Meilisearch
  任务队列:   Celery + Redis
  认证:       django-allauth + djangorestframework-simplejwt (JWT)
  存储:       Cloudflare R2 / AWS S3 (django-storages)
  支付:       Stripe (stripe Python SDK)
  邮件:       Resend / Django email backends
  监控:       Sentry (sentry-sdk[django])

前端:
  框架:       React 18 + Vite 6
  语言:       TypeScript
  UI:         Tailwind CSS + shadcn/ui
  路由:       React Router v7
  状态:       Zustand + TanStack Query
  API 客户端: 基于 OpenAPI 自动生成 (openapi-typescript-codegen)
  编辑器:     Tiptap (Markdown 文章)
  图表:       Recharts
  动画:       Framer Motion
  SEO:        react-helmet-async + react-snap (预渲染)
  监控:       PostHog
```

---

## 项目结构

### 后端 (Django)

```
backend/
├── config/                     # Django 项目配置
│   ├── settings/
│   │   ├── base.py            # 基础配置
│   │   ├── dev.py             # 开发环境
│   │   └── prod.py            # 生产环境
│   ├── urls.py                # URL 路由
│   ├── api.py                 # Django Ninja API 总路由
│   ├── celery.py              # Celery 配置
│   └── wsgi.py
│
├── apps/
│   ├── accounts/              # 用户管理、认证
│   │   ├── models.py          # User, Invitation
│   │   ├── api.py             # 用户 API 路由
│   │   ├── services.py        # 业务逻辑
│   │   └── schemas.py         # Pydantic 输入/输出 Schema
│   │
│   ├── skills/                # 技能市场
│   │   ├── models.py          # Skill, SkillVersion, SkillReview, SkillCall
│   │   ├── api.py
│   │   ├── services.py
│   │   └── tasks.py           # Celery 任务（热榜更新等）
│   │
│   ├── bounties/              # 悬赏任务板
│   │   ├── models.py          # Bounty, Application, Deliverable, Arbitration
│   │   ├── api.py
│   │   ├── services.py
│   │   └── tasks.py           # Celery 任务（超时检测等）
│   │
│   ├── workshop/              # 知识工坊
│   │   ├── models.py          # Article, Series, Comment, Vote, Tip
│   │   ├── api.py
│   │   └── services.py
│   │
│   ├── payments/              # 支付与交易
│   │   ├── models.py          # Transaction
│   │   ├── api.py
│   │   ├── services.py
│   │   └── webhooks.py        # Stripe Webhook 处理
│   │
│   ├── credits/               # 信用分系统
│   │   ├── models.py          # CreditLog
│   │   └── services.py        # CreditService
│   │
│   ├── notifications/         # 通知系统
│   │   ├── models.py          # Notification
│   │   ├── api.py
│   │   └── services.py
│   │
│   └── search/                # 搜索集成
│       ├── api.py
│       └── services.py        # Meilisearch 封装
│
├── common/                    # 共享工具
│   ├── permissions.py         # API 权限装饰器
│   ├── pagination.py          # Cursor 分页
│   ├── exceptions.py          # 统一异常处理
│   └── middleware.py          # 中间件
│
├── manage.py
├── pyproject.toml             # Python 依赖 (uv)
├── Justfile                   # 任务自动化
└── docker-compose.yml         # 本地开发基础设施
```

### 前端 (React + Vite)

```
frontend/
├── src/
│   ├── app/                   # App 入口、Router 配置
│   │   ├── App.tsx
│   │   ├── router.tsx         # React Router v7 路由定义
│   │   └── providers.tsx      # QueryClient, Auth, Theme 等 Provider
│   │
│   ├── pages/                 # 页面组件
│   │   ├── auth/              # 登录/注册
│   │   ├── marketplace/       # 技能市场
│   │   ├── bounty/            # 悬赏任务板
│   │   ├── workshop/          # 知识工坊
│   │   ├── profile/           # 个人中心
│   │   └── admin/             # 管理后台
│   │
│   ├── components/            # React 组件
│   │   ├── ui/                # shadcn/ui 基础组件
│   │   ├── layout/            # Header, Footer, Sidebar
│   │   ├── skill/             # SkillCard, SkillForm 等
│   │   ├── bounty/            # BountyCard, BountyTimeline 等
│   │   ├── workshop/          # ArticleCard, ArticleEditor 等
│   │   ├── user/              # CreditBadge, UserAvatar 等
│   │   └── shared/            # SearchBar, Pagination, FileUpload 等
│   │
│   ├── hooks/                 # 自定义 Hooks (useAuth, useCredit 等)
│   ├── lib/
│   │   ├── api/               # OpenAPI 自动生成的 API 客户端
│   │   ├── utils.ts           # 通用工具函数
│   │   └── constants.ts       # 常量定义
│   │
│   ├── stores/                # Zustand 状态管理
│   ├── types/                 # TypeScript 类型定义
│   └── styles/                # 全局样式
│
├── public/                    # 静态资源
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 开发规范

### 命名约定

```
后端 (Python):
  文件命名:     snake_case (skill_service.py)
  类命名:       PascalCase (SkillService)
  函数/变量:    snake_case (get_skill_by_id)
  常量:         UPPER_SNAKE_CASE (MAX_SKILL_PRICE)
  Django 模型:  PascalCase (Skill, BountyApplication)
  API Router:   snake_case (skill_router)

前端 (TypeScript):
  文件命名:     kebab-case (skill-card.tsx)
  组件命名:     PascalCase (SkillCard)
  函数/变量:    camelCase (getSkillById)
  常量:         UPPER_SNAKE_CASE (MAX_SKILL_PRICE)
  类型/接口:    PascalCase (SkillInput)
```

### API 权限层级

```python
# common/permissions.py
public_api          # 无需认证
login_required      # 需要 JWT 登录
moderator_required  # 需要版主及以上角色
admin_required      # 需要管理员角色
```

### 数据库事务

以下操作必须在 `transaction.atomic()` + `select_for_update()` 中执行：

- Skill 购买（扣费 + 分成）
- 悬赏发布（冻结余额）
- 悬赏结算（释放 + 划转）
- 打赏（扣费 + 转账 + 信用分）
- 充值到账（余额 + 邀请奖励）
- 信用分变更（分数 + 日志 + 等级检查）

### 前端 SEO 策略

| 页面类型 | 方案 |
|---------|------|
| 首页/热榜 | react-snap 预渲染 |
| Skill 详情 | react-helmet-async meta 标签 |
| Workshop 文章 | react-snap 预渲染（SEO 关键） |
| Bounty 列表 | SPA（SEO 非关键） |
| 个人中心/管理后台 | 纯 CSR |

---

## 关键设计决策

### 1. 为什么选择 Django + React 前后端分离？

- 团队对 Django 和 React 技术栈熟悉，降低学习成本
- 前后端独立部署，各自选择最优方案
- Django Ninja 自动生成 OpenAPI 文档，前端可自动生成类型安全 API 客户端
- 可借鉴 OpenShareHQ 项目的 Django 代码结构

### 2. 为什么选择单货币（$）而非双 Token？

- 简化用户理解成本
- 避免监管合规问题
- 信用分通过折扣间接体现价值

### 3. 仲裁系统设计要点

- 冷静期 24 小时 → 鼓励协商
- 社区仲裁团：3 名 ⚡专家 级以上用户
- 上诉机制：$0.50 上诉费，管理员终审

### 4. 信用分核心作用

- **信任门槛**：发布/接单需 ≥50 分
- **成本折扣**：等级越高，API 调用越便宜
- **投票权重**：高等级用户投票权重更高
- **仲裁资格**：≥500 分可参与仲裁

---

## 本地开发启动

```bash
# ─── 后端 ───

# 1. 安装依赖
cd backend
uv sync

# 2. 配置环境变量
cp .env.example .env

# 3. 启动基础设施（Docker）
docker compose up -d postgres redis meilisearch

# 4. 数据库迁移
python manage.py migrate

# 5. 填充种子数据
python manage.py seed

# 6. 启动后端开发服务器
python manage.py runserver

# ─── 前端 ───

# 7. 安装依赖
cd frontend
pnpm install

# 8. 配置环境变量
cp .env.example .env.local

# 9. 启动前端开发服务器
pnpm dev
```

---

## 设计文档索引

详细设计文档位于 `docs/` 目录：

| 文档 | 内容 |
|------|------|
| [01-project-overview.md](docs/01-project-overview.md) | 项目定位、经济系统、模块协同 |
| [02-technical-architecture.md](docs/02-technical-architecture.md) | 技术栈、架构图、目录结构 |
| [03-database-design.md](docs/03-database-design.md) | Django Models、ER 关系 |
| [04-api-design.md](docs/04-api-design.md) | Django Ninja REST API 接口定义 |
| [05-module-design.md](docs/05-module-design.md) | 业务逻辑、流程图、算法 |
| [06-frontend-design.md](docs/06-frontend-design.md) | 页面线框图、组件清单 |
| [07-development-tasks.md](docs/07-development-tasks.md) | 117 个开发任务分解 |
| [08-deployment.md](docs/08-deployment.md) | 部署、CI/CD、监控 |
| [09-opensharehq-reference.md](docs/09-opensharehq-reference.md) | OpenShareHQ 借鉴指南 |
| [10-merge-handoff.md](docs/10-merge-handoff.md) | 合并交接说明与高冲突文件 |
| [00-session-bootstrap.md](docs/00-session-bootstrap.md) | 新会话启动说明（入口） |

---

## 开发任务快速参考

**Phase 1（4周）**: P1-BASE-001(后端) + P1-BASE-002(前端) → P1-AUTH-001 → P1-USER-001 → P1-SKILL-001 → P1-WORK-001

**Phase 2（3周）**: P2-PAY-001 → P2-SKILL-001(付费) → P2-BOUNTY-001 → P2-TIP-001

**Phase 3（4周）**: P3-CREDIT-001 → P3-ADMIN-001 → P3-RANK-001 → P3-ARB-001

完整任务列表见 [docs/07-development-tasks.md](docs/07-development-tasks.md)

---

## 注意事项

### 安全相关

- Prompt 注入检测：所有 Skill 提交需通过 ModerationService.auto_review()
- 文件上传：类型白名单 + 大小限制
- 敏感操作：二次确认 + 操作日志
- CORS：仅允许前端域名 (`django-cors-headers`)
- CSRF：Django 内置 CSRF 保护
- 限流：`django-ratelimit` Redis 滑动窗口

### 性能相关

- 热门榜使用 Redis Sorted Set，Celery 定时刷新
- 搜索使用 Meilisearch，不同步到 DB
- 列表分页使用 Cursor-based（非 Offset）
- 后端异步任务使用 Celery + Redis

### 业务约束

- Skill 价格范围：$0.01 ~ $10.00
- 悬赏最低金额：$1.00
- 文章字数：500 ~ 2000 字
- 评价修改轮次：最多 3 轮
- 仲裁冷静期：24 小时

---

## 常用命令

```bash
# ─── 后端 ───
python manage.py runserver          # 启动开发服务器
python manage.py migrate            # 应用数据库迁移
python manage.py makemigrations     # 创建迁移文件
python manage.py seed               # 填充种子数据
python manage.py shell_plus         # Django Shell (django-extensions)
python manage.py createsuperuser    # 创建管理员
celery -A config worker -l info     # 启动 Celery Worker
celery -A config beat -l info       # 启动 Celery Beat
ruff check .                        # 代码检查
mypy .                              # 类型检查
pytest                              # 运行测试

# ─── 前端 ───
pnpm dev                            # 启动开发服务器 (Vite)
pnpm build                          # 构建生产版本
pnpm lint                           # ESLint 检查
pnpm type-check                     # TypeScript 类型检查
pnpm test                           # 运行单元测试
pnpm generate-api                   # 从 OpenAPI Schema 生成 API 客户端
```
