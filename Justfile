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
