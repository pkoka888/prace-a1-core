# WSGI/ASGI deployment recipe — Release 1A Delivery 1

Parent: [AGENTS.md](../../AGENTS.md) "Default delivery unit"; the four-delivery
sequence in [roadmap.md](../../roadmap.md); the active automation plan
[2026-09-08-local-a1-automation.md](../../plans/2026-09-08-local-a1-automation.md).

Scope: deliver a stable private URL, individual login, persistent database,
and the existing frontend/backend wired through a single WSGI/ASGI entrypoint.
This recipe covers Delivery 1 of the four-delivery sequence. Deployment,
real-data activation, queue dispatch and M3 queues/exceptions/retention
remain separate work tracked elsewhere.

This is **not** a production activation. Real-data activation remains
gated by [`docs/security/real-data-rules.md §14`](../security/real-data-rules.md#14-real-data-activation-gate)
and REV-003. The settings module used here is synthetic-only; it refuses
real-data operations at the intake service.

## What was added

* `portal/wsgi.py` — WSGI entrypoint exposing the Django WSGI handler.
* `portal/asgi.py` — ASGI entrypoint exposing the Django ASGI handler.
* `tests/test_wsgi_asgi.py` — entrypoint contract tests (5 tests).

The existing `portal/settings_supervised_synthetic.py` is the production-
style settings module: `DEBUG=False`, restrictive `ALLOWED_HOSTS`,
non-insecure `SECRET_KEY` (required env var), confined runtime root,
synthetic-only posture, optional PostgreSQL target. No second production
settings module is added; that would duplicate the supervised-synthetic
contract.

## Local development

Default `DJANGO_SETTINGS_MODULE` is `portal.settings` (synthetic M2, DEBUG=True,
SQLite at the repo root). For day-to-day development:

```bash
DJANGO_SETTINGS_MODULE=portal.settings venv/bin/python manage.py runserver
```

The runserver binds to `127.0.0.1:8000` by default. Login is via
`/accounts/login/`. The protected `/review/` page redirects anonymous users
to `/accounts/login/`.

## Host deployment (synthetic-gated)

The WSGI entrypoint works under gunicorn. The ASGI entrypoint works
under uvicorn/daphne. Both default to `portal.settings` if
`DJANGO_SETTINGS_MODULE` is not set; deployment scripts set it explicitly.

```bash
DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT=/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development \
    PRACE_SECRET_KEY=$(cat /etc/prace/secret.key) \
    PRACE_RELEASE_MANIFEST=/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development/release_manifest.json \
    PRACE_RELEASE_MANIFEST_SHA256=$(cat /etc/prace/manifest.sha256) \
    PRACE_ALLOWED_HOSTS=prace-v-nemecku.tvoje.info,127.0.0.1 \
    gunicorn portal.wsgi:application --bind 127.0.0.1:8001
```

The supervised synthetic settings module fails closed on missing env vars;
the gunicorn command above is the minimum viable contract. Reverse-proxying
is the operator's nginx configuration; this document does not prescribe it.

For ASGI (HTTP/2 or websockets):

```bash
DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    <same env vars as above> \
    uvicorn portal.asgi:application --host 127.0.0.1 --port 8001
```

## Persistent PostgreSQL (optional)

The supervised synthetic settings module accepts an all-or-none PostgreSQL
target. Set all four `PRACE_DB_NAME`, `PRACE_DB_USER`, `PRACE_DB_HOST`,
`PRACE_DB_PORT` to enable it; remote TCP additionally requires
`PRACE_DB_SSLMODE=verify-full` and `PRACE_DB_SSLROOTCERT`.

The SQLite path remains the default when no `PRACE_DB_*` is set. The
synthetic SQLite database at `<runtime-root>/db.sqlite3` is operator-owned
and confined (mode 0600).

## Limitations

* Production deployment infrastructure (systemd unit, nginx configuration,
  TLS certificate handling, secret delivery, backup scheduling) is owned
  by infrastructure, not this recipe.
* `django-q2` is installed but `Q_CLUSTER` is intentionally not configured;
  background jobs continue to run inline or as separate processes. Queue
  dispatch is Delivery-3 work.
* The synthetic SQLite database at `<runtime-root>/db.sqlite3` is operator-
  owned; the rehearsal lifecycle test (see below) prepares and tears down
  isolated roots under `runtime/portal/supervised-lifecycle-*`; production
  rehearsal roots must live outside the repository to avoid staging.
* Real-data activation is not enabled by importing the WSGI/ASGI module.
  `settings.M2_SYNTHETIC_ONLY` remains `True`; intake refuses non-synthetic
  configuration.

## Rehearsal lifecycle (Delivery-1 testing site)

`scripts/rehearse_synthetic_site.sh` exercises the full supervised-synthetic
lifecycle without touching real data or operator-owned services. It is the
canonical entrypoint for the bounded integration tests in
`tests/test_rehearse_synthetic_site_lifecycle.py` (anonymous HTTP),
`tests/_rehearse_workflow_browser.py` (real Chromium authenticated
journey against the running gunicorn) and
`tests/test_rehearse_workflow.py` (which drives the same journey as a
pytest case plus the restart-survival query). The bounded negative
fixtures for F1 (wrong-server / stopped-server smoke failures), F2
(child symlink before mkdir/chmod), and F8 (umask-022 file modes) live
in `tests/test_rehearse_synthetic_site.py`.

```bash
# 1. Confine-validate, mkdir, write the manifest, migrate, collectstatic.
bash scripts/rehearse_synthetic_site.sh prepare

# 2. Provision an individual synthetic operator + organization + TOTP MFA.
#    operator.json (mode 0600) holds the password and TOTP secret;
#    organization.json (mode 0600) holds the org record.
bash scripts/rehearse_synthetic_site.sh provision

# 3. Launch gunicorn against the supervised settings module. The
#    script asserts the bind is free, launches gunicorn with --pid,
#    waits for /health/ to return 200 with our manifest's commit
#    (delegated to scripts/smoke_probe.py for the strict JSON
#    contract), and records the launch identity so stop can refuse
#    wrong PIDs.
bash scripts/rehearse_synthetic_site.sh start

# 4. Strict smoke: /health/, /login/, /accounts/login/, /review/,
#    /readiness/, and the static assets actually shipped
#    (htmx-1.9.10.min.js, tailwind-2.2.19.min.css). 000/500/404 and
#    external-host redirects all fail.
bash scripts/rehearse_synthetic_site.sh smoke

# 5. Real-browser authenticated journey against gunicorn. Drives a
#    headless Chromium through the natural allauth login + TOTP
#    challenge, worker creation, document upload, document association,
#    OCR, assignment, and A1 preparation. Exit 0 on every documented
#    stage; exit 7 on a journey failure.
bash scripts/rehearse_synthetic_site.sh workflow

# 6. Graceful stop. Verifies PID ownership before SIGTERM.
bash scripts/rehearse_synthetic_site.sh stop

# Rollback stops the server; the operator removes the runtime root
# manually after inspection.
bash scripts/rehearse_synthetic_site.sh rollback
```

The `prepare-manifest-only` subcommand skips migrate/collectstatic and
is what the cheap unit tests use. The bounded lifecycle test exercises
the real gunicorn path and proves the smoke contract now catches
HTTP-500, no-server, a stale-pidfile scenario, and the same-origin
redirect contract. The workflow test (`tests/test_rehearse_workflow.py`)
covers prepare + provision + start + a real headless Chromium browser
journey against gunicorn (login + TOTP + worker + document upload +
document association + OCR + assignment + A1 preparation) + stop +
restart + query-after-restart + stop. The browser journey uses the
operator's session cookies through the natural allauth login form and
TOTP challenge — no service-side shortcut, no helper-side membership
widening. Sparse-input stages (OCR confirm when no proposals exist;
PDF download when the 44-field A1 contract is incomplete) are recorded
as documented skip paths, not failures. Restart-survival of the
synthetic record set is verified by stopping gunicorn, restarting it,
and querying the supervised-synthetic database for the worker and case
captured during the journey.

The `workflow` subcommand is implemented as a real entrypoint and is
the documented Delivery-1 acceptance path:

```bash
# After prepare + provision + start:
bash scripts/rehearse_synthetic_site.sh workflow
# Exit 0 on every documented stage; exit 7 on a journey failure.
```

The same journey is exposed as a pytest test
(`tests/test_rehearse_workflow.py`); the standalone subcommand and
the pytest test exercise identical paths through the real Chromium
journey script (`tests/_rehearse_workflow_browser.py`).

Playwright + Chromium are usable on loopback: Secure cookies over
plain HTTP are accepted because Chromium treats loopback as
potentially-trustworthy. The earlier "missing a TLS proxy" claim was
investigated and is no longer correct for the local rehearsal; a
TLS-terminating proxy is not a prerequisite for the synthetic browser
journey. PostgreSQL acceptance remains separate until an authorized
scoped target is available; the lifecycle test runs against SQLite.

## Distinguishing this synthetic hosting configuration from real-data

The `portal.settings_supervised_synthetic` module is appropriate for the
Delivery-1 testing site because it is *synthetic-only by design*: it fails
closed on missing env vars, refuses to fall back to `DEBUG=True`, confines
storage under `PRACE_RUNTIME_ROOT` with operator-only permissions, and
keeps `M2_SYNTHETIC_ONLY=True` so intake refuses non-synthetic configuration.

A future real-data deployment is **not** this settings module. Real-data
activation requires:

1. A dedicated real-data settings module that explicitly *flips*
   `M2_SYNTHETIC_ONLY=False`, names the production database, names the
   protected storage roots, and supplies the SOPS-decrypted secrets.
2. Migration of historical databases from synthetic fixtures to operator-
   approved real records.
3. A separate delivery contract (Delivery 3 in the four-delivery sequence)
   that records the activation evidence, the REV-003 approval and the
   infrastructure handoff.

The settings module shipped here is not a placeholder for real-data; it
is the synthetic hosting configuration for the testing site only.

## Verification

```bash
DJANGO_SETTINGS_MODULE=portal.settings_document_tests \
    venv/bin/python -m pytest tests/test_wsgi_asgi.py -v
```

Expected: 5 passed. The five tests confirm import, default settings
contract, basic routing (login redirect, health endpoint, protected
review page) and the synthetic-only posture.
