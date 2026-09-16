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

## Post-audit incremental repair — 2026-09-16

A bounded follow-up commit closes two audit items the prior table marked as
partial. Identified files and added tests:

- **F-2 empty/whitespace DB-name and role:** `portal/test_pg_contract.py`
  `resolve_test_postgres_target` now rejects an explicitly exported
  `DOCUMENT_TEST_PG_NAME` or `DOCUMENT_TEST_PG_USER` whose value is blank or
  whitespace (actionable `RuntimeError` naming the variable); previously such an
  explicit set fell through to an empty PostgreSQL name/role and produced a
  silent connection error. New unit coverage:
  `tests/test_test_pg_contract.py::test_blank_variable_is_refused_with_actionable_message`
  and `test_whitespace_database_name_not_accepted` (47 passed across the
  contract/guard/reproducer suites in 3.06 s).
- **F-4 exported acceptance environment chain:** `scripts/run_release_reproducer.py`
  now forwards `PRACE_WORKFLOW_PG` into the exported acceptance environment
  alongside `PGPASSWORD` and the migration/secret/runtime keys. The reproducer
  test `tests/test_release_reproducer.py::test_prace_workflow_pg_forwarded_when_set`
  asserts the forwarded value equals the caller's `PRACE_WORKFLOW_PG`.

The pre-existing plan-file `P0 new regression: psql_env rebuilds from ambient
environment and loses the supplied fixture target/ownership` paragraph is also
closed at `c24a293` (`fix: psql_env preserves caller target/ownership for cleanup
probe`, `d0903a8`); `psql_env` now reads only the supplied `values` dict
(`dict(values)`) and the unit test
`tests/test_disposable_pg_guard.py::test_psql_env_preserves_caller_target_and_ownership_keys`
pins that contract.

Remaining open items (F-1 settings `cmd_migrate` shell setter on owned PG,
F-4 full lifecycle ownership + real lock/cleanup negative cases + libpq TLS
end-to-end, F-5 routed-site recovery, F-6 INFRA-PG-01, JAN-01 OCR flake root
cause, JAN-03 default-exported core journey) are not closed by this commit and
remain in the plan and delivery record.

## Architect diagnostic dossier — outstanding engineering problems

Each problem below names what was observed, what evidence exists in the repo,
what evidence is **missing** for a complete fix, the official docs / community
sources that informed the proposed fix variants, and a recommended next step
the architect can approve or redirect.

### D-1: Journey `networkidle` flake at `/documents/1/`

**Observed.** First mandatory-hook run failed at
`tests/_rehearse_workflow_browser.py` navigating to `/documents/1/` with
`wait_until="networkidle"` and the default navigation timeout (`Page.goto:
Timeout 20000ms exceeded`). `SERVER_ERROR_CATEGORIES: []`, no gunicorn-side
error, runner is sequential. Identical retry passed in 239.28 s. The change
the flake exposed is not on `/documents/<pk>/` itself; it is the test's
readiness signal.

**Evidence in repo.**
- `runtime/portal/temporary/change-checks-dvp3wac9/check-8.stdout` lines
  52–61 — failed run.
- `runtime/portal/temporary/change-checks-3wz11m3j/check-8.stdout` — passed
  retry (239.28 s).
- `scripts/validate_change_packages.py::_execute_checks` — sequential loop,
  no `ThreadPoolExecutor` / asyncio gather.
- `tests/_rehearse_workflow_browser.py` — `page.goto(..., wait_until="networkidle")`
  at the document-detail navigation.

**Missing evidence.**
- No resource sample (CPU, RSS, gunicorn worker handle state, socket backlog)
  captured at the moment of failure.
- No chromium `--enable-precise-memory-info` / `--disable-gpu` / `--no-sandbox`
  diagnostic run.
- No reproduction under controlled parallelism; the flake is not characterised
  beyond "first attempt after the two heavy suites, retry passes".

**Official sources.**
- Playwright docs explicitly mark `wait_until="networkidle"` **DISCOURAGED**
  for testing and recommend relying on web assertions instead
  (https://playwright.dev/python/docs/api/class-page → `goto` option
  `wait_until`; same wording under `wait_for_load_state`).
- The 500 ms internal idle window is not user-tunable. Closed-as-not-planned
  feature request for a configurable idle interval: playwright #41190.
- Default navigation timeout in current Playwright is **30 s**, not the 20 s
  the failing log showed; the 20 s number is a Puppeteer-era artefact.
  Override per-page with `page.set_default_navigation_timeout(ms)`.

**Community / GitHub issues related to the symptom.**
- playwright #41513 (closed Jul 2026, v1.62): SSE/EventSource hangs networkidle
  because the long-lived stream is in the per-frame inflight set.
- playwright #37226 (closed not-planned Aug 2025): WebSocket stays alive so
  networkidle never resolves — same shape, different protocol.
- playwright #42598 (closed completed Sep 14 2026): driver counter
  inconsistency around `DOMContentLoaded` can leave a frame with an empty
  inflight set but no running idle timer; subsequent `WaitForLoadStateAsync(
  LoadState.NetworkIdle)` times out.
- No public issues link `networkidle` failures to Django or gunicorn
  specifically (searches `networkidle django` and `networkidle gunicorn`
  return zero relevant results).

**Worker-saturation hypothesis (assessed against gunicorn docs).** With
`gunicorn --workers 2`, a slow request on the *current* worker blocks
`Network.loadingFinished` until the response body is fully written; the
500 ms idle window cannot begin. A *different* worker being busy is invisible
to Chromium's inflight counter — it never sees that request. The hypothesis
is therefore plausible **only** for the worker that is currently serving
the journey's `/documents/<pk>/` view. Sources:
https://docs.gunicorn.org/design/ (sync workers; no keep-alive) and
https://docs.gunicorn.org/reference/settings/ (`workers`, `keepalive`,
`timeout`).

**Fix variants ranked.**
1. **(Recommended, smallest diff.)** Replace `wait_until="networkidle"` at
   every `page.goto` in `tests/_rehearse_workflow_browser.py` with
   `wait_until="load"` (the default `Page.goto` setting) plus an explicit
   `page.wait_for_selector("<view-stable-element>", state="visible")` or
   a web-first assertion targeting an element rendered by the destination
   view. The Django/journey views all render a stable title/H1 that can be
   awaited. This is the docs-recommended pattern and sidesteps the
   `networkidle` predicate entirely.
2. **Replace with `page.expect_response(...)` for the specific HTML response**
   for each `goto`. More verbose but gives precise assertion surface.
3. **Increase navigation timeout** (`page.set_default_navigation_timeout(60000)`)
   AND replace `networkidle` with `load`. Bump alone is masking and is not
   recommended by the docs.
4. **Capture diagnostic evidence first.** Add a single `--trace` / Chrome
   trace or `psutil` sample at the failing navigation so future failures
   are reproducible and bounded (one extra journey run, ~120 s). This is
   a precondition for any variant chosen.

**Next step for the architect.** Approve variant 1 with a precondition of
variant 4 once; then variants 1 and 4 as one committed-source increment.
Variant 2 is the fallback if a stable element cannot be identified at a
specific `goto` (none of the audited journey transitions have this problem).

### D-2: INFRA-PG-01 — operator-owned PostgreSQL not accessible to application

**Observed.** Manual `psql`/`pg_isready` on `127.0.0.1:5432` succeeds;
password authentication for `prace_synth_app` returns `FATAL: password
authentication failed`. Rehearsal Gunicorn unit `failed/MainPID 0`; an
orphan listener on `127.0.0.1:8001` (since Sep 14) is not the supervised
synthetic unit. Secret separation, approved build pin and routed-site
authentication not retested.

**Evidence in repo.**
- `docs/operations/git-delivery.md` row "Manual PostgreSQL verification and
  export-script audit — 2026-09-16 (s62)" — manual `pg_isready` and
  `psql` outputs as plain text labels only; no secret values recorded.
- `docs/security/real-data-rules.md` §14 — §14 gate unchanged.
- `INFRA-PG-01` rows in the active plan and FEEDBACK report — operator-owned.

**Missing evidence.**
- Current hashed value of `RETIRED_RUNTIME_CONFIG` `PRACE_DB_PASSWORD` and
  whether it matches `prace_synth_app`'s role password (hashed comparison
  only, never printed).
- HBA reconciliation status (`pg_hba.conf` lines for `prace_synth_app` and
  `127.0.0.1/::1`).
- Systemd unit reconciliation: orphan gunicorn PID 2681143 vs the
  operator-intended supervisor.

**Official sources.** PostgreSQL 18 client authentication docs
(https://www.postgresql.org/docs/18/client-authentication.html) for HBA
formats and `password` / `scram-sha-256` / `md5` method expectations.

**Fix variants.** All operator-owned; not an application fix:
1. Reset `prace_synth_app` password, rotate `RETIRED_RUNTIME_CONFIG`
   `PRACE_DB_PASSWORD`, restart the supervised synthetic gunicorn.
2. Reconcile the orphan listener (PID 2681143) with the selected supervisor.
3. HBA review: confirm `host prace_synthetic prace_synth_app 127.0.0.1/32
   scram-sha-256` (or `md5`) line.
4. Verify the rehearsal runtime can `SELECT current_user, current_database()`
   with the application password, **outside** the application process.

**Next step for the architect.** Issue the operator work order for
INFRA-PG-01 sub-items 1–3 (credential, supervisor, HBA) before any live
owned-PG `current_user` / `statement_timeout` evidence is claimed.

### D-3: JAN-01 OCR HTTP 500 flake

**Observed.** Historical flaky `OCR_STATUS_HTTP_500` on the rehearsal
runtime. WAL + `transaction_mode=IMMEDIATE` + `busy timeout=20` mitigation
in effect (uncommitted supervised-settings edit). Three full journeys
in this tree produced zero 500s; single reproduction remains flaky-class
evidence, not a statistical fix claim.

**Evidence in repo.**
- `portal/settings_supervised_synthetic.py` — WAL/IMMEDIATE/busy-timeout
  block (uncommitted, carried forward).
- `tests/test_rehearse_synthetic_site.py` + `tests/test_rehearse_synthetic_site_lifecycle.py`
  — 30 passed in 61.96 s (historical run).

**Missing evidence.**
- Repro frequency under load (target N≥20 runs with a workload that triggers
  the original 500).
- Gunicorn worker crash logs at the moment of the 500 (if any).
- Whether the mitigation is sufficient under `--workers 4` or under the
  persistent-runtime profile (`runtime/portal/supervised-jan-investigation`).

**Official sources.** SQLite docs on WAL and busy-timeout
(https://www.sqlite.org/wal.html, https://www.sqlite.org/pragma.html#pragma_busy_timeout);
Django `transaction_mode=IMMEDIATE` semantics
(https://docs.djangoproject.com/en/5.2/ref/databases/#transaction-mode).
The combination is documented but Django's transaction_mode option is
relatively new (5.2) — verify it is honoured by the current
`django.db.backends.sqlite3` backend at the pinned Django version.

**Fix variants.**
1. Keep WAL/IMMEDIATE/busy-timeout; commit the supervised-settings block
   so the mitigation is no longer uncommitted; document as a tactical fix.
2. Replace the inline OCR execution with a durable OcrRun job (web intake
   already queues one for `process_ocr`; the older inline-execution prose
   is corrected in the plan file). This is the architecture's intended
   path.
3. Add a deterministic-load fixture for a controlled N=20 run and require
   zero 500s as the acceptance gate for variant 2.

**Next step for the architect.** Decide between variant 1 (commit the
mitigation now, defer variant 2) and variant 2 + 3 (commit the migration to
durable OcrRun and prove with a deterministic load). Variant 1 is the
lower-risk path; variant 2 is the correct architecture.

### D-4: JAN-03 default-exported acceptance is A1-heavy

**Observed.** `scripts/run_release_reproducer.py::acceptance_commands`
remains A1-heavy and does not execute the browser/restart lifecycle; the
`--profile` flag is documented in the journey helper but not advertised
as implemented in the reproducer.

**Evidence in repo.**
- `tests/_rehearse_workflow_browser.py` — `--profile core|optional-a1`
  argument; default `core`.
- `scripts/run_release_reproducer.py` — current `acceptance_commands`
  list.

**Missing evidence.** A reproducible committed-source run of the core
journey from the reproducer, including the new `assignment_corrected`
non-A1 stage, with `case_pk` / `regenerated_case_pk` null in the evidence.

**Fix variants.**
1. Extend `acceptance_commands` with a `core` profile entry that calls
   the journey helper and asserts `assignment_corrected` is present and
   A1 stages are skipped.
2. Same as 1, with the existing A1 commands retained under an
   `optional-a1` profile flag.

**Next step for the architect.** Approve variant 1 + 2 as one bounded
increment; do not advertise the profile flag in the FEEDBACK report until
both profiles pass a committed-source reproducer run.

### D-5: State-machine anomaly — branch reset between sessions

**Observed (2026-09-16, this session).** Two commits (`fa87ad8`,
`a48a1e8`) created in the prior session existed as orphaned objects on
this session start; the branch HEAD was `a3a9a24` (JanSA1 placeholder),
not the expected `a48a1e8`. The working tree contained a **different**
revision of every file (c24a293-onward content + additional WT delta
beyond `a48a1e8` in 2 files: `run_release_reproducer.py` adding
`PRACE_WORKFLOW_PG` to forwarded env; `test_pg_contract.py` adding
explicit blank-target rejection).

**Evidence in repo.**
- `git fsck --unreachable` listed the two orphan commits.
- Diff tree against `c24a293` showed the WT delta.
- `git merge-base --is-ancestor 8d125f2 a3a9a24` returned true: `a3a9a24`
  is a descendant of `8d125f2`, so the branch had been moved forward by
  an external process, not reset to a foreign tip.

**Likely cause.** Another process (parallel review agent, CI worker, or
operator action) advanced the branch to `a3a9a24` (and onward to
`c24a293`, which is now on `origin`) between sessions. The orphan commits
were the previous session's final state.

**Missing evidence.**
- No audit log identifying the process that moved the branch (no
  reflog entry for `fa87ad8`/`a48a1e8`).

**Fix variants.**
1. Adopt the current WT as authoritative (chosen this session); commit
   the residual WT delta + docs as two new commits on top of the
   published `c24a293`; push with explicit refspec; verify remote SHA.
2. Add a server-side hook (e.g., a `post-commit` notification) to a
   log so cross-session branch movement is visible.

**Next step for the architect.** No application code fix; variant 1 is
the per-incident recovery. Variant 2 (cross-session branch audit log)
is a small infra-side change and would prevent future orphan commits
going unnoticed.

### D-6: Plan/skill staleness vs code state

**Observed.** The audit plan and both skill docs carried stale paragraphs
that described issues already closed in `c24a293` (`psql_env` regression,
empty-variable SQLite fallback). A separate review agent had already
produced the corrective FEEDBACK-REPORT and skills updates; this session
extended those updates with the post-audit incremental repair section.

**Evidence in repo.**
- `c24a293` (`d0903a8`) — `psql_env` regression fix.
- Pre-edit `plans/2026-09-14-delivery-reliability-and-jan-v1.md` table
  row "Open: incomplete environment chain" and paragraph "P0 new
  regression: psql_env rebuilds from ambient...".
- Post-edit (this session): both paragraphs updated in `5575135`.

**Fix variant.** Already applied: each delivery increment that closes
items in the audit table also updates the corresponding plan rows and
skill doc paragraphs in the same batch. The FEEDBACK-REPORT now carries
an explicit "Post-audit incremental repair" section that mirrors the
delivery record row, so the audit, plan and skills can be cross-checked.

**Next step for the architect.** Adopt the same "code closes + docs
update in one batch" pattern as a standing rule; the validation hook
already enforces it for path mapping. A lint that flags stale
"Open:" / "Partial:" rows in the plan file when the affected file's
mtime is more recent than the plan row would close the gap
mechanically; deferred until the architect decides.

### Summary table for the architect

| ID | Problem | Owner | Next step | Blocker for Jan acceptance? |
|---|---|---|---|---|
| D-1 | networkidle flake under hook load | workflow engineering | Replace with `wait_until="load"` + selector waits; capture one Chrome trace | No (acceptable as flaky-class evidence) |
| D-2 | INFRA-PG-01 operator credentials | operator | Credential reset + supervisor + HBA reconciliation | Yes — owned-PG acceptance cannot run until done |
| D-3 | OCR HTTP 500 flake | workflow engineering | Commit WAL/IMMEDIATE/busy-timeout mitigation; plan durable OcrRun migration | No (mitigation in effect; not statistical) |
| D-4 | Default-exported core journey missing | evidence tooling | Extend `acceptance_commands` with core profile | No (existing journey helper already covers it) |
| D-5 | Orphan commits after branch move | infra (audit) | Add cross-session branch-movement audit log | No (per-incident recovery sufficient) |
| D-6 | Docs staleness vs code | documentation | Standing rule "code closes + docs update in one batch" | No |
