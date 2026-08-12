# Plan O — Database, Query, Index, and Transaction Architecture

**Status:** planned
**Prerequisite:** Plan N role/data catalog; Plan E architecture proofs
**Milestone:** M1A–M1B
**Owner:** product engineering

## Objective

Produce a decision-complete logical and physical PostgreSQL design before Django
models are scaffolded.

## Work

- First deliver the Release 1A ERD, query-driven indexes, transaction boundaries,
  deletion graph, migration dry run, reconciliation report, concurrency tests, and
  ADR-002; expand later modules afterward.

- Define bounded modules and ownership for identity, organizations, recruitment,
  workforce, planning/time, documents/OCR, A1, payroll, operational finance, and
  platform/audit/integrations.
- Keep `Person`, `Worker`, and `User` distinct; use effective-dated profiles,
  contracts, organization roles, assignments, and rule sets.
- Specify entities, attributes, types, nullability, foreign keys, uniqueness,
  checks, status transitions, provenance, immutable versions, deletion behavior,
  and legacy A1 mappings.
- Create a role-driven query/report catalog with expected volumes and latency;
  derive indexes from those queries and verify them with representative synthetic
  data and `EXPLAIN`.
- Define atomic command boundaries, concurrency/locking behavior, durable outbox,
  idempotent job records, input snapshots, stale-output detection, retry behavior,
  and failure recovery for upload/OCR/review/assignment/time/A1/payroll/finance.
- Define migration order, compatibility boundaries, reporting/read models, and
  ADR-002 covering tenancy, temporal data, transaction, audit, and outbox strategy.

## Exit

The Release 1A slice is approved for M1A before broader expansion. ERD, data dictionary, state diagrams, query/index catalog, transaction matrix,
permission matrix, migration map, and synthetic concurrency/security tests are
approved. No index lacks a query and no authoritative field lacks provenance.
