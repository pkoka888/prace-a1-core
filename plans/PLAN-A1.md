# Plan PLAN-A1 — A1 Production, Repository History, and Privacy Baseline

**Status**: active
**Milestone**: A1 operations

## Purpose

Single governing plan for the fail-closed A1 production pipeline and the
repository history/reference/privacy baseline that guards its PII inputs.

Replaces and consolidates the dated plans/checkpoints:

- `plans/2026-08-12-plan-r-a1-production-stabilization.md`
- `plans/2026-08-12-plan-q-repository-history-reference-privacy.md`

The archive of the individual dated files lives under `.archive/plans/`; the
tracked source of truth is this file plus [`plans/INDEX.md`](INDEX.md).

## Status and governance

- Status: `active` — the A1 lane is the separate operational focus; the
  repository baseline (`c01aa2b`) is confirmed in
  [`DEC-014`](../docs/decisions/decision-register.md).
- Decision state: `prototype-required`; evidence: `operator-verified` (the
  published sanitized checkpoint and the R-01/R-02/R-03 production outputs were
  hash-bound and operator-verified).
- Executable: **no** — provisional regeneration is currently blocked because a
  `a1/review.csv` regeneration requires operator-populated per-row certificate,
  signatory, review-flag, and AUTHORITATIVE source fields before any employee
  passes `scripts/finalize_a1.py readiness`.

## Hard rules

- `A1_PRIVATE_DIR` is mandatory and fail-closed; there is no tracked fallback.
- Never copy field values between generated PDFs; data-first from authoritative
  sources (`$A1_PRIVATE_DIR/a1/review.csv`, `$A1_PRIVATE_DIR/a1/cohort.json`).
- Deterministic geometry/pixel validation plus local all-page visual review are
  authoritative; a free external vision model is advisory only.
- Final promotion to `output/final`/`output/pdf/` requires `validated_by_user=1`
  plus authoritative certificate/signatory evidence. Provisional outputs are
  never final aliases.
- Never commit or copy `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`,
  `employees/scans/`, `output/`, `runtime/portal/`, `secrets/`, `.env`, or
  `.history-remediation/`; PII-bearing outputs never enter a tracked archive.

## Contents and acceptance

- Canonical pipeline scripts:
  [`scripts/generate_provisional_a1.py`](../scripts/generate_provisional_a1.py),
  [`scripts/finalize_a1.py`](../scripts/finalize_a1.py),
  [`scripts/a1_quality_gate.py`](../scripts/a1_quality_gate.py).
- Skill: [`.agents/skills/a1-pdf-production/`](../.agents/skills/a1-pdf-production/SKILL.md).
- Operator guide: [`../readme-employees-to-a1-form.md`](../readme-employees-to-a1-form.md).
- Policy: [`docs/security/real-data-rules.md`](../docs/security/real-data-rules.md)
  with the 90-day default retention and default-deny real-data access.

Exit evidence: canonical cohort reproducible from authorized sources
(`validated_by_user=1` per row), repository baseline confirmed, and PII-bearing
artifacts never staged or published.

## Named-variable template experiment — 2026-09-07

The supplied vector/text reference was inspected separately from the canonical
raster background. Protected experiments now include a blank reference, a template
with 34 named variables, and two three-page synthetic filling examples. Both
methods format personal names in natural case while preserving raw OCR evidence.

The implementation is a bounded experiment plus a canonical display-casing fix,
not a completed template migration or employee delivery. Keep existing task IDs and
acceptance requirements. Next work: bind the approved reference and field geometry
through canonical configuration; resolve the inherited source/employment mapping
regression; then run production QA with complete reviewed inputs. No gate opens.
Detailed acceptance and Git publication evidence belong to the
[current comparison report](../docs/research/2026-09-07-pdf-tool-comparison.md).
