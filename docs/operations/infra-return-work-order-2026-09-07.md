# Infrastructure return work order — 2026-09-07

Parent: PLAN-INFRA. Status: decision preparation; no deployment authorization.
See the [application review](../research/2026-09-07-infra-application-review.md)
and [runtime manifest](runtime-manifest.md). Preserve the original packet unchanged.

## Application implementation update — 2026-09-07

Read the [new engineering report](../research/2026-09-07-runtime-j4-engineering.md)
first. Supervised settings, required trusted `PRACE_RELEASE_MANIFEST_SHA256`,
protected child paths, subprocess readiness, PostgreSQL timeouts and model checks
are now implemented. Earlier “not implemented” statements below are retained as
historical proposals, not current blockers. Artifact bytes/QA/previews and migration0011
are also implemented/tested. No actual host identity, DB, SOPS delivery, supervisor,
private routing or restore was provisioned. These remain your return work items.

## Priority 1: agree the isolated target and release

Proposed target `prace-synthetic-s62-v1` is distinct from existing review SQLite,
disposable tests and future production PostgreSQL. Proposed Unix identity/group
`prace-synthetic`, umask 0077; read-only reviewed source/static/model assets, write
access only to `runtime/portal/supervised-synthetic/` with separate storage, cache,
tmp and database children. No access to real A1/scans/evidence/output, repository
`.env` or unrelated secrets. Infrastructure provisions identity/permissions only
after authorization; app engineering supplies confined settings and preflight.
Existing `settings_synthetic_review` inherits shared storage and DEBUG=True and
must not be assumed to satisfy this contract. Browser test settings are test-only.

App engineering must deliver an immutable reviewed source inventory, dependency
lock/model hashes, entrypoint, explicit STATIC_ROOT/delivery, confined settings and
bounded storage/model/release readiness before durable startup. The current source
inventory is a working-tree snapshot, not a published release. Deliver migrations
0008/0009 with models and dependent services. Do not stage unknown research files.

## Priority 2: configuration and database interface

Current supported secret: `SYNTHETIC_REVIEW_SECRET` (nonempty string) for the
existing review settings. `DJANGO_SETTINGS_MODULE` selects settings.
`DOCUMENT_TEST_PG_SOCKET/USER` are test-only; `A1_PRIVATE_DIR` is for canonical CLI
operations and does not authorize giving a web service the real private root.

Proposed settings `portal.settings_supervised_synthetic` and variables below are
**not implemented or accepted configuration**. App engineering first implements
missing/invalid-value tests using dummy values. No second secret store is needed.

| Proposed variable | Type / requirement |
|---|---|
| PRACE_RUNTIME_ROOT | Required absolute confined synthetic root |
| PRACE_SECRET_KEY | Required nonempty secret, secure injection |
| PRACE_RELEASE_MANIFEST | Required read-only reviewed manifest path |
| PRACE_ALLOWED_HOSTS | Required validated host list |
| PRACE_TRUSTED_ORIGINS | Optional validated HTTPS origins; absent for loopback-only |
| PRACE_DB_NAME / USER / HOST | Required only for separately selected PostgreSQL target |
| PRACE_DB_PORT | Integer 1–65535 for TCP PostgreSQL |
| PRACE_DB_PASSWORD | Secret only where password authentication is selected |
| PRACE_DB_SSLMODE / SSLROOTCERT | verify-full and read-only trust root for remote PostgreSQL |

Keep DEBUG=False and synthetic-only behavior fixed in the new settings. Infra
returns endpoint/socket, DB name, runtime role without DDL, separate migration role,
authentication reference and owner. No passwords in reports. SOPS decryption remains
controller-side; deliver required fields only, no age private keys/full vaults,
shell eval/source, secret argv or debug logging. No host DB has been identified by
our disposable PostgreSQL test. Schema migration, data transfer and restore each
need separate rehearsal and receipts; no automatic migrate on service startup.

## Priority 3: execution, routing and observability

There is **no Q_CLUSTER or dispatch integration**. Correct the packet's ORM broker
claim; provision neither Redis nor an assumed ORM worker. Intake currently runs
inline with explicit retries; a lease is not an engine deadline.

Engineering defaults proposed for validation: one OCR job at a time, hard child
process limit 120 seconds/document, outer request limit 150 seconds, upload envelope
11 MiB with existing decoded limit 10 MiB, 20 pages, 20M pixels/page and 60M total.
These limits are not all implemented. Preserve RapidOCR/ONNX as default; optional
Tesseract results never authorize automatic field acceptance. Timeout routes to
sanitized failed/deferred state. Future queued execution needs separate testing.

Loopback-only private listener; infrastructure owns the approved proxy/TLS route
and public denial probes. `/ready` at nginx is placeholder liveness; `/health/`
is application liveness; `/readiness/` currently covers DB/migrations only.
Propose readiness target 2 seconds, probe timeout 5 seconds; implement bounded DB
connection/query and storage/model/release checks before claiming full readiness.
A test-server listener is not durable supervision or service restart proof.

Infra must correlate a nonsecret operation marker from the review receipt in its
log destination, test rotation and alert delivery, and report missing access as
PROBE-BLOCKED. The locally emitted marker is not proof of journal/Loki ingestion.
Log opaque correlation IDs, versions, durations and reason codes, not fields,
filenames, tokens or raw OCR. Test access as the actual selected service identity;
pavel's model read access and `.env`0600 do not prove that identity's permissions.

## Priority 4: coherent recovery

Proposed synthetic defaults: RPO 24 hours, RTO 4 hours, daily coherent DB/files
snapshot, 7 daily and 4 weekly retained backups. These need runtime-owner acceptance
and measured restore tests. Stop writers or prove a consistent snapshot boundary;
bind source/config/model manifests, originals, derivatives and job state. Restore
in isolation and verify hashes, tenant denial, stale artifacts and pending jobs.
Backup retention does not replace the 90-day document retention review policy.
Infrastructure on-call owns storage/process/backup alerts; application owner owns
semantic processing failures and retry disposition. Jan supplies workflow facts,
not database, legal-profile, engine, secret or storage choices.

No ENG-001/REV-002/REV-003 or real-data gate opens here. Minimum functioning J4
remains required before ENG-001, then REV-002, hardening/activation gates and REV-003.
