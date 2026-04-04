# 05 - 模块详细设计

## 5.1 Skill Marketplace（技能市场）详细设计

### 5.1.1 Skill 标准化数据结构

每个 Skill 包含以下结构化字段：

| 字段 | 必填 | 说明 | 约束 |
|------|------|------|------|
| name | ✅ | Skill 名称 | 2~80 字符 |
| description | ✅ | 功能说明 | 10~500 字符 |
| systemPrompt | ✅ | 系统提示词（核心资产） | ≥10 字符 |
| userPromptTemplate | ❌ | 用户输入模板 | 自由文本 |
| outputFormat | ❌ | 输出格式说明 | text/json/markdown/code |
| exampleInput | ❌ | 示例输入 | 自由文本 |
| exampleOutput | ❌ | 示例输出 | 自由文本 |
| category | ✅ | 一级分类 | 枚举（9个分类） |
| tags | ✅ | 自由标签 | 最多10个 |
| pricingModel | ✅ | 免费 / 按次付费 | 枚举 |
| pricePerUse | 条件 | 单次调用价格（付费时必填） | $0.01 ~ $10.00 |

### 5.1.2 分类体系

```
一级分类（固定）：
├── 💻 代码开发 (CODE_DEV)
├── ✍️ 文案写作 (WRITING)
├── 📊 数据分析 (DATA_ANALYTICS)
├── 🎓 学术研究 (ACADEMIC)
├── 🌐 翻译本地化 (TRANSLATION)
├── 🎨 创意设计 (CREATIVE)
├── 🤖 Agent 工具 (AGENT)
├── 📋 办公效率 (PRODUCTIVITY)
└── 🧩 其他 (MISC)

二级分类：无固定二级，通过 tags 自由细分
```

### 5.1.3 审核流程

```
创作者提交 Skill
      │
      ▼
 自动检测层（< 1分钟）
 ├─ prompt 安全扫描
 │   ├─ Jailbreak 模式检测（关键词 + 正则）
 │   ├─ Prompt Injection 检测
 │   └─ 敏感内容检测
 ├─ 示例输入/输出格式校验
 └─ 必填字段完整性检查
      │
      ├─ 🔴 不通过 → 返回具体原因，状态 REJECTED
      │
      ▼
 人工审核层（< 24小时）
 ├─ 功能真实性验证（用示例输入跑一遍）
 ├─ 分类和标签是否准确
 └─ 描述是否有误导性
      │
      ├─ 🔴 不通过 → 返回原因 + 修改建议
      ├─ ✅ 通过 → 上架，进入"最新"列表
      │
      ▼
 运营推荐（可选）
 └─ ✅ → 进入"精选"列表
```

**自动检测实现**：

```typescript
// src/server/services/moderation.service.ts

interface ModerationResult {
  passed: boolean;
  issues: ModerationIssue[];
}

interface ModerationIssue {
  type: "jailbreak" | "injection" | "sensitive" | "format" | "incomplete";
  field: string;
  message: string;
  severity: "error" | "warning";
}

class ModerationService {
  // 检测 Jailbreak 模式
  checkJailbreak(prompt: string): ModerationIssue[];

  // 检测 Prompt Injection
  checkInjection(prompt: string): ModerationIssue[];

  // 检测敏感内容
  checkSensitiveContent(text: string): ModerationIssue[];

  // 校验字段完整性
  checkCompleteness(skill: SkillInput): ModerationIssue[];

  // 综合审核
  autoReview(skill: SkillInput): Promise<ModerationResult>;
}
```

### 5.1.4 排序与发现机制

**首页展示区域**：

| 区域 | 数据来源 | 更新频率 |
|------|---------|---------|
| 精选推荐 (Editor's Pick) | 运营手动选取 | 每周 |
| 热门榜 (Trending) | 近7天调用量 × 平均评分 | 每小时（Redis 缓存） |
| 新品区 (New Arrivals) | 上架时间倒序，7天窗口期 | 实时 |
| 分类浏览 | 按分类筛选 + tag 搜索 | 实时 |

**搜索排序权重**：

```
综合得分 = 0.35 × 文本相关度
         + 0.25 × 调用量(归一化)
         + 0.20 × 平均评分(归一化)
         + 0.10 × 时间新鲜度
         + 0.10 × 创作者信用等级
```

**热门榜计算**（Redis Sorted Set）：

```typescript
// 热门分数 = 近7天调用量 × (平均评分 / 5)
// 每小时由后台任务刷新
async function updateTrendingScores() {
  const skills = await getSkillsCalledInLast7Days();
  for (const skill of skills) {
    const score = skill.recentCalls * (skill.avgRating / 5);
    await redis.zadd("skill:trending", score, skill.id);
  }
  await redis.expire("skill:trending", 3600);
}
```

### 5.1.5 定价与分成

| 模式 | 定价范围 | 平台抽成 | 创作者到手 |
|------|---------|---------|-----------|
| 免费 | $0 | 0 | 通过信用分间接回报 |
| 按次付费 | $0.01 ~ $10.00 | 15%（早期3月7.5%） | 85%（早期 92.5%） |

**结算流程**：

```
用户调用付费 Skill
      │
      ▼
 检查用户余额 ≥ pricePerUse
      │
      ├─ 🔴 不足 → 提示充值
      │
      ▼
 数据库事务：
 ├─ 用户余额 -= pricePerUse
 ├─ 创作者余额 += pricePerUse × (1 - 平台抽成率)
 ├─ 平台收入 += pricePerUse × 平台抽成率
 ├─ 记录 Transaction (用户: SKILL_PURCHASE)
 ├─ 记录 Transaction (创作者: SKILL_INCOME)
 ├─ 记录 SkillCall
 └─ 更新 Skill.totalCalls
      │
      ▼
 执行 Skill（调用 AI API）
      │
      ▼
 返回结果
```

### 5.1.6 版本管理

```
版本规则：
├── 每次更新 systemPrompt 或 userPromptTemplate 自动版本号 +1
├── 保留最近 10 个版本
├── 用户可选"锁定版本"或"自动跟随最新"
├── 重大更新判定：systemPrompt 变动 > 50%（按编辑距离计算）
└── 重大更新 → 通知所有使用过该 Skill 的用户
```

### 5.1.7 评价体系

```
评价条件：
├── 必须实际调用过该 Skill
├── 每人每 Skill 仅一次评价（可修改）
└── 首次调用后 24 小时内可评价

评分计算：
├── 原始评分 → 去掉最高 5% 和最低 5%
└── 加权平均 → 最终显示评分

标签评价选项：
├── 效果好 ✅
├── 响应快 ⚡
├── 说明清晰 📖
├── 需要改进 ⚠️
└── 有bug 🐛
```

---

## 5.2 Bounty Board（悬赏任务板）详细设计

### 5.2.1 任务类型

| 类型 | 说明 | 典型场景 |
|------|------|---------|
| Skill 定制 | 根据需求定制 Prompt/Skill | "帮我写一个翻译 PDF 的 Skill" |
| 数据处理 | 数据清洗/分析/可视化 | "帮我处理这份销售数据" |
| 内容创作 | 文案/文档/设计 | "帮我写产品使用教程" |
| 问题修复 | Debug/优化/排错 | "帮我优化这个 Prompt 的输出" |
| 通用任务 | 以上不包含的其他任务 | 自定义需求 |

### 5.2.2 任务生命周期详细设计

```
状态流转图：

  OPEN ──────────► CANCELLED（发布者取消，解冻 $）
    │
    ▼ (接受申请)
  IN_PROGRESS
    │
    ▼ (提交交付物)
  DELIVERED
    │
    ▼ (发布者审核)
  IN_REVIEW ──────► REVISION（需修改，最多3轮）
    │                   │
    │                   ▼ (重新提交)
    │               DELIVERED（循环）
    │
    ├─► COMPLETED（验收通过，结算 $）
    │
    └─► DISPUTED（拒绝验收）
         │
         ▼
     ARBITRATING（社区仲裁）
         │
         ├─► COMPLETED（接单者胜，划转 $）
         └─► CANCELLED（发布者胜，退回 $）

  超时规则：
  ├── OPEN 状态 72 小时无人接单 → 标记"冷门"
  ├── IN_PROGRESS 超过 deadline → 任务释放，接单者 -15 信用分
  └── DELIVERED 后 7 天未审核 → 自动验收通过
```

### 5.2.3 托管与结算机制

```
资金流向：

发布者 $ 余额         平台托管池          接单者 $ 余额
    │                   │                   │
    ├── 发布任务 ──────►│                   │
    │   (冻结悬赏 $)     │                   │
    │                   │                   │
    │   验收通过 ───────►├── 划转 $ ────────►│
    │                   │   (扣手续费)       │
    │                   │                   │
    │   争议仲裁 ───────►├── 退回/划转 ─────►│
    │                   │   (视仲裁结果)      │

手续费规则：
├── 悬赏 ≤ $10   → 8%（早期4%）
├── 悬赏 $10~$50 → 6%（早期3%）
└── 悬赏 > $50   → 5%（早期2.5%）

接单者实际到手 = 悬赏 $ × (1 - 手续费率)
```

**结算事务伪代码**：

```typescript
async function settleBounty(bountyId: string) {
  return await prisma.$transaction(async (tx) => {
    const bounty = await tx.bounty.findUniqueOrThrow({ where: { id: bountyId } });
    const feeRate = calculateFeeRate(bounty.reward);
    const fee = bounty.reward * feeRate;
    const hunterAmount = bounty.reward - fee;

    // 1. 从发布者冻结余额扣除
    await tx.user.update({
      where: { id: bounty.creatorId },
      data: { frozenBalance: { decrement: bounty.reward } },
    });

    // 2. 划转给接单者
    const hunter = await tx.bountyApplication.findFirst({
      where: { bountyId, isAccepted: true },
    });
    await tx.user.update({
      where: { id: hunter.applicantId },
      data: { balance: { increment: hunterAmount } },
    });

    // 3. 记录交易
    await tx.transaction.createMany({
      data: [
        { userId: hunter.applicantId, type: "BOUNTY_INCOME", amount: hunterAmount, ... },
        { userId: bounty.creatorId, type: "BOUNTY_RELEASE", amount: -bounty.reward, ... },
        { userId: "PLATFORM", type: "PLATFORM_FEE", amount: fee, ... },
      ],
    });

    // 4. 更新悬赏状态
    await tx.bounty.update({
      where: { id: bountyId },
      data: { status: "COMPLETED" },
    });

    // 5. 更新信用分
    await creditService.addCredit(tx, hunter.applicantId, "BOUNTY_COMPLETED", 20);
  }, { isolationLevel: "Serializable" });
}
```

### 5.2.4 争议仲裁机制

```
争议流程：

 发布者拒绝验收
      │
      ▼
 冷静期（24小时）
 ├── 双方在评论区继续协商
 └── 可随时达成和解 → 直接结算
      │
      ▼ (协商失败)
 提交仲裁陈述
 ├── 发布者提交陈述（≤ 500字）
 └── 接单者提交陈述（≤ 500字）
      │
      ▼
 组建仲裁团
 ├── 随机抽取 3 名 ⚡专家 级以上用户
 ├── 排除与双方有关联的用户
 └── 仲裁团成员 48 小时内投票
      │
      ▼
 仲裁结果（多数票决）
 ├── 接单者胜 → 全额划转悬赏 $
 ├── 发布者胜 → 全额退回冻结 $
 └── 部分完成 → 仲裁团决定比例（投票取中位数）
      │
      ▼
 上诉（可选，仅1次）
 ├── 上诉费 $0.50
 ├── 平台管理员终审
 ├── 胜诉 → 退回上诉费
 └── 败诉 → 上诉费归平台

 仲裁团激励：每次仲裁 +5 信用分
```

### 5.2.5 信用分门槛

| 操作 | 信用分要求 | 备注 |
|------|-----------|------|
| 发布悬赏 | ≥ 50 | 新用户不可立即发布 |
| 申请接单 | ≥ 50 | 需完善资料 |
| 发布 > $20 悬赏 | ≥ 200 | 大额门槛 |
| 申请 > $20 悬赏 | ≥ 200 | 大额门槛 |
| 参与仲裁 | ≥ 500 (⚡专家) | 仲裁员资格 |

### 5.2.6 超时与惩罚

```
超时规则：
├── 接单后超过 deadline 未提交 → 信用分 -15
├── 累计超时 3 次 → 永久禁止接单（可申诉）
└── 信用分 < 30 → 悬赏板冻结 30 天
```

---

## 5.3 Workshop（知识工坊）详细设计

### 5.3.1 内容模板

每篇文章必须包含以下结构（编辑器内置）：

```markdown
# [标题：动词开头，说清楚解决什么问题]

## 问题（Problem）
你遇到了什么具体问题？什么场景下会碰到？（50~200字）

## 方案（Solution）
你是怎么解决的？具体步骤是什么？（200~1000字，含代码块/截图/配置）

## 效果（Result）
解决后的效果如何？有数据对比吗？（50~300字）

## 注意事项（Caveats）— 可选
有什么坑？什么情况下不适用？

## 关联 Skill — 可选
链接到对应的 Skill
```

**字数约束**：总字数 500~2000 字。

### 5.3.2 标签体系

**固定标签维度**（发布时必选）：

| 维度 | 选项 |
|------|------|
| 难度 | 🟢 入门 / 🟡 进阶 / 🔴 高级 |
| 内容类型 | 📘 教程 / 📋 案例 / ⚠️ 踩坑记录 / 📊 评测 / 💬 讨论 |
| 模型标签 | Claude Sonnet 4 / Claude Opus 4 / Claude Haiku / 通用 / ... |

**自定义标签**：≤ 5 个，如 "MCP", "prompt工程", "PDF处理"。

### 5.3.3 投票机制

```
投票规则：
├── 每个用户每篇文章只能投一票（有用 👍 / 无用 👎）
├── 可以取消或更改投票
└── 投票权重按信用等级：

    等级    │ 权重
    ────────┼──────
    🌱 新芽  │ × 1.0
    🔧 工匠  │ × 1.5
    ⚡ 专家  │ × 2.0
    🏆 大师  │ × 3.0
    👑 宗师  │ × 5.0

净票数计算：
  netVotes = Σ(有用票 × 权重) - Σ(无用票 × 权重)

自动折叠：净票数 < -5 → 自动折叠（展开可见）
```

### 5.3.4 加精机制

```
加精流程：

 净票数 ≥ 10
      │
      ▼
 自动进入"待加精"队列
      │
      ▼
 版主审核
 ├── 确认质量、排版、准确性
 │
 ├─ ✅ 加精
 │   ├── 作者 +20 信用分
 │   ├── 作者 +$0.50 奖励
 │   └── 文章进入"精选"专区
 │
 └─ ❌ 暂不加精
     └── 留在普通列表，可再次进入队列
```

### 5.3.5 打赏系统

```
打赏规则：
├── 快捷金额：$0.10 / $0.30 / $0.50 / $1.00
├── 自定义金额：$0.01 ~ $50.00
├── 分配：作者获得 100%（直接转账）
├── 打赏者：每 $1 打赏 → +2 信用分
└── 打赏记录公开可见

打赏事务：
├── 打赏者余额 -= amount
├── 作者余额 += amount
├── 记录 Transaction (打赏者: TIP_SEND)
├── 记录 Transaction (作者: TIP_RECEIVE)
├── 记录 Tip
├── 更新 Article.totalTips
└── 打赏者信用分 += floor(amount × 2)
```

### 5.3.6 搜索排序

```
综合得分 = 0.30 × 文本相关度
         + 0.25 × 净票数(归一化)
         + 0.20 × 是否加精(0 或 1)
         + 0.15 × 时间衰减
         + 0.10 × 作者信用等级(归一化)

时间衰减公式：
  decay = 1 / (1 + 0.1 × days_since_publish)

示例：
  发布当天 → decay = 1.0
  第 7 天  → decay = 0.59
  第 30 天 → decay = 0.25
```

### 5.3.7 评论区设计

```
评论规则：
├── 每条 ≤ 500字
├── 支持代码块
├── 作者可置顶 1 条评论
├── 评论可被投"有用/无用"
├── 低质量评论自动折叠
├── 支持 @用户
├── 只支持一层回复（不盖楼）
└── 评论也可被举报
```

### 5.3.8 内容生命周期

```
过时标记：
├── 关联模型版本被淘汰 → 顶部显示 "⚠️ 模型版本可能已更新"
├── 6个月无更新 + 净票数 < 5 → 归档区
├── 作者更新文章 → 重置时间衰减因子
└── 归档文章仍可搜索，但不在默认列表

系列文章：
├── 作者创建"系列"
├── 系列有独立目录页
├── 按作者设定顺序排列
├── 系列可作为整体被收藏
└── 系列完成 → 作者 +$1.00 + 30 信用分
```

### 5.3.9 Workshop 激励汇总

| 行为 | $ 奖励 | 信用分 |
|------|--------|--------|
| 发布文章 | - | +10 |
| 文章被加精 | +$0.50 | +20 |
| 完成系列（≥3篇） | +$1.00 | +30 |
| 被打赏 | 打赏金额100% | - |
| 打赏他人 | - | +2/$ |

---

## 5.4 信用分系统详细设计

### 5.4.1 等级计算

```typescript
function calculateLevel(creditScore: number): UserLevel {
  if (creditScore >= 5000) return "GRANDMASTER";
  if (creditScore >= 2000) return "MASTER";
  if (creditScore >= 500)  return "EXPERT";
  if (creditScore >= 100)  return "CRAFTSMAN";
  return "SEED";
}

function getApiMultiplier(level: UserLevel): number {
  const multipliers = {
    SEED: 1.0,
    CRAFTSMAN: 0.95,
    EXPERT: 0.90,
    MASTER: 0.85,
    GRANDMASTER: 0.80,
  };
  return multipliers[level];
}

function getVoteWeight(level: UserLevel): number {
  const weights = {
    SEED: 1.0,
    CRAFTSMAN: 1.5,
    EXPERT: 2.0,
    MASTER: 3.0,
    GRANDMASTER: 5.0,
  };
  return weights[level];
}
```

### 5.4.2 信用分服务

```typescript
class CreditService {
  // 增加信用分（事务内调用）
  async addCredit(
    tx: PrismaTransaction,
    userId: string,
    action: CreditAction,
    amount: number,
    referenceId?: string
  ): Promise<void> {
    const user = await tx.user.findUniqueOrThrow({ where: { id: userId } });
    const newScore = user.creditScore + amount;
    const newLevel = calculateLevel(newScore);

    await tx.user.update({
      where: { id: userId },
      data: {
        creditScore: newScore,
        level: newLevel,
      },
    });

    await tx.creditLog.create({
      data: {
        userId,
        action,
        amount,
        scoreBefore: user.creditScore,
        scoreAfter: newScore,
        referenceId,
      },
    });

    // 等级变更通知
    if (user.level !== newLevel) {
      await notificationService.send(tx, userId, {
        type: "CREDIT_CHANGED",
        title: `恭喜升级到 ${getLevelName(newLevel)}！`,
        content: `您的信用分达到 ${newScore}，解锁了新特权。`,
      });
    }
  }

  // 扣减信用分
  async deductCredit(
    tx: PrismaTransaction,
    userId: string,
    action: CreditAction,
    amount: number,
    referenceId?: string
  ): Promise<void> {
    // amount 为正数，内部取负
    await this.addCredit(tx, userId, action, -amount, referenceId);

    // 检查是否触发冻结
    const user = await tx.user.findUniqueOrThrow({ where: { id: userId } });
    if (user.creditScore < 30 && !user.bountyFreezeUntil) {
      await tx.user.update({
        where: { id: userId },
        data: {
          bountyFreezeUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
        },
      });
    }
  }
}
```

---

## 5.5 通知系统设计

### 5.5.1 通知触发场景

| 事件 | 接收者 | 通知标题示例 |
|------|--------|-------------|
| Skill 审核通过 | 创作者 | "您的 Skill 已审核通过" |
| Skill 审核拒绝 | 创作者 | "您的 Skill 需要修改" |
| Skill 被调用 | 创作者 | "您的 Skill 被调用了（批量通知）" |
| 收到悬赏申请 | 发布者 | "有人申请了您的悬赏任务" |
| 申请被接受 | 接单者 | "您的申请已被接受" |
| 交付物已提交 | 发布者 | "接单者提交了交付物" |
| 验收通过 | 接单者 | "悬赏已结算，$ 已到账" |
| 需要修改 | 接单者 | "发布者要求修改" |
| 进入争议 | 双方 | "悬赏进入争议仲裁" |
| 文章被投票 | 作者 | "您的文章获得了新投票" (批量) |
| 文章被加精 | 作者 | "您的文章已被加精" |
| 收到评论 | 作者 | "有人评论了您的文章" |
| 收到打赏 | 作者 | "收到打赏 $X.XX" |
| 信用分变动 | 用户 | "信用分 +N / -N" |
| Skill 重大更新 | 使用者 | "您使用的 Skill 有重大更新" |

### 5.5.2 通知推送方式

```
推送渠道：
├── 站内通知（主要）
│   ├── 右上角铃铛图标 + 未读数
│   ├── 通知列表页
│   └── SSE 实时推送
│
├── 邮件通知（可选，用户设置）
│   ├── 重要事件：验收通过、争议仲裁、$ 到账
│   └── 每日摘要：汇总次要通知
│
└── 批量合并
    ├── Skill 调用通知：每100次合并为一条
    └── 投票通知：每10票合并为一条
```
