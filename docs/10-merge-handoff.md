# 10 - 合并交接说明

> 更新时间：2026-04-05
> 适用范围：当前工作区中尚未合并的前后端改动

## 1. 当前结论

当前仓库已经从“基础可运行”推进到“核心业务闭环可运行”状态。

- `B 线任务` 已补齐到可运行版本
- `A 线任务` 也有一部分已被顺带补上，但仍有剩余
- 后端测试通过，前端生产构建通过
- `docs/07-development-tasks.md` 仍然不是当前代码状态的完整真相，合并时应以代码和本文档为准

## 2. 本次可直接合并的成果

### 2.1 认证与用户侧

- Email 注册/登录、邮箱验证、忘记密码/重置密码
- GitHub / Google OAuth 授权跳转与兑换码登录桥接
- 公开用户页、信用分历史页、邀请中心
- 头像上传后端接口
- 站内通知列表、未读数、全部已读、通知中心页面
- OpenAPI 导出脚本与前端生成目录已落地

### 2.2 Skill Marketplace

- Phase 1 基础能力：CRUD、调用、自动审核、提审、我的 Skill、搜索
- Phase 2 付费能力：余额扣费、创作者分成、收入看板、评价系统、版本锁定、重大更新通知、热门榜
- Phase 4 推荐能力：个性化 Skill 推荐、推荐缓存刷新任务

### 2.3 Workshop

- Phase 1 基础能力：文章 CRUD、编辑器、渲染、投票、评论、搜索
- 评论投票、折叠规则、作者置顶
- Phase 4 推荐能力：个性化文章推荐、相关文章推荐
- Phase 4 系列能力：Series CRUD、目录页、文章排序、完成奖励
- Phase 4 生命周期能力：过时标记、自动归档、数据清理任务

### 2.4 Bounty / Arbitration / Payments

- Bounty 完整主流程：发布、托管、申请、接单、评论、交付、修改、验收、取消
- 争议仲裁：冷静期、组建仲裁团、投票、结算、上诉、管理员终审
- 双方互评
- 钱包基础后端：余额、充值入账、流水、Skill 收入看板
- 文章打赏后端、打赏排行榜后端

### 2.5 首页与前端入口

- 首页已从占位页替换为个性化首页
- 新增系列详情页
- 路由已接入推荐、系列、通知、用户公开页等入口

## 3. B 线完成范围

按照 [07-development-tasks.md](/Users/Administrator/Desktop/CaMeL-Community-Web/docs/07-development-tasks.md) 的负责人划分，当前代码已覆盖：

- `P1-SKILL-001 ~ P1-SKILL-010`
- `P1-WORK-001 ~ P1-WORK-009`
- `P2-SKILL-001 ~ P2-SKILL-006`
- `P2-BOUNTY-001 ~ P2-BOUNTY-012`
- `P3-ARB-001 ~ P3-ARB-007`
- `P4-REC-001 ~ P4-REC-004`
- `P4-SER-001 ~ P4-SER-003`
- `P4-LIFE-001 ~ P4-LIFE-003`

说明：

- 文档中部分任务原本假定依赖 Stripe、Redis Sorted Set、Celery Beat 生产部署。当前代码已提供本地可运行实现和任务入口。
- 对于需要外部基础设施的部分，当前实现优先保证“功能完整可跑”，不是“生产级第三方集成完全体”。

## 4. 核心新增文件与高冲突区域

### 4.1 新增文件

- `backend/apps/search/tasks.py`
- `backend/apps/workshop/tasks.py`
- `backend/tests/test_phase4_b_features.py`
- `frontend/src/pages/workshop/SeriesDetailPage.tsx`
- 以及多组此前未纳管的测试、页面、组件、脚本文件

### 4.2 新增迁移

- `backend/apps/accounts/migrations/0002_invitation_risk_fields.py`
- `backend/apps/skills/migrations/0002_skillusagepreference.py`
- `backend/apps/workshop/migrations/0002_commentvote.py`
- `backend/apps/bounties/migrations/0002_bountyreview.py`

### 4.3 高冲突文件

后续合并时，下面这些文件最容易和其他分支发生冲突：

- `backend/apps/accounts/api.py`
- `backend/apps/accounts/services.py`
- `backend/apps/accounts/user_api.py`
- `backend/apps/skills/api.py`
- `backend/apps/skills/services.py`
- `backend/apps/workshop/api.py`
- `backend/apps/workshop/services.py`
- `backend/apps/bounties/api.py`
- `backend/apps/bounties/services.py`
- `backend/apps/payments/services.py`
- `backend/apps/search/services.py`
- `backend/config/settings/base.py`
- `frontend/src/hooks/use-auth.tsx`
- `frontend/src/app/router.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/workshop/ArticleDetailPage.tsx`
- `frontend/src/pages/marketplace/MarketplacePage.tsx`
- `docs/07-development-tasks.md`

## 5. 建议的合并顺序

建议按下面顺序合并，冲突成本最低：

1. `backend` 的 `models / migrations / services / api / tasks`
2. `frontend` 的 `lib / hooks / router`
3. `frontend` 的页面和组件
4. `tests`
5. `docs`

如果只能分批合并，建议至少把下面三块绑定在同一次合并里：

- `skills + payments`
- `workshop + search + homepage`
- `bounties + arbitration + admin`

## 6. 已完成验证

### 6.1 后端

在 `backend/` 目录执行：

```bash
SECRET_KEY=test ../.venv/bin/python -m pytest -q
```

结果：

- `64 passed`

### 6.2 前端

在仓库根目录执行：

```bash
corepack pnpm -C frontend build
```

结果：

- 构建通过
- 仍有 `chunk size > 500 kB` 的构建告警，但不阻塞合并

## 7. 仍未彻底完成的部分

截至 2026-04-05，项目整体仍有一批 `A 线 / 非 B 线` 项目未完全完成。当前可按“后续工作”处理，而不是本次合并阻塞项。

主要包括：

- 真实 Stripe Checkout / Webhook 充值链路
- 钱包页面与导航栏余额组件
- 打赏前端 UI 与打赏记录展示
- 通知 SSE 实时推送仍是占位实现
- 头像上传前端交互仍未补完
- 邀请延迟奖励和 7 天活跃校验未完全落地
- 完整管理后台、排行榜页面、财务后台
- 移动端 PWA、SEO 预渲染

如果按此前对 `docs/07` 的实际核对口径，当前剩余任务主要集中在这些方向，总量约 `30` 个任务点。

## 8. 合并后的建议检查项

合并完成后建议立即执行：

```bash
cd backend
SECRET_KEY=test ../.venv/bin/python -m pytest -q

cd ..
corepack pnpm -C frontend build
```

再额外做一次人工检查：

- 访问首页，确认推荐模块能正常回退到热门内容
- 访问 `/workshop/series/:id`，确认系列详情正常
- 登录后访问 `/marketplace`、`/workshop`、`/bounty`、`/admin`
- 检查迁移文件是否被目标分支的新迁移抢号
- 检查 `docs/07-development-tasks.md` 是否需要在合并后统一回写状态

## 9. 结论

当前版本已经满足“合并后继续开发”的基本要求：

- 核心交易闭环可跑
- B 线能力完整
- Phase 4 中属于 B 的推荐、系列、生命周期能力已落地
- 测试和构建都通过

后续如需做正式发版前整理，优先处理：

1. `docs/07` 状态回写
2. Stripe 真集成
3. 管理后台与排行榜补齐
4. 前端性能拆包
