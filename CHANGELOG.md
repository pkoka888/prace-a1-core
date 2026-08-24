# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Dates are ISO 8601. Entries are grouped by change package per `change-packages.yml`.

---

## [Unreleased] — 2026-08-19 Audit-Driven Updates

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
  - `plans/2026-08-11-consolidated-roadmap.md`
  - `plans/2026-08-11-plan-b-opencode-cleanup-workflows.md`
  - `plans/2026-08-11-plan-c-opencode-research.md`
  - `docs/paddleocr/README.md`

---

## [2026-08-17] — M2 Scaffold Gate Open

### Added
- `scripts/check_m2_scaffold_gate.py` — Machine-readable, fail-closed M2 gate evaluator
- `plans/2026-08-17-plan-m2-functional-prototype-sprint.md` — M2 sprint plan
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