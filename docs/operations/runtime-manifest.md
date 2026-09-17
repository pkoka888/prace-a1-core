# Application runtime manifest

**Status:** Application engineering implemented; target deployment unverified
**Date:** 2026-09-07
**Parent:** PLAN-INFRA; no activation gate opens from this document

Current evidence: [runtime/J4 engineering](../research/2026-09-07-runtime-j4-engineering.md).
Historical infrastructure packet: [review](../research/2026-09-07-infra-application-review.md).
The working tree, including untracked migrations and helpers, is not a published release.

## Target and configuration

The proposed host target remains `prace-synthetic-s62-v1`, with proposed identity
`prace-synthetic` and root `runtime/portal/supervised-synthetic/`. These host resources
have not been provisioned or verified by the application tests.

Implemented settings: `portal.settings_supervised_synthetic`. DEBUG=False and
synthetic-only are fixed. Runtime root must be an owner-only, UID-owned direct
`supervised-*` child of project runtime/portal. Its ancestors and child paths reject
symlinks. Storage/media/static/cache/tmp/log children are private; Python temporary
files use tmp. No blanket access to existing A1/scans/evidence/output is required.

| Variable | Current contract |
|---|---|
| PRACE_RUNTIME_ROOT | Required approved absolute private runtime root |
| PRACE_SECRET_KEY | Required secret, no insecure base default |
| PRACE_RELEASE_MANIFEST | Required read-only JSON file, no symlinks, bounded64KiB |
| PRACE_RELEASE_MANIFEST_SHA256 | Required independently trusted64-character lowercase SHA-256 |
| PRACE_ALLOWED_HOSTS | Required comma-separated host list |
| PRACE_TRUSTED_ORIGINS | Optional HTTPS origins |
| PRACE_READINESS_BUDGET_MS | Optional100–60000ms; default2000; infrastructure must coordinate its probe timeout |
| PRACE_DB_NAME / USER / HOST / PORT | Complete PostgreSQL target or all absent for confined SQLite |
| PRACE_DB_PASSWORD | Password authentication only; value preserved exactly |
| PRACE_DB_SSLMODE / SSLROOTCERT | Remote TCP requires verify-full and readable trust file; local socket/loopback treated separately |

Manifest schema requires git_commit, app_build_id and timezone-aware generated_at;
current bytes must match both trusted hash and startup identity. This identifies a
trusted manifest; it is not proof that every installed source file matches a release.
The separate release inventory/export validation remains required before deployment.

No second secret store: SOPS delivery remains controller-owned, with only required
fields delivered to the selected runtime identity. No secret values in argv/logs.
Existing `settings_synthetic_review` uses its own persistent SQLite but inherits
shared storage; it is not an isolated supervised target. `settings_document_tests`
and `settings_browser_tests` use disposable fixtures and are never service substitutes.

## Health and readiness

- `/health/`: liveness and declared runtime identity only; no DB or document reads.
- `/synthetic/`: declared synthetic contract, not independent access-control proof.
- `/readiness/`: supervised worker validates apps, origins, runtime paths, manifest,
  local model hashes, DB connectivity and complete installed-app migration graph.
  Returns200 ready/current only on success; otherwise503 with sanitized reason/checks.
  GET/HEAD only and no-store. No migrations, OCR inference or provider calls.

Supervised checks run in a fresh subprocess with an overall deadline, not a web
thread or a fork of an initialized OCR process. Timeout kills the process group;
cleanup waits at most200ms beyond the budget. One active probe per web process;
concurrent probes defer with probe_busy. Kernel/storage failures still require
operational handling; this is not a hard real-time guarantee. PostgreSQL connects
with a1-second timeout and500ms statement limit; transaction-local set_config
covers DB/migration probes. Missing SQLite returns not_ready without creating it.
In-memory test settings use direct checks and reject late results; no supervised
latency claim is made for these test-only paths.

RapidOCR remains the default with three pinned local ONNX assets. Readiness hashes
assets via package metadata without loading engines. Optional Tesseract/fallback
is not wired into intake. Input limits remain10MiB,20pages,20M pixels/page,60M total.
Inline OCR execution still needs target-tested request/job limits; a15-minute lease
is not an inference deadline. No Q_CLUSTER or queue dispatch exists.

Public nginx `/ready` is placeholder liveness, separate from Django. Public denial,
private route/TLS, supervision and log collection need infrastructure receipts.

## J4 artifacts and operator interface

Internal `attach_a1_artifact` requires explicit authorized case/employee association,
unchanged source, canonical authoritative review validation and canonical rendering/
automated PDF QA. It never fills missing official certificate values from profiles.
Preparation alone has no PDF hash. Actual PDFs, snapshots, QA data and all-page
previews publish atomically below DOCUMENT_STORAGE_ROOT/j4 with opaque references.

GET/HEAD `/a1/<case>/artifact/` and `/a1/<case>/preview/<1..3>/` require membership,
MFA and capability; audit reads, verify integrity/current dependencies, reject stale
copies and return no-store protected bytes. The case card provides review links.
Staleness includes worker/assignment source, template/layout, renderer/QA code and
build identity. Accepted external review/institution inputs are immutable snapshots;
new accepted evidence requires a new case, not silent rereading of external files.

No public attachment endpoint, visual acceptance or final promotion is introduced.
The evidence-intake and visual-review interface remains a subsequent deliverable.
Jan confirms factual information; technical setup remains engineering-owned.

## Database, release and deployment evidence

Migration0011 adds artifact reference/dependency fields after0010. Deliver models,
services, migrations and dependent views together. Disposable PostgreSQL tests cover
fresh state, historical0007→0009 and0010→0011 with MigrationExecutor and restore the
latest graph. They establish no persistent review or service migration status.

Infrastructure must identify actual endpoint/socket, database, runtime role without
DDL, migration role and authentication reference. Schema migration, SQLite data
transfer and restore are separate procedures. Do not automatically migrate on startup
or run a supposed read-only SQLite preflight against an absent file. The implemented
readiness worker handles absence safely; deployment commands require the selected
settings/identity and secure configuration first.

A durable entrypoint/static serving/supervisor contract, source export and dependency
lock, service-identity permissions, external routing/log correlation and coherent
DB/files restore remain deployment evidence gaps. No service was started by this
handoff; disposable test listeners were stopped by their test harnesses.

## Next ownership and gates

Use the [infrastructure return work order](infra-return-work-order-2026-09-07.md)
for host tasks. Proposed synthetic RPO24h/RTO4h and7daily/4weekly backup retention
remain unaccepted operational defaults; document retention review remains separate.

Complete independent review and all remaining registered engineering checks before
ENG-001; then REV-002, remaining hardening/activation gates and REV-003. J4 bytes or
passing test counts do not grant visual acceptance, issuance or real-data activation.

## Runtime configuration path decision — 2026-09-16

The operator selected `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`
as the infrastructure-owned systemd EnvironmentFile for
`prace-v-nemecku-gunicorn.service`. The canonical source policy is
`desired-state/service-runtime-paths.yml`, service `prace-v-nemecku`, in the
server61 `/workspace/servers-infra-core` project. The application interface is
this runtime manifest contract. This source change is not
proof of host cutover: require infrastructure's byte-equivalence, loaded-unit
path and unchanged-service/process receipts. Path relocation does not rotate
secrets, approve the current manifest, authenticate the database or restart a service.

Keep checkout `.env` separate. `.runtime-config/` is a private infrastructure
namespace: exclude it from Git (including force-add), packages, fixtures, broad
inventory, web serving and ordinary checkout copying. Never print, hash, source
as shell code or copy its payload into documentation/evidence. Intended owner/modes:
root:prace-synthetic, directory0750 and file0640. These modes constrain direct
reads; writable shared checkout ancestors permit path replacement and already
permit application-code changes. They do not provide the former namespace boundary.
Temporary public hostname remains `prace-v-nemecku.expc.cz`, independent of checkout.

`RETIRED_RUNTIME_CONFIG` and `RETIRED_RUNTIME_CONFIG_DIRECTORY` in dated text are
historical placeholders, not deployable paths. Historical observations remain
historical; the new location is never substituted into old measurements.

### Bounded readiness diagnostics

`scripts/check_readiness.sh` now delegates to the unprivileged
[diagnostic implementation](../../scripts/validate_delivery_readiness.py).
It does not open the EnvironmentFile, query password verifiers, use sudo, or
change a service. Correct ownership and modes establish filesystem metadata;
they do not prove database authentication or permission to shell-source a file.
`git rev-parse --show-toplevel` and an absolute path do not change that boundary.
Keep EnvironmentFile parsing with the service manager; do not introduce a
`sudo bash -c 'source ...'` recipe. Systemd's value parsing differs from a shell,
which would execute command substitutions. See the
[upstream EnvironmentFile contract](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml).

From the repository root, run the independent source guard (the wrapper also
resolves its source when invoked by absolute path from another directory):

```bash
bash scripts/check_readiness.sh --source-only --json
```

Run local loaded-unit diagnostics with `bash scripts/check_readiness.sh --json`.
It reports missing release identity as blocked and makes no HTTP request in that
case. To compare the selected release with an explicitly selected route, pass
`--expected-commit` (full SHA), `--expected-build-id`, a numeric `--base-url`
(default `http://127.0.0.1:8001`) and `--host-header` (default the selected Práce
hostname). Obtain expected identities independently from the reviewed release;
never adopt the endpoint's own claim as the expected value. HTTP checks reuse
the canonical smoke transport and typed health/readiness contracts. Static
checks require MIME type and a library marker, not merely a nonempty HTTP 200;
they do not prove full asset byte identity.

Exit 0 means only the selected checks passed; 1 means an observed failure;
2 means incomplete evidence or invalid invocation. Native command errors and
missing source coverage cannot become PASS. Reports record the unit's local
host separately from the HTTP origin/Host header. A local active unit does not
prove ownership of a listener at a separately selected origin.

The generic diagnostic does not consume journal evidence and reports logging
delivery as blocked. A separate bounded check on September17 correlated two tagged
health requests with the selected unit's worker in journald. This establishes
access-log delivery for those requests, not log retention, error completeness or
the cause of an earlier empty journal. `ProtectSystem=strict` and
`--capture-output` alone establish no logging verdict. Full generic diagnostics
cannot currently return all-pass; this is a documented tool limitation, not a new
core-v1 acceptance gate. See the [reconciled observations](s62-operator-triage-report-2026-09-16.md).

### Static access and private runtime children — 2026-09-17

Owner-only directory access remains the default. Runtime traversal and the static
directory may use0750 only with the runtime process's effective primary group.
The owned root and symlink checks remain in force. Sensitive storage, media,
cache, temporary files, logs and inbox directories require0700 access; settings
must not accept layouts their OCR/inbox consumers reject. Existing directories
are checked, never silently chmodded. Disposable rehearsal remains owner-only.

This application permission check does not certify group membership. A boolean
probe confirmed that nginx's `www-data` identity could read the service
EnvironmentFile through its `prace-synthetic` membership; no payload was read.
The explicitly authorized host repair added nine static-only ACLs, removed that
membership and transitioned all four workers. Configuration read/traversal is
now denied, and all seven static assets pass on both routes with unchanged bytes.
The [infrastructure request](servers-infra-core-postgresql-request.md) retains
the before/after evidence. Infrastructure desired state must preserve this
separation; publication of application source alone does not deploy host ACLs.

### Owned PostgreSQL browser demonstration

The verified a57e069 committed export passed this real Chromium journey on a
fresh local PostgreSQL cluster; all lifecycle phases exited 0. The initial e55f132
run failed at readiness and remains in the private delivery receipt. No readiness
budget or assertion was relaxed, and the successful retry is not a causal
explanation of that failure. These test settings do not prove the live runtime
identity, assignment flow or restart persistence.

`make test-pg` invokes the existing `scripts/test_document_intake.py` harness
with browser settings and the explicit Chromium journey label. It provisions a
new private PostgreSQL cluster under this source checkout's runtime, with a Unix
socket and no TCP listener. Inherited database targets and password-file lookup
are excluded. Phase commands, native results and logs are retained; the harness
stops only its newly created cluster. It never consumes the service EnvironmentFile.

The canonical Python interpreter and PostgreSQL18/Chromium assets must be
installed. Long nested checkout paths fail before database startup because Unix
socket names have a finite length; use a short in-project source export and
`make PYTHON_BIN=/var/www/prace-v-nemecku.tvoje.info/venv/bin/python test-pg`
from that export. This exercises synthetic login/TOTP, document/OCR and access
boundaries on local PostgreSQL. Complete core workflow, exact corrected-value
restart persistence, deployed runtime-role separation and Jan acceptance remain
separate. `make test-pg-contract` executes only target/guard contract regressions.
