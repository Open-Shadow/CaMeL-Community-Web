# Ask Codex Input

## Question

You are reviewing a candidate implementation plan for CaMeL Community Web. This is a second-pass review to challenge and refine the plan.

## Context
The project is a Django+React community platform (Skill Marketplace, Bounty Board, Workshop). A comprehensive test report (2026-04-09) found 9 defects (D1-D9). The draft asks for full end-to-end testing and fixing of all user flows.

## Candidate Plan v1

### Goal
Fix all known defects and verify end-to-end flows for Auth, Skill Marketplace, Bounty Board, and Workshop modules, both locally and on the production server.

### Proposed Approach

**Milestone 1: Stabilize Baseline**
- Fix D8 (pytest segfault) - restore automated test baseline
- Fix D1 (logout 500) - add token blacklist support to SimpleJWT config
- Fix D3 (workshop tip 500) - change auth=login_required to auth=AuthBearer()
- Fix D5 (old invitation generate API) - remove or fix legacy endpoint
- Fix D4 (credit ranking my_rank/my_score null) - add AuthBearer() to ranking router

**Milestone 2: Fix Economic Flows**
- Fix D2 (invite first-deposit reward webhook 500) - handle Celery unavailability gracefully or ensure proper error handling
- Fix D7 (financial report total_fees=0) - persist PLATFORM_FEE transaction record when charging skill calls

**Milestone 3: Complete Missing Features**
- Fix D6 (bounty application reject) - add reject endpoint and frontend button
- Fix D9 (docs/code status mismatch) - update docs/07 to match actual code state

**Milestone 4: End-to-End Flow Verification**
- Auth flow: register -> verify email -> login -> profile edit -> logout
- Skill flow: create -> submit -> review/approve -> list/search -> call (free+paid) -> review -> version management
- Bounty flow: create -> publish -> apply -> accept -> deliver -> approve/revision -> dispute -> arbitrate
- Workshop flow: create article -> publish -> comment -> vote -> tip -> series
- Payment flow: deposit -> balance check -> transactions
- Cross-module: credit score effects, notification delivery, wallet reconciliation

**Milestone 5: Production Verification**
- Deploy fixes via GitHub Actions
- Verify flows on production server (43.248.9.221)
- Verify Docker containers, Celery workers, Redis connectivity

### Acceptance Criteria
- AC-1: All 9 defects (D1-D9) are fixed and verified
- AC-2: Backend pytest suite runs green (no segfault, all tests pass)
- AC-3: Frontend build passes without errors
- AC-4: Auth module end-to-end flow passes (register/login/logout/OAuth/password-reset)
- AC-5: Skill Marketplace end-to-end flow passes (create/review/call/payment)
- AC-6: Bounty Board end-to-end flow passes (create/apply/deliver/settle/arbitrate)
- AC-7: Workshop end-to-end flow passes (article/comment/vote/tip/series)
- AC-8: Economic invariants hold (balance + frozen_balance reconciles, fees recorded)
- AC-9: Production deployment succeeds and deployed flows work

### Path Boundaries
- Upper: Fix all D1-D9, verify all 4 module flows E2E, add post-deploy smoke test
- Lower: Fix D1/D2/D3/D8 (blocking defects), verify golden path for each module
- In scope: Auth, Skills, Bounties, Workshop, Payments, Credits, Notifications (as dependencies)
- Out of scope: Admin pages (P3-ADMIN-005/006/007/009), Leaderboard (P3-RANK-002/003/004), PWA/SEO, mobile layout

### Decisions Made
- Testing approach: manual simulation + backend pytest (no new E2E framework like Playwright)
- External providers: Stripe in test/sandbox mode; OAuth verified via mock only; email via console/locmem backend
- Staging: use local Docker environment for pre-deployment verification, production server for final smoke

## Review Request

Please provide your assessment in these exact sections:

AGREE: Points you accept as reasonable

DISAGREE: Points you consider unreasonable and why

REQUIRED_CHANGES: Must-fix items before this plan can proceed

OPTIONAL_IMPROVEMENTS: Non-blocking suggestions

UNRESOLVED: Opposite opinions that need the user to decide

## Configuration

- Model: gpt-5.4
- Effort: high
- Timeout: 3600s
- Timestamp: 2026-04-11_15-11-01
