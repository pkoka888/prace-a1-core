# ADR-002 — Release 1A data and transaction architecture

**Status:** accepted for synthetic M2 scaffolding
**Decision date:** 2026-08-17
**Approver:** Pavel/Jan delegated recommended-default instruction, limited to reversible synthetic design

## Decision

Adopt the frozen [Release 1A catalog](../architecture/release-1a-catalog.json)
and [minimum data contract](../architecture/release-1a-data-contract.md): shared
PostgreSQL schema with mandatory organization ownership, membership-scoped
authorization, effective-dated assignments, optimistic concurrency, atomic
audit/outbox, idempotent versioned jobs, protected opaque file storage,
hash-bound A1 snapshots, retention-aware deletion, and expand/migrate/contract
migrations.

## Acceptance checks

- Cross-organization queryset, mutation, task, Admin, and download paths deny.
- Concurrent writes reject stale versions; retry/duplicate/crash yields one effect.
- Audit/outbox commits atomically and contains no sensitive content.
- Protected files are unreachable through public/static paths.
- Assignment ambiguity blocks A1; source change marks prepared output stale.
- Deletion is default-deny, audited, retention/legal-hold aware, and reconciled.
- Every index maps to a named Release 1A query; migrations declare rollback or
  an accepted forward-fix and worker-version compatibility.

The synthetic transaction and isolation evidence is attached to ADR-001's
hash-bound manifest. Operational facts listed as exceptions in the catalog are
not invented and do not block reversible synthetic scaffolding. This decision
does not approve deployment, real data, production migrations, or host changes.

