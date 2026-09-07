# Plan PLAN-WORKERS-MIGRATE-TO-DB — Worker data: from JSON/CSV to database

**Status**: planned
**Milestone**: M2–M5 (after ENG-001 → REV-002)

## Purpose

Eliminate the duplicated, file-based worker data sources
(`a1/review.csv`, `a1/cohort.json`, `a1/employees_normalized.json`) and
move authoritative worker identity, assignment, OSSZ-institution, certificate
document number, issue date, activity territory, and approval state into the
Release 1A Django database. After this plan, the JSON/CSV files are
**archive-only** and never read by A1 generation.

A1 generation must read a single source of truth — the same records the
dashboard displays and the operator edits through the worker detail view.

## Why

- The CSV/JSON trio currently lives in three gitignored files in `a1/`.
  The cohort and review files are mutated outside the dashboard, by hand,
  by separate scripts. There is no audit trail, no row-level access control,
  no enforced referential integrity.
- The dashboard `portal/release1a/` already models Worker, Document, A1Case,
  Assignment, and Approval as Django models. Re-using these models for the
  authoritative data closes the gap and removes the dual-write problem.
- Once the dashboard is the only writer, the dashboard "Generate A1" button
  becomes a single-step routine that any operator can run with a single
  click, with provenance and approval already attached to the row.

## Scope (in scope)

- Move worker identity fields from `a1/review.csv` → `portal.Worker` rows
  (already partially modelled in M2).
- Move `cohort.json document_ids` and `issue_dates` →
  `portal.A1Case.document_id` and `portal.A1Case.issue_date` (already
  modelled in J4 minimum).
- Move `cohort.json additional_people` (when reconciled) → `portal.Worker`
  with provenance flag `reconciled_from_cohort`.
- Move `employees_normalized.json` (identity reference) → `portal.Worker`
  `insurance_number` / `dob` / `birth_place` fields, validated at write
  time by the shared OCR core.
- Render the A1 PDF directly from the Django model, with no CSV/JSON
  intermediate.
- Add a one-time migration command that reads the legacy files exactly
  once, writes them into the DB with full provenance, and verifies
  identical bytes against a fixture-driven A1 generation round-trip.
- After the migration is verified, the JSON/CSV files are frozen under
  `a1/_archive/` and a CI check fails the build if any tracked script
  reads them.

## Out of scope

- M3 OCR workflow and document intake — already implemented in
  [2026-09-06-OCR-SHARED-CORE-LOCAL](2026-09-06-ocr-shared-core-local-web.md).
- J4 PDF artifact storage — already implemented; will simply read from
  the DB instead of the CSV.
- Activation (real-data / production) — still gated on REV-003 and the
  PLAN-REAL-DATA gates.
- Removing `a1/_archive/` from git — only after one full sprint of
  dashboard-only writes succeed.

## Implementation milestones

| ID | Title | Acceptance command |
|---|---|---|
| DB-MIG-1 | Worker identity fields live in `portal.Worker`; CSV read path deprecated in scripts but still works. | `venv/bin/python -m pytest tests/m2/test_worker_detail.py -q` |
| DB-MIG-2 | Cohort `document_ids` / `issue_dates` live in `portal.A1Case`; cohort JSON read path deprecated. | `venv/bin/python -m pytest tests/test_finalize_a1.py -q` |
| DB-MIG-3 | `scripts/finalize_a1.row_to_form()` reads from `portal.A1Case` and `portal.Worker` (not the CSV). | `venv/bin/python -m pytest tests/test_finalize_a1.py tests/m2/test_release1a_vertical.py -q` |
| DB-MIG-4 | Dashboard "Generate A1" click → `portal.release1a.services.generate_a1_artifact()` reads from DB, calls `a1_core.generate_a1_pdf()`. | `venv/bin/python -m pytest tests/m2/test_release1a_vertical.py -q` |
| DB-MIG-5 | One-time migration command reads `a1/review.csv` + `a1/cohort.json` once, writes DB rows with provenance hashes. | `venv/bin/python scripts/migrate_a1_to_db.py --dry-run --source a1/review.csv` |
| DB-MIG-6 | Frozen `a1/_archive/` snapshot preserved; CI gate blocks any tracked script reading `a1/review.csv` or `a1/cohort.json`. | `venv/bin/python scripts/check_no_csv_reads.py` |
| DB-MIG-7 | Functional A1 round-trip via dashboard click produces bytes identical (sha256) to the legacy CSV-based generation for the same row, on synthetic data. | `venv/bin/python -m pytest tests/m2/test_db_round_trip.py -q` |

## File-system / naming conventions

- **DB models** stay where they are (`portal/release1a/models.py`).
- **Migration command** is `scripts/migrate_a1_to_db.py`. Domain prefix
  `a1_*` and verb `migrate_` together make the script's purpose obvious.
- **Archive directory** is `a1/_archive/` with a timestamped subdir
  per freeze, never auto-cleaned.
- **CI gate** is `scripts/check_no_csv_reads.py`. New scripts that need
  CSV-like input must import from `portal.release1a.services`, not
  open `a1/*.csv` directly.

## Child work packages

None yet. DB-MIG-1 through DB-MIG-7 will be tracked as dated sub-plans
once the parent plan is accepted.

## Dependencies

- `PLAN-INFRA` with gate `evidence-only` — operating model baseline
  must remain stable during the migration.
- `PLAN-WORKERS` with gate `implementation` — J1–J4 prototypes already
  in place; this plan depends on the worker-detail and A1-case pages
  being editable from the dashboard.
- `PLAN-LEGAL` with gate `evidence-only` — retention and access
  boundaries must be defined before deleting legacy files.

## Status and governance

- Status: `planned`. Implementation begins after ENG-001 opens and the
  Release 1A worker-detail page is observed-accepted.
- Decision state: not yet reviewed. The PRD-style decision brief will
  land at `docs/decisions/ADR-NNN-workers-data-db.md` when DB-MIG-1 is
  scoped.
- Evidence: `prototype-required`. Each milestone has its own acceptance
  command; full migration evidence is the cumulative run of those
  commands plus the DB-MIG-7 round-trip byte-equality proof.

## Documentation

- [Roadmap worker data section](../roadmap.md#release-1a-data-and-transactions)
  is updated with the new DB-first path.
- [A1_FRAMEWORKS.md](../docs/architecture/A1_FRAMEWORKS.md) is updated to
  reflect that the canonical pipeline reads from the DB, not the JSON
  cohort.
- [AGENTS.md](../AGENTS.md) carries the standing rule: "A1 generation
  reads from `portal.release1a` models. Legacy `a1/*.json` and `a1/*.csv`
  are frozen for archive only."
