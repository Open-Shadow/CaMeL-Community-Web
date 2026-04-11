# Admin Account System — Implementation Plan

## Goal Description

Bridge the gap between Django's native privilege system (`is_staff`/`is_superuser`) and CaMeL Community's business-layer role system (`role=ADMIN`) by implementing a reliable, secure, and idempotent admin account creation/elevation mechanism. This includes a management command, a custom UserManager, deployment auto-bootstrap, email uniqueness enforcement, privilege synchronization across all mutation paths, password validation settings, Django Admin registration, and comprehensive tests.

## Acceptance Criteria

Following TDD philosophy, each criterion includes positive and negative tests for deterministic verification.

- AC-1: `create_admin` management command creates or elevates admin accounts correctly
  - Positive Tests (expected to PASS):
    - `python manage.py create_admin --email new@example.com --password ValidPass1!` creates a new user with `role=ADMIN`, `is_staff=True`, `is_superuser=True`, `is_active=True`
    - Running `create_admin` on an existing non-admin user elevates them to `role=ADMIN`, `is_staff=True`, `is_superuser=True` without changing their password
    - `create_admin --email existing@example.com --set-password --password NewPass1!` elevates and resets password
    - Running the command twice with the same email is idempotent (no error, user remains admin)
    - Created admin user can authenticate via JWT and access `GET /api/admin/finance/report` (200)
  - Negative Tests (expected to FAIL):
    - `create_admin` with a password that fails Django validators is rejected with a clear error
    - `create_admin` without `--email` argument fails with usage error
    - In non-interactive mode (piped stdin), missing `--password` fails instead of hanging
  - AC-1.1: `--from-env` mode reads `ADMIN_EMAIL` and `ADMIN_PASSWORD` from environment
    - Positive: With both env vars set, `create_admin --from-env` creates/elevates the admin
    - Negative: With only `ADMIN_EMAIL` set (no `ADMIN_PASSWORD`), the command warns and exits without changes

- AC-2: `createsuperuser` automatically sets `role=ADMIN`
  - Positive Tests (expected to PASS):
    - `python manage.py createsuperuser` with valid inputs produces a user with `role=ADMIN`, `is_staff=True`, `is_superuser=True`
    - Programmatic `User.objects.create_superuser(username=..., email=..., password=...)` sets `role=ADMIN`
  - Negative Tests (expected to FAIL):
    - `User.objects.create_user(...)` does NOT set `role=ADMIN` (remains `USER` default)

- AC-3: Role/flag synchronization is enforced across all mutation paths
  - Positive Tests (expected to PASS):
    - Promoting a user to `ADMIN` via `PATCH /api/admin/users/{id}/role` also sets `is_staff=True`, `is_superuser=True`
    - Demoting an `ADMIN` to `USER` via the same endpoint also sets `is_staff=False`, `is_superuser=False`
    - Demoting to `MODERATOR` sets `is_staff=False`, `is_superuser=False`
  - Negative Tests (expected to FAIL):
    - After demotion from ADMIN, the user cannot access `GET /api/admin/finance/report` (403)
    - After demotion from ADMIN, the user cannot log into Django admin at `/admin/`

- AC-4: Email uniqueness is enforced at the database level (case-insensitive)
  - Positive Tests (expected to PASS):
    - Creating a user with a unique email succeeds
    - The database rejects a second user with the same email (different case, e.g., `User@Example.com` vs `user@example.com`)
    - Existing duplicate emails (if any) are detected and handled by data migration
  - Negative Tests (expected to FAIL):
    - `INSERT` of a user with a case-variant of an existing email raises `IntegrityError`

- AC-5: Production startup bootstrap works correctly via `scripts/start-web.sh`
  - Positive Tests (expected to PASS):
    - With `ADMIN_EMAIL` and `ADMIN_PASSWORD` set, startup creates admin before launching gunicorn
    - Without either env var, startup proceeds normally without admin creation
    - Repeated container starts with the same env vars are idempotent
  - Negative Tests (expected to FAIL):
    - With only `ADMIN_EMAIL` set, startup logs a warning (does not silently ignore misconfiguration)
    - Admin password never appears in stdout/stderr logs

- AC-6: `AUTH_PASSWORD_VALIDATORS` is configured with Django's 4 standard validators
  - Positive Tests (expected to PASS):
    - Registration with password "12345678" is rejected (too common)
    - Registration with password "ab" is rejected (too short)
    - `create_admin` with a weak password is rejected
  - Negative Tests (expected to FAIL):
    - A password matching the username exactly is rejected (similarity check)

- AC-7: User model is registered in Django Admin with basic management capabilities
  - Positive Tests (expected to PASS):
    - An `is_staff` user can log in to `/admin/` and see the User list
    - User list displays username, email, role, level, is_active
    - Admin can view user details in Django admin
  - Negative Tests (expected to FAIL):
    - A non-staff user cannot access `/admin/` (redirect to login)

- AC-8: Existing privilege-drifted accounts are repaired by data migration
  - Positive Tests (expected to PASS):
    - After migration, all users with `is_superuser=True` also have `role=ADMIN` and `is_staff=True`
    - Users with `role=ADMIN` but `is_superuser=False` are synced to `is_superuser=True`, `is_staff=True`
  - Negative Tests (expected to FAIL):
    - After migration, no user has `is_superuser=True` with `role != ADMIN`

- AC-9: Justfile provides an interactive admin creation shortcut
  - Positive Tests (expected to PASS):
    - `just admin user@example.com` invokes `create_admin` interactively (prompts for password)
  - Negative Tests (expected to FAIL):
    - Password is never passed as a visible CLI argument in the Justfile recipe

## Path Boundaries

Path boundaries define the acceptable range of implementation quality and choices.

### Upper Bound (Maximum Acceptable Scope)

The implementation includes all 9 acceptance criteria: the `create_admin` command with `--from-env` mode, custom UserManager, role/flag sync helper called from all mutation paths (create_admin, create_superuser, admin API role update), case-insensitive email uniqueness migration with data repair for duplicates and drifted accounts, startup bootstrap in `scripts/start-web.sh`, `AUTH_PASSWORD_VALIDATORS` in settings, Django Admin UserAdmin registration, Justfile recipe, and comprehensive pytest tests covering all positive/negative cases.

### Lower Bound (Minimum Acceptable Scope)

The implementation includes the `create_admin` command (AC-1), custom UserManager for `create_superuser` (AC-2), role/flag sync on admin API role changes (AC-3), case-insensitive email uniqueness (AC-4), and tests for these core features. The startup bootstrap, password validators, Django Admin registration, drift repair migration, and Justfile can be minimal but must satisfy their respective AC.

### Allowed Choices

- Can use: Django's `UserManager` as base class for custom manager; `UniqueConstraint` with `Lower()` for email uniqueness; `transaction.atomic()` + `select_for_update()` for concurrency safety; `getpass` for interactive password input; Django system checks framework for drift detection
- Cannot use: `BaseUserManager` as the manager base (must extend Django's `UserManager` to preserve `AbstractUser` contract); `unique=True` alone on email field (insufficient for case-insensitivity); CLI `--password` argument in `start-web.sh` (password exposure risk)

## Feasibility Hints and Suggestions

> **Note**: This section is for reference and understanding only. These are conceptual suggestions, not prescriptive requirements.

### Conceptual Approach

```
1. Create sync_admin_flags(user) helper:
   if user.role == ADMIN:
       user.is_staff = True
       user.is_superuser = True
   else:
       user.is_staff = False
       user.is_superuser = False
   user.save(update_fields=["is_staff", "is_superuser"])

2. Custom UserManager(django.contrib.auth.models.UserManager):
   def create_superuser(self, username, email=None, password=None, **extra_fields):
       extra_fields.setdefault("role", UserRole.ADMIN)
       return super().create_superuser(username, email, password, **extra_fields)

3. create_admin command:
   - Parse --email, --password, --set-password, --from-env
   - If --from-env: read ADMIN_EMAIL/ADMIN_PASSWORD from os.environ
   - Validate password via django.contrib.auth.password_validation.validate_password()
   - In atomic+select_for_update block: get_or_create user, set role+flags
   - Log action (created/elevated) to stdout, never echo password

4. Email migration:
   - AddConstraint(UniqueConstraint(Lower("email"), name="unique_email_ci"))
   - Data migration: normalize existing emails to lowercase, detect+report duplicates
   - Repair drift: set role=ADMIN for is_superuser=True users

5. start-web.sh addition (between migrate and gunicorn):
   if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
     python manage.py create_admin --from-env
   elif [ -n "$ADMIN_EMAIL" ] || [ -n "$ADMIN_PASSWORD" ]; then
     echo "WARNING: Only one of ADMIN_EMAIL/ADMIN_PASSWORD is set, skipping admin bootstrap"
   fi
```

### Relevant References

- `backend/apps/accounts/models.py` — User model, UserRole choices, no custom manager currently
- `backend/common/permissions.py` — admin_required, moderator_required decorators
- `backend/apps/accounts/admin_api.py` — update_user_role endpoint (needs sync_admin_flags call)
- `backend/apps/accounts/api.py` — registration flow, username generation pattern (`user_{uuid.hex[:12]}`)
- `backend/scripts/start-web.sh` — production startup script (migrate → collectstatic → gunicorn)
- `backend/config/settings/base.py` — settings file where AUTH_PASSWORD_VALIDATORS should be added
- `backend/Justfile` — existing dev shortcuts
- `backend/apps/accounts/management/commands/` — existing management commands directory

## Dependencies and Sequence

### Milestones

1. Foundation — Model and permission infrastructure changes
   - Custom UserManager with `create_superuser` override
   - `sync_admin_flags()` helper function
   - Email uniqueness migration + data repair migration
   - AUTH_PASSWORD_VALIDATORS in settings

2. Command — Admin creation management command
   - `create_admin` command implementation (depends on UserManager + sync helper)
   - Justfile recipe

3. Integration — Wire sync into existing mutation paths
   - Update `update_user_role` in admin_api.py to call `sync_admin_flags`
   - Startup bootstrap in `scripts/start-web.sh` (depends on create_admin command)
   - Django Admin UserAdmin registration

4. Verification — Tests and permission matrix validation
   - Tests for all acceptance criteria (depends on all above)

Milestone 1 must complete before Milestone 2. Milestones 2 and 3 are partially parallel (Justfile and Django Admin can proceed independently). Milestone 4 depends on all prior milestones.

## Task Breakdown

Each task must include exactly one routing tag:
- `coding`: implemented by Claude
- `analyze`: executed via Codex (`/humanize:ask-codex`)

| Task ID | Description | Target AC | Tag (`coding`/`analyze`) | Depends On |
|---------|-------------|-----------|--------------------------|------------|
| task1 | Add custom `UserManager` extending Django's `UserManager`, override `create_superuser()` to set `role=ADMIN` | AC-2 | coding | - |
| task2 | Implement `sync_admin_flags(user)` helper in `backend/apps/accounts/models.py` or a dedicated utils module | AC-3 | coding | - |
| task3 | Add case-insensitive email uniqueness migration with `UniqueConstraint(Lower("email"))` and lowercase normalization on save | AC-4 | coding | task1 |
| task4 | Add data migration to repair privilege-drifted accounts (`is_superuser=True` + `role!=ADMIN`) and normalize existing email case | AC-8 | coding | task3 |
| task5 | Add `AUTH_PASSWORD_VALIDATORS` with Django's 4 standard validators to `config/settings/base.py` | AC-6 | coding | - |
| task6 | Implement `create_admin` management command with `--email`, `--password`, `--set-password`, `--from-env` flags | AC-1 | coding | task1, task2, task5 |
| task7 | Update `update_user_role` in `admin_api.py` to call `sync_admin_flags` after role change | AC-3 | coding | task2 |
| task8 | Add admin bootstrap logic to `backend/scripts/start-web.sh` with env var differentiation | AC-5 | coding | task6 |
| task9 | Add Justfile `admin` recipe for interactive admin creation | AC-9 | coding | task6 |
| task10 | Register User model in Django Admin with `UserAdmin` in `backend/apps/accounts/admin.py` | AC-7 | coding | task1 |
| task11 | Verify existing admin permission matrix against the documented endpoints | AC-1, AC-3 | analyze | task7 |
| task12 | Write pytest tests for `create_admin` command (create, elevate, idempotent, weak password, --from-env, duplicate email) | AC-1 | coding | task6 |
| task13 | Write pytest tests for `create_superuser` override, role/flag sync on promotion/demotion, email uniqueness, and drift repair | AC-2, AC-3, AC-4, AC-8 | coding | task4, task7 |
| task14 | Write pytest tests for password validators and Django Admin access | AC-6, AC-7 | coding | task5, task10 |

## Claude-Codex Deliberation

### Agreements

- A dedicated `create_admin` management command is the right operational entry point
- Overriding `create_superuser()` on a custom manager is necessary to prevent future drift
- Email uniqueness must be case-insensitive (matching existing app behavior)
- `scripts/start-web.sh` is the correct production bootstrap hook (not a hypothetical `docker-entrypoint.sh`)
- Password must never be passed on the CLI in production startup scripts
- `validate_password()` must be called in the management command
- Bootstrap env handling must differentiate: both absent (no-op), one present (warn), both present (proceed)
- Comprehensive tests are required for all mutation paths
- Role/flag sync must be enforced at all mutation points, not just creation time

### Resolved Disagreements

- **Manager base class**: Draft proposed `BaseUserManager`; Codex flagged this would break `AbstractUser` contract. Resolved: extend Django's `UserManager` and preserve `username`-based `create_superuser(username, email, password, **extra_fields)` signature.
- **Email uniqueness approach**: Claude initially proposed `unique=True`; Codex noted PostgreSQL uniqueness is case-sensitive. Resolved: use `UniqueConstraint(Lower("email"))` + lowercase normalization on save.
- **Password in CLI**: Draft showed `--password` in `start-web.sh`; Codex flagged process-argument leakage. Resolved: use `--from-env` flag that reads from `os.environ` directly.
- **Existing drifted accounts**: Codex argued this is not optional. User decided: data migration auto-fix.
- **Scope of role/flag sync**: Claude initially only covered creation paths; Codex required sync in `update_user_role` API too. Resolved: `sync_admin_flags` called from all mutation paths.
- **`select_for_update` alone insufficient**: Codex noted it doesn't protect the create path. Resolved: `transaction.atomic()` + `IntegrityError` handling for the create case.

### Convergence Status

- Final Status: `converged`
- Rounds: 2
- All `REQUIRED_CHANGES` from both rounds have been addressed

## Pending User Decisions

- DEC-1: ADMIN role privilege mapping
  - Claude Position: ADMIN = is_staff + is_superuser (simplest, full Django admin access)
  - Codex Position: Either approach works; is_staff-only is more granular but adds complexity
  - Tradeoff Summary: Both flags is simpler and matches current expectations; is_staff-only would need additional Django permission configuration
  - Decision Status: `DECIDED — ADMIN = is_staff + is_superuser`

- DEC-2: Existing drifted account handling
  - Claude Position: Data migration auto-fix (sync is_superuser users to role=ADMIN)
  - Codex Position: Must be addressed, not optional; data migration or system check
  - Tradeoff Summary: Auto-fix is cleaner but could silently elevate accounts; system check is safer but manual
  - Decision Status: `DECIDED — Data migration auto-fix`

- DEC-3: AUTH_PASSWORD_VALIDATORS configuration
  - Claude Position: Add now, since validate_password() is already called but has no validators configured
  - Codex Position: Either add now or defer; calling validate_password() without validators is effectively a no-op
  - Tradeoff Summary: Adding validators now affects registration and password change flows globally, not just create_admin
  - Decision Status: `DECIDED — Add Django's 4 standard validators now`

- DEC-4: Django Admin User model registration
  - Claude Position: Register basic UserAdmin for operational convenience
  - Codex Position: Optional improvement; useful if Django admin is meant as a real operational fallback
  - Tradeoff Summary: Low effort, provides immediate value for user browsing/debugging via /admin/
  - Decision Status: `DECIDED — Register basic UserAdmin`

## Implementation Notes

### Code Style Requirements
- Implementation code and comments must NOT contain plan-specific terminology such as "AC-", "Milestone", "Step", "Phase", or similar workflow markers
- These terms are for plan documentation only, not for the resulting codebase
- Use descriptive, domain-appropriate naming in code instead

### Security Considerations
- `create_admin` is CLI-only; no API endpoint exposes admin creation
- Passwords are read via `getpass` (interactive) or `os.environ` (--from-env), never echoed
- Admin accounts cannot be banned by other admins (existing guard in `admin_api.py`)
- Admins cannot modify their own role (existing guard in `admin_api.py`)
- Production `ADMIN_PASSWORD` should be injected via secrets management (not in code or config files)

--- Original Design Draft Start ---

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

--- Original Design Draft End ---
