# Plan PLAN-WORKERS — Worker, Role, Data, UX, and OCR Workflow Discovery

**Status**: active
**Milestone**: M1A–M3


2026-09-09 draft checkpoint: synthetic inbox/`a1_prepare_draft` now calls the
canonical unverified-draft publisher. Migration 0016 reserves an immutable number,
source/profile/dependencies and package UUID; retries recover the same package.
Unknown certificate dates remain blank; every page has an UNVERIFIED DRAFT notice.
Human/visual confirmation and official issuance remain separate. Migration 0017 adds
immutable generations for changed dependencies, preserving the number and prior packages.
BO generation access and generation-bound visual confirmation are implemented. BO field confirmation is revision-checked. BO identity association/conflict resolution now submits source- and worker-revision-bound choices to the canonical identity service. Explicit synthetic legacy-key reconciliation is implemented. Selected-cohort CSV/identity input bundles are implemented. Profile-bound protected publication and the synthetic export CLI are implemented. Next: BO bundle access with pinned manifest hashes. See the
[local automation contract](2026-09-08-local-a1-automation.md) and delivery record.
Existing environments remain unchanged; selected supervised release needs 0014–0019.

## Local automation and data ownership — 2026-09-08

The [consolidated local automation plan](2026-09-08-local-a1-automation.md) extends
J2/J4 and DB-MIG-1 through DB-MIG-7 without adding top-level catalog entries.
The [44-field mapping](../docs/architecture/release-1a-field-mapping.md) reuses
proposals, decisions and identity/case revisions; the review's missing-column
estimate is not a schema specification. One command will prepare proposals and
eligible unverified drafts without waiting for BO; human confirmation remains an
actor/time/revision decision. Bounded synthetic J2 inbox intake is implemented:
completed batches reuse the shared intake/OCR adapter, preserve proposals and
resume failed runs. Durable evaluations and typed-identifier claims now support
conditional unconfirmed drafts; explicit resolution has source/revision checks.
Revision-bound canonical input snapshots/exports and assignment facts (0015) are implemented.
Generation-bound visual confirmation is implemented. BO field confirmation is revision-checked. BO identity association/conflict resolution is revision-checked. Explicit synthetic legacy-key reconciliation is implemented. Selected-cohort input bundles are implemented. Profile-bound publication and the synthetic CLI are implemented. Next is BO access
to pinned bundles. The selected supervised environment needs migrations 0014–0019;
see the child contract and delivery record for the precise acceptance scope.

## Shared intake Git delivery — 2026-09-08

Child: [shared document intake](2026-09-06-ocr-shared-core-local-web.md),
OCR-CORE-1 through OCR-CORE-14.

Shared offline processing and synthetic runtime dependencies are committed in
separate scopes. Document replacement now uses the shared intake pipeline with
version preservation, retry reuse and rejection of obsolete OCR acceptance.
The [current delivery record](../docs/operations/git-delivery.md) separates exported-snapshot tests,
Git publication and remaining gates. No deployment or real-data activation is
included; all existing plan IDs and approval states remain unchanged.

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

Single governing plan for who works for the operator, the roles and data they
exercise, and the employee/document/OCR workflows: Jan workflow discovery,
UX/UI/copy research, Release 1A role and data discovery, and the Release 1A
database and transaction architecture.

## Child work packages

- [2026-09-06-OCR-SHARED-CORE-LOCAL](2026-09-06-ocr-shared-core-local-web.md) — shared
  Python document core, local CLI adapter, Django protected storage/jobs, and
  mixed-document segmentation (OCR-CORE-1 through OCR-CORE-14). Bounded synthetic implementation
  and checks: [shared intake](../docs/architecture/shared-document-intake.md).

Replaces and consolidates the dated plans:

- `plans/2026-08-12-plan-f-jan-workflow-discovery.md`
- `plans/2026-08-12-plan-h-ux-ui-and-copy-research.md`
- `plans/2026-08-12-plan-n-full-platform-role-and-data-discovery.md`
- `plans/2026-08-12-plan-o-database-and-transaction-architecture.md`

The archive of the individual dated plans lives under `.archive/plans/`; the
tracked source of truth is this file plus [`plans/INDEX.md`](INDEX.md).

## Status and governance

- Status: `active` — the Release 1A role/data/transaction slice is progressing
  while the M3 workflow and UX maturity gates remain open.
- Decision state: `accepted` — the Release 1A slice (N/O) was accepted with
  delegated defaults on 2026-08-17.
- Evidence: `primary-source-verified` (Jan workflow and UX research derive from
  primary sources; the frozen Release 1A catalog is synthetic but reviewed).

## Dependencies (catalog-recorded)

- `PLAN-INFRA` with gate `evidence-only` — operating model and architecture
  baseline bound the role/data and workflow design.
- `PLAN-LEGAL` with gate `evidence-only` — data protection and legal
  requirements constrain collection, retention, and UX copy.

## Implementation versus acceptance boundary

Synthetic OCR/J2 prerequisite implementation proceeds before ENG-001; that gate
consumes its evidence. Parent ownership is not a dependency that blocks the child
from implementing prerequisites. Observed acceptance and production activation
remain gated. The [current review](../docs/research/2026-09-06-a1-session-architect-review.md)
confirms 75 core and 15 PostgreSQL intake tests passing; release packaging and
remaining J4/ENG evidence are still pending.

## Contents and exit evidence

- **Release 1A role and data discovery:** frozen Release 1A catalog in
  [`docs/architecture/release-1a-catalog.json`](../docs/architecture/release-1a-catalog.json);
  ADR-002 in
  [`docs/decisions/ADR-002-release-1a-data-and-transactions.md`](../docs/decisions/ADR-002-release-1a-data-and-transactions.md);
  acceptance brief
  [`docs/release-1a/unblock-review-packet.md`](../docs/release-1a/unblock-review-packet.md).
- **Jan workflow discovery:** environment available via `Kontrola Release 1A` at `/review/`; `REV-002` is in `proposed` state with `implementation_gate: blocked` — J2 and minimum J4 require Sprint 1–3 implementation before functional acceptance; one acceptance record written per review session (immutable, git-commit-bound). Individual reviewer accounts (non-superuser, inactive until `activate_reviewer`); real TOTP enrollment required. See `docs/operations/release-1a-review-environment.md`.
  matrix; decision input
  [`docs/decisions/2026-08-12-jan-release-1-solution-brief.md`](../docs/decisions/2026-08-12-jan-release-1-solution-brief.md).
- **UX/UI/copy:** tested workflow, localization, and accessibility contract
  with observed Jan/operator journeys before exit.
- **OCR/assignment workflows (M3):** synthetic document/OCR review and
  assignment overlap behavior are exercised on the synthetic vertical slice.
- **Document-first intake:** the shared document core (2026-09-06-OCR-SHARED-CORE-LOCAL)
  is the authoritative intake path. Document processing is central, not a later
  adapter concern. Classification and matching use document-region evidence;
  filenames are hints only.
- **Scan ingestion:**
  [`../readme-scan-to-employees.md`](../readme-scan-to-employees.md) documents
  the private reconciliation reference.

## Document coverage, field sufficiency, and workflow readiness

The synthetic vertical slice implements prototype interfaces for the M2
review environment (J1 worker display, J3 assignment overlap, J4 A1 readiness
trigger). These prototype interfaces are working in the synthetic context but
do not constitute complete implementations:

| Interface | Prototype status | Missing functionality |
|---|---|---|
| Worker display (J1) | Synthetic worker records plus accepted identity revisions and associated documents | Observed workflow acceptance and remaining authorization/retention gates |
| Document/OCR review (J2) | Shared local/web processor, actual local OCR, segmentation, protected source/derivative storage, retries and region acceptance | Production scanner/encryption/retention evidence; broader document edition calibration |
| Assignment overlap (J3) | Implemented (M2 review) | Real placement calculation, missing-data tasks |
| A1 readiness trigger (J4) | Implemented (M2 review) | Functioning J4 snapshots/previews (minimum Sprint 3 before ENG-001) |

Document coverage: the shared document core handles segmentation,
classification (OP/ZP/passport), field interpretation, and side matching.
Field sufficiency: the core returns canonical field maps aligned with
`docs/architecture/release-1a-catalog.json`. Workflow readiness: the core
feeds the Django `OcrRun` model (reused, not replaced); jobs are retryable on failure.

Exit evidence: approved Release 1A scenarios, traceability matrix, and frozen
catalog; minimum synthetic data and ADR-002 contract accepted; employee,
document, OCR, and assignment workflow journeys complete on the synthetic
slice; shared document core passes all 14 OCR-CORE acceptance tests.
The [operator workflow contract](../docs/architecture/operator-a1-workflow.md) defines automatic technical routing, fact-only questions and one consolidated confirmation. Its application interface follows stabilization; existing identity acceptance and legal authorization remain distinct.
