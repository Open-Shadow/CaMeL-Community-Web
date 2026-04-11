CORE_RISKS

- The draft assumes “manual user simulation” is enough, but the scoped flows already depend on external systems: email, OAuth, Stripe, Stripe webhooks, Redis/Celery, Meilisearch, SSE, and media storage. Those fail differently from normal page-click testing.
- It assumes local and production are behaviorally close. They are not: current test settings use SQLite + locmem cache/email, while production uses PostgreSQL + Redis + Celery + Meilisearch. A flow can pass locally and still fail in Docker/prod.
- It assumes the current baseline is stable enough to “fix immediately, then re-verify.” The repo already records broken closures such as logout, workshop tip, invite first-deposit reward, and an unusable pytest baseline in [测试报告.md](/home/yinch/Projects/CaMeL_Community_Web/docs/测试报告.md).
- It treats the four business modules as isolated. In reality, Skill/Bounty/Workshop all cross the same auth, wallet, credits, permissions, notifications, and async infrastructure.
- It assumes checking `http://43.248.9.221/` is sufficient production verification. That does not prove callback URLs, CORS/CSRF, HTTPS-sensitive behavior, worker execution, or provider integrations.
- It assumes deployment success equals user-flow success. Current GitHub Actions deploy only restarts containers and prints `docker compose ps`; it does not run app-level smoke tests after deploy.

MISSING_REQUIREMENTS

- Explicit role coverage: guest, normal user, creator, moderator, admin.
- Explicit state-machine coverage for each module:
  - Skill: draft, submit, approve/reject, publish, call, review.
  - Bounty: create, publish, apply, accept/reject, deliver, revision, approve, dispute, arbitration, appeal, cancel.
  - Workshop: draft, publish, comment, vote, tip, series.
- Negative-path requirements: invalid/expired tokens, duplicate email, bad invite code, insufficient balance, self-tip/self-purchase, invalid amounts, unauthorized access, deleted content, repeated submissions.
- Idempotency and double-action protection: repeated Stripe webhook, double payment callback, repeated approve/dispute actions, concurrent bounty acceptance.
- Real provider requirements: email delivery, OAuth provider config, Stripe test-mode flow, webhook replay.
- Browser/device requirements: mobile layout, major browsers, console/network errors, upload handling.
- Data integrity requirements: wallet balance, frozen balance, fees, rewards, and transaction history must reconcile after every economic flow.
- Observability requirements: what logs/metrics/screenshots are required to prove a failure and prove a fix.
- Scope boundaries: admin, leaderboard, invitations, notifications, search, SEO/PWA are adjacent to the scoped flows but not clearly included/excluded.

TECHNICAL_GAPS

- There is no real browser E2E harness in the repo now; only backend tests plus frontend build/type-check level coverage.
- Local test parity is weak. `config.settings.test` swaps production dependencies out for SQLite/locmem, so it is not a faithful end-to-end environment.
- Current WSL environment may not be enough by itself to validate the production topology if Docker, Redis, PostgreSQL, and Meilisearch are not actually running.
- Production deployment lacks post-deploy smoke automation and rollback gates in [.github/workflows/deploy.yml](/home/yinch/Projects/CaMeL_Community_Web/.github/workflows/deploy.yml).
- Some route/API contracts are already inconsistent, especially around payments and trailing-slash behavior; that makes manual testing ambiguous unless a canonical API contract is fixed first.
- Async work is a major gap: many flows are only truly complete after Celery tasks/webhooks run.
- Public-IP verification is not enough for root-cause analysis unless the tester also has server SSH/log access.
- No clear staging environment is defined, so “test on production server” risks mixing verification with live-user state.

ALTERNATIVE_DIRECTIONS

- Split the work into two stages:
  - Stage 1: stabilize baseline and fix known blocking defects first.
  - Stage 2: run full-flow regression only after baseline is trustworthy.
- Add a small golden-path E2E suite for the highest-value flows instead of relying mainly on ad hoc manual clicking.
- Use a Dockerized staging environment that matches production services more closely than WSL test settings.
- Add post-deploy smoke checks in CI against the deployed app, not just container restart checks.
- Define an “economic invariants” test set for wallet, escrow, tips, fees, rewards, and webhook idempotency.
- Test external-provider flows in sandbox mode and reserve public-production checks for smoke only.
- Treat server verification as “observe and confirm” and do destructive/full-state testing in staging, not on the live host.

QUESTIONS_FOR_USER

- Do you want real end-to-end validation for Stripe, email, GitHub OAuth, and Google OAuth, or are mocks/sandbox flows acceptable?
- Do we have SSH and log access to the production server, or only the public URL?
- Is a staging environment allowed, or must all server verification happen on the live deployment?
- Are admin/moderator flows in scope for this task, or only normal end-user flows?
- Are invitations, wallet/payments, notifications, and search considered in scope because they are dependencies of the four main modules?
- What is the pass/fail bar: no P0/P1 defects in scoped flows, or literally all known issues fixed?
- Can the implementation add testing infrastructure such as Playwright, health endpoints, and CI smoke tests?

CANDIDATE_CRITERIA

- A reproducible local/staging environment exists that includes PostgreSQL, Redis, Celery, and Meilisearch, not only SQLite test settings.
- Backend regression is stable and green; frontend build/type-check/lint are green; no baseline crash blocks retesting.
- The plan defines exact golden flows, actors, and expected state transitions for Auth, Skill Marketplace, Bounty Board, and Workshop.
- All scoped economic flows verify ledger correctness: balance, frozen balance, fees, rewards, and history all reconcile.
- External-provider flows are either validated end to end in sandbox or explicitly marked out of scope with rationale.
- Each defect found is fixed, retested locally, and retested once in a production-like environment.
- GitHub Actions deployment completes and a post-deploy smoke suite passes against the deployed URL.
- No open High severity defects remain in the scoped flows.
- The plan records evidence for each acceptance item: request/response proof, screenshots, logs, or DB state checks.
- Out-of-scope incomplete areas are explicitly listed so “full flow” is not interpreted ambiguously.
