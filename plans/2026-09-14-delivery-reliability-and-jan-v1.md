# Delivery reliability and Jan core v1 — 2026-09-14

**Status**: active
**Milestone**: M0–M3; separately gated M5
**Parents**: [PLAN-INFRA](PLAN-INFRA.md), [PLAN-WORKERS](PLAN-WORKERS.md)
**Owner**: primary agent integrates; engineering owns source repairs; infrastructure owns live operations; Jan owns observed usability acceptance
**Authority**: user scope; [roadmap](../roadmap.md); existing ADR-001/ADR-002
**Audit baseline**: original audit `a48a1e843a3b59d783d3710dd414993964296368`; follow-up `4a38067` plus explicitly identified unstaged dependency/PG changes, 2026-09-16. Remote feature branch observed at `8d125f2ced67fced2206a470e9299d57761549e6`. These are dated observations, not release approval.

## Outcome, sources and expected results

Jan can complete normal login/TOTP → save a worker with optional facts unknown →
upload a protected document → review/correct OCR proposals → create/correct an
assignment → download the protected original. The same records, corrected facts,
relationships and source bytes survive restart on the intended PostgreSQL target.
Czech instructions, visible failures/retry and a short limitations note accompany
that demonstration. Operator acceptance is separate from automated acceptance.

Official A1 generation/issuance is outside v1. Existing drafts are optional;
A1 readiness, institution approval and PDF checks must not gate core acceptance.
Shared authorization, provenance, audit and storage remain required. Weekly budget
is unresolved business scope, not an engineering prerequisite. Legacy data transfer,
real-data activation, host mutations and CI activation are outside this audit.

| Question | Source | Expected evidence |
|---|---|---|
| What should ship? | Current roadmap/PRD and explicit user scope | Bounded core scenario and exclusions |
| Which facts are authoritative? | Authorized source revision and explicit human review | Actor/time/revision; OCR proposals never silently confirmed; unknowns remain unknown |
| What code is being evaluated? | Git object plus dependency/settings identity | Reproducible candidate; related uncommitted bytes cannot certify that object |
| What actually passed or failed? | Native receipts/logs and focused reproductions | Command, source identity, exit, duration, target label, proves/does-not-prove |
| What is running? | Fresh nonsecret service/route/build/database observations | Actual selected deployment and target; document claims alone do not establish it |
| Is it useful? | Jan's observed scenario | Recorded outcome, limitations, recovery instructions and next owner |

The user-supplied OpenCode transcript is a claim to audit, not evidence of completion.
Current conclusions below supersede its “packaging only”, “load-induced”, blanket
“FIXED” and publication claims where they conflict with inspected evidence.

Technical references checked for the proposed repairs: [Playwright navigation/readiness](https://playwright.dev/python/docs/api/class-page#page-goto) discourages `networkidle` as a testing readiness signal; [PostgreSQL psql options](https://www.postgresql.org/docs/18/app-psql.html#APP-PSQL-OPTIONS) prohibit mixing SQL and meta-commands in one `-c` argument. These explain API contracts; local receipts establish what happened here.

## Audit results — 2026-09-16

Private receipts and baseline snapshots: `runtime/portal/temporary/delivery-audit-20260916-moriz8mx/`.
The [delivery record](../docs/operations/git-delivery.md) owns publication and final
validation; detailed logs remain private. No host secret payload was read.

| Existing task | Verified result / remaining gap | Evidence and consequence |
|---|---|---|
| REL-03 / JAN-04 | **Specific dependency closed at `b687abe`:** shell setter and operator-target refusal are committed; broader candidate/PG acceptance remains open | Committed refusal/scope-gating tests pass; live `current_user`/`statement_timeout` on owned PG remains on the JAN-04 real-PG rows below |
| REL-03 | **Open: hook checks working-tree bytes.** Staged paths choose checks, but subprocess `cwd` is the mutable checkout; receipts do not bind the complete tested input set | `scripts/validate_change_packages.py::_run_command/_execute_checks`. Existing hook PASS is working-tree evidence, not committed-export evidence |
| JAN-04 | **Open: ownership is self-declared.** Workflow fixture writes its own disposable marker/record from the supplied target; guard runs at teardown, after migrations. Table-wide DELETEs remain | `tests/test_rehearse_workflow.py::_postgres_env/_write_disposable_ownership/_cleanup_pg_operator`. A synthetic configuration probe accepts a self-created record when lock success is mocked; this does not prove live exclusivity |
| JAN-04 | **Reproduced application defect: invalid lock probe.** `psql -Atc` receives both `\set` and SQL. It fails against a reachable isolated cluster and is misreported as transport/credential/lock blockage | `scripts/disposable_pg_guard.py::_try_exclusive_lock`; private `postgres-probe.json`: actual probe refuses, mixed command exit 1, plain-SQL control exit 0 (`t`, `t`). New Unix-socket-only cluster stopped successfully; no operator DB used |
| JAN-04 | **Cleanup regression closed (post-`2f58c65` review).** `psql_env` now preserves every caller key (no `os.environ` rebuild); `_cleanup_pg_operator` asserts `verdict["lock_key"]` is an `int` so a refused verdict fails closed instead of `KeyError`-ing into the destructive DELETEs. Isolated PG 18 `initdb` cluster: positive probe `acquired: True`, holder-transaction negative probe `acquired: False — already held` | Deterministic: `tests/test_disposable_pg_guard.py::test_psql_env_preserves_caller_target_and_ownership_keys` plus the existing guard suite, 129 passed. Broader: 153 passed across `test_rehearse_synthetic_site / test_settings_supervised_synthetic / test_run_collector_proposals / test_collector_execution / test_release_reproducer` |
| JAN-04 | **Closed at `c24a293` (`d0903a8`):** Guard psql chain now preserves every caller key in `values`, translates `PRACE_DB_SSLMODE/SSLROOTCERT` to `PGSSLMODE/PGSSLROOTCERT` and assigns `PGPASSWORD`. The post-`2f58c65` `KeyError('lock_key')` regression reproduced in an isolated subprocess-mocked probe is closed | `tests/test_disposable_pg_guard.py::test_psql_env_preserves_caller_target_and_ownership_keys`. Forwarded `PRACE_WORKFLOW_PG` and migration credentials remain to be retested on an owned PG with a live migrate/runtime role check |
| JAN-04 | **Partially closed at `c24a293` + incremental:** `resolve_test_postgres_target` now rejects explicitly exported blank/whitespace `DOCUMENT_TEST_PG_NAME` / `DOCUMENT_TEST_PG_USER` with an actionable `RuntimeError`. Empty-variable → SQLite fallback remains the documented default for unset partial targets | `tests/test_test_pg_contract.py::test_blank_variable_is_refused_with_actionable_message` and `test_whitespace_database_name_not_accepted`. Live owned-cluster normalization still open |
| JAN-01/JAN-02 | **Timeout cause unresolved.** First hook fails at document-detail `networkidle`, 20000 ms; captured `SERVER_ERROR_CATEGORIES: []`. Retry passes; runner is sequential | Failure `change-checks-dvp3wac9/check-8.stdout`, lines 52–61. Error names elsewhere in the log are printed test source, not observed server failures. No resource sample or request trace establishes load as cause |
| JAN-03 | **Partial core separation.** `a48a1e8` adds non-A1 correction and optional A1-fact filling. Core lifecycle still unconditionally requires `_rehearse_workflow_data_path.py` A1 preparation/reservation assertions | Sparse saving currently uses direct ORM creation, not a browser proof. Split the optional assertions while retaining a core incomplete-input scenario and shared controls |
| JAN-03 / REL-03 | **Open: default exported acceptance omits the core journey.** `run_release_reproducer.py::acceptance_commands` remains A1-heavy and does not execute the browser/restart lifecycle | Extend the existing entrypoint and receipt contract; do not advertise a proposed profile flag as implemented |
| REL-04 | **Open: overlap and broad selection.** Dependency selector emits a three-file lifecycle command; package emits five files. Exact-command dedup cannot merge them | First failed hook 674.08 s; retry 733.59 s, including shared suites 304.66 + 162.95 s; next hook 224.87 s. These are different attempts/scopes, not a measured optimization |
| JAN-04 / REL-03 | **Implemented but acceptance partial.** `a48a1e8` reads actual stored source bytes; verifier dedup reuses actual prior results | Keep these improvements. Standalone persistence verifier does not perform the restart; broad exception handling also needs a regression distinguishing unavailable DB from programming/schema errors |
| JAN-01 / INFRA-PG-01 | **Fresh bounded observations.** Installed allauth 65.19.1 matches its pin (earlier mismatch no longer observed). PostgreSQL unit running; application unit failed, MainPID 0; 8001 listener exists; selected EnvironmentFile loaded | Read-only unit/socket/package metadata only. No new DB authentication, route, secret separation, release approval or restore proof; those remain unverified |

Historical JAN-01 SQLite mitigation and JAN-02 download-redirect investigation
remain valid for their dated scope. Their successful SQLite runs do not close
PostgreSQL, routed-site, recovery or human acceptance. The original attempt is
retained beside successful retries; a pass does not diagnose the earlier failure.

## Implementation/dependency follow-up — 2026-09-16

The [review](../docs/research/2026-09-16-document-orchestration-review.md) checks the
new install report and source updates at `4a38067`. Earlier table entries about
probe syntax/forwarding/empty targets describe the initial `a48a1e8` audit; the
unstaged source now partly repairs them. Distinguish that progress from publication
and full effective-role/TLS/owned-target integration.

- `b687abe` closes the missing shell-file dependency, not every candidate requirement.
- `c24a293` (`d0903a8`) removes mixed meta/SQL, forwards workflow selection and
  migration credentials, maps TLS variables to `PGSSLMODE`/`PGSSLROOTCERT`, and
  preserves every caller key in `psql_env`. Subsequent incremental commits close
  the explicit empty/blank test-target gap and forward `PRACE_WORKFLOW_PG`.
  Guard/resolver/reproducer tests pass (47); live setup/workload/cleanup
  acceptance on owned PG remains open.
- Dependency pins match installed packages; `pip check` passes. Freeze/dry-run/imports
  do not prove a fresh install. Duplicate base/dev pins, open ONNX range, browser/model
  provisioning and inconsistent existing CI install commands need one tested contract.
- Three generated-document OCR cases passed with OS networking disabled, and 18
  isolated worker tests passed. Web intake queues durable OcrRun jobs for `process_ocr`;
  older inline-execution prose is corrected. Quality calibration/stage recovery remain
  OCR-CORE-10/11/13/14 follow-up. LangGraph is an optional measured comparison under
  that plan, not a new v1 prerequisite or a replacement for domain review services.

Native receipts/source identities live in
`runtime/portal/temporary/ocr-orchestration-review-20260916-3iu4h9nx/`.
No clean install, LangGraph implementation, live target or new human approval is claimed.

## Implementation backlog and execution order

All broad task IDs below remain open. This audit repairs planning/instructions;
it does not implement or certify the remaining application repairs. Capability
mapping is retained: REL-01–06 → JAN-VALIDATION; JAN-01 → JAN-ACCESS; JAN-02 →
JAN-WORKERS/JAN-DOCUMENTS/JAN-ASSIGNMENTS; JAN-03 → JAN-A1-OPTIONAL; JAN-04,
INFRA-PG-01, DB-MIG-1–7 and PILOT-01 → JAN-RUNTIME.

| Priority / ID | Next bounded work and owned paths | Validation / expected result | Owner |
|---|---|---|---|
| P0 REL-03 + JAN-04 | Retain the shell dependency integrated in `b687abe`; complete effective-role/timeout evidence and review target refusal at the disposable-test boundary. Own `scripts/rehearse_synthetic_site.sh`, affected settings and tests | Candidate contains dependencies; committed-source command-scope test proves migration role/timeout and ordinary runtime role/timeout. Refusal occurs before mutation | primary + runtime engineering |
| P0 JAN-04 | Repair provisioning-owned target identity, pre-migration verification, run exclusivity, cleanup scope and failure propagation. Own `scripts/disposable_pg_guard.py`, workflow fixture and guard tests | Dedicated disposable target; foreign/unowned target refused before migration; second run denied before writes; same-session cleanup verified with real PG; simulated cleanup failure reported. Consumer cannot mint its own authority | runtime engineering |
| P0 JAN-04 | Review/integrate the unstaged psql/forwarding/normalization repairs; fix `psql_env` losing supplied target/ownership and conflicting ambient TLS. Keep a single explicit connection contract through every subprocess | Isolated real-PG positive/negative lock tests; empty/whitespace/partial/contradictory targets rejected; `SELECT current_user` / `SHOW statement_timeout` in migrate/runtime; settings and libpq use intended target/TLS. No global migration-scope leakage into web/worker | runtime engineering |
| P1 JAN-01/JAN-02 | Replace `networkidle` at affected transitions with response/URL/domain-state assertions; preserve bounded synthetic failure evidence before cleanup. Own browser helper/lifecycle tests | Focused reproduction distinguishes timeout, HTTP failure, auth redirect and OCR state; evidence includes failing stage, elapsed time and relevant request/server categories without cookies/bodies. Controlled repeated runs assess reproducibility, not statistical reliability | workflow engineering |
| P1 JAN-01/JAN-02 | Complete normal access/recovery and core review behavior using existing services/templates. Preserve the currently matching dependency pin; do not repeat historical drift as current | Real login/TOTP/logout and documented recovery; role/action and cross-org deny cases for worker read/edit/archive/delete and document download; OCR proposal confirmation bound to exact revision/actor; stale edit refusal; duplicate retry one effect; actionable Czech pending/error/retry states. Reuse matching evidence, repair only reproduced gaps | access + workflow engineering |
| P1 JAN-03 | Separate optional A1 across sparse helper, lifecycle, reproducer, review UI and machine requirements. Extend existing entrypoints, not another runner | Core succeeds with optional A1 disabled/unavailable; required core failure exits nonzero; optional A1 reports its own failures. Sparse save through shipped UI with unknowns intact; denied download returns no bytes; corrected facts survive reload/restart | primary + workflow engineering |
| P1 REL-03 | Bind receipts to actual source/dependency/config/settings identity; guard related drift and stale reuse; preserve staged privacy checks | Synthetic Git fixture with partially staged helper/config proves unstaged success cannot certify index/candidate. Committed export drives the actual core journey. Persistence mismatch exits 1; unavailable environment exits 2; coding errors do not masquerade as environment blockage | evidence tooling |
| P1 REL-03/REL-05 | Reconcile `requirements.txt`, dev and snapshot constraints with existing bootstrap/CI callers. Keep tested versions; record browser/native/model assets and source/environment identity | Fresh private Python 3.13 environment from documented constraints passes `pip check`, isolated Django check, real offline OCR and synthetic browser core. Prove required assets available, classify optional tools, compare resolved versions; do not use installed-environment dry-run as clean-build evidence | environment + validation engineering |
| P1 REL-04 | Define shared compatible test units once; reconcile selector/package commands; preserve changed shared behavior integration | Selection-only regressions for docs/tooling/core/shared/A1/deletions/dependencies, with runner/settings/fixture identity. Record comparable before/after timings; no arbitrary speedup promise or bypassed mandatory hook | validation engineering |
| Parallel OCR-EXP-LG | Bounded LangGraph comparison per the orchestration review and `OCR-CORE-10/11/13 / optional experiment`. Run an isolated, synthetic-only measurement against the existing `process_ocr` worker plus a minimal Django stage-receipt variant and a thin LangGraph adapter using identical engines/models/corpus. Do not adopt into the canonical `venv`. Budget ≤ 2 engineering days, never delays JAN-01–04 | Mandatory cases (clean, missing/corrupt model, malformed input, timeout, crash before/after publish, duplicate/resume, cross-tenant resume, inactive reviewer, source replacement while waiting, restart during review, DB outage, retention deletion, graph-version change). Compare semantic field correctness and recovery semantics, not timing trophies. Refusal of duplicate/cross-tenant/stale/revoked resume is invariant; no automatic confirmation, no external traffic, no duplicate effect, no stale-source acceptance. Completed stages must not rerun during recovery. Record dependency/license diff and exact pinned versions; record checkpoint durability, rollback/drain behaviour and the data-class classification of graph state. If a graph benefit fails to clear those invariants, retain the current worker and surface stage-receipt work as the next binding layer | OCR engineering, primary reviews result, architecture owner records adopt/defer |
| Parallel INFRA-PG-01 | Reconcile existing credentials, supervisor/listener ownership, approved build/pin, route and target through returned infrastructure contract | Fresh intended-target authentication and health/build/engine evidence; operator-owned service recovery. Existing path-only deployment does not satisfy these checks. No guessed secrets, repin, restart or HBA reorder | infrastructure owner |
| Candidate JAN-04 | After repairs and selected-target availability, run one reproducible committed-source core scenario through intended route; normal runtime role, expected build/engine/target | Historical migrations/concurrency on owned PG; login/TOTP, upload/review/correction/download; deny/retry/incomplete cases; authorized restart with identical IDs/relationships/corrected values and source bytes; no reseed. Jan instructions and limitations attached | primary + runtime engineering, then Jan |
| REL-01 | Reconcile five refresh outputs from six existing summaries; account for all 71 input requirement rows through mapping/dedup/replacement/deferral | Meaningful capability IDs, resolving references, separate evidence layers; no invented human approvals. Do not restart the six analyses | packet integrator |
| REL-02 | Audit inherited `scripts/validate_project_refresh.py` before adoption; extend existing schema/CLI where sufficient | Invalid structure/refs, orphan/duplicate IDs, dropped coverage, cycles, contradictory states and unsupported approval provenance fail. Valid unverified material passes structure only; semantic review remains separate | evidence tooling |
| REL-05 | Map installed hook, framework config, GitHub and proposed GitLab CI to selectors/settings/checks/receipts | Coherent source proposal; inactive proposals cannot run accidentally; preserve required-check identities or document transition. Remote CI/settings unverified until observed. No new remote or CI activation | CI reviewer + primary |
| REL-06 | Reconcile skill/procedure claims with executable behavior; audit effective agent configuration only within scope | Skills distinguish desired contracts, actual limitations and available commands. Record effective version/instruction paths/permissions without secrets; one isolated synthetic edit/verify and one rejected false completion exercise the agent/verifier contract. Avoid incident-specific global rules | primary |
| DB-MIG-1–7 | Retain legacy transfer planning separately | Selected authority, mapping, dry-run reconciliation, idempotency, backup/restore and explicit cutover authority; no real-record transfer in this batch | engineering + primary |
| PILOT-01 | Restricted real-data pilot after usable core | Existing §14 access/storage/retention/recovery/capacity gates and scoped decision; A1-only requirements excluded from core; PG5 backup-plus-files restore separately demonstrated | operator/legal/sysadmin |

REL work may proceed alongside product repairs where independent; refresh-packet
cleanup is not a prerequisite for fixing a UI or database defect. Infrastructure
credential repair does not block pure contracts or an engineering-owned in-project
PostgreSQL test cluster. That cluster is not acceptance of the deployed target.

## Validation contract

| Layer | Execute / inspect | What it proves |
|---|---|---|
| Documentation and skills | Existing selected planning checks, relevant links/status consistency, whitespace and skill frontmatter; staged-content review | Coherent instructions and plan, not application runtime |
| Focused repair | Regression reproducing the changed behavior on identified source | That defect's behavior; no unrelated broad rerun |
| Integration | Affected real DB/storage/auth flows; owned isolated PG for PG-specific behavior | Actual interactions, including failure and cleanup; mocks alone cannot certify locking |
| Release candidate | Existing export mechanism extended to execute core browser/restart on explicit target and pinned inputs | Exact committed candidate on named environment; no automatic human approval |
| Operator / activation | Jan scenario and separate §14/PG5 evidence | Usability / authorization only within recorded scope |

Before a commit, inspect selected checks without running them; let the mandatory
hook execute once. Read its complete private report and failed command log before
retrying. A tool yield is not a deadline. Reuse evidence only when tested inputs
match; related working-tree drift invalidates candidate claims. Implement narrow
source-isolation protection under REL-03; do not declare the current hook index-tested.

Existing commands (use only for the relevant scope):
```bash
venv/bin/python scripts/validate_change_packages.py --staged
venv/bin/python scripts/validate_planning.py
git diff --cached --check
```
The planning check is already selected for these documentation paths; do not
pre-run it and then duplicate it through the hook. Future candidate profile syntax
must be documented after implementation. Current `scripts/release_reproducer.sh
<commit-sha>` is a supported regression export, not complete core-v1 acceptance.

Each result records command, cwd, native exit, duration, exact tested source,
dependency/settings identity, nonsecret target label, private log reference and
proves/does-not-prove. Separate implementation, validation, publication, deployment
and operator acceptance. Never hash secret-bearing configuration into evidence.
On a failure preserve the original result; rerun the smallest discriminating case
before paying for unchanged broad suites. A successful retry is additional evidence,
not a root-cause diagnosis. If two corrections leave disputed bytes unchanged,
return to the actual diff and a fresh bounded review rather than another PASS summary.

## Ownership and integration

Primary owns shared plan/roadmap/index, catalog and final integration. Assign named
source paths before parallel edits; tests must use separate databases, roots, ports
and cleanup targets. At task handoff include desired observable behavior, current
source, changed paths, before/after, evidence, residual risks and next owner.
Do not race another session's staging/commits. Preserve unrelated inherited edits.

Keep procedures in existing skills, executable logic in canonical scripts,
architecture in ADRs, scope in roadmap/PRD, current TODOs here and delivery evidence
in one record. Preserve all 34 top-level catalog entries and existing approvals;
regenerate derived assets only when their source changes. The inherited institution
edits, session helpers, experimental refresh artifacts and quarantined OCR benchmark
are not adopted merely because they share a dirty checkout.

## Historical references and limitations

The September 14–15 repair/checkpoint narrative remains in Git history and the
[delivery record](../docs/operations/git-delivery.md). Architecture ADR-001/002 and
historical bounded synthetic evidence are retained; this audit retracts broad
completion claims rather than overwriting their underlying receipts. Path-only
infrastructure deployment below is a distinct historical event. No credential,
service, release activation or human approval follows from these document updates.

## Runtime path retirement checkpoint — 2026-09-16

Operator selected `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env` as the infra-owned EnvironmentFile.
See [runtime contract](../docs/operations/runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
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

## Verification run — 2026-09-16

Six focused regression suites run against the committed source at `c1fced1`:

| Suite | Result | Evidence |
|---|---|---|
| `tests/test_disposable_pg_guard.py` | 16 passed, 0 failed | Guard + `exclusive_cleanup_sql` + `psql_env` + held-lock tests |
| `tests/test_test_pg_contract.py` | 14 passed, 0 failed | Blank-target rejection, TCP password requirement, operator-name refusal |
| `tests/test_settings_supervised_synthetic.py` (migration/scope) | 9 passed (+62 deselected) | `PRACE_MIGRATION_SCOPE=1` gate, migration user/password, `statement_timeout` |
| `tests/test_release_reproducer.py` | 17 passed, 0 failed | Receipt sanitization, `PRACE_WORKFLOW_PG` forwarding, env forwarding |
| `tests/test_persistence_verifier.py` | 10 passed, 0 failed | Source-byte verification, db-hash vs source-byte failure classification, exit-2 blocked |
| `tests/test_rehearse_workflow.py` | 4 passed, 0 failed | Core journey with `assignment_corrected` stage, `optional-a1` profile separation |

**Total: 70 passed, 0 failed.** No false positives, no silent skips, no unexpected passes. The two files that differ from the published base `c24a293` are exactly `scripts/run_release_reproducer.py` (+1 line forwarding `PRACE_WORKFLOW_PG`) and `portal/test_pg_contract.py` (+9/-2 lines adding blank-target rejection). The other changed files match `c24a293` exactly.

### Live-state verification (server62, 2026-09-16)

PostgreSQL 18.3 is running. Role `prace_synth_app` exists with `rolcanlogin=true` and a non-null password hash. The `PRACE_DB_PASSWORD` stored in `.runtime-config/gunicorn.env` (length 44) does **not** authenticate against the live role over `scram-sha-256` TCP or `md5` local socket — 9 `FATAL: password authentication failed` entries in `/var/log/postgresql/postgresql-18-main.log` across ~90 minutes on Sep 16. The systemd gunicorn unit is `failed (Result: signal)` since Sep 14; a divergent manual instance (PID 2681143, user `prace-s+`, workers 2) serves on `127.0.0.1:8001`. Static files are uncollected (`static/` empty, Sep 11 log shows 404s for `htmx-1.9.10.min.js` and `tailwind-2.2.19.min.css`). `journalctl -u prace-v-nemecku-gunicorn` is empty — `ProtectSystem=strict` + `--capture-output` blocks journald. The unit file's filesystem `Birth` (Sep 16 02:02) is after the first failure (Sep 14 03:41) — most probable cause: operator repair attempt without addressing root cause.

### Residual open items

| ID | Item | Status | Owner | Evidence |
|---|---|---|---|---|
| G-1 | `prace_synth_app` password desync | **Open (active)** | Operator | 9 FATAL entries in PG log; `psql` test fails with env password |
| G-2 | systemd unit failed; manual gunicorn diverges | **Open** | Operator (after G-1) | `systemctl status`; `ps` shows `prace-s+` and `--workers 2` |
| G-3 | static files 404 / empty static dir | **Open** | Engineering | `ls static/` empty; `/tmp/gunicorn.log` 404s |
| G-4 | journalctl empty for unit | **Open** | Operator | `journalctl` empty; unit has `ProtectSystem=strict` + `--capture-output` |
| D-1 | networkidle flake under hook load | **Open** | Engineering | 19 `networkidle` references remain in `_rehearse_workflow_browser.py`; `_wait_networkidle` still uses 20 000 ms |
| JAN-01 | OCR HTTP 500 flake | Mitigation in effect | Engineering | WAL/IMMEDIATE/busy-timeout in supervised settings; bounded-set evidence |
| JAN-03 | Default-exported core journey | **Partial** | Engineering | `run_release_reproducer.py` acceptance commands still A1-heavy |
| SMTP | Python 3.13 `smtpd` removal | **Broken** | Engineering | `/tmp/smtp.log`: `No module named smtpd`; `/tmp/smtp_server.log`: port 25 bind `PermissionError` |

Full verification report: `docs/operations/s62-verification-report-2026-09-16.md`. Full triage with Ansible playbook and meta-pattern library: `docs/operations/s62-comprehensive-triage-and-fix-playbook-2026-09-16.md`.
