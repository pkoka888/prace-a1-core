# Delivery-1 PostgreSQL/private-site handoff — application integration recipe

**STATUS: recipe — pending application repair and validation (JAN-04). The
infrastructure request is issued and awaiting the returned contract.**

## Application-side status: pending repair and validation

The recipe below describes the intended integration path, not a validated one.
The 2026-09-16 corrective audit at `a48a1e8` found remaining application
repairs as well as intended-host prerequisites. The
[active plan](../../plans/2026-09-14-delivery-reliability-and-jan-v1.md) owns the
current TODOs, evidence, validation and owners; the
[delivery record](git-delivery.md) owns publication.

Application repairs (JAN-04/REL-03) are not infra-only blockers: integrate the
missing committed shell migration-scope dependency; verify independently provisioned
exclusive disposable targets before mutation; repair the invalid mixed-meta/SQL psql
probe; propagate target selection, migration credentials and TLS through every
subprocess. The owned-cluster audit reproduced the probe failure without using host
credentials. The current workflow writes its own ownership record and performs
table-wide cleanup, so it must not run against an arbitrary/shared/operator DB.

JAN-03 is partial: the browser helper supports `core|optional-a1`, but the lifecycle
still unconditionally calls A1 sparse assertions and the default release reproducer
omits the browser/restart journey. Actual source-byte checks are implemented; the
standalone persistence command does not perform a restart. A successful local hook
runs working-tree bytes and does not certify the committed candidate.

Infrastructure independently returns/reconciles the
[target contract](servers-infra-core-postgresql-request.md): current authentication,
supervision/listener ownership, approved build and route. Fresh audit observations
show PostgreSQL running, application service failed and a port 8001 listener; no
new authentication test was performed and no live secret payload read. An
infrastructure response alone cannot close application defects or JAN-04 acceptance.

Engineering can continue synthetic contracts and an owned in-project PostgreSQL
cluster using the existing ephemeral harness pattern. This is separate from host
services and does not prove the deployed target. A missing intended target is
blocked/unverified; do not substitute SQLite acceptance. After repairs, execute one
committed-source core scenario against the selected intended route/PG target, then
Jan's observed use. Real-data activation and PG5 backup/restore remain separate.

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
- Intended roles: a restricted runtime login for application reads/writes and a
  separately scoped migration identity for schema changes. No runtime `SUPERUSER`,
  `CREATEROLE` or `CREATEDB`; verify effective privileges in the returned contract.
  Source settings alone do not prove the deployed role separation.
- Default `search_path` is acceptable; the application uses
  unqualified table names.
- The application runtime uses a per-session `statement_timeout` of
  500 ms by default (configurable via `PRACE_RUNTIME_STATEMENT_TIMEOUT_MS`).
  Migrations use a separate command-scoped longer timeout
  (`PRACE_MIGRATION_STATEMENT_TIMEOUT_MS`, default 60000 ms). The
  readiness probe reads the configured runtime timeout from settings,
  not a hardcoded value. Leave cluster-wide defaults alone.

## Database and role creation (operator-owned)

Infrastructure provisions the selected database, runtime and migration roles,
explicit schema privileges and secret references under its own authorization.
Consume the returned contract; do not copy a generic superuser SQL example into
an unknown cluster or grant schema ownership to the runtime role by default.
An engineering-owned disposable cluster has its own verified provisioning/teardown
identity and must never reuse the deployed database or secret-file payload.

## Lifecycle invocation (operator-owned)

The selected live owner is `prace-v-nemecku-gunicorn.service`. Its configured
EnvironmentFile is `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`;
see [runtime configuration policy](runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
Systemd reads this file itself. Do not export secrets through `grep`, `cut`, `cat`
or shell sourcing, and do not mix it with the checkout tool `.env`.

`scripts/rehearse_synthetic_site.sh` remains the canonical **disposable rehearsal**
lifecycle. Select a separate root, bind and synthetic credentials under its existing
contract; never prepare/provision/start it against the live supervised-synthetic root
or port 8001. Its prepare/provision/start/smoke/workflow sequence is not a second live
supervisor and must not overwrite a live manifest.

Manifest approval comes from the selected release/build, not from copying the
current `.release_manifest.sha256` marker. The reported env-pin mismatch and
application-authenticated PostgreSQL identity remain unresolved until independently
verified. Runtime path relocation alone authorizes neither a repin, credential
rotation nor restart. Temporary public hostname remains `prace-v-nemecku.expc.cz`.

Disposable workflow evidence must preserve exact synthetic record/file identities
for later persistence assertions. Core/optional-A1 gates, JAN-01–04 and PG5 remain
separate; a source documentation change does not establish their acceptance.

## Explicit target acceptance (operator-owned)

For the existing operator database, use authorized read-only identity/schema checks
against the selected transport and record `current_database`, `current_user` and
effective `search_path`. An empty schema is **not** an acceptance criterion for the
existing `prace_synthetic` database: the September 16 administrative observation
recorded 43 public base tables. Do not drop, truncate, recreate or reset that database
to make an empty-table assertion pass. Runtime-role authentication remains a separate
check; the earlier administrative observation does not prove it.

A zero-table precondition applies only to a newly created, explicitly disposable,
fixture-owned database with verified creation/teardown boundaries. It must use a
separate test identity and synthetic credentials, never copied from the live service
EnvironmentFile. Absence, access failure and empty schema are different outcomes.

Loopback or a Unix socket is local under the current settings contract; remote TCP
requires `PRACE_DB_SSLMODE=verify-full` and `PRACE_DB_SSLROOTCERT`. Verify transport
and effective access rather than modifying HBA from generic login failure.

## Acceptance procedure

**Live service:** infrastructure first establishes the selected systemd supervisor,
approved release/configuration and database identity through its reviewed operational
procedure. Then use its declared endpoint for read-only health/readiness checks and
an explicitly scoped synthetic login/protected-document/OCR journey. Preserve each
native result independently. HTTP success alone is not database or workflow acceptance.
This document gives no manual server-start command and authorizes no restart.

**Disposable rehearsal:** before any lifecycle command, select and record all of:

- Canonical checkout working directory and `A1_PRIVATE_DIR` matching that checkout.
- A uniquely owned disposable `PRACE_RUNTIME_ROOT`, never the live supervised-synthetic
  root; independently validate its approved source/manifest before preparation.
- A test-owned bind/port that is not live port 8001, plus an ownership guard that refuses
  a foreign listener. Do not rely on helper defaults.
- A disposable SQLite or PostgreSQL target with verified create/cleanup boundaries,
  independent synthetic credentials and no live secret-file reuse.
- One fixture-owned supervisor, private evidence destination and cleanup ownership.

Only that isolated context may run the existing rehearsal prepare/provision/start/
smoke/workflow/stop lifecycle. If the current helper cannot accept and enforce the
selected disposable root/bind, fix and test it before running; do not fall back to
live defaults. The canonical code and existing fixture tests define supported flags.

## Persistence acceptance

Capture exact synthetic organization, worker, document and assignment identifiers
and original document bytes before restart, with the selected target and release.
For the core profile, verify those same records, relationships and exact bytes after
restart; recreated rows with new identifiers do not pass. Optional A1 case/PDF checks
remain a separate profile and do not gate the core workflow.

For the live target, only the infrastructure-owned supervisor performs an authorized
restart after recovery and process-ownership prerequisites pass. Never use rehearsal
stop/start against the live listener. For a disposable target, the fixture's exclusive
supervisor may restart only its recorded processes after rechecking identity/start
information and target boundaries. Neither route may rebuild, reseed or overwrite
state during the persistence check.

The existing `scripts/rehearse_verify_persistence.py` and workflow tests provide
record/byte assertions; prepare their required nonsecret synthetic identifiers in
the same explicitly selected context. Unavailable PostgreSQL is blocked, not a pass;
wrong target, missing inputs, record mismatch or byte mismatch fail acceptance. Keep
private records/evidence inside the authorized private runtime, outside source reports.

## Recovery procedure

- **Process ownership:** infrastructure owns live service adoption/stop/restart and
  checks current executable, start identity and supervisor. Rehearsal PID/rollback
  helpers apply only to their explicitly owned disposable fixture, never live port 8001.
- **Database failure:** distinguish transport, authentication and target errors with
  authorized read-only checks; report uncertainty. Do not reset a password or restart
  Gunicorn simply because a connection fails.
- **Migration drift:** inspect the approved migration plan and target first. Apply
  through the separately scoped migration identity/procedure; never use fake migration
  state to hide divergence or rerun fixture provisioning on operator data.
- **Rollback:** infrastructure selects an approved compatible release/configuration and
  recovery path for live operation. Never blindly adopt current mutable manifests,
  restore exposed credentials, delete the live root, or use rehearsal rollback as a
  live recovery command. Disposable cleanup may remove only its verified owned target.
- **Restore:** actual consistent database-plus-protected-files recovery remains PG5,
  with a named owner, isolated restore proof and agreed recovery objectives. Path
  retirement, documentation or a successful health probe does not close that gate.

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
