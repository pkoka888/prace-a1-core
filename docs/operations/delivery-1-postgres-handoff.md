# Delivery-1 PostgreSQL/private-site handoff (DRAFT) — sysadmin recipe

**STATUS: DRAFT — recipe complete, operator execution pending.** The
recipe now contains an explicit bind acceptance, a single consistent
environment contract, and a persistence acceptance that verifies the
exact pre-restart identifiers and artifact bytes (no replacement
rows). No host service, configuration or database change in this
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
- The application session pins `statement_timeout=500` (ms) itself
  (see `settings_supervised_synthetic.py`), so the cluster default
  does not matter for the rehearsal. Leave cluster settings alone.

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
real-browser authenticated journey (login + TOTP, worker, OP-card
upload + OCR confirm, address, assignment, A1 prepare, protected PDF
download, correction, regeneration). The `workflow` command prints a
JSON evidence document on stdout; **record `worker_pk`, `assignment_pk`,
`case_pk`, `regenerated_case_pk` and the artifact `sha256` values from
it** — the persistence acceptance below verifies those exact
identifiers after restart.

## Explicit bind acceptance (operator-owned)

Before the lifecycle run, confirm the database role can connect and
own the schema with exactly the values the application will use:

```bash
export PRACE_DB_NAME=prace_synthetic
export PRACE_DB_USER=prace_synth_app
export PRACE_DB_HOST=127.0.0.1
export PRACE_DB_PORT=5432
export PRACE_DB_PASSWORD=set-by-operator
PGPASSWORD="$PRACE_DB_PASSWORD" psql \
    -h "$PRACE_DB_HOST" -p "$PRACE_DB_PORT" \
    -U "$PRACE_DB_USER" -d "$PRACE_DB_NAME" -v ON_ERROR_STOP=1 \
    -c "select current_database() = '$PRACE_DB_NAME' as db_ok,
               current_user = '$PRACE_DB_USER' as user_ok;
         select count(*) = 0 as no_rows_before
           from information_schema.tables
          where table_schema = 'public';"
```

Loopback (`localhost`/`127.0.0.1`/`::1` or a `/`-prefixed Unix socket
path) is treated as local by the settings module: no `sslmode` is
required. Any other hostname is remote and **must** set
`PRACE_DB_SSLMODE=verify-full` plus `PRACE_DB_SSLROOTCERT`, or the
settings module refuses to load.

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

Capture the journey identifiers **before** the restart, then stop
and restart gunicorn and verify exactly those rows and artifact
bytes. The same pks must come back — a reappeared row with a new pk
would mean data was recreated, which this acceptance must reject.
Recording replacements is not allowed here; the restart must change
nothing.

```bash
# 1. Run the journey once and save its evidence.
bash scripts/rehearse_synthetic_site.sh workflow \
  > /var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json

# 2. Copy the exact identifiers from that evidence (do not guess).
export WORKER_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['worker_pk'])")"
export ASSIGNMENT_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['assignment_pk'])")"
export CASE_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['case_pk'])")"
export REGENERATED_CASE_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['regenerated_case_pk'])")"
export PDF_SHA256="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['stages']['a1_pdf_downloaded']['sha256'])")"

# 3. Restart without touching data.
bash scripts/rehearse_synthetic_site.sh stop
bash scripts/rehearse_synthetic_site.sh start

# 4. Verify the exact rows and the artifact bytes. Every check must
#    print exactly one row / file and the expected sha256.
env DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT=/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development \
    PRACE_SECRET_KEY="$(cat /etc/prace/secret.key)" \
    PRACE_ALLOWED_HOSTS=prace-v-nemecku.tvoje.info,127.0.0.1 \
    PRACE_DB_NAME=prace_synthetic PRACE_DB_USER=prace_synth_app \
    PRACE_DB_HOST=127.0.0.1 PRACE_DB_PORT=5432 \
    PRACE_DB_PASSWORD=set-by-operator \
    PRACE_RELEASE_MANIFEST=/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development/release_manifest.json \
    PRACE_RELEASE_MANIFEST_SHA256="$(cat /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-development/.release_manifest.sha256)" \
    WORKER_PK="$WORKER_PK" ASSIGNMENT_PK="$ASSIGNMENT_PK" \
    CASE_PK="$CASE_PK" REGENERATED_CASE_PK="$REGENERATED_CASE_PK" \
    PDF_SHA256="$PDF_SHA256" \
    venv/bin/python manage.py shell -c "
import os, hashlib
from pathlib import Path
from django.conf import settings
from portal.release1a.models import Worker, Assignment, A1Case, Document

checks = []
for model, pk in ((Worker, int(os.environ['WORKER_PK'])),
                  (Assignment, int(os.environ['ASSIGNMENT_PK'])),
                  (A1Case, int(os.environ['CASE_PK'])),
                  (A1Case, int(os.environ['REGENERATED_CASE_PK']))):
    qs = model.objects.filter(pk=pk)
    checks.append(f'{model.__name__} pk={pk}: {qs.count()} row(s)')
for label, pk in (('original', int(os.environ['CASE_PK'])),
                  ('regenerated', int(os.environ['REGENERATED_CASE_PK']))):
    case = A1Case.objects.get(pk=pk)
    key = (case.artifact_reference or {}).get('key')
    pdf = Path(settings.DOCUMENT_STORAGE_ROOT) / 'j4' / key / 'artifact.pdf'
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.is_file() else 'MISSING'
    checks.append(f'artifact {label}: exists={pdf.is_file()} sha256={digest}')
print('\\n'.join(checks))
"
```

Each `Worker`/`Assignment`/`A1Case` check must print exactly `1
row(s)`, both artifacts must print `exists=True`, and both sha256
values must equal the values printed by the journey's
`a1_pdf_downloaded` / `regeneration_differs` stages. None of these
checks creates or updates rows.

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
- It does not modify cluster defaults. The application session pins
  `statement_timeout=500` (ms) itself via the connection options in
  `settings_supervised_synthetic.py`; leave cluster settings alone.

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
