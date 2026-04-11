# 管理员账号系统

## 背景

CaMeL Community 目前已有 `UserRole.ADMIN` 角色和 `admin_required` 权限装饰器，但缺少一个可靠的方式来**初始化第一个管理员账号**。现有的 `createsuperuser` 命令只设置 Django 的 `is_superuser`/`is_staff`，不会设置业务层的 `role=ADMIN`，导致通过 Django 命令创建的超级用户无法通过 `admin_required` 权限检查。

## 目标

提供一个安全、可重复的管理员账号创建/提权机制，使得：

1. 首次部署时能通过命令行创建拥有最高权限的管理员
2. 管理员同时拥有 Django 层（`is_superuser=True`, `is_staff=True`）和业务层（`role=ADMIN`）的最高权限
3. 现有管理员可通过 Admin API 提权其他用户（已实现）
4. 部署环境中可通过环境变量自动初始化管理员（适用于 Docker/CI）

## 需要实现的内容

### 1. 自定义 `create_admin` 管理命令

创建 `backend/apps/accounts/management/commands/create_admin.py`：

```
用法: python manage.py create_admin --email admin@example.com --password <password>

行为:
- 如果邮箱对应的用户不存在 → 创建新用户
- 如果邮箱对应的用户已存在 → 提权为管理员
- 设置 role=ADMIN, is_superuser=True, is_staff=True, is_active=True
- 输出操作结果（创建/提权）到终端
- 密码参数可选，不提供时交互式输入（适配 CI 和手动两种场景）
```

### 2. 覆写 `createsuperuser` 行为

在 User 模型或 UserManager 中确保 `createsuperuser()` 自动设置 `role=ADMIN`，使 Django 原生 `createsuperuser` 命令也能正确设置业务角色。

```python
# 在 User model 或 custom manager 中
class UserManager(BaseUserManager):
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)
```

### 3. Docker/部署环境自动初始化

在 `docker-entrypoint.sh` 或启动脚本中支持通过环境变量自动创建管理员：

```bash
# 环境变量
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<secure-password>

# 启动时自动执行（幂等，重复运行不会报错）
python manage.py create_admin --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD"
```

### 4. Justfile 快捷命令

在 `backend/Justfile` 中添加管理员相关命令：

```just
# 创建/提权管理员账号
admin email password="":
    python manage.py create_admin --email {{email}} {{if password != "" { "--password " + password } else { "" } }}
```

### 5. 权限矩阵确认

确认当前 `role=ADMIN` 的用户拥有以下全部权限（已实现，此处仅做确认清单）：

| 权限 | 端点 | 状态 |
|------|------|------|
| 平台仪表盘 | `GET /api/admin/dashboard` | ✅ moderator+ |
| 用户列表/详情 | `GET /api/admin/users` | ✅ moderator+ |
| 修改用户角色 | `PATCH /api/admin/users/{id}/role` | ✅ admin only |
| 封禁/解封用户 | `POST /api/admin/users/{id}/ban\|unban` | ✅ admin only |
| 调整信用分 | `POST /api/admin/users/{id}/credit-adjust` | ✅ admin only |
| Skill 审核 | `POST /api/admin/skills/{id}/review` | ✅ moderator+ |
| 设置精选 | `POST /api/admin/skills/{id}/featured` | ✅ moderator+ |
| 财务报表 | `GET /api/admin/finance/report` | ✅ admin only |
| 仲裁终审 | `POST /api/bounties/{id}/arbitration/admin-finalize` | ✅ admin only |
| Django Admin 后台 | `/admin/` | ✅ is_staff |

## 安全要求

- `create_admin` 命令只能通过服务器命令行执行，**不可通过 API 调用**
- 密码必须通过 Django 密码验证器校验
- 管理员账号不可被其他管理员封禁（已实现，见 `admin_api.py:309-310`）
- 管理员不可修改自己的角色（已实现，见 `admin_api.py:287-288`）
- 生产环境中 `ADMIN_PASSWORD` 环境变量应通过 secrets management 注入，不应出现在代码或配置文件中

## 验证方式

1. 运行 `python manage.py create_admin --email test@admin.com --password TestPass123!`
2. 用该账号登录，验证 JWT token 中 role 为 ADMIN
3. 访问 `/api/admin/dashboard`，确认返回 200
4. 访问 `/api/admin/finance/report`，确认返回 200
5. 用普通用户访问以上端点，确认返回 403
