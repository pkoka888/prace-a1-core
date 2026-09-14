---
name: synthetic-portal-delivery
description: Operate, debug, and extend the Delivery-1 supervised synthetic rehearsal site (prepare -> provision -> start -> real browser core workflow and separately scoped optional A1 regression -> stop -> restart). Use when exercising, troubleshooting or extending the canonical rehearsal lifecycle, the provisioned jan_planner + TOTP operator, the real Chromium authenticated journey, restart-survival, the sparse-input blocked evidence path, the bounded negative fixtures, or the related change-package selectors.
---

# Synthetic portal delivery (Delivery 1)

This skill links the canonical scripts, tests, settings and evidence for the
Delivery-1 supervised synthetic rehearsal site. Use it instead of inventing a
new test harness or a separate settings module. Real-data activation remains
gated by `docs/security/real-data-rules.md §14`; the supervised synthetic
settings module is synthetic-only by design.

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
- assignment creation (facts filled incl. the verifiable `decin`
  institution profile)
- A1 case preparation
- `a1_draft_generate` form submission / prepared-auto path
- protected PDF download (verified against the `%PDF-` magic)
- correction: one assignment input fact edited through the shipped
  form and verified to persist; the regenerated PDF is extracted
  with pymupdf and must contain the corrected text
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

The current extended rehearsal still includes A1 stages in its required set.
This is an optional-A1 regression profile, not the core-v1 release definition.
JAN-03 must implement separate core/optional profiles; no proposed flag exists yet.
A failing required stage still exits nonzero; do not relabel a failure as a skip.
`tests/document_web/test_browser_journey.py` independently exercises normal
login/TOTP, protected upload, condition-based OCR refresh, native selection,
confirmation, original download, tenant denial and logout. Its test-owned consumer
uses the same processing primitive; the extended rehearsal exercises the separate
worker command through Gunicorn. Neither SQLite run proves PostgreSQL acceptance.

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
proves that only the missing-facts path blocks.

## Validation policy

The rehearsal selects tests through `change-packages.yml`'s
`delivery_lifecycle_rehearsal` package; staging any of:

- `scripts/rehearse_synthetic_site.sh`
- `scripts/rehearse_dev_local.sh`
- `scripts/rehearse_verify_persistence.py`
- `scripts/build_release_manifest.py`
- `scripts/provision_synthetic_operator.py`
- `scripts/smoke_probe.py`
- `tests/test_rehearse_synthetic_site.py`
- `tests/test_rehearse_synthetic_site_lifecycle.py`
- `tests/test_rehearse_workflow.py`
- `tests/_rehearse_workflow_browser.py`
- `tests/_rehearse_workflow_data_path.py`

runs:

```bash
venv/bin/python -m pytest \
    tests/test_rehearse_synthetic_site.py \
    tests/test_rehearse_synthetic_site_lifecycle.py \
    tests/test_rehearse_workflow.py -q
```

Prose-only edits under `.agents/skills/synthetic-portal-delivery/`
are routed through a separate package that runs only structural and
planning checks; the 2½-minute rehearsal suite is not duplicated.

`scripts/select_infrastructure_git_workflow_checks.py` adds the same
rehearsal suite when a `requirements*.txt` is staged; the dispatcher
deduplicates identical commands across packages.

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

PostgreSQL is a target-dependent acceptance step. Set all four
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
journey, run the canonical acceptance script:

```bash
venv/bin/python scripts/rehearse_verify_persistence.py
```

It reuses the workflow test's restart-verification logic (exact
worker, assignment, both A1 cases, both PDF sha256s) and exits
non-zero with an actionable message on mismatch or missing
configuration. When the PostgreSQL target is unavailable it exits 2
(`PERSISTENCE_ACCEPTANCE_BLOCKED`) so the operator can distinguish a
transport failure from a data mismatch.

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