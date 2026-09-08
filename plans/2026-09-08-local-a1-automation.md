# Local scan intake to worker database and A1 drafts

Status: proposed implementation contract, not an implemented command or activation.
Parents: [PLAN-WORKERS](PLAN-WORKERS.md),
[PLAN-WORKERS-MIGRATE-TO-DB](PLAN-WORKERS-MIGRATE-TO-DB.md), and
[PLAN-A1](PLAN-A1.md). Extends existing DB-MIG-1 through DB-MIG-7 and J2/J4;
no new top-level catalog entries or changes to registered approval states.

## Operator outcome

Upload a completed batch of scans and run one local Python command. The system
validates files, runs local OCR, matches people, saves new proposals or draft worker
records, and generates eligible A1 drafts. The batch does not wait for BO
(back-office) confirmation. Each worker has a visible verification state;
later BO confirmation records who confirmed which revision and when.

Proposed command after implementation and environment provisioning:

```bash
venv/bin/python manage.py a1_process_inbox
```

This command does not exist yet. Its thin Django management adapter will call
shared services; it must not contain another OCR engine, worker matcher or PDF
renderer. The organization, account mapping, inbox and database are configured
once by engineering. No API keys, model selection or repeated approval prompts
belong in routine operator use. Start with explicit runs; a scheduled invocation
or watcher can call the same coordinator later.

## One source of truth

Use the existing Django database and organization-scoped models, with PostgreSQL
as the target. Do not introduce an independent SQLite worker database.
Reuse Worker, Document, DocumentVersion, OcrRun, FieldProposal, FieldDecision,
WorkerIdentityRevision, Assignment and A1Case. Extend only missing contracts using
Django migrations; transition tests use MigrationExecutor.

JSON/CSV are derived, version-bound compatibility inputs/exports, not parallel
editable master records. During transition, create an immutable four-way binding:
database revision, review CSV, cohort JSON and normalized identity snapshot. After
the existing DB-MIG acceptance, the renderer consumes a database snapshot directly.
Do not freeze, relocate or delete the current source files before reconciliation.
Existing issued identifiers and confirmed facts are never replaced by defaults.

## Automated processing

1. Claim only complete batches. Uploader writes temporary files and atomically
   publishes a manifest/ready marker after upload; the command never processes a
   file still being written. Record actor, organization, purpose and retention date.
2. Validate path, size, MIME, signature and readability through existing intake
   services. Use opaque filenames immediately. Malformed inputs go to quarantine
   with a reason code, while unrelated batch items continue.
3. Hash the document. The existing organization/document-hash uniqueness prevents
   duplicate intake. Use document version plus engine/model/config versions as
   the OCR reuse key. A rerun returns the prior result unless its dependencies changed.
4. Run local RapidOCR/shared document processing in `src/document_core/`.
   Split and associate pages/sides from evidence, never filename or upload order.
   Keep values, field confidence, source page/region and input hash as proposals.
5. Match within the organization using validated identity evidence. An exact,
   consistent strong identifier may link a proposal to an existing worker.
   Name/date similarity only suggests candidates. Conflicting identifiers,
   multiple candidates or insufficient identity remain unresolved intake records;
   never auto-merge workers. A new, unambiguous identity may create a draft worker.
6. Save a versioned proposal and machine-check result. For existing workers,
   confirmed fields remain intact; changed values become proposed corrections.
   Automatically refresh only the unconfirmed proposal/draft revision. Use a
   transaction, uniqueness constraints and revision checks to prevent race duplicates.
7. Resolve assignment and A1 inputs from existing records or explicit operator
   defaults. Scans do not supply missing employment facts. For the currently
   requested self-employed provisional presentation, 5.1 is blank and 5.2 is
   `DE, CZ`; retain row-specific, subsequently confirmed territory overrides.
   Keep employee and self-employed profiles distinct.
8. Build a draft when identity association and required inputs are coherent.
   Missing facts/conflicts defer only that person's artifact with an actionable
   reason. Continue all other records. Use `scripts/a1_core.py` for fields, dates,
   provisional numbers, typography and PDF rendering; reserve generated numbers
   in the database transaction and reuse them on retries. Generated dates/numbers
   remain labelled provisional and never acquire official-source status.
9. Render previews, run deterministic and visual checks, and publish atomically
   with snapshot/template/layout/renderer/QA hashes. Artifact reuse is keyed by
   the complete input and dependency revision. A changed fact marks prior drafts
   stale and schedules regeneration; preserve their audit trail.
10. Write a protected batch receipt with opaque references, counts and reasons:
    new workers, matched workers, proposals, unchanged inputs, drafts generated,
    conflicts and failures. Keep sensitive values out of console logs.

## Verification without blocking the batch

Avoid one ambiguous `verified` boolean. Map these proposed fields to existing
immutable decisions/revisions where possible rather than duplicating them:

| Information | Automatic run | BO confirmation |
|---|---|---|
| Machine validation | status, checked_at, check version, reasons | Remains machine evidence |
| Human verification | pending; verified_by/verified_at are null | Confirmed/rejected by logged-in user at timestamp |
| Confirmed revision | Previous confirmed revision preserved | Exact accepted revision and source version recorded |
| Pending corrections | Proposed changes and conflicts retained | Accept/reject per field, with reason where changed |
| A1 artifact | Unverified draft with immutable input snapshot | Review relates to that exact artifact/revision |

BO shows the source, accepted values, proposed changes and missing facts together.
Confirmation is atomic and checks the expected revision: a stale browser cannot
confirm newer OCR it did not display. Later changed evidence reopens the relevant
verification state; the old confirmation stays in history. A machine actor is
never recorded as the human verifier.

The existing canonical publisher currently requires human approval flags, so
fully unattended preparation from fresh OCR needs an explicit draft service
contract under J4. Do not set those flags automatically or route around validation.
Reuse the core renderer through that service with a visible UNVERIFIED DRAFT
notice and separate draft status. Official issuance, submission, final approval
and human verification remain distinct. This plan does not declare that missing
draft contract already implemented.

## Protected storage and names

All paths below are relative to the repository. Use the existing storage services;
these are target contracts, not authorization to move historical files now.

| Content | Target path/name |
|---|---|
| Incoming batch | `scans/inbox/<batch_uuid>/<upload_uuid>.<ext>` plus protected manifest |
| Pending/rejected unsafe files | `runtime/portal/quarantine/<object_uuid>.<ext>` |
| Accepted original scans | `runtime/portal/documents/<document_uuid>/<version_uuid>.<ext>` |
| OCR results/crops and batch receipts | `ocr/<run_uuid>/result.json`, opaque crop names |
| A1 draft versions | `runtime/portal/generated/<artifact_uuid>/document.pdf` and manifest |
| A1 page previews | `runtime/portal/previews/<artifact_uuid>/page-001.png` etc. |
| Transitional canonical CSV/JSON snapshots | `a1/runs/<run_uuid>/` |
| Transitional canonical PDF packages | `output/provisional/<run_uuid>/A1_<opaque_worker_uuid>.pdf` |

Names, birth dates, national identifiers and certificate numbers never appear in
stored paths. Human-friendly document titles belong in protected database metadata
and the authorized BO list. Successful intake verifies the stored hash and durable
receipt before removing an inbox copy; failed moves retain a resumable state.
Processed is a database state, not another uncontrolled copy of every scan.
Quarantine is visible to the operator and never an abandoned error directory.

Use 0700 directories/0600 files (or the documented dedicated-group alternative),
no public static serving, audited access, and the existing 90-day retention-review
default. Reuse approved encrypted recovery procedures; do not create ad-hoc backups.

## Delivery order and acceptance

1. **J2 coordinator, synthetic first:** complete-batch intake, audited account and
   organization context, local OCR reuse, per-record retry/resume and summary.
2. **DB-MIG-1/2/5:** map existing worker/A1 facts and source revisions; reconcile
   existing CSV/JSON before import; prove identity matching and deduplication.
3. **DB-MIG-3/4 and J4 draft contract:** direct shared-core rendering from explicit
   pending/confirmed snapshots; 5.1/5.2 policy, stable provisional IDs, protected
   draft files, all-page QA and dependency-aware regeneration.
4. **BO confirmation:** source comparison, pending queue, immutable actor/time/
   revision decisions, conflict resolution and stale-draft handling.
5. **DB-MIG-6/7:** accept the database as master after round-trip evidence; freeze
   legacy editing only then. Scheduled processing follows a successful manual run.

Required synthetic acceptance: repeated batch causes no duplicates; simultaneous
runs cannot create duplicate workers; changed scans create versions; homonyms and
conflicting IDs never auto-merge; partial upload is ignored; crash after storage
resumes without losing a file; one bad document does not stop others; machine
checks never set human verification; confirmed fields resist OCR overwrite; stale
BO confirmation is rejected; 5.1 blank/5.2 `DE, CZ`; stable IDs and one number per
page; no clipped/duplicated content; cross-organization reads/writes fail; all
sensitive reads/exports are audited. Acceptance commands are added with the
implementation, not presented here as existing runnable tools.

## Current evidence and limits

This session accepted a four-person local provisional package and shared-core
Section 5 correction. That is not acceptance of unattended scan-to-database
automation, a database migration, or portal real-data activation. Existing
operator-only A1 work remains separate. The registered DB migration and
[real-data activation](PLAN-REAL-DATA.md) dependencies remain in force.

Next owner: engineering, to implement the bounded synthetic J2 coordinator and
draft-service contract under the parent plans; operator supplies missing business
facts and later confirms revisions in BO. No recurring per-batch engineering
permission step is proposed.
