AGREE:
- Adding Step 0 is the right correction. On April 11, 2026, the current branch passes the existing gate: `scripts/fullflow_check.sh` completed with 75 targeted tests, 513 total backend tests, frontend typecheck, and production build. That makes D8 a revalidation item, not an assumed active defect.
- Requiring regression coverage for code defects is reasonable and raises the plan quality.
- Splitting acceptance into local deterministic, mocked external, and production smoke is the right scope boundary.
- Renaming the effort to “full-flow defect fix and regression verification” is accurate.
- Marking D1, D7, and production-depth choices as user decisions is correct.
- The D2 direction is reasonable: keep webhook processing resilient when Celery submission fails, and make reward granting idempotent.
- Adding explicit production prerequisites and separating read-only from mutating checks is necessary.
- Using [scripts/fullflow_check.sh](/home/yinch/Projects/CaMeL_Community_Web/scripts/fullflow_check.sh#L1) as the local deterministic gate is reasonable.

DISAGREE:
- “Each defect fix now requires a corresponding automated test” is too absolute. D9 is docs drift, and D8 may already be closed; neither necessarily maps to a new regression test.
- Treating [scripts/fullflow_check.sh](/home/yinch/Projects/CaMeL_Community_Web/scripts/fullflow_check.sh#L1) as the single proof point for all AC buckets is not accurate today. It runs pytest, typecheck, and build only; it does not perform production probes and does not explicitly exercise a Stripe webhook/sandbox path.
- D6 is not a small endpoint addition. Current [backend/apps/bounties/models.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/bounties/models.py#L58) has no application status/history fields, and current [backend/apps/bounties/services.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/bounties/services.py#L179) rewrites an existing application in place.

REQUIRED_CHANGES:
- Make D6 a schema/API/UI change, not just a route/button change. You need explicit `BountyApplication` review state such as status, rejection reason, reviewer/timestamp, and updated API responses; otherwise “reject”, “cannot reapply”, notification, and visible history are not cleanly implementable.
- Tighten D2’s fallback spec. The `try/except` must wrap broker submission failure around `.delay()` only, not broadly swallow downstream business errors. Also define the idempotency guard concretely, ideally with a durable reward reference keyed to inviter + invitee + first deposit. Current webhook code in [backend/apps/payments/webhooks.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/payments/webhooks.py#L17) does not yet specify that.
- Align the verification story with the actual gate. Either extend [scripts/fullflow_check.sh](/home/yinch/Projects/CaMeL_Community_Web/scripts/fullflow_check.sh#L1) to cover the mocked-external checks you claim, or state explicitly that it is only the deterministic local gate and mocked/prod validation are separate steps.
- Step 0 should define a disposition for each D1-D9 item: reproduced and fixed, reproduced and deferred by boundary, or closed as non-repro/already resolved. D8 specifically should now be treated as “verify closed if green”.

OPTIONAL_IMPROVEMENTS:
- Add a Step 0 results table with exact command and outcome for each D1-D9 item.
- Add a dedicated webhook-level regression test around [backend/apps/payments/webhooks.py](/home/yinch/Projects/CaMeL_Community_Web/backend/apps/payments/webhooks.py#L17), even if payment service tests already exist.
- Add acceptance rows for both D1 logout strategies so the chosen behavior is explicit before implementation.
- Add a short rollback/containment note for production smoke if a mutating probe fails after deploy.

UNRESOLVED:
- D1 logout behavior: blacklist-backed invalidation vs stateless client-side logout.
- D7 accounting scope: prospective-only `PLATFORM_FEE` recording vs historical backfill/reconciliation.
- Production validation depth: smoke-only vs money-moving flows with dedicated test accounts.
