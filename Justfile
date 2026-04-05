# CaMeL Community - 一键启动

# 启动所有服务（基础设施 + 后端 + 前端）
all: infra backend frontend

# 启动基础设施
infra:
    cd backend && docker compose up -d

# 启动后端
backend:
    cd backend && uv run python manage.py migrate && uv run python manage.py runserver

# 启动前端
frontend:
    cd frontend && pnpm dev

# 安装所有依赖
install:
    cd backend && uv sync
    cd frontend && pnpm install

# 停止基础设施
stop:
    cd backend && docker compose down

# 查看日志
logs:
    cd backend && docker compose logs -f

# 数据库迁移
migrate:
    cd backend && uv run python manage.py migrate

# 创建迁移文件
makemigrations:
    cd backend && uv run python manage.py makemigrations

# 运行测试
test:
    cd backend && uv run pytest
    cd frontend && pnpm test

# 代码检查
lint:
    cd backend && uv run ruff check .
    cd frontend && pnpm lint

# Django Shell
shell:
    cd backend && uv run python manage.py shell_plus

# 创建超级用户
superuser:
    cd backend && uv run python manage.py createsuperuser

# 启动 Celery Worker
worker:
    cd backend && uv run celery -A config worker -l info

# 启动 Celery Beat
beat:
    cd backend && uv run celery -A config beat -l info

# 仅启动基础设施 + Celery worker（后台）
infra-only:
    cd backend && docker compose up -d postgres redis meilisearch
    cd backend && uv run celery -A config worker -l info --detach --logfile=celery.log --pidfile=celery.pid
    @echo "✅ 基础设施 + Celery worker 已启动，日志: backend/celery.log"

# 停止 Celery worker
stop-worker:
    cd backend && uv run celery -A config control shutdown 2>/dev/null || true

# 删除指定邮箱用户（用法：just delete-user email@example.com）
delete-user email:
    cd backend && uv run python manage.py shell -c "from apps.accounts.models import User; u = User.objects.filter(email='{{email}}'); print(f'找到 {u.count()} 个账号'); u.delete(); print('已删除')"
reset-db:
    cd backend && docker compose down -v && docker compose up -d postgres redis meilisearch && uv run python manage.py migrate
