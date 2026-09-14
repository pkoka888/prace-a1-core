# Plan REAL-DATA — Real-Data Activation After Sprint 4 Gates

**Status**: active
**Milestone**: M5
**Activation gate**: real-data-rules §14; this plan records the existing Sprint 1–4 dependencies and evidence

## Core-v1 scope reconciliation — 2026-09-14

The [current roadmap](../roadmap.md) excludes official A1 generation/issuance from
v1; existing drafts are optional. JAN-03 in the
[bounded plan](2026-09-14-delivery-reliability-and-jan-v1.md) must scope the existing
review/gate definitions accordingly. The registered legacy J1–J4 dependency chain
below remains recorded until that explicit reconciliation; it is not evidence
that official PDFs belong in core v1. Shared access, storage, revisions, backup,
retention/deletion and §14 real-data controls remain required. No gate is approved
or live environment activated by this documentation change.

## Consolidation boundary — 2026-09-08

The [local automation plan](2026-09-08-local-a1-automation.md) documents one data
owner, fresh synthetic development and later BO confirmation. It does not import
real workers, change registered approvals or activate a service. The operational
activation gate remains [real-data-rules §14](../docs/security/real-data-rules.md#14-real-data-activation-gate),
with this plan recording its staged dependencies and evidence. Existing authorized
operator-only A1 work remains separate. Capacity, recovery and production provisioning
do not block safe synthetic implementation. Preserve current databases and working
PDF packages; any future production root must be aligned with policy §5 before use.

## Stabilization checkpoint — 2026-09-07

Bounded stabilization is synthetic-accepted: **157 passed, 19 subtests** in the
final focused suite; document core **75 passed**. Preserve the initial failed
baseline (**5 failed, 33 passed**) as history. Deployment is not performed or
implied. Final isolated-storage/cache reruns passed **15 PostgreSQL intake tests**
and **33 affected M2 tests**, with no model/migration drift. See the
[stabilization report](../docs/research/2026-09-07-a1-stabilization.md).
The broader A1 repair and engineering gates remain active/pending.
See [current roadmap and historical evidence policy](../roadmap.md).
Next bounded J4/promotion engineering may start with sequential file ownership;
this does not approve final promotion or activation. Minimum functioning
J4 remains before ENG-001 → REV-002 → remaining activation gates → REV-003.
No service migration is authorized: identify service settings/database separately;
use fresh PostgreSQL and historical MigrationExecutor states for test evidence.
RapidOCR/ONNX does not require Tesseract. Organization work is read-only inventory,
with unknown artifacts classified before any relocation or deletion.

## Execution sequence

The authoritative execution sequence is:

```
Sprint 1–3 tasks (including minimum J4 implementation)
  → ENG-001 (implementation_gate: open)
  → REV-002 (human_decision: approved) — Jan/operator J1–J4 observed
  → Sprint 4 tasks (A1 hardening, encrypted backup)
  → operational/legal/infrastructure gates (OPS-001, LEG-001, INF-001)
  → REV-003 (human_decision: approved)
  → real-data activation
```

Minimum J4 implementation (snapshot model, preview/artifact generation, state machine)
is part of Sprint 3 and is required before ENG-001 opens. Sprint 4 contains
A1 hardening and artifact production after REV-002 approval, plus encrypted backup.
REV-002 is a human-decision gate; it does not map to an engineering check.

Sprint labels denote ordered delivery batches, with acceptance evidence tracked
in the tables below; no separate sprint-plan files are required. Shared OCR/J2
synthetic implementation precedes ENG-001 and supplies its evidence. Passing its
tests does not complete minimum J4 or authorize real-data activation.

## Activation prerequisite mapping

Individual prerequisites map to actual engineering check IDs as recorded in
`planning/approvals.json` and `scripts/release_verifier.py`. Sprint 3 includes
minimum J4 implementation required before ENG-001 opens. Sprint 4 items follow
REV-002 approval.

| Prerequisite | Maps to | Notes |
|---|---|---|
| Sprint 1: Protected storage | ENG-J2-STORAGE | Django Storage backend; bytes from storage |
| Sprint 1: Scanner fail-closed | ENG-J2-SCANNER | Size/MIME/scan structural checks |
| Sprint 1: FieldDecision immutability | ENG-J2-IMMUTABLE | No mutation path after creation |
| Sprint 1: Identity revisions | ENG-J2-REVISION | WorkerIdentityRevision created on confirmation |
| Sprint 1: Capability checks | ENG-AUTH | Role × action matrix; cross-org zero-bytes |
| Sprint 1: Concurrency | ENG-J3-CONCURRENCY | Optimistic locking on PostgreSQL |
| Sprint 2: Migrations | ENG-MIGRATION | MigrationExecutor transitions from 0005 on PostgreSQL |
| Sprint 3: WCAG engineering baseline | ENG-A11Y | axe-core automated + manual spot checks |
| Sprint 3: Minimum J4 snapshot model | ENG-J4-SNAPSHOT | A1InputSnapshot model exists; schema migrated |
| Sprint 3: Minimum J4 preview/artifact | ENG-J4-PREVIEW | A1Artifact and preview generation defined |
| Sprint 3: Minimum J4 state machine | ENG-J4-STATE | Deterministic generation; fail-closed pipeline defined |
| Sprint 4: A1 artifact production | Follows REV-002 | Full A1 snapshot/artifact generation after approval |
| Sprint 4: Encrypted backup | (INF-001) | Separate operator/sysadmin gate |
| Sprint 4: Review observation | Follows ENG-001 | REV-002 human decision; follows ENG-001 opening |
| REV-002 | Human decision gate | Jan/operator J1–J4; follows ENG-001 opening |
| OPS-001, LEG-001, INF-001 | Activation-only gates | Operator/legal/sysadmin; outside ENG-001 |

## Purpose

Define prerequisites and evidence for a later, explicit real-data activation
decision. Completion of this plan does not itself authorize real-data processing.
The controlling authority is [`docs/security/real-data-rules.md`](../docs/security/real-data-rules.md),
with explicit operator/legal/sysadmin approval required.

This plan does not authorize production deployment, public exposure, or GitLab CI.

## Activation prerequisites

Every item is required before any real-data upload or new real-person record creation.

### Sprint 1 — Security and functional P0 (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S1-P0-1 | Every material action reachable from an HTTP view passes through a capability check | Complete role × action matrix documented; all roles tested for allowed and denied actions; cross-org read/write/task/download returns zero bytes for unauthorized |
| S1-P0-2 | Service-level child/parent organization validation; complete cross-tenant test coverage | Cross-tenant insert/update/delete returns explicit domain error at service layer; `tests/tenant/` covers every tenant model for cross-org read/write/task/download |
| S1-P0-3 | Protected storage implemented via Django `Storage` interface with encryption-at-rest evidence | Upload writes to `runtime/portal/quarantine/<opaque-key>`; authorized download returns bytes; unauthorized returns zero bytes; filesystem encryption enabled and verified per DEC-009 |
| S1-P0-4 | Scanner adapter fail-closed: scanner error blocks upload | File acceptance includes size limit, SHA-256, extension allowlist, independently detected MIME, structural parser check; scanner failure or unavailability is a hard reject, not advisory |
| S1-P0-5 | OCR consumes bytes from storage, not opaque-key-as-path | OCR run opens `storage.open(opaque_key)`; exceptions are not silently swallowed; failed OCR is visible and retryable |
| S1-P0-6 | FieldProposal and FieldDecision genuinely immutable from creation | No mutation path for proposals or decisions at any state; DB uniqueness for one final decision per proposal |
| S1-P0-7 | Authoritative identity revisions created and read by readiness | `WorkerIdentityRevision` created on confirmation; readiness reads current authoritative revision |
| S1-P0-8 | Zero-field confirmation cannot confirm a document | Confirmation requires at least one accepted decision; document remains unconfirmed otherwise |
| S1-P0-9 | Both upload paths and both OCR confirmation paths consolidated | One upload pipeline; one confirmation path; no competing code paths |

### Sprint 2 — Database and recovery P1 (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S2-P1-1 | Forward-only migrations from `0005` to current | `MigrationExecutor` transition tests pass from `0005` to HEAD on PostgreSQL |
| S2-P1-2 | Composite tenant foreign keys on PostgreSQL | `FOREIGN KEY (organization_id, document_id) REFERENCES ...` on all tenant-owned relations; PostgreSQL RLS as optional defense in depth with non-owner application role |
| S2-P1-3 | Idempotency keys unique; conditional optimistic locking | `OcrRun.idempotency_key UNIQUE`; `UPDATE ... WHERE id=? AND version=?` on Assignment; Worker version field enforces same pattern |
| S2-P1-4 | Audit/outbox replaces manual StatusEvent/AuditEvent duplication | One typed append-only event stream; no duplicate writes for the same domain event |
| S2-P1-5 | Query-derived composite indexes added | `CREATE INDEX` for confirmed filter, assignment overlap, readiness aggregation |

### Sprint 3 — M3 completeness (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S3-M3-1 | `IntakeItem`, partial-failure recovery, and operator retry queue | Multi-file intake partially succeeds gracefully; each file has explicit staged state and reconciliation |
| S3-M3-2 | Purpose, legal-basis, and retention fields on all document types and derivatives | `purpose`, `legal_basis_reference`, `retention_review_at`, `retention_status`, `legal_hold_at`, `deleted_at` present and enforced on `Document`, `DocumentVersion`, `OcrRun`, `FieldProposal`, `FieldDecision`, `WorkerIdentityRevision`, `A1InputSnapshot`, and `A1Artifact` |
| S3-M3-3 | Deletion exercise: revoke, purge, tombstone | Revocation removes access to bytes; derivative bytes (OCR output, previews, A1 artifacts) are purged; a minimal tombstone is preserved with legal hold check; `legal_hold_at` is checked before any purge |
| S3-M3-4 | Czech copy complete; translation catalog coverage measured | `python manage.py compilemessages` passes; extraction catalog covers all user-facing strings; coverage percentage documented; German glossary deferred until operator need confirmed |
| S3-M3-5 | WCAG 2.2 AA engineering baseline | axe-core automated pass on all user-facing templates; manual spot checks for keyboard navigation, focus visibility, 200% zoom, 320px reflow, error identification, destructive-action confirmation, and screen-reader logical reading order |
| S3-M3-6 | Pre-activation A1 acceptance uses synthetic profiles only | A1 case generation for acceptance testing uses synthetic profiles; real A1 submissions require REV-003 approved and operator-supplied authoritative sources |

### Sprint 4 — M4/M5 gates (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S4-M4-1 | A1 immutable snapshots and artifacts | `A1InputSnapshot` and `A1Artifact` created per A1 case; bytes stored in protected storage |
| S4-M4-2 | Deterministic A1 generation with QA evidence | `scripts/a1_quality_gate.py render+validate` passes for all approved profiles |
| S4-M4-3 | Submission and authority response tracking | `AuthoritySubmission` and `AuthorityResponse` records; submission identifier from the actual competent institution stored |
| S4-M4-4 | Encrypted backup and isolated restore proof | Covers: encrypted `pg_dump`, protected file snapshots, manifest with integrity hashes, off-host copy, and isolated application-level restore confirmed |
| S4-M4-5 | Jan/operator J1–J4 observation recorded | `REV-002` human_decision: approved; acceptance evidence in `planning/approvals.json` |

## Real-data rules (never relaxed)

Per `docs/security/real-data-rules.md`:

1. **Purpose limitation** — each document record carries explicit purpose and legal-basis reference; no global consent as default.
2. **Storage separation** — portal documents go to `runtime/portal/quarantine/` and `runtime/portal/documents/` only; `a1/` is the separate A1 production lane.
3. **Opaque storage keys** — no filesystem path beside `opaque_key`; resolve through storage backend only.
4. **Retention review** — `retention_review_at` enforced; no silent retention beyond stated purpose.
5. **Minimum collection** — support selective verification/redaction instead of mandatory full OP/ZP scan retention.
6. **Immutable audit** — every real-data action recorded in audit event without copying sensitive values into logs.

## What this plan does NOT authorize

- Public deployment or HTTPS exposure
- GitLab runner, CI pipeline, or deployment automation
- Collection of data without a documented purpose and applicable lawful basis
- Production database access from developer machines
- Merger of `a1/` and portal storage lanes
- **Portal** real-person record creation until REV-003 `human_decision: approved` in `planning/approvals.json` — the separate A1 operations lane is governed by its own gate and is not affected

## REV-002 → REV-003 promotion procedure

Jan completing the review and clicking **Schválit Release 1A** creates a database
`Release1aAcceptance` record. It does **not** automatically update `planning/approvals.json`.
The promotion to a tracked approval record follows this sequence:

```
Jan completes J1–J4 review
  → application creates build-bound Release1aAcceptance receipt
  → operator verifies receipt commit/build identity matches
  → sanitized evidence reference prepared (no PII in approval register)
  → `REV-002` checks updated to passed in `planning/approvals.json`
  → `REV-002` human_decision set to approved
  → `REV-002` approver and approved_at filled in
  → approval-data.js regenerated from approvals.json
  → validators run: scripts/validate_planning.py and scripts/validate_approvals.py both pass
  → exact scoped files committed through explicit staged path list
  → branch pushed (only if separately approved per DEC-016)
```

**No PII** from the review session, meeting notes, or database receipt is copied into
`planning/approvals.json` or any tracked approval artifact.

For REV-003 (real-data activation), the same pattern applies with the additional
legal/sysadmin sign-off requirement documented in the REV-003 record.

## Exit evidence

| Criterion | Evidence |
|---|---|
| All Sprint 1–4 gates pass | `planning/approvals.json` records `REV-003` with `human_decision: approved` and all checks passed |
| P0 authorization defects closed | Complete role × action matrix in `docs/architecture/`; all roles tested for allowed and denied actions; cross-org tests green on PostgreSQL |
| P0 storage/OCR defects closed | `tests/architecture/test_protected_storage.py` passes with real Django Storage backend; OCR run passes bytes from storage |
| Translation coverage | `python manage.py compilemessages` clean; extraction catalog document with coverage percentage |
| Encrypted backup verified | Restore to isolated PostgreSQL instance confirmed; all artifacts verified; off-host copy confirmed |
| Operator trained | Jan/operator signed acknowledgment of incident procedures and access protocols |
