# Ask Codex Input

## Question

You are performing a second convergence review of a revised candidate plan for CaMeL Community Web full-flow testing and fix effort.

## Changes Made After Round 1 Feedback

1. ADDED Step 0: Revalidate D1-D9 on current branch before fixing. D8 (pytest segfault) may already be resolved (513 tests passing as of April 11).

2. REVISED: Each defect fix now requires a corresponding automated test in the regression suite.

3. SPLIT AC into three buckets:
   - Local deterministic: pytest green, frontend build+typecheck, API-level flow tests
   - Mocked external: OAuth mock, email via locmem, Stripe sandbox
   - Production smoke: read-only probes + limited flow verification

4. REVISED D2 fix strategy: Webhook will use synchronous fallback when Celery .delay() fails (try/except around delay, fall back to synchronous execution). Add idempotency guard (check if reward already granted before processing). Add automated test for both Celery-available and Celery-unavailable scenarios.

5. REVISED D6 specification: Add reject_application endpoint with REJECTED status. Rejected applicants cannot reapply to the same bounty. Rejection triggers notification. Rejection is visible in application history. Frontend adds reject button alongside accept.

6. MARKED D7 historical accounting as user decision: prospective-only fix (new PLATFORM_FEE transactions from fix forward) vs backfill historical data.

7. ADDED production prerequisites: SSH/log access required, dedicated test accounts, distinction between read-only checks (homepage, API docs, listing pages) and state-mutating checks (register test account, create/delete test content).

8. ADDED: Use scripts/fullflow_check.sh as the verification gate, which runs targeted flow tests, full pytest regression, frontend typecheck, and production build.

9. REVISED Path Boundaries:
   - Upper: Fix all reproducible D1-D9 defects, add regression tests for each, verify golden path for each module via API-level tests and manual UI smoke, deploy and smoke-test on production
   - Lower: Fix D1/D2/D3 (blocking defects), revalidate D8, run scripts/fullflow_check.sh green, verify golden paths locally via manual simulation

10. REVISED: Renamed effort from 'full end-to-end' to 'full-flow defect fix and regression verification' to be honest about scope.

11. ADDED: D1 logout strategy marked as user decision (blacklist vs stateless).

12. ADDED: Production validation depth marked as user decision (smoke-only vs money-moving flows with test accounts).

## Prior Disagreements Status
- D8 stale assumption: RESOLVED (added revalidation step)
- D1 too prescriptive: RESOLVED (marked as user decision)
- D2 too vague: RESOLVED (concrete sync fallback + idempotency)
- 'Full E2E' overstated: RESOLVED (renamed, split AC buckets)
- Production too broad: RESOLVED (prerequisites + read-only/mutating split)

## Review Request
Provide your assessment in these exact sections:

AGREE: Points you accept as reasonable
DISAGREE: Points you consider unreasonable and why
REQUIRED_CHANGES: Must-fix items before convergence
OPTIONAL_IMPROVEMENTS: Non-blocking suggestions
UNRESOLVED: Opposite opinions needing user decisions

## Configuration

- Model: gpt-5.4
- Effort: high
- Timeout: 3600s
- Timestamp: 2026-04-11_15-17-57
