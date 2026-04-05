# CaMeL Community - 项目设计文档

> AI 技能的创作、交易与知识平台

## 文档索引

| 编号 | 文档 | 说明 |
|------|------|------|
| 01 | [项目概述](01-project-overview.md) | 项目定位、用户画像、经济系统、模块协同、邀请机制、项目范围 |
| 02 | [技术架构设计](02-technical-architecture.md) | 技术栈、系统架构图、目录结构、架构决策、缓存策略、环境配置 |
| 03 | [数据库设计](03-database-design.md) | ER 关系、Prisma Schema 完整定义、索引策略、事务场景 |
| 04 | [API 接口设计](04-api-design.md) | tRPC Router 全部接口定义、权限、错误处理、Rate Limiting |
| 05 | [模块详细设计](05-module-design.md) | Skill/Bounty/Workshop 三模块业务逻辑、流程图、算法、信用分系统、通知系统 |
| 06 | [前端页面设计](06-frontend-design.md) | 设计系统、全局布局、各页面线框图、组件清单、响应式断点 |
| 07 | [开发任务分解](07-development-tasks.md) | 117个任务、4个Phase、详细步骤、依赖关系、关键路径 |
| 08 | [部署与运维](08-deployment.md) | 部署架构、CI/CD、监控告警、备份、安全、性能优化、上线检查清单 |
| 09 | [OpenShareHQ 借鉴指南](09-opensharehq-reference.md) | 可借鉴模块、改造建议、不适用部分 |
| 10 | [合并交接说明](10-merge-handoff.md) | 当前工作区实现范围、验证结果、迁移与合并注意事项 |

## 快速导航

### 按角色

- **产品/设计师** → [01 项目概述](01-project-overview.md) → [06 前端设计](06-frontend-design.md)
- **后端开发** → [03 数据库](03-database-design.md) → [04 API](04-api-design.md) → [05 模块设计](05-module-design.md)
- **前端开发** → [06 前端设计](06-frontend-design.md) → [04 API](04-api-design.md)
- **DevOps** → [02 架构](02-technical-architecture.md) → [08 部署](08-deployment.md)
- **项目经理** → [07 任务分解](07-development-tasks.md)

### 按开发阶段

- **Phase 1（3周）** — 基础架构 + 认证 + 用户系统 + Skill 基础 + Workshop 基础 + 邀请
- **Phase 2（3周）** — 支付 + Skill 付费 + Bounty Board + 打赏
- **Phase 3（4周）** — 信用等级特权 + 管理后台 + 排行榜 + 争议仲裁
- **Phase 4（持续）** — 推荐算法 + 系列文章 + 生命周期管理 + 移动端

## 技术栈一览

```
后端: Django 5.2 · Django Ninja · Python 3.12 · Celery
前端: React 18 · Vite 6 · TypeScript · Tailwind CSS · shadcn/ui
数据库: PostgreSQL 16 · Redis · Meilisearch
认证: django-allauth · simplejwt
存储: Cloudflare R2 · Stripe · Resend · Sentry · PostHog
```
