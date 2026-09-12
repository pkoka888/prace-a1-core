# Delivery-1 PostgreSQL/private-site handoff (DRAFT) — sysadmin recipe

**STATUS: DRAFT.** The operator adapts the values below to the authorized
target. No host service, configuration or database change in this
repository activates this draft. See
`plans/2026-09-08-local-a1-automation.md` § Delivery alignment for the
engineering-side evidence and § PostgreSQL handoff for the open gap.

## Scope

Scoped database/user, environment variable contract, lifecycle
invocation, acceptance commands and recovery steps. The supervised
synthetic settings module `portal.settings_supervised_synthetic` is
synthetic-only by design. Switching to PostgreSQL does not enable
real-data operations; the intake service still refuses non-synthetic
configuration until REV-003.

## Required credentials (operator-supplied)

| Variable | Purpose | Example shape |
|---|---|---|
| `PRACE_DB_NAME` | database name | `prace_synthetic` |
| `PRACE_DB_USER` | database role | `prace_synth_app` |
| `PRACE_DB_HOST` | bind host | `127.0.0.1` |
| `PRACE_DB_PORT` | bind port | `5432` |
| `PRACE_DB_PASSWORD` | role password | `<set by operator>` |
| `PRACE_DB_SSLMODE` | TLS posture | `verify-full` for remote; omit for loopback |
| `PRACE_DB_SSLROOTCERT` | CA bundle path | `/etc/prace/db-ca.pem` |

The supervised synthetic settings module refuses to start unless
all four `PRACE_DB_NAME`, `PRACE_DB_USER`, `PRACE_DB_HOST`,
`PRACE_DB_PORT` are set; remote TCP additionally requires
`PRACE_DB_SSLMODE=verify-full` and a populated
`PRACE_DB_SSLROOTCERT`.

## PostgreSQL cluster target

- PostgreSQL 18 (matching the existing binaries on the host).
- A dedicated database role with login and schema-owning rights on
  the application schema; no `SUPERUSER`, no `CREATEROLE`, no
  `CREATEDB`. The supervised synthetic settings module does not need
  to create databases or roles at runtime.
- Default `search_path` is acceptable; the application uses
  unqualified table names.
- `statement_timeout` is left at the cluster default unless the
  operator observes slow readiness probes under load.

## Database and role creation (operator-owned)

Run as a PostgreSQL superuser:

```sql
CREATE ROLE prace_synth_app LOGIN PASSWORD 'set-by-operator';
CREATE DATABASE prace_synthetic OWNER prace_synth_app;
GRANT ALL PRIVILEGES ON DATABASE prace_synthetic TO prace_synth_app;
\c prace_synthetic
GRANT ALL ON SCHEMA public TO prace_synth_app;
```

The migration command (`manage.py migrate`) will create all Release 1A
tables in the `public` schema; no DDL pre-steps are required.

## Lifecycle invocation (operator-owned)

This recipe uses the canonical rehearsal script. Running
`scripts/rehearse_synthetic_site.sh` produces a runtime root under
`runtime/portal/supervised-<name>/` that the same script later
manages (start/stop/restart/rollback), and that
`scripts/rehearse_dev_local.sh` persists a stable signing key
across ordinary invocations. The handoff reuses that lifecycle; it
does not invent a parallel one.

```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
export PRACE_RUNTIME_ROOT="/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development"
export PRACE_SECRET_KEY="$(cat /etc/prace/secret.key)"
export PRACE_ALLOWED_HOSTS=prace-v-nemecku.tvoje.info,127.0.0.1
export PRACE_DB_NAME=prace_synthetic
export PRACE_DB_USER=prace_synth_app
export PRACE_DB_HOST=127.0.0.1
export PRACE_DB_PORT=5432
export PRACE_DB_PASSWORD=set-by-operator
# PRACE_DB_SSLMODE / PRACE_DB_SSLROOTCERT only for remote TCP.
cd "$A1_PRIVATE_DIR"
bash scripts/rehearse_synthetic_site.sh prepare
bash scripts/rehearse_synthetic_site.sh provision
bash scripts/rehearse_synthetic_site.sh start
bash scripts/rehearse_synthetic_site.sh smoke
bash scripts/rehearse_synthetic_site.sh workflow
```

`prepare` records the supervised release manifest, runs `migrate`
and `collectstatic`. `provision` writes the synthetic operator +
organization + MFA. `start` launches gunicorn, verifies the bind, and
records the launch identity so a later `stop` refuses wrong PIDs.
`smoke` exercises the typed JSON contract; `workflow` runs the
real-browser authenticated journey.

## Acceptance commands

Run on the host after gunicorn is up:

```bash
# 1. /health/ must report the supervised contract.
curl -sS -H "Host: 127.0.0.1" http://127.0.0.1:8001/health/ | python -m json.tool

# 2. /readiness/ must report ready under the configured budget.
curl -sS -H "Host: 127.0.0.1" http://127.0.0.1:8001/readiness/ | python -m json.tool

# 3. Rehearsal script's smoke probe.
bash scripts/rehearse_synthetic_site.sh smoke

# 4. Real-browser journey end-to-end (requires Playwright + Chromium).
bash scripts/rehearse_synthetic_site.sh workflow
```

## Persistence acceptance

Stop and restart gunicorn, then confirm the journey's records
survive the restart:

```bash
bash scripts/rehearse_synthetic_site.sh stop
bash scripts/rehearse_synthetic_site.sh start
bash scripts/rehearse_synthetic_site.sh workflow   # creates new journey records

# Query-after-restart against the supervised PostgreSQL.
env DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT=/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development \
    PRACE_SECRET_KEY="$(cat /etc/prace/secret.key)" \
    PRACE_DB_NAME=prace_synthetic PRACE_DB_USER=prace_synth_app \
    PRACE_DB_HOST=127.0.0.1 PRACE_DB_PORT=5432 \
    PRACE_DB_PASSWORD=set-by-operator \
    venv/bin/python manage.py shell -c "
from portal.release1a.models import Worker, A1Case
print('workers:', Worker.objects.count(), 'cases:', A1Case.objects.count())
"
```

A non-zero record count is positive evidence. Operators confirm
the records match the journey's printed `worker_pk`,
`document_pk` and `case_pk` from the previous workflow run.

## Recovery steps

- **Stale gunicorn pidfile**: `bash scripts/rehearse_synthetic_site.sh
  stop` reads `/proc/<pid>/cmdline` and refuses to signal an
  unrelated process. Inspect the pidfile contents and remove them
  only when the recorded pid is confirmed dead.
- **Database connection refused**: confirm the cluster is up
  (`pg_isready -h $PRACE_DB_HOST -p $PRACE_DB_PORT`) and that
  `pg_hba.conf` accepts the role from the gunicorn host over the
  configured transport. Restart gunicorn after fixing the cluster.
- **Migration drift**: `manage.py migrate --plan` shows pending
  operations; commit-and-run `manage.py migrate` to apply them.
  Never use `--fake` to hide divergence; investigate first.
- **Rollback**: `bash scripts/rehearse_synthetic_site.sh rollback`
  stops the server and preserves the runtime root. The operator
  removes the runtime root manually after inspecting the logs and
  the manifest. PostgreSQL data is preserved; restoration requires
  a separate backup/restore authorization.

## What this recipe does NOT do

- It does not flip `M2_SYNTHETIC_ONLY`; real-data operations remain
  refused by the intake service.
- It does not approve `REV-003`; the supervised-synthetic settings
  module continues to fail closed against real-data intent.
- It does not change GitHub remotes, CI configuration or
  protected-path policies.

## Authorization reminder

The cluster start, the database creation and the systemd
configuration are sysadmin-owned. Engineering prepares this recipe
and walks the operator through the steps; only the operator executes
host-level changes.

## Catalog ownership

This handoff is a *delivery recipe*, not a *runtime* change. The
canonical rehearsal script (`scripts/rehearse_synthetic_site.sh`)
already owns the lifecycle commands and is registered in
`change-packages.yml` under `delivery_lifecycle_rehearsal`. The
handoff's lifecycle invocation therefore inherits the existing
catalog ownership; this document does not need a separate
package entry.
