# Delivery reliability and Jan core v1 — 2026-09-14

**Status**: active
**Milestone**: M0–M3; separately gated M5
**Parents**: [PLAN-INFRA](PLAN-INFRA.md), [PLAN-WORKERS](PLAN-WORKERS.md)
**Owner**: primary agent integrates; named engineering agents own bounded paths
**Authority**: current user scope; [roadmap](../roadmap.md); existing ADR-001/ADR-002
**Baseline**: repository HEAD 00786f74fb5321900f9f293f989447e5d7bd8016 on review; inherited dirty/untracked work preserved. This plan is implementation-ready, not implementation acceptance.

## Review checkpoint — 2026-09-15

This is a documentation/review checkpoint only: it claims no code repair,
credential change, service change, deployment or operator acceptance. It maps
the confirmed findings onto the existing task IDs; no new plan, catalog ID or
competing roadmap is introduced. The 2026-09-14 bounded JAN-01/JAN-02 repair
record and all historical evidence remain valid for their own scope.

| Task | Required update and acceptance |
|---|---|
| JAN-01/JAN-02 | Investigate the OCR HTTP 500 and the download mismatch as separate defects; in each, distinguish authentication redirects from file corruption. Demonstrate normal login and protected original download before broader acceptance is claimed |
| JAN-03 | Record the core/optional-A1 profiles as partially implemented; remove remaining A1-specific requirements from core acceptance |
| JAN-04 | Repair target forwarding, verified disposable cleanup, migration credential scope and the effective statement timeout; verify actual file bytes and exact records after restart |
| REL-03/REL-04 | Eliminate manufactured PASS results and incorrect test deduplication; bind every receipt to the actual tested inputs |
| REL-06 | Reconcile skill instructions with the executable configuration and observed cleanup behavior |
| INFRA-PG-01 | Next action changes from presumed new provisioning to inspection/reconciliation of the existing infrastructure and return of the completed response contract |

Observed on 2026-09-15 (see the
[sysadmin reconciliation report](../docs/operations/sysadmin-postgresql-reconciliation-2026-09-15.md)):
PostgreSQL was observed running, but configured application authentication
failed; the Gunicorn systemd unit was failed while separate Gunicorn processes
carried no PostgreSQL target variables. Application-side defects and
infrastructure reconciliation are both open; neither subsumes the other.

Status after the 2026-09-16 investigations (see
[git-delivery.md](../docs/operations/git-delivery.md)):

- **JAN-01** — the OCR `OCR_STATUS_HTTP_500` is a genuine server 500 (write
  contention under gunicorn + SQLite), not an authentication redirect. The
  supervised-settings mitigation (`WAL`, `IMMEDIATE` writes, busy timeout 20)
  is in effect and three consecutive full journeys produced zero 500s; the
  historical reproduction was flaky, so this stays an investigation/mitigation
  record, not a statistical fix claim.
- **JAN-02** — the protected-download "bytes differ" failure was an
  authentication-redirect artifact, not file corruption. Page-context fetch
  served the exact uploaded PNG bytes (200, `image/png`, 36462 B, matching
  `Document.sha256`, `document.downloaded` audited), while Playwright's
  `APIRequestContext` drops the `Secure` session cookie over plain loopback
  HTTP and silently followed the login redirect (200 HTML). Stage 9c now
  fetches through the real browser session and asserts status, non-HTML type,
  exact size and SHA-256; the canonical workflow test passes (core profile).
- **JAN-03** — core/optional-A1 profile separation verified end-to-end at
  runtime: core requires only its non-A1 stage set and records `a1_skipped`;
  optional-A1 exercises the full A1 stages.
- **INFRA-PG-01 (manual re-verification, 2026-09-16 on `server62`)** — the
  cluster is online (`postgresql@18-main`, `pg_isready` 127.0.0.1:5432
  accepting), roles include `prace_synth_app`, and databases
  `prace_synthetic` + `prace_synthetic_test` exist. TCP `scram-sha-256`
  authentication with the configured `/etc/prace/env` password still fails
  (`password authentication failed`) — the credential mismatch is confirmed
  directly, not inferred. The orphan gunicorn (PID 2681143, user
  `prace-synthetic`, bind 127.0.0.1:8001) continues to run with no
  `PRACE_DB_*` variables and a SQLite `db.sqlite3` in
  `runtime/portal/supervised-synthetic`; both remain sysadmin-owned.
- **Tooling audit (2026-09-16, with committed fixes)** — engineered defaults
  that could silently invent or guess DB targets were replaced by fail-closed
  contracts: test PG target `_postgres_env` (no invented password/defaults),
  `DOCUMENT_TEST_PG_PASSWORD` support with a required password for TCP test
  targets, producer forwarding of the caller's real `PRACE_DB_*`/
  `DOCUMENT_TEST_PG_*`/`PGPASSWORD` into the exported acceptance run, and an
  all-or-none `PRACE_DB_*` guard plus effective-target banner in
  `scripts/rehearse_synthetic_site.sh`. These harden JAN-04 target
  forwarding; they do not close JAN-04 (the credential reset and supervision
  reconciliation remain INFRA-PG-01).

Execution order: application repairs (JAN-01–JAN-04) and sysadmin
reconciliation (INFRA-PG-01) proceed independently; then one committed-source
core acceptance run; then Jan's observed use. Nothing in this checkpoint
substitutes for that acceptance, and an infrastructure response alone cannot
close JAN-04.

## Outcome and limits

Deliver a truthful handoff and a usable Jan workflow, with less repeated validation.
Normal login/TOTP → worker → protected document/OCR review → assignment/correction →
protected source-document download → durable persistence is required.
Official A1 generation/issuance is outside v1; existing drafts are optional.
Do not make complete A1 fields, PDF review or institution approval prerequisites
for worker saving or core-v1 release. Weekly-budget inclusion remains unresolved.

No new top-level catalog IDs, blanket gate approvals, host changes, new remotes or
CI activation. Draft/source changes are reviewable engineering work; publication
that changes active CI behavior must follow existing CI authorization.
Do not commit inherited session reports/helpers or institution edits without their
own sanitized review. Preserve the quarantined OCR benchmark test.

## Implementation backlog

Tasks remain open except the bounded JAN-01/JAN-02 repair below. Broader task
acceptance is not implied by this repair. Audit leads are not automatically defects.

| ID / capability | Work and reason | Acceptance / dependency | Owner |
|---|---|---|---|
| REL-01 / JAN-VALIDATION | Rebuild the five refresh outputs from the six existing summaries. Account for all 71 input requirement rows through dedup/replacement/deferral; create meaningful capability IDs, separate evidence states, no invented human approvals | Every input row mapped or explicitly dispositioned; file refs resolve; Jan core scope consistent; semantic reviewer checks final files. No dependence on a new tool | packet integrator |
| REL-02 / JAN-VALIDATION | Add a small deterministic refresh validator, reusing existing jsonschema/CLI conventions; no LLM service. Validate structure/references/coverage, not prose keywords as acceptance | Invalid JSON, missing/orphan/duplicate IDs, unresolved/cyclic hard deps, dropped requirements, missing/unresolvable approval provenance, contradictory structured states and source-only evidence labeled runtime PASS fail. Resolve approval references against authoritative records; semantic review checks their meaning/authenticity. Valid partial/unverified output succeeds structurally without claiming acceptance | evidence tooling |
| REL-03 / JAN-VALIDATION | Bind runner receipts to tested source, dependency/config identity and evidence mode; preserve staged privacy checks | Partial staging cannot be certified as index-tested when checks used worktree bytes; related helper/config drift detected. Regression uses a synthetic temporary Git repo, never inherited staging. Reuse committed-export mechanism for release evidence | evidence tooling after REL-02 |
| REL-04 / JAN-VALIDATION | Resolve compatible test units once; fix observed J4 overlap, reversed A1 target order, delivery-doc overdispatch and smoke-test underdispatch; add reviewed refresh-document ownership | Selection-only cases show correct commands for docs/tooling/worker/shared-service/A1/deleted-test changes; changed shared behavior retains integration. Timings recorded before/after on comparable inputs, no promised arbitrary speedup | validation selection |
| REL-05 / JAN-VALIDATION | Inventory installed hook, framework config, GitHub and proposed GitLab CI, selectors, pins and actual command outputs. Prepare coherent CI source delta | One trigger→selector→runner/settings→test units→receipt map; disabled proposals cannot run accidentally; preserve required-check identities or document required transition. Current remote settings/runs unknown until read | CI reviewer; primary integrates |
| REL-06 / JAN-VALIDATION | Audit effective OpenCode config/rules/skill discovery and refine only persistent procedure gaps | Record version, loaded instruction paths, agent/tool permissions without secrets. One tiny synthetic edit/verify task proves tools execute; one deliberately false completion is rejected by verifier. Skills link canonical commands and distinguish optional A1 | primary, after evidence protocol settled |
| JAN-01 / JAN-ACCESS | Reproduce normal login/TOTP/logout/recovery through intended middleware/proxy. Verify role×action and tenant isolation for worker read/edit/archive/delete; repair confirmed gaps | Normal browser login, explicit denied role/cross-org cases, legitimate operator succeeds; recovery path documented. Test-client cookie injection is not onboarding. Reconcile allauth pin/install drift before new auth acceptance | access engineering |
| JAN-02 / JAN-WORKERS / JAN-DOCUMENTS / JAN-ASSIGNMENTS | Verify incomplete worker save, OCR proposal/review revision, corrections/retry, assignment and protected source-document download; repair confirmed UI/service defects | Sparse worker saved with unknowns intact; OCR not silently confirmed; duplicate retry no duplicate effect; correction persists; denied download yields no bytes; actionable Czech error/loading/stale states | workflow engineering |
| JAN-03 / JAN-A1-OPTIONAL | Split core-v1 acceptance from optional A1 in journey stage definitions, review surface, release verifier, catalog/plan semantics and skill | Core can pass with optional PDF unavailable, without falsifying A1 PASS; required core-stage failure exits nonzero; optional A1 execution still reports its own failures; shared auth/storage/revisions and §14 remain enforced. Depends on stable JAN-01/02 interfaces | primary with workflow owner |
| JAN-04 / JAN-RUNTIME | Prove intended PostgreSQL target, migrations, normal routed browser workflow and exact restart persistence; fix standalone persistence script/exit behavior if reproduced | Explicit engine/target/build identity, historical migration and concurrency evidence, same row IDs/source-document hashes after restart; target unavailable reported as unverified/blocked environment, not SQLite PASS. One committed-source candidate acceptance after JAN-01–03; application-side recipe ready, infrastructure contract awaited for target acceptance | runtime engineering + authorized host owner |
| INFRA-PG-01 / JAN-RUNTIME | Issue and publish the infrastructure request for a private PostgreSQL target; await the servers-infra-core response with the completed contract. **2026-09-15 review checkpoint:** the next action is inspection/reconciliation of the existing infrastructure and return of the completed response contract — not presumed new provisioning. See the [sysadmin reconciliation report](../docs/operations/sysadmin-postgresql-reconciliation-2026-09-15.md) | `docs/operations/servers-infra-core-postgresql-request.md` v1.0 published, status request—awaiting infrastructure response, contract template ready for completion; sysadmin report forwarded through the user, response returned into the template | application team forwards to servers-infra-core |
| DB-MIG-1–7 / JAN-RUNTIME | Retain existing-data transfer and real-data migration planning for later work; do not implement SQLite-to-PostgreSQL copying in this increment | Planning retained: selected source authority, field mappings, dry-run reconciliation, provenance, idempotency, backup/restore and explicit cutover authorization required before any transfer; no automated SQLite-to-PG copying, no import of real worker records, no cutover in this batch | engineering + primary, separately gated |
| PILOT-01 / JAN-RUNTIME | Prepare scoped restricted real-data pilot after usable core | Backup/restore, TLS/access/storage, retention/deletion and §14 decisions for selected org/target; Jan limitations/onboarding; no inherited A1-only prerequisite silently blocks core | operator/legal/sysadmin |

REL-02 proposed files: `scripts/validate_project_refresh.py`,
`tests/test_validate_project_refresh.py`, and a schema beside the existing work-order
template if reusing it is insufficient. These files/commands are **not implemented
by this planning checkpoint**. Prefer extending existing entrypoints if that is
smaller. Avoid adding a second general-purpose test runner.

## JAN-01/JAN-02 bounded repair — 2026-09-14

Implemented: HTTP persists pending OCR work; the explicit organization/actor worker
consumes committed rows sequentially with existing claim/token fencing and lease
recovery. The inbox command retains terminal synchronous receipts. Rehearsal owns
both web and worker start/stop/restart. The Czech page exposes refresh, completion,
failure and bounded retry. Browser interactions use native selection and observed
completion, with explicit submission navigation waits.

Worker edit/create state transitions cannot bypass archive permission; permanent
hard deletion stays denied pending a separately authorized policy. Legitimate
ordinary updates remain allowed. Focused negative tests and SQLite browser/lifecycle
checks exist; delivery-record receipts bind final integration results to source.
JAN-01/JAN-02 remain partial overall: authentication recovery/pin reconciliation and
full agreed workflow acceptance are not established by this repair alone.

JAN-03 optional-A1 profile separation remains open; no new core-only CLI flag is
advertised. JAN-04 requires committed-source PostgreSQL/routed-site and exact-row
acceptance. REL-01/REL-02 refresh reconciliation is separate and not claimed fixed.
No host deployment, systemd change, activation or human approval follows.

## Parallel waves and file ownership

One batch means one dependency-aware delivery effort, not one giant commit.

- **Wave A:** packet integrator owns only the five consolidated refresh files;
  evidence tooling owns proposed refresh schema/validator/test; CI reviewer reads
  workflows/config and proposes a diff without editing shared catalog files.
  Product reproduction can proceed in isolated synthetic roots.
- **Wave B:** after REL-02, evidence tooling owns runner/receipt tests (REL-03).
  Selection agent owns selector modules and selector tests (REL-04).
  Primary alone integrates `change-packages.yml`, `scripts/validate_planning.py`,
  AGENTS, roadmap/index, approvals/catalog and delivery record.
- **Wave C:** access owner has named auth/settings/worker-view files;
  workflow owner has named document/assignment/template files; runtime owner has
  rehearsal/persistence scripts. Primary assigns actual paths after reproduction.
  If both need `portal/release1a/views.py` or `services.py`, sequence those edits
  or use isolated source checkouts and integrate once. Use separate test DBs/ports.
- **Wave D:** primary integrates JAN-03 scope changes and reviews; one candidate
  acceptance JAN-04. Operator observes usable workflow; pilot authority separate.

Use at most three simultaneous source-editing lanes on this shared host until
resource evidence supports more. Parallel tests must not share runtime roots,
database names, ports, caches, credentials or process cleanup targets. This is an
engineering default, not a permanent throughput limit.

## Completion protocol and report contract

At task start: read current scope, inspect inherited diff/staging, name the desired
observable behavior, identify owning paths and one acceptance command/scenario.
Record assumption/unknown facts separately. A copied TODO list is not evidence.

Every task report contains:
`task_id, source_requirement, changed_paths, before_behavior, after_behavior,
source_identity, validation[], residual_risks, next_owner`.
Each validation includes:
`command_argv, cwd, executed, exit_code, elapsed_seconds, result,
tested_source_identity, dependency_config_identity, log_reference, proves,
does_not_prove`. Do not include secrets, session cookies, source PII or raw env dumps.

A source identity includes baseline HEAD plus the actual selected tree/file hashes
and mode (working_tree/index/committed_export). Hash dependencies/settings without
publishing secret-bearing values or low-entropy secret fingerprints. Record runtime
target using a nonsecret label. A live-target receipt additionally needs observation
time, deployed build and environment identity. Hashing a report cannot establish
the truth of its claims.

Use states per layer: implementation, validation, publication, deployment and
operator_acceptance. Evidence-only inspection cannot become runtime PASS.
A missing target is unverified, not “not deployed.” A recommendation is not Jan
approval; an approval needs actor, scope, time and authoritative evidence.
Machine structural validation cannot certify prose or business acceptance.

After a rejected review, return finding → actual diff → affected evidence.
If the same disputed file hash is unchanged, explain why the finding is invalid or
keep it open; do not claim it was fixed. After two unchanged failed correction
attempts, switch integrator/fresh bounded context and inspect raw outputs rather
than generating another completion summary. Do not retry a costly unchanged suite.

## Validation tiers and execution

- **Fast documentation:** scoped link/schema/consistency/diff checks.
- **Focused code:** one changed-behavior regression; retain a failure regression
  where it protects a meaningful contract.
- **Integration:** shared authorization/storage/migrations/dependencies use the
  appropriate Django runner/settings and isolated PostgreSQL where required.
- **Candidate:** one exported committed-source core journey. Optional A1 regression
  only when its source changed or when explicitly evaluating that optional capability.

Before a commit, let the mandatory hook run selected checks once; do not duplicate
with a pre-run of `--run-checks`. Read its private `VALIDATION_REPORT` and check
logs before retrying. Keep progress visible; do not kill a healthy process at a
tool yield deadline. Detect hangs by elapsed time/progress and process state, not
absence of a final line. Preserve exit status; no `| tail` masking.

Existing commands, used only for their stated scope:
```bash
venv/bin/python scripts/validate_planning.py
venv/bin/python scripts/validate_change_packages.py --staged
git diff --check
env -u DJANGO_SETTINGS_MODULE -u PRACE_RUNTIME_ROOT venv/bin/python -m pytest tests/test_validate_change_packages.py tests/test_release_reproducer.py -q
```
The last command is for changes to those runner/reproducer contracts; it is not a
mandatory documentation check. Core journey profile/CLI syntax will be documented
with JAN-03 implementation; do not advertise a proposed flag as working.

## Structure and governance disposition

| Path/scope | Disposition |
|---|---|
| roadmap.md, prd.md, plans/INDEX.md | Current scope/sequence/owners; updated at meaningful checkpoint |
| This plan | Single bounded current backlog; no parallel replacement roadmap |
| Five refresh outputs | Repair in place; handoff summarizes actual catalog/requirements; six agent inputs retained as dated evidence |
| scripts/validate_change_packages.py and selectors | Keep canonical runner; repair observed contracts |
| scripts/pre-commit + installer | Keep effective canonical hook; reconcile competing framework instructions |
| .pre-commit-config.yaml | Audit/retire or deliberately integrate; do not install a replacement hook over canonical validation |
| .github/workflows/ci.yml | Existing CI: prepare synchronized selection/trigger delta; remote activation/required-check changes separate |
| .gitlab-ci.yml | Inactive proposal in an executable location: prepare explicit nonactivation guard/disposition before use |
| .agents/skills/synthetic-portal-delivery/ | Keep canonical procedure; add core-v1 vs optional-A1 scope after scripts support it |
| .agents/skills/a1-pdf-production/ | Keep separate optional/operator A1 capability; no official-PDF v1 prerequisite |
| .opencode/agents/free-eval-* and experimental research skill | Separate evaluation lane; not generic delivery agents or v1 prerequisites |
| docs/operations/servers-infra-core-postgresql-request.md | Infrastructure request v1.0; application team forwards, does not send automatically; response feeds JAN-04 |
| docs/operations/sysadmin-postgresql-reconciliation-2026-09-15.md | Sysadmin reconciliation report (2026-09-15 observations); user forwards, does not send automatically; response feeds INFRA-PG-01 and JAN-04 |
| Inherited session helpers/reports, institution edits, OCR benchmark test | Preserve; sanitize/classify/reproduce before adoption, no blind stage or deletion |

Update AGENTS only for stable project-wide policy or recurring failure prevention.
Put command procedures in the owning existing skill, implementation in scripts,
architecture changes in ADRs, scope/priority in PRD/roadmap, measured output in private
receipts plus one concise delivery entry. Audit overlaps whenever a runner, workflow,
selector, dependency pin or instruction source changes; broader inventory once at
this reset and at release checkpoints, not on every edit.

## Completion of this planning checkpoint

Roadmap, parent-plan pointers and PRD scope are updated; the research/audit and this
work order are prepared. Implementation tasks remain open. Machine gate/UI/catalog
scope reconciliation belongs to JAN-03; no historical human receipt is rewritten.
