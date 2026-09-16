---
name: postgres-ops
description: Operate, debug, and extend PostgreSQL-backed rehearsal and test runs for this repository. Use for connection setup, migration, target selection, test database isolation, SQLite-vs-PostgreSQL flakiness diagnosis, retention/cleanup, or the supervised-synthetic settings module database contract.
---

# PostgreSQL operations

Use the existing settings, lifecycle and PostgreSQL harness. Read `AGENTS.md`,
the [active plan](../../../plans/2026-09-14-delivery-reliability-and-jan-v1.md)
and [delivery record](../../../docs/operations/git-delivery.md) for current scope,
source identity and evidence. Inspect branch/index/worktree before executing;
a working-tree fix may be absent from the selected commit.

## Select the operation and target

Distinguish application-owned disposable integration from operator-owned deployed
acceptance. Engineering may use the in-project ephemeral PostgreSQL pattern in
`scripts/test_document_intake.py` (unique private root, Unix socket, no TCP
listener, owned initdb/pg_ctl lifecycle). It does not use host credentials or prove
the live target. Do not run its broad suite unless relevant to the change.

The operator owns host services, cluster configuration, credentials and recovery.
Consume its explicitly returned target/secret references through the approved
injection mechanism; never obtain a test credential by reading the live secret file.
The selected EnvironmentFile is
`/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`; keep it separate
from checkout `.env`, do not shell-source/print/copy/hash its payload, and follow
[the runtime policy](../../../docs/operations/runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
Path deployment does not prove authentication, release approval or service recovery.

## Connection contracts

`portal.settings_supervised_synthetic` selects PostgreSQL with all four nonempty
`PRACE_DB_NAME`, `PRACE_DB_USER`, `PRACE_DB_HOST`, `PRACE_DB_PORT`; no target selects
confined SQLite, partial target is rejected. Password comes from the selected
identity's approved mechanism. Remote TCP additionally requires
`PRACE_DB_SSLMODE=verify-full` and `PRACE_DB_SSLROOTCERT`. Never interpret SQLite
success as requested PostgreSQL acceptance. The settings remain synthetic-only.

`portal.settings_document_tests` and `portal.settings_browser_tests` use
`portal/test_pg_contract.py::resolve_test_postgres_target`. Configure an explicitly
owned test name/user plus exactly one of `DOCUMENT_TEST_PG_SOCKET` (resolved within
project runtime) or `DOCUMENT_TEST_PG_HOST`. TCP requires `DOCUMENT_TEST_PG_PASSWORD`;
socket defaults to port 55439, TCP to 5432 unless explicit. Use the selected test
role, not the live application's identity. `PRACE_TEST_DB_*` is deprecated and
rejected by supervised settings.

Boundary defects (resolver treated empty variables as absent and accepted
whitespace name/user after stripping) are closed at `c24a293` plus the
incremental repair: `resolve_test_postgres_target` now refuses an explicitly
exported blank/whitespace `DOCUMENT_TEST_PG_NAME` or `DOCUMENT_TEST_PG_USER`
with an actionable `RuntimeError`. Empty variables still select SQLite by
design — that is the no-target rehearsal default. Live owned-cluster
normalization remains under JAN-04.

For transport diagnostics specify host/socket, port, database and user explicitly;
`pg_isready` alone proves no application authentication. Avoid command-line passwords.
Record a nonsecret target label and result; keep source values and credentials out
of logs. Do not infer an HBA repair or password reset from an undifferentiated error.

## Disposable-target ownership and lifecycle

Before any test migration or cleanup, establish independently that provisioning
created the exact exclusively owned disposable target. A database name denylist,
`PRACE_DISPOSABLE_TARGET=1`, or a record written by the consumer is insufficient.
Use a per-run target and an ownership record bound to provisioning/run/target;
retain ownership across setup, workload and teardown. A cooperating advisory lock
can coordinate those clients; it cannot exclude clients that never take the lock.

**Current limitation (JAN-04):** `tests/test_rehearse_workflow.py` still writes its
own ownership record, invokes the guard only during cleanup, and uses table-wide
DELETEs. Do not run this PostgreSQL lifecycle against a shared/operator database.
The existing guard is not proof that an arbitrary configured target is safe.
`scripts/disposable_pg_guard.py::_try_exclusive_lock` also mixes a psql meta-command
and SQL in one `-c` argument; the 2026-09-16 owned-cluster audit reproduced failure
on a reachable target. Fix invocation and real-cluster negative/positive cases
before using this path as acceptance evidence. No new user approval is needed for
those authorized source repairs.

For corrected cleanup, verify scope before mutation, hold the needed ownership
through the operation, and propagate native errors. Exercise wrong-target,
simultaneous-run, partial failure and successful cleanup against owned synthetic
PostgreSQL. Preserve operator data and private retention artifacts; no bulk cleanup
of live roots. Stop only processes bound to the fixture's launch identity before
removing its uniquely owned cluster directory.

## Migration identity and forwarding

Runtime timeout defaults to 500 ms (`PRACE_RUNTIME_STATEMENT_TIMEOUT_MS`), migration
timeout to 60000 ms (`PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`). The settings select
migration credentials/timeout only with `PRACE_MIGRATION_SCOPE=1`; the intent is a
single migration command, never a globally exported flag inherited by web/worker.
Ordinary runtime must retain its restricted role even when a migration credential
pair is available to the launcher.

At audit baseline `a48a1e8` the workflow fixture dropped the migration pair, the
export omitted `PRACE_WORKFLOW_PG`, and the psql guard/cleanup did not map
`PRACE_DB_SSLMODE/SSLROOTCERT` to libpq options. `c24a293` (`d0903a8`)
forwarded the migration pair and mapped the TLS variables (`PGSSLMODE` /
`PGSSLROOTCERT`); the subsequent incremental repair forwards `PRACE_WORKFLOW_PG`.
Inspect the caller's export before claiming forwarding is complete. Verify
actual `current_user`, `statement_timeout` and target on owned PostgreSQL;
import-only settings tests cannot prove command scope. Do not print credential
values.

## Validation and diagnosis

Use focused regressions for resolver/forwarding logic; use a real owned cluster
for lock semantics, effective role/timeout, historical migrations and concurrency.
Mocks prove only refusal/control flow. Follow AGENTS.md's commit-hook cadence and
read failing reports before reruns; do not duplicate broad integration by default.

Separate server HTTP errors, authentication redirects, OCR state and browser wait
timeouts. A successful retry does not identify a cause. Check the actual error
line, not error-name literals in pytest's displayed source. SQLite lock contention
requires corresponding evidence; selecting PostgreSQL does not itself diagnose
or fix a browser `networkidle` timeout. Record source/settings and bounded timing
or request evidence for the affected transition.

## Intended-target persistence acceptance

Once application defects and the infrastructure contract are resolved, run the
committed-source core browser/restart scenario on the explicitly selected target.
The current default `scripts/release_reproducer.sh <commit-sha>` omits that scenario;
JAN-03/REL-03 must extend it before it can be called complete core acceptance.

`scripts/rehearse_verify_persistence.py --profile core` verifies supplied exact
worker/document/assignment identifiers, relationships and stored source bytes.
Supply its required environment or journey receipt in the same target context;
it does not restart the service. The authorized target owner performs restart
without reseeding, then the same IDs/bytes/corrected values are checked. Optional
A1 rows/PDFs belong to `--profile optional-a1`. A mismatch fails; unavailable target
is blocked/unverified (exit 2). Broad exception classification remains a plan item.
Neither a local PostgreSQL probe nor this verification alone grants Jan acceptance,
real-data activation or the separate backup-plus-files restore gate.
