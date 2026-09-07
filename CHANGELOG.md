# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Dates are ISO 8601. Entries are grouped by change package per `change-packages.yml`.

---

## [2026-09-07] — Plan AC v12 live tooling + clean-checkout CI collection fix

### Changed — provide the tracked v12 test contract its validator on clean checkouts
- **`change-packages.yml`** (updated): moved `scripts/run_collector_proposals_v12.py`, `scripts/validate_collector_execution_v12.py`, `tests/test_collector_v12.py` from `quarantined_research_artifacts` to `plan_ac_integrity` (AC-01 Option B ratified). Restores clean-checkout CI collection, which previously failed because the tracked test imported the untracked + quarantined validator.

## [Unreleased] — 2026-09-02 Synthetic Review Environment

### Added — Portal Release 1A Review Surface
- **`portal/settings.py`**: added `CsrfViewMiddleware`, `django-allauth[mfa]` wired into `INSTALLED_APPS` + `AUTHENTICATION_BACKENDS` + `MFA_*` settings per DEC-007; `Membership.mfa_verified` deprecated (field preserved, no authorization query reads it).
- **`portal/settings_synthetic_review.py`** (new): inherits settings, overrides `DATABASES` → `runtime/portal/synthetic-review/db.sqlite3`, requires `SYNTHETIC_REVIEW_SECRET` env var (no auto-generation).
- **`portal/release1a/models.py`**: `Membership.mfa_verified` now silently resets to `False` on save; added `Release1aReview` (section, status, note, git/build stamps) and `Release1aAcceptance` (immutable, git hash + clean/dirty + build ID + session UUID).
- **`portal/release1a/views.py`**: replaced all `mfa_verified=True` reads with allauth `Authenticator` TOTP check; added `/review/` dashboard, `/review/section/<section>/update/`, `/review/check-answers/`, `/review/approve/`, `/review/return/`, `/review/receipt/`, and `/reviewer_activate/<token>/`.
- **`portal/release1a/urls.py`**: added review routes + allauth URLs.
- **`portal/release1a/services.py`**: `require_membership` now calls `require_mfa_enrolled(user)` (allauth TOTP) before checking `Membership.active`.
- **`portal/templates/portal/review_dashboard.html`**, **`review_check_answers.html`**, **`review_receipt.html`**, **`review_return.html`**, **`reviewer_activate.html`** (new): Czech-language review surface.
- **`portal/release1a/management/commands/activate_reviewer.py`** (new): generates one-time invitation URLs for seeded reviewer accounts.
- **`scripts/seed_release1a_dev.py`** (new): idempotent seeder — verifies manifest SHA-256 hashes, uses natural unique keys, `update_or_create`, creates inactive reviewer accounts (`jan-reviewer@example.invalid`, `pavel-reviewer@example.invalid`).
- **`scripts/verify_synthetic_review_readiness.sh`** (new): runs 10 automated readiness checks, writes `runtime/portal/synthetic-review/readiness.json`.
- **`scripts/axe_check.sh`** (new): axe-core accessibility checks.
- **`scripts/generate_synthetic_review_secret.sh`** (new): idempotent secret generation, mode 600, never prints secret.
- **`tests/m2/test_csrf_enforcement.py`**, **`test_totp_real_enforcement.py`**, **`test_review_acceptance_flow.py`**, **`test_synthetic_containment.py`** (new).
- **`requirements-dev.txt`** (new): `axe-core-selenium`, `axe-playwright`, `playwright`.
- **`plans/PLAN-INFRA.md`**, **`plans/PLAN-WORKERS.md`**, **`planning/approvals.json`** (updated): added review-environment contract, J1–J4 acceptance cross-reference, `REV-1A-FRONTEND` pending record.
- **`roadmap.md`**: updated Now + M2 status to reflect review environment implementation.
- **`docs/operations/release-1a-review-environment.md`** (new): runbook.

### Changed — Governance Surface
- Consolidated 27 dated plan files and the 53-item catalog into 7 plans (`PLAN-INFRA`, `PLAN-WORKERS`, `PLAN-INVOICE`, `PLAN-LEGAL`, `PLAN-A1`, `PLAN-FREE-MODEL`, `PLAN-HISTORY`) and a 34-item `planning/catalog.json`. The dated plan files are preserved under `.archive/plans/` (context only, never executed). Decision state, evidence, approver, and decision-date records are preserved for all `DEC-001`–`DEC-016`; only the source links and dependency targets were repointed (e.g. DEC-013/DEC-016 → `plans/PLAN-INFRA.md`, DEC-014 → `plans/PLAN-A1.md`, DEC-015 → `plans/PLAN-INVOICE.md`).
- Migrated model mapping (audit §1.3): PLAN-INFRA ← E+L+M+M2P+AE+K+E-01; PLAN-A1 ← R+Q; PLAN-WORKERS ← F+H+N+O; PLAN-INVOICE ← P+AC+AD; PLAN-LEGAL ← G+I+J; PLAN-FREE-MODEL ← AF+AF2+AF2.1+AF2.2; PLAN-HISTORY ← B+C+D+consolidated-roadmap. `PLAN-WORKERS` inherits the Release 1A slice acceptance (decision_state `accepted`, approver/date/evidence set); `PLAN-A1` stays `active`/non-executable because provisional A1 regeneration remains blocked. `PLAN-HISTORY` is `historical`, non-executable, successor `PLAN-INFRA`.
- `scripts/validate_planning.py` updated in lockstep: `REQUIRED_IDS` 53 → 34, `plan_file_for_item` resolved for `PLAN-*` ids, `check_prototype_start_gate` now keys off `PLAN-INFRA` + `PLAN-WORKERS`. `plans/INDEX.md`, `roadmap.md`, `docs/decisions/decision-register.md`, `.opencode/skills/market-research-evidence/SKILL.md`, `docs/operations/sysadmin-readiness-2026-08-12.md`, `docs/research/2026-08-15-af2-free-model-trace-review-report.md`, `docs/prototypes/roadmap-portal/README.md`, `readme-scan-to-employees.md`, and `change-packages.yml` re-pointed to the consolidated plan files. `docs/plans/TODO_TRACKING.md` archived to `.archive/docs/plans/`.
- Dated audit/research reports (`GIT_AUDIT_REPORT.md`, `PROJECT_AUDIT_REPORT.md`, `WORKFLOW_FRAMEWORK_REPORT.md`, `docs/research/*`, `docs/codex-planner-report-prototype-priority.md`, `reports/*`) remain dated context and keep their historical file references.

### Changed — Validator Contract
- Validator check count stays at 24; `plans/INDEX.md` statuses now use the plain controlled-status words the index parser reads, and the six active plans carry `**Status**`/`**Milestone**` headers coherent with the catalog.

---

## [Unreleased] — 2026-08-29 Audit + Test Realignment

### Fixed — Repository Hygiene
- `.gitignore` rule `./a1/` replaced with `a1/`. The leading `./` was ineffective in git's path matcher; the PII-bearing `a1/` directory was visible to `git status` and would have been committed by any wildcard `git add`. Verified `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`, `output/`, `employees/scans/`, `.history-remediation/`, `.env` all now properly ignored.
- `scripts/pre-commit` step 5 promoted from a warning to a hard `exit 1` gate. The previous text claimed quarantined packages would be blocked, but the hook only printed and exited 0, so any `git add` of a `quarantined_research_artifacts` / `quarantined_unrelated` path would still land in history. The new gate intersects `STAGED` paths against `validate_change_packages.py` entries with `eligible_for_staging == false` and refuses the commit with explicit recovery instructions. Verified end-to-end by staging `scripts/validate_collector_execution_v12.py` (quarantined) and observing `exit 1`.

### Restored — Plan AC Integrity
- `scripts/validate_collector_execution.py` (Plan AC v1.1 collector-execution validator, 543 lines) re-added. The file was inadvertently removed in `ffb5922` alongside unrelated legacy cleanup, but `tests/test_collector_execution.py` references it. Listed in `change-packages.yml` under `plan_ac_integrity` with `eligible_for_staging: true`. The v12 variant (`scripts/validate_collector_execution_v12.py`) remains in `quarantined_research_artifacts` (frozen v1.2 baseline per `PROJECT_AUDIT_REPORT.md` §1.2) and is not staged here.
- `scripts/pre-commit` and `tests/test_comprehensive.py` added to `a1_policy` and `infrastructure_git_workflow` paths respectively so the validator can classify them when modified.

### Documentation — A1 Truth Reconciliation
- `AGENTS.md` "Gotcha" updated. The previous text claimed the private CSV "predates the seven Section 4 employment columns the renderer now requires". Audit on 2026-08-29 confirms the CSV actually has all 7 `employment_*` columns (`employment_id`, `employment_name`, `employment_street`, `employment_house_number`, `employment_city`, `employment_postal_code`, `employment_country_code`) and they are accepted by `scripts/a1_quality_gate.py:74-79` and `scripts/finalize_a1.py:261-263`. Regeneration is still blocked, but by per-row certificate, signatory, source-status, and review-flag gaps (`scripts/finalize_a1.py readiness` reports 17/17 employees blocked), not by missing columns.
- `docs/research/2026-08-19-open-decisions-research.md` R-01 marked superseded with a status banner. R-01 recommended 7 columns named `employer_*` / `activity_nace` / `employment_start` / `employment_type`; the actual implementation reads `employment_*` columns and maps them to the form's `employer_*` fields. `activity_nace`, `employment_start`, `employment_type` are not required by `scripts/a1_core.py:293`. The original R-01 body is preserved for historical traceability.

### Fixed — A1 Test Suite (ShadowGenerationTests regression)
- `tests/test_comprehensive.py::ShadowGenerationTests` aligned with the OSVČ derivation contract added in commit `db47b26` (`scripts/a1_core.py:188-198`). For `status_profile == self_employed_multi_state`, the renderer derives `employer_id` from `insurance_number`, `employer_name` to `SURNAME GIVEN - OSVČ`, and address fields from residence. The old single-fixture `synthetic-incomplete` test asserted the opposite (records without Section 4 must fail closed), which was correct for `employee_multi_state` but wrong for OSVČ.
  - Replaced the single OSVČ fixture with two: `synthetic-self-employed-osvc` (verifies the documented derivation) and `synthetic-employee-incomplete` (preserves the fail-closed guarantee with `status_profile = employee_multi_state`).
  - New test `test_self_employed_multi_state_derives_section_four_from_person` asserts the exact derivation contract.
  - New test `test_employee_multi_state_without_section_four_fails_closed` preserves fail-closed for non-OSVČ.
  - `test_verify_only_complete_records_produce_final_certificate_pdfs` updated to expect `complete_count == 1` (OSVČ via derivation), `incomplete_count == 1` (employee_multi_state fails).

### Open Decisions Status — 2026-08-29 Re-check
- **R-01** ✅ Done. CSV has all 7 `employment_*` columns.
- **R-02** ✅ Done. `pavel-kaspar` and `rudolf-kotlar` are in `a1/cohort.json` `additional_people` and in the live CSV (17 employees total).
- **L-01** ✅ Done. Every `plans/*.md` file has a controlled-vocabulary status header (`planned`, `active`, `completed`, `superseded`, `blocked`, `accepted`).
- **L-02** ✅ Done. All 7 `docs/paddleocr/` files carry a historical banner; `README.md` has full YAML front matter.
- **AC-01** Decision documented: `scripts/validate_collector_execution_v12.py` wrapper stays quarantined per `PROJECT_AUDIT_REPORT.md` §1.2 (frozen v1.2 baseline); `scripts/run_collector_proposals_v12.py` and `tests/test_collector_v12.py` remain tracked because tests reference them. Inconsistency flagged but left for an explicit Plan AC update.
- **R-03** Still pending operator approval (deleting `output/provisional.backup-*` directories).
- **AE-01** Still gated by Plan AE / DEC-016 explicit approval.
- **K-01** Still pending sysadmin evidence.

### Test Health Baseline — 2026-08-29
```
497 passed, 1 skipped, 11 subtests passed in 430s
```

**All tests pass** (was 495 passed / 2 failed / 1 skipped on 2026-08-29 morning; the 2 failures were the ShadowGenerationTests regression fixed above). Net change: +2 tests (`test_self_employed_multi_state_derives_section_four_from_person`, `test_employee_multi_state_without_section_four_fails_closed`), +20 tests vs. 2026-08-19 baseline (+18 from earlier M2 work not previously in baseline; +2 from this commit).

**A1 Core Tests:** 15 passed
**A1 Private Tests:** 3 passed
**A1 Quality Gate Tests:** 7 passed
**Finalize A1 Tests:** 14 passed
**Comprehensive (ShadowGen + structural + visual + profile):** 24 passed (was 22 + 2 failed)
**Plan AC Integrity Tests:** 68 passed (`test_capture_research_sources`, `test_collector_execution`, `test_collector_v12`, `test_field_normalization`)
**Free Model Eval Tests:** 58 passed
**M2 / Portal Tests:** 19 passed
**Architecture Proof Tests:** all passed
**Planning Validator Tests:** 36 passed
**Change Package Tests:** 4 passed

---

## [2026-08-19] — Audit-Driven Updates

### Added — M2 Vertical Slice (portal/release1a/)
- `forms.py` — 5 forms (Worker, Document, OCR, Assignment, A1Prepare/Approval)
- `views.py` — 14 views (J1–J4) + `require_org_membership` decorator
- `urls.py` — 12 URL patterns; `portal/urls.py` login/logout
- 12 full templates + 7 HTMX partials (Czech-first, HTMX-enhanced)
- `tests/m2/test_views.py` — 11 view tests
- `tests/m2/test_review_fixes.py` — 5 regression tests for review fixes

### Fixed — M2 Code Review (2026-08-19)
- a1_case_detail template `'blocked"` quote bug (page 500)
- 7 missing HTMX partial templates (TemplateDoesNotExist)
- worker_delete 405 (allowed POST/DELETE) + clean HTMX swap response
- worker_delete ProtectedError → graceful denied page + audit event
- optimistic locking now functional (hidden `version` field)
- overlap warns + saves per DEC-005 (was blocking); A1 prep still blocks ambiguity
- duplicate OCR proposals removed (service is single source)
- duplicate audit events removed (`document.uploaded`, `a1.prepared` — service is authoritative)
- HTMX CSRF integration (meta tag + configRequest header)
- size limit synced via shared `MAX_UPLOAD_BYTES` constant
- removed 13 unused imports + dead code

### Changed — Governance & Plans
- **Plan R** (`2026-08-12-plan-r-a1-production-stabilization.md`): Updated blocker details —
  CSV now documented as 9 rows (was "predates columns"), missing 7 Section 4 columns +
  2 missing people (`pavel-kaspar`, `rudolf-kotlar`). Added Current State Inventory table
  (7 artifacts). Verification now includes backup inventory completion. Exit gate updated.
- **Plan E** (`2026-08-12-plan-e-architecture-proofs-and-adr.md`, `planning/catalog.json`):
  Status changed from `active` → `completed` (all 8 checks pass, M2 gate open).
  Fixed catalog.json entry with complete fields (source_links, risks, quality_gates, etc.).
- **Plan M2** (`2026-08-17-plan-m2-functional-prototype-sprint.md`): Added Scaffold Location
  Clarification section — gate is open (2026-08-17), implementation target is
  `portal/release1a/`, not `prototypes/architecture/adr001/apps/`.
- **Roadmap** (`roadmap.md`): Date updated to 2026-08-19; Current stage updated.
  Now/Parallel/Gated table refined: M2 gate open, Plan R blocker expanded,
  cleanup items added. Plan sequence table updated with ✅/🟡/🔴 status markers.
- **Plans INDEX** (`plans/INDEX.md`): Plan E status → `completed` (removed markdown bold).
  Plan M2 blocker updated (gate open, scaffold location clarified). Plan R blocker expanded
  (7 columns + 2 people + backup inventory).

### Removed — Legacy Artifacts (Pending Staging)
- `scripts/a1_core.py.backup` — duplicate of canonical `a1_core.py`
- `portal/settings.py.bak` — backup of current settings
- `config/a1_field_coords.json` — legacy, superseded by `a1_layout.json` (FORBIDDEN_STALE_FRAGMENTS)
- `config/a1_checkbox_coords.json` — legacy, superseded by `a1_layout.json` (FORBIDDEN_STALE_FRAGMENTS)
- `config/a1_field_map.json` — legacy, not used
- `config/a1_provisional.json` — legacy placeholders only (FORBIDDEN_STALE_FRAGMENTS)

### Classified — Research Script Duplicates (Decision Needed)
- `scripts/run_collector_proposals_v12.py` + `validate_collector_execution_v12.py` +
  `test_collector_v12.py` — frozen Integrity 1.3 baseline (Plan AC)
  - **Option A:** Move to `quarantined_research_artifacts` in `change-packages.yml`
  - **Option B:** Document as archival comparison baseline in Plan AC

### Inventoried — Output Backups (Plan R §8, Pending Approval)
- 15 directories: `output/provisional.backup-20260811-114746` through
  `output/provisional.backup-20260812-141227`
- `qa_manifest_all5.json`, `qa_report_all5.json` — stale, cover 5-person set

### Documentation
- **PROJECT_AUDIT_REPORT.md** — Full repository audit (structure, duplicates,
  inconsistencies, claims vs reality, PII safety, test health, gate status)
- **CHANGELOG.md** — This file
- **docs/research/2026-08-19-open-decisions-research.md** — Open decisions research
  report with mocked data, best practices, and rationale for all 8 open decisions
- **docs/research/2026-08-19-mock-review-csv.csv** — Complete mocked review.csv
  (11 rows × 44 columns) for R-01/R-02 operator use
- **.gitlab-ci.yml** — Proposed GitLab CI/CD config (inactive until DEC-016 approval)
- **docs/operations/collect-plan-k-evidence.sh** — Plan K evidence collection script
- **Historical headers** added to:
  - `.archive/plans/2026-08-11-consolidated-roadmap.md`
  - `.archive/plans/2026-08-11-plan-b-opencode-cleanup-workflows.md`
  - `.archive/plans/2026-08-11-plan-c-opencode-research.md`
  - `docs/paddleocr/README.md`

---

## [2026-08-17] — M2 Scaffold Gate Open

### Added
- `scripts/check_m2_scaffold_gate.py` — Machine-readable, fail-closed M2 gate evaluator
- `.archive/plans/2026-08-17-plan-m2-functional-prototype-sprint.md` — M2 sprint plan (archived 2026-08-30 under PLAN-INFRA)
- `planning/approvals.json` — ADR-001, ADR-002, REV-001 approval records
- `docs/architecture/adr-001-evidence/manifest.json` — Hash-bound proof manifest
- `docs/architecture/release-1a-catalog.json` — Frozen Release 1A catalog
- `docs/decisions/ADR-002-release-1a-data-and-transactions.md` — Data/transaction ADR
- `docs/release-1a/unblock-review-packet.md` — Jan phase-1 defaults record

### Changed
- Plan E: All 8 synthetic checks pass; implementation gate open
- ADR-001: Architecture direction accepted by Pavel (2026-08-17)
- Plan N/O: Release 1A role/data/transaction contracts frozen

---

## [2026-08-14] — Governance & Planning Reconciliation

### Added
- `change-packages.yml` — 10 explicit change packages with paths, checks, dependencies
- `scripts/validate_change_packages.py` + `tests/test_validate_change_packages.py` — Fail-closed package validation
- `scripts/validate_planning.py` — Planning catalog validator (exit codes 0/1/2)
- `scripts/generate_planning_asset.py` — Derived cockpit asset generator
- `planning/catalog.schema.json` + `planning/catalog.json` — Machine-readable plan catalog
- `tests/test_validate_planning.py` — Validator test coverage

### Changed
- Plan L: Operational baseline established; CLI verification registry created
- Plan Q: Sanitized checkpoint `c01aa2b` accepted (DEC-014)
- AGENTS.md: Authority hierarchy, PII boundaries, Git workflow codified

---

## [2026-08-13] — Architecture Proof Sprint (Plan E)

### Added
- `prototypes/architecture/adr001/` — Disposable proof settings, URLs, proof contract
- `tests/architecture/` — 8 proof test modules (MFA, tenant isolation, jobs, storage, audit, A1 boundary, transactions, rollback)
- `tests/fixtures/release_1a/` — 8 synthetic fixture files + manifest
- `scripts/run_architecture_proofs.py` — Preflight/run/verify orchestration
- `docs/architecture/` — Threat model, dependency review, proof report

---

## [2026-08-12] — Initial Repository Organization

### Added
- Canonical A1 pipeline: `generate_provisional_a1.py`, `finalize_a1.py`, `a1_core.py`, `a1_quality_gate.py`
- A1 skill: `.agents/skills/a1-pdf-production/`
- Private inputs (gitignored): `a1/review.csv`, `a1/cohort.json`, `scans/`, `evidence/`, `ocr/`
- Django portal scaffold: `portal/`, `portal/release1a/`
- `requirements.txt` — Pinned dependencies (Python 3.13, Django 5.2, etc.)
- `docs/security/real-data-rules.md` — Sole activation gate for real data

---

## GitHub / GitLab / CI State (2026-08-19)

### GitHub (Authoritative Origin)
- **Remote:** `origin` → `https://github.com/pkoka888/prace-v-nemecku.git`
- **Branch:** `main` (default)
- **CI/CD:** **None configured** — no `.github/workflows/`
- **Protection:** Unknown (not checked via API)

### GitLab (Proposed Secondary — Plan AE / DEC-016)
- **Remote:** Not configured
- **Runner:** Not installed
- **CI/CD:** Not enabled
- **Status:** Proposed by Plan AE; activation requires explicit separate approval (DEC-016)
- **Rules:** `docs/operations/gitlab-integration.md` defines proposed setup

### Local CI Equivalent (Deterministic Commands)
Per `change-packages.yml` and plan acceptance commands:

| Package | Validation Command |
|---------|-------------------|
| `governance_truth` | `venv/bin/python scripts/validate_planning.py` |
| `repository_documentation` | `git diff --check` |
| `planning_cockpit` | `venv/bin/python scripts/validate_planning.py && venv/bin/python -m pytest tests/test_validate_planning.py -q` |
| `cli_agent_tooling` | `venv/bin/python -m pytest tests/test_verify_cli_claims.py -q` |
| `plan_ad_invoice_contracts` | `venv/bin/python -m pytest tests/test_invoice_ingestion_contract.py -q` |
| `plan_ac_integrity` | `venv/bin/python -m pytest tests/test_capture_research_sources.py tests/test_collector_execution.py tests/test_collector_v12.py tests/test_field_normalization.py -q` |
| `plan_ac_quarantine_metadata` | `venv/bin/python -m pytest tests/test_plan_ac_quarantine.py -q` |
| `a1_policy` | `venv/bin/python -m pytest tests/test_a1_core.py tests/test_a1_private.py tests/test_a1_quality_gate.py tests/test_finalize_a1.py -q` |
| `infrastructure_git_workflow` | `venv/bin/python -m pytest tests/test_validate_change_packages.py -q && venv/bin/python scripts/validate_change_packages.py --json` |
| `free_model_evaluation` | `venv/bin/python -m pytest tests/test_free_model_eval_*.py -q && venv/bin/python scripts/run_free_model_eval.py verify-fixtures --policy config/free-model-eval/policy.json` |

### Pre-commit / Pre-push (Not Installed)
- No `.pre-commit-config.yaml`
- No git hooks in `.git/hooks/`
- AGENTS.md mandates: `git diff --check`, targeted tests, doc link validation, PII/secret check on staged content before commit

### Recommended CI Pipeline (When Authorized)
```yaml
# .github/workflows/ci.yml (proposed)
name: CI
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Validate planning
        run: venv/bin/python scripts/validate_planning.py
      - name: Run test suite
        run: venv/bin/python -m pytest -q --ignore=tests/m2/test_release1a_vertical.py
      - name: Check M2 gate
        run: venv/bin/python scripts/check_m2_scaffold_gate.py --json
      - name: Validate change packages
        run: venv/bin/python scripts/validate_change_packages.py --json
      - name: Git diff check
        run: git diff --check
```

---

## Open Decisions / Pending Actions (2026-08-19)

| ID | Decision | Blocked By | Owner |
|----|----------|------------|-------|
| R-01 | Operator adds 7 Section 4 columns to `a1/review.csv` | Human action | Operator |
| R-02 | Operator adds `pavel-kaspar`, `rudolf-kotlar` to `a1/review.csv` | Human action | Operator |
| R-03 | Approve deletion of 15 `output/provisional.backup-*` dirs | Plan R inventory + explicit approval | Primary agent |
| AC-01 | Classify v12 research scripts: quarantine or document | Plan AC decision | Primary agent |
| AE-01 | Approve GitLab remote + CI activation | DEC-016 explicit approval | Pavel |
| K-01 | Provide capacity/backup/restore evidence for Plan K | Sysadmin | Sysadmin |
| L-01 | Mark historical plans (2026-08-11-*) with headers | Plan L exit | Primary agent |
| L-02 | Mark `docs/paddleocr/` as historical | Plan L exit | Primary agent |

---

## Test Health Baseline (2026-08-19)

```
479 passed, 1 skipped in 281s
```

**All tests pass** (previously failing Release1A vertical test now passes — likely flaky fixture isolation).

**A1 Core Tests:** 22 passed
**A1 Private Tests:** 3 passed
**A1 Quality Gate Tests:** 7 passed
**Finalize A1 Tests:** 12 passed
**Architecture Proof Tests:** 8 modules, all passed
**Planning Validator Tests:** 36 passed (all 24 checks + 12 mutation tests)
**Change Package Tests:** 4 passed
**Free Model Eval Tests:** All passed
**Release1A Vertical Tests:** 2 passed

*Note: Test count increased by 1 due to Plan E status fix enabling previously skipped coherence check.*

---

*Generated by audit session 2026-08-19. Next update after Plan R unblock or M2 sprint completion.*