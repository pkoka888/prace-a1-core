# Plan O — Database, Query, Index, and Transaction Architecture

**Status:** active
**Prerequisite:** Plan N's Release 1A catalog and Plan E proofs are required before
ADR-002 acceptance. The operational Plan L/M baseline is sufficient for logical
modeling, query discovery, and synthetic transaction design to proceed now.
**Milestone:** M1A–M1B
**Owner:** product engineering

## Objective

Produce a decision-complete logical and physical PostgreSQL design before Django
models are scaffolded.

## Release 1A slice — critical path

- Complete the Release 1A ERD, dictionary, query/index catalog, transaction and
  permission matrices, deletion graph, migration dry run and reconciliation
  design, synthetic concurrency tests, and ADR-002 evidence; expand later modules
  afterward.
- The minimum synthetic M2 contract and acceptance checks are accepted in
  `docs/decisions/ADR-002-release-1a-data-and-transactions.md`; broader physical
  PostgreSQL measurement and Plan O discovery remain active.

## Broader platform slice — parallel, non-blocking

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
Release 1A data slice is approved first; broader M1B expansion follows.
