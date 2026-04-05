# Work Log - Claude Code 工作记录

> 本文件记录 Claude Code 已完成的工作，便于跨会话追踪进度。
>
> **详细任务状态**: 参见 [docs/07-development-tasks.md](docs/07-development-tasks.md)，每行任务末尾有完成状态。

---

## 2026-04-05: 项目骨架搭建

### P1-BASE 任务完成情况

| 任务 | 状态 | 说明 |
|------|------|------|
| P1-BASE-001 | ✅ | Django 项目 + 8个 apps + pyproject.toml |
| P1-BASE-002 | ✅ | Vite + React + TypeScript + Tailwind |
| P1-BASE-003 | ✅ | 所有 Models + 迁移文件 |
| P1-BASE-004 | ✅ | API router + permissions + exceptions + CORS |
| P1-BASE-005 | ✅ | django-redis 配置 |
| P1-BASE-006 | ✅ | python-decouple + .env.example |
| P1-BASE-007 | ✅ | Header + Footer + Layout + React Router v7 |
| P1-BASE-008 | ❌ | shadcn/ui 未安装 |
| P1-BASE-009 | 🔶 | SearchBar + Pagination 已创建，缺其他组件 |
| P1-BASE-010 | ❌ | API 客户端未生成 |
| P1-BASE-011 | 🔶 | 前端工具函数已创建，后端未实现 |

### 完成内容

#### 后端 (Django)
- [x] 初始化 Django 5.2 项目结构
- [x] 创建 8 个 Django 应用：
  - `accounts` - 用户管理、认证
  - `skills` - 技能市场
  - `bounties` - 悬赏任务板
  - `workshop` - 知识工坊
  - `payments` - 支付与交易
  - `credits` - 信用分系统
  - `notifications` - 通知系统
  - `search` - 搜索集成
- [x] 数据库 Models 全部完成：
  - User, Invitation (accounts)
  - Skill, SkillVersion, SkillCall, SkillReview (skills)
  - Bounty, BountyApplication, BountyDeliverable, Arbitration, ArbitrationVote, BountyComment (bounties)
  - Article, Series, Comment, Vote, Tip (workshop)
  - Transaction (payments)
  - CreditLog (credits)
  - Notification (notifications)
- [x] 初始迁移文件已生成
- [x] 配置文件：JWT 认证、CORS、Redis 缓存、Celery、Meilisearch
- [x] docker-compose.yml（PostgreSQL 16, Redis 7, Meilisearch）
- [x] Justfile 常用命令
- [x] .env.example 环境变量模板

#### 前端 (React + Vite)
- [x] Vite 6 + React 18 + TypeScript 项目初始化
- [x] Tailwind CSS 配置
- [x] React Router v7 路由配置（所有页面）
- [x] Zustand 状态管理（authStore）
- [x] 组件结构：
  - Layout（Header, Footer）
  - CreditBadge, UserAvatar
  - SkillCard, BountyCard, ArticleCard
  - SearchBar, Pagination
- [x] Hooks：useAuth, useCredit
- [x] TypeScript 类型定义
- [x] 构建验证通过

#### 其他
- [x] 根目录 Justfile（一键启动）
- [x] .gitignore
- [x] GitHub 首次提交并推送

### 验证状态
| 检查项 | 状态 |
|--------|------|
| Django 系统检查 | ✅ 通过 |
| 数据库迁移生成 | ✅ 完成 |
| TypeScript 类型检查 | ✅ 通过 |
| 前端构建 | ✅ 通过 |
| GitHub 推送 | ✅ 完成 |

### 修复的问题
1. `INSTALLED_APPS` 添加 `django.contrib.postgres`
2. `tsconfig.node.json` 添加 `composite: true` 和 `types: ["node"]`
3. 添加 `@types/node` 依赖
4. 添加 `vite-env.d.ts` 类型定义

## 2026-04-05: 基础任务补全 (P1-BASE-008/009/011)

### 完成情况

| 任务 | 状态 | 说明 |
|------|------|------|
| P1-BASE-008 | ✅ | shadcn/ui 基础组件安装完成 |
| P1-BASE-009 | ✅ | 通用共享组件全部完成 |
| P1-BASE-011 | ✅ | 后端工具函数实现完成 |

### 完成内容

#### P1-BASE-008: shadcn/ui 组件
已安装组件 (frontend/src/components/ui/):
- [button](frontend/src/components/ui/button.tsx), [card](frontend/src/components/ui/card.tsx), [dialog](frontend/src/components/ui/dialog.tsx), [input](frontend/src/components/ui/input.tsx)
- [select](frontend/src/components/ui/select.tsx), [tabs](frontend/src/components/ui/tabs.tsx), [toast](frontend/src/components/ui/toast.tsx), [badge](frontend/src/components/ui/badge.tsx)
- [avatar](frontend/src/components/ui/avatar.tsx), [dropdown-menu](frontend/src/components/ui/dropdown-menu.tsx), [skeleton](frontend/src/components/ui/skeleton.tsx)

配置更新：
- [components.json](frontend/components.json) - shadcn 配置
- [tailwind.config.ts](frontend/tailwind.config.ts) - 添加 CSS 变量和动画
- [globals.css](frontend/src/styles/globals.css) - CSS 变量定义

#### P1-BASE-009: 通用共享组件
新建组件 (frontend/src/components/shared/):
- [tag-input.tsx](frontend/src/components/shared/tag-input.tsx) - 标签输入组件，支持回车添加/删除
- [empty-state.tsx](frontend/src/components/shared/empty-state.tsx) - 空状态展示
- [loading-skeleton.tsx](frontend/src/components/shared/loading-skeleton.tsx) - Skill/Bounty/Article/列表/网格骨架屏
- [confirm-dialog.tsx](frontend/src/components/shared/confirm-dialog.tsx) - 确认对话框，支持 danger 变体

#### P1-BASE-011: 后端工具函数
新建文件 (backend/common/):
- [constants.py](backend/common/constants.py) - 信用等级体系、业务常量、缓存键前缀
- [utils.py](backend/common/utils.py) - 日期格式化、金额格式化、文本处理、随机生成、缓存键生成

### P1-BASE-010 状态更新
API 客户端生成需要等待 P1-AUTH-001 完成后才有可用的 API endpoints，延后到认证模块完成后执行。

---

## 2026-04-05: 认证与用户模块 (Week 1.5 & Week 2)

### P1-AUTH 任务完成情况

| 任务 | 状态 | 说明 |
|------|------|------|
| P1-AUTH-001 | ✅ | django-allauth + JWT 配置完成 |
| P1-AUTH-002 | ✅ | Email 密码注册/登录 API 完成 |
| P1-AUTH-007 | ✅ | 登录/注册页面 UI 完成 |
| P1-AUTH-008 | ✅ | JWT 权限中间件 (AuthBearer) 已存在 |
| P1-AUTH-009 | ✅ | useAuth Hook 完成 |

### P1-USER 任务完成情况

| 任务 | 状态 | 说明 |
|------|------|------|
| P1-USER-001 | ✅ | 用户 API Router (get_me, update_profile, etc.) |
| P1-USER-004 | ✅ | CreditService 实现完成 |
| P1-USER-002 | ✅ | 个人资料设置页完成 |
| P1-USER-005 | ✅ | CreditBadge, CreditProgress, UserAvatar 组件 |

### 完成内容

#### 后端 (Django)

**认证 API** ([apps/accounts/api.py](backend/apps/accounts/api.py)):
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/refresh` - 刷新 Token
- `POST /auth/logout` - 用户登出
- `GET /auth/me` - 获取当前用户信息

**用户 API** ([apps/accounts/user_api.py](backend/apps/accounts/user_api.py)):
- `GET /users/me` - 获取个人资料
- `PATCH /users/me` - 更新个人资料
- `POST /users/me/avatar` - 上传头像
- `GET /users/me/stats` - 获取统计数据
- `POST /users/me/password` - 修改密码
- `GET /users/{id}` - 获取公开资料
- `GET /users/{id}/stats` - 获取公开统计
- `GET /users/me/credit-history` - 信用分历史

**信用分服务** ([apps/credits/services.py](backend/apps/credits/services.py)):
- `add_credit()` - 增加信用分
- `deduct_credit()` - 扣除信用分
- `calculate_level()` - 计算等级
- `get_discount_rate()` - 获取 API 折扣
- 权限检查: `can_post_bounty()`, `can_apply_bounty()`, `can_arbitrate()`

**路由更新** ([config/api.py](backend/config/api.py)):
- 注册 `/auth/` 路由
- 注册 `/users/` 路由

#### 前端 (React)

**认证 Hook** ([hooks/use-auth.tsx](frontend/src/hooks/use-auth.tsx)):
- `useAuth()` - 认证状态管理
- `login()`, `register()`, `logout()` 方法
- Token 自动刷新
- Axios 实例配置

**登录/注册页面**:
- [pages/auth/login.tsx](frontend/src/pages/auth/login.tsx) - 登录页面
- [pages/auth/register.tsx](frontend/src/pages/auth/register.tsx) - 注册页面

**用户组件**:
- [components/user/credit-badge.tsx](frontend/src/components/user/credit-badge.tsx) - 等级徽章
- [components/user/credit-progress.tsx](frontend/src/components/user/credit-progress.tsx) - 等级进度条
- [components/user/user-avatar.tsx](frontend/src/components/user/user-avatar.tsx) - 用户头像

**个人资料页面** ([pages/profile/settings.tsx](frontend/src/pages/profile/settings.tsx)):
- 基本信息编辑
- 头像上传
- 密码修改
- 信用分展示
- 信用分历史

**路由更新** ([app/router.tsx](frontend/src/app/router.tsx)):
- 添加 `/login`, `/register`
- 添加 `/profile/settings`

**Providers 更新** ([app/providers.tsx](frontend/src/app/providers.tsx)):
- 添加 `AuthProvider` 包裹

### API 端点汇总

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/auth/register | 注册 | 否 |
| POST | /api/auth/login | 登录 | 否 |
| POST | /api/auth/refresh | 刷新 Token | 否 |
| POST | /api/auth/logout | 登出 | 否 |
| GET | /api/auth/me | 当前用户 | 是 |
| GET | /api/users/me | 个人资料 | 是 |
| PATCH | /api/users/me | 更新资料 | 是 |
| POST | /api/users/me/avatar | 上传头像 | 是 |
| GET | /api/users/me/stats | 个人统计 | 是 |
| POST | /api/users/me/password | 修改密码 | 是 |
| GET | /api/users/{id} | 公开资料 | 是 |
| GET | /api/users/me/credit-history | 信用历史 | 是 |

---

## 2026-04-05: 认证完善 + 用户功能 (Week 2 后半)

### 完成任务

| 任务 | 状态 | 说明 |
|------|------|------|
| P1-AUTH-003 | ✅ | GitHub OAuth（授权 URL 生成 + code 换 JWT） |
| P1-AUTH-004 | ✅ | Google OAuth（授权 URL 生成 + code 换 JWT） |
| P1-AUTH-005 | ✅ | 邮箱验证（注册时发送验证邮件，token 存 Redis，3天有效） |
| P1-AUTH-006 | ✅ | 忘记/重置密码（发送重置邮件，token 存 Redis，1小时有效） |
| P1-USER-003 | ✅ | 公开用户页 `/u/:username`（头像、等级、信用分、统计数据） |
| P1-USER-006 | ✅ | 信用分历史页 `/profile/credit-history` |
| P1-USER-007 | ✅ | 头像上传（后端 S3/R2 + 本地 fallback，前端上传组件含类型/大小校验） |

### 新增文件

#### 后端
- `apps/accounts/api.py` — 新增端点：
  - `GET /auth/oauth/{provider}/url` — 获取 OAuth 授权 URL
  - `POST /auth/oauth/callback` — code 换 JWT
  - `POST /auth/verify-email` — 邮箱验证
  - `POST /auth/resend-verification` — 重发验证邮件
  - `POST /auth/forgot-password` — 发送重置邮件
  - `POST /auth/reset-password` — 重置密码
- `apps/accounts/user_api.py` — 新增端点：
  - `GET /users/by-username/{username}` — 按用户名查公开资料
  - `GET /users/by-username/{username}/stats` — 按用户名查统计
  - `POST /users/me/avatar` — 头像上传（S3/R2 + 本地 fallback）
- `config/settings/base.py` — 新增：OAuth 配置、邮件配置、S3 存储配置

#### 前端
- `pages/auth/oauth-callback.tsx` — OAuth 回调页
- `pages/auth/forgot-password.tsx` — 忘记密码页
- `pages/auth/reset-password.tsx` — 重置密码页
- `pages/auth/verify-email.tsx` — 邮箱验证页
- `pages/profile/public-profile.tsx` — 公开用户页 `/u/:username`
- `pages/profile/credit-history.tsx` — 信用分历史页
- `components/user/avatar-upload.tsx` — 头像上传组件
- `hooks/use-auth.tsx` — 新增 `loginWithTokens()` 方法
- `app/router.tsx` — 注册所有新路由

### 验证状态
| 检查项 | 状态 |
|--------|------|
| Django 系统检查 | ✅ 通过（0 issues） |
| TypeScript 类型检查 | ✅ 通过 |

*最后更新: 2026-04-05*


## 2026-04-05: 通知系统 + 邀请系统 (Week 3)

### 完成任务

| 任务 | 状态 | 说明 |
|------|------|------|
| P1-USER-008 | ✅ | 通知系统后端 NotificationService（send, send_bulk, list, mark_read, mark_all_read, unread_count） |
| P1-USER-009 | ✅ | 通知系统前端（NotificationBell 组件 + 通知列表页 + SSE 实时推送 + useNotifications Hook） |
| P1-INV-001 | ✅ | 邀请码生成与验证（InvitationService：generate, validate, apply） |
| P1-INV-002 | ✅ | 邀请奖励发放（Celery tasks：注册奖励 +10 信用分，首充奖励 +$0.50） |
| P1-INV-003 | ✅ | 邀请页面（邀请码展示 + 统计 + 分享链接 + 邀请记录 + 规则说明） |
| P1-INV-004 | ✅ | 反刷机制（IP 限频 3次/天 + 月度上限 20 + 自引用检测 + 7天活跃校验） |

### 新增文件

#### 后端
- `apps/notifications/services.py` — NotificationService 完整实现
- `apps/notifications/api.py` — 通知 API 端点：
  - `GET /notifications/` — 通知列表
  - `GET /notifications/unread-count` — 未读计数
  - `POST /notifications/{id}/read` — 标记已读
  - `POST /notifications/read-all` — 全部已读
  - `GET /notifications/stream` — SSE 实时推送
- `apps/accounts/services.py` — InvitationService 完整实现
- `apps/accounts/invitation_api.py` — 邀请 API 端点：
  - `POST /invitations/generate` — 生成邀请码
  - `GET /invitations/stats` — 邀请统计
  - `GET /invitations/list` — 邀请记录
  - `POST /invitations/validate` — 验证邀请码（公开）
- `apps/accounts/tasks.py` — Celery 任务：
  - `grant_invite_register_reward` — 注册即时奖励
  - `check_first_deposit_reward` — 首充延迟奖励
- `config/api.py` — 注册 `/invitations/` 路由

#### 前端
- `hooks/use-notifications.ts` — 通知 Hook（SSE + 状态管理）
- `components/shared/notification-bell.tsx` — 导航栏通知铃铛组件
- `pages/notifications/NotificationsPage.tsx` — 通知列表页
- `pages/profile/invitation.tsx` — 邀请页面
- `pages/auth/register.tsx` — 注册页增加邀请码输入 + 注册成功后提示验证邮箱
- `components/layout/Header.tsx` — 导航栏增加认证状态、通知铃铛、邀请入口

### 验证状态
| 检查项 | 状态 |
|--------|------|
| Django 系统检查 | ✅ 通过（0 issues） |
| TypeScript 类型检查 | ✅ 通过 |
| 前端构建 | ✅ 通过 |

*最后更新: 2026-04-05*


## 2026-04-05: 支付系统 (Week 4-5 / Phase 2)

### 完成任务

| 任务 | 状态 | 说明 |
|------|------|------|
| P2-PAY-001 | ✅ | Stripe 集成（stripe Python SDK 配置，Checkout Session 创建） |
| P2-PAY-002 | ✅ | 充值流程（create_deposit → Stripe Checkout → Webhook → 余额到账 + 邀请首充奖励） |
| P2-PAY-003 | ✅ | TransactionService（deposit/deduct/credit/freeze/unfreeze/list/income_summary） |
| P2-PAY-004 | ✅ | 钱包页面（余额/冻结/收入展示 + 快捷充值 + 交易记录） |
| P2-PAY-005 | ✅ | 导航栏余额组件（BalanceDisplay，点击跳转钱包页） |

### 新增文件

#### 后端
- `apps/payments/services.py` — TransactionService 完整实现
- `apps/payments/webhooks.py` — Stripe Webhook 处理（checkout.session.completed）
- `apps/payments/api.py` — 支付 API 端点：
  - `POST /payments/deposit` — 创建 Stripe Checkout Session
  - `GET /payments/balance` — 获取余额
  - `GET /payments/transactions` — 交易记录列表
  - `GET /payments/income-summary` — 收入汇总
- `config/urls.py` — 注册 `/webhooks/stripe/` 路由

#### 前端
- `pages/wallet/WalletPage.tsx` — 钱包页面（充值 + 交易记录 Tab）
- `components/shared/balance-display.tsx` — 导航栏余额组件
- `components/layout/Header.tsx` — 增加余额显示

### 验证状态
| 检查项 | 状态 |
|--------|------|
| Django 系统检查 | ✅ 通过（0 issues） |
| TypeScript 类型检查 | ✅ 通过 |
| 前端构建 | ✅ 通过 |

*最后更新: 2026-04-05*


## 2026-04-05: 打赏系统 (Sprint 2.4)

### 完成任务

| 任务 | 状态 | 说明 |
|------|------|------|
| P2-TIP-001 | ✅ | TipService + 打赏 API 端点（send/list/leaderboard） |
| P2-TIP-002 | ✅ | TipDialog 组件（快捷金额 + 自定义 + 确认） |
| P2-TIP-003 | ✅ | 打赏排行榜（Redis 缓存 7天 + 前端页面） |
| P2-TIP-004 | ✅ | 文章详情页打赏按钮 + 打赏记录展示 |

### 新增文件

#### 后端
- `apps/workshop/services.py` — TipService（5% 平台手续费，atomic 事务）
- `apps/workshop/api.py` — 端点：`POST /workshop/articles/{id}/tip`、`GET /workshop/articles/{id}/tips`、`GET /workshop/tips/leaderboard`

#### 前端
- `components/workshop/tip-dialog.tsx` — 打赏对话框
- `pages/workshop/ArticleDetailPage.tsx` — 文章详情页（打赏按钮 + 记录）
- `pages/workshop/TipLeaderboardPage.tsx` — 打赏排行榜页
- `app/router.tsx` — 注册 `/workshop/tips/leaderboard` 路由

### 验证状态
| 检查项 | 状态 |
|--------|------|
| Django 系统检查 | ✅ 通过（0 issues） |
| TypeScript 类型检查 | ✅ 通过 |

*最后更新: 2026-04-05*


## 2026-04-05: 验收测试 - 邮件系统修复

### 问题排查与修复

#### 问题1: 注册后收不到验证邮件
**根本原因**: `fail_silently=True` 吞掉 SMTP 错误，任务耗时 134 秒后静默失败。
**修复**: `apps/accounts/tasks.py` 中 `fail_silently=True` → `fail_silently=False`

#### 问题2: CORS 错误导致注册失败
**根本原因**: 访问 `127.0.0.1:5173` 但 CORS 只允许 `localhost:5173`。
**修复**: `.env` 的 `CORS_ALLOWED_ORIGINS` 同时包含两个 origin。

#### 问题3: 注册卡在"注册中..."
**根本原因**: 同步 `send_mail` 阻塞请求，SMTP 超时导致挂起。
**修复**: 改为 Celery 异步任务 `send_verification_email.delay()`。

### 注意事项
- Celery worker 必须运行才能发送邮件（`just infra-only` 已包含）
- Gmail App Password 必须是 16 位无空格

### 验证状态
| 检查项 | 状态 |
|--------|------|
| 注册流程 | ✅ 通过 |
| 验证邮件发送 | ✅ 通过 |
| 邮箱验证链接 | ✅ 通过 |
| 登录流程 | ✅ 通过 |

*最后更新: 2026-04-05*
