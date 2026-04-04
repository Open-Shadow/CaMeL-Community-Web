# 09 - OpenShareHQ 借鉴指南

> 参考仓库：https://github.com/opensharehq/backend
> 本文档说明哪些模块可以直接借鉴、哪些需要改造、哪些不适用。

---

## 项目相似点

| 维度 | OpenShareHQ | CaMeL Community |
|------|-------------|-----------------|
| 框架 | Django 5 | Django 5.2 |
| Python | 3.12+ | 3.12+ |
| 依赖管理 | uv | uv |
| 数据库 | PostgreSQL | PostgreSQL 16 |
| 任务自动化 | Justfile | Justfile |
| 用户系统 | accounts/ | apps/accounts/ |
| 积分/经济系统 | points/ | apps/credits/ + apps/payments/ |
| 通知系统 | messages/ | apps/notifications/ |
| 搜索 | homepage/ | apps/search/ (Meilisearch) |
| 共享工具 | common/ | common/ |

---

## 可直接借鉴的部分

### 1. 项目骨架结构

OpenShareHQ 的 `config/` 目录组织方式（settings、urls、wsgi/asgi）与我们的设计完全一致，可以直接参考：

- `config/settings/` 分层（base / dev / prod）
- `config/urls.py` 主路由组织方式
- `config/celery.py` Celery 配置
- `common/` 共享工具的组织方式

### 2. accounts 模块

OpenShareHQ 的 `accounts/` 包含：
- 用户模型扩展（Profile、地址）
- 社交认证集成

可借鉴：
- 用户 Profile 模型的字段设计
- 社交登录的接入方式（django-allauth）
- 用户相关的 URL 路由组织

### 3. points 模块 → 对应 credits/

OpenShareHQ 的积分池、交易账本设计与我们的信用分系统逻辑相近：

- `CreditLog` 模型设计可参考其交易账本（ledger）模式
- 积分变更的原子性事务处理方式
- 管理命令（management commands）用于批量积分操作

### 4. Justfile 任务命令

可直接复用其 `just run`、`just worker`、`just test`、`just fmt` 等命令定义模式。

### 5. 开发环境配置

- `docker-compose.yml` 中 PostgreSQL + Redis 的配置方式
- `.env.example` 环境变量组织方式

---

## 需要改造的部分

### 1. API 层

OpenShareHQ 使用标准 Django views/templates（非纯 API），我们使用 **Django Ninja**（REST API + OpenAPI 自动生成）。

改造方向：将其 view 逻辑提取为 service 层，再用 Django Ninja Router 包装。

### 2. 积分系统 → 信用分 + $ 额度双轨

OpenShareHQ 只有单一积分体系，我们是 **$ 额度（货币）+ 信用分（声望）** 双轨：

- $ 额度需要对接 Stripe，OpenShareHQ 无此模块
- 信用分等级特权（API 倍率折扣）是我们独有的逻辑

### 3. 认证方式

OpenShareHQ 可能使用 session 认证，我们使用 **JWT**（djangorestframework-simplejwt），需要替换认证中间件。

---

## 不适用的部分

| OpenShareHQ 模块 | 原因 |
|-----------------|------|
| `shop/` 兑换商店 | 我们无实物商品，支付走 Stripe 充值 |
| `chdb/` ClickHouse | 我们用 PostHog 做分析，不需要 ClickHouse |
| `templates/` 前端模板 | 我们是前后端分离，前端独立 React 项目 |

---

## 借鉴操作建议

1. **不要 fork**，手动参考其代码结构，避免引入不需要的依赖
2. 重点阅读：`accounts/models.py`、`points/models.py`、`common/`、`config/`
3. 借鉴时保持我们自己的命名规范（见 CLAUDE.md 开发规范）
4. 所有借鉴的代码需适配 Django Ninja（而非 Django REST Framework 或纯 views）
