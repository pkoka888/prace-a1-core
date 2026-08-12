# Plan and Repository Reorganization Review — 2026-08-12

> **Status: Review report — advisory for the final plan update.** This report does
> not execute cleanup, archival, commit, or deletion. It validates the current
> planning/governance state, lists what should be reorganized, archived, or cleaned,
> and identifies missing parts. Authority remains `AGENTS.md`, `roadmap.md`,
> `plans/INDEX.md`, and `docs/security/real-data-rules.md`.

**Reviewer:** primary agent
**Date:** 2026-08-12
**Branch:** `codex/unified-a1-core` (12 commits ahead of origin, dirty worktree)
**Scope:** governance documents, plans A–P, decision brief, real-data policy,
historical documents, canonical A1 READMEs, repository/configuration state,
and the documented verification claims.

---

## 1. Verified claims (what already passes)

- **Tests:** `venv/bin/python -m pytest -q` → **60 passed, 1 skipped, 12 subtests**.
- **`git diff --check`:** clean (exit 0).
- **Internal `[]()` links:** 0 broken across 42 checked Markdown files (the stated
  "34 checked" was an ad-hoc subset; not reproducible without a committed tool).
- **Authority/status coherence:** all plan files' statuses agree with `plans/INDEX.md`.
- **Historical banners:** `docs/paddleocr/`, `plans/2026-08-11-*`, `CLEANUP_REPORT.md`,
  root `research/*` files all carry non-executable banners.
- **`A1_PRIVATE_DIR` resolution:** verified — `a1/review.csv` (9 rows + header),
  `a1/employees_normalized.json`, `config/a1_provisional.json`,
  `config/institutions/` (7 profiles), and 9 `evidence/` files all resolve.
- **Skill boundary:** only `a1-pdf-production` is active; skill has `SKILL.md`,
  `references/` (field-policy, mcp-contract, visual-qa.schema), and `agents/openai.yaml`.

## 2. Coherence fixes (reorganize)

| # | Issue | Where | Priority |
|---|---|---|---|
| 1 | **Canonical READMEs (authority #3) contain stale, non-existent paths** — `archive/2026-08-11/employee_scan_processor.py`, `plans/2026-08-10-ocr-engine-pivot-rapidocr.md` (file does not exist), and `data/employees_normalized.json` (now `$A1_PRIVATE_DIR/a1/employees_normalized.json`, gitignored) | `readme-scan-to-employees.md:10,136,138,139`, `readme-employees-to-a1-form.md:154` | High |
| 2 | **`roadmap.md` lists Plan D under "Active plans"** although Plan D is marked "Superseded planning input" and INDEX treats it as reviewed handoff | `roadmap.md:104` | High |
| 3 | **`prd.md` carries stale worktree counts** — "296 uncommitted paths (239 untracked, 52 deleted)" is outdated (current: 48 status entries, 0 deletions) | `prd.md:31` | Medium |
| 4 | **ADR location is ambiguous** — `docs/decisions/` holds the brief, Plan D §11 lists `docs/adr/`, Plan L says "future `docs/adr/`". Decide one location before ADR-001 | Plan D §11, Plan L §Rules | Medium |
| 5 | **No authoritative decision-status register** — the solution brief has mixed checked/unchecked "Decision" rows; several items say "Confirmed by Pavel" but no single list separates approved vs pending until Plan M's catalog exists | `docs/decisions/2026-08-12-jan-release-1-solution-brief.md` | Medium |
| 6 | **Two institution-config sources** — active path is `config/institutions/<profile>.json` (AGENTS.md), but `scripts/finalize_a1.py:471` still defaults `--current-institution` to tracked `config/institution.json`. Document the role of the singular file or remove it from the prepare path | `scripts/finalize_a1.py:471` | Low |

## 3. Archive / cleanup candidates

| # | Item | Recommendation | Trigger |
|---|---|---|---|
| 1 | **Legacy tracked A1 configs** — `config/a1_field_coords.json`, `config/a1_checkbox_coords.json`, `config/a1_field_map.json`, `templates/a1_placeholders.json` are declared non-active in AGENTS.md; `a1_placeholders.json` has zero code consumers, the coords files are only touched by `tests/test_comprehensive.py` | Move to a project-local archive (e.g. `docs/archive/`) only after a reachability/reference audit updates the test and AGENTS.md | Plan L reference/privacy audit |
| 2 | **Dead `.gitignore` rules** — `archive/**` block (no `archive/` exists), duplicate `employees/scans/ocr_results_stepfun.json`, `data/employees/` double-rule | Prune in a dedicated `.gitignore` edit, not mixed with other changes | Reference audit |
| 3 | **`docs/paddleocr/`, `plans/2026-08-11-*`, `CLEANUP_REPORT.md`, root `research/*`** | Keep in place with banners (already done). No move/delete until the clean documentation checkpoint + reference audit | Plan L gate |
| 4 | **Stale runtime output (A1 track, gitignored)** — 13 `output/provisional.backup-*`, `A1-client-confirmation.tar.gz`, `quarantine-2026-08-11`, `preview-contacts`, `provisional-contact-sheets` | Consolidate under the A1 skill; the current `output/provisional/` holds **5 PDFs and 15 previews**, not the required 11/33 contract. Regenerate the full cohort or restore from backup evidence. **No agent deletion of real data without explicit approval** | A1 production |
| 5 | **`scripts/validate_ocr_proposals.py`** — untracked, unreferenced, undocumented, untested | Index + document + test it, or explicitly defer it | Documentation checkpoint |
| 6 | **`config/institution.json`** contains a named office contact (provisional signatory) — permitted as tracked config, but its provisional status should be machine-visible | Leave tracked; treat contact as provisional until OSSZ confirms | none |
| 7 | **`.playwright-mcp/traces/`** (empty, untracked, unignored), empty `employees/docs-a1/`, `data/processed_images/` | Add `.playwright-mcp/` to `.gitignore`; empty dirs need no action | Reference audit |

## 4. Missing parts

| # | Gap | Required by | Suggested owner / placement |
|---|---|---|---|
| 1 | **Threat model** — required in roadmap M1 exit ("threat model"), but no plan owns or schedules it; Plan E only covers proofs and trust boundaries | `roadmap.md:54` | Plan E (add deliverable) or a small bounded task before ADR-001 |
| 2 | **Git-history / public-repo privacy remediation procedure** — the repo is 12 commits ahead, prior public exposure is documented in `CLEANUP_REPORT.md`, and M0 exit requires a "separately verified procedure" before any rewrite; no such procedure document exists | `roadmap.md:37`, Plan L §Remote/history, `CLEANUP_REPORT.md:39-41` | New bounded plan (e.g. Plan Q) or a decision brief with exact remote targets, rollback, coordination, and approval |
| 3 | **Committed doc link/status validator and PII/secret pre-commit scan** — AGENTS.md and Plan L exit require "doc link/status validation" and "PII/secret checks over staged content", but no committed script exists (the 34-doc check was ad-hoc; bare-path references such as `archive/...` are not even covered by `[]()` link checks) | `AGENTS.md:78`, Plan L §Validation | Plan M validators + `scripts/` lint module |
| 4 | **Decision register** until Plan M's catalog lands — which brief items are approved vs pending | `docs/decisions/...solution-brief.md` §1,2,3,5,9 unchecked | Plan L documentation checkpoint |
| 5 | **A1 manifest completeness** — `docs/a1-release-gate.md` TODO: record source commit + SHA-256 of scripts, template, layout in the manifest; **no owner** | `docs/a1-release-gate.md:47-49` | A1 track backlog |
| 6 | **Font hash-locking** — `docs/a1-release-gate.md` requires a bundled Czech-capable font and runtime SHA-256 assert; **no owner** | `docs/a1-release-gate.md:8-18` | A1 track backlog |
| 7 | **Reference/reachability/privacy audit task** — Plan L requires it after a clean checkpoint, but no bounded task schedules it; without it M0's archive/cleanup exit cannot complete | Plan L §Historical-document policy | New bounded task (can be part of Plan Q) |
| 8 | **`docs/operations/`** referenced in Plan D §11 does not exist; align the planned docs structure (decisions/adr/operations/research/prototypes/security) in one place | Plan D §11 | Documentation checkpoint |
| 9 | **Scan-to-employees adapter port** — `readme-scan-to-employees.md` states "not executable from the active tree"; RapidOCR v3 adapter and schema mapping remain unmapped to any plan (portal OCR is Plan N/O, but the legacy local adapter decision is unowned) | `readme-scan-to-employees.md:9-16` | A1/portal track decision |

## 5. Recommended final-plan-update actions (ordered)

1. **Checkpoint the documentation now** — a separate documentation commit (governance + plans + brief + real-data rules) staged without A1 code/config or ignored paths, per Plan L exit. This unlocks the subsequent reference audit.
2. **Fix the canonical READMEs** (Section 2.1) and `roadmap.md`/`prd.md` stale references (2.2, 2.3) in that checkpoint.
3. **Record the decision register** (4.4) and ADR location choice (2.4) before any ADR-001 work.
4. **Assign the threat model** to Plan E (4.1) and create the bounded history-remediation/reference-audit plan (4.2, 4.7) so M0's exit gates have owners.
5. **Add the doc-link and PII/secret validators** to Plan M deliverables (4.3) — they are currently assumed by AGENTS.md but do not exist.
6. **After the checkpoint and audit**, archive the legacy configs (3.1), prune `.gitignore` (3.2), and index or defer `validate_ocr_proposals.py` (3.5).
7. **A1 track (separate review)**: regenerate the 11-PDF/33-preview cohort contract and consolidate the stale `output/` backups (3.4), and schedule the manifest/font TODOs (4.5, 4.6).

## 6. Evidence notes

- Worktree: 48 status entries (27 modified, 21 untracked paths), 0 staged, 0 deleted.
- `output/pdf/` empty (no promotion); `output/provisional/` = 5 PDFs, 15 PNGs + manifest/checklist/verification_table; 13 stale backup dirs present.
- Local branch 12 ahead / 0 behind `origin/codex/unified-a1-core`; `master` also exists; remote is the previously-exposed public repo.
- No committed link/PII validators; bare backtick paths are not covered by link checks.
