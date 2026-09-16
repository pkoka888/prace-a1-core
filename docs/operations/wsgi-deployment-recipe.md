# WSGI/ASGI deployment recipe — Release 1A Delivery 1

Parent: [AGENTS.md](../../AGENTS.md) "Default delivery unit"; the four-delivery
sequence in [roadmap.md](../../roadmap.md); the active delivery plan
[delivery reliability and Jan core v1](../../plans/2026-09-14-delivery-reliability-and-jan-v1.md).

Scope: deliver a stable private URL, individual login, persistent database,
and the existing frontend/backend wired through a single WSGI/ASGI entrypoint.
This recipe covers Delivery 1 of the four-delivery sequence. Deployment,
real-data activation and M3 queue expansion/exceptions/retention
remain separate work tracked elsewhere.

This is **not** a production activation. Real-data activation remains
gated by [`docs/security/real-data-rules.md §14`](../security/real-data-rules.md#14-real-data-activation-gate)
and REV-003. The settings module used here is synthetic-only; it refuses
real-data operations at the intake service.

## Current acceptance limitations — 2026-09-16

At `a48a1e8`, source corrections are partial: the shell migration-scope dependency
remains outside the commit; disposable PG ownership/probe/forwarding need repair;
core lifecycle still requires optional-A1 sparse assertions; the default export
omits browser/restart acceptance. Follow the active plan and
[PostgreSQL handoff](delivery-1-postgres-handoff.md) before treating this recipe as
an accepted candidate. A green local hook proves working-tree checks only.

Fresh read-only audit: PostgreSQL unit running, application unit failed/MainPID 0,
and an 8001 listener present. Authentication, intended route/build and restart
acceptance were not reverified. The installed allauth version now matches its pin;
this observation alone does not prove authentication recovery. No service restart
or credential change is authorized by this document update.

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

The infrastructure-owned `prace-v-nemecku-gunicorn.service` injects configuration
through this unit directive (unit syntax, not a shell command):

```ini
EnvironmentFile=/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env
```

See [runtime configuration policy](runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
The intended unit contract selects `portal.settings_supervised_synthetic`, an approved runtime root,
manifest and pin, and the complete selected database target. Do not extract a
secret with `cat`/`grep`, shell-source the file, or launch a parallel manual WSGI/ASGI
process on live port 8001. A rehearsal must use its own disposable root, credentials
and port. The temporary public hostname is `prace-v-nemecku.expc.cz`; the checkout
remains `/var/www/prace-v-nemecku.tvoje.info`.

A matching marker proves only on-disk consistency, not release approval. The
currently reported pin mismatch must be reconciled against an approved release;
this recipe does not authorize repinning or service restart. Infrastructure owns
unit/reverse-proxy adoption; the application supplies its nonsecret interface.

## Persistent PostgreSQL (required for intended-target acceptance)

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
  OCR now uses the existing durable `OcrRun` table and a sequential
  `process_ocr` management command. Broader queue infrastructure stays deferred.
* The synthetic SQLite database at `<runtime-root>/db.sqlite3` is operator-
  owned; the rehearsal lifecycle test (see below) prepares and tears down
  isolated roots under `runtime/portal/supervised-lifecycle-*`; production
  rehearsal roots remain confined under repository `runtime/portal/supervised-*`
  and are never staged.
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

Use the sequence below only after selecting a unique owned disposable runtime,
synthetic credentials, a fixture-owned port and a verified target. Never use the
live port 8001/root defaults. For PostgreSQL, the current workflow guard is insufficient:
complete the JAN-04 ownership/probe/forwarding repairs before using the PG workflow
as acceptance. SQLite rehearsal remains local implementation evidence.

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
redirect contract. The workflow test drives prepare/provision/start, a real
Chromium core journey and stop/start persistence checks. The core browser stages
cover normal login/TOTP, worker creation, document upload/association/OCR review,
assignment correction and protected original download. Optional A1 preparation,
PDF download and regeneration are a separate browser profile. A required-stage
failure is never relabeled as a skip.

Current limitation: the lifecycle still unconditionally calls the service-level
A1 sparse helper between stop and restart. JAN-03 must separate that dependency
and demonstrate incomplete saving through the UI. Restart evidence must retain
exact worker/document/assignment IDs, relationships, corrected facts and source
bytes; optional A1 artifacts do not gate core acceptance.

The `workflow` subcommand is implemented as a real entrypoint and is
the documented local core journey entrypoint; intended-route PostgreSQL and
restart acceptance require the full candidate scenario:

```bash
# After prepare + provision + start:
bash scripts/rehearse_synthetic_site.sh workflow
# Core is the default profile. A required journey failure exits nonzero.
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

## JAN-01/JAN-02: durable OCR worker

Upload returns after persisting pending work. Start the canonical rehearsal after
`prepare` and `provision`; it owns both Gunicorn and one OCR consumer. Its `status`,
`stop` and `restart` cover the worker as well. No host service is installed.

For a supervised foreground diagnostic with the same environment as the web app:

```bash
venv/bin/python manage.py process_ocr --help
# Replace the two IDs with the provisioned synthetic actor/organization IDs.
venv/bin/python manage.py process_ocr --organization-id <organization-id> --actor-id <actor-id>
```

Default is a single sequential job; `--loop --poll-interval 1` keeps consuming.
No guessed operator or organization is allowed. Only synthetic settings are accepted.
The existing `a1_process_inbox` command remains synchronous and writes terminal
receipts. Failed processing is visible on the Czech document page; **Obnovit stav**
refreshes pending/completed state, **Opakovat zpracování** retries a failed attempt.
Three attempts exhaust automatic processing; the operator investigates the private
`logs/ocr-worker.log` and opaque run/audit references. Interrupted claims become
eligible after the existing fifteen-minute lease; files and records remain durable.

Worker state edits, initial archived creation, archive and restoration enforce the
archive capability. Ordinary permitted editing continues. Permanent deletion is
unavailable until a distinct authorized retention/deletion workflow is defined.
This is a manual request to the responsible operator, not permission to delete SQL rows.

Official A1 PDF production is outside Jan core v1. The current extended `workflow`
command still covers optional A1 regression; splitting profiles is JAN-03. A SQLite
browser/lifecycle pass alone does not complete Delivery 1 or authorize activation.
