# 00 - 新会话启动说明

> 更新时间：2026-04-06  
> 目的：让任何新对话在 5 分钟内对齐“项目状态 + 开发流程 + 风险点”。

## 1. 必读顺序（不要跳过）

1. `docs/00-session-bootstrap.md`（本文件）
2. `docs/07-development-tasks.md`（当前任务状态看板，已按代码回写）
3. `docs/10-merge-handoff.md`（历史交接背景与冲突提示）
4. `work.md`（阶段性工作记录）

如果文档和代码冲突：**以代码与测试结果为准**。

## 2. 当前状态快照（按代码核对）

- 任务总数：`117`
- `✅ 完成`：`101`
- `🔶 部分完成`：`4`
- `❌ 未完成`：`12`
- 文档状态基线：`docs/07-development-tasks.md` 顶部已标注 `2026-04-06`

### 最近验证结果

- 后端：`cd backend && SECRET_KEY=test uv run pytest -q` → `492 passed`
- 前端：`corepack pnpm -C frontend build` → 构建通过（有 chunk size 警告，不阻塞）

## 3. 新会话先做的 5 分钟检查

```bash
# 1) 看工作区是否脏（避免误覆盖）
git status --short

# 2) 快速确认任务状态文档基线
rg -n "状态回写基线" docs/07-development-tasks.md

# 3) （可选）后端回归
cd backend && SECRET_KEY=test uv run pytest -q

# 4) （可选）前端构建回归
cd .. && corepack pnpm -C frontend build
```

## 4. 已知偏差与风险点（高频踩坑）

1. API 路径现实值是 `/api/`，不是 `docs/04` 中大量示例的 `/api/v1/`。  
2. 支付链路部分完成：后端有 `/payments/checkout` + webhook；前端钱包当前调用 `/payments/deposit`（接口名存在不一致，见 `P2-PAY-002/004`）。
3. 邀请链路部分完成：注册奖励、首充奖励、IP/设备/月上限已落地；`7天活跃校验`、`首月消费奖励`未完整落地。
4. 管理后台仍有占位页：`P3-ADMIN-003/005/006/007/009`。
5. 排行榜未完成：`P3-RANK-002/003/004`。
6. 移动端/PWA/SEO 预渲染未完成：`P4-MOB-*`、`P4-SEO-001`。

## 5. 本地启动（标准）

```bash
# 基础设施
just infra

# 后端（新终端）
cd backend
uv run python manage.py migrate
uv run python manage.py runserver

# Celery（新终端，建议）
cd backend
uv run celery -A config worker -l info

# 前端（新终端）
cd frontend
pnpm dev
```

## 6. 会话收尾要求（建议）

完成功能后至少做：

1. 更新 `docs/07-development-tasks.md` 对应任务状态。  
2. 记录关键结果到 `work.md`（做了什么、验证如何、剩余什么）。  
3. 提供可复现验证命令（测试/构建/关键接口）。  

