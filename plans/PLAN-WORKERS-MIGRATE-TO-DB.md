# Plan PLAN-WORKERS-MIGRATE-TO-DB — Worker data: from JSON/CSV to database

**Status**: planned
**Milestone**: M2–M5 (accepted cutover after ENG-001 → REV-002)


2026-09-09 draft checkpoint: synthetic inbox/`a1_prepare_draft` now calls the
canonical unverified-draft publisher. Migration 0016 reserves an immutable number,
source/profile/dependencies and package UUID; retries recover the same package.
Unknown certificate dates remain blank; every page has an UNVERIFIED DRAFT notice.
Human/visual confirmation and official issuance remain separate. Migration 0017 adds
immutable generations for changed dependencies, preserving the number and prior packages.
BO generation access and generation-bound visual confirmation are implemented. Next: expected-revision identity/field confirmation in BO. See the
[local automation contract](2026-09-08-local-a1-automation.md) and delivery record.
Existing environments remain unchanged; selected supervised release needs 0014–0018.

## Consolidated contract — 2026-09-08

The [local automation plan](2026-09-08-local-a1-automation.md) is the bounded child
contract for J2/J4 and DB-MIG-1 through DB-MIG-7. Its
[44-field mapping](../docs/architecture/release-1a-field-mapping.md) supersedes the
older assumption that every CSV field needs a Worker/A1Case column. This is a
planning checkpoint, not a completed migration or portal activation.

Respect [ADR-001](../docs/decisions/ADR-001-jan-portal-architecture.md) and
[ADR-002](../docs/decisions/ADR-002-release-1a-data-and-transactions.md).
Preserve catalog IDs and registered approvals. No extra ADR, repeated operator
permission or new activation gate is required for the authorized synthetic preparation.

2026-09-09 implementation checkpoint: seed/reproducer repairs and bounded J2
synthetic intake have behavioral coverage. Fixture role mapping, duplicate/case
reconciliation and exact settings selection are implemented; evidence belongs in
the delivery record. J2 now persists evaluated evidence and unconfirmed identifier
claims, creates eligible drafts and exposes revision-checked explicit resolution.
Migrations 0014/0015 are tested on disposable databases; existing environments are preserved.
Synthetic input snapshots and all 44 canonical CSV columns are exported by
`portal/release1a/a1_exports.py`, with versioned assignment facts and provenance.
No DB-MIG cutover is accepted. Generation-bound visual confirmation is implemented. Next: expected-revision identity/field confirmation in BO, with identity revision integration in parallel and selected supervised
migration before runtime use. Existing cutover dependencies remain unchanged.

## Purpose and current ownership

After accepted cutover, organization-scoped Django services own worker identity,
assignment, institution, A1 input and confirmation revisions. Both dashboard and
local coordinator use those services; A1 rendering uses the shared Python core.
CSV/JSON are revision-bound compatibility exports, not editable masters.

Before cutover, preserve and reconcile `a1/review.csv`, `a1/cohort.json`, normalized
identity sources and explicitly selected scoped run snapshots. Never choose a
winner by modification time, copy facts from generated PDFs, or freeze sources
before reconciliation. Issued identifiers and confirmed facts retain their evidence.

Worker has names, birth date and broad activity profile today; accepted additional
identity fields fit WorkerIdentityRevision. FieldProposal/FieldDecision already
hold review evidence. There is no Approval model or dedicated A1Case.document_id
or issue_date column. Case facts fit versioned snapshots with structured provenance
and input decisions; visual confirmation is separate. The mapping proposes only
`Worker.legacy_employee_id` and `Assignment.a1_facts_json` as additional columns,
with the required constraints and revision/service contracts. Assignment facts now
have migration 0015 and a synthetic update/export service; the legacy key remains planned.

## Implementation milestones

Preserve existing task IDs. Acceptance descriptions below define future scoped
checks; test modules and commands are added/updated with implementation, not assumed
available from their mention here. Use one shared export adapter in
`portal/release1a/a1_exports.py`, as specified by the mapping.

| ID | Contract | Required acceptance |
|---|---|---|
| DB-MIG-1 | Reconcile identity/legacy bindings into Worker projections and immutable identity revisions; preserve pending proposals | All identity fields mapped; tenant uniqueness; historical MigrationExecutor transition; pending OCR never overwrites accepted fields |
| DB-MIG-2 | Store versioned assignment facts, institution/profile payload and case certificate inputs with structured provenance | Explicit profile/assignment selection; source and input decision binding; generated IDs/dates remain provisional; visual and input acceptance distinct |
| DB-MIG-3 | Adapt a selected database snapshot to the existing core form contract; keep finalize_a1.row_to_form Django-independent | Same normalized core input as the pinned compatibility export; one export service; no live legacy master reads on the cutover path |
| DB-MIG-4 | Dashboard/local coordinator use shared services and the existing canonical renderer/J4 artifact publisher | Actual PDF, snapshot, previews and receipt; stable retry ID; stale dependencies rejected; all-page QA |
| DB-MIG-5 | Resumable reconciliation/import of explicitly selected CSV/cohort/identity snapshots with source hashes | Dry-run reports conflicts without changes; approved synthetic apply is transactional/idempotent; no duplicate workers or invented confirmations |
| DB-MIG-6 | Freeze legacy master editing only after accepted reconciliation; maintain protected history and derived compatibility exports | Guard cutover production adapters against live legacy-master reads; historical import and explicit export adapters remain allowed; rollback references preserved |
| DB-MIG-7 | Demonstrate dashboard/local/core round-trip equivalence on the same synthetic revision | Compare every mapped value/provenance and renderer input; compare PDF bytes with pinned template, renderer, dependencies and deterministic metadata; explain any nondeterminism |

## Environment and delivery order

Follow the child plan's inventory, fresh development database, seed reconciliation
and release reproduction prerequisites before the coordinator/cutover work.
Use `runtime/portal/supervised-development/` with `portal.settings_supervised_synthetic`;
PostgreSQL supplies migration/concurrency acceptance, SQLite isolated synthetic tests.
The existing root and synthetic-review SQLite databases are historical inputs to
inventory, not a database template. Rebuild fresh from the on-disk migration graph;
never fabricate migration records or propagate inconsistent history with `--fake`.

Extend the existing seed deliberately for that synthetic environment and planned
`--verify` fixture reconciliation. Implement the planned
`scripts/release_reproducer.sh <sha>` for immutable `runtime/s-<full-commit-sha>/`
exports and protected receipts. Neither command is introduced by this documentation.

One editable source tree remains. Do not move entire PDF packages or duplicate
runtime credentials. Classified private retained material uses
`runtime/portal/temporary/retained/<uuid>/`, with hash/location manifest and retention
review; `.archive/` is non-sensitive. Existing protected data was never Git material,
so this plan does not require deleting an archive from Git or rewriting history.

## Dependencies, acceptance and next owner

- PLAN-INFRA owns runtime provisioning and infrastructure evidence; routine synthetic
  implementation remains authorized under existing active plans.
- PLAN-WORKERS owns worker/BO workflow acceptance; ENG-001 and observed Release 1A
  acceptance remain cutover dependencies. No registered approval state changes here.
- PLAN-LEGAL supplies purpose/retention interpretation; real-data portal migration
  and activation follow [real-data-rules §12–14](../docs/security/real-data-rules.md#12-mandatory-recovery-before-real-data-activation)
  and [PLAN-REAL-DATA](PLAN-REAL-DATA.md). Production prerequisites do not block
  synthetic preparation; existing authorized operator-only A1 work stays distinct.

Run affected checks once against matching source/dependencies/configuration, under
[AGENTS.md](../AGENTS.md). Update [one delivery record](../docs/operations/git-delivery.md)
with implementation, validation, publication, deployment and activation separately.
Documentation/field coverage alone cannot establish runtime acceptance.

Next owner: engineering for the inventory and fresh synthetic development setup,
then the DB-MIG tasks above. Jan supplies missing business facts and confirms exact
revisions in BO. The [framework guide](../docs/architecture/A1_FRAMEWORKS.md) describes
the current file-based/case-snapshot paths without claiming cutover already happened.
