# Skill Module Transformation: Package-Based Marketplace

## Goal Description

Transform the CaMeL Community Skill module from a "platform-hosted Prompt template" model to a "user-uploaded code package (ZIP)" model, inspired by ClawHub. This involves:

1. Replacing inline prompt fields with uploaded ZIP packages containing `SKILL.md` + optional scripts/resources
2. Changing the pricing model from per-use billing (FREE/PER_USE) to one-time purchase (FREE/PAID)
3. Replacing manual review with enhanced automated security scanning + community reporting
4. Adding purchase/download/reporting workflows with proper entitlement tracking
5. Rebuilding frontend skill creation, detail, and profile pages for the new package model

Payment remains $ balance only (credit points are reputation, not currency). Trusted users (credit level >= Craftsman) can instant-publish; new users require admin review.

## Acceptance Criteria

Following TDD philosophy, each criterion includes positive and negative tests for deterministic verification.

- AC-1: Data model correctly reflects the package-based skill structure
  - Positive Tests (expected to PASS):
    - Skill model has fields: `package_file`, `package_sha256`, `package_size`, `readme_html`, `download_count`
    - Skill `pricing_model` accepts values `FREE` and `PAID` only
    - Skill `price` field (renamed from `price_per_use`) stores one-time purchase price
    - Skill `status` enum includes `DRAFT`, `SCANNING`, `APPROVED`, `REJECTED`, `ARCHIVED` (no `PENDING_REVIEW`)
    - SkillVersion has `package_file`, `package_sha256`, `changelog`, `status` fields
    - SkillVersion has no `system_prompt` or `user_prompt_template` fields
    - SkillPurchase model exists with `skill`, `user`, `paid_amount`, `payment_type` fields
    - SkillPurchase enforces unique_together on (skill, user)
    - SkillCall has no `amount_charged` field
    - SkillReport model exists with `skill`, `reporter`, `reason`, `created_at` fields
  - Negative Tests (expected to FAIL):
    - Creating a Skill with `pricing_model=PER_USE` is rejected
    - Creating a Skill with `status=PENDING_REVIEW` is rejected
    - Creating a duplicate SkillPurchase for the same user+skill raises IntegrityError
    - Setting `price` above $10.00 or below $0.01 for PAID skills is rejected by validation
  - AC-1.1: Skill model no longer has inline prompt fields
    - Positive: Skill model does not have `system_prompt`, `user_prompt_template`, `output_format`, `example_input`, `example_output` columns
    - Negative: Attempting to access `skill.system_prompt` raises AttributeError
  - AC-1.2: SkillVersion has version-scoped status for moderation
    - Positive: Each SkillVersion has its own `status` field (SCANNING/APPROVED/REJECTED/ARCHIVED)
    - Negative: A SkillVersion with `status=REJECTED` does not appear in public version listings

- AC-2: ZIP package upload, validation, and storage work correctly
  - Positive Tests (expected to PASS):
    - Uploading a valid ZIP containing SKILL.md creates a Skill record with package fields populated
    - SHA-256 hash is computed and stored on both Skill and SkillVersion
    - Package file is stored with private ACL (not public-read)
    - SKILL.md frontmatter is parsed and metadata fields are populated
    - readme_html is generated from SKILL.md body content and sanitized
    - Package size in bytes is recorded
  - Negative Tests (expected to FAIL):
    - ZIP without SKILL.md is rejected with clear error
    - ZIP exceeding ~10 MB is rejected
    - ZIP containing a file exceeding ~2 MB is rejected
    - ZIP with more than ~50 files is rejected
    - ZIP containing forbidden extensions (.exe, .dll, .so, .bin, .pyc) is rejected
    - ZIP with path traversal (../../) is rejected
    - ZIP with symlinks is rejected
    - ZIP bomb (high compression ratio) is rejected
    - SKILL.md with invalid/missing frontmatter is rejected
  - AC-2.1: SKILL.md frontmatter parsing
    - Positive: `name`, `description`, `version` (SemVer), `output_format`, `category`, `tags`, `example_input`, `example_output` are extracted from frontmatter
    - Negative: Non-SemVer version string is rejected; missing required fields (`name`, `description`, `version`) are rejected

- AC-3: Automated security scanning pipeline processes packages asynchronously
  - Positive Tests (expected to PASS):
    - Submitting a skill triggers a Celery task that runs the scan pipeline
    - Skill/version status transitions to SCANNING immediately upon submission
    - Scan pipeline checks: structure validation, content safety (prompt injection, jailbreak, sensitive content), script safety (shell injection, credential access, data exfiltration, persistence, command injection, obfuscation), metadata consistency
    - PASS result transitions status to APPROVED
    - FAIL result transitions status to REJECTED with `rejection_reason` populated
    - WARN result transitions status to APPROVED with a warning flag
    - Version must have SemVer greater than the latest approved version
  - Negative Tests (expected to FAIL):
    - A skill in SCANNING state cannot be called or downloaded
    - A rejected skill cannot be published without resubmission
  - AC-3.1: Trust-gated publishing
    - Positive: Users with credit level >= Craftsman (score >= 100) have their skills auto-published after scan PASS
    - Negative: Users with credit level < Craftsman have their skills enter a moderator review queue after scan PASS (status remains SCANNING until admin approval)

- AC-4: Purchase workflow creates durable entitlements
  - Positive Tests (expected to PASS):
    - Purchasing a FREE skill creates a SkillPurchase with `payment_type=FREE`, `paid_amount=0`
    - Purchasing a PAID skill deducts from buyer's balance and creates SkillPurchase + Transaction records
    - Platform fee (15%) is deducted and creator receives 85% of purchase price
    - Purchase is idempotent: re-purchasing an already-purchased skill returns the existing record
    - Purchase grants access to all current and future versions
    - Creator buying their own skill auto-creates a free SkillPurchase
  - Negative Tests (expected to FAIL):
    - Purchasing with insufficient balance is rejected (402/400)
    - Purchasing a skill that is not APPROVED is rejected
    - Calling a paid skill without a SkillPurchase record returns 403
    - Downloading a paid skill without a SkillPurchase record returns 403

- AC-5: Download endpoint serves packages securely
  - Positive Tests (expected to PASS):
    - Download endpoint generates a pre-signed S3/R2 URL with ~10 minute expiry
    - Response is 302 redirect to pre-signed URL
    - download_count is incremented on each download
    - Purchasers can download any version of the purchased skill
  - Negative Tests (expected to FAIL):
    - Non-purchasers receive 403
    - Direct S3 URL access without pre-signed token is rejected
    - A version that has been archived for security reasons cannot be downloaded (even by purchasers)

- AC-6: Skill call endpoint works for prompt-based packages
  - Positive Tests (expected to PASS):
    - Skills with `prompts/` directory containing `.txt`/`.md` files can be called on-platform
    - Call reads prompt templates from the package's `prompts/system.txt` and `prompts/user_template.txt`
    - SkillCall record is created without amount_charged
    - Version pinning (SkillUsagePreference) still works
  - Negative Tests (expected to FAIL):
    - Calling a skill that has no `prompts/` directory returns 400 "This skill is download-only"
    - Calling a skill without a SkillPurchase returns 403
    - Scripts in `scripts/` directory are never executed server-side

- AC-7: Community reporting and quarantine work correctly
  - Positive Tests (expected to PASS):
    - Users can report a skill with a reason code (malicious_code, false_description, copyright, other)
    - One report per user per skill (idempotent)
    - When ~3 unique users report a skill, the version is auto-quarantined (hidden from marketplace, existing purchasers retain non-security access)
    - Quarantined skills are escalated to moderator queue
    - Moderators can: confirm archive, dismiss reports, or reinstate
    - Reporter eligibility: account age >= 7 days
  - Negative Tests (expected to FAIL):
    - Same user reporting the same skill twice creates only one report
    - Users with account age < 7 days cannot report
    - More than 5 reports per user per day are rate-limited
  - AC-7.1: Security-archived version handling
    - Positive: When a version is archived for security/policy reasons, its download is blocked for all users including existing purchasers; other versions of the same skill remain accessible
    - Negative: A security-archived version cannot be downloaded even with a valid SkillPurchase

- AC-8: Review eligibility supports dual execution model
  - Positive Tests (expected to PASS):
    - Users with a SkillCall record can leave a review (on-platform execution proof)
    - Users with a SkillPurchase and >= 7 days since purchase can leave a review (download-only proof)
  - Negative Tests (expected to FAIL):
    - Users without SkillPurchase cannot review
    - Users with SkillPurchase < 7 days old and no SkillCall cannot review

- AC-9: API endpoints are updated for the package model
  - Positive Tests (expected to PASS):
    - `POST /api/skills/` accepts multipart/form-data with ZIP file
    - `PATCH /api/skills/{id}` supports uploading a new version ZIP
    - `POST /api/skills/{id}/submit` triggers async scan pipeline
    - `POST /api/skills/{id}/purchase` handles FREE and PAID purchases
    - `GET /api/skills/{id}/download` serves pre-signed download URL
    - `GET /api/skills/purchased` lists user's purchased skills
    - `POST /api/skills/{id}/report` creates a report
    - `GET /api/skills/{id}` for paid skills shows metadata + readme_html but NOT package contents
    - Skill list API shows pricing info (FREE/PAID, price) per skill
  - Negative Tests (expected to FAIL):
    - Creating a skill without a ZIP file is rejected
    - Submitting a draft skill without a package is rejected

- AC-10: Frontend pages reflect the new package-based model
  - Positive Tests (expected to PASS):
    - CreateSkillPage has file upload area (drag-and-drop ZIP), pricing settings (FREE/PAID, price input), and SKILL.md preview
    - SkillDetailPage renders readme_html, shows package file tree, displays purchase/download buttons, and shows version history with changelogs
    - New "My Purchased Skills" page in profile with search and category filter
    - MySkillsPage shows download count and purchase-based income stats
    - Skill creation form auto-fills name/description from uploaded SKILL.md frontmatter
  - Negative Tests (expected to FAIL):
    - CreateSkillPage does not show system_prompt or user_prompt_template text areas
    - SkillDetailPage does not expose raw package contents for paid skills to non-purchasers

- AC-11: Database migration runs cleanly
  - Positive Tests (expected to PASS):
    - Migration adds new fields, creates new tables, modifies enums
    - Clean-slate migration (reset skill data) runs without errors
    - All existing tests pass after migration (or are updated)
  - Negative Tests (expected to FAIL):
    - Migration does not leave orphaned data or broken foreign keys

- AC-12: Admin interface supports the new model
  - Positive Tests (expected to PASS):
    - Django admin shows scan results for skills
    - Admin can view/manage the report queue
    - Admin can manually approve/reject/archive skills
    - Admin can look up purchases for a skill
  - Negative Tests (expected to FAIL):
    - Admin does not show obsolete fields (system_prompt, user_prompt_template)

## Path Boundaries

Path boundaries define the acceptable range of implementation quality and choices.

### Upper Bound (Maximum Acceptable Scope)

The implementation includes all 12 acceptance criteria with:
- Full async scan pipeline via Celery with comprehensive security checks (structure, content, script, metadata)
- Complete purchase/download flow with pre-signed URLs and private storage
- Trust-gated publishing with credit level checks
- Community reporting with anti-abuse controls (rate limits, age gates, moderator escalation)
- Version-scoped moderation with security-archive download blocking
- Dual review eligibility (SkillCall or 7-day purchase)
- Frontend with drag-drop upload, SKILL.md preview, file tree viewer, purchase flow, download buttons
- Admin interface with scan results, report queue, purchase lookup
- Full test coverage for all new services and API endpoints

### Lower Bound (Minimum Acceptable Scope)

The implementation includes core acceptance criteria (AC-1 through AC-5, AC-9, AC-11) with:
- Data model changes with migration
- Synchronous package validation (async scan deferred)
- Basic purchase/download flow
- API endpoints for create, submit, purchase, download
- Minimal frontend updates (file upload, basic detail page changes)
- Status set directly to APPROVED/REJECTED after validation (SCANNING state still exists but scan completes synchronously)

### Allowed Choices

- Can use: `python-frontmatter` or `PyYAML` for SKILL.md parsing; `bleach` or `nh3` for HTML sanitization; `markdown` or `markdown-it-py` for Markdown rendering; custom Django storage class or per-field `storage` kwarg for private S3 ACL
- Cannot use: external malware scanning services (VirusTotal, etc.); CLI publishing tools; GitHub/OAuth integration; package dependency resolution systems
- Fixed per draft: ZIP as the package format; SKILL.md as the required manifest file; YAML frontmatter format; S3/R2 as storage backend

## Feasibility Hints and Suggestions

> **Note**: This section is for reference and understanding only. These are conceptual suggestions, not prescriptive requirements.

### Conceptual Approach

```
1. Model Layer Changes:
   - Modify Skill: remove prompt fields, add package fields, change pricing_model enum, add SCANNING status
   - Modify SkillVersion: remove prompt fields, add package_file/sha256/changelog/status
   - New SkillPurchase model (skill, user, paid_amount, payment_type)
   - New SkillReport model (skill, reporter, reason, created_at)
   - Remove SkillCall.amount_charged

2. Package Processing Service:
   class PackageService:
       def validate_and_process(zip_file) -> PackageResult:
           # Unpack to temp dir
           # Validate structure (SKILL.md exists, file limits, no forbidden types)
           # Check archive safety (zip-slip, symlinks, zip-bomb)
           # Parse SKILL.md frontmatter
           # Render and sanitize readme_html
           # Compute SHA-256
           # Return metadata + validation result

3. Enhanced ModerationService:
   class ModerationService:
       def scan_package(skill_version_id):  # Celery task
           # Layer 1: Structure validation (from PackageService)
           # Layer 2: Content scanning (prompt injection, jailbreak, sensitive, script safety)
           # Layer 3: Metadata consistency (name match, SemVer check, version progression)
           # Update version status based on result

4. Purchase Service:
   class SkillPurchaseService:
       def purchase(user, skill, payment_type):
           # Idempotency check
           # Balance/eligibility check
           # Atomic: deduct balance, create SkillPurchase, create Transaction, calculate platform fee
           # Return purchase record

5. Download Service:
   def generate_download_url(user, skill, version=None):
       # Check SkillPurchase exists
       # Check version not security-archived
       # Generate pre-signed URL (10 min expiry)
       # Increment download_count
       # Return URL

6. Private Storage:
   class PrivateS3Storage(S3Boto3Storage):
       default_acl = 'private'
       querystring_auth = True  # Enable pre-signed URLs
```

### Relevant References

- `backend/apps/skills/models.py` - Current Skill, SkillVersion, SkillCall, SkillReview, SkillUsagePreference models
- `backend/apps/skills/services.py` - Current SkillService and ModerationService
- `backend/apps/skills/api.py` - Current API endpoints
- `backend/apps/skills/schemas.py` - Current Pydantic schemas
- `backend/apps/payments/services.py` - PaymentsService.charge_skill_call (reference for purchase logic)
- `backend/apps/payments/models.py` - Transaction model and TransactionType enum
- `backend/apps/credits/services.py` - CreditService.add_credit, calculate_level, get_discount_rate
- `backend/apps/accounts/models.py` - User model with balance, credit_score, level fields
- `backend/config/settings/base.py` - S3/storage configuration
- `backend/common/constants.py` - Price limits, platform fee rate
- `frontend/src/pages/marketplace/` - MarketplacePage, SkillDetailPage, CreateSkillPage, MySkillsPage
- `frontend/src/lib/skills.ts` - API client for skills
- `frontend/src/components/skill/SkillCard.tsx` - Skill card component

## Dependencies and Sequence

### Milestones

1. **Data Foundation**: Model changes and migration
   - Phase A: Modify Skill model (remove prompt fields, add package fields, update enums)
   - Phase B: Modify SkillVersion model (add package/status fields, remove prompt fields)
   - Phase C: Create SkillPurchase and SkillReport models
   - Phase D: Modify SkillCall (remove amount_charged)
   - Phase E: Generate and apply migration (clean-slate)

2. **Package Processing Pipeline**: Upload, validation, and storage
   - Phase A: Implement private S3 storage class
   - Phase B: Implement PackageService (ZIP validation, extraction, frontmatter parsing, README rendering)
   - Phase C: Implement async scan pipeline (Celery task wrapping ModerationService enhancements)
   - Phase D: Implement archive safety checks (zip-slip, symlinks, zip-bomb, MIME verification)

3. **Purchase and Download**: Entitlement and access control
   - Phase A: Implement SkillPurchaseService (purchase flow, idempotency, platform fee)
   - Phase B: Implement download endpoint with pre-signed URLs
   - Phase C: Implement trust-gated publishing logic

4. **API Layer**: Endpoint updates and new endpoints
   - Phase A: Update create/update endpoints for multipart/form-data
   - Phase B: Update submit endpoint for async scan
   - Phase C: Add purchase, download, purchased, report endpoints
   - Phase D: Update call endpoint (purchase check, prompt-from-package)
   - Phase E: Update schemas and list/detail responses

5. **Community Safety**: Reporting and moderation
   - Phase A: Implement report submission with anti-abuse controls
   - Phase B: Implement auto-quarantine logic
   - Phase C: Implement moderator review actions
   - Phase D: Implement security-archive version blocking

6. **Frontend**: UI updates
   - Phase A: Rework CreateSkillPage (file upload, frontmatter preview, pricing UI)
   - Phase B: Rework SkillDetailPage (README rendering, purchase/download, file tree)
   - Phase C: Add "My Purchased Skills" page
   - Phase D: Update MySkillsPage (download count, purchase income stats)
   - Phase E: Update API client types and hooks

7. **Admin and Testing**: Admin interface and comprehensive tests
   - Phase A: Update Django admin for new model
   - Phase B: Write unit tests for all new services
   - Phase C: Write API integration tests
   - Phase D: End-to-end flow verification

Dependencies:
- Milestone 2 depends on Milestone 1 (models must exist before package processing)
- Milestone 3 depends on Milestones 1 and 2 (purchase needs models; download needs package storage)
- Milestone 4 depends on Milestones 1, 2, and 3 (APIs wrap service layer)
- Milestone 5 depends on Milestone 1 (SkillReport model)
- Milestone 6 depends on Milestone 4 (frontend consumes API)
- Milestone 7 runs partially in parallel; tests can be written alongside each milestone

## Task Breakdown

Each task must include exactly one routing tag:
- `coding`: implemented by Claude
- `analyze`: executed via Codex (`/humanize:ask-codex`)

| Task ID | Description | Target AC | Tag (`coding`/`analyze`) | Depends On |
|---------|-------------|-----------|--------------------------|------------|
| task1 | Analyze current Skill model fields, relationships, and usages across the codebase to identify all references that need updating | AC-1 | analyze | - |
| task2 | Modify Skill model: remove prompt fields, add package fields, update pricing_model and status enums, rename price_per_use to price | AC-1 | coding | task1 |
| task3 | Modify SkillVersion model: remove prompt fields, add package_file/package_sha256/changelog/status fields | AC-1 | coding | task2 |
| task4 | Create SkillPurchase model with skill, user, paid_amount, payment_type fields and unique constraint | AC-1 | coding | task2 |
| task5 | Create SkillReport model with skill, reporter, reason, created_at fields | AC-1, AC-7 | coding | task2 |
| task6 | Modify SkillCall: remove amount_charged field | AC-1 | coding | task2 |
| task7 | Generate and apply database migration (clean-slate for skill data) | AC-11 | coding | task2, task3, task4, task5, task6 |
| task8 | Implement PrivateS3Storage class for package files with private ACL | AC-5 | coding | - |
| task9 | Implement PackageService: ZIP extraction, structure validation, archive safety checks, frontmatter parsing, README rendering and sanitization | AC-2 | coding | task7, task8 |
| task10 | Analyze existing ModerationService patterns and security scan rules to design enhanced package scanning | AC-3 | analyze | task9 |
| task11 | Implement enhanced ModerationService: content safety scanning for packages (prompt injection, script safety, metadata consistency) | AC-3 | coding | task9, task10 |
| task12 | Implement async scan Celery task wrapping the scan pipeline, with SCANNING status transitions | AC-3 | coding | task11 |
| task13 | Implement trust-gated publishing: credit level check for instant vs queued publishing | AC-3.1 | coding | task12 |
| task14 | Implement SkillPurchaseService: purchase flow with idempotency, balance check, platform fee, transaction creation | AC-4 | coding | task7 |
| task15 | Implement download endpoint: entitlement check, pre-signed URL generation, download_count increment, security-archive blocking | AC-5 | coding | task8, task14 |
| task16 | Update Skill create/update API endpoints for multipart/form-data with ZIP upload | AC-9 | coding | task9 |
| task17 | Update submit API endpoint to trigger async scan pipeline | AC-9 | coding | task12 |
| task18 | Implement purchase API endpoint | AC-9 | coding | task14 |
| task19 | Implement download API endpoint | AC-9 | coding | task15 |
| task20 | Implement purchased list API endpoint | AC-9 | coding | task14 |
| task21 | Implement report API endpoint with anti-abuse controls | AC-7, AC-9 | coding | task5 |
| task22 | Update call API endpoint: purchase check, read prompts from package, download-only detection | AC-6 | coding | task9, task14 |
| task23 | Update review eligibility logic: SkillCall OR 7-day SkillPurchase | AC-8 | coding | task14 |
| task24 | Implement auto-quarantine logic: threshold reports trigger hide + moderator escalation | AC-7 | coding | task21 |
| task25 | Implement moderator actions: confirm archive, dismiss, reinstate | AC-7 | coding | task24 |
| task26 | Implement security-archive version blocking for downloads | AC-7.1 | coding | task15, task25 |
| task27 | Update Skill API schemas (input/output) for new fields, remove obsolete fields | AC-9 | coding | task16 |
| task28 | Update skill list/detail API responses: hide package contents for paid skills, show readme_html | AC-9 | coding | task27 |
| task29 | Analyze frontend component structure and API client to plan UI update approach | AC-10 | analyze | task27 |
| task30 | Update frontend API client types and functions for new endpoints | AC-10 | coding | task27, task29 |
| task31 | Rework CreateSkillPage: file upload (drag-drop ZIP), frontmatter auto-fill, pricing settings, SKILL.md preview | AC-10 | coding | task30 |
| task32 | Rework SkillDetailPage: README rendering, purchase/download buttons, file tree, version history with changelog | AC-10 | coding | task30 |
| task33 | Create "My Purchased Skills" page with search and category filter | AC-10 | coding | task30 |
| task34 | Update MySkillsPage: download count, purchase-based income stats | AC-10 | coding | task30 |
| task35 | Update Django admin for new Skill model fields, scan results, report queue, purchase lookup | AC-12 | coding | task7 |
| task36 | Write unit tests for PackageService | AC-2 | coding | task9 |
| task37 | Write unit tests for enhanced ModerationService | AC-3 | coding | task11 |
| task38 | Write unit tests for SkillPurchaseService | AC-4 | coding | task14 |
| task39 | Write API integration tests for all new and modified endpoints | AC-9 | coding | task16-task28 |
| task40 | Update common/constants.py: price limits ($0.01-$10.00), add package size constants | AC-1 | coding | task2 |

## Claude-Codex Deliberation

### Agreements

- **Credit point payment should be dropped**: Both agree that `credit_score` is reputation, not spendable currency. The existing system has no transfer ledger, and making credits spendable would break level-based permissions, discount rates, and trust thresholds. Payment remains $ balance only.
- **Async scanning is necessary**: Package scanning (unpack, hash, validate, run security checks) is not instant. A SCANNING state and Celery-based async pipeline is needed.
- **One-time purchase model is correct**: For downloadable packages, per-use billing doesn't make sense. Buy once, own permanently.
- **Keep SkillCall for analytics**: Execution logs are still needed for trending, analytics, and on-platform review gating. Just remove billing fields.
- **Clean-slate migration**: Project is in dev stage with seed data only. Fresh migration is safest.
- **README HTML sanitization is mandatory**: readme_html is a stored XSS surface and must be sanitized (bleach/nh3).
- **Private storage for packages**: Package files need private ACL with pre-signed URL delivery, overriding the global `public-read` default.
- **Admin tooling is necessary**: Scan results, report queue, moderation actions, and purchase lookup are essential.
- **Archive safety controls**: Zip-slip, symlink rejection, zip-bomb detection, MIME verification, file count/size caps are all needed.

### Resolved Disagreements

- **Status lifecycle (PENDING_REVIEW)**: Codex wanted to restore `PENDING_REVIEW` for safety. Claude argued the draft explicitly removes it. **Resolution**: Remove `PENDING_REVIEW` per draft, but add trust-gated publishing (DEC-7 user decision): trusted users get instant publish after scan, new users go through admin review. This addresses Codex's safety concern without contradicting the draft's intent.

- **Review eligibility for download-only users**: Codex argued SkillCall-only proof is insufficient for off-platform use. **Resolution**: Dual eligibility - SkillCall record OR SkillPurchase with >= 7 days since purchase.

- **On-platform execution scope**: Codex argued arbitrary code execution is unsafe. **Resolution**: Platform only executes declarative prompt files from `prompts/` directory. Scripts in `scripts/` are download-only. Skills without `prompts/` return 400 on call.

- **Community reporting threshold**: Codex argued 3 reports is too easy to brigade. **Resolution**: 3 reports triggers auto-quarantine (hide from marketplace) + escalation to moderator queue, not immediate archive. Anti-abuse controls added (account age gate, rate limits, one-report-per-user-per-skill).

- **Paid package content leakage**: Codex identified that current APIs expose prompt contents publicly. **Resolution**: Paid skill detail/list APIs show only metadata + readme_html. Package download requires SkillPurchase.

- **Version-scoped moderation**: Codex required status/quarantine/archive decisions to attach to specific versions. **Resolution**: Added `status` field to SkillVersion. Security-archived versions block downloads individually.

### Convergence Status

- Final Status: `converged`
- Rounds: 2
- All REQUIRED_CHANGES addressed. Remaining disagreements (manual review removal) resolved via user decisions.

## Pending User Decisions

- DEC-1: Manual review removal
  - Claude Position: Remove per draft intent. Automated scanning + community reporting + trust-gated publishing is sufficient.
  - Codex Position: Downloadable code packages need human review. Auto-scan is only a prefilter.
  - Tradeoff Summary: Removing speeds up publishing but increases risk. Keeping adds latency but provides safety.
  - Decision Status: `Remove manual review (per draft)` - User chose to follow draft, augmented with trust-gated publishing (DEC-7)

- DEC-2: Version entitlement model
  - Claude Position: All future versions (per draft: "购买后永久可用...可下载所有版本")
  - Codex Position: Consider major-version repurchase using existing `is_major` concept
  - Tradeoff Summary: All-versions is simpler but eliminates paid major upgrades.
  - Decision Status: `All future versions` - User confirmed

- DEC-3: Price ceiling
  - Claude Position: Accept draft's $50.00 for one-time purchase
  - Codex Position: Keep current $10.00 cap
  - Tradeoff Summary: Higher ceiling justified by one-time model but risks price gouging on early platform.
  - Decision Status: `$10.00 (current cap)` - User chose conservative option

- DEC-6: Buyer handling when paid version is security-archived
  - Claude Position: Block affected version download, keep other versions accessible
  - Codex Position: Need explicit policy
  - Tradeoff Summary: Blocking the specific version balances security with buyer rights. No refund keeps implementation simple.
  - Decision Status: `Block affected version, keep others` - User confirmed

- DEC-7: Instant publish eligibility
  - Claude Position: All users (per draft)
  - Codex Position: Only verified/trusted publishers
  - Tradeoff Summary: Restriction reduces malicious package risk but adds friction for new users.
  - Decision Status: `Only trusted users (credit level >= Craftsman) can instant-publish; new users require admin review` - User chose trust-gated approach

## Implementation Notes

### Code Style Requirements
- Implementation code and comments must NOT contain plan-specific terminology such as "AC-", "Milestone", "Step", "Phase", or similar workflow markers
- These terms are for plan documentation only, not for the resulting codebase
- Use descriptive, domain-appropriate naming in code instead

### Key Design Decisions Summary

1. **Payment**: $ balance only. Credit point payment dropped (credits are reputation, not currency).
2. **Status flow**: DRAFT -> SCANNING -> APPROVED/REJECTED/ARCHIVED (no PENDING_REVIEW).
3. **Trust gate**: Credit level >= Craftsman (100 points) for instant publish; lower levels need admin review.
4. **Execution**: Platform only executes declarative prompts from `prompts/` dir. Scripts are download-only.
5. **Pricing**: FREE or PAID ($0.01-$10.00). One-time purchase, all future versions included.
6. **Reporting**: 3 reports -> auto-quarantine + moderator escalation. Anti-abuse: age gate, rate limit.
7. **Security archive**: Blocks download of affected version only. Other versions remain accessible. No refund.
8. **Storage**: Private ACL for packages. Pre-signed URLs for downloads (~10 min expiry).
9. **Migration**: Clean-slate (reset skill data). Dev stage, no real user data to preserve.

### Draft Deviations

The following changes were made compared to the original draft based on Claude-Codex deliberation and user decisions:

| Draft Specification | Plan Decision | Reason |
|---|---|---|
| Payment: $ balance OR credit points | $ balance only | Credit points are reputation, not currency. No transfer ledger exists. |
| Price range: $0.01-$50.00 | $0.01-$10.00 | User chose to keep current conservative cap |
| Status: no SCANNING state | Added SCANNING state | Package scanning is async (Celery), needs intermediate state |
| All users can instant-publish | Trust-gated publishing | User chose: only Craftsman+ level can instant-publish |
| 3 reports -> auto-archive | 3 reports -> auto-quarantine + moderator escalation | Codex identified brigading risk; softened to quarantine |
| SkillPurchase.paid_credit field | Removed | Credit payment dropped entirely |
| SkillPurchase.payment_type: MONEY/CREDIT/FREE | MONEY/FREE only | Credit payment dropped |
| Skill.payment_accept: MONEY/CREDIT/BOTH | Removed | Credit payment dropped; only $ balance accepted |

### Quantitative Metrics (Optimization Targets, Not Hard Requirements)

All numeric thresholds are optimization directions per user confirmation:
- ZIP max size: ~10 MB
- Per-file max: ~2 MB
- File count cap: ~50
- Price range: $0.01-$10.00
- Download link expiry: ~10 minutes
- Report quarantine threshold: ~3 unique reporters
- Review wait period (download-only): ~7 days after purchase

--- Original Design Draft Start ---

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

--- Original Design Draft End ---
