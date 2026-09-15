---
name: postgres-ops
description: Operate, debug, and extend PostgreSQL-backed rehearsal and test runs for this repository. Use for connection setup, migration, target selection, test database isolation, SQLite-vs-PostgreSQL flakiness diagnosis, retention/cleanup, or the supervised-synthetic settings module database contract.
---

# PostgreSQL operations

This skill links the canonical PostgreSQL configuration, settings contracts,
test isolation rules and cleanup procedures for the supervised synthetic
portal. Use it instead of inventing a second database layer or a separate
settings module.

## Ground the run

1. Read `AGENTS.md` first; real-data rules, the four-delivery sequence and
   the proportional validation cadence are authoritative.
2. Read the active `plans/2026-09-14-delivery-reliability-and-jan-v1.md`
   and `docs/operations/git-delivery.md` for the current PostgreSQL
   acceptance target and evidence requirements.
3. Inspect `git status` and `git log --oneline -5`; preserve unrelated work.
4. Confirm the local cluster is reachable: `psql -U <user> -d <db> -c 'SELECT 1;'`
   succeeds with the configured password.
5. Synthetic implementation does not require a running cluster; a missing
   target is unverified, not a failure. Do not silently downgrade a
   PostgreSQL-configured run to SQLite.

## Target contract

`portal.settings_supervised_synthetic` uses one all-or-none PostgreSQL
target or confined SQLite. Set all four `PRACE_DB_NAME`, `PRACE_DB_USER`,
`PRACE_DB_HOST`, `PRACE_DB_PORT`; omit all four for SQLite. A partial set
is rejected at import time with `ImproperlyConfigured`.

Local Unix socket:
```bash
export PRACE_DB_NAME="prace_synthetic"
export PRACE_DB_USER="prace_synth_app"
export PRACE_DB_HOST="/var/run/postgresql"
export PRACE_DB_PORT="5432"
export PRACE_DB_PASSWORD="<password>"
```

Remote TCP (requires explicit operator authorization):
```bash
export PRACE_DB_SSLMODE="verify-full"
export PRACE_DB_SSLROOTCERT="/path/to/ca.crt"
```

Runtime statement timeout defaults to 500 ms; override with
`PRACE_RUNTIME_STATEMENT_TIMEOUT_MS`. Migration timeout defaults to 60000 ms;
override with `PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`.

The settings module rejects symlinks on the SQLite database path and
confines the runtime root to operator-owned directories. PostgreSQL targets
bypass the SQLite symlink check but retain runtime-root confinement.

## Test database isolation

`portal.settings_document_tests` supports an explicit isolated PostgreSQL
test target via `DOCUMENT_TEST_PG_SOCKET` or `DOCUMENT_TEST_PG_NAME`. The
socket path must resolve inside the project `runtime/` tree. When neither
variable is set, tests fall back to SQLite in-memory.

```bash
export DOCUMENT_TEST_PG_SOCKET="/var/www/.../runtime/portal/supervised-<name>/pg.sock"
export DOCUMENT_TEST_PG_NAME="prace_synthetic_test"
export DOCUMENT_TEST_PG_USER="prace_synth_app"
# DOCUMENT_TEST_PG_PORT defaults to 55439 when socket is set
```

`settings_supervised_synthetic` no longer accepts `PRACE_TEST_DB_NAME`,
`PRACE_TEST_DB_USER`, `PRACE_TEST_DB_HOST` or `PRACE_TEST_DB_PORT`. That
test-variable mechanism is deprecated and any presence of those variables is
rejected at import time with `ImproperlyConfigured`. Use `DOCUMENT_TEST_PG_*`
(above, via `portal.settings_document_tests`) for isolated test targets.

The rehearsal lifecycle test (`tests/test_rehearse_workflow.py`) does not
use `pytest.mark.django_db`. Its subprocesses inherit `DJANGO_SETTINGS_MODULE`
and database env vars from the parent. Set `PRACE_DB_*` in the test's
`workflow_env` fixture to run the lifecycle against PostgreSQL.

## Migration and prepare

The canonical `prepare` subcommand runs:
```bash
bash scripts/rehearse_synthetic_site.sh prepare
```
It validates confinement, creates the runtime layout, writes the manifest,
runs `manage.py migrate --noinput` and `manage.py collectstatic --noinput`,
then re-asserts private permissions on the database file (SQLite only).

Migrations run with `DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic`
and inherit `PRACE_DB_*` from the environment. Django's migration tracking
is idempotent; rerunning `prepare` against an existing PostgreSQL target
reapplies pending migrations without recreating the schema.

## Implemented, defective and intended

Distinguish what is implemented, what is a known defect and what is the
intended repair (tracked in the active child plan's 2026-09-15 review
checkpoint). Do not present prose here as runtime proof.

Implemented (in source, observed behavior may still contain the listed
defects):

- The all-or-none `PRACE_DB_*` target contract and partial-set rejection at
  import time; the deprecated `PRACE_TEST_DB_*` variables are rejected.
- `DOCUMENT_TEST_PG_*`-scoped isolated test targets via
  `portal.settings_document_tests`.
- `scripts/rehearse_verify_persistence.py` exits 2
  (`PERSISTENCE_ACCEPTANCE_BLOCKED`) when the target is unavailable and
  supports `--profile core|optional-a1` in the current working tree.

Known defects (open, JAN-04 / JAN-03):

- Target forwarding from the rehearsal lifecycle to the configured
  `PRACE_DB_*` target is not verified end to end.
- Disposable-target cleanup is not verified against an exclusively owned
  target; cleanup behavior must be demonstrated before it is relied on.
- Migration credential scope (`PRACE_MIGRATION_DB_USER` /
  `PRACE_MIGRATION_DB_PASSWORD`) and the effective statement timeout
  (`PRACE_RUNTIME_STATEMENT_TIMEOUT_MS` /
  `PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`) exist in the working tree but are
  pending validation.
- The core/optional-A1 profile separation is partially implemented; A1-only
  requirements must not gate core acceptance.

Intended repairs are owned by JAN-04 (target forwarding, verified disposable
cleanup, migration credential scope, effective timeout, restart verification
of actual file bytes and exact records) and JAN-03 (profile separation).
Repair progress is recorded in the child plan and the delivery record, not by
editing this skill.

## Flakiness diagnosis

SQLite under gunicorn with concurrent requests can produce `database is
locked` or intermittent HTTP 500 errors. Switching the supervised target
to PostgreSQL removes the file-lock bottleneck. Symptoms:
- `OperationalError: database is locked` in gunicorn logs
- `IntegrityError` under concurrent write load
- Intermittent HTTP 500 on form submissions or document uploads

Remediation: run the affected test or rehearsal against PostgreSQL by
setting `PRACE_DB_*` in the environment. The rehearsal script and the
workflow test both forward these env vars to their subprocesses.

## Cleanup and retention

The operator owns PostgreSQL cluster lifecycle (start, configuration,
backup, recovery). Engineering prepares a scoped recipe and hands it to
the operator.

For local synthetic PostgreSQL targets:
- Use a dedicated database per acceptance run when possible.
- Do not bulk-delete rows; retention review owns cleanup.
- A killed gunicorn or worker process may leave unreferenced derivative
  files under `DOCUMENT_STORAGE_ROOT`; retention review owns cleanup.
- The `rehearse_verify_persistence.py` script exits 2
  (`PERSISTENCE_ACCEPTANCE_BLOCKED`) when the PostgreSQL target is
  unavailable, distinguishing transport failure from data mismatch.

## Avoid

- Do not silently downgrade a PostgreSQL-configured run to SQLite.
- Do not point test database creation or teardown at the operator database.
- Do not invent a second settings module; reuse
  `portal.settings_supervised_synthetic`.
- Do not run `manage.py migrate` directly against the operator database
  from a test runner without explicit test-target configuration.
- Do not commit protected paths (`a1/`, `scans/`, `data/`,
  `runtime/portal/`, `secrets/`, `.env`).

## Related references

- `AGENTS.md` — operational authority.
- `docs/operations/git-delivery.md` — implementation/validation/
  publication/deployment/activation record.
- `plans/2026-09-14-delivery-reliability-and-jan-v1.md` — JAN-04
  PostgreSQL acceptance target.
- `portal/settings_supervised_synthetic.py` — DATABASES and
  PRACE_DB_* contract.
- `portal/settings_document_tests.py` — DOCUMENT_TEST_PG_* test target.
- `scripts/rehearse_synthetic_site.sh` — canonical lifecycle with
  PRACE_DB_* forwarding.
- `tests/test_rehearse_workflow.py` — lifecycle test; set PRACE_DB_*
  in `workflow_env` for PostgreSQL target.
