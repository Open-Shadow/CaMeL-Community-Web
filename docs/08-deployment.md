# 08 - 部署与运维

## 8.1 部署架构

```
                    ┌─────────────┐
                    │   Cloudflare│
                    │   DNS + CDN │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌──────────┐             ┌──────────────┐
        │  Vercel  │             │ Railway/Render│
        │  React   │             │ Django + Gunicorn│
        │  SPA     │             │ + Celery Worker │
        └──────────┘             └──────┬───────┘
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                  ┌──────────┐  ┌──────────┐  ┌──────────┐
                  │Neon/     │  │ Upstash  │  │Meilisearch│
                  │Supabase  │  │  Redis   │  │  Cloud   │
                  │Postgres  │  │          │  │          │
                  └──────────┘  └──────────┘  └──────────┘
                        │
               ┌────────┴────────┐
               ▼                 ▼
          ┌────────┐        ┌────────┐
          │   R2   │        │ Stripe │
          │  (S3)  │        │        │
          └────────┘        └────────┘
```

---

## 8.2 环境规划

| 环境 | 用途 | 后端 | 前端域名 |
|------|------|------|---------|
| Development | 本地开发 | localhost:8000 | localhost:5173 |
| Preview | PR 预览 | staging DB | pr-xxx.camelcommunity.com |
| Staging | 上线前测试 | Staging DB | staging.camelcommunity.com |
| Production | 正式环境 | Production DB | camelcommunity.com |

---

## 8.3 CI/CD 流水线

### 8.3.1 后端 CI（GitHub Actions）

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths: ['backend/**']
  pull_request:
    branches: [main]
    paths: ['backend/**']

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd backend && uv sync
      - run: cd backend && uv run ruff check .
      - run: cd backend && uv run mypy .

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: camel_test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd backend && uv sync
      - run: cd backend && uv run python manage.py migrate
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/camel_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SETTINGS_MODULE: config.settings.test
      - run: cd backend && uv run pytest
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/camel_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SETTINGS_MODULE: config.settings.test
```

### 8.3.2 前端 CI（GitHub Actions）

```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths: ['frontend/**']
  pull_request:
    branches: [main]
    paths: ['frontend/**']

jobs:
  lint-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd frontend && pnpm install --frozen-lockfile
      - run: cd frontend && pnpm lint
      - run: cd frontend && pnpm type-check
      - run: cd frontend && pnpm build
```

### 8.3.3 部署流程

```
PR 提交
  │
  ├─ 后端 CI（lint + test）
  ├─ 前端 CI（lint + type-check + build）
  ├─ Vercel Preview 自动部署（前端）
  │
  ▼
PR Merge 到 main
  │
  ├─ 后端：Railway/Render 自动部署
  │   └─ python manage.py migrate（release command）
  ├─ 前端：Vercel Production 自动部署
  └─ Meilisearch 索引同步（Django management command）
```

---

## 8.4 后端部署（Railway / Render）

### 8.4.1 Procfile / 启动命令

```
# Procfile
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
worker: celery -A config worker -l info
beat: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
release: python manage.py migrate
```

### 8.4.2 生产环境配置

```python
# config/settings/prod.py
from .base import *

DEBUG = False
ALLOWED_HOSTS = [env("ALLOWED_HOSTS")]

# 数据库
DATABASES = {
    "default": env.db("DATABASE_URL")
}

# Redis
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

# 静态文件（Whitenoise）
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# 存储（Cloudflare R2）
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_S3_ENDPOINT_URL = env("R2_ENDPOINT_URL")
AWS_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("R2_BUCKET_NAME")

# Sentry
import sentry_sdk
sentry_sdk.init(dsn=env("SENTRY_DSN"), traces_sample_rate=0.1)
```

### 8.4.3 环境变量清单（后端）

```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
ALLOWED_HOSTS=api.camelcommunity.com
DJANGO_SETTINGS_MODULE=config.settings.prod
CORS_ALLOWED_ORIGINS=https://camelcommunity.com

# OAuth
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Stripe
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...

# Storage
R2_ENDPOINT_URL=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...

# Search
MEILISEARCH_URL=...
MEILISEARCH_MASTER_KEY=...

# Email
RESEND_API_KEY=...

# Monitoring
SENTRY_DSN=...
```

---

## 8.5 前端部署（Vercel）

### 8.5.1 Vercel 配置

```json
// vercel.json
{
  "buildCommand": "pnpm build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

### 8.5.2 环境变量清单（前端）

```
VITE_API_BASE_URL=https://api.camelcommunity.com
VITE_STRIPE_PUBLISHABLE_KEY=...
VITE_POSTHOG_KEY=...
VITE_SENTRY_DSN=...
```

---

## 8.6 数据库迁移策略

```
开发阶段：
├── python manage.py makemigrations --name <描述>
├── python manage.py migrate
└── python manage.py seed   → 填充种子数据

部署阶段（自动）：
├── python manage.py migrate   → release command 自动执行
└── 失败时 Railway/Render 自动回滚部署

规范：
├── 不使用 migrate --fake（生产禁止）
├── 每次迁移有明确的描述名称
├── 破坏性变更分多次迁移执行
└── 保留所有迁移历史记录
```

---

## 8.7 监控与告警

### 8.7.1 应用监控（Sentry）

```
监控项：
├── 未捕获异常 (Unhandled Exceptions)
├── API 错误率 (4xx / 5xx)
├── 性能指标 (Web Vitals: LCP, FID, CLS)
├── 慢查询（API 响应 > 3s）
└── 前端运行时错误

告警规则：
├── 5xx 错误率 > 1% → Slack 告警
├── P99 延迟 > 5s → Slack 告警
└── 未捕获异常 > 10次/小时 → 紧急告警
```

### 8.7.2 业务监控（PostHog）

```
关键事件：
├── 用户注册 / 登录
├── Skill 创建 / 调用
├── 悬赏发布 / 完成
├── 文章发布 / 投票
├── 充值 / 交易
└── 邀请注册

关键漏斗：
├── 注册 → 首次 Skill 调用 → 首次付费
├── 浏览 Skill → 调用 → 评价
└── 浏览悬赏 → 申请 → 完成
```

### 8.7.3 基础设施监控

| 监控项 | 工具 | 告警阈值 |
|--------|------|---------|
| PostgreSQL 连接数 | Neon Dashboard | > 80% |
| Redis 内存使用 | Upstash Console | > 70% |
| Django API 响应时间 | Sentry Performance | > 3s |
| 存储用量 | R2 Dashboard | > 80% 容量 |
| Stripe 支付成功率 | Stripe Dashboard | < 95% |
| Celery 队列积压 | Flower / Redis | > 100 任务 |

---

## 8.8 备份策略

| 数据 | 备份频率 | 保留期限 | 方式 |
|------|---------|---------|------|
| PostgreSQL 数据库 | 每日自动 | 30 天 | Neon/Supabase 自动备份 |
| 对象存储文件 | 实时冗余 | 永久 | R2 多区域复制 |
| Redis 数据 | RDB 快照 | 7 天 | Upstash 自动 |
| 迁移历史 | Git 版本控制 | 永久 | 随代码库 |

---

## 8.9 安全运维

### 8.9.1 Secret 管理

```
环境变量管理：
├── 本地开发：.env（gitignore）
├── CI/CD：GitHub Secrets
├── Railway/Render：Environment Variables（加密存储）
└── 禁止：硬编码密钥、提交 .env 文件

密钥轮换：
├── Django SECRET_KEY：每季度轮换
├── Stripe Key：Stripe 控制台轮换
├── DB 密码：每半年轮换
└── OAuth Client Secret：按需轮换
```

### 8.9.2 安全扫描

```
自动化扫描：
├── Dependabot：依赖漏洞自动检测
├── GitHub CodeQL：代码安全分析
├── uv audit / pip-audit：Python 依赖审计
├── pnpm audit：前端依赖审计
└── 人工：季度安全评审
```

---

## 8.10 性能优化

### 8.10.1 后端性能

| 优化项 | 措施 |
|--------|------|
| 数据库查询 | select_related / prefetch_related 防 N+1 + 索引优化 |
| 缓存 | Redis 多层缓存（django-redis）+ stale-while-revalidate |
| 分页 | Cursor-based 分页（非 Offset） |
| 异步任务 | Celery 队列处理耗时操作（邮件、通知、排行榜更新） |
| 搜索 | Meilisearch 独立搜索服务 |
| 连接池 | django-db-geventpool 或 PgBouncer |

### 8.10.2 前端性能

| 优化项 | 措施 |
|--------|------|
| 代码分割 | Vite 动态 import + React.lazy |
| 图片 | WebP + 懒加载 |
| 预渲染 | react-snap 预渲染 SEO 关键页面（Skill 详情、文章详情） |
| 字体 | 字体子集化 + preload |
| CSS | Tailwind Purge 无用样式 |

**目标 Web Vitals**：

| 指标 | 目标 |
|------|------|
| LCP | < 2.5s |
| FID | < 100ms |
| CLS | < 0.1 |
| TTFB | < 600ms |

---

## 8.11 本地开发环境搭建

```bash
# 1. 克隆仓库
git clone <repo-url>
cd camel-community

# 2. 启动基础设施（Docker）
docker compose up -d postgres redis meilisearch

# 3. 后端
cd backend
uv sync
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py seed
uv run python manage.py runserver        # http://localhost:8000

# 另开终端启动 Celery
uv run celery -A config worker -l info

# 4. 前端
cd frontend
pnpm install
cp .env.example .env.local
pnpm dev                                  # http://localhost:5173
```

### Docker Compose（本地开发）

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: camel
      POSTGRES_PASSWORD: camel_dev
      POSTGRES_DB: camel_community
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  meilisearch:
    image: getmeili/meilisearch:v1.11
    environment:
      MEILI_MASTER_KEY: dev_master_key
    ports:
      - "7700:7700"
    volumes:
      - msdata:/meili_data

volumes:
  pgdata:
  msdata:
```

---

## 8.12 上线检查清单

### Phase 1 上线前

```
□ 所有 CI 测试通过（后端 + 前端）
□ 数据库迁移验证（staging 环境先跑）
□ 环境变量全部配置（后端 + 前端）
□ CORS 配置正确（CORS_ALLOWED_ORIGINS）
□ JWT 密钥配置（SECRET_KEY）
□ OAuth 提供商回调 URL 正确
□ Stripe Webhook 端点验证
□ Sentry DSN 配置（后端 + 前端）
□ Meilisearch 索引创建
□ 种子数据加载（分类、管理员账户）
□ SSL 证书配置
□ 域名 DNS 解析（前端 + 后端 API 子域名）
□ 错误页面（404, 500）测试
□ 响应式布局基本验证
□ 安全 Headers 配置（Django SECURE_* 设置）
□ Celery Worker 正常运行
□ django-ratelimit 限流配置验证
```
