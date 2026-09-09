# Plan PLAN-A1 — A1 Production, Repository History, and Privacy Baseline

**Status**: active
**Milestone**: A1 operations


2026-09-09 draft checkpoint: synthetic inbox/`a1_prepare_draft` now calls the
canonical unverified-draft publisher. Migration 0016 reserves an immutable number,
source/profile/dependencies and package UUID; retries recover the same package.
Unknown certificate dates remain blank; every page has an UNVERIFIED DRAFT notice.
Human/visual confirmation and official issuance remain separate. Migration 0017 adds
immutable generations for changed dependencies, preserving the number and prior packages.
BO generation access and generation-bound visual confirmation are implemented. BO field confirmation is revision-checked. BO identity association/conflict resolution now submits source- and worker-revision-bound choices to the canonical identity service. Next: synthetic legacy-key reconciliation and complete revision-bound compatibility export. See the
[local automation contract](2026-09-08-local-a1-automation.md) and delivery record.
Existing environments remain unchanged; selected supervised release needs 0014–0018.

## Local A1 consolidation — 2026-09-08

The [local automation contract](2026-09-08-local-a1-automation.md) and
[44-field mapping](../docs/architecture/release-1a-field-mapping.md) define the
J2/J4/DB-MIG follow-up. Reconcile baseline/scoped inputs explicitly; preserve working
provisional packages. The canonical renderer and both frameworks remain in place.
Blank provisional self-employed 5.1 and default 5.2 `DE, CZ` follow existing core
policy; readiness now selects provisional mode explicitly with `--provisional`.
Its default authoritative-evidence mode and human input flags remain intact. Artifact creation,
input acceptance, visual review and external issuance are distinct.
This documentation checkpoint changes no PDFs or readiness/approval states. Current
instructions in AGENTS.md supersede repetitive historical validation procedures.
Existing operator-only A1 work remains authorized under the canonical pipeline;
new portal activation uses real-data-rules §14, not a second A1 gate.

## Runtime and J4 engineering — 2026-09-07

Runtime confinement, mandatory live manifest validation, killable supervised
readiness, PostgreSQL cancellation and model verification are implemented.
J4 stores actual canonical PDF bytes, automated QA, immutable snapshots and all-page
previews, with protected audited delivery and source/template/layout staleness.
Preparation alone produces no PDF hash. Migration0011 is implementation/test evidence,
not a service migration. Exact results and limitations are recorded in the
[engineering delivery](../docs/research/2026-09-07-runtime-j4-engineering.md).

Visual acceptance, the remaining ENG-001 checks and deployment remain gated.
No automatic ENG-001 opening follows; retain prerequisites including J4 → ENG-001
→ REV-002 → hardening/activation gates → REV-003. Jan confirms facts; routine source
repairs and tests need no per-edit operator approval. Research cleanup remains
retain pending review. Preserve all34 catalog IDs and existing child task IDs.
Earlier partial-status defect lists below are historical baselines superseded by
this checkpoint only where the delivery report records completed validation.

## Stabilization checkpoint — 2026-09-07

Bounded stabilization is synthetic-accepted: **157 passed, 19 subtests** in the
final focused suite; document core **75 passed**. Preserve the initial failed
baseline (**5 failed, 33 passed**) as history. Deployment is not performed or
implied. Final isolated-storage/cache reruns passed **15 PostgreSQL intake tests**
and **33 affected M2 tests**, with no model/migration drift. See the
[stabilization report](../docs/research/2026-09-07-a1-stabilization.md).
The broader A1 repair and engineering gates remain active/pending.
See [roadmap stabilization](../roadmap.md#stabilization-synthetic-acceptance--2026-09-07).
Next bounded J4/promotion engineering may start with sequential file ownership;
this does not approve final promotion or activation. Minimum functioning
J4 remains before ENG-001 → REV-002 → remaining activation gates → REV-003.
No service migration is authorized: identify service settings/database separately;
use fresh PostgreSQL and historical MigrationExecutor states for test evidence.
RapidOCR/ONNX does not require Tesseract. Organization work is read-only inventory,
with unknown artifacts classified before any relocation or deletion.

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

## Engineering implementation — 2026-09-07

[Delivery report](../docs/research/2026-09-06-a1-engineering-delivery.md): canonical
employee profiles, repaired data-driven template checkboxes, reviewed-value
preservation, profile/CSV guards, snapshot/dependency hashes, sanitized readiness
receipts and final-destination blocking implemented. Earlier checks were resolved before the subsequent stabilization regressions;
current acceptance is recorded above. Production regeneration remains blocked by actual evidence;
J4 and receipt-bound promotion remain pending in the
[OpenCode packet](../docs/operations/opencode-work-orders/README.md).

## J4 minimum — partial status — 2026-09-07

The OpenCode session produced a `J4 minimum` slice (13 tests passing in
isolation). The slice is a **migration file** (`portal/release1a/migrations/0010_a1case_j4_minimum.py`) implementing five
`A1Case` columns (`source_snapshot_json`, `is_stale`,
`receipt_build_id`, `receipt_git_commit`, `notes`); the
`prepare_a1()` service persists the snapshot, syncs `is_stale`
bidirectionally (was a latent `AttributeError`), and binds
`prepared_artifact_hash` to `app_build_id`/`git_commit` when the
release manifest is configured; `a1_regenerate()` is now idempotent
(clears `is_stale` and emits `a1.regenerated_no_change` when the source
is unchanged); `a1_case_detail` POST persists `notes`.

**Evidence is recorded in three independent states, all of which must
hold for the migration to be considered complete for any deployment
purpose.** Implementation of the migration file is one state;
acceptance in disposable transition tests is another; deployment on a
target database is a third.

| State | Evidence recorded this session | Status |
|---|---|---|
| Migration file implementation | `0010_a1case_j4_minimum.py` written; `django makemigrations --check` reports no drift; the file appears in `portal/release1a/migrations/` and is part of the model graph | code artifact only |
| Disposable transition-test acceptance | migration applied in `tests/m2/test_readiness.py` (`TransactionTestCase`) on the Django in-memory SQLite created by `settings_document_tests.py`; `tests.m2.test_release1a_vertical` exercises the service layer; `tests.test_j4_minimum.py` adds 13 tests against the same disposable DB | synthetic acceptance only |
| Deployment on a target database | **not performed.** No target database has been identified; no migration has run against an authorized service instance | not attempted |

The migration file is therefore a code artifact, not deployment
evidence. Receipt-bound promotion to `output/final/` and any
authorization to advance `ENG-001` requires the deployment state to be
recorded separately, on a target identified by infrastructure and
authorized under the deployment gate.

Independent reviewer enumeration found the slice **partial — J4 remains
incomplete**:

- `prepared_artifact_hash` hashes metadata (`source_hash` + build
  identity), **not stored PDF bytes**. The J4 artifact-evidence
  requirement (stored bytes, deterministic generation, all-page QA,
  protected previews, immutable snapshots, dependency staleness) is
  not yet satisfied. Receipt-bound promotion cannot proceed against
  this hash.
- All-page QA is not implemented.
- Protected previews are not implemented.
- Dependency staleness (input source → template revision → engine
  receipts → build identity) is not detected.
- `is_stale` semantics were extended only at the level of source
  re-hashing; downstream staleness signals remain.

`ENG-001` remains blocked. J4 stored-artifact evidence is the next
required engineering deliverable before any gate opening. Child task
IDs are unchanged.

## Synthetic input integration — 2026-09-09

The inbox now prepares revision-bound A1 input cases using
`portal/release1a/a1_exports.py`: canonical 44-field CSV/JSON export, structured
provenance and explicit missing-fact blockers. Migration 0015 stores versioned
assignment facts. The input service itself creates no PDF or human approval. The subsequent
draft checkpoint above implements the shared publisher and stable reservations;
replacement generation revisions are implemented; BO generation access and visual confirmation are implemented; field confirmation is revision-checked; identity association/conflict BO integration is implemented; synthetic legacy reconciliation and cohort export remain next.
Existing environments remain unchanged; see the delivery record for test evidence.

## Current session review and next implementation

[Architect review — 2026-09-06](../docs/research/2026-09-06-a1-session-architect-review.md)
supersedes current-state assumptions in the earlier baseline: 25/25 rows remain
blocked; four employee PDFs were generated outside the canonical publisher;
26 provisional PDFs and 25 final PDFs now require reconciliation. No final
approval follows from file presence or hash equality/inequality.

Prioritize A1-REPAIR-1/4/5/6/7 evidence/package repair, then A1-REPAIR-2/3 canonical
employee support. Extend existing scripts, not the one-off generator. Include
row-specific employment kind, distinct posting/multi-state mapping, independent
employer evidence, Section 5 omission, calibrated checkboxes, DE-only scope and
consistent field-specific display formatting. Pre-patch A1 checks were 34 passed,
2 failed (territory expectation and VERIFIED placeholder profile); see current engineering results above. Rendering and
ready-to-publish evidence remain separate. Existing authoritative gates stand.

## Dated findings (2026-09-06 investigation baseline)

The following observations were made during the 2026-09-06 investigation and
are recorded as baseline facts, not a replacement cohort contract:

| Observation | Count | Notes |
|---|---|---|
| Rows blocked in `finalize_a1.py readiness` | 25/25 | Every row fails the readiness gate |
| Rows with AUTHORITATIVE source status | 0/25 | No row has an authoritative source status |
| Provisional and final PDF hash equality | yes | Historical byte observation only; does not establish approval |
| VERIFIED profiles | present | Placeholder institution entries, not authoritative sources |

Counts are observations. The operator must populate per-row certificate/
signatory/review fields from authoritative sources before any row can pass
the readiness gate.

## Child work packages

- [2026-09-06-A1-EVIDENCE-STATUS-REPAIR](2026-09-06-a1-evidence-status-repair.md) —
  A1 evidence status repair: reject placeholder institution profiles, enforce
  provisional-generation restrictions, distinguish application readiness from
  certificate issuance, reconcile cohort/artifact provenance, repair snapshots
  and staleness, repair final-promotion evidence (A1-REPAIR-1 through A1-REPAIR-7)

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
Application preparation and Jan confirmation follow the [operator workflow contract](../docs/architecture/operator-a1-workflow.md).

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
