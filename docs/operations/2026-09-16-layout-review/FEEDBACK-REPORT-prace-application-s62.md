# Application feedback report for the s61 work order — server62

Corrective audit: 2026-09-16. Application source inspected at `a48a1e8`, with
inherited working-tree changes identified separately. This supersedes the earlier
blanket FIXED/engineering-complete/publication draft; it does not supersede raw
receipts or authorize infrastructure actions. Requesting repository remains
servers-infra-core on server61; application checkout is on server62.

## Goal and sources

Deliver the core Jan login/worker/document-review/assignment/correction/download
workflow with durable PostgreSQL records and protected source bytes. Official A1
issuance is outside v1. Scope and decisions come from the roadmap/PRD; behavior
comes from inspected source and executed evidence, not the agent transcript.

The [active plan](../../../plans/2026-09-14-delivery-reliability-and-jan-v1.md)
owns current repair TODOs, exact affected paths, validation criteria and owners.
The [delivery record](../git-delivery.md) owns source publication and evidence layers.

## Reconciled findings

| Finding | Current state | Next owner / evidence required |
|---|---|---|
| F-1 migration role/timeout | Partial. Settings gate exists; shell setter absent from `a48a1e8` but present unstaged. Workflow fixture drops migration credential pair; global scope forwarding needs isolation | Engineering/JAN-04: coherent source plus actual migrate/runtime role and SHOW statement_timeout checks on owned PG |
| F-2 test-target contract | Implemented for common partial/TCP/socket conflicts; incomplete for empty/whitespace inputs. Hardcoded operator-name refusal is not proof of ownership | Engineering/JAN-04: normalize/reject invalid explicit targets and verify owned provisioning before first mutation |
| F-3 all-or-none runtime target | Existing supervised settings guard retained; SQLite remains the no-target rehearsal default | Engineering: keep partial-target regressions; never treat SQLite as intended-PG acceptance |
| F-4 forwarding/receipts/cleanup | Receipt environment sanitization implemented. Cleanup safety is open: consumer mints its own ownership record, guard is teardown-only, table-wide DELETEs persist. Invalid mixed-meta/SQL psql probe reproduced on reachable owned PG; export/fixture/TLS forwarding incomplete | Engineering/JAN-04, not an infra-only blocker: independently provisioned per-run target, full lifecycle ownership, real lock/cleanup negative cases and exact target/identity/TLS propagation |
| F-5 readiness contract | Source/test coverage exists; this audit does not certify current deployed build, route or authenticated target | Engineering + infra: fresh intended-route health/readiness/build/engine and actual workflow evidence |
| F-6 infrastructure | Fresh read-only unit query: PostgreSQL running; application service failed/MainPID 0; 8001 listener exists; selected EnvironmentFile loaded. Password authentication, secret separation and approved pin not retested | Infrastructure/INFRA-PG-01: credential, supervision, routing and build reconciliation; PG5 restore remains separate |
| F-7 verification/core workflow | `a48a1e8` implements stored-byte verification, real-result dedup and non-A1 correction. Broad acceptance stays partial: default export omits browser/restart; core lifecycle still unconditionally requires A1 sparse assertions; timeout cause unresolved | Engineering/JAN-01–04/REL-03–04: targeted failures, true core profile and committed-source intended-target acceptance, then Jan |

## Evidence and limits

- Failed hook: `runtime/portal/temporary/change-checks-dvp3wac9/report.json`.
  The actual error is a 20000ms document-detail `networkidle` timeout;
  `SERVER_ERROR_CATEGORIES: []`. No measured load cause. The runner is sequential.
- Successful retry: `runtime/portal/temporary/change-checks-3wz11m3j/report.json`
  (733.59s total); subsequent batch:
  `runtime/portal/temporary/change-checks-fak3qz33/report.json` (224.87s).
  These run working-tree bytes; they are not committed-export acceptance.
- Fresh isolated PG audit: `runtime/portal/temporary/delivery-audit-20260916-moriz8mx/postgres-probe.json`.
  Mixed psql command exit 1; plain SQL control exit 0; actual guard falsely reports
  cluster/credential/lock blockage. Owned Unix-socket-only cluster stopped and removed.
  Initial initdb sync attempt exceeded its 30s audit budget; retry used disposable
  `--no-sync`. This is narrow command evidence, not application durability acceptance.
- Synthetic configuration probes in the same private directory confirm self-created
  ownership acceptance with mocked lock, dropped migration pair, empty-variable
  SQLite fallback and accepted blank DB name. No operator database was mutated.
- Installed Django 5.2.17, allauth 65.19.1 and psycopg 3.3.4 match inspected pins;
  the older allauth mismatch is no longer observed. Full pinned-environment and
  authentication recovery acceptance remain separate.

## Remaining blockers and publication

**B-1 / INFRA-PG-01:** intended deployed target requires current authentication,
supervision, approved build and routing evidence. Earlier authentication failures
are historical observations; this audit did not read the live secret payload.

**B-2 / engineering: OPEN.** The application defects above are not packaging-only.
Local owned-cluster integration is available independently of B-1. Repair source,
execute affected evidence, then produce one coherent committed-source candidate.

**B-3 / infrastructure:** reconcile the 8001 listener with the selected supervisor;
no guessed-PID kills or application-side service recovery.

At the audit observation, `fa87ad8` and `a48a1e8` were local commits; direct
`git ls-remote` returned `8d125f2ced67fced2206a470e9299d57761549e6` for the existing
feature branch. Publication must be recorded from a verified remote object, not
predicted in advance. Current/final status belongs to the delivery record.
No deployment, real-data activation, backup restore or Jan acceptance is claimed.
