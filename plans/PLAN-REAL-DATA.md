# Plan REAL-DATA — Real-Data Activation After Sprint 4 Gates

**Status**: planned
**Milestone**: M5
**Activation gate**: this plan's acceptance criteria plus all preceding Sprint 1–4 gates

## Purpose

Authorize real PII upload, OCR processing, document storage, and worker identity
management in the portal after all P0/P1 security and functional gaps are closed.
This plan does not authorize production deployment, public exposure, or GitLab CI.

## Activation prerequisites

Every item is required before any real-data upload or new real-person record creation.

### Sprint 1 — Security and functional P0 (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S1-P0-1 | Every material action reachable from an HTTP view passes through a capability check | All roles tested for allowed and denied actions; cross-org read/write/task/download returns zero bytes for unauthorized |
| S1-P0-2 | Child/parent organization referential integrity enforced at DB and service layer | DB composite FKs on PostgreSQL; cross-tenant insert returns explicit domain error |
| S1-P0-3 | Protected storage implemented via Django `Storage` interface | Upload writes to `runtime/portal/quarantine/<opaque-key>`; authorized download returns bytes; unauthorized returns zero bytes |
| S1-P0-4 | Quarantine state and scanner adapter in place | File acceptance includes size, SHA-256, extension allowlist, MIME detection, structural parser check, and explicit scanner unavailable state |
| S1-P0-5 | OCR consumes bytes from storage, not opaque-key-as-path | OCR run opens `storage.open(opaque_key)`; exceptions are not silently swallowed; failed OCR is visible and retryable |
| S1-P0-6 | FieldProposal and FieldDecision genuinely immutable | No mutation path for confirmed proposals; DB uniqueness for one final decision per proposal |
| S1-P0-7 | Authoritative identity revisions created and read by readiness | `WorkerIdentityRevision` created on confirmation; readiness reads current authoritative revision |
| S1-P0-8 | Zero-field confirmation cannot confirm a document | Confirmation requires at least one accepted decision; document remains unconfirmed otherwise |
| S1-P0-9 | Both upload paths and both OCR confirmation paths consolidated | One upload pipeline; one confirmation path; no competing code paths |

### Sprint 2 — Database and recovery P1 (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S2-P1-1 | Forward-only migrations from `0005` to current | `MigrationExecutor` transition tests pass from `0005` to HEAD on PostgreSQL |
| S2-P1-2 | Composite tenant foreign keys on PostgreSQL | `FOREIGN KEY (organization_id, document_id) REFERENCES ...` on all tenant-owned relations |
| S2-P1-3 | Idempotency keys unique; conditional optimistic locking | `OcrRun.idempotency_key UNIQUE`; `UPDATE ... WHERE id=? AND version=?` on Assignment |
| S2-P1-4 | Audit/outbox replaces manual StatusEvent/AuditEvent duplication | One typed append-only event stream; no duplicate writes for the same domain event |
| S2-P1-5 | Query-derived composite indexes added | `CREATE INDEX` for confirmed filter, assignment overlap, readiness aggregation |

### Sprint 3 — M3 completeness (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S3-M3-1 | `IntakeItem`, partial-failure recovery, and operator retry queue | Multi-file intake partially succeeds gracefully; each file has explicit staged state and reconciliation |
| S3-M3-2 | Purpose, legal-basis, and retention fields on all document types | `purpose`, `legal_basis_reference`, `retention_review_at`, `retention_status`, `legal_hold_at`, `deleted_at` present and enforced |
| S3-M3-3 | Czech copy complete; all 48 portal templates load translation tags | `python manage.py compilemessages` passes; no hardcoded user-facing strings remain |
| S3-M3-4 | WCAG 2.2 AA baseline met | axe-core audit passes AA on all user-facing templates; focus visibility, error identification, and destructive-action confirmation accessible |

### Sprint 4 — M4/M5 gates (required)

| # | Requirement | Acceptance criterion |
|---|---|---|
| S4-M4-1 | A1 immutable snapshots and artifacts | `A1InputSnapshot` and `A1Artifact` created per A1 case; bytes stored in protected storage |
| S4-M4-2 | Deterministic A1 generation with QA evidence | `scripts/a1_quality_gate.py render+validate` passes for all approved profiles |
| S4-M4-3 | Submission and authority response tracking | `AuthoritySubmission` and `AuthorityResponse` records; ČSSZ/DVKA submission identifier stored |
| S4-M4-4 | Encrypted backup and isolated restore proof | `pg_dump` encrypted with reviewed key; restore to isolated environment verified; integrity hash matches |
| S4-M4-5 | Jan/operator J1–J4 observation recorded | `REV-1A-FRONTEND` approved; acceptance evidence in `planning/approvals.json` |

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
- Collection of real data from non-consenting individuals
- Production database access from developer machines
- Merger of `a1/` and portal storage lanes

## Exit evidence

| Criterion | Evidence |
|---|---|
| All Sprint 1–4 gates pass | `planning/approvals.json` records `REAL-DATA-GATE` with `human_decision: approved` |
| P0 authorization defects closed | `tests/security/test_capabilities.py` 100% coverage; cross-org tests green on PostgreSQL |
| P0 storage/OCR defects closed | `tests/architecture/test_protected_storage.py` passes with real Django Storage backend |
| All 48 templates translated | `python manage.py compilemessages` clean; `gettext` extracted for all user-facing strings |
| Encrypted backup verified | Restore to isolated PostgreSQL instance confirmed; hash matches `pg_dump` output |
| Operator trained | Jan/operator signed acknowledgment of incident procedures and access protocols |
