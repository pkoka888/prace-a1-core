# Runtime and J4 engineering delivery — 2026-09-07

Parent: PLAN-INFRA / PLAN-A1 / PLAN-WORKERS. Working-tree implementation;
no commit, service migration, deployment, final promotion or real-data processing.
Existing changes were preserved. This supersedes prior claims of completed
confinement/deadlines and metadata-only J4 artifact evidence.

## Implemented contract

Supervised settings require a direct child of the project `runtime/portal/` named
`supervised-*`, owned by the runtime UID with owner-only directory permissions.
Existing synthetic review/verification/shared roots are not accepted targets.
Root ancestors, child storage/media/static/cache/tmp/log directories and SQLite
file paths reject symlinks. Probes use exclusive owner-only file creation with a
directory descriptor and remove only their own files. Temporary Python files use
the configured private tmp directory. No existing runtime was moved or repaired.

`PRACE_RELEASE_MANIFEST_SHA256` is mandatory. One implementation checks read-only,
bounded, non-symlink manifest bytes, trusted SHA-256, JSON shape, commit/build ID
and timezone-aware timestamp. Readiness revalidates current bytes against startup
identity. PostgreSQL passwords retain their exact value; remote TCP requires
verify-full plus a trust file. Connection timeout is 1 second; supervised startup
options set statement timeout 500 ms. Transaction-local set_config covers the actual
DB and migration probes and is rolled back/restored on failure.

Supervised `/readiness/` runs checks in a fresh process, with a default 2-second
whole-process budget and process-group termination on timeout. Cleanup waits at
most 200 ms; this is not a real-time scheduling or failed-kernel-storage guarantee.
One in-flight probe per web process prevents local fan-out; concurrent requests
receive probe_busy (503). No web-thread fork, detached timeout thread or engine load
is used. Required model files are hashed through package metadata without importing
RapidOCR/ONNX. Missing SQLite is rejected without creating a database. Test-only
in-memory settings use direct checks, report late results as not_ready, and are
explicitly not supervised runtime targets.

J4 preparation now stores a source snapshot and leaves the PDF hash empty until
an artifact actually exists. Source hashing includes ordered assignment identities,
dates, labels, state and version. New current snapshots are fresh; previous changed
snapshots are stale. Normal model saves reject snapshot or attached-artifact
replacement. Direct administrative SQL/QuerySet.update is outside this guard.

The explicit `attach_a1_artifact` service requires organization capability,
current-source agreement, immutable case association, canonical review validation,
authoritative source/approval fields and canonical rendering. It reuses canonical
PDF QA (including Ghostscript and template checks), then publishes a complete
protected package with actual PDF bytes, snapshot, all-page PNGs and hash-bound
receipt. Publication rejects existing destinations and synchronizes staged files
and directory entries. No certificate fields are inferred from a worker name.

Protected GET/HEAD `/a1/<case>/artifact/` and `/a1/<case>/preview/<1..3>/` require
organization membership/MFA and A1 capability. They audit reads, verify package
integrity and current source/template/layout/renderer/QA-code/build dependencies, reject stale copies,
return no-store responses, and never generate on GET. No public storage URL is
created. The canonical accepted review/institution inputs are immutable snapshot
dependencies: new accepted external evidence requires a new case; external files
are not silently polled or reinterpreted as new acceptance.

## Evidence and status

Acceptance is for the working tree, not committed or deployed code. Synthetic
receipts/logs live under `runtime/portal/hardening-20260907/`. Test settings use
isolated databases and disposable storage; no service database was inspected.
Migration 0011 adds artifact reference/dependency fields. The PostgreSQL harness
covers fresh state, historical 0007→0009 and 0010→0011 using MigrationExecutor and
restores graph leaf migrations. These are schema-test results, not deployment.

Earlier integration failures were retained: tests expecting metadata hashes and
date-only source hashes were corrected to the new evidence contract. The browser
fixture's old exact liveness dictionary needed to account for the existing runtime
contract fields. The live browser fixture also exposed SQLite InterfaceError failures during concurrent
requests against a shared in-memory connection. A disposable file-backed database
resolved this; two complete offline browser journeys passed, including authenticated
download bytes, readiness, and console assertions. Runtime-mode metadata now has an
explicit settings fallback. No skipped assertion is counted as acceptance.

## Remaining gates and ownership

Artifact byte/pixel integrity and canonical automated QA are not visual acceptance,
certificate issuance, submission authorization or final promotion. A complete
operator evidence-intake interface, visual-review receipt workflow and the remaining
ENG-001 registered checks still require their own acceptance. No gate is opened
by these changes. Keep functioning J4/prerequisites → ENG-001 → REV-002 → remaining
hardening/activation gates → REV-003.

Infrastructure still owns the service identity, deployed secret references,
actual PostgreSQL target, supervised service, private routing, log correlation,
rotation/alerts and coherent backup/restore evidence. Existing numeric resource
and recovery proposals remain proposals until validated on that selected target.
Research cleanup remains retain pending review; no new human-per-file approval
or archive/delete operation is introduced. Jan supplies facts and consolidated
confirmation; technical configuration belongs to engineering/infrastructure.

## Acceptance results

| Suite | Result | Receipt |
|---|---|---|
| Runtime settings, manifest, deadlines, models and artifact packages | 127 passed; 5 Django database-override warnings | `unit-complete.log` |
| Canonical A1, CLI, private paths and approvals regression | 157 passed; 19 subtests | `a1.log` |
| Disposable PostgreSQL intake, cancellation and historical migrations | 22 passed | `postgres.log` |
| M2 readiness, views, review fixes, vertical flow and J4 | 68 passed | `portal-final.log` |
| J4 service, minimum and protected delivery follow-up | 22 passed | `j4-final.log` |
| Final protected delivery and service follow-up | 8 passed | `j4-delivery.log` |
| Offline Chromium journey, repeated after fixture repair | 1 passed per run | `browser-filedb.log`, `browser-complete.log` |

Suites overlap; these counts are not additive. Earlier failed logs remain available.
No full-repository or production acceptance claim is made. Final planning, approval,
migration-drift and whitespace checks are recorded in `acceptance.json` beside these
logs, together with hashes of the reviewed source inventory.

Reproduction commands (repository root; synthetic settings only):

```bash
venv/bin/python -m pytest -q tests/test_a1_core.py tests/test_a1_quality_gate.py tests/test_finalize_a1.py tests/test_a1_private.py tests/test_a1_stabilization.py tests/test_a1_cli_journey.py tests/test_a1_employee_delivery.py tests/test_validate_approvals.py
venv/bin/python scripts/test_document_intake.py
env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_USER DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m django test tests.m2.test_j4_delivery --noinput -v 0
timeout 180 unshare --user --map-root-user --net sh -c 'ip link set lo up && PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/playwright_smoke.py'
venv/bin/python scripts/validate_planning.py
venv/bin/python scripts/validate_approvals.py
```

The runtime/package pytest suite initializes Django before pytest collection:

```bash
env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_USER DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python - <<'PYTEST'
import django
import pytest
django.setup()
raise SystemExit(pytest.main(['-q', 'tests/test_runtime_hardening.py',
    'tests/test_settings_supervised_synthetic.py', 'tests/test_readiness_checks.py',
    'tests/test_runtime_contract.py', 'tests/test_j4_artifacts.py']))
PYTEST
```

Publication uses a destination lock and a single directory rename. A later database
transaction failure can leave an unreferenced protected package; it is not accepted
or served and requires retention review rather than automatic deletion. Existing
approval scope detection already includes `portal/`, canonical audit/path helpers,
and `tests/`, so these changes cannot bypass the dirty-review-scope check.
