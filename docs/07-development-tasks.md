# 07 - 开发任务分解

## 任务编号规则

```
格式：P{phase}-{module}-{sequence}
示例：P1-BASE-001

Phase: P1 / P2 / P3 / P4
Module: BASE(基础) / AUTH(认证) / USER(用户) / SKILL(技能市场) / BOUNTY(悬赏) / WORK(工坊) / PAY(支付) / TIP(打赏) / CREDIT(信用) / ADMIN(管理) / INV(邀请) / RANK(排行) / ARB(仲裁) / REC(推荐) / SER(系列) / LIFE(生命周期) / MOB(移动端)

标注：[B] = 后端任务  [F] = 前端任务  [B+F] = 前后端联合任务
```

---

## 架构说明

本项目采用 **前后端分离** 架构，分为两个独立的代码仓库：


| 端      | 技术栈                                                       | 目录          |
| ------ | --------------------------------------------------------- | ----------- |
| **后端** | Django 5.2 + Django Ninja + Celery + PostgreSQL + Redis   | `backend/`  |
| **前端** | React 18 + Vite 6 + TypeScript + Tailwind CSS + shadcn/ui | `frontend/` |


前后端通过 **Django Ninja 自动生成的 OpenAPI Schema** 保持类型同步，前端使用 `openapi-typescript-codegen` 生成类型安全的 API 客户端。

---

## Phase 1：基础架构 + 核心功能（4周）

### Sprint 1.1：项目初始化与基础架构（第1周）


| 任务ID        | 任务名称                  | 端     | 描述                                                                                           | 优先级 | 预估  | 依赖       | 状态                               | 负责人 |
| ----------- | --------------------- | ----- | -------------------------------------------------------------------------------------------- | --- | --- | -------- | -------------------------------- | --- |
| P1-BASE-001 | 后端项目脚手架               | [B]   | Django 项目初始化，创建所有 apps，配置 pyproject.toml + uv                                                | P0  | 3h  | -        | ✅ 完成                             | A   |
| P1-BASE-002 | 前端项目脚手架               | [F]   | Vite + React + TypeScript 项目初始化，配置 Tailwind CSS                                              | P0  | 2h  | -        | ✅ 完成                             | A   |
| P1-BASE-003 | 数据库模型定义               | [B]   | 编写所有 Django apps 的 ORM Models，执行首次迁移                                                         | P0  | 5h  | 001      | ✅ 完成                             | A   |
| P1-BASE-004 | Django Ninja API 基础配置 | [B]   | 配置 API router、权限类、异常处理中间件、CORS                                                               | P0  | 3h  | 001      | ✅ 完成                             | A   |
| P1-BASE-005 | Redis 连接配置            | [B]   | 配置 django-redis，封装缓存工具函数                                                                     | P0  | 1h  | 001      | ✅ 完成                             | A   |
| P1-BASE-006 | 环境变量管理                | [B]   | 配置 python-decouple，创建 .env.example 文件                                                        | P0  | 1h  | 001      | ✅ 完成                             | A   |
| P1-BASE-007 | 全局布局组件                | [F]   | Header（导航栏）、Footer、MainLayout，配置 React Router v7                                             | P0  | 4h  | 002      | ✅ 完成                             | A   |
| P1-BASE-008 | shadcn/ui 组件安装        | [F]   | 安装常用基础组件：Button, Card, Dialog, Input, Select, Tabs, Toast, Badge, Avatar, Dropdown, Skeleton | P0  | 2h  | 002      | ✅ 完成                             | A   |
| P1-BASE-009 | 通用共享组件                | [F]   | SearchBar, Pagination, TagInput, EmptyState, LoadingSkeleton, ConfirmDialog                  | P1  | 4h  | 008      | ✅ 完成                             | A   |
| P1-BASE-010 | API 客户端生成             | [F]   | 基于 Django Ninja 的 OpenAPI Schema，使用 openapi-typescript-codegen 生成类型安全的 API 客户端               | P0  | 3h  | 004      | ✅ 完成（使用手写类型化 API 客户端 + OpenAPI codegen 脚本备用） | A   |
| P1-BASE-011 | 工具函数库                 | [B+F] | 后端：utils（格式化、常量）；前端：utils.ts + constants.ts（日期、金额格式化、枚举映射）                                   | P1  | 2h  | 001, 002 | ✅ 完成                             | A   |


#### P1-BASE-001 详细步骤（后端脚手架）

```bash
# 1. 创建项目目录并初始化
mkdir backend && cd backend
uv init
uv add django django-ninja django-cors-headers django-environ
uv add djangorestframework-simplejwt django-allauth[socialaccount]
uv add psycopg2-binary django-redis celery[redis]
uv add stripe sentry-sdk[django] django-storages boto3
uv add django-ratelimit meilisearch Pillow

# 2. 创建 Django 项目
django-admin startproject config .

# 3. 创建业务 apps
python manage.py startapp accounts
python manage.py startapp skills
python manage.py startapp bounties
python manage.py startapp workshop
python manage.py startapp payments
python manage.py startapp credits
python manage.py startapp notifications
python manage.py startapp search

# 4. 目录结构
# backend/
# ├── config/              # Django 项目配置
# │   ├── settings/        # 拆分 settings（base/dev/prod）
# │   ├── urls.py
# │   ├── celery.py
# │   └── wsgi.py
# ├── accounts/            # 用户 & 认证
# ├── skills/              # 技能市场
# ├── bounties/            # 悬赏板
# ├── workshop/            # 知识工坊
# ├── payments/            # 支付 & 交易
# ├── credits/             # 信用分系统
# ├── notifications/       # 通知系统
# ├── search/              # Meilisearch 集成
# ├── common/              # 公共工具（权限、分页、异常）
# ├── manage.py
# └── pyproject.toml
```

#### P1-BASE-002 详细步骤（前端脚手架）

```bash
# 1. 创建 Vite 项目
npm create vite@latest frontend -- --template react-ts

# 2. 安装核心依赖
cd frontend
pnpm add react-router-dom @tanstack/react-query zustand
pnpm add react-helmet-async dayjs dompurify
pnpm add @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder
pnpm add recharts framer-motion
pnpm add -D tailwindcss postcss autoprefixer
pnpm add -D openapi-typescript-codegen

# 3. 初始化 shadcn/ui
npx shadcn@latest init

# 4. 安装基础组件
npx shadcn@latest add button card dialog input select tabs toast badge avatar dropdown-menu skeleton

# 5. 目录结构
# frontend/
# ├── src/
# │   ├── api/             # openapi-typescript-codegen 生成的 API 客户端
# │   ├── components/      # React 组件
# │   │   ├── ui/          # shadcn/ui 基础组件
# │   │   ├── layout/      # 布局组件
# │   │   ├── skill/       # Skill 相关组件
# │   │   ├── bounty/      # Bounty 相关组件
# │   │   ├── workshop/    # Workshop 相关组件
# │   │   ├── user/        # 用户相关组件
# │   │   └── shared/      # 共享组件
# │   ├── hooks/           # 自定义 Hooks
# │   ├── lib/             # 工具库
# │   ├── pages/           # 页面组件
# │   ├── stores/          # Zustand 状态管理
# │   ├── types/           # TypeScript 类型
# │   ├── router.tsx       # React Router v7 路由配置
# │   ├── App.tsx
# │   └── main.tsx
# ├── index.html
# ├── vite.config.ts
# ├── tailwind.config.ts
# └── package.json
```

#### P1-BASE-003 详细步骤（数据库模型）

```
1. 将 docs/03-database-design.md 中的数据模型转换为 Django ORM Models
2. 每个 app 编写独立的 models.py
   - accounts/models.py: User, UserProfile, Invitation
   - skills/models.py: Skill, SkillVersion, SkillCall, SkillReview
   - bounties/models.py: Bounty, BountyApplication, BountyDelivery, BountyReview
   - workshop/models.py: Article, Comment, Vote, Series, SeriesArticle
   - payments/models.py: Transaction, Deposit, Tip
   - credits/models.py: CreditLog
   - notifications/models.py: Notification
3. 配置 DATABASE_URL（PostgreSQL）
4. 运行 python manage.py makemigrations && python manage.py migrate
5. 创建 management command: seed_data（种子数据）
```

#### P1-BASE-004 详细步骤（Django Ninja API 配置）

```
1. 创建 config/api.py
   - 初始化 NinjaAPI 实例
   - 配置 OpenAPI schema 自动生成（title、version、description）
   - 注册所有 app 的 router

2. 创建 common/permissions.py
   - 定义权限类：IsAuthenticated, IsModerator, IsAdmin
   - 基于 simplejwt 的 JWT 认证

3. 创建 common/middleware.py
   - CORS 配置（django-cors-headers）
   - 请求日志中间件
   - 异常处理（统一错误响应格式）

4. 创建 common/pagination.py
   - 基于 Cursor 的分页器（非 Offset）

5. 配置 config/urls.py
   - 挂载 /api/ 路由
   - 挂载 /api/docs（OpenAPI 文档）
```

---

### Sprint 1.2：认证系统（第1周后半 ~ 第2周前半）


| 任务ID        | 任务名称                    | 端     | 描述                                                  | 优先级 | 预估  | 依赖                 | 状态   | 负责人 |
| ----------- | ----------------------- | ----- | --------------------------------------------------- | --- | --- | ------------------ | ---- | --- |
| P1-AUTH-001 | django-allauth + JWT 配置 | [B]   | 配置 django-allauth + simplejwt，JWT access/refresh 策略 | P0  | 3h  | BASE-003           | ✅ 完成 | A   |
| P1-AUTH-002 | Email 密码注册/登录 API       | [B]   | 注册、登录、登出接口，密码哈希（Django 内置）                          | P0  | 4h  | AUTH-001           | ✅ 完成 | A   |
| P1-AUTH-003 | GitHub OAuth            | [B]   | 配置 django-allauth GitHub Provider，返回 JWT            | P1  | 2h  | AUTH-001           | ✅ 完成 | A   |
| P1-AUTH-004 | Google OAuth            | [B]   | 配置 django-allauth Google Provider，返回 JWT            | P1  | 2h  | AUTH-001           | ✅ 完成 | A   |
| P1-AUTH-005 | 邮箱验证                    | [B]   | django-allauth 内置邮箱验证流程 + 自定义模板                     | P1  | 2h  | AUTH-002           | ✅ 完成 | A   |
| P1-AUTH-006 | 忘记密码/重置密码               | [B]   | 重置密码 API + 邮件发送                                     | P1  | 3h  | AUTH-002           | ✅ 完成 | A   |
| P1-AUTH-007 | 登录/注册页面                 | [F]   | 登录页、注册页 UI（含 OAuth 按钮），对接后端 API                     | P0  | 4h  | AUTH-001, BASE-010 | ✅ 完成 | A   |
| P1-AUTH-008 | Auth 中间件                | [B+F] | 后端：JWT 权限校验；前端：路由守卫（/profile, /admin 等）             | P0  | 3h  | AUTH-001, BASE-007 | ✅ 完成 | A   |
| P1-AUTH-009 | useAuth Hook            | [F]   | useAuth() hook：JWT 存储/刷新、获取当前用户信息、登出                | P0  | 2h  | AUTH-001, BASE-010 | ✅ 完成 | A   |


---

### Sprint 1.3：用户系统与信用分（第2周）


| 任务ID        | 任务名称          | 端     | 描述                                                                        | 优先级 | 预估  | 依赖                 | 状态   | 负责人 |
| ----------- | ------------- | ----- | ------------------------------------------------------------------------- | --- | --- | ------------------ | ---- | --- |
| P1-USER-001 | 用户 API Router | [B]   | Django Ninja userRouter：get_me, update_profile, get_profile, get_my_stats | P0  | 4h  | AUTH-001, BASE-004 | ✅ 完成 | A   |
| P1-USER-002 | 个人资料设置页       | [F]   | 编辑显示名、头像、简介                                                               | P0  | 3h  | USER-001, BASE-010 | ✅ 完成 | A   |
| P1-USER-003 | 公开用户页         | [F]   | /u/:username 公开资料页，展示统计数据和贡献                                              | P1  | 3h  | USER-001           | ✅ 完成 | A   |
| P1-USER-004 | 信用分服务         | [B]   | CreditService：add_credit, deduct_credit, calculate_level（Django 服务层）      | P0  | 4h  | BASE-003           | ✅ 完成 | A   |
| P1-USER-005 | 信用分 UI 组件     | [F]   | CreditBadge（等级徽章）、CreditProgress（进度条）、等级特权展示                              | P0  | 3h  | USER-004, BASE-010 | ✅ 完成 | A   |
| P1-USER-006 | 信用分历史页        | [F]   | 信用分变动记录列表                                                                 | P1  | 2h  | USER-004           | ✅ 完成 | A   |
| P1-USER-007 | 头像上传          | [B+F] | 后端：Django 文件上传 API（django-storages + S3/R2）；前端：上传组件 + 裁剪                  | P1  | 3h  | USER-001           | ✅ 完成 | A   |
| P1-USER-008 | 通知系统后端        | [B]   | NotificationService：send, mark_read, list（Django 服务层）                     | P1  | 3h  | BASE-003           | ✅ 完成 | A   |
| P1-USER-009 | 通知系统前端        | [F]   | NotificationBell 组件 + 通知列表页 + SSE 实时推送                                    | P1  | 4h  | USER-008, BASE-010 | ✅ 完成 | A   |


---

### Sprint 1.4：Skill Marketplace 基础版（第2~3周）


| 任务ID         | 任务名称                    | 端   | 描述                                                                      | 优先级 | 预估  | 依赖                  | 状态    | 负责人 |
| ------------ | ----------------------- | --- | ----------------------------------------------------------------------- | --- | --- | ------------------- | ----- | --- |
| P1-SKILL-001 | Skill API Router (CRUD) | [B] | Django Ninja skillRouter：create, update, get_by_id, list, get_my_skills | P0  | 6h  | BASE-004, BASE-003  | ✅ 完成 | B   |
| P1-SKILL-002 | Skill 创建页面              | [F] | 表单页面：名称、描述、Prompt、分类、标签、定价（Phase1 免费优先）                                 | P0  | 5h  | SKILL-001, BASE-010 | ✅ 完成 | B   |
| P1-SKILL-003 | Skill 详情页               | [F] | 完整详情展示 + 试用面板（调用 Skill）                                                 | P0  | 6h  | SKILL-001           | ✅ 完成 | B   |
| P1-SKILL-004 | Skill 市场首页              | [F] | 卡片网格列表 + 分类筛选 + 搜索 + 排序                                                 | P0  | 5h  | SKILL-001           | ✅ 完成 | B   |
| P1-SKILL-005 | SkillCard 组件            | [F] | 卡片组件：图标、名称、描述、评分、价格、创作者                                                 | P0  | 2h  | BASE-008            | ✅ 完成 | B   |
| P1-SKILL-006 | Skill 调用逻辑              | [B] | call API：输入 → 执行 → 返回结果（Phase1 免费，无扣费）                                  | P0  | 4h  | SKILL-001           | ✅ 完成 | B   |
| P1-SKILL-007 | Skill 自动审核              | [B] | ModerationService（Python 实现）：安全扫描（jailbreak/injection 检测）               | P1  | 4h  | SKILL-001           | ✅ 完成 | B   |
| P1-SKILL-008 | Skill 提交审核流程            | [B] | submit_for_review：DRAFT → PENDING_REVIEW → APPROVED/REJECTED            | P0  | 3h  | SKILL-007           | ✅ 完成 | B   |
| P1-SKILL-009 | 我的 Skill 页面             | [F] | 创作者后台：Skill 列表 + 状态管理 + 基础统计                                            | P1  | 4h  | SKILL-001, BASE-010 | ✅ 完成 | B   |
| P1-SKILL-010 | Meilisearch 搜索集成        | [B] | Skill 数据同步到 Meilisearch，全文搜索 API（自定义集成或 django-meilisearch）             | P1  | 4h  | SKILL-001, BASE-005 | ✅ 完成 | B   |

---

### Sprint 1.5：Workshop 基础版（第3~4周）


| 任务ID        | 任务名称                       | 端     | 描述                                                                           | 优先级 | 预估  | 依赖                           | 状态                               | 负责人 |
| ----------- | -------------------------- | ----- | ---------------------------------------------------------------------------- | --- | --- | ---------------------------- | -------------------------------- | --- |
| P1-WORK-001 | Workshop API Router (CRUD) | [B]   | Django Ninja workshopRouter：create, update, publish, delete, list, get_by_id | P0  | 5h  | BASE-004, BASE-003           | ✅ 完成                             | B   |
| P1-WORK-002 | Tiptap 富文本编辑器组件            | [F]   | 基于 @tiptap/react 的编辑器，内置模板（Problem/Solution/Result），支持 Markdown 输入           | P0  | 6h  | BASE-008                     | ✅ 完成                             | B   |
| P1-WORK-003 | 文章渲染组件                     | [F]   | 客户端渲染：代码高亮、表格、图片、Skill 卡片嵌入                                                  | P0  | 4h  | BASE-008                     | ✅ 完成                             | B   |
| P1-WORK-004 | 写文章页面                      | [F]   | 文章编辑页：标题、内容、标签、难度、类型、关联 Skill                                                | P0  | 5h  | WORK-001, WORK-002, BASE-010 | ✅ 完成                             | B   |
| P1-WORK-005 | 文章详情页                      | [F]   | 完整文章展示 + 投票 + 评论 + 打赏 + 关联 Skill                                             | P0  | 6h  | WORK-001, WORK-003           | 🔶 基础版完成（打赏占位，正式支付待 P2-TIP） | B   |
| P1-WORK-006 | 文章列表页                      | [F]   | 列表 + 筛选（难度/类型/模型）+ 排序 + 搜索                                                   | P0  | 4h  | WORK-001, BASE-010           | ✅ 完成                             | B   |
| P1-WORK-007 | 投票系统                       | [B+F] | vote/remove_vote API：权重按信用等级，净票数计算；前端投票组件                                    | P0  | 3h  | WORK-001, USER-004           | ✅ 完成                             | B   |
| P1-WORK-008 | 评论系统                       | [B+F] | add_comment API + 一层回复 + 作者置顶 + 投票折叠；前端评论组件                                  | P1  | 5h  | WORK-001                     | 🔶 基础版完成（评论投票折叠待后续增强）   | B   |
| P1-WORK-009 | 文章搜索（Meilisearch）          | [B]   | 文章数据同步 + 全文搜索 API                                                            | P1  | 3h  | SKILL-010                    | ✅ 完成                             | B   |

---

### Sprint 1.6：邀请系统（第4周）


| 任务ID       | 任务名称     | 端   | 描述                                          | 优先级 | 预估  | 依赖                | 状态   | 负责人 |
| ---------- | -------- | --- | ------------------------------------------- | --- | --- | ----------------- | ---- | --- |
| P1-INV-001 | 邀请码生成与验证 | [B] | 生成唯一邀请码，注册时绑定邀请关系                           | P1  | 3h  | AUTH-002          | ✅ 完成 | A   |
| P1-INV-002 | 邀请奖励发放   | [B] | 注册奖励（即时）+ 首充奖励（延迟）+ 消费奖励（延迟），使用 Celery 异步处理 | P1  | 4h  | INV-001, USER-004 | ✅ 完成 | A   |
| P1-INV-003 | 邀请页面     | [F] | 邀请码展示 + 邀请统计 + 分享链接                         | P1  | 3h  | INV-001, BASE-010 | ✅ 完成 | A   |
| P1-INV-004 | 反刷机制     | [B] | IP/设备检测 + 7天活跃校验 + 月度上限                     | P2  | 3h  | INV-001           | ✅ 完成 | A   |


---

## Phase 2：交易闭环（3周）

### Sprint 2.1：支付系统（第5周）


| 任务ID       | 任务名称           | 端     | 描述                                                                           | 优先级 | 预估  | 依赖                         | 状态   | 负责人 |
| ---------- | -------------- | ----- | ---------------------------------------------------------------------------- | --- | --- | -------------------------- | ---- | --- |
| P2-PAY-001 | Stripe 集成      | [B]   | 使用 stripe Python SDK，配置 Stripe 密钥和产品                                         | P0  | 4h  | BASE-003                   | ✅ 完成 | A   |
| P2-PAY-002 | 充值流程           | [B+F] | create_deposit_session → Stripe Checkout → Django Webhook 视图 → Celery 异步余额到账 | P0  | 6h  | PAY-001                    | ✅ 完成 | A   |
| P2-PAY-003 | Transaction 服务 | [B]   | TransactionService（Django 服务层）：记录交易流水，查询余额，生成报表                              | P0  | 4h  | BASE-003                   | ✅ 完成 | A   |
| P2-PAY-004 | 钱包页面           | [F]   | 余额展示 + 充值入口 + 交易记录 + 收入报表                                                    | P0  | 5h  | PAY-002, PAY-003, BASE-010 | ✅ 完成 | A   |
| P2-PAY-005 | 余额组件           | [F]   | 导航栏余额展示 + 充值快捷入口                                                             | P1  | 2h  | PAY-003, BASE-010          | ✅ 完成 | A   |


### Sprint 2.2：Skill 付费交易（第5~6周）


| 任务ID         | 任务名称        | 端     | 描述                                                   | 优先级 | 预估  | 依赖                     | 负责人 |
| ------------ | ----------- | ----- | ---------------------------------------------------- | --- | --- | ---------------------- | --- |
| P2-SKILL-001 | 付费 Skill 支持 | [B]   | 扩展 call 逻辑：余额校验 → 扣费 → 分成 → 记录交易（transaction.atomic） | P0  | 5h  | PAY-003, P1-SKILL-006  | B   |
| P2-SKILL-002 | 创作者收入看板     | [F]   | 详细统计：调用趋势图（recharts）、收入明细、评分分布                       | P0  | 5h  | PAY-003, BASE-010      | B   |
| P2-SKILL-003 | Skill 评价系统  | [B]   | add_review, update_review API + 防刷规则 + 评分计算（去极端值）    | P0  | 4h  | P1-SKILL-001           | B   |
| P2-SKILL-004 | Skill 评价 UI | [F]   | 评价表单 + 评价列表 + 评分统计                                   | P0  | 3h  | SKILL-003, BASE-010    | B   |
| P2-SKILL-005 | 版本管理        | [B+F] | 版本历史 + 锁定版本 + 重大更新通知                                 | P1  | 4h  | P1-SKILL-001           | B   |
| P2-SKILL-006 | 热门榜 + 精选    | [B]   | Redis Sorted Set 排行榜 + 运营精选 + Celery Beat 定时刷新任务     | P1  | 4h  | P1-SKILL-010, BASE-005 | B   |


### Sprint 2.3：Bounty Board 完整版（第6~7周）


| 任务ID          | 任务名称              | 端     | 描述                                                                                                | 优先级 | 预估  | 依赖                   | 负责人 |
| ------------- | ----------------- | ----- | ------------------------------------------------------------------------------------------------- | --- | --- | -------------------- | --- |
| P2-BOUNTY-001 | Bounty API Router | [B]   | Django Ninja bountyRouter：create, list, get_by_id, apply, accept, submit, approve, reject, cancel | P0  | 8h  | BASE-004, PAY-003    | B   |
| P2-BOUNTY-002 | 托管机制              | [B]   | 发布悬赏时冻结 $ → 验收后释放并划转 → 取消后解冻（transaction.atomic）                                                  | P0  | 6h  | PAY-003              | B   |
| P2-BOUNTY-003 | 悬赏列表页             | [F]   | 列表 + 筛选（类型/状态/金额）+ 排序 + 搜索                                                                        | P0  | 4h  | BOUNTY-001, BASE-010 | B   |
| P2-BOUNTY-004 | 发布悬赏页面            | [F]   | 表单：标题、描述、类型、金额、截止时间、附件、技能要求                                                                       | P0  | 4h  | BOUNTY-001, BASE-010 | B   |
| P2-BOUNTY-005 | 悬赏详情页             | [F]   | 完整详情 + 状态时间线 + 申请列表 + 沟通评论区                                                                       | P0  | 6h  | BOUNTY-001           | B   |
| P2-BOUNTY-006 | 申请接单流程            | [B+F] | 申请表单 + 发布者审核申请列表 + 接受/拒绝                                                                          | P0  | 4h  | BOUNTY-001           | B   |
| P2-BOUNTY-007 | 交付与验收流程           | [B+F] | 提交交付物 → 验收通过/要求修改(<=3轮)/拒绝 → 结算                                                                   | P0  | 6h  | BOUNTY-002           | B   |
| P2-BOUNTY-008 | BountyCard 组件     | [F]   | 卡片：标题、金额、状态、类型、发布者、申请人数                                                                           | P0  | 2h  | BASE-008             | B   |
| P2-BOUNTY-009 | BountyTimeline 组件 | [F]   | 状态时间线组件                                                                                           | P1  | 3h  | BASE-008             | B   |
| P2-BOUNTY-010 | 我的悬赏页面            | [F]   | 发布者视角 + 接单者视角（切换 Tab）                                                                             | P1  | 4h  | BOUNTY-001, BASE-010 | B   |
| P2-BOUNTY-011 | 悬赏超时处理            | [B]   | Celery Beat 定时任务：检测超时 → 释放任务 → 扣信用分 → 冷门标记                                                        | P1  | 3h  | BOUNTY-001, USER-004 | B   |
| P2-BOUNTY-012 | 双方互评              | [B+F] | 完成后互评：质量、沟通、响应速度                                                                                  | P1  | 3h  | BOUNTY-007           | B   |


### Sprint 2.4：打赏功能（第7周）


| 任务ID       | 任务名称   | 端     | 描述                                               | 优先级 | 预估  | 依赖                | 负责人  |
| ---------- | ------ | ----- | ------------------------------------------------ | --- | --- | ----------------- | ---- |
| P2-TIP-001 | 打赏后端逻辑 | [B]   | tip API：余额扣减 → 转账 → 记录 → 信用分（transaction.atomic） | P0  | 3h  | PAY-003           | ✅ 完成 |
| P2-TIP-002 | 打赏 UI  | [F]   | TipDialog 组件：快捷金额 + 自定义 + 确认                     | P0  | 3h  | TIP-001, BASE-010 | ✅ 完成 |
| P2-TIP-003 | 打赏排行榜  | [B+F] | 按累计收到打赏排序 + 每周更新 + Redis 缓存                      | P1  | 3h  | TIP-001           | ✅ 完成 |
| P2-TIP-004 | 打赏记录展示 | [F]   | 文章详情页显示打赏记录                                      | P1  | 2h  | TIP-001, BASE-010 | ✅ 完成 |


---

## Phase 3：运营工具（4周）

### Sprint 3.1：信用等级特权（第8周）


| 任务ID          | 任务名称     | 端   | 描述                   | 优先级 | 预估  | 依赖          | 状态   | 负责人 |
| ------------- | -------- | --- | -------------------- | --- | --- | ----------- | ---- | --- |
| P3-CREDIT-001 | API 倍率折扣 | [B] | Skill 调用时根据等级计算折扣价格  | P0  | 3h  | P1-USER-004 | ✅ 完成 | A   |
| P3-CREDIT-002 | 等级门槛校验   | [B] | 悬赏发布/接单的信用分门槛检查      | P0  | 2h  | P1-USER-004 | ✅ 完成 | A   |
| P3-CREDIT-003 | 等级可视化增强  | [F] | 头像等级框、特效、VIP 标识      | P1  | 4h  | P1-USER-005 | ✅ 完成 | A   |
| P3-CREDIT-004 | 悬赏板冻结逻辑  | [B] | 信用分 < 30 自动冻结 + 恢复检查 | P1  | 2h  | P1-USER-004 | ✅ 完成 | A   |


### Sprint 3.2：管理后台（第8~9周）


| 任务ID         | 任务名称      | 端     | 描述                                                | 优先级 | 预估  | 依赖                   | 状态   | 负责人 |
| ------------ | --------- | ----- | ------------------------------------------------- | --- | --- | -------------------- | ---- | --- |
| P3-ADMIN-001 | Admin 布局  | [F]   | 管理后台侧边栏布局 + 权限路由守卫                                | P0  | 3h  | P1-AUTH-008          | ✅ 完成 | A   |
| P3-ADMIN-002 | 仪表盘       | [B+F] | 平台概览数据 API + 前端展示：用户数、Skill数、文章数、流水额（recharts 图表） | P0  | 4h  | P2-PAY-003           | ✅ 完成 | A   |
| P3-ADMIN-003 | Skill 审核页 | [B+F] | 后端审核 API + 前端：待审核列表 + 审核操作（通过/拒绝 + 理由）+ 预览        | P0  | 5h  | P1-SKILL-008         | A   |
| P3-ADMIN-004 | 用户管理页     | [B+F] | 后端用户管理 API + 前端：用户列表 + 搜索 + 封禁/解封 + 角色调整          | P0  | 4h  | P1-USER-001          | ✅ 完成 | A   |
| P3-ADMIN-005 | 文章管理页     | [B+F] | 文章管理 API + 前端：文章列表 + 归档 + 删除                      | P1  | 3h  | P1-WORK-001          | A   |
| P3-ADMIN-006 | 加精队列页     | [B+F] | 待加精文章列表（净票数 >= 10）+ 加精/跳过操作                       | P0  | 4h  | P1-WORK-007          | A   |
| P3-ADMIN-007 | 悬赏管理页     | [B+F] | 悬赏管理 API + 前端：悬赏列表 + 强制结算/取消                      | P1  | 3h  | P2-BOUNTY-001        | A   |
| P3-ADMIN-008 | 财务管理页     | [B+F] | 财务统计 API + 前端：充值统计 + 手续费收入 + $ 流通量 + 趋势图          | P1  | 5h  | P2-PAY-003           | ✅ 完成 | A   |
| P3-ADMIN-009 | 精选管理      | [B+F] | Skill 精选设置 + Workshop 精选管理                        | P1  | 3h  | ADMIN-003, ADMIN-006 | A   |


### Sprint 3.3：排行榜与数据看板（第9~10周）


| 任务ID        | 任务名称      | 端   | 描述                                              | 优先级 | 预估  | 依赖                     | 状态   | 负责人 |
| ----------- | --------- | --- | ----------------------------------------------- | --- | --- | ---------------------- | ---- | --- |
| P3-RANK-001 | 信用分排行榜    | [B+F] | Top 50 用户 + Redis cache + Celery Beat 定时更新 + 前端排行榜页面 | P1  | 3h  | P1-USER-004            | ✅ 完成 | A   |
| P3-RANK-002 | Skill 热门榜 | [B] | 近7天调用量 x 评分排序 + 每小时刷新（Celery Beat）              | P1  | 3h  | P2-SKILL-006           | ❌ 未完成 | A   |
| P3-RANK-003 | 创作者排行榜    | [B] | 按总收入/总调用/信用分排序                                  | P2  | 3h  | P2-SKILL-002           | ❌ 未完成 | A   |
| P3-RANK-004 | 排行榜页面     | [F] | 统一排行榜展示页面（Tab切换不同榜单）                            | P1  | 4h  | RANK-001~003, BASE-010 | ❌ 未完成 | A   |


### Sprint 3.4：争议仲裁系统（第10~11周）


| 任务ID       | 任务名称    | 端     | 描述                                       | 优先级 | 预估  | 依赖                     | 负责人 |
| ---------- | ------- | ----- | ---------------------------------------- | --- | --- | ---------------------- | --- |
| P3-ARB-001 | 争议触发流程  | [B]   | 拒绝验收 → 冷静期(24h) → 提交陈述（Celery 延迟任务管理冷静期） | P0  | 4h  | P2-BOUNTY-007          | B   |
| P3-ARB-002 | 仲裁团组建   | [B]   | 随机抽取3名专家级用户 + 关联排除                       | P0  | 4h  | ARB-001, P1-USER-004   | B   |
| P3-ARB-003 | 仲裁投票系统  | [B]   | 匿名投票 + 结果计算（多数票/中位数比例）                   | P0  | 5h  | ARB-002                | B   |
| P3-ARB-004 | 仲裁结算    | [B]   | 根据结果划转/退回 $ + 信用分调整（transaction.atomic）  | P0  | 4h  | ARB-003, P2-BOUNTY-002 | B   |
| P3-ARB-005 | 上诉流程    | [B]   | 上诉申请 + $0.50 上诉费 + 管理员终审                 | P1  | 4h  | ARB-004                | B   |
| P3-ARB-006 | 仲裁 UI   | [F]   | 仲裁面板 + 陈述提交 + 投票界面 + 结果展示                | P0  | 5h  | ARB-001~005, BASE-010  | B   |
| P3-ARB-007 | 管理后台争议页 | [B+F] | 活跃争议列表 + 终审操作                            | P1  | 3h  | ARB-005, P3-ADMIN-001  | B   |


---

## Phase 4：持续迭代（持续进行）

### Sprint 4.1：推荐与个性化


| 任务ID       | 任务名称       | 端   | 描述                                | 优先级 | 预估  | 依赖                         | 负责人 |
| ---------- | ---------- | --- | --------------------------------- | --- | --- | -------------------------- | --- |
| P4-REC-001 | Skill 推荐算法 | [B] | 基于用户调用历史 + 标签偏好的协同推荐（Celery 离线计算） | P2  | 8h  | P2-SKILL-001               | B   |
| P4-REC-002 | 文章推荐       | [B] | 基于阅读历史 + 标签的相关推荐                  | P2  | 6h  | P1-WORK-001                | B   |
| P4-REC-003 | 搜索算法优化     | [B] | Meilisearch 搜索排序权重调优 + A/B 测试     | P2  | 6h  | P1-SKILL-010               | B   |
| P4-REC-004 | 个性化首页      | [F] | 根据用户行为定制首页展示                      | P2  | 5h  | REC-001, REC-002, BASE-010 | B   |


### Sprint 4.2：系列文章


| 任务ID       | 任务名称    | 端   | 描述                                                 | 优先级 | 预估  | 依赖                | 负责人 |
| ---------- | ------- | --- | -------------------------------------------------- | --- | --- | ----------------- | --- |
| P4-SER-001 | 系列 CRUD | [B] | create_series, update_series, reorder_articles API | P2  | 4h  | P1-WORK-001       | B   |
| P4-SER-002 | 系列目录页   | [F] | 系列信息 + 有序文章列表 + 整体收藏                               | P2  | 4h  | SER-001, BASE-010 | B   |
| P4-SER-003 | 系列完成奖励  | [B] | >=3篇 → 作者 +$1.00 + 30 信用分（Celery 异步发放）             | P2  | 2h  | SER-001           | B   |


### Sprint 4.3：内容生命周期管理


| 任务ID        | 任务名称   | 端   | 描述                                            | 优先级 | 预估  | 依赖          | 负责人 |
| ----------- | ------ | --- | --------------------------------------------- | --- | --- | ----------- | --- |
| P4-LIFE-001 | 过时标记   | [B] | 模型版本检测 + 自动提示                                 | P2  | 3h  | P1-WORK-001 | B   |
| P4-LIFE-002 | 自动归档   | [B] | 6个月无更新 + 净票数 < 5 → 归档（Celery Beat 定时任务）       | P2  | 2h  | P1-WORK-001 | B   |
| P4-LIFE-003 | 数据清理任务 | [B] | Celery Beat 定时任务：SkillCall 聚合、通知清理、Session 清理 | P2  | 3h  | BASE-005    | B   |


### Sprint 4.4：移动端适配与 PWA


| 任务ID       | 任务名称   | 端     | 描述                                                  | 优先级 | 预估  | 依赖      | 负责人 |
| ---------- | ------ | ----- | --------------------------------------------------- | --- | --- | ------- | --- |
| P4-MOB-001 | 响应式优化  | [F]   | 全站响应式适配（手机端核心页面）                                    | P2  | 8h  | 全部 UI   | A   |
| P4-MOB-002 | PWA 配置 | [F]   | Vite PWA 插件 + manifest.json + Service Worker + 离线支持 | P2  | 4h  | MOB-001 | A   |
| P4-MOB-003 | 推送通知   | [B+F] | Web Push Notification（后端推送服务 + 前端接收）                | P3  | 4h  | MOB-002 | A   |


### Sprint 4.5：SEO 优化


| 任务ID       | 任务名称  | 端   | 描述                                                  | 优先级 | 预估  | 依赖   | 负责人 |
| ---------- | ----- | --- | --------------------------------------------------- | --- | --- | ---- | --- |
| P4-SEO-001 | 预渲染方案 | [F] | 配置 react-snap 或 prerender.io，关键页面预渲染（Skill 详情、文章详情） | P2  | 5h  | 全部页面 | A   |


---

## 任务统计


| Phase   | 任务数       | 预估总工时     | 周期         |
| ------- | --------- | --------- | ---------- |
| Phase 1 | 45 个      | ~160h     | 4 周        |
| Phase 2 | 25 个      | ~100h     | 3 周        |
| Phase 3 | 22 个      | ~85h      | 4 周        |
| Phase 4 | 13 个      | ~60h      | 持续迭代       |
| **总计**  | **105 个** | **~405h** | **~11+ 周** |


> 相比单体 Next.js 架构，前后端分离增加了约 30h 的工时（API 客户端生成、认证双端配置、独立部署配置等），但带来了更好的关注点分离和独立部署能力。

---

## 任务依赖关键路径

```
P1-BASE-001 (后端) ──► P1-BASE-003 (Models) ──► P1-AUTH-001 ──► P1-USER-001
P1-BASE-002 (前端) ──► P1-BASE-007 (Layout) ──► P1-AUTH-007 (Auth UI)
                                                        │
P1-BASE-004 (API setup) ──► P1-BASE-010 (API client) ──┘
                                                        ▼
                    P1-SKILL-001 ──► P2-SKILL-001 ──► P2-PAY-001
                                                        │
                                                        ▼
                                                   P2-BOUNTY-001 ──► P3-ARB-001
```

关键路径：**后端脚手架 → 数据库模型 → 认证 → 用户系统 → 信用分 → 支付 → 交易闭环 → 仲裁**

并行路径：前端脚手架和后端脚手架可以同时进行；在 API 客户端生成（P1-BASE-010）完成后，前端页面开发可以与后端 API 开发并行推进。

### 前后端并行开发策略

```
后端开发流程：
  Django Model → Django Ninja Router → Service Layer → Celery Tasks
  （每完成一个 Router，自动更新 OpenAPI Schema）

前端开发流程：
  Layout + UI 组件 → API 客户端生成 → 页面开发 → 联调
  （可先使用 Mock 数据开发页面，再对接真实 API）

协作节点：
  ► OpenAPI Schema 变更时，前端重新生成 API 客户端
  ► 共享 .env.example 中的环境变量约定
  ► 统一错误码和分页格式（在 P1-BASE-004 中定义）
```

每个 Sprint 可并行执行非关键路径任务，前后端开发者可各自独立推进，在联调阶段汇合，加速整体开发进度。