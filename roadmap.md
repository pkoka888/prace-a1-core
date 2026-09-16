# Product Roadmap — Jan Pilot to Recruitment Platform

**Status:** Authoritative
**Original date:** 2026-08-19
**Last status update:** 2026-09-16
**Current stage:** Release 1A in progress. Repository implementation and historical synthetic evidence exist; current private-site usability, PostgreSQL acceptance and Jan acceptance remain separately verifiable. A separate infrastructure request for the PostgreSQL target is issued and awaiting response.

2026-09-16 audit at `a48a1e8`: core correction, source-byte verification and
verifier-result reuse are implemented, but candidate completeness, PostgreSQL
ownership/locking/forwarding, core acceptance coverage and browser timeout diagnosis
remain open. Fresh read-only observations: PostgreSQL running, application systemd
unit failed, port 8001 listener present; current DB authentication and routed workflow
not reverified. **Delivery 1 is not accepted.** Source-publication status and receipts
live in the [delivery record](docs/operations/git-delivery.md). Fresh synthetic
records remain the first-delivery scope; legacy transfer, real-data activation and
official A1 issuance remain separate.

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

1. **REL-03 / JAN-04: complete and protect the candidate.** Integrate the missing
   shell migration-scope dependency; verify independent disposable-target ownership
   before mutation; repair the reproduced psql lock-probe error and environment/TLS
   forwarding. Use isolated in-project PostgreSQL for application integration; host
   credential recovery is not a prerequisite for these repairs.
2. **JAN-01–JAN-03: make the core workflow independently demonstrable.** Diagnose
   the document-detail timeout with response/domain-state evidence, replace fragile
   waits, and preserve bounded failure diagnostics. Remove unconditional optional-A1
   sparse assertions from core acceptance; prove incomplete saving through the shipped
   UI. Retain the implemented non-A1 correction and protected byte checks.
3. **REL-03–REL-06: make evidence accurate and proportional.** Bind validation to
   actual source/dependencies/settings, fix overlapping selection, and extend the
   existing export entrypoint to run the core browser/restart scenario. Reconcile
   skills, CI proposals and current status without another general-purpose runner.
   REL-01/REL-02 refresh reconciliation continues independently, not as a gate on fixes.
4. **INFRA-PG-01 + JAN-04: intended-target acceptance.** Infrastructure reconciles
   credentials, supervisor/listener ownership, approved build and routing. Engineering
   then runs one committed-source core candidate on the intended PostgreSQL target,
   proving exact records, corrected values and document bytes across an authorized
   restart. Supply Czech instructions and limitations, then observe Jan's use.
5. **PILOT-01: restricted real-data pilot.** Complete the existing scoped access,
   privacy, retention and recovery/PG5 activation evidence. No A1-only requirement
   becomes a core-v1 prerequisite.

Tasks, dependencies and ownership live in the
[bounded plan](plans/2026-09-14-delivery-reliability-and-jan-v1.md).
No invented approval or automatic gate opening follows from this scope correction.
Registered gate definitions and the review UI still need scope reconciliation
under JAN-03; preserve historical approval receipts and the 34 top-level catalog IDs.

### Public hostname and environment (2026-09-16 review decision)

The canonical **checkout** is `/var/www/prace-v-nemecku.tvoje.info` (operator-declared).
A checkout directory does not choose a public hostname. Operator decision on
2026-09-16: proceed **temporarily** with the public hostname
`prace-v-nemecku.expc.cz`, matching the provisioned nginx vhost and the
`PRACE_ALLOWED_HOSTS` value in `RETIRED_RUNTIME_CONFIG` (systemd `EnvironmentFile`, 0640
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

## Runtime path retirement checkpoint — 2026-09-16

Operator selected `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env` as the infra-owned EnvironmentFile.
See [runtime contract](docs/operations/runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
This update changes application source guidance only: production cutover requires
separate infrastructure receipts, with exact payload retained and no restart or rotation.
The temporary hostname stays `prace-v-nemecku.expc.cz`; checkout `.env` stays separate.
Earlier authentication failures remain report-attributed; no fresh password test
was performed here. Current manifest bytes/marker are not an approved release.
JAN-01–04, committed-source acceptance, supervision and PG5 remain open.

## Runtime path deployment evidence — 2026-09-16

Infrastructure applied the authorized path-only migration and reloaded systemd,
without restarting the failed service or rotating credentials. Independent current
unit query confirms `EnvironmentFiles=/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`,
`NeedDaemonReload=no`, and unchanged failed/signal9 status. Server61 core receipts:
`evidence/reviews/2026-09-16-prace-path-retirement/parent/migration-apply.json`
and `parent/migration-repeat.json` (native0; repeat changed0), plus
`review-policy/postflight.json` (private on-host byte-equivalence, metadata and
unchanged listener-process checks) and `review-app/loaded-unit-final.json`.
These references are under that same server61 core evidence directory, not local
application files. At that path-deployment checkpoint, source updates were uncommitted and
unpublished in this application checkout; current publication is in the delivery record. No PostgreSQL authentication,
secret separation/rotation, manifest approval/repin, service recovery, JAN acceptance
or PG5 restore gate is closed by the path deployment.
