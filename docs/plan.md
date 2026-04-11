# Full-Flow Test & Fix Plan

## Goal Description

Verify and fix all user-facing flows across the four core modules (Auth, Skill Marketplace, Bounty Board, Workshop) to ensure a smooth end-to-end user experience. All fixes must work both locally (WSL) and on the production server (43.248.9.221) deployed via GitHub Actions + Docker.

## Acceptance Criteria

Following TDD philosophy, each criterion includes positive and negative tests for deterministic verification.

- AC-1: Authentication flows work correctly and securely
  - Positive Tests (expected to PASS):
    - New user can register, receives JWT tokens, and gets initial credit score of 50
    - Registered user can log in with correct email/password and receive valid tokens
    - Logged-in user can log out and refresh token is invalidated
    - Token refresh returns new valid access token for active users
    - Deactivated user's existing tokens are rejected by AuthBearer
  - Negative Tests (expected to FAIL):
    - Login with wrong password returns 401
    - Deactivated user cannot refresh tokens
    - Logged-out user's refresh token cannot be reused
    - Unauthenticated requests to protected endpoints return 401
  - AC-1.1: Registration generates a non-email username for privacy
    - Positive: New user's username is a random string, not their email
    - Negative: Public profile URL does not contain user's email address

- AC-2: Financial operations are correct and atomic
  - Positive Tests (expected to PASS):
    - Deposit endpoint requires Stripe webhook proof before crediting balance
    - Bounty escrow correctly freezes creator's balance on creation
    - Bounty completion pays out to hunter and releases escrow
    - Skill call charges discounted price and records PLATFORM_FEE transaction
    - Invitation reward uses Decimal arithmetic (no TypeError)
  - Negative Tests (expected to FAIL):
    - Direct POST to /deposits without Stripe proof does not credit balance
    - Insufficient balance bounty creation is rejected
    - Float + Decimal mixing in payment operations raises TypeError (before fix)

- AC-3: Bounty lifecycle flows work end-to-end
  - Positive Tests (expected to PASS):
    - Creator posts bounty → applicant applies → creator accepts → hunter delivers → creator approves → COMPLETED
    - Creator can request revision (up to 3 rounds) before approval
    - Creator can cancel OPEN or IN_PROGRESS bounty with escrow refund
    - Dispute → cooldown → arbitration → vote → settlement works correctly
    - Appeal charges fee and makes case visible to admin
  - Negative Tests (expected to FAIL):
    - Non-party user cannot start arbitration
    - Non-party user cannot appeal
    - Already-resolved arbitration cannot be double-settled
    - GET endpoints do not trigger side effects (no automations on read)

- AC-4: Workshop (Knowledge Base) flows work correctly
  - Positive Tests (expected to PASS):
    - User can create, edit, publish articles
    - Users can vote, comment on articles
    - Tip endpoint requires authentication and correctly transfers balance
  - Negative Tests (expected to FAIL):
    - Unauthenticated user cannot tip (tip endpoint enforces auth)
    - Tip with insufficient balance is rejected

- AC-5: Notification and credit systems are reliable
  - Positive Tests (expected to PASS):
    - Bounty freeze notification is sent when credit drops below threshold
    - Bounty unfreeze notification is sent when credit recovers
    - Credit score changes produce correct log entries
  - Negative Tests (expected to FAIL):
    - NotificationService.send() with wrong parameter name raises TypeError (before fix)
    - SSE endpoint does not block all workers (after fix)

- AC-6: Infrastructure is production-ready
  - Positive Tests (expected to PASS):
    - Docker build completes successfully
    - Deploy workflow uses proper health check instead of sleep
    - Meilisearch version is pinned in compose files
    - All existing tests pass (492+) after fixes
    - Frontend type-check and build pass
  - Negative Tests (expected to FAIL):
    - Unpinned meilisearch:latest should not appear in deploy compose

- AC-7: Bounty detail API returns role-appropriate data
  - Positive Tests (expected to PASS):
    - Bounty creator sees full detail including all applications, deliverables, arbitration
    - Accepted applicant sees full detail
    - Arbitrators see arbitration details
    - Non-participant sees bounty summary with empty applications/deliverables and null arbitration
    - Comments and reviews remain public for all users
  - Negative Tests (expected to FAIL):
    - Anonymous user should not see application proposals
    - Non-participant should not see deliverable content

## Path Boundaries

### Upper Bound (Maximum Acceptable Scope)
All 16 identified issues are fixed with targeted tests, bounty detail API is role-aware, auth system properly checks is_active at all layers, arbitration workflow is complete with appeal visibility, SSE endpoint is converted to polling or timeout-bounded, production deployment verified with full user flow on 43.248.9.221.

### Lower Bound (Minimum Acceptable Scope)
All 8 blocker issues (B1-B8) are fixed, the 4 high-severity issues (H3-H6) are fixed, existing test suite remains green, frontend builds cleanly, and core user flows (register → login → create bounty → complete bounty) work on production.

### Allowed Choices
- Can use: Django ORM, existing test patterns (pytest + Django test client), existing schema patterns
- Can use: Polling-based SSE replacement OR timeout-bounded SSE (either approach acceptable)
- Can use: Random username generation (UUID prefix, adjective-noun pattern, or similar)
- Cannot use: New dependencies or frameworks not already in the project
- Cannot use: Breaking changes to existing API contracts (add fields, don't remove)

## Feasibility Hints and Suggestions

### Conceptual Approach

**Auth fixes (B2, B4, B7, B8)**: Straightforward — add `is_active` check in `AuthBearer.authenticate()`, add blacklist app to INSTALLED_APPS + migration, replace `login_required` with `AuthBearer()` in workshop tip route, add `is_active` check in refresh endpoint.

**Financial fixes (B1, B3, B5, H6)**: B1 requires removing or guarding the direct deposit endpoint. B3 is a one-line `Decimal("0.50")` fix. B5 is a one-line `user=` → `recipient=` fix. H6 requires adding a `PLATFORM_FEE` Transaction.objects.create() call in `charge_skill_call`.

**Arbitration fixes (B6)**: Multi-part — fix the idempotency guard in `_apply_arbitration_result` to check `resolved_at` alone (not AND with `admin_final_result`), add actor authorization to `start_arbitration`, restrict `appeal` to bounty parties, add bounty status check in `start_arbitration`, update `list_active_disputes` to include appealed cases.

**API safety (H3, H4, H5)**: H3 — move `process_automations()` to a Celery periodic task. H4 — add connection timeout or convert to polling. H5 — check request.auth identity against bounty participants in `_detail_out`.

### Relevant References
- `backend/common/permissions.py` — AuthBearer class, login_required decorator
- `backend/apps/accounts/api.py` — register, login, logout, refresh endpoints
- `backend/apps/bounties/services.py` — BountyService with all business logic
- `backend/apps/bounties/api.py` — Bounty API routes
- `backend/apps/payments/services.py` — PaymentsService with charge/settle/deposit
- `backend/apps/payments/api.py` — Deposit endpoint
- `backend/apps/credits/services.py` — CreditService with notification calls
- `backend/apps/notifications/services.py` — NotificationService.send() signature
- `backend/apps/notifications/api.py` — SSE endpoint
- `backend/apps/workshop/api.py` — Tip endpoint with broken auth
- `backend/apps/accounts/tasks.py` — Invitation reward with float bug
- `backend/config/settings/base.py` — INSTALLED_APPS
- `deploy/docker-compose.server.yml` — Meilisearch version
- `.github/workflows/deploy.yml` — Deploy with sleep 10
- `scripts/fullflow_check.sh` — Existing verification gate

## Dependencies and Sequence

### Milestones

1. **Milestone 1 — Security & Auth (B1, B2, B4, B7, B8, AC-1.1/M3-reg-only)**:
   - Phase A: Fix AuthBearer to check is_active (B7)
   - Phase B: Fix refresh to check is_active (B8)
   - Phase C: Install token blacklist app + migration (B4)
   - Phase D: Replace login_required with AuthBearer() in workshop tip (B2)
   - Phase E: Guard or remove direct deposit endpoint (B1)
   - Phase F: Generate random username on registration instead of email (M3)
   - Phase G: Add/update tests for all auth fixes

2. **Milestone 2 — Financial Integrity (B3, B5, H6)**:
   - Phase A: Fix float→Decimal in invitation reward (B3)
   - Phase B: Fix user= → recipient= in CreditService notifications (B5)
   - Phase C: Add PLATFORM_FEE transaction record in charge_skill_call (H6)
   - Phase D: Add/update tests for financial fixes

3. **Milestone 3 — Bounty Workflow & API Safety (B6, H3, H5, AC-7)**:
   - Phase A: Fix arbitration idempotency guard (B6-guard)
   - Phase B: Add actor authorization to start_arbitration (B6-auth)
   - Phase C: Restrict appeal to bounty parties + fix appeal visibility (B6-appeal)
   - Phase D: Add bounty status check in start_arbitration (B6-state)
   - Phase E: Move process_automations to Celery periodic task (H3)
   - Phase F: Implement role-based bounty detail response (H5/AC-7)
   - Phase G: Add/update tests for bounty fixes

4. **Milestone 4 — Infrastructure & SSE (H4, M5, M6)**:
   - Phase A: Fix SSE endpoint — add timeout or convert to polling (H4)
   - Phase B: Pin Meilisearch version in deploy compose (M5)
   - Phase C: Replace sleep 10 with health check endpoint in deploy (M6)

5. **Milestone 5 — Regression & Production Verification**:
   - Phase A: Run full backend test suite (target: 492+ tests passing)
   - Phase B: Run frontend type-check and build
   - Phase C: Deploy to production and verify full user flow on 43.248.9.221
   - Phase D: Document test results

Milestone 1 has no dependencies. Milestones 2 and 3 can start in parallel after Milestone 1 (auth fixes needed first for proper testing). Milestone 4 is independent. Milestone 5 runs after all others complete.

## Task Breakdown

| Task ID | Description | Target AC | Tag | Depends On |
|---------|-------------|-----------|-----|------------|
| task1 | Fix AuthBearer.authenticate() to check is_active | AC-1 | coding | - |
| task2 | Fix refresh endpoint to check is_active | AC-1 | coding | - |
| task3 | Add token_blacklist to INSTALLED_APPS + run migration | AC-1 | coding | - |
| task4 | Replace login_required with AuthBearer() in workshop tip endpoint | AC-4 | coding | - |
| task5 | Guard/remove direct deposit endpoint (require Stripe webhook) | AC-2 | coding | - |
| task6 | Generate random username on registration (not email) | AC-1.1 | coding | - |
| task7 | Add tests for auth security fixes (B1, B2, B4, B7, B8, M3) | AC-1 | coding | task1-task6 |
| task8 | Fix float→Decimal in invitation reward task | AC-2 | coding | - |
| task9 | Fix user= → recipient= in CreditService notification calls | AC-5 | coding | - |
| task10 | Add PLATFORM_FEE transaction in charge_skill_call | AC-2 | coding | - |
| task11 | Add tests for financial fixes (B3, B5, H6) | AC-2, AC-5 | coding | task8-task10 |
| task12 | Fix arbitration idempotency guard (_apply_arbitration_result) | AC-3 | coding | - |
| task13 | Add actor authorization to start_arbitration + status check | AC-3 | coding | - |
| task14 | Restrict appeal to bounty parties + fix appeal admin visibility | AC-3 | coding | - |
| task15 | Move process_automations from GET endpoints to Celery periodic task | AC-3 | coding | - |
| task16 | Implement role-based bounty detail response (hide sensitive data from non-participants) | AC-7 | coding | - |
| task17 | Add tests for bounty workflow fixes (B6, H3, H5) | AC-3, AC-7 | coding | task12-task16 |
| task18 | Fix SSE endpoint — add timeout or convert to polling | AC-5 | coding | - |
| task19 | Pin Meilisearch version in deploy compose files | AC-6 | coding | - |
| task20 | Replace sleep 10 with health check in deploy workflow | AC-6 | coding | - |
| task21 | Run full backend test suite + frontend build | AC-6 | coding | task7, task11, task17 |
| task22 | Deploy to production and verify full user flow | AC-6 | analyze | task21 |
| task23 | Document test results and remaining known issues | AC-6 | coding | task22 |

## Claude-Codex Deliberation

### Agreements
- All 8 blocker issues (B1-B8) are correctly identified and prioritized
- AuthBearer must check is_active (B7), refresh must check is_active (B8)
- Direct deposit endpoint is a critical security vulnerability (B1)
- Float + Decimal mixing is a real runtime error (B3)
- CreditService notification uses wrong parameter name (B5)
- process_automations() in GET endpoints is a side-effect risk (H3)
- SSE with sync workers is a DoS vector (H4)
- Bounty detail exposes too much data to non-participants (H5)
- PLATFORM_FEE transaction is missing from skill call accounting (H6)
- Meilisearch should be version-pinned (M5)
- M3 (username=email) should be fixed for new registrations only

### Resolved Disagreements
- **B2 scope**: Codex noted only one route uses login_required (workshop tip). Claude agreed to narrow wording but still fix the no-op decorator and any occurrences. Chosen: fix all occurrences but acknowledge scope is narrow.
- **B5 severity**: Codex suggested narrowing. Claude agreed the fix is trivial (one-line per call site) but kept as blocker because the affected flow (bounty freeze) is critical. Chosen: keep as blocker with narrowed description.
- **H4 severity**: Codex agreed High is reasonable. The 3-worker sync setup makes it a real concern.
- **M2 classification**: Codex correctly identified simulated skill output as missing feature. Claude agreed and deferred it.
- **M6 evidence**: Codex initially couldn't find sleep 10, but it exists in .github/workflows/deploy.yml:84. Validated.
- **B6 expansion**: Codex identified additional gaps (start_arbitration state guard, appeal workflow visibility). Claude incorporated all into B6.
- **H5 contract**: Codex asked for clarity on response format. User chose: same schema with empty lists/null for non-participants, comments and reviews stay public.

### Convergence Status
- Final Status: `converged`

## Pending User Decisions

- DEC-1: Username privacy (M3)
  - Claude Position: Fix only at registration time (generate random username for new users)
  - Codex Position: Full fix requires URL/lookup migration, too risky for this cycle
  - Tradeoff Summary: Registration-only fix is low risk but doesn't help existing users
  - Decision Status: `Fix at registration only — new users get random username, existing data unchanged`

- DEC-2: Bounty detail visibility (H5)
  - Claude Position: Same schema, sensitive sub-objects emptied for non-participants
  - Codex Position: Need explicit contract before implementation
  - Tradeoff Summary: Empty-list approach avoids schema changes; full summary-only is more restrictive but requires frontend changes
  - Decision Status: `Hide sensitive sub-objects — applications=[], deliverables=[], arbitration=null for non-participants; comments and reviews stay public`

- DEC-3: Production verification depth
  - Claude Position: Full flow verification with test data creation
  - Codex Position: N/A — open question
  - Tradeoff Summary: Full verification catches deployment-specific issues but creates test data in production
  - Decision Status: `Full flow verification on 43.248.9.221 with test data (clean up after)`

## Implementation Notes

### Code Style Requirements
- Implementation code and comments must NOT contain plan-specific terminology such as "AC-", "Milestone", "Step", "Phase", or similar workflow markers
- These terms are for plan documentation only, not for the resulting codebase
- Use descriptive, domain-appropriate naming in code instead

### Issue Reference

**Blockers (8)**:
- B1: Direct balance crediting bypass — `/payments/deposits` credits balance without Stripe proof (backend/apps/payments/api.py)
- B2: login_required is no-op decorator — workshop tip endpoint has no auth (backend/common/permissions.py, backend/apps/workshop/api.py)
- B3: Float + Decimal TypeError — invitation reward uses `0.50` float (backend/apps/accounts/tasks.py)
- B4: Token blacklist not installed — logout crashes calling `.blacklist()` (backend/config/settings/base.py)
- B5: CreditService notification TypeError — `user=` vs `recipient=` (backend/apps/credits/services.py)
- B6: Arbitration double-settlement + authorization gaps — guard condition, start_arbitration no actor/state check, appeal no party restriction, appeal invisible to admin (backend/apps/bounties/services.py)
- B7: AuthBearer ignores is_active — banned users retain API access (backend/common/permissions.py)
- B8: Refresh token ignores is_active — banned users can infinitely refresh (backend/apps/accounts/api.py)

**High (4)**:
- H3: GET endpoints trigger process_automations() — money-moving side effects from read operations (backend/apps/bounties/api.py, backend/apps/bounties/services.py)
- H4: SSE DoS — while True + time.sleep(5) blocks sync workers (backend/apps/notifications/api.py)
- H5: Bounty detail data exposure — applications/deliverables/arbitration visible to all (backend/apps/bounties/api.py)
- H6: Missing PLATFORM_FEE record — charge_skill_call computes fee but doesn't record it (backend/apps/payments/services.py)

**Medium (4)**:
- M3: Username = email at registration — privacy leak for new users (backend/apps/accounts/api.py) — fix registration only
- M5: Meilisearch unpinned — `latest` tag in deploy compose (deploy/docker-compose.server.yml)
- M6: Deploy readiness gap — `sleep 10` instead of health probe (.github/workflows/deploy.yml:84)

**Deferred**:
- Simulated skill output (missing feature, not a bug)
- Ranking API missing AuthBearer (low traffic endpoint)
- Existing user username migration (deferred per user decision)

--- Original Design Draft Start ---

# 全流程测试修复

## 背景

目前 CaMeL Community 的功能开发已经完毕，接下来需要验证所有功能是否稳定可用，能够直接让用户能够注册访问使用。

## 目标

测试所有功能是否逻辑通畅，不会出现问题，让用户能够有一个流畅的用户体验。
主要注意的模块有如下几点：
- 注册登录模块
- Skill 模型模块
- 悬赏模块
- 知识库模块

请一定保证这几个模块通畅可用。
而且目前的环境是wsl本地开发，最后是需要git action来通过docker部署到服务器上的，请你也务必要保证这些流程在服务器上也是完美可用的。

关于验证测试，你可以直接启动本地的服务，然后查看是否有缺陷，也可以直接访问http://43.248.9.221/ 这个IP来验证，这是我部署服务器的IP。

## 大致思路

测试时，请直接模拟人类用户的操作进行测试验证，查看在流程中是否会遇到问题与bug。如果有，请立即修复并且再次验证。
--- Original Design Draft End ---
