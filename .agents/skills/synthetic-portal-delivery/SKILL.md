---
name: synthetic-portal-delivery
description: Operate, debug, and extend the Delivery-1 supervised synthetic rehearsal lifecycle, real Chromium core workflow, optional A1 regression, restart persistence and related check selection. Use for provisioned operator login, sparse-input evidence, owned process cleanup and scoped acceptance diagnostics.
---

# Synthetic portal delivery (Delivery 1)

This skill links the canonical scripts, tests, settings and evidence for the
Delivery-1 supervised synthetic rehearsal site. Use it instead of inventing a
new test harness or a separate settings module. Real-data activation remains
gated by `docs/security/real-data-rules.md §14`; the supervised synthetic
settings module is synthetic-only by design.

> **Selected runtime contract (2026-09-16):** infrastructure owns
> `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`, injected by
> `prace-v-nemecku-gunicorn.service` through `EnvironmentFile=`. See
> [runtime policy](../../../docs/operations/runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
> Keep tool `.env` separate; never print, copy/hash the payload, shell-source it or
> stage `.runtime-config/`. Path retirement changes no secret values, release pin
> or process ownership. Require infrastructure cutover receipts before calling it deployed.
> Existing reports identify equal on-disk secrets and a pin/manifest mismatch;
> actual DB authentication and approved release remain unverified here. Do not infer
> the correct pin from the current marker. No automatic password reset or restart.
> Rehearsals use disposable roots/ports and must not race the selected live8001
> listener or overwrite its manifest. Temporary hostname remains `prace-v-nemecku.expc.cz`.

## Ground the run

1. Read `AGENTS.md` first; the four-delivery sequence, the proportional
   validation cadence and the real-data rules are authoritative.
2. Read `roadmap.md` and the active
   `plans/2026-09-14-delivery-reliability-and-jan-v1.md`; the older local
   automation plan records historical A1 work, not the core-v1 acceptance scope.
3. Read the current Delivery-1 entry in `docs/operations/git-delivery.md`
   for the demonstrated contract and limitations.
4. Inspect `git status` and `git log --oneline -5`; preserve inherited edits
   and untracked files (notably `tests/test_ocr_benchmark_contract.py`).
5. Resolve the runtime root: `<repo>/runtime/portal/supervised-<name>/`,
   owned by the operator, mode 0700. The rehearsal script refuses any
   path outside this layout.
6. Confirm prerequisites are installed: Playwright Python package plus
   the matching Chromium build under `~/.cache/ms-playwright`. The
   journey helper fails closed if Chromium cannot launch; no
   service-side shortcut substitutes the real browser path.

## Canonical entrypoint

The shell entrypoint `scripts/rehearse_synthetic_site.sh` is the
documented acceptance path. Exit codes are documented in its header
comment:

```text
0  success
1  preparation failure (confined root, manifest, settings)
2  start failure (gunicorn did not accept requests in time / wrong server)
3  stop failure (gunicorn still listening)
4  restart failure (start after stop did not accept)
5  rollback failure (operator intervention required)
6  smoke failure (HTTP probe did not match expected contract)
7  workflow failure (a required authenticated-browser stage failed
   or the journey script returned non-zero)
```

The supervised synthetic lifecycle (not routed-site/Jan acceptance):

```bash
bash scripts/rehearse_synthetic_site.sh prepare        # 1
bash scripts/rehearse_synthetic_site.sh provision      # 2
bash scripts/rehearse_synthetic_site.sh start          # 3
bash scripts/rehearse_synthetic_site.sh smoke          # 4 (typed JSON contract)
bash scripts/rehearse_synthetic_site.sh workflow       # 5 (real Chromium journey)
bash scripts/rehearse_synthetic_site.sh stop           # 6
bash scripts/rehearse_synthetic_site.sh start          # 7 (restart-survival)
# query-after-restart against the supervised SQLite
bash scripts/rehearse_synthetic_site.sh stop
```

The `workflow` subcommand sets `cwd` and `PYTHONPATH` to the repo
root before invoking the journey helper, so it works as a standalone
shell command without the pytest `pythonpath = .` setting.

Convenience wrapper `scripts/rehearse_dev_local.sh` keeps the
signing key stable across ordinary invocations while confining the
runtime root: it validates the RAW path before any `mkdir` (rejects
out-of-tree and symlinked children), refuses a `.secret_key`
symlink, recovers from an empty persisted key by replacing it with a
fresh usable secret, and mints `$PRACE_RUNTIME_ROOT/.secret_key`
atomically (`mktemp` + `mv -f` + `chmod 0600`) when the caller does
not supply `PRACE_SECRET_KEY`. It forwards every command to the
canonical `rehearse_synthetic_site.sh` from the repo root. Prefer it
for one-shot local runs:

```bash
bash scripts/rehearse_dev_local.sh prepare
bash scripts/rehearse_dev_local.sh provision
bash scripts/rehearse_dev_local.sh start
bash scripts/rehearse_dev_local.sh workflow
bash scripts/rehearse_dev_local.sh stop
```

## Provisioning contract

`scripts/provision_synthetic_operator.py` is idempotent on rerun. It
creates a `jan_planner` membership (worker:create, assignment:create,
a1:prepare, document:upload, document:confirm) — not `operator`, which
lacks the worker/assignment capabilities. It also creates a verified
`EmailAddress` so allauth's mandatory email verification does not
block the login. The TOTP secret and password are reused on ordinary
reruns; rotation is explicit via `--rotate-credentials` or
`--password`.

The script refuses to run unless `--runtime-root` equals the configured
`PRACE_RUNTIME_ROOT` (preventing "fix one, point at a different
database" foot-guns). If an operator already exists without an
`operator.json` and no rotation is requested, the script refuses
rather than silently minting a credential it cannot record.

`operator.json` (mode 0600) holds the password and TOTP secret;
`organization.json` (mode 0600) holds the org record. Both live
inside the operator-owned runtime root; the script never prints the
password outside a deliberate read of that file. Evidence receipts
and JSON journey outputs never include the TOTP code.

## OCR execution and recovery

HTTP intake/supersession persists `OcrRun.PENDING` and returns without running OCR.
The existing intake/execute/inbox service defaults remain synchronous for CLI and
business-rule callers. Do not use their `_sync=True` tests as async evidence.

Rehearsal `start` launches one owned sequential OCR worker once provisioned;
`provision` starts it if the owned web server is already running. `workflow`
ensures it exists. `stop`/`restart` own both processes. Before provisioning,
`start` may serve anonymous smoke checks without a worker.

The canonical worker command is `venv/bin/python manage.py process_ocr
--organization-id <id> --actor-id <id>`. Both IDs are mandatory; the active actor
must have `document:upload`. Default processes at most one job; `--loop` polls
once per second and reloads authorization each batch. Use the same supervised
environment/DB as the web app. `--max-runs` bounds a sequential batch, not concurrency.
The lifecycle helper supplies `--ready-file`; don't fabricate its handshake.

Jobs become visible after commit; there is no request-launched thread or dispatch
notification, so no `on_commit` callback is needed. If a future notification is
added, schedule it with `on_commit`, never before the outer transaction commits.
Expired fifteen-minute leases are recovered with a new attempt token; stale
publishers cannot overwrite it. Failed jobs require explicit retry, up to three
attempts. The Czech document page offers **Obnovit stav** and failed-job retry.
An unavailable worker leaves a visible saved/pending document, not OCR success.

`logs/ocr-worker.log` contains sanitized tags and opaque run IDs; use it with the
existing audit/run state before retrying. DB outage preserves durable claims for
lease recovery. A killed process may leave private unreferenced derivative files;
retention review owns cleanup, never bulk-delete runtime artifacts.
The worker PID record `.ocr-worker.json` binds runtime, actor/org, argv and Linux
start ticks; the helper uses pidfd signals and refuses foreign/reused PIDs.

## Real-browser journey

`tests/_rehearse_workflow_browser.py` drives a real headless
Chromium through the shipped frontend end-to-end:

- login + TOTP
- worker creation (the form has `method="post"`; the helper does not
  inject attributes)
- document upload (synthetic OP card with `PRIJMENI`, `JMENO`,
  `DATUM NAROZENI` and `TRVALY POBYT` labels so the address review
  form appears)
- OCR proposal confirmation (family_name, given_name, birth_date,
  residence_address)
- missing-identity form (birth_place, nationality, sex,
  insurance_number)
- address review form (street, house_number, city, postal_code,
  country_code)
- assignment creation (both profiles; the A1 input facts incl. the
  verifiable `decin` institution profile are filled only by the
  `optional-a1` profile)
- non-A1 assignment correction (`assignment_corrected`, both profiles):
  one plain assignment fact is edited through the shipped assignment
  edit form — optimistic-lock `version` included — and verified to
  persist after reload; the core profile exercises correction with NO
  A1 dependency
- protected source-document download (both profiles; real browser-session
  fetch verifies status, non-HTML content type, exact size and SHA-256 against
  the uploaded synthetic PNG). Optional A1 PDF checks are listed separately below

The `optional-a1` profile (`--profile optional-a1`, exercised only by
the separately scoped A1 regression) additionally drives:
- A1 case preparation and `a1_draft_generate` form submission /
  prepared-auto path
- protected A1 PDF download (verified against the `%PDF-` magic)
- A1 correction: one assignment input fact edited through the shipped
  a1-inputs form and verified to persist (`a1_corrected_facts`)
- regeneration: a NEW A1 case prepared from the corrected snapshot;
  its PDF must differ from the first (new sha256) and the canonical
  generation input (`A1DraftGeneration.snapshot["row"]`) is queried
  to confirm the corrected value was bound

Every stage uses real HTTP requests with the operator's session
cookies. There is no JS route replacement, no hidden form/button
injection, no service-side shortcut and no helper-side membership
widening. HTMX is allowed to run; the templates provide `method="post"`
and `action="."` so the browser's native submit path succeeds
whether or not HTMX intercepts.

The journey defaults to the `core` profile (the Release 1A core-v1
definition): A1 stages are intentionally skipped, the required core
stage set includes the non-A1 `assignment_corrected` stage, and a single
explicit `a1_skipped` stage is recorded with `case_pk`/
`regenerated_case_pk` null in the evidence. The `optional-a1` profile is
the separately scoped A1 regression, not the core-v1 acceptance
definition. The core/optional-A1 profile separation (JAN-03) is
implemented in the browser helper, but not complete across acceptance: the
lifecycle still unconditionally executes A1 sparse preparation/reservation checks
and the default committed export omits this journey. JAN-03 remains partial. The canonical
persistence verifier (`scripts/rehearse_verify_persistence.py`) accepts
`--profile core|optional-a1` and defaults to `core`. A failing
required stage still exits nonzero; do not relabel a failure as a skip.
`tests/document_web/test_browser_journey.py` independently exercises normal
login/TOTP, protected upload, condition-based OCR refresh, native selection,
confirmation, original download, tenant denial and logout. Its test-owned consumer
uses the same processing primitive; the extended rehearsal exercises the separate
worker command through Gunicorn. Neither SQLite run proves PostgreSQL acceptance.

Defect status from the 2026-09-15 review checkpoint and the delivered
JAN work: the OCR HTTP 500 (JAN-01) has a working-tree SQLite mitigation
(`journal_mode=WAL`, `transaction_mode=IMMEDIATE`, busy timeout) that
removed 500s from three consecutive journeys, but a bounded run set is
not a statistical fix claim. The protected-download byte mismatch
(JAN-02) was an authentication-redirect artifact in the journey helper
and is fixed by fetching through the real browser page. JAN-04 repairs
remain open; the active plan records the missing committed shell dependency,
self-declared disposable ownership, reproduced invalid psql probe and incomplete
forwarding. Actual source-byte verification is implemented; intended-target
restart acceptance is still unverified. Treat skill instructions here as
the reconciliation reference against executable configuration, not as
evidence that PostgreSQL acceptance is closed.

## Sparse-input evidence path

`tests/_rehearse_workflow_data_path.py` (standalone script; the
workflow test runs it between stop and restart) exercises the
canonical services against the same supervised SQLite after a
journey: the `jan_planner` membership is intact, an unknown-optional-
facts sparse worker still saves, its `prepare_a1` case has
`readiness=BLOCKED`, and `reserve_application_draft` raises
`DraftInputBlocked` naming the missing facts. Running it standalone
requires the same env as the lifecycle (`PRACE_RUNTIME_ROOT`,
`PRACE_SECRET_KEY`, manifest + sha vars, all four `PRACE_DB_*` when
targeting PostgreSQL):

```bash
PYTHONPATH="$PWD" venv/bin/python tests/_rehearse_workflow_data_path.py \
    /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development
```

A fully-named sibling worker's A1 case is `READY`, so the script also
checks the missing-facts A1 path. This is currently an unconditional dependency
of the lifecycle's core profile; it must move to optional-A1 under JAN-03.
The sparse row is created directly through the ORM, so this does not prove that
Jan can save the same incomplete input through the frontend. Add that core UI
scenario without requiring A1 preparation or reserving a draft.

## Validation policy

Inspect `change-packages.yml` and the actual selectors for the owned staged
paths. `delivery_lifecycle_rehearsal` currently selects site, lifecycle, workflow,
OCR-worker lifecycle and disposable-guard tests. Skill-only changes use structural
and planning checks, not a browser rehearsal. Let the mandatory hook run its
selection once for commit-bound work; do not duplicate it with `--run-checks`.

The dependency selector currently emits a shorter three-file lifecycle command;
the dispatcher only deduplicates identical commands. REL-04 must reconcile this
overlap; do not claim it is already deduplicated. The hook runs working-tree code,
so its success is not an index/committed-source proof. Inspect candidate dependencies
and use the existing export mechanism for release evidence after core coverage is
implemented. Keep dependency/settings/target identity with the private receipt.

### Investigating a browser failure

Read the failing stage and native exit from the private report/log first. Retain
the initial failure alongside any successful retry. `networkidle` is still used
at several transitions; replace affected waits with expected response/URL and
visible domain-state assertions, preserving real HTMX/browser behavior. Do not
increase timeouts or diagnose load merely because a standalone run passes.

Before fixture cleanup, capture bounded synthetic failing-stage timing, response
status/redirect classification and server/request error categories. Keep cookies,
TOTP, credentials and document bodies out of evidence. On early exceptions the
current helper prints a generic failure JSON and loses its accumulated stage map;
preserving that map is part of JAN-01/JAN-02. A source literal such as
`"database is locked"` in a pytest traceback is not an observed server error.

## Smoke contract

`scripts/smoke_probe.py` issues typed HTTP probes against `/health/`,
`/login/`, `/accounts/login/`, `/review/`, `/readiness/` and the
shipped static assets. It honors the configured `Host` header and
method by passing the constructed `urllib.request.Request` to
`opener.open(request, ...)`. Connect and body-read share one
wall-clock deadline enforced through `time.monotonic()` checks
before and after the body read, and the underlying socket is armed
with the remaining budget so a fully held-open body is interrupted
at the OS level. The `HTTPError` path reads the body straight from
the socket, which returns partial data and honors the armed
timeout exactly, so a slow or held error body always raises
`TimeoutError` within the budget. The success body is read through
the http.client buffered reader using `read1` (which returns partial
data without waiting for the full internal buffer) so each
iteration observes the wall-clock deadline even against a
continuously dripping server; a slow drip is bounded by the
per-iteration wall-clock check, and `BlockingIOError` is treated as
a budget overrun. Any 000/500/404 or external-host redirect fails
the contract.

## Bounded negative fixtures

`tests/test_rehearse_synthetic_site.py` covers the negative
fixtures: wrong-server smoke failure, no-server smoke failure,
stale-pidfile rejection, wrong-pidfile-contents rejection, child
symlink rejection before mkdir/chmod, permissive-umask mode
contract, wrapper out-of-tree path rejection, wrapper symlinked
`.secret_key` rejection, wrapper positive root + atomic key
creation, held-body socket-interruption regression (success +
error), slow-drip wall-clock regression (success + error). Each
assertion reproduces one of the bugs the bounded lifecycle test
caught.

## Test cleanup

`tests/test_rehearse_workflow.py` stops the test-owned gunicorn
process in a `try/finally` block before the runtime root fixture
removes its directory; a failed journey still leaves no leaked
process. The canonical `stop` command runs **first** and refuses
to signal a pidfile whose PID does not match the launch record
(bind, runtime, start time, cmdline). The fallback direct signal
runs only after the canonical stop, and repeats the same ownership
checks (`.gunicorn.started_at` vs `/proc/<pid>` stat + cmdline
containing `gunicorn` and `portal.wsgi:application`) before
sending SIGTERM/SIGKILL.

## PostgreSQL acceptance

PostgreSQL is a target-dependent acceptance step. Before invoking the PG test
lifecycle, read [postgres-ops](../postgres-ops/SKILL.md): current disposable ownership
and lock-probe defects make an arbitrary/shared target unsafe. Engineering-owned
isolated PostgreSQL integration is possible independently of operator credentials. Set all four
`PRACE_DB_NAME`, `PRACE_DB_USER`, `PRACE_DB_HOST`, `PRACE_DB_PORT`;
remote TCP additionally requires `PRACE_DB_SSLMODE=verify-full` and
`PRACE_DB_SSLROOTCERT`. Omitting all four permits the default SQLite
target; a partial set is rejected by the supervised settings module.
The lifecycle test runs against SQLite by default. The supervised
settings module is synthetic-only and intentionally refuses real-data
configuration; PostgreSQL acceptance does not change that posture.

Host PostgreSQL is sysadmin-owned (cluster start, configuration,
backup, recovery). Engineering prepares a scoped recipe (database
name, user, storage root, environment contract, acceptance commands,
recovery steps) and hands it to the operator. Local synthetic
implementation does not require a running cluster.

After the documented `prepare → provision → start → workflow`
journey, run the canonical acceptance script (core profile by default,
matching the default `workflow` journey):

```bash
venv/bin/python scripts/rehearse_verify_persistence.py
```

It checks supplied exact records/source bytes after the target owner performs
restart; the command itself does not restart any service. It exits
non-zero with an actionable message on mismatch or missing
configuration. The `--profile core` acceptance covers worker, document,
assignment and document-bytes checks; `--profile optional-a1` additionally
verifies A1 case rows and artifact bytes on disk. When the PostgreSQL target
is unavailable it exits 2
(`PERSISTENCE_ACCEPTANCE_BLOCKED`) so the operator can distinguish a
transport failure from a data mismatch. A verified core run does not
prove PostgreSQL acceptance (JAN-04 remains open) and does not skip the
restart byte/record checks.

## Avoid

- Do not invent a second settings module. Reuse
  `portal.settings_supervised_synthetic`.
- Do not add a helper-side membership widening or service-side
  shortcut in the journey — the operator role is what Jan would
  actually exercise.
- Do not redirect through a TLS proxy in the local rehearsal;
  Chromium treats loopback as potentially-trustworthy. A real
  deployment still requires TLS, but it is not a rehearsal
  prerequisite.
- Do not stage protected paths (`a1/`, `scans/`, `data/`,
  `runtime/portal/`, `secrets/`, `.env`).
- Do not delete the inherited `tests/test_ocr_benchmark_contract.py`.
- Do not declare Delivery 1 complete without demonstrating
  restart-survival against a target that matches the documented
  contract.

## Related references

- `AGENTS.md` — operational authority.
- `docs/operations/wsgi-deployment-recipe.md` — Delivery-1 recipe.
- `docs/operations/git-delivery.md` — implementation/validation/
  publication/deployment/activation record.
- `plans/2026-09-08-local-a1-automation.md` — Delivery alignment
  (Delivery 1 acceptance paragraph).
- `docs/security/real-data-rules.md §14` — real-data activation gate.
