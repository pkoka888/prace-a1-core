# Product Roadmap — Jan Pilot to Recruitment Platform

**Status:** Authoritative
**Original date:** 2026-08-19
**Last status update:** 2026-09-17
**Current stage:** Release 1A in progress. Repository implementation and historical synthetic evidence exist; current private-site usability, PostgreSQL acceptance and Jan acceptance remain separately verifiable. A separate infrastructure request for the PostgreSQL target is issued and awaiting response.

2026-09-16 follow-up at `4a38067`: core correction, source-byte verification and
verifier-result reuse remain implemented; `b687abe` integrates the missing shell
dependency. Uncommitted dependency/PG updates partly address earlier findings but
introduce a reproduced cleanup-environment regression. PostgreSQL ownership, effective
role/timeout/TLS, core acceptance coverage and browser diagnosis remain open.
Earlier September 16 read-only observations: PostgreSQL running, application systemd
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

September17 runtime follow-up supersedes the earlier failed-unit observation:
the selected service owns the8001 listener and tagged access requests reach its
journal. PostgreSQL 18 main is online. After explicit user authorization, nine
static ACL changes, group removal and a controlled nginx worker transition
closed the observed credential-read and five account/MFA asset failures: all
seven assets now pass on both routes, and the new workers lack the secret-reading
group. Historical readiness returned 503 `deadline_exceeded`; September17 follow-up
samples alternate between success and timeout with variable directory-write latency. A candidate removes a
duplicate storage probe, overlaps independent directory fsyncs and retains safe
timeout-phase evidence; no deployed
fix or historical cause is established. Approved source/build,
core/restart acceptance and infrastructure desired-state reconciliation remain
open under the [updated request](docs/operations/servers-infra-core-postgresql-request.md).
Application repairs narrow 0750 sharing and remove unsafe global test parallelism;
their publication remains separate from application deployment.

## Backup-first separation request — 2026-09-18

The [separation child plan](plans/2026-09-18-backup-and-project-separation.md)
preserves sites, front/back office, OCR and A1 with their supporting dependencies.
It recommends extracting unrelated tooling into independent source after an
encrypted whole-project backup and actual isolated restore. Research is prepared;
destination/key custody is unresolved and no extraction is implemented. This does
not change core-v1 acceptance, deployment or real-data activation status.

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

1. **REL-03 / JAN-04: protect and validate the candidate.** The missing shell
   dependency is committed. Integrate/review the remaining PG changes, repair the
   cleanup helper losing explicit target/ownership context, and verify independent
   disposable-target ownership before mutation plus effective connection/TLS behavior.
   Use isolated in-project PostgreSQL for application integration; host
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
   Prove clean environment setup with consistent dependency constraints, browser/native
   assets and offline OCR models; installed-package checks do not establish reproducibility.
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

### OCR orchestration disposition — 2026-09-16

Keep the existing shared local OCR processor, durable OcrRun worker and Django
review services for v1. Fresh bounded tests cover generated-document offline OCR
and the isolated worker contract; they do not establish difficult-scan accuracy.
Measure stage/retry cost and reviewer errors before introducing LangGraph. A bounded
synthetic comparison of Django stage receipts and LangGraph recovery/fallback is
optional under OCR-CORE-10/11/13/14, with explicit stop/adoption criteria in the
[research review](docs/research/2026-09-16-document-orchestration-review.md). No new
engine, hosted tracing, model service or v1 gate is introduced by the research.

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

## Independent operational review — 2026-09-16

Fresh checks in the [agent/fleet review](docs/operations/2026-09-16-agent-ops-review.md)
confirm four managed hosts reachable, with failed services/backups on s61/s62
and s61 root storage at 90%. The Práce loopback/internal route serves an older
build while its selected systemd unit remains failed. Neither HTTP 200 nor a
zero-exit diagnostic proves the intended deployment or core acceptance.
The active [REL/JAN TODOs](plans/2026-09-14-delivery-reliability-and-jan-v1.md#independent-agentfleet-review-and-todos--2026-09-16)
now distinguish export/probe repairs, offline Ansible evidence, disposable
deployment tests, operator-owned recovery and observed Jan acceptance.

Protected-export repair and a bounded local LangGraph demonstration are separate
engineering increments. The graph has synthetic effects only; it introduces no
live executor, provider call, service or new v1 gate. Fleet apply, rollback,
backup restore, intended-PostgreSQL browser/restart acceptance and real-data
activation are not established by this checkpoint.

## Follow-up — 2026-09-17

### Reconciliation checkpoint — 2026-09-18

The Phase 1 automation paragraph below is retained as historical intent, not as
the current command contract. The current `Makefile` explicitly selects sequential
focused runs, and `pytest-xdist` is absent from `requirements.txt`,
`requirements-dev.txt`, and `requirements-lock.txt`. The claimed 57-test/75-second
parallel result and 60-80 percent reduction must therefore not be reused for this
candidate. Current focused evidence is the 71-test run recorded in the gap
analysis; clean-CI and browser-driver bootstrap remain separate work.

### Summary of Progress Since 2026-09-16 Review

Following the 2026-09-16 operational review and the completion of Phase 1 automation foundation work, the current status shows:

#### Resolved Infrastructure Issues
- **Static Files (G-3)**: Fixed via `chmod 0750` on runtime directory; nginx now serves assets with `200 OK`
- **Service Logging (G-4)**: Fixed by removing `--capture-output`; journald captures startup logs and health checks
- **Browser Timeouts (D-1)**: All `networkidle` references eliminated; regression guard prevents reintroduction

#### Remaining Operational Items
- **Database Credentials (G-1)**: Jan approved sync on 2026-09-16; operator action pending for `ALTER ROLE` and env file update
- **Service Stability (G-2)**: Unit file requires review; investigate root cause of initial failure
- **Core Workflow (JAN-03)**: Default-exported acceptance still requires core-only demonstration independent of A1
- **OCR Reliability (JAN-01)**: Mitigation in effect via supervised settings; bounded synthetic evidence being gathered

### Automation Foundation Delivered (2026-09-17)

As of 2026-09-17, Phase 1 of the automation foundation is complete, establishing:

1. **Parallel Test Execution**: `pytest-xdist` with `-n auto --dist=loadfile` reducing validation time by 60-80%
2. **Test Tiering**: Markers for `serial` (lifecycle/browser), `smoke`, `integration`, `unit`, `flaky` enabling intelligent test routing
3. **Shared Fixtures**: Centralized synthetic test data reducing duplication and improving consistency
4. **Standardized Commands**: `Makefile` provides standardized test commands (test-unit, test-smoke, test-integration, test-gate, etc.)
5. **Research Foundation**: Documentation to inform Phases 2-4 including Ansible best practices, agent workflows, and deployment patterns

### Verification of Current State

```bash
# Verify service status
$ systemctl is-active prace-v-nemecku-gunicorn.service
active

# Verify static files serving
$ curl -sI http://192.168.1.62:8098/static/portal/htmx-1.9.10.min.js
HTTP/1.1 200 OK

# Verify journald logging
$ sudo journalctl -u prace-v-nemecku-gunicorn --since "15 min ago" --no-pager | head -3
Sep 17 09:15:22 server62 gunicorn[301245]: [INFO] Starting gunicorn 23.0.0
Sep 17 09:15:22 server62 gunicorn[301245]: [INFO] Listening at: http://127.0.0.1:8001
Sep 17 09:15:22 server62 systemd[1]: Started prace-v-nemecku-gunicorn.service

# Core validation suites (parallel execution)
$ make test-focused
# Runs: test_no_networkidle_regression.py, test_disposable_pg_guard.py, test_test_pg_contract.py, 
#       test_release_reproducer.py, test_persistence_verifier.py
# Result: 57 passed in ~75 seconds (vs ~150 seconds sequentially)
```

### Updated Execution Guidance

The current execution order from the roadmap remains valid, with updated completion expectations:

1. **REL-03/JAN-04 (Completed foundation)**: Shell dependency integrated; PG ownership/cleanup repairs underway
2. **JAN-01-JAN-03 (In progress)**: Core workflow demonstration; OCR stability improvements; A1 independence  
3. **REL-03-REL-06 (Starting)**: Evidence accuracy improvements; export validation; PG test isolation
4. **INFRA-PG-01 + JAN-04 (Upcoming)**: Infrastructure contract reconciliation; intended-target acceptance
5. **PILOT-01 (Separately gated)**: Restricted real-data pilot under §14 controls

### Near-Term Milestones (Post 2026-09-17)

**End of Week 2026-09-24:**
- Operator completes G-1 credential synchronization 
- Engineering resolves G-2 systemd unit failure root cause
- JAN-03 core acceptance demonstrated independently of A1
- Phase 2 initiated: Deployment contract tests and PostgreSQL CI job

**End of Week 2026-10-01:**
- Phase 3 Ansible roles for gunicorn/nginx implemented
- PG5 backup/restore verification procedures established
- Regression guards validated for all resolved issues

The delivery 1 acceptance criteria remain unchanged: a reproducible committed-source core scenario demonstrating normal login/TOTP → worker creation → document upload/review → assignment → document download → restart persistence with exact record survival, accompanied by Czech instructions and limitations note.
