# Delivery-1 PostgreSQL/private-site handoff — application integration recipe

**STATUS: recipe — pending application repair and validation (JAN-04). The
infrastructure request is issued and awaiting the returned contract.**

## Application-side status: pending repair and validation

The recipe below describes the intended integration path, not a validated one.
A 2026-09-15 review checkpoint confirmed application-side defects that must be
repaired and revalidated before PostgreSQL acceptance (JAN-04):

- **Target forwarding** from the rehearsal lifecycle to the configured
  `PRACE_DB_*` target is not yet verified end to end.
- **Disposable-test-target cleanup** is not yet verified against an exclusively
  owned target; cleanup behavior must be demonstrated, not presumed.
- **Migration credential scoping** (`PRACE_MIGRATION_DB_USER` /
  `PRACE_MIGRATION_DB_PASSWORD`) and the **effective statement timeout**
  (`PRACE_RUNTIME_STATEMENT_TIMEOUT_MS` /
  `PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`) exist in the current working tree but
  are pending validation.
- **Restart persistence** must verify actual file bytes and exact records, and
  has not passed against the intended PostgreSQL target.

The PostgreSQL target acceptance that completes JAN-04 is **blocked on both
application repair and the infrastructure response** from
`servers-infra-core`. The application team has issued
[the infrastructure request](servers-infra-core-postgresql-request.md)
(v1.0) and is awaiting the returned contract with verified database, roles,
credentials, TLS, backup/restore and operational ownership.
**An infrastructure response alone cannot close JAN-04**: the defects above
must be repaired and revalidated against the returned target, and one
committed-source core acceptance run must pass, before any acceptance claim.

**This repository does not provision host services, databases, roles or
credentials.** The `servers-infra-core` task runs on a separate host under
its own authorization; its owner chooses hosts, versions, ports, transport,
schemas and service arrangements. The application team only forwards the
request and consumes the returned nonsecret contract values plus secret
references.

Until the infrastructure response arrives:
- Local synthetic implementation continues against the default SQLite target.
- The `PRACE_DB_*` contract, migration credential scoping and test isolation
  repairs in `portal/settings_supervised_synthetic.py` exist in the current
  working tree and are **pending repair and validation** before they are
  treated as ready to consume the returned target.
- The `--profile core|optional-a1` separation, the canonical persistence
  verifier and the release verifier's required-check declaration are partially
  implemented in the working tree; validation is pending (JAN-03/JAN-04).
- Required regressions (ignored/partial target configuration, wrong-target
  cleanup refusal, simultaneous-run refusal, cleanup failure, actual
  migration timeout, historical migration transitions, PostgreSQL concurrency,
  core success without A1, required-check failure propagation, missing/
  corrupted files, unavailable PostgreSQL) remain defined; they execute
  against the returned target when it is available.

**Local synthetic implementation does not require a running PostgreSQL
cluster.** A missing or unavailable target is reported as unverified or
blocked environment, never downgraded to a SQLite PASS.
The recipe describes an explicit bind acceptance, a single consistent
environment contract, a canonical persistence-acceptance script and a
persistence acceptance that verifies exact pre-restart identifiers
and actual file bytes (no replacement rows) — as the intended target,
with the defects listed above still pending repair and validation. No host
service, configuration or database change in this repository activates this
recipe. See the [infrastructure request](servers-infra-core-postgresql-request.md)
for the values the infrastructure team must provide, and
[`plans/2026-09-14-delivery-reliability-and-jan-v1.md`](../../plans/2026-09-14-delivery-reliability-and-jan-v1.md)
for the bounded JAN-01–04 task ownership and the 2026-09-15 review checkpoint.

## Scope

Application-side recipe: environment variable contract, lifecycle
invocation, acceptance commands, recovery steps and PostgreSQL-target
configuration. The supervised synthetic settings module
`portal.settings_supervised_synthetic` is synthetic-only by design.
Switching to PostgreSQL does not enable real-data operations; the
intake service still refuses non-synthetic configuration until a
separately approved activation gate.

Official A1 PDF generation and issuance are outside v1 by explicit
direction on 2026-09-14. Existing draft PDFs are optional. Missing A1
fields must not block worker saving or acceptance of the core workflow.
This recipe no longer treats optional A1 artifacts as mandatory for
persistence or workflow acceptance.

## Infrastructure request (prerequisite)

Before executing this recipe, the infrastructure team must complete and
return the contract in
[`docs/operations/servers-infra-core-postgresql-request.md`](servers-infra-core-postgresql-request.md).
Application-side preparation does not authorize host changes or
credential delivery. The recipe below consumes the returned values;
unknown or missing values block PostgreSQL acceptance with an explicit
message, never a silent fallback to SQLite during PostgreSQL acceptance.

## Required credentials (operator-supplied via infrastructure secret management)

| Variable | Purpose | Source |
|---|---|---|
| `PRACE_DB_NAME` | database name | infrastructure contract |
| `PRACE_DB_USER` | database role | infrastructure contract |
| `PRACE_DB_HOST` | bind host or socket path | infrastructure contract |
| `PRACE_DB_PORT` | bind port | infrastructure contract |
| `PRACE_DB_PASSWORD` | role password | secret reference from infrastructure |
| `PRACE_DB_SSLMODE` | TLS posture | infrastructure contract (omit for loopback/socket) |
| `PRACE_DB_SSLROOTCERT` | CA bundle path | infrastructure contract (required for remote verify-ca/verify-full) |

Return references, never secret values. The supervised synthetic
settings module refuses to start unless all four `PRACE_DB_NAME`,
`PRACE_DB_USER`, `PRACE_DB_HOST`, `PRACE_DB_PORT` are set; remote TCP
additionally requires `PRACE_DB_SSLMODE=verify-full` and a populated
`PRACE_DB_SSLROOTCERT`. Omitting all four PostgreSQL variables permits
the default SQLite target; a partial set (some but not all four) is
rejected with `ImproperlyConfigured`. During PostgreSQL acceptance a
missing or partial set blocks acceptance; it never silently substitutes
SQLite and reports PASS.

## PostgreSQL cluster target

The values below are historical observations from the September 12
document; they require fresh verification and may differ from the
infrastructure team's selected target.

- PostgreSQL version: as selected by infrastructure and returned in the
  contract. Django 5.2 supports PostgreSQL 14+; infrastructure selects
  a currently supported fleet version.
- A dedicated database role with login and schema-owning rights on
  the application schema; no `SUPERUSER`, no `CREATEROLE`, no
  `CREATEDB`. The supervised synthetic settings module does not need
  to create databases or roles at runtime.
- Default `search_path` is acceptable; the application uses
  unqualified table names.
- The application runtime uses a per-session `statement_timeout` of
  500 ms by default (configurable via `PRACE_RUNTIME_STATEMENT_TIMEOUT_MS`).
  Migrations use a separate command-scoped longer timeout
  (`PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`, default 60000 ms). The
  readiness probe reads the configured runtime timeout from settings,
  not a hardcoded value. Leave cluster-wide defaults alone.

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
# PostgreSQL target (all four set together; omit all four to use SQLite).
export PRACE_DB_NAME=prace_synthetic
export PRACE_DB_USER=prace_synth_app
export PRACE_DB_HOST=127.0.0.1
export PRACE_DB_PORT=5432
export PRACE_DB_PASSWORD=set-by-operator
# PRACE_DB_SSLMODE / PRACE_DB_SSLROOTCERT only for remote TCP.
export PRACE_RELEASE_MANIFEST="$PRACE_RUNTIME_ROOT/release_manifest.json"
export PRACE_RELEASE_MANIFEST_SHA256="$(cat "$PRACE_RUNTIME_ROOT/.release_manifest.sha256")"
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
export ORG_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['organization_id'])")"
export WORKER_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['worker_pk'])")"
export DOCUMENT_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['document_pk'])")"
export DOCUMENT_SHA256="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['document_sha256'])")"
export ASSIGNMENT_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['assignment_pk'])")"
# Optional A1 identifiers (only for optional-a1 profile):
export CASE_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['case_pk'])")"
export REGENERATED_CASE_PK="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['regenerated_case_pk'])")"
export PDF_SHA256="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['stages']['a1_pdf_downloaded']['sha256'])")"
export REGEN_SHA256="$(python -c "import json;print(json.load(open('/var/www/prace-v-nemecku.tvoje.info/runtime/portal/evidence.workflow.json'))['stages']['regeneration_differs']['sha256'])")"

# 3. Restart without touching data.
bash scripts/rehearse_synthetic_site.sh stop
bash scripts/rehearse_synthetic_site.sh start

# 4. Verify the exact rows and the artifact bytes with the canonical
#    acceptance script. Use --profile core for worker/document/assignment
#    only; use --profile optional-a1 to additionally verify A1 identifiers.
#    Exit 0 means every check passed; any other exit blocks publication.
cd "$A1_PRIVATE_DIR"
# Core profile (no A1 identifiers required):
venv/bin/python scripts/rehearse_verify_persistence.py \
  --profile core
# Optional A1 profile (requires CASE_PK, REGENERATED_CASE_PK, PDF_SHA256, REGEN_SHA256):
# venv/bin/python scripts/rehearse_verify_persistence.py \
#   --profile optional-a1
```

The script reuses the same post-restart query logic exercised by
`tests/test_rehearse_workflow.py`: it queries the supervised database
for the worker, document, assignment and their relationships captured
during the browser journey. The `core` profile verifies document
existence, the worker→document and worker→assignment links, and the
document's stored SHA-256 hash against `DOCUMENT_SHA256`. The
`optional-a1` profile additionally verifies A1 case rows and the
artifact bytes on disk. It exits non-zero with an actionable message
on mismatch or missing configuration. When the PostgreSQL target is
unavailable the script exits 2
(`PERSISTENCE_ACCEPTANCE_BLOCKED`) so the operator can distinguish a
transport failure from a data mismatch.

For `core` profile, the required environment variables are:
`ORG_PK`, `WORKER_PK`, `DOCUMENT_PK`, `DOCUMENT_SHA256`,
`ASSIGNMENT_PK`. A1 identifiers (`CASE_PK`, `REGENERATED_CASE_PK`,
`PDF_SHA256`, `REGEN_SHA256`) are required only for the
`optional-a1` profile.

Each row check must print `ok`; the document hash check must print
`sha256=matched`. None of these checks creates or updates rows.

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
- It does not approve any activation gate; the supervised-synthetic
  settings module continues to fail closed against real-data intent.
- It does not change GitHub remotes, CI configuration or
  protected-path policies.
- It does not modify cluster defaults. The application runtime uses
  `PRACE_RUNTIME_STATEMENT_TIMEOUT_MS` (default 500 ms) via the
  connection options in `settings_supervised_synthetic.py`; migrations
  use the separately passed `PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`
  (default 60000 ms). The readiness probe reads the configured runtime
  timeout from settings. Leave cluster settings alone.
- It does not require official A1 PDF generation/issuance for
  PostgreSQL acceptance or workflow success; optional A1 artifacts are
  independently reportable via the `--profile optional-a1` flag.

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
