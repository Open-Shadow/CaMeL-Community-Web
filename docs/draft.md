# Skill 模块变更计划：融合 ClawHub 模式

> **目标**：将 CaMeL Skill 从"平台托管的 Prompt 模板"转型为"用户上传的代码包"，同时保留 CaMeL 自有的经济系统和信用体系。
>
> **参考**：[ClawHub](https://clawhub.ai)（OpenClaw 的技能注册中心）的发布流程、包结构和安全扫描机制。

---

## 一、变更摘要

| 维度 | 当前状态 | 变更后 |
|------|---------|--------|
| **Skill 载体** | 表单填写 Prompt（`system_prompt` + `user_prompt_template`） | 用户上传文件包（ZIP），包含 `SKILL.md` + 可选脚本/资源 |
| **定价模型** | FREE / PER_USE（按次付费） | FREE / PAID（一次性购买，购买后可无限调用和下载） |
| **支付方式** | 仅 $ 额度 | $ 额度 **或** 信用点，由作者选择接受哪种 |
| **审核流程** | 自动安全扫描 + 人工审核 | 仅自动安全扫描（去掉人工审核环节） |
| **获取方式** | 在线调用（平台代执行） | 购买/获取后 → 可调用 + 可下载源文件包 |

---

## 二、数据模型变更

### 2.1 `Skill` 模型修改

```
需要修改的字段：
─────────────────────────────────────────────────────────
删除字段（不再需要）：
  - system_prompt          → 移入上传文件包
  - user_prompt_template   → 移入上传文件包
  - output_format          → 移入 SKILL.md frontmatter
  - example_input          → 移入 SKILL.md
  - example_output         → 移入 SKILL.md

保留字段（不变）：
  - creator, name, slug, description
  - category, tags, is_featured
  - current_version, total_calls, avg_rating, review_count
  - created_at, updated_at

修改字段：
  - pricing_model:  FREE | PER_USE  →  FREE | PAID
  - price_per_use   → 重命名为 price（一次性价格，非按次）
  - status:         去掉 PENDING_REVIEW，保留 DRAFT | APPROVED | REJECTED | ARCHIVED
  - rejection_reason → 保留，用于自动扫描拒绝时的反馈

新增字段：
  - package_file:       FileField        # 上传的 ZIP 包存储路径（S3/R2）
  - package_sha256:     CharField(64)    # ZIP 包的 SHA-256 哈希，用于完整性校验
  - package_size:       IntegerField     # 文件大小（bytes），用于限制和展示
  - readme_html:        TextField        # 从 SKILL.md 渲染的 HTML，缓存用于详情页展示
  - payment_accept:     CharField        # 接受的支付方式：MONEY | CREDIT | BOTH
  - download_count:     IntegerField     # 下载次数统计
```

### 2.2 新增 `SkillPurchase` 模型

```python
class SkillPurchase(TimestampMixin):
    """记录用户对 Skill 的购买/获取关系"""
    skill       = ForeignKey(Skill)
    user        = ForeignKey(User)
    paid_amount = DecimalField(null=True)       # 实付金额（$ 额度），免费则为 0
    paid_credit = IntegerField(default=0)       # 实付信用点
    payment_type = CharField()                  # MONEY | CREDIT | FREE

    class Meta:
        unique_together = ("skill", "user")     # 一个用户对一个 Skill 只有一条记录
```

**作用**：判断用户是否已购买（有记录 = 可调用 + 可下载），替代当前按次扣费的逻辑。

### 2.3 `SkillVersion` 模型修改

```
修改字段：
  - system_prompt          → 删除（不再存储原始 Prompt）
  - user_prompt_template   → 删除

新增字段：
  - package_file:       FileField        # 该版本对应的 ZIP 包
  - package_sha256:     CharField(64)    # 该版本的哈希
  - changelog:          TextField        # 变更说明（从 SKILL.md 或提交参数获取）
```

### 2.4 `SkillCall` 模型修改

```
保留：skill, caller, skill_version, input_text, output_text, duration_ms, created_at
修改：amount_charged → 删除（不再按次计费）
```

### 2.5 `SkillUsagePreference` 模型

保持不变，仍然支持用户锁定版本或自动跟进最新版。

---

## 三、文件包规范

### 3.1 包结构（借鉴 ClawHub SKILL.md 规范）

```
my-skill/
├── SKILL.md              # 必需 - 核心描述文件
├── README.md             # 可选 - 扩展文档
├── scripts/              # 可选 - 脚本文件
│   └── main.py
├── prompts/              # 可选 - Prompt 模板文件
│   ├── system.txt
│   └── user_template.txt
└── assets/               # 可选 - 静态资源（图片等）
    └── icon.png
```

### 3.2 SKILL.md Frontmatter 格式

```yaml
---
name: my-awesome-skill
description: 一句话描述这个 Skill 做什么
version: "1.0.0"                    # SemVer，每次更新必须 bump
output_format: text                 # text | json | markdown | code
category: code_dev                  # 对应平台分类枚举
tags:
  - python
  - code-review
requires:                           # 可选：运行时依赖声明
  bins:
    - python3
  env:
    - OPENAI_API_KEY
example_input: "请帮我 review 这段代码..."
example_output: "这段代码有以下问题..."
---

# My Awesome Skill

这里是 Skill 的详细使用说明...

## 使用方法

## 注意事项
```

### 3.3 上传限制

| 约束 | 值 | 理由 |
|------|-----|------|
| ZIP 最大体积 | 10 MB | 防止滥用存储 |
| 单文件最大 | 2 MB | 排除大型二进制 |
| 文件数量上限 | 50 | 合理范围 |
| 禁止文件类型 | `.exe`, `.dll`, `.so`, `.bin`, `.pyc` | 安全考量 |
| 必须包含 | `SKILL.md` | 核心描述文件 |

---

## 四、定价与支付变更

### 4.1 定价模型

```
FREE:
  - 任何人可直接获取（自动创建 SkillPurchase 记录，paid_amount=0）
  - 作者通过 download_count 和信用分获取回报

PAID:
  - 作者自定义价格：$0.01 ~ $50.00（放宽上限，因为是一次性购买）
  - 作者选择接受的支付方式：
    - MONEY:  仅接受 $ 额度
    - CREDIT: 仅接受信用点
    - BOTH:   两者均可（用户购买时选择）
  - 购买后永久可用（无限调用 + 可下载所有版本）
```

### 4.2 信用点支付的汇率

```
1 信用点 = $0.01（固定汇率，简化实现）

示例：
  - 作者定价 $5.00，接受 BOTH
  - 用户可选择支付 $5.00 额度 或 500 信用点
```

### 4.3 收入分成

```
沿用现有比例：
  - 平台抽成：15%（早鸟期 7.5%）
  - 作者所得：85%（早鸟期 92.5%）

分成只在 $ 额度支付时产生。
信用点支付时：全部信用点转给作者，平台不抽成（信用点不可提现，无实际损失）。
```

### 4.4 支付流程

```
用户点击"购买" →
  ├─ 免费 Skill → 直接创建 SkillPurchase，payment_type=FREE
  └─ 付费 Skill →
       ├─ 选择支付方式（受 payment_accept 约束）
       ├─ MONEY → 检查余额 → 扣费 → 分成 → 创建 SkillPurchase + Transaction
       └─ CREDIT → 检查信用点 → 扣除 → 转给作者 → 创建 SkillPurchase + CreditLog
```

---

## 五、审核流程变更

### 5.1 去掉人工审核

```
当前流程：  DRAFT → 自动扫描 → PENDING_REVIEW → 人工审核 → APPROVED/REJECTED
变更后：    DRAFT → 自动扫描 → APPROVED/REJECTED（一步到位）

status 枚举删除 PENDING_REVIEW。
```

### 5.2 自动安全扫描（增强版，借鉴 ClawHub）

在 `ModerationService.auto_review()` 中增加针对文件包的检查：

```
第一层：包结构校验
  ✓ 必须包含 SKILL.md
  ✓ SKILL.md frontmatter 格式合法（YAML 解析 + 必填字段检查）
  ✓ 文件大小/数量在限制内
  ✓ 不包含禁止文件类型
  ✓ ZIP 解压后无路径穿越（../../ 等）

第二层：内容安全扫描（保留现有 + 扩展）
  ✓ Prompt 注入检测（扫描所有 .txt / .md 文件）
  ✓ 越狱关键词检测（现有 regex 规则）
  ✓ 敏感内容检测
  ✓ 脚本安全检查：
    - 检测 shell 注入模式（curl|bash, wget|sh 等）
    - 检测凭据访问（.ssh, .aws, .env 读取）
    - 检测数据外传（可疑外部 POST 请求）
    - 检测持久化行为（crontab, systemd 写入）
    - 检测命令注入向量（base64 解码执行、eval、exec 等）
    - 检测 obfuscation（过度编码、pickle 反序列化等）

第三层：元数据一致性
  ✓ name / description 与 SKILL.md frontmatter 一致
  ✓ version 符合 SemVer 格式
  ✓ 版本号必须大于当前已发布版本（防止回退）

扫描结果：
  - PASS  → status 设为 APPROVED，上架
  - FAIL  → status 设为 REJECTED，rejection_reason 写入具体原因
  - WARN  → status 设为 APPROVED，但在详情页显示安全警告标签
```

### 5.3 社区举报机制（补偿人工审核的缺失）

```
- 用户可举报已上架 Skill（理由：恶意代码 / 虚假描述 / 侵权等）
- 累计 ≥3 个不同用户举报 → 自动下架（status → ARCHIVED），通知作者
- 下架后作者可修改并重新提交
```

---

## 六、API 端点变更

### 6.1 修改的端点

```
POST   /api/skills/                    # 创建 Skill（改为接收 multipart/form-data，含 ZIP 文件）
PATCH  /api/skills/{id}                # 更新 Skill（支持上传新版本 ZIP）
POST   /api/skills/{id}/submit         # 提交审核（触发自动扫描，不再进入人工队列）
POST   /api/skills/{id}/call           # 调用 Skill（增加购买检查：未购买 → 403）
```

### 6.2 新增的端点

```
POST   /api/skills/{id}/purchase       # 购买 Skill（FREE 或 PAID）
GET    /api/skills/{id}/download       # 下载 Skill 文件包（需已购买）
GET    /api/skills/purchased           # 我购买的 Skill 列表
POST   /api/skills/{id}/report         # 举报 Skill
```

### 6.3 删除/降级的端点

```
# 以下 moderation 端点降级（暂不需要人工操作）：
POST   /api/skills/{id}/approve        # 保留但改为内部调用（自动扫描通过后自动执行）
POST   /api/skills/{id}/reject         # 同上
```

---

## 七、前端页面变更

### 7.1 Skill 创建/编辑页（`SkillForm`）

```
当前：
  - 表单字段：name, description, system_prompt, user_prompt_template, 
              output_format, example_input, example_output, category, tags, pricing

变更后：
  - 基础信息表单：name, description, category, tags（仍通过表单填写）
  - 文件上传区域：拖拽上传 ZIP 或逐文件上传
    - 上传后自动解析 SKILL.md frontmatter，回填 name/description 等字段
    - 展示包内文件列表（树形结构预览）
  - 定价设置：
    - 定价模型：免费 / 付费
    - 价格输入：$0.01 ~ $50.00
    - 接受支付方式：$ 额度 / 信用点 / 两者均可
  - 发布前预览：渲染 SKILL.md 的 Markdown 内容
```

### 7.2 Skill 详情页

```
当前：
  - 左栏：元数据 + 描述 + 示例 I/O
  - 右栏：在线试用面板（输入 → 调用 → 看输出）

变更后：
  - 左栏：
    - 元数据（名称、评分、分类、标签、作者、版本、更新日期）
    - SKILL.md 渲染内容（类似 GitHub README 展示）
    - 包内文件列表（可展开查看目录结构）
  - 右栏：
    - 购买/获取按钮（未购买时显示价格和支付选项）
    - 已购买状态标识 + 下载按钮
    - 在线试用面板（仅已购买用户可用）
  - Tab 区域：
    - 评价（保持不变）
    - 版本历史（带 changelog 展示）
    - 相关教程（保持不变）
```

### 7.3 个人中心新增

```
- "我购买的 Skill" 列表页（带搜索和分类筛选）
- "我的 Skill" 页面增加下载量和收入统计
```

---

## 八、后端实现要点

### 8.1 文件上传处理

```python
# 上传流程：
1. 接收 ZIP 文件（multipart/form-data）
2. 计算 SHA-256 哈希
3. 安全解压到临时目录（防路径穿越）
4. 校验包结构（必须有 SKILL.md，文件大小/数量限制）
5. 解析 SKILL.md frontmatter（PyYAML / python-frontmatter）
6. 运行自动安全扫描
7. 扫描通过 → 上传 ZIP 到 S3/R2 → 创建/更新 Skill 和 SkillVersion 记录
8. 扫描失败 → 返回错误原因，不保存文件
9. 清理临时目录
```

### 8.2 下载处理

```python
# 下载流程：
1. 检查用户是否有该 Skill 的 SkillPurchase 记录
2. 有 → 生成 S3/R2 预签名 URL（有效期 10 分钟）→ 302 重定向
3. 无 → 403 Forbidden
4. download_count += 1
```

### 8.3 购买事务

```python
# 购买流程（必须在 transaction.atomic() + select_for_update() 中执行）：
1. 检查是否已购买（SkillPurchase.exists()）
2. 检查支付方式是否被作者接受
3. 扣除余额或信用点
4. 创建 SkillPurchase 记录
5. 创建 Transaction / CreditLog 记录
6. 计算并执行分成（仅 $ 额度支付时）
```

---

## 九、迁移策略

### 9.1 数据库迁移

```
1. 添加新字段（package_file, package_sha256, readme_html 等），允许 null
2. 创建 SkillPurchase 表
3. 修改 pricing_model 枚举（FREE | PAID）
4. 修改 status 枚举（移除 PENDING_REVIEW）
5. 将现有 SkillCall 中有记录的用户 → 自动创建对应 SkillPurchase（迁移兼容）
6. 旧字段（system_prompt 等）暂时保留但标记 deprecated，下个版本删除
```

### 9.2 已有 Skill 处理

```
现有 Skill 数据量小（开发阶段），可以选择：
  方案 A：直接清库重建（推荐，如果没有真实用户数据）
  方案 B：保留旧 Skill，将 system_prompt 自动打包为 SKILL.md + ZIP
```

---

## 十、不做的事情（明确排除）

| 排除项 | 理由 |
|-------|------|
| CLI 发布工具 | CaMeL 是 Web 平台，不需要 CLI 工具，Web 上传足够 |
| GitHub 账号绑定 | 当前认证体系基于邮箱+JWT，不增加外部依赖 |
| VirusTotal 集成 | 过重，现阶段自建安全扫描规则足够 |
| 每日重新扫描 | 文件包上传后不可变，无需重复扫描 |
| 包管理 / 依赖解析 | CaMeL Skill 是独立单元，不做依赖树 |

---

## 十一、实施顺序

```
Phase 1 — 数据层（~2天）
  ├─ 修改 Skill / SkillVersion 模型
  ├─ 新增 SkillPurchase 模型
  ├─ 生成并应用迁移
  └─ 编写模型单元测试

Phase 2 — 文件处理（~2天）
  ├─ ZIP 上传/解压/校验逻辑
  ├─ SKILL.md frontmatter 解析
  ├─ S3/R2 存储集成
  └─ 下载预签名 URL 生成

Phase 3 — 安全扫描（~1天）
  ├─ 扩展 ModerationService.auto_review()
  ├─ 新增文件包安全扫描规则
  └─ 社区举报逻辑

Phase 4 — 购买与支付（~2天）
  ├─ 购买 API + 事务逻辑
  ├─ 信用点支付集成
  ├─ 分成计算
  └─ SkillPurchase 权限检查

Phase 5 — API 端点（~1天）
  ├─ 修改现有端点（create, update, submit, call）
  ├─ 新增端点（purchase, download, purchased, report）
  └─ Schema 更新

Phase 6 — 前端（~3天）
  ├─ 重构 SkillForm（文件上传 + frontmatter 回填）
  ├─ 重构详情页（README 渲染 + 购买/下载 UI）
  ├─ 新增"我购买的 Skill"页面
  └─ 定价设置 UI
```

---

## 十二、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 恶意文件上传 | 严格白名单 + 解压沙箱 + 安全扫描 |
| 去掉人工审核后质量下降 | 社区举报 + 3 举报自动下架 + 未来可重新启用人工审核 |
| 信用点定价被滥用（刷信用点） | 信用点不可提现 + 转移记录可审计 |
| 大文件占用存储 | 10MB 上限 + S3 生命周期策略清理被删除 Skill 的文件 |
| 已购买 Skill 被下架 | 已购买用户仍可下载已获取的版本（不删文件，只隐藏列表） |
