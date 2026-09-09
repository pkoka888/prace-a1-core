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
