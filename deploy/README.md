# 服务器部署指南（Docker Compose 生产版）

这套部署会启动以下服务：
- `frontend`：Nginx + React 静态文件（对外暴露 `80`）
- `backend`：Django + Gunicorn
- `worker` / `beat`：Celery Worker / Beat
- `postgres` / `redis` / `meilisearch`

## 1. 服务器准备

在 Ubuntu 22.04+ 安装：

```bash
sudo apt-get update
sudo apt-get install -y git curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 重新登录后生效
```

## 2. 拉取代码并准备配置

```bash
git clone <your-repo-url> CaMeL_Community_Web
cd CaMeL_Community_Web
cp deploy/.env.example deploy/.env
cp deploy/backend.prod.env.example deploy/backend.prod.env
```

必须修改：
- `deploy/.env`：`POSTGRES_PASSWORD`、`MEILI_MASTER_KEY`
- `deploy/backend.prod.env`：`SECRET_KEY`、`ALLOWED_HOSTS`、`CORS_ALLOWED_ORIGINS`、`CSRF_TRUSTED_ORIGINS`

如果你启用 HTTPS（推荐），请保持：
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`

## 3. 首次启动

```bash
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

检查状态：

```bash
docker compose --env-file .env -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.prod.yml logs -f backend
```

访问：
- 前端主页：`http://<服务器IP或域名>/`
- API 文档：`http://<服务器IP或域名>/api/docs`

## 4. 日常更新发布

```bash
cd ~/CaMeL_Community_Web
git pull
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

## 5. 常用运维命令

```bash
# 查看所有日志
docker compose --env-file .env -f docker-compose.prod.yml logs -f

# 仅看 celery worker
docker compose --env-file .env -f docker-compose.prod.yml logs -f worker

# 重启后端
docker compose --env-file .env -f docker-compose.prod.yml restart backend

# 停服
docker compose --env-file .env -f docker-compose.prod.yml down
```

## 6. 反向代理与 HTTPS

当前 compose 暴露 `80` 端口。生产建议在外层接入：
- Cloudflare + 源站证书，或
- 宿主机 Nginx / Caddy 做 TLS 终止并反向代理到 `127.0.0.1:80`

配置 HTTPS 后，`backend.prod.env` 中保留 `SECURE_SSL_REDIRECT=True` 可强制全站 HTTPS。
