# Plan PLAN-WORKERS — Worker, Role, Data, UX, and OCR Workflow Discovery

**Status**: active
**Milestone**: M1A–M3

## Local automation and data ownership — 2026-09-08

The [consolidated local automation plan](2026-09-08-local-a1-automation.md) extends
J2/J4 and DB-MIG-1 through DB-MIG-7 without adding top-level catalog entries.
The [44-field mapping](../docs/architecture/release-1a-field-mapping.md) reuses
proposals, decisions and identity/case revisions; the review's missing-column
estimate is not a schema specification. One command will prepare proposals and
eligible unverified drafts without waiting for BO; human confirmation remains an
actor/time/revision decision. No new coordinator or data import is implemented
by this checkpoint. Next engineering work is the source/input inventory and fresh
synthetic development setup, then the existing bounded coordinator/DB tasks.

## Shared intake Git delivery — 2026-09-08

Child: [shared document intake](2026-09-06-ocr-shared-core-local-web.md),
OCR-CORE-1 through OCR-CORE-14.

Shared offline processing and synthetic runtime dependencies are committed in
separate scopes. Document replacement now uses the shared intake pipeline with
version preservation, retry reuse and rejection of obsolete OCR acceptance.
The [current delivery record](../docs/operations/git-delivery.md) separates exported-snapshot tests,
Git publication and remaining gates. No deployment or real-data activation is
included; all existing plan IDs and approval states remain unchanged.

## Purpose

Single governing plan for who works for the operator, the roles and data they
exercise, and the employee/document/OCR workflows: Jan workflow discovery,
UX/UI/copy research, Release 1A role and data discovery, and the Release 1A
database and transaction architecture.

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

## Contents and exit evidence

- **Release 1A role and data discovery:** frozen Release 1A catalog in
  [`docs/architecture/release-1a-catalog.json`](../docs/architecture/release-1a-catalog.json);
  ADR-002 in
  [`docs/decisions/ADR-002-release-1a-data-and-transactions.md`](../docs/decisions/ADR-002-release-1a-data-and-transactions.md);
  acceptance brief
  [`docs/release-1a/unblock-review-packet.md`](../docs/release-1a/unblock-review-packet.md).
- **Jan workflow discovery:** environment available via `Kontrola Release 1A` at `/review/`; `REV-002` is in `proposed` state with `implementation_gate: blocked` — J2 and J4 require Sprint 1 implementation before functional acceptance; one acceptance record written per review session (immutable, git-commit-bound). Individual reviewer accounts (non-superuser, inactive until `activate_reviewer`); real TOTP enrollment required. See `docs/operations/release-1a-review-environment.md`.
  matrix; decision input
  [`docs/decisions/2026-08-12-jan-release-1-solution-brief.md`](../docs/decisions/2026-08-12-jan-release-1-solution-brief.md).
- **UX/UI/copy:** tested workflow, localization, and accessibility contract
  with observed Jan/operator journeys before exit.
- **OCR/assignment workflows (M3):** synthetic document/OCR review and
  assignment overlap behavior are exercised on the synthetic vertical slice.
- **Scan ingestion:**
  [`../readme-scan-to-employees.md`](../readme-scan-to-employees.md) documents
  the private reconciliation reference.

Exit evidence: approved Release 1A scenarios, traceability matrix, and frozen
catalog; minimum synthetic data and ADR-002 contract accepted; employee,
document, OCR, and assignment workflow journeys complete on the synthetic
slice.