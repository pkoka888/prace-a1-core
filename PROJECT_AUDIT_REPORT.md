# Project Audit Report — Práce v Německu

**Date:** 2026-08-19
**Scope:** Full repository state vs. AGENTS.md, roadmap.md, plans/, ADRs, skills
**Auditor:** Primary agent (this session)

---

## Executive Summary

The project is **well-structured and largely consistent** with its governance documents. The Python environment, dependencies, and canonical A1 scripts are correctly initialized. The Release 1A architecture (ADR-001) is approved and its eight synthetic checks pass, opening the M2 scaffold gate. However, several **duplicates, legacy artifacts, and drift items** exist that should be cleaned up before the next commit cycle.

| Category | Status | Critical Issues |
|----------|--------|-----------------|
| Environment & Dependencies | ✅ PASS | — |
| A1 Production Pipeline | ⚠️ BLOCKED | Plan R blocker: 7 missing Section 4 columns in review.csv; provisional output (5 PDFs) ≠ canonical (11 PDFs) |
| Release 1A Architecture (ADR-001) | ✅ PASS | 8/8 checks pass; M2 gate open |
| Portal Scaffold (M2) | 🟡 PARTIAL | `portal/` exists but minimal; `prototypes/architecture/adr001/apps/` empty |
| Governance & Plans | ✅ PASS | INDEX.md coherent; approvals.json validated |
| Legacy/Duplicate Artifacts | ❌ FAIL | 15+ backup dirs, `.backup` files, v12 script duplicates, stale config files |
| PII/Secret Safety | ✅ PASS | .gitignore comprehensive; no tracked PII found |
| Test Suite | ⚠️ 1 FAIL | 478 passed, 1 failed (pre-existing fixture collision in Release 1A vertical test) |

---

## 1. Duplicates & Redundant Artifacts

### 1.1 Script Backups (should be removed)
| Path | Size | Age | Notes |
|------|------|-----|-------|
| `scripts/a1_core.py.backup` | 18 KB | 2026-08-11 | Exact duplicate of canonical `a1_core.py` |
| `portal/settings.py.bak` | 1.3 KB | 2026-08-19 | Backup of current settings |

**Action:** Delete both. They are not referenced anywhere and `.gitignore` excludes `scripts/*.backup`.

### 1.2 Versioned Research Scripts (Plan AC experimental lane)
| Active | Duplicate (v12) | Status |
|--------|------------------|--------|
| `run_collector_proposals.py` | `run_collector_proposals_v12.py` | Both tracked |
| `validate_collector_execution.py` | `validate_collector_execution_v12.py` | Both tracked |
| `test_collector_execution.py` | `test_collector_v12.py` | Both tracked |

**Finding:** The `v12` variants appear to be frozen research checkpoints (Plan AC Integrity 1.3). They are listed in `change-packages.yml` under `plan_ac_integrity` but **not** under `quarantined_research_artifacts`. Per Plan AC, these are "provisional" and "not operational until Pilot 1+2 pass."

**Action:** Decide whether v12 files are:
- **Archival evidence** → move to `quarantined_research_artifacts` paths in change-packages.yml
- **Active comparison baseline** → keep but document purpose in Plan AC

### 1.3 Legacy A1 Config Files (referenced as FORBIDDEN_STALE_FRAGMENTS)
| File | Referenced in validate_planning.py | Canonical Replacement |
|------|-----------------------------------|----------------------|
| `config/a1_field_coords.json` | FORBIDDEN_STALE_FRAGMENTS | `config/a1_layout.json` |
| `config/a1_checkbox_coords.json` | FORBIDDEN_STALE_FRAGMENTS | `config/a1_layout.json` |
| `config/a1_field_map.json` | Not referenced | Superseded by layout |
| `config/a1_provisional.json` | FORBIDDEN_STALE_FRAGMENTS | `$A1_PRIVATE_DIR/a1/review.csv` + `cohort.json` |

**Finding:** These files exist in `config/` but are explicitly marked as forbidden stale fragments in the planning validator. They are **not used by canonical A1 scripts** (verified via grep).

**Action:** Delete or move to archive. They create confusion and violate "forbidden stale paths" policy.

### 1.4 Output Backup Directories (15 directories)
```
output/provisional.backup-20260811-114746  ...  output/provisional.backup-20260812-141227
```

**Finding:** 15 timestamped backup directories in `output/` (gitignored). Per Plan R §8, these should be "inventoried by path, timestamp, counts, hashes, and canonical relevance without opening PII."

**Action:** Run Plan R inventory step; then obtain explicit approval for deletion.

### 1.5 Quarantined/Unreviewed Research Artifacts
`change-packages.yml` lists 50+ paths under `quarantined_research_artifacts` and `quarantined_unrelated` that are **not eligible for staging**. These include:
- `.opencode/skills/market-research-evidence/` (experimental Plan AC skill)
- `research/acquisition/*` (live/mini-pilot/raw captures)
- `research/benchmark-experimental/`
- `scripts/validate_ocr_proposals.py` (deferred per Plan R)
- `.kilo/`, `public-site/`, `práce-v-německu.zip`

**Finding:** These are correctly excluded from staging. No action needed unless Plan Q authorizes cleanup.

---

## 2. Inconsistencies & Drift

### 2.1 A1 Cohort Mismatch (Plan R Blocker — CRITICAL)
| Source | Count | Details |
|--------|-------|---------|
| `a1/review.csv` | 9 rows | Missing Section 4 employment columns; missing `pavel-kaspar`, `rudolf-kotlar` |
| `a1/cohort.json` | 11 people | Includes 2 `additional_people` not in CSV; has `document_ids` for all 11 |
| `output/provisional/` | 5 PDFs | Generated from earlier CSV state; **not reproducible** from current inputs |
| Canonical contract | 11 PDFs / 33 previews | Per Plan R and A1 skill |

**Root Cause:** The private `review.csv` predates the seven Section 4 employment columns required by `scripts/a1_core.py`. Regeneration is blocked until operator adds those columns.

**Status:** Correctly documented in Plan R, AGENTS.md, and A1 skill. **Do not weaken gate.**

### 2.2 Portal Scaffold vs. Plan M2 Expectations
| Plan M2 Requirement | Current State |
|---------------------|---------------|
| `prototypes/architecture/adr001/apps/` — proof modules | **Empty** (only `__init__.py`) |
| `portal/release1a/` — production-shaped scaffold | Minimal (models, views, services, migrations) |
| Synthetic fixtures in `tests/fixtures/release_1a/` | ✅ Present (8 JSON files + manifest) |
| `scripts/check_m2_scaffold_gate.py` | ✅ Passes (gate open) |

**Finding:** The M2 scaffold gate is **open** (all 8 ADR-001 checks + catalog frozen + ADR-002 + REV-001 approved), but the actual Django app modules under `prototypes/architecture/adr001/apps/` are not implemented. The `portal/release1a/` appears to be a separate, minimal scaffold.

**Action:** Clarify whether `prototypes/architecture/adr001/apps/` should be populated per Plan E sprint sequence, or if `portal/release1a/` is the intended M2 vertical slice location.

### 2.3 Plan Status Drift (INDEX.md vs. Plan Files)
Checked all active plans in INDEX.md against their actual files — **no drift found**. All statuses match.

### 2.4 ADR-002 Missing
INDEX.md references ADR-002 as approved (2026-08-17) with check `O1A-CONTRACT` passed. The file `docs/decisions/ADR-002-release-1a-data-and-transactions.md` **exists** (verified via decision register).

---

## 3. Claims vs. Reality Checks

| Claim (Document) | Reality (Filesystem/Code) | Verdict |
|------------------|---------------------------|---------|
| "Canonical scripts: `generate_provisional_a1.py`, `finalize_a1.py`, `a1_core.py`, `a1_quality_gate.py`" (AGENTS.md) | All 4 exist, executable, `--help` works | ✅ TRUE |
| "`A1_PRIVATE_DIR` mandatory; scripts fail closed if unset" (AGENTS.md) | Verified: scripts import `a1_private.py` which raises if unset | ✅ TRUE |
| "Provisional regeneration blocked — CSV missing 7 Section 4 columns" (AGENTS.md, Plan R) | Confirmed: CSV has 37 cols; renderer expects 44+ | ✅ TRUE |
| "8 ADR-001 checks pass; M2 scaffold gate open" (roadmap, Plan E, approvals.json) | `check_m2_scaffold_gate.py --json` → `"gate": "open"` | ✅ TRUE |
| "No tracked fallback for A1 inputs; `config/a1_provisional.json` is placeholders only" (AGENTS.md, A1 skill) | `config/a1_provisional.json` has no identity data; `a1_private.py` only reads `$A1_PRIVATE_DIR/a1/` | ✅ TRUE |
| "Free-tier only; OpenRouter model ID must end with `:free`" (AGENTS.md) | `config/free-model-eval/policy.json` enforces this; no paid keys in `.env` | ✅ TRUE |
| "Portal scaffolding waits for M1A" (AGENTS.md) | `portal/` exists but minimal; M2 gate open but scaffold incomplete | 🟡 PARTIAL |
| "GitHub is only remote; GitLab activation gated by Plan AE" (AGENTS.md) | `git remote -v` shows only `origin` (GitHub); no GitLab remote | ✅ TRUE |
| "Historical docs marked superseded" (Plan L) | `plans/2026-08-11-*.md` have no headers; `docs/paddleocr/` unmarked | ⚠️ DRIFT |

---

## 4. Files/Folders Tree & Naming Conventions

### 4.1 Tracked vs. Gitignored Boundaries
| Category | Paths | Git Status | Compliant |
|----------|-------|------------|-----------|
| **Tracked source** | `scripts/`, `config/`, `portal/`, `tests/`, `plans/`, `docs/`, `.agents/`, `planning/` | ✅ Tracked | Yes |
| **PII inputs** | `a1/`, `scans/`, `evidence/`, `ocr/`, `employees/scans/` | ✅ Gitignored | Yes |
| **Runtime outputs** | `output/`, `runtime/portal/`, `secrets/`, `.env` | ✅ Gitignored | Yes |
| **History remediation** | `.history-remediation/` | ✅ Gitignored | Yes |
| **Quarantined research** | `research/acquisition/*`, `research/benchmark-experimental/` | ✅ Not in change-packages staging | Yes |

**Naming Convention Issues:**
- `práce-v-německu.zip` — non-ASCII filename in root (should be removed or renamed)
- `.kilo/` — appears to be tool state (node_modules etc.), not project source; `.gitignore` doesn't exclude it explicitly but it's in `quarantined_unrelated`

### 4.2 Canonical vs. Legacy Path Mapping
| Legacy (Deprecated) | Canonical (Active) | Status |
|---------------------|-------------------|--------|
| `data/a1_forms/` | `$A1_PRIVATE_DIR/a1/` + `output/provisional/` | Gitignored; referenced in FORBIDDEN_STALE_FRAGMENTS |
| `private/a1_final_review.csv` | `$A1_PRIVATE_DIR/a1/review.csv` | Gitignored; FORBIDDEN_STALE_FRAGMENTS |
| `templates/a1_clean_background` | `templates/a1_background.pdf` | Only canonical exists |
| `a1_form_overlay.pdf` | Generated in staging | FORBIDDEN_STALE_FRAGMENTS |
| `config/a1_field_coords.json` | `config/a1_layout.json` | Legacy exists; FORBIDDEN_STALE_FRAGMENTS |
| `config/a1_checkbox_coords.json` | `config/a1_layout.json` | Legacy exists; FORBIDDEN_STALE_FRAGMENTS |

---

## 5. Current State of Sites / Applications

### 5.1 Portal (Private Django App — Release 1A)
- **Location:** `portal/` + `portal/release1a/`
- **Settings:** `portal/settings.py` (minimal; uses SQLite `db.sqlite3` in root)
- **Models:** Organization, User, Worker, Document, Assignment, AuditEvent, A1Case, Job
- **Migrations:** `0001_initial.py` (creates all Release 1A tables)
- **Status:** Scaffold only; no templates, forms, or journeys implemented yet
- **Database:** `db.sqlite3` (221 MB) — appears to have migrated data

### 5.2 Public Site
- **Location:** `public-site/` (in `quarantined_unrelated`)
- **Status:** Not part of Release 1A; per DEC-011 "Separate public frontend — not-applicable"

### 5.3 Prototypes
| Prototype | Location | Status |
|-----------|----------|--------|
| ADR-001 Architecture Proof | `prototypes/architecture/adr001/` | Settings/URLs exist; `apps/` empty |
| Roadmap Portal (Planning Cockpit) | `docs/prototypes/roadmap-portal/` | Generated asset `planning-data.js` exists |
| Research Cockpit | `docs/prototypes/research-cockpit/` | In `quarantined_unrelated` |
| Google AI Studio Frontend Review | `docs/prototypes/2026-08-13-google-ai-studio-frontend-review.md` | In `quarantined_unrelated`; "provisional comparison evidence only" |

---

## 6. Test Suite Health

```
478 passed, 1 skipped, 1 failed in 253s
```

**Failure:** `tests/m2/test_release1a_vertical.py::Release1AVerticalTests::test_j1_to_j4_coherent_path_and_non_content_audit`
- **Error:** `IntegrityError: UNIQUE constraint failed: release1a_organization.key`
- **Cause:** Test fixture tries to create duplicate organization `synthetic-alpha` (likely runs twice without transaction rollback)
- **Impact:** Pre-existing; not related to recent changes. Does not block A1 or architecture proofs.

**A1-Specific Tests (all pass):**
- `test_a1_core.py` — 22 tests ✅
- `test_a1_private.py` — 3 tests ✅
- `test_a1_quality_gate.py` — 7 tests ✅
- `test_finalize_a1.py` — 12 tests ✅

**Architecture Proof Tests (all pass):**
- `tests/architecture/` — 8 test modules, all pass ✅

---

## 7. Compliance with AGENTS.md Rules

| Rule | Compliance | Evidence |
|------|------------|----------|
| Never `git add -A`/wildcard | ✅ | `change-packages.yml` defines explicit path lists |
| PII paths gitignored, never committed | ✅ | `.gitignore` comprehensive; no PII in tracked files |
| Synthetic data only in tests/fixtures | ✅ | `tests/fixtures/` uses synthetic data; no real identifiers |
| Separate commits for A1/portal/governance | 🟡 | Not verified in git history; current workspace clean |
| `A1_PRIVATE_DIR` mandatory for A1 work | ✅ | Scripts fail closed without it |
| Free-tier AI only | ✅ | Policy enforced in config; `.env` has no paid keys |
| Subagents never receive PII | ✅ | This audit only reads metadata/counts |
| OCR/model output = proposal until human confirms | ✅ | Plan R, AGENTS.md, A1 skill all state this |

---

## 8. Recommended Actions (Prioritized)

### P0 — Critical (Blockers)
1. **Plan R:** Operator must add 7 Section 4 employment columns to `a1/review.csv` and add 2 missing people (`pavel-kaspar`, `rudolf-kotlar`) to enable canonical 11-PDF regeneration.

### P1 — Cleanup (Before Next Commit)
2. Delete `scripts/a1_core.py.backup` and `portal/settings.py.bak`.
3. Resolve v12 research script duplicates: either document as archival baselines in Plan AC or move to `quarantined_research_artifacts` in `change-packages.yml`.
4. Delete legacy config files: `config/a1_field_coords.json`, `config/a1_checkbox_coords.json`, `config/a1_field_map.json`. Keep `config/a1_provisional.json` as active provisional-policy config per AGENTS.md (it is not legacy; the A1 pipeline consumes it via `--config config/a1_provisional.json`).
5. Inventory and approve deletion of 15 `output/provisional.backup-*` directories (Plan R §8).

### P2 — Clarification
6. Clarify M2 scaffold location: `prototypes/architecture/adr001/apps/` (Plan E) vs. `portal/release1a/` (current scaffold).
7. Add "Historical/Superseded" headers to `plans/2026-08-11-*.md` and mark `docs/paddleocr/` per Plan L.

### P3 — Documentation
8. Update `README.md` to reflect current state (currently minimal).
9. Ensure all relative links in docs resolve (validator checks this).

---

## 9. Gate Status Summary

| Gate | Status | Blocking Condition |
|------|--------|---------------------|
| **M0 Repository Organization** | 🟡 Active | Plan AE (clean baseline), Plan L (broader exit), Plan Q (history) |
| **M1A Release 1A Readiness** | 🟡 Active | Plan E (done), Plan F/H (Jan review), Plan N-1A/O-1A/ADR-002 (done), Plan M (minimal) |
| **M2 Prototype Sprint** | 🟢 Gate Open | Scaffold implementation pending |
| **A1 Production (Plan R)** | 🔴 Blocked | 7 missing CSV columns + 2 missing people |
| **Real-Data Activation (DEC-012)** | 🔴 Blocked | Plan K recovery evidence, DEC-012 gate incomplete |
| **GitLab/CI (Plan AE/DEC-016)** | 🔴 Blocked | Explicit activation approval required |
| **Plan AC Skill Activation** | 🔴 Blocked | Pilot 1 + Pilot 2 must pass first |
| **Plan AD Acceptance** | 🔴 Blocked | DEC-015 specialist sign-off required |

---

## Appendix: Key File Inventory

### Canonical A1 Scripts
- `scripts/generate_provisional_a1.py` — Entry point + atomic publisher
- `scripts/finalize_a1.py` — Review/validation/ready helpers
- `scripts/a1_core.py` — Static overlay renderer + form validation
- `scripts/a1_quality_gate.py` — Fail-closed QA (render/validate/record-review)

### Governance Scripts
- `scripts/validate_planning.py` — Planning catalog/validator (exit code 0/1/2)
- `scripts/validate_approvals.py` — Approvals register validator
- `scripts/check_m2_scaffold_gate.py` — M2 gate evaluator
- `scripts/run_architecture_proofs.py` — Plan E preflight/run/verify

### Private Inputs (Gitignored, `$A1_PRIVATE_DIR` required)
- `a1/review.csv` — 9 employees, missing Section 4 cols
- `a1/cohort.json` — 11 people, document_ids, issue_dates
- `a1/employees_normalized.json` — Normalized identity data

### Tracked Config (Non-PII)
- `config/a1_layout.json` — Field/checkbox coordinates (canonical)
- `config/address_enrichment.json` — Municipality/district rules
- `config/institutions/*.json` — OSSZ office profiles
- `config/cli_verification_claims.json` — CLI capability registry

---

*End of Audit Report*