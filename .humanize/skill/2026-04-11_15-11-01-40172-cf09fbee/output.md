AGREE:
- Sequencing the work as baseline -> money paths -> missing features -> verification is reasonable.
- Keeping production to a final smoke after local verification is reasonable. The repo already has a deploy workflow at [deploy.yml](/home/yinch/Projects/CaMeL_Community_Web/.github/workflows/deploy.yml#L1).
- Not introducing Playwright right now is reasonable if the plan compensates with stronger API-level regression tests plus a small manual UI smoke.
- D2 and D7 deserve explicit attention because they affect wallet/accounting correctness, not just UI behavior.
- D6 and D9 are valid scope items. The codebase really does only expose accept today at [api.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/bounties/api.py#L222) and the bounty page only renders an accept button at [BountyDetailPage.tsx](/home/yinch/Projects/CaMeL_Community_Web/frontend/src/pages/bounty/BountyDetailPage.tsx#L185).

DISAGREE:
- Milestone 1 assumes D8 is still an open blocker. On April 11, 2026, the current workspace `pytest` baseline is already green: `513 passed`. So D8 should be revalidated first, not treated as a guaranteed fix item.
- “Fix D1 by adding token blacklist support” is too prescriptive. The current logout code calls `refresh.blacklist()` at [api.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/accounts/api.py#L205), but blacklist support is not installed in [base.py](/home/yinch/Projects/CaMeL_Community_Web/backend/config/settings/base.py#L9) or configured in [base.py](/home/yinch/Projects/CaMeL_Community_Web/backend/config/settings/base.py#L157). That is a product/architecture choice, not an obvious one-line fix.
- “Handle Celery unavailability gracefully or ensure proper error handling” for D2 is too vague. The real issue is the webhook doing `.delay()` inline at [webhooks.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/payments/webhooks.py#L71); the plan does not define whether rewarding becomes synchronous fallback, durable retry, or best-effort async.
- Calling the whole effort “full end-to-end” is overstated. The stated approach is manual simulation plus pytest, while OAuth and email are mock-only and not real provider E2E.
- Production verification as written is too broad for money-moving flows. Deposits, tips, bounties, and rewards mutate balances and credits; that cannot be a vague “verify flows on production” step.

REQUIRED_CHANGES:
- Add a Step 0: revalidate D1-D9 on the current branch and produce a fresh defect matrix. The April 9, 2026 test report is already partially stale relative to the April 11, 2026 workspace.
- Replace “manual simulation + backend pytest” with an explicit regression matrix: for each still-open defect, add or update an automated test. The current suite can pass while these defects exist; for example, the repo has no automated coverage for logout, ranking personalization, invitation generate, or webhook broker-down behavior.
- Split acceptance criteria into three buckets:
  1. Local deterministic checks.
  2. Mocked external-provider checks.
  3. Production smoke.
  Do not claim OAuth/real email/Stripe are “E2E passed” unless they are verified against actual configured providers.
- Make D2 concrete: define the expected behavior when Redis/Celery is unavailable, require idempotency, and require a recovery path so the inviter reward is not silently lost.
- Make D6 concrete: define rejected-application state, whether the applicant can reapply, whether rejection is visible in history, and whether notifications are sent.
- Make D7 concrete for existing data: decide whether the fix is prospective only or includes backfilling historical `PLATFORM_FEE` records. Just writing new fee rows will not repair current admin reports.
- Add production prerequisites: required access, test accounts, rollback criteria, and which prod checks are read-only vs state-mutating.
- Clarify the verification gate to use the existing regression script at [fullflow_check.sh](/home/yinch/Projects/CaMeL_Community_Web/scripts/fullflow_check.sh#L1) or an expanded equivalent, not an ad hoc checklist only.

OPTIONAL_IMPROVEMENTS:
- Add `frontend` type-check to acceptance, not just build.
- Batch D1/D3/D4/D5 into one small API-fix milestone before the economic work; they are narrow and unblock reliable regression faster.
- Add one scripted post-deploy smoke command set for health, login, a read-only module probe, and worker/redis status.
- Update deployment docs too. The live repo deploy path is Docker/GHCR/SSH in [deploy.yml](/home/yinch/Projects/CaMeL_Community_Web/.github/workflows/deploy.yml#L1), while [08-deployment.md](/home/yinch/Projects/CaMeL_Community_Web/docs/08-deployment.md#L1) still describes Railway/Vercel.

UNRESOLVED:
- D1 logout strategy: server-side refresh-token revocation via blacklist, or a simpler stateless logout contract. Both are defensible, but the plan must pick one.
- Scope target: “fix every reproducible defect plus golden paths” vs “full exhaustive flow verification across all modules.” The current lower/upper bounds and acceptance criteria do not agree.
- D7 historical accounting: should the team repair old fee data, or accept that reports become correct only from the fix forward?
- Production validation depth: should prod run only smoke-safe checks, or should it exercise money-moving flows with dedicated sandbox/test accounts?
