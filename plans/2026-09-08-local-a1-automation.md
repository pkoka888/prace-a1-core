# Local scan intake to worker database and A1 drafts

Status: planned. Consolidated implementation contract, updated 2026-09-08;
this documentation delivery does not implement the command or activate a service.
Parents: [PLAN-WORKERS](PLAN-WORKERS.md),
[PLAN-WORKERS-MIGRATE-TO-DB](PLAN-WORKERS-MIGRATE-TO-DB.md),
[PLAN-A1](PLAN-A1.md), [PLAN-INFRA](PLAN-INFRA.md) and
[PLAN-REAL-DATA](PLAN-REAL-DATA.md). Extends existing DB-MIG-1 through DB-MIG-7 and J2/J4;
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

## Consolidation scope and owners

One editable source tree stays at the repository root. Consolidate A1/OCR/BO first;
inventory unrelated work in place. Do not copy the whole workspace into a second
editable production tree. Source exports are immutable commit snapshots, not another
source master. Database rebuilding, file relocation and coordinator implementation
are follow-up work; this checkpoint changes documentation and instructions only.

Respect [ADR-001](../docs/decisions/ADR-001-jan-portal-architecture.md) and
[ADR-002](../docs/decisions/ADR-002-release-1a-data-and-transactions.md).
No new ADR or activation approval is implied by accepting this implementation plan.

| Concern | Authoritative owner |
|---|---|
| A1 policy, dates/numbers, casing, flattening and rendering | `scripts/a1_core.py`; both frameworks share policy and adapters call the canonical core |
| A1 input/readiness contract | `scripts/finalize_a1.py`; its `CSV_FIELDS` is the compatibility header contract |
| Local OCR processing | `src/document_core/`; Django/CLI adapters do not introduce another engine |
| Worker/case facts after accepted cutover | Organization-scoped Django models, decisions/revisions and migrations in `portal/release1a/` |
| Inputs before cutover | Reconciled `a1/review.csv`, `a1/cohort.json`, normalized identity input and explicitly selected scoped run snapshots |
| Runtime configuration | Named `portal/settings*.py` module and one non-secret environment manifest; engineering owns configuration, sysadmin owns credential delivery |
| Source/derivative bytes | `portal/release1a/document_storage.py`; database owns opaque references and hashes |
| J4 PDF packages | `portal/release1a/j4_artifacts.py`; separate atomic publisher and receipt contract |
| Planning/approval state | `roadmap.md`, `plans/INDEX.md`, `planning/catalog.json` and existing approval register; preserve the 34 top-level IDs |

Use the existing Django models with PostgreSQL as the target, not an independent
worker SQLite database. The [44-field mapping](../docs/architecture/release-1a-field-mapping.md)
assigns each CSV column a destination, transform, provenance, confirmation meaning
and export mapping. Reuse FieldProposal, FieldDecision and WorkerIdentityRevision;
not every field absent from Worker needs a new direct column. Planned destinations
are not claims that their schema or BO workflow already exists. Audit through the
existing `AuditEvent` and canonical A1 audit adapters, without logging source values.

Before import, reconcile baseline files with explicitly selected scoped corrections
and institution-profile overrides. Record source hashes, authority and unresolved
conflicts; modification time or PDF appearance never selects the winner. Preserve
existing issued identifiers and confirmed facts. Do not freeze, move or delete
current inputs before reconciliation and accepted cutover.

During transition bind the database revision, review CSV, cohort JSON and normalized
identity snapshot immutably. After DB-MIG acceptance, render from a database snapshot;
CSV/JSON become compatibility exports through the single service specified in the
field mapping. They are not parallel editable masters. An export does not mutate
human confirmation, certificate status or existing artifacts.

## Current evidence and review corrections

The 2026-09-08 schema inspection found the synthetic-review SQLite database at
migration 0009, with 0010–0013 on disk. The root SQLite history includes an absent
`0008_squashed_document_intake_and_j4` and duplicate
`0002_release1a_review_and_acceptance` records. Preserve both historical databases;
create a fresh development database from the on-disk graph. Do not migrate corrupt
history forward, invent replacement history rows or use `--fake` to hide divergence.
A gap in migration row IDs alone does not establish manual editing or its author.

The review's original “39 missing columns” claim overstates the schema gap. Existing
proposal/revision structures own many facts; the mapping is the per-field contract.
PDF creation is artifact presence, never proof of SUBMITTED/ISSUED external status.
Visual confirmation is distinct from confirmation of identity/certificate inputs.
Structured provenance must not exist solely in notes or decision-reason text.

Review inputs (local, unpublished context, not execution authority):
`docs/research/2026-09-08-local-a1-automation-review.md`,
`docs/research/2026-09-08-consolidation-plan-feedback.md` and
`docs/research/2026-09-08-agents-md-audit-and-skill-plan.md`.
Legal conclusions in those memos remain review inputs; no additional operational
legal rules are activated by this consolidation.

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

These relative locations are contracts, not instructions to relocate files now:

| Purpose | Location and state |
|---|---|
| Editable source | Existing repository source directories |
| Immutable release exports | `runtime/s-<full-commit-sha>/`; reuse the existing `s-` convention |
| Fresh supervised development | `runtime/portal/supervised-development/`, using `portal.settings_supervised_synthetic` |
| Historical review shell | Keep `runtime/portal/synthetic-review/`; do not relabel it as the new environment |
| Future production data | `runtime/portal/production/`; future separately provisioned `portal.settings_production`, not the synthetic settings module |
| Complete incoming batches | `scans/inbox/<batch_uuid>/` with opaque upload names and an atomic ready manifest |
| Rejected/unsafe files | `runtime/portal/quarantine/`, opaque keys and actionable reasons |
| Source scans and OCR derivatives | Existing `ProtectedDocumentStorage` keys beneath the configured `DOCUMENT_STORAGE_ROOT` |
| J4 draft packages | `<configured-artifact-root>/<artifact_uuid_hex>/artifact.pdf`, `snapshot.json`, `page-1.png` etc., `receipt.json` |
| Transitional inputs and CLI PDFs | `a1/runs/<run_uuid>/` and `output/provisional/<run_uuid>/` |
| Classified private obsolete material | `runtime/portal/temporary/retained/<uuid>/` with protected original-location/hash manifest, reason, owner and retention review |
| Non-sensitive historical material | Existing `.archive/`; `.history-remediation/` stays in place and sensitive |

The exact source/derivative key regex is enforced by
[document_storage.py:13–16](../portal/release1a/document_storage.py):

```text
(?:documents|generated)/[a-f0-9]{32}(?:/[a-f0-9]{64})?\.(?:source|json|png)
```

`portal/release1a/j4_artifacts.py` deliberately publishes a separate PDF package
format; its PDF path must not be passed through the source-storage regex. Both
publishers keep opaque database references, hashes and access controls. Audit and
batch receipts use protected runtime; human-readable titles stay in BO metadata.

Use `0700` directories/`0600` files; only the documented dedicated-group alternative
permits `0750`/`0640`. No public static serving or PII in paths/logs. Verify stored
hashes and a durable receipt before removing an inbox copy. Processed is a database
state, not another full scan tree. Failed moves retain a resumable state.

SQLite remains available for isolated synthetic tests. PostgreSQL provides migration
and concurrency acceptance. The supervised settings currently require a confined
`runtime/portal/supervised-*` root and explicit release/secret configuration; the
old seed accepts only `portal.settings_synthetic_review`. Extend it deliberately for
the new synthetic environment rather than bypassing containment. Provisioning is
owned by engineering/sysadmin; missing production capacity or recovery evidence
does not block synthetic implementation. Before production storage is activated,
align its explicit roots with real-data-rules §5 under the existing §14 gate.

No wholesale archive of `output/provisional/`. Preserve working packages and
unclassified historical files. Retained material is subject to the existing 90-day
review/hold rules; this is not authority for ad-hoc backups, deletion or Git changes
to protected material. Record a reversible source/destination/hash manifest before
any later classified relocation, verify destination hashes, and retain unresolved items.

## Delivery order and acceptance

Documentation checkpoint (this delivery): consolidated plan and AGENTS.md, complete
field mapping, corrected framework/archive documentation and parent references.
One delivery record distinguishes implemented, validated, published, deployed and
activated; none implies the next. No databases, artifacts or services are changed.

Consolidation prerequisites for implementation:

1. Inventory source dependencies, configuration owners, active input snapshots and
   artifact references. Reconcile field mapping and source conflicts without moves.
2. Build a fresh development database from all on-disk migrations. Preserve historical
   databases. Transition tests must use `MigrationExecutor` historical app states.
3. Extend `scripts/seed_release1a_dev.py` for the explicitly selected synthetic
   environment and add `--verify`: compare against approved
   `tests/fixtures/release_1a/workers.json` and `assignments.json` after seed; report
   missing/extra rows, activity-profile, status-to-state and assignment-label differences.
   Verify is read-only and nonzero on mismatch; repeated seeding is idempotent.
4. Add `scripts/release_reproducer.sh <sha>`: resolve a commit, export its tracked
   source to `runtime/s-<full-commit-sha>/`, use the venv interpreter for selected
   checks, and write a protected hash-bound receipt with commands/results/dependencies.
   Never overwrite a differing existing export or export dirty/untracked inputs.
   Use isolated synthetic test state; no deployment, historic DB mutation or secret
   copying. The command is planned, not currently available.

Then deliver the existing automation tasks in bounded increments:

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

## Validation, activation and optional tooling

Apply the proportional validation policy in [AGENTS.md](../AGENTS.md): documentation
links/status/whitespace and staged-content review; focused code regressions;
integration checks for migrations, storage, authorization and shared rendering;
one committed-source release acceptance; artifact-specific all-page A1 QA.
Reuse evidence only for matching source/dependency/configuration hashes. A required
failure blocks its affected behavior; record unrelated failures without stopping
safe independent work. Existing hooks remain effective until deliberately updated.
`git diff-tree` checks contents, not runtime behavior; avoid duplicate full suites.

Record the implementation/validation/publication/deployment/activation fields in
[one delivery record](../docs/operations/git-delivery.md). Keep parent plan task IDs,
34 catalog entries and registered approval states unchanged. Real-data portal
activation uses [real-data-rules §14](../docs/security/real-data-rules.md#14-real-data-activation-gate),
not a new gate; existing authorized operator-only A1 work remains distinct.
The previously accepted local provisional package and shared-core Section 5 fix do
not prove unattended automation, production migration or portal activation.

The proposed django-portal-conventions, postgres-ops, pii-guard and git-delivery
skills, filesystem/GitHub/Context7 MCPs and client-specific hooks are optional
follow-ups, not prerequisites. Reuse existing tools first. Filesystem MCP allowed
roots do not supply “repository except sensitive directories” enforcement; search
exclusions are not access controls ([upstream documentation](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md)).
A directory-scoped subagent assignment likewise is not a security sandbox.
No tool installation, new credentials, paid service, history rewrite, force-push,
public release or deployment belongs to this documentation delivery.

Next owner: engineering, starting with the bounded dependency/input inventory and
fresh synthetic development setup, then J2/J4 and DB-MIG tasks above. Jan supplies
missing business facts and confirms revisions in BO; no recurring per-batch
engineering permission step or mandatory second human reviewer is introduced.
