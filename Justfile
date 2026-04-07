set shell := ["bash", "-cu"]

# CaMeL Community - 标准一键启停
runtime_dir := ".runtime"

default: up
all: up

# 一键启动（infra + backend + celery + frontend）
up: infra migrate
    mkdir -p {{runtime_dir}}
    if [[ -f {{runtime_dir}}/backend.pid ]] && kill -0 "$(cat {{runtime_dir}}/backend.pid)" 2>/dev/null; then \
      echo "backend already running (pid $(cat {{runtime_dir}}/backend.pid))"; \
    else \
      (cd backend && UV_CACHE_DIR=/tmp/uv-cache nohup uv run python manage.py runserver 0.0.0.0:8000 --noreload > ../{{runtime_dir}}/backend.log 2>&1 &); \
      sleep 1; \
      pgrep -n -f "[m]anage.py runserver 0.0.0.0:8000 --noreload" > {{runtime_dir}}/backend.pid; \
      echo "backend started"; \
    fi
    if [[ -f {{runtime_dir}}/celery.pid ]] && kill -0 "$(cat {{runtime_dir}}/celery.pid)" 2>/dev/null; then \
      echo "celery already running (pid $(cat {{runtime_dir}}/celery.pid))"; \
    else \
      (cd backend && UV_CACHE_DIR=/tmp/uv-cache nohup uv run celery -A config worker -l info > ../{{runtime_dir}}/celery.log 2>&1 &); \
      sleep 1; \
      pgrep -n -f "[c]elery -A config worker -l info" > {{runtime_dir}}/celery.pid; \
      echo "celery started"; \
    fi
    if [[ -f {{runtime_dir}}/frontend.pid ]] && kill -0 "$(cat {{runtime_dir}}/frontend.pid)" 2>/dev/null; then \
      echo "frontend already running (pid $(cat {{runtime_dir}}/frontend.pid))"; \
    else \
      nohup corepack pnpm -C frontend dev --host 0.0.0.0 --port 5173 > {{runtime_dir}}/frontend.log 2>&1 & echo $! > {{runtime_dir}}/frontend.pid; \
      sleep 1; \
      pgrep -n -f "[v]ite --host 0.0.0.0 --port 5173" > {{runtime_dir}}/frontend.pid; \
      echo "frontend started"; \
    fi
    @echo "✅ Up complete"
    @echo "   frontend: http://localhost:5173"
    @echo "   backend:  http://localhost:8000/api/docs"

# 一键关闭（frontend + celery + backend + infra）
down:
    mkdir -p {{runtime_dir}}
    for svc in frontend celery backend; do \
      pid_file="{{runtime_dir}}/${svc}.pid"; \
      if [[ -f "$pid_file" ]]; then \
        pid="$(cat "$pid_file")"; \
        if kill -0 "$pid" 2>/dev/null; then \
          kill "$pid" || true; \
        fi; \
        rm -f "$pid_file"; \
        echo "$svc stopped"; \
      fi; \
    done
    cd backend && docker compose down
    @echo "✅ Down complete"

# 查看运行状态
status:
    @echo "== app pids =="
    @for svc in backend celery frontend; do \
      pid_file="{{runtime_dir}}/${svc}.pid"; \
      if [[ -f "$pid_file" ]]; then \
        pid="$(cat "$pid_file")"; \
        if kill -0 "$pid" 2>/dev/null; then \
          echo "$svc: running (pid $pid)"; \
        else \
          echo "$svc: stale pid ($pid)"; \
        fi; \
      else \
        echo "$svc: not tracked"; \
      fi; \
    done
    @echo "== infra containers =="
    @cd backend && docker compose ps

# 启动基础设施
infra:
    cd backend && docker compose up -d postgres redis meilisearch

# 启动后端（前台）
backend:
    cd backend && uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8000

# 启动前端（前台）
frontend:
    corepack pnpm -C frontend dev --host 0.0.0.0 --port 5173

# 安装所有依赖
install:
    cd backend && uv sync
    corepack pnpm -C frontend install

# 停止基础设施
stop:
    cd backend && docker compose down

# 查看基础设施日志
logs:
    cd backend && docker compose logs -f

# 查看应用日志
logs-app:
    tail -n 200 -f {{runtime_dir}}/backend.log {{runtime_dir}}/celery.log {{runtime_dir}}/frontend.log

# 数据库迁移
migrate:
    cd backend && uv run python manage.py migrate

# 创建迁移文件
makemigrations:
    cd backend && uv run python manage.py makemigrations

# 运行测试
test:
    cd backend && uv run pytest
    corepack pnpm -C frontend test

# 代码检查
lint:
    cd backend && uv run ruff check .
    corepack pnpm -C frontend lint

# Django Shell
shell:
    cd backend && uv run python manage.py shell_plus

# 创建超级用户
superuser:
    cd backend && uv run python manage.py createsuperuser

# 启动 Celery Worker（前台）
worker:
    cd backend && uv run celery -A config worker -l info

# 启动 Celery Beat（前台）
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

# 给指定邮箱账号增加余额（用法：just add-balance email@example.com 20.50）
add-balance email amount:
    cd backend && uv run python manage.py shell -c "import sys; from decimal import Decimal; from apps.accounts.models import User; from apps.payments.services import PaymentsService; email='{{email}}'; raw='{{amount}}'; u=User.objects.filter(email=email).first(); print(f'用户不存在: {email}') if not u else None; sys.exit(1) if not u else None; amt=Decimal(raw); print('金额必须大于 0') if amt <= 0 else None; sys.exit(1) if amt <= 0 else None; before=u.balance; PaymentsService.create_deposit(u, amt, reference_id=f'admin-manual:{email}'); u.refresh_from_db(); print(f'充值成功: {email}  {before} -> {u.balance}')"

# 给指定邮箱账号调整信用分（用法：just add-credit email@example.com 50 或 just add-credit email@example.com -20）
add-credit email amount:
    cd backend && uv run python manage.py shell -c "import sys; from apps.accounts.models import User; from apps.credits.services import CreditService; email='{{email}}'; raw='{{amount}}'; ok=raw.lstrip('-').isdigit(); print(f'分值格式错误: {raw}') if not ok else None; sys.exit(1) if not ok else None; delta=int(raw); print('分值不能为 0') if delta == 0 else None; sys.exit(1) if delta == 0 else None; u=User.objects.filter(email=email).first(); print(f'用户不存在: {email}') if not u else None; sys.exit(1) if not u else None; before=u.credit_score; after=CreditService.admin_adjust(u, delta, reference_id=f'admin-manual:{email}:credit'); print(f'信用分调整成功: {email}  {before} -> {after}')"

reset-db:
    cd backend && docker compose down -v
    cd backend && docker compose up -d postgres redis meilisearch
    cd backend && uv run python manage.py migrate
