---
name: synthetic-portal-delivery
description: Operate, debug, and extend the Delivery-1 supervised synthetic rehearsal site (prepare -> provision -> start -> real browser journey -> stop -> restart). Use when exercising, troubleshooting or extending the canonical rehearsal lifecycle, the provisioned jan_planner + TOTP operator, the real Chromium authenticated journey, restart-survival, the bounded negative fixtures, or the related change-package selectors.
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
2. Read the active local automation plan
   `plans/2026-09-08-local-a1-automation.md` for the Delivery-1 status.
3. Read the current Delivery-1 entry in `docs/operations/git-delivery.md`
   for the demonstrated contract and limitations.
4. Inspect `git status` and `git log --oneline -5`; preserve inherited edits
   and untracked files (notably `tests/test_ocr_benchmark_contract.py`).
5. Resolve the runtime root: `<repo>/runtime/portal/supervised-<name>/`,
   owned by the operator, mode 0700. The rehearsal script refuses any
   path outside this layout.

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
7  workflow failure (authenticated session could not exercise the journey)
```

The full Delivery-1 lifecycle:

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

Convenience wrapper `scripts/rehearse_dev_local.sh` generates a fresh
synthetic secret on every invocation and forwards to the canonical
script. Prefer it for one-shot local runs:

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
database" foot-guns). `operator.json` (mode 0600) holds the password
and TOTP secret; `organization.json` (mode 0600) holds the org record.
Both live inside the operator-owned runtime root; the script never
prints the password outside a deliberate read of that file.

## Real-browser journey

`tests/_rehearse_workflow_browser.py` drives a headless Chromium
(Playwright 1.62.0+, Chromium 1228/1234 from `~/.cache/ms-playwright`)
through the natural allauth login form and TOTP challenge, then
worker creation, document upload, document association, OCR confirm
(when proposals exist), assignment creation, A1 preparation, and case
detail visibility. HTMX is neutralized at the network level so the
Release 1A forms behave as plain HTML; every POST goes through the
operator's session cookie jar — no service-side shortcut, no
helper-side membership widening.

Sparse-input stages are documented skip paths, never failures:

- `ocr_field_confirmed`: skipped when no OCR proposals match the
  selected document/region (synthetic OP card fixture-specific).
- `a1_pdf_downloaded`: skipped when the worker does not satisfy the
  full 44-field A1 contract; the dedicated `tests/document_web`
  cohort suite exercises the full A1 contract on a complete input row.

Restart-survival of the synthetic record set is verified by stopping
gunicorn, restarting it, and querying the supervised-synthetic
database for the worker and case captured during the journey.

## Validation policy

The rehearsal selects tests through `change-packages.yml`'s
`delivery_lifecycle_rehearsal` package; staging any of:

- `scripts/rehearse_synthetic_site.sh`
- `scripts/rehearse_dev_local.sh`
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

The `infrastructure_git_workflow` package adds the rehearsal
unit/lifecycle tests through
`scripts/select_infrastructure_git_workflow_checks.py` whenever a
`requirements*.txt` is staged, so a silent `whitenoise`/`rapidocr`
regression does not slip past pure-tooling checks.

## Smoke contract

`scripts/smoke_probe.py` issues typed HTTP probes against `/health/`,
`/login/`, `/accounts/login/`, `/review/`, `/readiness/` and the
shipped static assets. It honors the configured `Host` header and
method by passing the constructed `urllib.request.Request` to
`opener.open(request, ...)`. Connect and body-read share one
wall-clock deadline so the timeout contract is documented and
asserted. Any 000/500/404 or external-host redirect fails the contract.

## Bounded negative fixtures

`tests/test_rehearse_synthetic_site.py` covers the F1–F8 negative
fixtures: wrong-server smoke failure, no-server smoke failure,
stale-pidfile rejection, wrong-pidfile-contents rejection, child
symlink rejection before mkdir/chmod, and permissive-umask mode
contract. Each assertion reproduces one of the bugs the bounded
lifecycle test caught.

## PostgreSQL acceptance

PostgreSQL is a target-dependent acceptance step. Set all four
`PRACE_DB_NAME`, `PRACE_DB_USER`, `PRACE_DB_HOST`, `PRACE_DB_PORT`;
remote TCP additionally requires `PRACE_DB_SSLMODE=verify-full` and
`PRACE_DB_SSLROOTCERT`. The lifecycle test runs against SQLite by
default. The supervised settings module is synthetic-only and
intentionally refuses real-data configuration; PostgreSQL acceptance
does not change that posture.

## Avoid

- Do not invent a second settings module. Reuse
  `portal.settings_supervised_synthetic`.
- Do not add a helper-side membership widening or service-side
  shortcut in the journey — the operator role is what Jan would
  actually exercise.
- Do not redirect through a TLS proxy in the rehearsal; Chromium
  treats loopback as potentially-trustworthy and Secure cookies
  work over plain HTTP locally.
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