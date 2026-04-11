# Ask Codex Input

## Question

You are reviewing a candidate plan for CaMeL Community Web full-flow test & fix. This is a second-pass review.

## Candidate Plan v1 (discovered independently, no test report)

### Discovered Issues (by severity)

BLOCKERS:
B1: Any logged-in user can credit own balance via POST /payments/deposits without Stripe payment
B2: Logout 500 - token_blacklist not in INSTALLED_APPS
B3: Workshop tip 500 - auth=login_required is a no-op decorator, not AuthBearer()
B4: Invite first-deposit reward TypeError - adds float 0.50 to DecimalField
B5: CreditService notification calls use user= instead of recipient= (TypeError)
B6: Arbitration double-settlement - auto_finalize then admin_finalize can double-payout

HIGH:
H1: AuthBearer doesn't check is_active - banned users keep API access
H2: Token refresh doesn't check is_active - banned users can refresh indefinitely
H3: Bounty GET endpoints trigger process_automations() (mutates data, settles money)
H4: SSE notifications block sync gunicorn workers (3 connections = DoS)
H5: Bounty detail exposes all applications/deliverables/arbitration publicly
H6: Platform fee not recorded as PLATFORM_FEE transaction

MEDIUM:
M1: Credit ranking my_rank/my_score always null (missing AuthBearer)
M2: Bounty application lacks reject feature (no status field)
M3: Username = email (privacy leak in public profiles)
M4: Skill calls return simulated output (not real AI)
M5: Meilisearch uses :latest (unpinned in production)
M6: Deploy has no health check (just sleep 10)

### Proposed Approach
Milestone 1: Fix blockers (B1-B6)
Milestone 2: Fix high-severity issues (H1-H6) 
Milestone 3: Fix medium issues (M1-M3, M6)
Milestone 4: Defer M4 (AI integration) and M5 to separate effort
Milestone 5: Full-flow verification (local + production)

### Scope Decisions
- M4 (skill AI output) deferred as it requires AI provider integration, not a bug fix
- Admin panel: test as dependency, not full coverage
- External providers: sandbox/mock only
- Production: state-mutating test with dedicated accounts

## Review Request
AGREE: Points accepted as reasonable
DISAGREE: Points unreasonable and why
REQUIRED_CHANGES: Must-fix before convergence
OPTIONAL_IMPROVEMENTS: Non-blocking suggestions
UNRESOLVED: Items needing user decision

## Configuration

- Model: gpt-5.4
- Effort: high
- Timeout: 3600s
- Timestamp: 2026-04-11_16-20-37
