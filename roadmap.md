# Product Roadmap — Jan Pilot to Recruitment Platform

**Status:** Authoritative
**Original date:** 2026-08-19
**Last status update:** 2026-09-15
**Current stage:** Release 1A in progress. Repository implementation and historical synthetic evidence exist; current private-site usability, PostgreSQL acceptance and Jan acceptance remain separately verifiable. A separate infrastructure request for the PostgreSQL target is issued and awaiting response.

2026-09-15 observations: PostgreSQL was observed running, but configured
application authentication failed. The Gunicorn systemd unit was failed, while
separate Gunicorn processes lacked PostgreSQL target variables. Application-side
defects and infrastructure reconciliation are both open. **Delivery 1 is not
accepted.** Fresh synthetic records remain the first-delivery scope;
existing-data migration, real-data activation and official A1 issuance remain
separate. See the
[sysadmin reconciliation report](docs/operations/sysadmin-postgresql-reconciliation-2026-09-15.md)
and the active child plan.

This is the execution roadmap. The [PRD](prd.md) defines product scope and the
[plan index](plans/INDEX.md) assigns owners. The bounded next batch is
[delivery reliability and Jan v1](plans/2026-09-14-delivery-reliability-and-jan-v1.md).
Older dated checkpoints remain in Git history and the
[delivery record](docs/operations/git-delivery.md); they are not an active queue.

## Product objective and v1 boundary

Give Jan a private Czech operator portal: normal login and TOTP → create/save a
worker → upload a document → review/correct OCR proposals → create/correct an
assignment → retrieve protected documents and retain records across restart.
Use the existing Django/HTMX frontend, Python services and PostgreSQL architecture.

Official A1 PDF generation and issuance are outside v1 by explicit user direction
on 2026-09-14. Existing provisional/draft PDFs are optional recommendations and a
separate maintained capability. Missing A1 fields, institution verification or PDF
review must not prevent worker saving or acceptance of the core portal workflow.
Keep audit, organization/capability isolation, source revisions and protected storage.

Optional fields may remain null. Missing required facts block only the relevant
operation with actionable Czech guidance. Documented manual review/retry/recovery
fallbacks are acceptable with an owner. Weekly-budget inclusion in v1 remains a
business-scope question; a static mockup is not a delivered budgeting feature.

## Four deliveries and acceptance

| Delivery | Jan's outcome | Required evidence | Current state |
|---|---|---|---|
| 1. Integrated testing site | Stable private URL, individual normal login, frontend/backend/scripts, intended persistent PostgreSQL target | Real browser core journey; protected source-document download; exact worker/document/assignment identifiers survive restart; expected build and DB engine/target checked | **Not accepted.** Historical synthetic rehearsal exists. 2026-09-15: PostgreSQL reachable but configured application authentication failed; Gunicorn supervision mismatch. Fresh synthetic records are the first-delivery scope |
| 2. Usable v1 workflow | Czech instructions, visible missing facts, retry/correction, reliable downloads; one incomplete worker does not stop another | Core success path plus incomplete-input, denied-access and recovery paths; Jan/operator observed use and known-limitations note | In progress; audit leads require focused reproduction, then fixes |
| 3. Restricted production pilot | Same core workflow for the authorized organization and real records | Scoped configuration, access/storage, applicable retention/deletion, backup/restore, operational ownership and §14 activation evidence | Separately gated; no activation approved by this roadmap |
| 4. Later releases | Optional A1 expansion, richer queues, budget if requested, reporting, partner/worker access | New bounded outcomes justified by observed use | Deferred; no new Release 2A/3A names |

Code publication or an isolated SQLite journey does not complete Delivery 1.
Browser, database, publication, deployment and operator acceptance are separate
evidence layers. Recheck host facts before repeating “cluster down” or “not
deployed”; neither is established by this repository-only checkpoint.

## Current execution order

1. **REL-01–REL-03: repair the completion contract.** Reconcile the existing six
   subagent analyses into truthful capability/requirement records, validate their
   references/states, and bind executable evidence to tested inputs. Do not restart
   the six analyses or write repeated PASS summaries.
2. **REL-04–REL-06: make verification proportional.** Audit/deduplicate compatible
   checks, correct document ownership, map effective hooks/CI/configuration,
   and keep concise instructions. Work can run alongside product fixes with
   exclusive file ownership; tooling is not a prerequisite for every UI fix.
3. **JAN-01–JAN-03: deliver normal access and the core workflow.** Investigate
   the OCR HTTP 500 and the download mismatch separately, distinguishing
   authentication redirects from file corruption; repair confirmed defects and
   split optional A1 stages from core acceptance while retaining shared
   safeguards. Bounded JAN-01/JAN-02 repair now provides durable sequential OCR,
   synchronous inbox receipts, visible refresh/retry and archive-state
   authorization. Broader task acceptance stays partial; the core/optional-A1
   profile separation is partially implemented; JAN-04 target acceptance remains
   open. See the child plan and delivery record for evidence.
4. **JAN-04: one candidate acceptance.** Run the committed-source core workflow on
   the scoped PostgreSQL testing target when available, through the intended route;
   record exact restart persistence (actual file bytes and exact records) and
   usable Czech instructions. Repair target forwarding, verified disposable
   cleanup, migration credential scope and the effective statement timeout
   before or alongside acceptance. Prepare scripts and synthetic fixtures before
   host authorization where possible. Application repairs and sysadmin
   reconciliation proceed independently; then one committed-source core
   acceptance run, followed by Jan's observed use.
5. **PILOT-01: restricted real-data pilot.** Consolidate outstanding operational
   facts and activation decisions. A1-only requirements do not become core-v1
   requirements; shared privacy/access/durability requirements remain.

Tasks, dependencies, ownership and parallel waves live in the
[bounded plan](plans/2026-09-14-delivery-reliability-and-jan-v1.md).
No invented approval or automatic gate opening follows from this scope correction.
Registered gate definitions and the review UI still need scope reconciliation
under JAN-03; preserve historical approval receipts and the 34 top-level catalog IDs.

### Public hostname and environment (2026-09-16 review decision)

The canonical **checkout** is `/var/www/prace-v-nemecku.tvoje.info` (operator-declared).
A checkout directory does not choose a public hostname. Operator decision on
2026-09-16: proceed **temporarily** with the public hostname
`prace-v-nemecku.expc.cz`, matching the provisioned nginx vhost and the
`PRACE_ALLOWED_HOSTS` value in `/etc/prace/env` (systemd `EnvironmentFile`, 0640
root:prace-synthetic). Recipes and the PostgreSQL handoff now reference that
hostname; the checkout path is unchanged. Live environment facts stay
operator-owned and are documented in the
[layout review](docs/operations/2026-09-16-layout-review/REPORT-prace-application-s62.md);
the shared-secret equality with the DB password is a boolean-only finding pending
credential rotation.

## Validation and review cadence

| Change/risk | Evidence before completion |
|---|---|
| Documentation or skill prose | Parse/schema where applicable, links, requirement/status consistency, scoped diff/whitespace; no browser rehearsal |
| Ordinary source edit | Relevant regression once; inspect selected test units and selection reasons |
| Shared services, authorization, storage, dependencies, migrations | Affected integration with isolated settings/DB; PostgreSQL for PostgreSQL-specific guarantees |
| Release candidate | One reproducible committed-source core browser/DB acceptance; optional A1 evidence separately |
| Failure or disputed completion | Read existing receipt/logs; reproduce smallest failure; map finding → changed bytes → fresh affected evidence |

Existing mandatory hooks stay in force until deliberately repaired. Reuse results
only for matching source, dependencies, settings and selection. A timeout is a
maximum budget, not a performance objective. Profile routine checks approaching
one minute; remove irrelevant or duplicate execution before tightening deadlines.
Keep full private logs and short summaries. JSON validity and hashes alone do not
prove business correctness. See the [bounded plan](plans/2026-09-14-delivery-reliability-and-jan-v1.md) for evidence follow-up.

## Milestones retained for traceability

| ID | Outcome and current interpretation |
|---|---|
| M0 | Coherent repository, ownership, instructions and reproducible workflow; PLAN-INFRA owns reliability work |
| M1A | Jan core-v1 scope and architecture; existing ADR-001/ADR-002 retained |
| M1B | Broader platform design, non-blocking for Jan v1 |
| M2 | Shared synthetic worker/document/OCR/assignment foundation and integrated testing site |
| M3 | Core correction/retry/missing-data UX now; richer queues/reporting after core delivery |
| M4 | Optional deterministic A1 capability and separate A1 operations; not a prerequisite for core-v1 delivery |
| M4-A | Existing DB-MIG-1–7 traceability; distinguish core persistence from optional PDF equivalence and legacy cutover |
| M5 | Restricted real-data pilot under existing §14 controls and scoped recorded approval |
| M6 | Later partner/worker/public recruitment and other modules driven by demand |

Release names remain Release 1A (Jan operational core), Release 1B (connected
operations), Release 1C (certified administration) and Release 2 (public growth).
Later labels carry no automatic implementation or activation authorization.

## Ownership and boundaries

- Jan supplies operational facts, priorities and observed acceptance; routine
  engineering choices belong to engineering.
- The primary agent integrates shared files, reconciles evidence and publishes
  only authorized coherent source batches.
- Scoped agents own independent named paths and isolated test databases. No
  concurrent edits to shared services, catalog or roadmap.
- Sysadmin owns host services, routing/TLS, database provisioning, credentials and
  backups. Read-only diagnostics can refine the handoff; host writes require authority.
- Activation decisions remain those in
  [real-data rules §14](docs/security/real-data-rules.md#14-real-data-activation-gate).

New MCPs, model benchmarks, public frontend replacement, microfrontends,
containerization, a second settings module and queue rollout are not prerequisites.
Adopt tools only to close demonstrated gaps in the chosen increment.

<a id="stabilization-synthetic-acceptance--2026-09-07"></a>

## Historical checkpoint references

Older plan links to the September 7 stabilization resolve here for compatibility.
Those results describe their dated source only; consult the delivery record and
Git history for provenance. They do not establish current runtime or Jan acceptance.
