# Release 1A Architecture and Data Readiness Contract

**State:** ADR-001 direction accepted; technical validation and ADR-002 pending

Provisional boundary: Django modular monolith, PostgreSQL, templates with targeted
HTMX, organization-scoped authorization, background jobs, protected filesystem,
append-only audit events, and a Django-independent A1 engine interface.

```text
User/MFA → view/form authorization → domain command → PostgreSQL transaction
                                      ├→ append-only AuditEvent
                                      └→ durable job/outbox → worker → protected artifact
```

The Release 1A logical model keeps User, Person/Worker, Membership, ActivityProfile,
DocumentVersion, OCRRun/Proposal, Workplace/Assignment, A1Case/Snapshot/Artifact,
ReviewTask, Job/Outbox, and AuditEvent distinct. Organization ownership is required
on every tenant record. Effective dates and immutable versions preserve history.

Transaction proofs must cover duplicate uploads, concurrent OCR decisions, stale
assignment edits, idempotent job retry, worker crash/restart, A1 snapshot staleness,
and audit/outbox atomicity. Query/index evidence must begin with scoped worker
lists, attention queues, document review, current assignment, A1 readiness, and
object audit history; no index is accepted without its query.

Deletion design must distinguish revocation/archive, retention expiry, legal hold,
derived proposal cleanup, immutable audit metadata, and protected artifact removal.
Migration dry runs use synthetic legacy-shaped rows and produce reconciliation
counts and rejection reasons only.

ADR-001 implementation readiness still requires measured MFA, queue, storage/download, audit, tenancy,
dependency, observability, recovery, and rollback proofs. ADR-002 requires the
approved N-1A catalog, ERD/dictionary, permission and transaction matrices,
deletion graph, migration reconciliation, query/index evidence, and concurrency
tests. No portal scaffold is authorized by this outline alone.
