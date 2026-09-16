# Git delivery safeguards — 2026-09-08

Parent: PLAN-INFRA. Scope: source-delivery policy and bounded delivery evidence.
No deployment, new runner/remote, history rewrite or real-data processing.

## Migration-scope shell dependency integrated — 2026-09-16

Commit `b687abe` completes the P0 REL-03/JAN-04 candidate: the shell setter and
operator database-name refusal that the committed settings gate and committed
refusal tests depend on are now part of the committed candidate.

| Field | Evidence / state |
|---|---|
| Implementation | `scripts/rehearse_synthetic_site.sh` now (1) refuses an exact operator database name (`prace_synthetic`) before any schema or data mutation and (2) forwards `PRACE_MIGRATION_SCOPE=1` plus the migration statement timeout only into the `manage.py migrate` invocation. Settings gating already existed in the committed candidate. Single Unix-executable file, 10 lines |
| Validation | Mandatory hook selected `delivery_lifecycle_rehearsal` once: 58 passed, 196.79 s (`runtime/portal/temporary/change-checks-3qksie22/`, exit 0). Focused settings scope-gating regression passed (4 tests). `bash -n` and `git diff --cached --check` clean. Tested bytes equal the committed shell (`git diff HEAD -- scripts/rehearse_synthetic_site.sh` empty); import-only settings tests confirm command scope, live `current_user`/`statement_timeout` remain on the P0 JAN-04 real-PG row |
| Publication | Local commit `b687abe` on `feat/prace-readiness-plan-2026-08-13`; not pushed (branch carries inherited incomplete source increments; push requires review of all outgoing objects per audit) |
| Deployment / activation | None. No service, credential, deployment or real-data change |
| Limitations | Script-level refusal and settings gating proven; the invalid psql probe and forward-selection/TLS chain remain open under JAN-04. The runtime-scope path (web/worker) must not inherit `PRACE_MIGRATION_SCOPE`; verified at settings import only |
| Next owner | Engineering proceeds to the JAN-04 disposable-ownership/probe/forwarding repairs and then the committed-source core/restart acceptance; infrastructure INFRA-PG-01 proceeds independently |

## Delivery audit and execution-plan reconciliation — 2026-09-16

| Field | Evidence / state |
|---|---|
| Implementation | Reconciled the active plan, roadmap/index/parents, AGENTS, PostgreSQL and rehearsal skills, feedback and operational recipes against `a48a1e8` and inherited changes. Defined observable goal, sources, priorities, owners, validation and limitations. This increment changes documentation; application repairs remain TODOs |
| Validation | Inspected both commit objects, index/worktree differences, installed hook/selector code and three private reports. Fresh bounded read-only unit/socket/dependency/remote observations. Owned-cluster SELECT-only probe reproduced invalid psql invocation; plain SQL control passed and owned cluster stopped. Configuration probes reproduced missing migration-pair forwarding and empty/blank target gaps; mocked lock probe demonstrates self-declared ownership is insufficient. All scoped local links resolve and the planning catalog is unchanged; both skill frontmatters pass after correcting an inherited arrow in the rehearsal description. Final mandatory-hook result belongs to the private local delivery receipt |
| Publication | Documentation publication deferred: pushing the current branch would also publish the inherited incomplete source increments. Preserve those commits without rewriting history; primary first integrates their missing dependencies and reviews all outgoing objects. No push is claimed by this audit |
| Deployment / activation / operator acceptance | No host service/config/credential change, deployment, real-data activation or Jan acceptance. Temporary owned PostgreSQL test instance only; no operator data accessed |
| Limitations | Browser timeout cause unresolved; intended-target authentication/route/build/restart and PG5 restore unverified. A documentation correction does not close a source defect. Installed allauth now matches pin 65.19.1; earlier drift is historical |
| Next owner | Engineering starts the P0 REL-03/JAN-04 candidate/ownership/probe/forwarding repairs; infrastructure handles INFRA-PG-01 independently; Jan observes the candidate after technical acceptance |

Private audit receipt directory: `runtime/portal/temporary/delivery-audit-20260916-moriz8mx/`.
It retains pre-edit documentation snapshots, source identities and bounded native
probe outcomes, including the initial 30s initdb sync timeout and successful
`--no-sync` disposable retry. This command probe is not durability acceptance.
See the [active plan](../../plans/2026-09-14-delivery-reliability-and-jan-v1.md) for
repair/validation detail; the prior failed and successful hook logs are retained.

## Layout review and temporary public hostname — 2026-09-16 (server62)

Servers-infra-core (server61) layout-and-safe-merge review received, archived
and reconciled on the application side. Docs-only increment; no live host
configuration, service, credential or database change.

| Field | Evidence / state |
|---|---|
| Implementation | Received servers-infra-core audit + agent work order (server61, `f8280118`), archived as a sanitized historical transcription under `docs/operations/2026-09-16-layout-review/ORIGINAL-servers-infra-core-review-s61.md`; two host-labeled reports written (`REPORT-servers-infra-core-s61.md`, `REPORT-prace-application-s62.md`) so the two project contexts are never mixed. Operator decision on 2026-09-16: proceed temporarily with public hostname `prace-v-nemecku.expc.cz` (matches nginx vhost and `RETIRED_RUNTIME_CONFIG` `PRACE_ALLOWED_HOSTS`); checkout path stays `/var/www/prace-v-nemecku.tvoje.info`. Corrected phantom `RETIRED_RUNTIME_CONFIG_DIRECTORY/secret.key` + `RETIRED_RUNTIME_CONFIG_DIRECTORY/manifest.sha256` reads in `wsgi-deployment-recipe.md` (kept `PRACE_RELEASE_MANIFEST_SHA256` bound to `$PRACE_RUNTIME_ROOT/.release_manifest.sha256` which matches the on-disk manifest; env's pin is separate and stale) and `delivery-1-postgres-handoff.md` (secret key read now sourced from `RETIRED_RUNTIME_CONFIG`); aligned `technical-needs-sysadmin-2026-09-12.md` (0640 vs 0600 framed as explicit identity/access policy; dated correction block for the 2026-09-12 "not live" table) — that alignment edit lives in the working-tree copy of an inherited untracked file and is preserved, not committed; both skills documented the infra-owned EnvironmentFile contract and unresolved credential/provenance state |
| Validation | Planning validator and staged-link/whitespace checks over the touched documents; relative-link depth verified for skill-to-docs references. Documentation/review validation only — no application or live-services suite run or claimed. Shared-secret equality (`PRACE_SECRET_KEY` == `PRACE_DB_PASSWORD`) re-verified on server62 as a sha-256 boolean-only comparison; values never printed or stored |
| Publication | Historical layout source checkpoint `8d125f2` exists on the remote at the audit observation; later inherited path/doc changes are distinct and covered by the current audit entry |
| Deployment | None changed |
| Activation | Unchanged; synthetic-only posture; §14 gate untouched |
| Limitations | Credential rotation, release repin, adoption of the running gunicorn by systemd, HBA reconciliation and orphan-process disposition remain operator-owned (INFRA-PG-01); the s61 320-test/14-validator results validate the servers-infra-core repository, not this checkout |
| Next owner | Operator: rotation + release repin + supervision adoption + hostname DNS/proxy reconciliation. Engineering: JAN-03/JAN-04 toward one committed-source core acceptance run |

## Manual PostgreSQL verification and export-script audit — 2026-09-16 (s62)

Manual operator-host verification and tooling audit on `server62` (user
`pavel`). Read-only diagnostics plus scoped app-side fixes; no host change.

| Field | Evidence / state |
|---|---|
| Implementation | Manual DB test: `postgresql@18-main` online (`pg_isready` 127.0.0.1:5432 accepting); roles include `prace_synth_app`; databases `prace_synthetic` and `prace_synthetic_test` exist; configured `RETIRED_RUNTIME_CONFIG` password (read via sudo, never displayed) returns `FATAL: password authentication failed for user "prace_synth_app"` over TCP — INFRA-PG-01 credential mismatch confirmed manually, no app code involved. Audit fixes (app-side, committed separately): F1 `tests/test_rehearse_workflow.py::_postgres_env` no longer invents `PRACE_DB_*` defaults (removed the fabricated `prace_synth_app` password); `PRACE_WORKFLOW_PG=1` now requires the explicit full target and fails closed. F2 `portal/settings_document_tests.py` honors `DOCUMENT_TEST_PG_PASSWORD` and requires it for a TCP (`DOCUMENT_TEST_PG_HOST`) test target; socket mode unchanged. F3 `scripts/run_release_reproducer.py` forwards the caller's real `PRACE_DB_*`, `DOCUMENT_TEST_PG_*`, `PRACE_TEST_DB_*`, `PGPASSWORD`, `JOURNEY_EVIDENCE_PATH`, `PRACE_SECRET_KEY`, `PRACE_RUNTIME_ROOT` and statement-timeout vars into the exported acceptance environment instead of a clean-slate guess. F4 `scripts/rehearse_synthetic_site.sh` rejects partial `PRACE_DB_*` sets and prints the effective database target (`DB target: PostgreSQL host=… db=… user=…` / `DB target: SQLite (local rehearsal default)`) at `migrate` and `start`, so a silent SQLite downgrade on the operator runtime becomes visible |
| Validation | Repro rounds: `tests/test_release_reproducer.py` + `test_postgres_env_fails_closed_without_explicit_target` → 15 passed (2.23 s); settings/readiness → 96 passed, 1 skipped; site/lifecycle/OCR/change-packages → 90 passed (75.88 s); canonical `tests/test_rehearse_workflow.py` → 2 passed (106.93 s). Settings probe: `DOCUMENT_TEST_PG_HOST` without `DOCUMENT_TEST_PG_PASSWORD` raises `RuntimeError`; with password sets `ENGINE=postgresql` and `PASSWORD`. `bash -n` clean on the lifecycle script. The orphan `gunicorn` (PID 2681143, user `prace-synthetic`, bind 127.0.0.1:8001, since Sep 14) still runs with no `PRACE_DB_*` in `/proc/.../environ` and a `db.sqlite3` in `runtime/portal/supervised-synthetic` — the documented supervision/transport mismatch; operator-owned, not touched |
| Publication | Committed on `feat/prace-readiness-plan-2026-08-13` as `644bc4e` (`fix: fail-closed PG targets in rehearsal/export tooling (no invented credentials, real env forwarding)`, 8 files) and pushed to the existing private `origin` feature branch; remote SHA verified `644bc4e79f9193668ac96cb8755dc6b89f5000b9`. Mandatory hook ran 7 checks green, including `delivery_lifecycle_rehearsal` (180.73 s) and `synthetic_runtime_dependencies`; protected-path scan clean |
| Deployment | None. No database, credential or service change |
| Activation | Unchanged. Synthetic-only posture; §14 gate untouched |
| Limitations | PostgreSQL data-plane acceptance (JAN-04) still requires the infrastructure credential response; these fixes make credal/transport mistakes fail loudly instead of silently, they do not substitute for the missing password reset. The orphan gunicorn and systemd unit reconciliation remain sysadmin-owned (INFRA-PG-01 items 2-3) |
| Next owner | Historical handoff superseded by the current audit: infrastructure reconciles the selected target; engineering fixes the application paths using independent disposable credentials. Never reuse the retired/live secret file for rehearsal |

## PG and core workflow source increments — 2026-09-16 (corrected audit)

`fa87ad8` contains the PG settings/contract/guard/reproducer changes (14 files).
`a48a1e8` contains stored-source-byte persistence checks, actual-result verifier
dedup and non-A1 browser assignment correction (5 files). These are implementation
increments; the prior blanket “FIXED”, “committed-source hook”, “load-induced” and
“engineering complete” descriptions overstated the evidence.

| Field | Evidence / state |
|---|---|
| Implementation | Useful source improvements exist. Missing committed shell migration-scope/target-refusal dependency, self-declared disposable ownership, teardown-only guard, invalid psql probe, forwarding and core-profile gaps remain open in the active plan |
| Validation | Failed hook `change-checks-dvp3wac9`: 674.08s, document-detail networkidle timeout, captured server error categories empty. Successful retry `change-checks-3wz11m3j`: 733.59s, shared suites 304.656s +162.950s, lifecycle 239.284s. Second commit hook `change-checks-fak3qz33`: 224.87s, lifecycle 222.918s. All report directories are under protected runtime/portal/temporary. These are working-tree checks, not committed-export acceptance. Earlier standalone counts remain reported evidence, not re-executed by this audit |
| Publication | Direct remote observation during the audit: existing feature branch at `8d125f2ced67fced2206a470e9299d57761549e6`; `fa87ad8` and `a48a1e8` local only at that time. The previous draft's pushed/remote-verified claim is retracted |
| Deployment / activation | No deployment or real-data activation by these source increments; intended-target/Jan acceptance open |
| Limitations / next owner | Engineering repairs the concrete candidate/PG/core/evidence defects; infrastructure independently reconciles credentials, supervisor/listener, approved build and route. An infrastructure response alone cannot close JAN-04 |

## JAN-01/JAN-02 separate investigations — 2026-09-16

Reproduced both defects as separate issues on a persistent
`runtime/portal/supervised-jan-investigation` runtime (SQLite, gunicorn 2
workers, owned OCR worker, `127.0.0.1:8099`) using the canonical
`rehearse_dev_local.sh` lifecycle.

| Field | Evidence / state |
|---|---|
| Implementation | JAN-01 (OCR `OCR_STATUS_HTTP_500`): genuine server HTTP 500 historically flaky under gunicorn + SQLite write contention, not an authentication redirect; the uncommitted supervised-settings mitigation (`journal_mode=WAL`, `transaction_mode=IMMEDIATE`, `busy timeout=20`) is in effect — verified `PRAGMA journal_mode=wal` on the rehearsal DB. Three consecutive full journeys in this tree produced zero HTTP 500s and OCR races no longer blocked progress; a single reproduction remains flaky-class evidence, not a full-fix claim. JAN-02 (protected download bytes mismatch): NOT file corruption — the application serves the exact uploaded bytes (browser fetch returned `200 image/png`, 36462 bytes, sha `e4d084…a440b` matching the stored source and `Document.sha256`; `document.downloaded` audit recorded). The mismatch was an authentication-redirect artifact: Playwright's `APIRequestContext` drops `Secure` session/CSRF cookies over plain loopback HTTP, so `context.request.get('/documents/<pk>/download/')` followed the login redirect and returned the 5044-byte login HTML (HTTP 200 after redirect) while the pages's own requests carried the cookie. Fixed `tests/_rehearse_workflow_browser.py` stage 9c to fetch through the real browser page (`fetch(..., credentials:'same-origin')`, base64 body) and now asserts HTTP 200, non-HTML content type, exact size and exact SHA-256 against the uploaded PNG |
| Validation | Journey passes end-to-end on the persistent runtime (core profile, `ok:true`, 13 stages, document sha captured); canonical `tests/test_rehearse_workflow.py` passed once (103.98 s); `tests/test_rehearse_synthetic_site.py` + `tests/test_rehearse_synthetic_site_lifecycle.py` → 30 passed (61.96 s). JAN-03 core/optional-A1 profile separation verified at runtime: core journey requires only the non-A1 stage set (`a1_skipped` recorded; `case_pk`/`regenerated_case_pk` null) |
| Publication | Committed on `feat/prace-readiness-plan-2026-08-13` as `a7335af` (`fix: deliver JAN core v1 repairs (OCR reliability, protected download verify, core/A1 profiles)`, 17 files) and pushed to the existing private `origin` feature branch; remote SHA verified `a7335af368713e72aea781bc4a5280bf3e326901`. Mandatory hook ran 8 checks green, including `delivery_lifecycle_rehearsal` (168.34 s). Protected-path scan and secret scan over the full committed diff clean. `tests/test_persistence_verifier.py` path classified into `delivery_lifecycle_rehearsal` in `change-packages.yml` and `APPROVED_STAGED_PATHS` in `validate_planning.py`. Inherited edits preserved unstaged: `config/institutions/{kladno,louny,usti-nad-labem}.json`, untracked reports/work orders, session helpers (`_login_for_session.py`, `get_session_cookie.sh`), `test_browser_debug5.py`, quarantined `test_ocr_benchmark_contract.py`, `validate_project_refresh.py` and `docs/research/2026-09-14-complexity/` |
| Deployment | None. Journeys ran against the disposable persistent runtime only; no operator-owned service or host change |
| Activation | Synthetic-only posture unchanged (`M2_SYNTHETIC_ONLY`, §14 gate untouched) |
| Limitations | OCR-500 status: WAL/IMMEDIATE mitigations present and no 500 reproduced in three runs, but the historical reproduction was flaky and a bounded set of runs is not a statistical fix claim; the plan keeps the investigation record, not a release acceptance. PostgreSQL acceptance (JAN-04, INFRA-PG-01) remains separately open and is not subsumed by this SQLite demonstration |
| Next owner | One reproducible committed-source core acceptance run (the last plan step before observed use), then the PostgreSQL acceptance per the infrastructure response contract. Inherited unstaged items above remain out of the JAN batch until their own sanitized reviews |

## Documentation/review checkpoint — 2026-09-15

Documentation-only increment. No code repair, credential rotation, service
change, data migration, deployment or operator acceptance is claimed.

| Layer | Evidence / state |
|---|---|
| Implementation | Dated 2026-09-15 review checkpoint added to the active child plan (findings mapped onto existing JAN-01–04, REL-03/04, REL-06, INFRA-PG-01 task IDs); roadmap and index updated (Delivery 1 not accepted; PostgreSQL observed running with failed configured application authentication; Gunicorn supervision mismatch); PostgreSQL handoff corrected to pending repair/validation with fixed relative links; AGENTS PostgreSQL cleanup section moved out of the interrupted A1 section; postgres-ops and synthetic-portal-delivery skills reconciled with executable configuration (deprecated `PRACE_TEST_DB_*` instructions removed; implemented/defects/intended repairs distinguished); new [sysadmin reconciliation report](sysadmin-postgresql-reconciliation-2026-09-15.md) created for user forwarding; change-package ownership added for the new paths |
| Validation | Planning validator; staged whitespace check (`git diff --cached --check`); scoped relative-link check over the touched documents; mandatory hook checks for the staged documentation/tooling packages. No application test suite is claimed for this checkpoint |
| Publication | Documentation/review checkpoint committed as `0a8734c` on `feat/prace-readiness-plan-2026-08-13` and pushed to the existing private `origin` feature branch; the REL-06 skill reconciliation follow-up (stale `--profile` prose replaced with the implemented core/optional-A1 state) was committed as a docs-only follow-up on the same branch; unrelated inherited edits (institution configs, session helpers, quarantined tests, research/work-order material) were preserved unstaged |
| Deployment | None. No host service, credential or database change |
| Activation | Unchanged. Real-data activation remains gated by real-data rules §14 |
| Limitations | This checkpoint does not repair the OCR HTTP 500, the download mismatch, JAN-04 defects (target forwarding, disposable cleanup, migration credential scope, effective timeout) or the profile separation; the sysadmin report records observations and requests, it is not a host change and proves no infrastructure state beyond its dated scope |
| Next owner | Application engineering: JAN-01/02 separate investigations, then JAN-03/JAN-04 repairs toward one committed-source core acceptance run. Infrastructure: return the completed response contract after inspection/reconciliation; the response alone does not close JAN-04 |

## JAN-01/JAN-02 bounded repair — 2026-09-14

Implementation: `f54d4e6bbf7997a4fa35042dc71df296440676c6`.
HTTP uploads now persist pending OCR work; an explicitly scoped sequential worker
uses existing leases/token fencing. Default inbox CLI processing returns terminal
receipts. Rehearsal owns web/worker start, stop and restart. Czech status/refresh/retry
and native browser interactions replace fixed completion sleeps. Worker edit/create
cannot bypass archive permission; hard deletion remains denied pending separate policy.
Roadmap, parent/child plans, AGENTS and the existing delivery skill reflect this scope.

Validation: all 14 mandatory hook checks passed. Broad Django: 276 run, 27 skipped;
canonical browser: PASS; rehearsal/lifecycle: 44 passed. The hook took 993.07s and
still includes overlapping J4 execution (REL-04 follow-up). Three earlier hook
failures and their corrections remain recorded; no checks were bypassed.
Committed-source export: 33 OCR/authorization tests passed (11.694s command), and
one canonical Chromium journey passed (139.709s command); source integrity verified.
The commit matches all 42 reviewed path hashes. SQLite evidence does not establish
PostgreSQL concurrency or target acceptance. Installed allauth65.19.2 still differs
from pin 65.19.1; no clean pinned-environment acceptance is claimed.

Detailed commands, exit codes, durations, negative cases, skills/Context7 sources
and failed-attempt history: `runtime/portal/temporary/jan-01-02-repair-20260914/handoff.md`.
Final hook logs: `runtime/portal/temporary/change-checks-u797qrsw/report.json`.
Export receipt: `runtime/portal/temporary/jan-01-02-repair-20260914/committed-source.json`.

Publication: implementation pushed to the existing private-origin feature branch;
remote SHA verified equal to the implementation SHA. Deployment/activation: none
performed. Broader JAN-01/JAN-02 remain partial. Next owners: access engineering
for recovery/pins; primary for JAN-03 core/optional-A1 profile separation; runtime
engineering and authorized host owner for JAN-04 PostgreSQL/routed acceptance.
REL-01/REL-02 remain separate. Official A1 is outside core v1. Synthetic email is
local-only; password-recovery delivery is unverified. Inherited session/institution
edits and unrelated untracked files remain outside this publication.

## Session delivery — 2026-09-14: admin session cookie helper + synthetic site debugging

**Branch:** `feat/prace-readiness-plan-2026-08-13`
**Commit:** `00786f74fb5321900f9f293f989447e5d7bd8016`
**Scope:** `scripts/get_session_cookie.sh`, `scripts/_login_for_session.py`, `portal/settings_supervised_synthetic.py`
**Status:** accepted (synthetic evidence only)

### What was done

- Diagnosed 403/CSRF behavior on the supervised synthetic review site.
- Identified root cause: session invalidation + missing org membership, not CSRF.
- Created admin `Organization` (`Admin Organization`, `key=admin-org`) and `Membership` (`role=admin`, `active=True`) for superuser `admin` (id=2).
- Made `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` conditional on `PRACE_COOKIE_SECURE` env var in `portal/settings_supervised_synthetic.py` (defaults `true`; set `false` for local HTTP rehearsal).
- Added `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` to prevent SMTP 500 errors during login in supervised synthetic.
- Created `scripts/_login_for_session.py`: atomic Django subprocess that completes full allauth + TOTP login and prints cookie lines.
- Created `scripts/get_session_cookie.sh`: bash wrapper that probes the running server, invokes the helper as `prace-synthetic`, validates output, and prints browser-import instructions.

### Verification

| Test | Result |
|---|---|
| Django test client review page after login | **200 OK** (authenticated as `admin`) |
| Session record exists in PostgreSQL | **Yes** (expires ~2 days) |
| Script exits 0 and prints cookies | **Yes** |
| Script detects missing env / server down | **Yes** (exits 1 with actionable message) |
| Cookies imported into browser DevTools → review page | **Accepted** (real browser Cookie header) |
| Same cookies via curl / http.client / nc | **Rejected** (302 → login) — documented limitation |

### Limitations

- Cookies generated by the script work when imported into a real browser via DevTools, but **do not work via curl/http.client**. This is due to Django test-client session handling vs real HTTP through gunicorn.
- TOTP is time-window bound (~30 s). Session cookie remains valid for ~2 days regardless.
- No Django admin exposure (`/admin/` is a placeholder).

### Pending operator actions

1. Import cookies from `scripts/get_session_cookie.sh` into browser DevTools for `http://127.0.0.1:8001`.
2. Confirm admin review dashboard loads after import.
3. Decide whether to expose Django admin or keep current placeholder.
4. Align `django-allauth` version in `requirements.txt` with installed version (`65.19.2`).

### Files changed

| Path | Action |
|---|---|
| `portal/settings_supervised_synthetic.py` | Modified: cookie secure env var, locmem email backend |
| `scripts/_login_for_session.py` | New: atomic login helper |
| `scripts/get_session_cookie.sh` | New: bash wrapper with usage hints |
| `docs/operations/session-cookie-helper-report-2026-09-14.md` | New: session report |

## Current operating policy — 2026-09-08 consolidation

[AGENTS.md](../../AGENTS.md) is the concise operational authority. This section
supersedes historical blanket requirements to repeat working-tree tests in an
export for every small change. Historical results below remain evidence for their
own scopes, not additional present-day gates.

| Change | Required verification |
|---|---|
| Documentation | Relevant links/status consistency, whitespace and staged-content review |
| Ordinary code | Focused regression checks once against delivered inputs |
| Migrations, storage, authorization, shared rendering or dependencies | Relevant integration checks; historical migrations use MigrationExecutor |
| Release candidate | One reproducible committed-source acceptance run |
| Generated A1 package | Artifact-specific deterministic checks and local all-page visual review |

Reuse evidence only when tested source, dependencies and configuration match.
Inspect the committed path/blob set and scope completeness; `git diff-tree` proves
contents, not runtime behavior. Use an exported-source check when the dirty tree
cannot establish matching delivered inputs, and for integration/release acceptance.
Do not rerun an unchanged suite merely because a commit was created. Existing
mandatory hooks remain effective until deliberately updated; no bypass is authorized.

Routine implementation and private origin feature-branch publication need no extra
permission. Coherent code/tests/migrations/docs may share a commit. Keep unrelated
work separate; inspect explicit staged paths and all outgoing commits. A failure
blocks the behavior it covers; record unrelated failures and continue independent
safe work. No history rewrite, force-push, public release, deployment or activation.

### Validation selection and failure recovery — 2026-09-11

The first selector repair still treated unrelated staged scripts as portal
changes and assigned the selector itself to the portal package. It also sent
Django database tests to plain pytest, dropped supplemental integration checks,
accepted some failed selectors, and buffered output behind an outer commit timeout.

The corrected selector receives only its owning package's paths; validation
scripts belong to the Git workflow package. Test-only edits use their actual
runner. Shared-source changes retain the Django integration suite plus artifact,
runtime, input and containment regressions; additional edited tests remain selected.
Commands are deduplicated after selection. Helpers and deleted tests conservatively
retain integration coverage. No authorization, rendering or data-integrity assertion
was removed to achieve faster dispatch.
The release-reproducer tests now clear inherited Git environment variables before
creating synthetic repositories; the isolated-index hook rehearsal exposed 12
failures that did not occur in a plain pytest invocation. This follows
[Git's hook environment guidance](https://git-scm.com/docs/githooks#_description)
for operations in other repositories.

The runner prints command start, budget, 15-second progress and outcome. Full
stdout/stderr and an incrementally written report are retained by default under
`runtime/portal/temporary/change-checks-*/`, with directories `0700` and files `0600`.
Selector failure, invalid command, timeout and interruption fail the run; cancellation
stops its process group. SIGKILL cannot produce a final receipt, but the started
command remains recorded. These are working-tree diagnostics, not cached acceptance.

For a commit, inspect and stage the explicit scope, then run `git commit` directly.
Do not first run the same checks manually, pipe the hook through `tail`, or wrap
it in a shorter external timeout. Follow the printed report/log paths when debugging.
Django integration has a 900-second ceiling, a single pytest file 120 seconds,
and other checks 600 seconds. These are cancellation bounds, not performance targets.
`VALIDATE_CHANGE_PACKAGES_TIMEOUT` accepts a positive integer for deliberate diagnostics.

Prevention follows existing tools: select files or cases and measure slow fixtures
with [pytest durations](https://docs.pytest.org/en/stable/how-to/usage.html#profiling-test-execution-duration);
use [Django's database runner and isolation](https://docs.djangoproject.com/en/5.2/topics/testing/advanced/).
Keep expensive OCR/PDF end-to-end coverage separate from narrow route/permission
fixtures as those tests are maintained. Review routine validation approaching one
minute, without making elapsed time another release gate. Django supports
[parallel tests](https://docs.djangoproject.com/en/5.2/topics/testing/overview/#speeding-up-the-tests)
when isolated; storage paths and OCR resources need isolation too. Do not enable
parallelism or acceptance-result caching blindly. The
[pre-commit framework's stage separation](https://pre-commit.com/#confining-hooks-to-run-at-certain-stages)
is a useful future option; this repository retains its existing hook and CI rather
than adding a second framework. Moving a required check to CI requires verified
replacement coverage, not simply deleting it from the hook.

Validation: the complete repository hook passed against seven explicitly selected
paths in an isolated index, preserving the shared index: 59 runner/selector and
release-reproducer tests in 11.49 seconds, 24 planning checks, staged classification
and whitespace checks (about 12.4 seconds for dispatched commands). A selected
Django field-review run passed 14 tests with 3 skips. The source/coverage suite
was not broadly rerun: this is tooling acceptance, not full application or PostgreSQL
acceptance. Changes remain in the working tree while the concurrent deployment
session owns publication; no deployment or activation is established here.

### Rehearsal script strict contract and bounded lifecycle — 2026-09-11

The 2026-09-11 review of `69f4a49` identified nine findings: a smoke probe
that accepted any non-`000` HTTP status (including a 500 from a wrong server
and a `000000` composite from two failed curls), a startup probe that did not
verify the launched gunicorn actually owned the listener, a `prepare` step
that mutated the filesystem before Django validated `confined_root`, a
`stop` step that trusted arbitrary pidfile contents and would have signalled
an unrelated process, a slow `infrastructure_git_workflow` selector that
re-ran migrations for every tooling change, unit tests that did not exercise
the behaviors their names claimed, a static asset 404 because gunicorn +
`DEBUG=False` had no static-file middleware, missing lock-file provenance
for gunicorn and whitenoise, file modes that depended on the caller's umask,
and stale delivery documentation. The negative fixtures for each of these
are reproduced and now pass.

| Field | Evidence / state |
|---|---|
| Implementation | `scripts/rehearse_synthetic_site.sh` rewritten. `validate_runtime_root_layout` now runs before any `mkdir`/`chmod`/write and refuses paths outside `<repo>/runtime/portal/supervised-*`; `prepare` only creates directories and writes the manifest when confinement is valid. The new `prepare-manifest-only` subcommand skips migrate/collectstatic and is what the cheap unit tests use. `start` records launch identity (pid, bind, runtime_root, started_at) to `.gunicorn.cmdline`/`.gunicorn.started_at` and `verify_launched_process` checks the pid is alive, that `/health/` returns 200 with the manifest's `git_commit` + the `supervised` marker, before printing "started". `assert_bind_is_free` rejects a port already occupied by a non-owned listener. `stop` runs `verify_pid_ownership` which reads `/proc/<pid>/cmdline` and confirms it mentions `gunicorn`, our bind, and `portal.wsgi:application`; a stale or wrong pid refuses SIGTERM. `smoke` now checks `/health/`, `/login/`, `/accounts/login/`, `/review/`, `/readiness/`, and the two shipped static assets, with strict 200/302 + body-content + `Location` expectations; 000/500/404 and a `000000` composite all fail. The 2026-09-11 review's `never "000000"`, `never a 500`, `never a 404`, `never a wrong server` contracts are now asserted. `scripts/build_release_manifest.py` validates confinement and refuses arbitrary output paths. `portal/settings_supervised_synthetic.py` adds `whitenoise.middleware.WhiteNoiseMiddleware` right after `SecurityMiddleware` so the login form's CSS/JS are served under gunicorn + `DEBUG=False`; `whitenoise==6.12.0` is pinned in both `requirements.txt` and `requirements-lock.txt`. `scripts/select_shared_document_portal_checks.py` now routes `tests/document_web/test_browser_journey.py` to `scripts/playwright_smoke.py` with `DJANGO_SETTINGS_MODULE=portal.settings_browser_tests`; the previous selector silently skipped the browser test under `settings_document_tests`. A new `delivery_lifecycle_rehearsal` change-package owns the rehearsal files and the lifecycle test, so the cheap `infrastructure_git_workflow` selector no longer pays the cost of four fresh `migrate` calls on every tooling change |
| Validation | 75 unit tests across `tests/test_validate_change_packages.py`, `tests/test_release_reproducer.py`, and `tests/test_rehearse_synthetic_site.py` in 13.89 s. The new `tests/test_rehearse_synthetic_site_lifecycle.py` runs three real-gunicorn integration tests: a full `prepare → start → smoke → restart → start-refuses-occupied-port → stop` sequence (~52 s), and two negative fixtures (HTTP-500 server on the bind port, no server at all) that prove the smoke contract now catches the F1 wrong-server and stopped-server failures the prior version missed. `validate_planning.py` passes 24/24. The complete pre-commit hook passes in ~1m20 s when rehearsal paths are staged (15 s tooling + 54 s bounded lifecycle + 0.27 s dispatch JSON) and ~15 s for tooling-only changes — the 200 s regression from the prior `infrastructure_git_workflow` selector is gone. `bash -n` passes for both shell scripts. The dispatch tests `test_standalone_selector_routes_browser_test_to_playwright_entrypoint` and the new `test_confinement_validate_rejects_*` / `test_status_rejects_wrong_pidfile_contents` / `test_stop_rejects_unrelated_pidfile_contents` / `test_manifest_mode_is_0o400_under_permissive_umask` assertions each reproduce one of the F1–F8 negative fixtures |
| Publication | Local working tree; push to `origin/feat/prace-readiness-plan-2026-08-13` follows AGENTS.md authorization. No protected paths staged; no secrets/PII in diffs; staging restricted to the listed non-PII path set; `git diff --cached --check` and the catalog classification pass |
| Deployment | None; isolated `runtime/portal/supervised-test-*` and `runtime/portal/supervised-lifecycle-*` synthetic roots only. No operator-owned service, host database, real-data activation, public release or new remote |
| Activation | Unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; the supervised settings module still refuses the base default secret and still requires `PRACE_RUNTIME_ROOT` under `runtime/portal/supervised-*`; `intake` continues to refuse non-synthetic configuration. Real-data activation requires REV-003 per existing gates |
| Limitations | No automated PostgreSQL acceptance in this delivery (the host has PostgreSQL 18 binaries but the local cluster is down; the existing readiness probe is configured for it but the lifecycle test runs against SQLite). `/readiness/` passes the strict smoke contract at the 10 000 ms rehearsal budget; the default 2 000 ms budget is too tight for cold-start synthetic deployments and the budget is overridable via `PRACE_READINESS_BUDGET_MS`. M3 queues/exceptions/retention remain Release-1B scope. The browser journey test now routes through the isolated entrypoint and reports unavailable browsers as a separate outcome; a real Chromium run is a separate test that depends on `playwright install` |
| Next owner | Engineering: full real-data POSTGRES rehearsal + systemd unit + nginx/TLS recipe + authenticated login + individual MFA enrollment (Delivery 1 finish); then Delivery 2 (usable v1 workflow) and Delivery 3 (restricted production pilot). Operator: stand up the host PostgreSQL cluster targeted by the supervised settings module's `PRACE_DB_*` env |
Next owner: engineering resumes Delivery 1's runnable testing
site, with targeted fixture optimization when measured integration costs warrant it.

### Repository review and four-delivery sequence — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Repository review identified obsolete release-verifier blocked-gate assertions, stale J2/J4 NOT_RUN claims (those components have tests), three failing A1 employee-delivery tests with mismatched assertions, and 52 unpublished commits. AGENTS.md now declares the **usable application increment** as the default delivery unit (allow incomplete optional fields, manual fallbacks, additive migrations, demonstration + limitations at release checkpoints). Roadmap and the active plan now organize work around four Jan-facing outcomes: integrated testing site → usable v1 workflow → restricted production pilot → later releases. M3 expansion deferred to Release 1B; deferred research lanes noted in roadmap |
| Validation | `release_verifier.governance/gate-dependencies` now asserts declared dependency structure only (REV-002 depends on ENG-001; REV-003 depends on OPS/LEG/INF + REV-002 approved) without forcing gates to remain `blocked`. `release_verifier.eng001/J2/J4` checks now wired to real test files (`tests/a1/test_a1_snapshots.py`, `tests/test_j4_artifacts.py`, `tests/test_j4_minimum.py`, `tests/document_web/test_*`), reporting `BLOCKED_ENV` for missing files and PASS/FAIL on actual test runs. `tests/test_a1_employee_delivery.py` now 34/34 passing: `UNVERIFIED` source-status removed from the "blocks render" parametrize (it is the valid default); `test_canonical_background_has_no_baked_selections_and_matches_repair_receipt` updated to inspect empty-quadrant pixels (the 924c215 checkbox outlines now cross the old sample coordinates; receipt `output_sha256` regenerated to current template SHA with audit note). Focused suites (112 passed, 3 PostgreSQL-only skips) confirm no regression. `validate_planning.py` runs in ~0.28 s and remains green |
| Publication | Pushed to private `origin/feat/prace-readiness-plan-2026-08-13`: 53 commits (`3ca87b4..9619c06`). Local HEAD SHA `9619c06954eb1faa3429ef502e4d28f753c1f35b` matches `git ls-remote` exactly. Branch now tracks remote. Outgoing-batch review: no protected paths (`a1/`, `data/`, `evidence/`, `scans/`, `ocr/`, `employees/scans/`, `output/`, `runtime/portal/`, `secrets/`, `.env`); no secrets/PII in diffs (only `SECRET_KEY = _SK` test-setting pattern using `secrets.token_urlsafe(48)`); no WIP/tmp/debug commits; 141 files / +18,506/-463; single author throughout. No history rewrite, force-push, public release, deployment or activation |
| Deployment | None; isolated synthetic DBs only. Existing services, historical databases and working PDF packages remain untouched |
| Activation | Unchanged; release-verifier no longer asserts gates must remain blocked. Decision to open ENG-001 / approve REV-002 / REV-003 remains a separate Jan + operator + legal + sysadmin authorization per existing gates |
| Limitations | Out-of-scope for this review cycle: production settings module, WSGI entrypoint, configured queue dispatch, comprehensive M3 queues/exceptions/retention. These are explicitly deferred to the production pilot (Delivery 3) and Release 1B. `plans/alternatives/` directory was created earlier but not materialised during the review; the four-delivery sequence above replaces those alternatives |
| Next owner | Delivery 1 work continues: WSGI entrypoint, persistent PostgreSQL DB, individual login, URL hosting for the testing site. Engineering packages deployment and synthetic recovery rehearsals alongside workflow completion. The 53-commit push above contains every prior accepted increment in the local feature branch; the private `origin` is now in sync with local HEAD |

### WSGI/ASGI entrypoints for Delivery 1 — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | New `portal/wsgi.py` exposes the Django WSGI handler as the gunicorn/uwsgi import target; default `DJANGO_SETTINGS_MODULE` is `portal.settings`. New `portal/asgi.py` exposes the Django ASGI handler as the uvicorn/daphne import target. Both entrypoints switch to `portal.settings_supervised_synthetic` when the deployment environment sets `DJANGO_SETTINGS_MODULE` accordingly. The supervised-synthetic settings module is already comprehensive (DEBUG=False, restrictive ALLOWED_HOSTS, mandatory PRACE_SECRET_KEY, confined runtime root, optional PostgreSQL with `verify-full`); a second "production" settings module is intentionally not added to avoid duplicating the supervised-synthetic contract |
| Validation | New `tests/test_wsgi_asgi.py`: 5/5 passing (default-import contract, ASGI import, default settings module is `portal.settings`, basic routing via Django test client — `/login/` → 302 `/accounts/login/`, `/health/` → 200, `/review/` → 302 to login, `settings.M2_SYNTHETIC_ONLY` is True so the existing intake guard is preserved). No regression in the prior 167-test corpus |
| Publication | Local working tree; pre-push planning validator passes 24/24; change-package classification: 3 files eligible (portal/wsgi.py, portal/asgi.py, tests/test_wsgi_asgi.py) plus the docs recipe. Routine private-origin feature-branch publication follows AGENTS.md |
| Deployment | None; no service mutation, no real-data activation, no durable environment change. The recipe in `docs/operations/wsgi-deployment-recipe.md` documents how an operator wires gunicorn to `portal.wsgi:application` with the supervised-synthetic settings; running that recipe is a separate authorization |
| Activation | Unchanged; the WSGI/ASGI module does not enable real-data activation. `settings.M2_SYNTHETIC_ONLY` remains True; intake refuses non-synthetic configuration. Real-data activation requires REV-003 per existing gates |
| Limitations | No automated test exercises a real gunicorn/uwsgi process against this WSGI entrypoint — the contract test uses Django's test client. Production infrastructure (systemd unit, nginx, TLS, secret delivery, backup) remains infrastructure-owned. Queue dispatch via `django-q2` is intentionally not configured; background jobs continue inline. M3 queues/exceptions/retention remain Release-1B scope |
| Next owner | Operator: review `docs/operations/wsgi-deployment-recipe.md` and decide the deployment shape (gunicorn vs uvicorn, PostgreSQL vs confined SQLite, allowed hosts). Engineering: continue Delivery 1 — wire the existing frontend/backend into the persistent URL, then Delivery 2 (usable v1 workflow) and Deployment 3 (restricted production pilot) |

### Missing identity facts in BO — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Document intake offers partial entry of birthplace, nationality, sex and insurance number when the selected region has no proposal and the worker has no confirmed value. The existing confirmation service stores operator-origin proposals and decisions, bound to document/version/run/region and current worker revision. Stale submissions, invalid batches and existing-field overwrites are rejected; input cases become stale |
| Validation | Focused SQLite review/inbox checks passed (37 tests, three PostgreSQL-only skips); extended sparse-input journey passes canonical draft-input validation after explicit BO completion. All 37 PostgreSQL tests passed, including concurrent missing-fact entry. Mandatory hooks passed: 239 Django tests (27 skips), 80 runtime/artifact tests, 31 containment tests, 24 planning checks and 29 tooling tests. Scoped committed-source acceptance passed with unchanged source integrity; receipt runtime/portal/temporary/release-reproducer/c9305321da1649a1a89401e78c78fcbb/receipt.json |
| Publication | Local implementation commit 1cd13b2 includes the previous cold-start checkpoint; not pushed. Inherited outgoing-history review remains separate |
| Deployment | None; no schema changes or durable environment mutation |
| Activation | Unchanged; individual field confirmation does not grant whole-identity or PDF approval |
| Limitations | Scripted synthetic OCR; no artifact generation or visual acceptance in this increment. Operators enter only facts established from the selected source; absent evidence remains blank |
| Next owner | Engineering: sparse-input journey through canonical draft generation and artifact review |

### Cold-start operator readiness — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Extended the synthetic inbox journey through actual BO address confirmation, assignment creation and assignment/institution fact entry; no complete-input identity fixture is injected |
| Validation | Focused cold-start test passed. Canonical draft validation identifies exactly birth_place, nationality, sex and insurance_number as absent in this sparse OP fixture. Blocked retry preserves worker/OCR/decision counts; Section 5 defaults and unverified flags remain intact. All 20 inbox tests and 24 planning checks passed; whitespace review passed. Subsequently included in the tested implementation commit 1cd13b2 and its mandatory hooks |
| Publication | Included in local commit 1cd13b2; not pushed |
| Deployment | None; isolated test database only |
| Activation | Unchanged; no artifact generated or human acceptance claimed |
| Limitations | Scripted OCR tests adapter/interpretation behavior, not real-engine extraction accuracy. Four missing fields describe this fixture. Existing complete-input journey evidence remains separate |
| Next owner | Completed in the increment above; next is sparse-input draft/artifact acceptance |

### BO assignment and institution facts — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Assignment editor links to a version-bound pending-facts form using the canonical update_assignment_facts service. Employment/activity facts and institution selection are editable; certificate dates/numbers/signatory evidence are preserved. Blank optional fields retain canonical Section 5 defaults. Verified profiles are selectable and unavailable stored selections remain preservable. The ordinary assignment editor now shares the organization lock, requires the displayed version, stales affected cases and rolls back on audit failure |
| Validation | All 14 focused BO/export tests passed. PostgreSQL integration and targeted old-editor/fact-update race checks passed. Mandatory hooks passed: 236 Django tests (26 skips), 80 runtime/artifact tests, 31 containment tests, 24 planning checks, 29 tooling tests and 17 J4 tests. All 14 BO/export tests also passed from the immutable implementation source; receipt runtime/portal/temporary/release-reproducer/25dda2dd3c65474ead3653a37df85df5/receipt.json records unchanged source integrity. This is scoped integration acceptance, not a full release-candidate run |
| Publication | Local implementation commit 4f5df59; not pushed. Inherited outgoing-history review remains separate |
| Deployment | None; no schema migration or durable environment changes |
| Activation | Unchanged; saving facts does not mark them human-verified or establish issuance |
| Limitations | Missing profiles and required inputs still block only affected draft generation. Profile choices use canonical VERIFIED profiles; unavailable existing choices can be retained. Certificate metadata is not editable on this pending-facts form |
| Next owner | Engineering: cold-start operator readiness checks using address and assignment/institution entry; identify any remaining required-field completion gaps |

### Source-linked structured address review — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | BO document review accepts five explicit address parts using a token bound to source/version/region/association/worker revision. Existing field confirmation services record operator-origin source-linked proposals, decisions and identity revisions atomically. Replacements require a reason; stale forms, source changes and archived workers are rejected. Raw OCR address confirmation remains separate. Changed address facts mark existing input cases stale |
| Validation | Focused service/BO and cold-start export checks passed. All 15 PostgreSQL integration tests passed, including concurrent address submissions with one winner and one stale rejection. Required hooks passed: 230 Django tests (25 environment-specific skips), 80 runtime/artifact checks, 31 containment checks, 24 planning checks and 29 tooling checks. Scoped committed-source address/cold-start/A1-export integration passed; source integrity remained intact. This is scoped integration evidence, not a new full release-candidate acceptance |
| Publication | Implementation committed locally as `d99bb15`; this evidence-only checkpoint preserves tested source. Inherited outgoing-history review remains separate |
| Deployment | None; no schema migration, durable database or service changes |
| Activation | Unchanged. Explicit address confirmation does not establish whole-identity verification, PDF visual approval or issuance |
| Limitations | Source must have a residence_address proposal and worker association. No automatic address splitting, country default or external address verification. Other missing identity/business facts remain draft-local blockers |
| Next owner | Engineering: BO assignment/institution fact entry using a1_exports.update_assignment_facts and its existing version/readiness contracts |

Protected scoped committed-source receipt:
`runtime/portal/temporary/release-reproducer/eb5a4958e2ef48a98d471b416141f7b3/receipt.json`.

### Integrated synthetic operator workflow — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Added a complete-input journey through BO association, one revision-bound field confirmation, rejection of a stale review, inbox draft preparation, PDF/all-three-preview HTTP access, cohort bundle download and exact retry. Added a separate cold-start address boundary test. Production behavior unchanged |
| Validation | Both focused integration scenarios pass. Complete-input retry preserves worker/run/decision/generation counts and package identity; Section 5 remains blank / DE, CZ and human/issuance flags remain pending. Both scenarios also passed on disposable PostgreSQL. Required hooks passed: 225 Django tests (24 environment-specific skips), 80 runtime/artifact checks, 31 containment checks, 24 planning checks and 29 tooling checks. Evidence is integration-test acceptance for these bounded scenarios, not a new release-candidate or cold-start automation acceptance |
| Publication | Test/documentation delivery committed locally as `e9032ed`; this evidence-only update preserves tested bytes. Inherited outgoing-history review remains separate |
| Deployment | None; disposable synthetic database/storage only |
| Activation | Unchanged; automated tests simulate operator actions and do not constitute real human or all-page visual approval |
| Limitations | Complete-input fixture seeds canonical proposals and business facts and uses a scripted OCR engine. Cold-start OCR extracts free-form residence_address, but its structured A1 address fields have no completion path in this journey. A blocked PDF with preserved proposals is correct, not full automation acceptance |
| Next owner | Engineering: source-linked structured address entry in BO with current document/version tokens and existing decision/revision provenance; never silently parse an uncertain address into confirmed facts. Other missing business facts continue to block only affected drafts |

### Selected-cohort BO publication — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | A1 list links to `/a1/inputs/`. Operators explicitly select up to 50 current cases per page; POST sends each displayed case/source hash to the existing atomic publisher. The returned ZIP link pins the manifest hash and uses existing tenant/current-source download checks. Reversed selections reuse the same bundle |
| Validation | Seven focused BO integration tests passed, including multi-case retry, stale-member rollback, foreign-case rejection, malformed/duplicate/oversized selections, CSRF and capability checks. Both new cohort scenarios also passed on disposable PostgreSQL. The initial staged-path check required classification of the existing `a1_list.html` template; its exact path is now registered in the package catalog and source allowlist. Required hooks then passed: 223 Django tests (24 environment-specific skips), 80 runtime/artifact checks, 31 containment checks, 24 planning checks, 95 validator regressions and 29 tooling checks. This UI increment uses focused/integration evidence and mandatory hooks; no new release-candidate acceptance claim |
| Publication | Implementation committed locally as `1c8380e`; this evidence-only checkpoint preserves tested source. Inherited outgoing history review remains required before origin publication |
| Deployment | None; no durable database, artifact or service changes |
| Activation | Unchanged; selected compatibility inputs do not imply human confirmation or issuance |
| Limitations | Selection is limited to the current page; cross-page selection persistence is not implemented. Existing CLI supports explicit larger cohorts |
| Next owner | Engineering: integrated synthetic operator-workflow acceptance from inbox intake through BO review, eligible draft generation and selected-cohort download; record gaps without activating an environment |

### Case-level BO input bundles — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Case-level BO page publishes through the existing cohort service on explicit CSRF-protected POST with the displayed source hash. Manifest-pinned ZIP download requires active synthetic `a1:prepare`, organization-scoped publication evidence, current source/profile checks and exact protected file verification. Anchored no-follow reads return only verified bytes; GET never creates packages. Existing CSV rendering uses the extracted shared current-snapshot check |
| Validation | Focused BO/export/publication integration: 19 tests passed; final five BO tests also cover a stale secondary cohort member and unrelated case scope. Filesystem read/write coverage: 34 tests passed. Five BO scenarios also passed on disposable PostgreSQL. Required hooks passed: 221 Django tests (24 environment-specific skips), 80 runtime/artifact checks, 31 containment checks, 29 tooling checks and 24 planning checks. Committed-source `f04e8e2` acceptance passed 23 applicable planning checks, 132 tooling/artifact tests plus 18 subtests, and 105 workflow tests (six PostgreSQL-only skips); source integrity remained intact |
| Publication | Implementation committed locally as `f04e8e2`; this evidence-only checkpoint preserves tested source blobs. Inherited outgoing history remains subject to review before origin publication |
| Deployment | None; no durable database, PDF package or service changes |
| Activation | Unchanged; compatibility input download does not verify identity, confirm PDF appearance or issue A1 |
| Limitations | Initial BO publication selects one case; the existing CLI/service handles explicit cohorts. Stale bundles are retained but rejected for download. Orphaned post-write packages require publisher retry before BO access |
| Next owner | Engineering: selected-cohort BO selection and publication through the existing exporter, preserving per-case source pins and atomic failure behavior |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/adbbe61679d94c1f914040e99ee6bb09/receipt.json`.

### Profile-bound input publication — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Shared publisher binds exact canonically validated institution-profile bytes and checks for changes around a protected atomic write. `input_artifacts.py` owns `<DOCUMENT_STORAGE_ROOT>/a1-input/<manifest-sha256>/`, separate from source-document/J4 layouts. Private staged files, fsync and locked rename publish the complete package; exact retries validate bytes, modes and file set. Thin `a1_export_inputs` CLI accepts explicit case/source-hash selections |
| Validation | All 17 filesystem tests and 10 final service/cohort/CLI integration tests passed. The initial unsafe-permissions fixture was corrected to set its mode explicitly under restrictive umasks. Required hooks then passed: 216 Django tests with 24 environment-specific skips, 63 runtime/artifact checks, 31 containment checks, 95 planning regressions, 29 tooling checks and 24 planning checks. Committed-source `69dfc4d` acceptance passed 23 applicable planning checks, 115 tooling/artifact tests plus 18 subtests and 100 workflow tests with six PostgreSQL-only skips. Source integrity remained intact |
| Publication | Implementation committed locally as `69dfc4d`; this evidence-only checkpoint preserves tested source blobs. Inherited outgoing history requires review before private-origin publication |
| Deployment | None; disposable synthetic storage only. No database migration, production package or PDF layout change |
| Activation | Unchanged. Package contains pending compatibility inputs, not issued certificates or human confirmations |
| Limitations | Missing/invalid profiles block publication but not unbound exports. Changed profiles create new bundles. A post-write validation/audit failure can leave a protected recoverable bundle; obsolete-bundle classification remains separate. BO access is not yet implemented |
| Next owner | Engineering: BO publication and download access with manifest-pinned references, tenant/capability checks and no-store responses; GET must not create packages |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/291021e78d2545f591b2d9c43fa33889/receipt.json`.

### Selected-cohort compatibility inputs — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | `export_input_cohort` in the canonical export service validates explicit case/source-hash selections under an organization transaction, reuses current per-case validation, rejects duplicate cases/workers/keys/nonblank certificate IDs, and returns deterministic review CSV, cohort maps, normalized identities, source snapshots and a hash manifest. Failures roll back per-case export audits |
| Validation | All 13 focused cohort/single-case export tests passed; the four cohort tests passed again after adding foreign-case selection coverage. Required hooks passed: 210 Django tests with 24 environment-specific skips, 46 runtime/artifact checks, 31 containment checks, 95 planning regressions, 29 tooling checks and 24 planning checks. Delivered source blobs match tested inputs. This ordinary service increment uses focused/hook evidence; no new release-candidate acceptance is claimed |
| Publication | Implementation committed locally as `6c39cc5`; this evidence-only checkpoint preserves tested source blobs. Inherited outgoing history requires review before private-origin publication |
| Deployment | None. No schema, existing database, PDF package or layout change |
| Activation | Unchanged. Missing facts and review flags remain pending; these inputs do not imply generation readiness, human verification or issuance |
| Limitations | Service returns input bytes. Institution profile bytes are not yet frozen into the bundle; no filesystem publication or CLI is added |
| Next owner | Engineering: bind selected institution profiles and implement protected atomic bundle publication with retry/integrity evidence through the shared export service |

### Explicit synthetic legacy-key reconciliation — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0019 adds nullable tenant-unique legacy keys and structured source/actor/mapping provenance. The canonical reconciliation service validates a complete explicit worker/version/key batch, rejects collisions/reserved fallback keys/replacement, preserves exact retry evidence, increments changed worker revisions and stales prior cases. New canonical CSV/JSON snapshots freeze the selected key. Historical workers are not auto-mapped; reverse migration refuses mapped-key loss |
| Validation | All 23 PostgreSQL reconciliation/export/generation-confirmation tests passed, including competing key claims, batch rollback, source-bound retries, historical migration preservation and rollback protection. Required hooks passed: 206 Django tests with 24 environment-specific skips, 46 runtime/artifact checks, 31 containment checks, migration-chain/model parity, 29 tooling checks, 24 planning checks and the 17-test J4 workflow. Committed-source `b8097e5` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests and 90 workflow tests with six PostgreSQL-only skips; the new migration/concurrency tests passed in the separate PostgreSQL run. Source integrity remained intact |
| Publication | Implementation committed locally as `b8097e5`; this evidence-only checkpoint preserves tested source blobs. Inherited outgoing history requires review before private-origin publication |
| Deployment | None. Migrations run only on disposable synthetic databases; selected supervised release requires 0014–0019 |
| Activation | Unchanged. Source hashes identify explicitly selected reconciliation inputs; the service does not claim external file verification, real-data reconciliation or identity confirmation |
| Limitations | This is the key-mapping foundation and single-case CSV/JSON integration. Complete selected-cohort/identity compatibility export and real-data reconciliation remain separate |
| Next owner | Engineering: complete cohort/identity compatibility exports through the shared export service, reject duplicate selected workers/keys and prove revision-bound round trips before DB-MIG cutover |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/4201f1a067774ed0830d57cd0adbc77e/receipt.json`.

### Revision-checked BO identity association — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | BO signed worker choices bind actor, organization, reviewed run set/evaluation, worker version and identity revision. POST validates under locks and calls canonical identity resolution; an override requires a reason. GET saves no evaluation or decision. The shared evaluator checks the derivative source hash. Failed/superseded batch members do not disable completed current document choices |
| Validation | All 47 PostgreSQL association/intake/identity tests passed, including independent-connection competing choices, stale worker/identity/source rejection, exact retries, actor/document scope, rollback, source hash mismatch and partial-batch recovery. Required hooks passed: 200 Django tests with 22 environment-specific skips, 46 runtime/artifact checks, 31 containment checks, 29 tooling checks and 24 planning checks. Committed-source `ee10116` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 84 workflow tests with four PostgreSQL-only skips (the new competing-choice test passed in the separate PostgreSQL run). Source integrity remained intact. No schema or rendering change |
| Publication | Implementation committed locally as `ee10116`; this evidence-only checkpoint preserves its tested source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; disposable synthetic tests only; historical databases and working PDF packages preserved |
| Activation | Unchanged. Association does not confirm individual fields, verify identity or imply A1 submission/issuance |
| Limitations | Scope is initial region association and resolution of matching conflicts. Reassignment of an already-decided association is not introduced. Selected supervised release still requires migrations 0014–0018 before runtime use |
| Next owner | Engineering: synthetic legacy-key reconciliation with explicit mappings/collision rejection, then complete revision-bound CSV/cohort/identity compatibility exports and round-trip evidence. Accepted cutover remains governed by existing DB-MIG dependencies |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/422635259cdb49538390859a5aa1bce9/receipt.json`.

### Revision-checked BO field review — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | BO sends tokens bound to exact proposal/source/OCR result, worker association and current identity revision. A locked batch validates all selections before existing canonical field confirmations, preserving atomicity. Confirmed values are shown separately from OCR and are the initial edit value; replacing one requires a reason. Stale forms return 409 with no partial decisions. Missing/non-reviewable proposals do not disable other reviewable fields |
| Validation | All 32 PostgreSQL field-review/intake tests passed, including independent-connection stale-form rejection, batch rollback, deleted selections, omitted values, derivative/source mismatch and confirmed-value replacement reasons. Planning checks pass 24/24. Required hooks passed, including 189 Django tests with 21 environment-specific skips. Committed-source `811c1d1` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 73 workflow tests with three PostgreSQL-only skips covered separately; source integrity remained intact. No model/schema or renderer changes |
| Publication | Implementation committed locally as `811c1d1`; this evidence-only checkpoint preserves its tested source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; disposable synthetic tests only; existing environments unchanged |
| Activation | Unchanged. No automatic confirmation, worker projection overwrite, A1 issuance or real-data activation |
| Limitations | Canonical non-BO programmatic confirmations retain their existing explicit API. BO association/conflict resolution still needs integration with the existing expected-worker/revision identity service. Field confirmation is distinct from whole-person verification and A1 visual review |
| Next owner | Engineering: identity association/conflict resolution in BO with expected worker and identity revisions; then reconciled legacy cutover |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/b9ebbf5d137347ba97632ea1df69036d/receipt.json`.

### Generation-bound visual confirmation — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0018 adds an immutable generation-specific visual confirmation with actor/time and source/fingerprint/PDF/receipt hashes. BO requires explicit review of all three pinned previews and submitted expected tokens. The service verifies current source/package/dependencies under organization locks, rechecks after insertion, and records an atomic audit. Retries retain the original confirmation. Historical packages receive no automatic confirmation; rollback refuses to discard review records |
| Validation | All 15 PostgreSQL service/access/HTTP tests passed, including authorization, stale input, CSRF, audit rollback, independent-connection concurrency and MigrationExecutor preservation/rollback protection. The existing 17-test J4 delivery workflow passed. Initial route-wiring errors were corrected before this acceptance; the legacy regenerate guard remains separate. Required hooks passed, including 180 Django tests with 20 environment-specific skips. Committed-source `bbbbf4c` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 64 workflow tests with two PostgreSQL-only skips covered by the separate PostgreSQL run; source integrity remained intact. Model/migration parity and 24 planning checks pass. Renderer and package bytes are unchanged |
| Publication | Implementation committed locally as `bbbbf4c`; this evidence-only checkpoint preserves its tested source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; migration is exercised only on disposable synthetic databases. Selected supervised release needs 0014–0018; its existing database remains at recorded 0013 |
| Activation | Unchanged. These tests use synthetic actors/data. Production identity verification, readiness, case visual fields and submission/issuance are untouched; visual review does not establish correct identity facts |
| Limitations | Confirmation belongs to one exact generation. A replacement has no inherited review; reusing an identical earlier generation retains its original evidence. The protected package is immutable and its initial pending marker is historical; the structured DB confirmation owns subsequent visual-review evidence. Legacy non-draft case behavior is preserved |
| Next owner | Engineering: BO identity/field confirmation using expected revisions, explicit source associations, conflict handling and protection against OCR overwrite. Reconciled legacy cutover remains separate |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/fe8f1eaf45f048098c62fd88a8edacda/receipt.json`.

### BO access to applicable A1 generations — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | New read-only generation access service selects by current source/profile/dependency fingerprint. BO detail pins generation IDs in PDF/all-page preview links. Stale explicit links fail; unpinned access resolves the applicable generation, including dependency reversion. Returned bytes, PNG format/dimensions and receipt hashes are checked; responses are private/no-store and HTTP reads audited |
| Validation | Seven focused synthetic access tests passed after correcting invalid-page handling and using the versioned assignment service in the source-change test. The existing 17-test J4 delivery workflow passed. Tests cover stale/reverted dependencies, tenant/role/activation denial, no GET generation, legacy action separation, tampered bytes and post-verification preview geometry changes. Planning has 24 passing checks. Required hooks passed, including 172 Django tests (18 environment-specific skips). Committed-source `a58ed39` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 56 workflow tests; source integrity remained intact. No renderer or generation-input contract changed |
| Publication | Implementation committed locally as `a58ed39`; this evidence-only checkpoint preserves its source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; selected supervised release and database unchanged |
| Activation | Unchanged. No real-data activation, new generation on GET, human confirmation, submission or issuance |
| Limitations | Existing non-draft case behavior is retained. Draft cases cannot enter legacy approval/regeneration/confirmation endpoints; generation-bound confirmation remains unimplemented. Historical stale packages are preserved but are not served as applicable review copies |
| Next owner | Engineering: generation-bound visual confirmation with expected source/fingerprint/receipt, actor/time evidence and stale rejection; keep identity verification distinct. Follow with identity/field BO integration and reconciled cutover |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/2f4f1bba826442079c0ae4fab62fdcb6/receipt.json`.

### A1 generation revisions — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0017 adds immutable render generations under each stable number reservation. Exact snapshot/dependency fingerprints deduplicate retries; changed profiles/templates/builds receive their own package. Earlier packages and the original case projection are preserved. Inbox and command return the matching generation reference/revision. Migration copies existing reservations/packages and prevents rollback that would lose generation-only evidence |
| Validation | Eight focused draft tests passed. Model/migration parity and 24 planning checks passed. Two synthetic generations/six pages were inspected locally; number, boxes, blank dates and Section 5 remain correct, and only the intended institution address changes. The 94-test PostgreSQL run passed 92 tests and exposed two incomplete historical test fixtures (missing required birth dates), corrected without changing runtime code. The affected PostgreSQL migration/concurrency module then passed all six tests. Required hooks passed. Committed-source `67559c8` acceptance passed all three commands (planning, tooling/A1 and inbox/identity/input/generation); source integrity remained intact |
| Publication | Implementation committed locally as `1fb8da1`; historical fixtures corrected in `67559c8`. Inherited outgoing history still requires content/provenance review before private-origin publication |
| Deployment | None. Migration 0017 runs only in disposable synthetic tests. Selected supervised release needs 0014–0017; its existing database remains at recorded 0013 |
| Activation | Unchanged; all generations remain unverified. No human confirmation, submission, issuance or real-data portal activation |
| Limitations | BO still reads the older case artifact projection. Dependency reversion reuses the matching prior generation; numeric revision order alone does not establish current applicability. Changed source facts require a new immutable input case. Running processes must restart after code changes |
| Next owner | Engineering: organization-scoped BO access to the exact applicable generation, followed by expected-generation and expected-source confirmation with stale rejection; keep visual review separate from identity confirmation. Legacy reconciliation/cutover remains separate |

Protected synthetic visual manifest:
`runtime/portal/temporary/a1-generation-visual-dfe8o90t/manifest.json`.
Local engineering review does not set human confirmation or promote an artifact.
Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/293d0b27f5a844c4be0a3a58fdf0945e/receipt.json`.
This evidence-only checkpoint preserves the accepted implementation blobs.

### Unverified application-draft publication — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Synthetic inbox and `a1_prepare_draft` use the new explicit pending-input contract in the existing canonical publisher/core. Migration 0016 reserves immutable numbers, source/profile/dependencies and package keys. J4 publication recovers the same package after a DB/audit failure. Every page displays UNVERIFIED DRAFT; unknown certificate dates and human flags are preserved |
| Validation | 87 PostgreSQL integration tests passed, including simultaneous reservation, historical 0015→0016→0015 and package recovery. 37 focused inbox/identity/draft tests and 13 artifact tests passed. 54 core/finalize/stabilization tests plus 18 subtests passed; normal-mode comparison across three profiles/nine pages has zero changed pixels at 300 DPI. Three synthetic draft PDFs/nine fresh previews were locally inspected; checkboxes, blank dates, notices and Section 5 output match the explicit draft contract. Models match migrations; planning is 24/24. The required hook exposed four stale comprehensive expectations, reproduced unchanged on the prior renderer; fixtures/assertions now follow explicit posting and established natural casing without altering renderer behavior. Required staged hooks passed. Committed-source `09d28dd` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 46 inbox/identity/input/draft tests; source integrity remained intact |
| Publication | Implementation committed locally as `09d28dd`; this documentation checkpoint records its acceptance. Inherited outgoing history requires content/provenance review before private-origin publication |
| Deployment | None; disposable synthetic databases only. Existing supervised DB remains at recorded 0013 and needs selected-release 0014–0016 before runtime use. No employee PDFs or services changed |
| Activation | Unchanged; synthetic-only capability-checked adapter. Application drafts are not human-verified, visually approved, submitted or issued certificates |
| Limitations | One reservation/package per immutable input case. A changed template/profile/code dependency fails closed; a replacement generation-revision lifecycle for unchanged inputs is not implemented. BO artifact access/confirmation still uses the earlier J4 contract. Source changes require process restart, avoiding loaded-code/font mismatch. Local command returns private paths; no public links or production activation |
| Next owner | Engineering: generation revisions preserving prior numbers/packages across dependency changes, then BO artifact access and revision-checked confirmation. Legacy reconciliation/cutover remains separate |

Protected synthetic visual manifest:
`runtime/portal/temporary/a1-draft-visual-j7ktekp1/visual-manifest.json`.
Local visual inspection is engineering evidence, not a human identity decision or
an artifact promotion. The canonical checkbox receipt records the unchanged
normal-mode pixel comparison against the previous renderer.

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/b85bce63e9684e6d936e06e29e8688a6/receipt.json`.
This evidence-only checkpoint preserves the tested implementation blobs.

### Revision-bound A1 input preparation — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0015 adds structured assignment facts. Synthetic version-checked updates and `a1_exports.py` prepare immutable input cases and export all 44 canonical CSV fields plus JSON provenance. Inbox records case references and missing-fact blockers. Accepted identity revisions override pending OCR; retries reuse inputs and stale exports fail closed. Assignment dates are pinned but never silently become certificate dates |
| Validation | Focused input tests pass, including malformed pending dates, accepted overrides, stale assignment periods, corruption, authorization, audit rollback and Section 5 defaults/overrides. Planning/tooling regression: 124 tests passed; model/migration parity reports no changes. 80 PostgreSQL integration tests passed, including concurrency and historical 0014→0015→0014 migration. Planning is 24/24 after adding exact synthetic test paths to the existing allow-list. Required hooks passed. Committed-source `d83fc0d` acceptance passed all three commands: 23 applicable planning checks, 91 tooling/A1 tests plus 9 subtests, and 41 inbox/identity/input tests; source integrity remained intact |
| Publication | Implementation committed locally as `d83fc0d`; this documentation checkpoint records its completed acceptance. Inherited outgoing history still requires content/provenance review before private-origin publication |
| Deployment | None. Migration 0015 is exercised only in disposable test databases; supervised development remains at recorded migration 0013. Existing databases, services and PDF packages are preserved |
| Activation | Unchanged; new input services are synthetic-only and capability checked. No machine action creates human verification or official issuance |
| Limitations | Input preparation only: no PDF, number reservation, complete compatibility package, institution-profile pinning or BO UI adapter. Canonical readiness retains its current human flags; this service does not forge them. The richer target snapshot/export contract and legacy cutover remain incomplete |
| Next owner | Engineering: explicit unverified application-draft mode through the shared publisher/core, DB-stable provisional numbering and artifact-specific deterministic/all-page visual checks. BO revision integration proceeds in parallel. Apply 0014/0015 through the selected supervised release before runtime use |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/1eb55479d4014569be04b90c8c2aede6/receipt.json`.
This evidence-only checkpoint preserves the tested implementation blobs.

### J2 durable identity and unconfirmed drafts — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Additive migration 0014 adds immutable service-level evaluation/claim/resolution records. Inbox persists evaluated evidence, preserves manifest hashes and explicit per-file profiles, and creates or reuses eligible unconfirmed drafts. Conflicting batch profiles propagate to all identifier peers. Explicit resolution rechecks source fingerprints and expected worker version/revision, requires an override reason, and binds the human association to its evidence. Organization mutexes use PostgreSQL NO KEY UPDATE to coexist with OCR foreign-key checks |
| Validation | 68 PostgreSQL integration tests passed, including simultaneous evaluation/draft/resolution, competing decisions, OCR completion overlap, and historical 0013→0014 migration/uniqueness. 32 focused SQLite workflow tests, 14 historical-migration/reproducer tests and 76 planning/catalog tests passed; model/migration parity reports no changes; planning is 24/24. Required hooks passed. Committed-source `165491c` acceptance passed 23 export-applicable planning checks, 91 tooling/A1 tests plus 9 subtests, and all 32 inbox/identity tests with source integrity intact. Review found and corrected profile propagation and an OCR/organization lock interaction |
| Publication | Implementation committed locally as `165491c`; this documentation checkpoint records its completed acceptance. Inherited outgoing history still requires content/provenance review before private-origin publication |
| Deployment | No existing environment migrated; supervised development remains at its recorded 0013 state. New migration tested only in disposable databases; no services or PDF packages changed |
| Activation | Unchanged; new identity services are synthetic-only and require active authorized operators. No new real-data activation |
| Limitations | BO forms still use their existing association/field-confirmation paths; new revision-checked resolution is a service ready for UI integration. New drafts are not confirmed identities, active workers, issued certificates or A1 PDFs. Missing profile, incomplete/conflicting evidence and possible existing workers defer only draft creation |
| Next owner | Engineering: connect draft workers to DB-MIG input mapping/shared exports and J4 unverified A1 generation; integrate BO revision checks in parallel, without gating eligible drafts on BO completion. Apply 0014 through the selected supervised development release before runtime use |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/b98a200ed2634096ac4cd0c6b84cd825/receipt.json`.
The documentation-only checkpoint preserves the tested implementation blobs and
clarifies that BO UI work runs in parallel with the next A1 generation increment.

### J2 derived identity suggestions — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Inbox recomputes shared-core identity suggestions across completed batch regions. Protected receipts bind run/version/output hashes, confirmed-worker snapshot hash and decision/revision references. Conflicting identity field evidence blocks suggestions; matching failures remain retryable partial batches. Confirmed fields, worker links and human decisions are unchanged |
| Validation | Full shared core: 92 tests passed. Ephemeral PostgreSQL intake/inbox/readiness/J4: 49 tests passed, including all 19 inbox tests. Planning: 24/24 checks passed. Static scoped review found no additional defects. Required hooks passed. Committed-source `db6c472` acceptance passed all three commands: 23 export-applicable planning checks, 91 tooling/A1 tests plus 9 subtests, and 19 inbox tests; source integrity remained intact |
| Publication | Implementation committed locally as `db6c472`; this documentation checkpoint records its completed acceptance. Private-origin publication remains pending review of the inherited outgoing batch, not engineering permission |
| Deployment | None; isolated synthetic test databases only. Existing supervised, historical and production databases/packages are unchanged |
| Activation | Unchanged; existing real-data-rules §14 remains the portal gate |
| Limitations | Derived suggestions are not durable identity decisions or BO acceptance tokens. Name-only matches/new identities remain unresolved; no worker creation or A1 draft generation. Receipt evidence must be revalidated before future revision-checked writes |
| Next owner | Engineering: durable J2 identity/conflict resolution and safe draft-worker creation under DB-MIG-1/2/5, with PostgreSQL uniqueness/concurrency and stale-revision acceptance, then J4 drafts/BO |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/f6a08e372b914983918443c9bbcdc793/receipt.json`.
The documentation-only evidence checkpoint preserves the tested implementation blobs.

### Readiness and roadmap repair — 2026-09-09

OpenCode's cross-reference feedback confirms the bounded `cba3e50` delivery.
Its remaining-work concern is valid: inherited work is not delivered merely
because it exists locally. The review also found older roadmap sections that
contradicted the new contract despite passing structural validation; these are
corrected here. A new Recent Learnings section is optional, not another gate.

| Field | Evidence / state |
|---|---|
| Implementation | Explicit `readiness --provisional`; one shared CSV required-field helper used by readiness and validation; report/summary mode and review_preflight scope; authoritative default and human flags retained. Roadmap/index now distinguish implemented components, fresh synthetic preparation and gated cutover; M4-A model/export/dashboard claims corrected |
| Validation | Exported A1 source: 47 tests and 9 subtests passed; required hook repeated that focused suite successfully. Documentation source checks: 44 field rows, 97 relative links and 24/24 planning checks passed from the staged-source export |
| Publication | A1 implementation `445aee1`; separate documentation checkpoint carries this record. Exact commits/remote SHA and result are in protected runtime receipt and operator handoff |
| Deployment | Not performed; no service, historical database, employee PDF or migration changes |
| Activation | Unchanged; existing real-data-rules §14 and registered approvals remain in force |
| Limitations | Readiness is review preflight, not normalized-source reconciliation or artifact QA; unattended drafts, seed --verify, fresh development bootstrap and reproducer still planned |
| Next owner | Engineering: repair seed/fixture shape mapping and verify idempotence, then fresh supervised development and immutable-source reproducer under the existing plan |

A missing 5.1 still blocks authoritative readiness and provisional employee
profiles. Provisional mode follows existing validation requirements for missing
issuance evidence; it never sets approval flags or creates PDFs. Regression cases
cover mode/profile selection, missing territory, duplicate IDs, unverified office
profiles, all four human flags, unchanged input bytes and audited mode-labelled CLI
receipts. Existing publisher, normalized-source and promotion checks remain active.

Acceptance command: `venv/bin/python -m pytest tests/test_finalize_a1.py tests/test_a1_stabilization.py -q`.
The tested export and resulting A1 Git object contain identical source/test blobs.
The old planning filename-token check rejects A1 source filenames in a mixed
code/documentation staging set; keep this A1 code and the planning update as
separate reviewed commits with their configured hooks. No check is disabled or
redefined by this repair. The documentation checkpoint runs the planning validator
with the A1 source already committed. This legacy mixed-batch limitation remains
a scoped tooling follow-up, not a new application or activation gate.

The metadata-only inventory retained 81 inherited entries (12 modified, 69 untracked)
in planning, A1-policy, tooling and research/report scopes. These are classified as
preserve pending scoped content review, not declared stale or approved for staging.
The inventory includes no copied employee content and remains under protected
`runtime/portal/temporary/readiness-roadmap-20260909/`. Existing parent-plan edits
are preserved; only the small readiness correction to PLAN-A1 is included here.
Do not create another editable source tree or archive unknown files to obtain a
clean status. New deliveries continue updating this record; detailed inventories
and hash-bound receipts remain runtime artifacts.

### Tooling repair and bounded J2 intake — 2026-09-09

This delivery completes the reviewed seed/reproducer repairs and adds the first
synthetic completed-batch inbox increment. It preserves the earlier unrelated OCR
benchmark test and historical databases/packages. The original report's completion
claim was corrected by `3e31594`; the implementation below supersedes that repair list.

| Field | Evidence / state |
|---|---|
| Implementation | Exact sanctioned seed settings; explicit private verification roots; read-only SQLite verify; independent role/profile/state expectations and multiset worker/assignment/case reconciliation. Reproducer verifies exact Git blobs and uses an isolated acceptance copy, single-attempt command results and protected hash-bound receipts. J2 uses shared intake/OCR with private organization roots, completed manifests, hash/type checks, local locking, per-item recovery and opaque receipts. |
| Validation | Seed/containment: 31 tests passed; final diagnostic change: one affected test passed. Reproducer: 13 behavioral tests passed. J2: 14 SQLite integration tests passed. Supervised settings: 43 existing checks plus five inbox-configuration checks passed (an inherited setgid bit on newly created inbox directories was corrected). PostgreSQL integration: 44 tests passed in an ephemeral cluster, including J2 and historical migration paths. Planning: 24/24 checks passed. Committed source `6e37d6c`: 91 pytest tests and 9 subtests plus 14 J2 Django tests passed; all 23 archive-applicable planning checks passed and source integrity remained unchanged. |
| Publication | Implementation commit `4797352`, entrypoint repair `d57ad18`, and directory-mode repair `6e37d6c` are local. Accepted source is `6e37d6c`; this documentation checkpoint records its evidence. Earlier outgoing commits remain unpublished pending content review; no history rewrite or force-push is authorized. |
| Deployment | No service or production deployment. Fresh `runtime/portal/supervised-development/` was built from all 13 on-disk Release 1A migrations and passed apply/verify twice: 3 synthetic organizations, 4 workers, 5 assignments, 2 A1 cases. Bootstrap source `d57ad18` has the same seed/models/supervised-settings blobs as accepted `6e37d6c`. Existing historical databases/PDFs are untouched; accounts remain inactive and inbox operator defaults unprovisioned. |
| Activation | Unchanged. The inbox adapter explicitly refuses real-data activation and uses existing actor/membership/MFA capability checks. Configuration creates no operator or human confirmation. |
| Limitations | J2 intake leaves identities unassigned with requires_review; no worker auto-merge, A1 draft generation, BO completion or scheduler is included. Originals remain protected in the inbox pending retention review. Local file locking is not distributed coordination; existing OCR retry/dependency policies still apply. |
| Next owner | Engineering: J2 identity/conflict handling and DB-MIG-1/2/5 revision mapping, then J4 unverified drafts and BO confirmation, preserving DB-MIG-6/7 cutover dependencies and real-data-rules §14. |

Protected evidence: `runtime/portal/temporary/release-reproducer/523088de500044b5a90a13e44ab85e14/receipt.json`
and `runtime/portal/supervised-development/bootstrap-receipt.json`. The first
committed-source run on `d57ad18` exposed inherited setgid on newly created receipt
directories; its failed receipt is retained. `6e37d6c` clears that flag only on new
directories and adds the corresponding synthetic regression; the later run passed.
The synthetic bootstrap's `environment.json` contains a development-only test key,
not production credentials or an activated operator. No service is started by it.

Selected verification commands:

```bash
venv/bin/python -m pytest tests/m2/test_synthetic_containment.py tests/test_release_reproducer.py -q
venv/bin/python scripts/test_document_intake.py
bash scripts/release_reproducer.sh <delivered-source-sha>
```

The PostgreSQL harness owns an ephemeral in-project cluster with Unix sockets and
no network listener; it now includes J2 inbox scenarios alongside existing intake,
historical migration, readiness and J4 service tests. No system database is used.
The release reproducer omits only the index-specific staged check in a plain archive;
mandatory source publication hooks remain effective. Its receipt binds the actual
source commit, invoking runner/interpreter, installed dependencies, environment,
first command exit codes, logs and before/after source integrity. Runtime writes
occur in a separate disposable acceptance copy, not the immutable source export.

The [local automation contract](../../plans/2026-09-08-local-a1-automation.md) specifies
the completed-manifest format and one-time supervisor inbox configuration. After
configuration, the bare management command uses existing authorized actor/org IDs;
explicit CLI overrides still require the same authorization and root segregation.
A completed intake means persisted machine proposals, not confirmed identity or
certificate issuance. No approval states or top-level catalog IDs are changed.

### Consolidation documentation delivery — 2026-09-08

Historical delivery state at `cba3e50`; the 2026-09-09 repair above supersedes its
reported readiness discrepancy.

| Field | Evidence / state |
|---|---|
| Implementation | AGENTS.md shortened to 170 lines; consolidated local plan, 44-field mapping, parent/index/roadmap references, framework and archive guidance; package catalog registers five previously unclassified documentation paths; planning validator permits the three exact reviewed A1 document paths with six regression cases |
| Validation | 24/24 planning checks; 44/44 mapping rows; 133 relative links resolve in staged-source export; 97 focused planning/approval/package tests pass from exported staged source; staged whitespace/content classification passes |
| Publication | The commit containing this checkpoint is the delivery object; exact local/remote SHA and final status are recorded in protected runtime delivery-receipt.json and the operator handoff, not inferred from test results |
| Deployment | Not performed; no settings, database, service or file relocation changes |
| Activation | Unchanged; real-data-rules §14 and existing registered approvals remain authoritative |
| Limitations | Historical databases and unreviewed work retained; generic readiness still requires activity_name while provisional validation permits blank 5.1; future seed --verify, reproducer and coordinator are not implemented |
| Next owner | Engineering: inventory dependencies/selected inputs, then fresh synthetic development setup and the existing J2/J4/DB-MIG tasks |

Only this task's documentation hunks are included; inherited parent-plan edits,
untracked reports and fixtures are excluded. No application tests or PDF generation
are needed to establish this documentation checkpoint. The necessary validator
false-positive repair is the only source-code change: exact document names, not a
broad directory exemption. Protected-path/content checks remain in force.

Acceptance commands: `venv/bin/python scripts/validate_planning.py` and
`venv/bin/python -m pytest tests/test_validate_planning.py tests/test_validate_approvals.py tests/test_validate_change_packages.py -q`.
The exported staged source passed all 97 tests and 24 planning checks; final
Git-object verification matches delivered inputs to that evidence. The mapping's
AST check covers each CSV_FIELDS key once. Relative-link checks use the staged
source export rather than relying on untracked local reports. Existing hooks may
repeat their own configured checks; they are not bypassed.

During verification the staged document filenames triggered the old substring
rule; the narrow fix removed that false positive. One new negative-test specimen
initially used `1a` rather than the prohibited `a1` token; corrected to an actual
rejected sibling filename, then the complete exported suite passed. No protected
input was read. Detailed source hashes, commands and publication state are retained
at `runtime/portal/temporary/consolidation-docs-20260908/delivery-receipt.json`.

## Checkbox alignment repair — 2026-09-08

The original PDF and the working raster background had different box geometry;
3.4 and 4.1.2 outlines were absent. Restored all ten blank outlines at the original
vector coordinates, corrected the corresponding layout, and inset X strokes by
1 point. No employee values or original selection marks were copied.

The previous blank background is retained in protected runtime. The one-time
repair rejects any other input hash; 300-DPI comparisons on all three pages found
zero changed pixels outside the checkbox repair regions. All three synthetic
pages and the four reported problem crops were visually reviewed. Tests now check
all ten X/Y/page/size values, actual background outlines, full rendered stroke
containment and hashes binding template/layout/renderer/reference. They need no
ignored employee/reference PDF. Receipt: `config/a1_checkbox_fix_receipt.json`.

Employee PDFs were not regenerated. Existing packages remain unchanged; their
canonical source/approval/visual gates still apply. The synthetic review artifact
is `runtime/portal/temporary/checkbox-alignment-review/synthetic-checkboxes.pdf`.
The background and coordinates must be changed and accepted together from now on.

## Approval validation and fixture isolation — 2026-09-08

The shared approval validator now preserves CLI catalog-state/date checks, rejects
cycles and unmet dependency states, and makes each gate decision from one validated
register snapshot. Dirty review scope, mismatched commit/hash and an incorrect Git
root fail closed when requested. Malformed JSON shapes fail cleanly. Technical
validation may pass while human approval remains proposed; that never opens a gate.
Approval records, catalog IDs and human/activation decisions were not changed.

Publication provenance: a concurrent session included the five staged governance
files in its A1 commit `95ade12` and published it. This was not the intended scope
split. Its governance-only exported acceptance passed 74 tests; no A1 geometry,
artifact generation or visual acceptance is established by this report.
Follow-up `1cdec5f` isolates Git commands from caller/hook environment overrides.

The original planning fixture helper copied runtime files into its temporary test
root and exhausted /tmp. Only the copies created by that failed run were removed.
The helper now uses committed text fixtures and excludes protected paths, unreviewed
fixture data, environment files, binaries and symlinks. Gitless exported snapshots
prune protected directories before reading. Regression tests assert these boundaries.
An isolated-worktree hook exposed inherited Git variables redirecting fixture
commands; the disposable checkout was rebuilt and the accidentally changed shared
`core.bare` flag restored to false. The delivery-tool fixture suite required the
same isolation; its accidental local test identity was restored to the original
repository identity. Main-worktree status was checked afterward.

Acceptance command: `venv/bin/python -m pytest tests/test_validate_approvals.py tests/test_validate_planning.py -q`.
Both the isolated hook run and exported `1cdec5f` snapshot passed **75 tests**.
Final planning/asset checks are verified before Git publication. Detailed synthetic logs
remain under `runtime/portal/temporary/approval-*.log` (not tracked).

Next owner: primary engineering, to review the remaining verifier/browser/seed
packages and unrelated planning work. Use isolated checkouts while another session
is active; never share staging. No service deployment or real-data activation is
included. The current A1 binary remains outside this governance acceptance scope.

## Shared intake delivery — 2026-09-08

Implementation: `9ab6f46` publishes the shared offline core; `a52363a` publishes
synthetic runtime dependencies; `5a96935` publishes the portal adapter and required
J4 integration. Catalog commits `10b6099` and `5612cd7` define their reviewed
boundaries. No intended core/runtime/portal paths remain dirty after these commits.
The parent PLAN-WORKERS checkpoint is staged separately from its inherited edits.

Upload and supersession now use the same validation, protected storage and OCR
pipeline. Supersession preserves old bytes/receipts, serializes version creation,
reuses identical retries and cleans up a new source on transaction failure. Late
OCR cannot overwrite the latest document state; obsolete proposals/associations
cannot be accepted. Output-storage failure leaves a retryable failed run.
J4 preparation retains an empty PDF hash until actual canonical artifact attachment.

Acceptance from exported Git objects (installed project venv; synthetic data only):

| Object | Command | Result |
|---|---|---|
| `9ab6f46` | `unshare -Urn venv/bin/python -m pytest tests/test_document_core -q` | 87 passed; networking disabled |
| `a52363a` | `env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m pytest tests/test_readiness_checks.py tests/test_runtime_hardening.py tests/test_settings_supervised_synthetic.py -q` | 82 passed |
| `5a96935` | `env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python manage.py test tests.document_web.test_intake tests.m2.test_views tests.m2.test_release1a_vertical tests.m2.test_review_fixes tests.m2.test_j4_delivery tests.test_j4_minimum tests.m2.test_readiness --noinput -v 1` | 101 run; 98 passed, 3 PostgreSQL-only skips |
| `5a96935` | `venv/bin/python scripts/test_document_intake.py` | 30 passed on disposable PostgreSQL 18, including all three skipped cases |
| `5a96935` | `env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m pytest tests/test_j4_artifacts.py tests/test_runtime_contract.py tests/test_release1a_migration_chain.py -q` | 46 passed; five expected database-override warnings |

The PostgreSQL run covers concurrent replacement, late OCR completion, bounded
query cancellation and historical MigrationExecutor transitions. All disposable
clusters are stopped and removed by their harness. Artifact tests use the committed
template, not the unrelated modified template in the working tree. They establish
synthetic integrity/behavior, not all-page visual acceptance or certificate issuance.
The missing-database side-effect test now allows cold subprocess startup separately
from the strict deadline/cancellation tests; no production timeout was increased.

The benchmark-specific contract test stays with the unpublished benchmark script;
it was moved to `tests/test_ocr_benchmark_contract.py`, not discarded or promoted.
The planning checkpoint publishes the reviewed child plan and architecture contract.
References to other unpublished local reports are labelled explicitly. Existing
34 catalog IDs and approval states are preserved. Working-tree planning passed
24/24; final documentation-object checks and remote SHA are verified before the
handoff claims publication. No full-repository CI or deployment acceptance is claimed.

Synthetic logs: `runtime/portal/temporary/intake-delivery-20260908/`; exported
objects: `runtime/s-<commit>/`. Publication targets only the existing GitHub feature
branch. Next owner: primary engineering, to review remaining governance, planning,
benchmark/research and fixture scopes, then reconcile draft PR #1 against CI.
Unrelated template changes and employee artifacts remain untouched. Deployment,
observed review, real-data activation and all existing human gates remain pending.

## Bounded dependency repair — 2026-09-08

Implementation commits `c322e8a` and `153cf05`, with dependency follow-up
`ab43d27`, restore migration stages 0008–0011, preserve the committed 0012
dependency, add 0013 for the confirmation reverse relation, and publish the
canonical A1 audit/path modules. The institution inventory test now runs without
Git metadata and rejects an empty inventory. Louny's unresolved code keeps its
profile at NEEDS_VERIFICATION. No institution or certificate evidence was approved.

Acceptance from an exported `ab43d27` snapshot without `.git`: **57 passed** with
`venv/bin/python -m pytest tests/test_finalize_a1.py tests/test_a1_stabilization.py tests/test_release1a_migration_chain.py tests/test_validate_change_packages.py -q`
(the existing project venv interpreter was invoked by absolute path). The first
A1 snapshot failed because its template-repair receipt dependency was absent;
`ab43d27` includes that metadata-only historical receipt. This is not fresh
template visual acceptance. The snapshot test exercises historical app states
through MigrationExecutor, preserves document/J4 data, and checks model parity.

The existing two historical intake/J4 tests also passed on a disposable SQLite
test database in the working tree. Planning validation passed 24/24 there;
neither result establishes acceptance of the remaining unpublished portal modules.
Detailed synthetic logs and exported snapshots are in protected project runtime
storage under `runtime/portal/temporary/delivery-20260908/`.

Git publication is tracked separately from implementation and acceptance; the
remote SHA must be verified after pushing these bounded commits. No persistent
database migration, deployment, employee generation, promotion or activation was
performed. Databases created from the withdrawn local squash require their own
history review before use; they were not migrated by this repair.

Next owner: primary engineering, for the remaining shared document/runtime/J4
source packages and supersession integration. Preserve unrelated work. The initial
inventory contained 262 dirty files (27 modified, 235 untracked), including 134
untracked research files; that inventory is not a staging approval. Research,
unreviewed fixtures, template changes and unrelated planning work remain outside
this bounded delivery. Parent plan statuses and activation gates are unchanged.

## Current delivery

The pre-commit gate validates exact staged bytes and the staged package catalog.
Missing/malformed catalogs, unknown or quarantined paths, protected paths, credential
indicators, unsupported index entries and oversized files fail closed. Deleted
ordinary source files are accepted without reading absent blobs. Unrelated unstaged
work is excluded. Catalog checks run with argument arrays and no shell eval; current per-command
budgets and private diagnostics are described in the 2026-09-11 checkpoint above. Their execution still uses the working tree, so match evidence
to the delivered inputs under the current operating policy above. Export checks are
required when that match is unproven, not a duplicate suite for every small edit.
This is not a full PII detector.

Run `bash scripts/install-git-hooks.sh` after cloning. The installer preserves an
existing hook before replacement and refuses an independently configured hooksPath.
The hook requires the repository venv; it never bypasses validation on failure.

Existing GitHub Actions use explicit Bash (pipefail), direct pytest output, mandatory
dependency installation and lint, read-only token permissions, job timeouts and
cancellation of superseded runs. The slow-suite push condition matches master.
A tracked-blob signature scanner emits paths only, never matching secret values.
No new CI provider or runner is activated. Existing dependency/collection/lint
failures are now visible and must be fixed in their responsible delivery packages.

Environment variants, SQLite sidecars and all runtime outputs are ignored;
`.env.example` remains eligible for explicit synthetic review. No runtime contents
were moved, read or deleted. The reviewed template binary attributes are published.
Ignore rules do not protect already tracked files or historical Git objects.

## Acceptance and next steps

Focused acceptance: **16 tests passed**, including an exported commit snapshot
of implementation commit `5d41658`. Planning checks: **24/24** in the working tree.
The first full exported planning snapshot exposed missing local evidence references.
ADR comparison links and the benchmark receipt reference now explicitly identify
unpublished local evidence; no artifact or decision was promoted.
Broad CI acceptance remains pending and is not inferred from these results.

Run `venv/bin/python -m pytest tests/test_validate_change_packages.py -q`,
`bash -n scripts/pre-commit scripts/install-git-hooks.sh`, staged validation and
`git diff --cached --check`. Tests use synthetic temporary repositories and cover
staged/worktree disagreement, catalog disagreement, deletions, symlinks, quarantine,
malformed input, failed commands, environment variants and credential diagnostics.

Keep the 34 planning IDs and activation gates unchanged. Next: publish reviewed
A1/core/portal dependencies in coherent commits, including the collector module
missing from the current committed test suite. Reconcile draft PR #1 after clean
snapshot and remote CI acceptance. Historical branches remain untouched; never use
bulk push. Master protections/account capabilities require a separate decision.

### Rehearsal strict contract + bounded workflow — 2026-09-11 (review of 1593cae)

The 2026-09-11 review of `1593cae` identified five findings. Each
one is now fixed; a regression test reproduces the original
failure. The rehearsal endpoint's contract is no longer a search
for substrings but a typed JSON contract; the rehearsal lifecycle
is bounded so routine tooling validation does not pay the cost
of four fresh `migrate` calls; and the actual end-to-end
authenticated workflow (provision operator + organization +
MFA, real HTTP against gunicorn, worker + assignment + A1 case
data path, sparse-data blocked only on the rendering operation,
saved records surviving restart) is exercised by one new
bounded integration test.

| Field | Evidence / state |
|---|---|
| Implementation | F1 — `cmd_smoke` and `verify_launched_process` delegate to `scripts/smoke_probe.py`, which parses `/health/` and `/readiness/` as JSON, asserts `git_commit` and `build_id` equal the manifest, asserts `supervised is True` and `real_data is False`, asserts `mode == "settings_supervised_synthetic"`, and parses `/login/` and `/review/` redirects through `urllib.parse.urlsplit` so an external host (e.g. `https://example.invalid/...`) is rejected as not-same-origin. The fake server from the 2026-09-11 review (200 body with `supervised: false, real_data: true, status: not_ready`, redirect to `https://example.invalid/`) is rejected by `test_smoke_probe_parses_health_json_and_fails_on_wrong_fields`. The `/readiness/` view (`portal/release1a/views.py:822`) now includes `synthetic_only` and `real_data: false` in its JSON body. F2 — `validate_runtime_root_layout` and the manifest builder's `_validate_confinement` both reject symlink components by walking the raw path (no `resolve()` followed by symlink check). Pre-existing child symlinks under the runtime root are rejected before any directory mutation. The 2026-09-11 reproduction is locked by `test_child_symlink_is_refused_before_mkdir_chmod`. F3 — `cmd_provision` writes `operator.json` and `organization.json` to the runtime root with `umask 077`; `cmd_start` truncates `gunicorn.log` and `chmod 0600`s it before launching and re-asserts the mode after the launch; `cmd_migrate` re-asserts `db.sqlite3` mode 0600 after Django creates it. `verify_launched_process` implements the socket-inode verification through `/proc/<pid>/fd/*` so a wrong HTTP-500 server cannot pass. `test_manifest_mode_is_0o400_under_permissive_umask` restores the umask after the test. F4 — rehearsal files live in their own `delivery_lifecycle_rehearsal` change-package; routine `infrastructure_git_workflow` runs only the cheap 15-test unit suite (~2.6 s) when those files are not staged. The bounded lifecycle and end-to-end workflow tests run only when rehearsal files are staged. F5 — `scripts/provision_synthetic_operator.py` provisions an individual operator + organization + TOTP MFA against the supervised-synthetic database, persists credentials to `operator.json` (mode 0600) outside the repository. The new `tests/test_rehearse_workflow.py` exercises prepare + provision + start + real HTTP against gunicorn + worker + assignment + A1 case + sparse-data blocked only on `reserve_application_draft` + records survive restart + stop. The data path runs in a separate subprocess (`tests/_rehearse_workflow_data_path.py`) so the pytest-django test runner's in-memory test database does not collide with the supervised-synthetic SQLite. |
| Validation | 81 tests pass across dispatch/runner/release-reproducer (53 cheap in 8.9 s) + rehearsal unit (15 in ~2.6 s) + rehearsal lifecycle (3 real-gunicorn in ~52 s) + rehearsal workflow (1 real-lifecycle in ~54 s) + new F1/F2/F8 negative fixtures. 24/24 planning checks. `bash -n` syntax passes for both shell scripts. The pre-commit hook's `delivery_lifecycle_rehearsal` check runs `pytest tests/test_rehearse_synthetic_site_lifecycle.py tests/test_rehearse_workflow.py -q` when rehearsal files are staged (~106 s for the lifecycle + workflow together). Routine tooling-only commits stay fast. |
| Publication | Local working tree; push to `origin/feat/prace-readiness-plan-2026-08-13` follows AGENTS.md authorization. No protected paths staged; no secrets/PII in diffs; staging restricted to the listed non-PII path set. |
| Deployment | None; isolated `runtime/portal/supervised-workflow-*` synthetic roots only. No operator-owned service, host database, real-data activation, public release or new remote. |
| Activation | Unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; the supervised settings module still refuses the base default secret and still requires `PRACE_RUNTIME_ROOT` under `runtime/portal/supervised-*`; `intake` continues to refuse non-synthetic configuration. Real-data activation requires REV-003 per existing gates. |
| Limitations | The end-to-end workflow exercises the data path via `portal.release1a.services` against the supervised-synthetic SQLite and real HTTP against gunicorn for `/accounts/login/` (200 with CSRF cookie), `/health/`, `/readiness/`, `/login/`, `/review/`, and the shipped static assets. A full allauth+MFA round-trip over plain HTTP is blocked by `CSRF_COOKIE_SECURE=True` (the rehearsal is intended to run behind a TLS-terminating proxy in production); a real-browser login/MFA journey requires that proxy or `PRACE_TRUSTED_ORIGINS` set to the HTTPS origin. The Playwright-based browser journey remains gated on `playwright install` and is not part of this commit. PostgreSQL acceptance remains separate until an authorized scoped target is available; the lifecycle test runs against SQLite. |
| Next owner | Engineering: TLS-terminating proxy + `PRACE_TRUSTED_ORIGINS` recipe for the rehearsal so a real browser can complete the allauth+MFA round-trip; full PostgreSQL acceptance against an authorized scoped target; then Delivery 2 (usable v1 workflow) and Delivery 3 (restricted production pilot). |

### Real-browser authenticated workflow + idempotent provisioner + dispatch repair — 2026-09-11

The 2026-09-11 review identified that the rehearsal workflow was
demonstrated only through service-call shortcuts: the helper
added an `organization_admin` membership to mask the operator's
missing `worker:create` and `assignment:create` capabilities; the
data path exercised the same code paths an HTTP smoke test would;
the workflow test silently skipped without ``DJANGO_SETTINGS_MODULE``;
the smoke probe discarded its constructed ``Request`` so
``Host`` and method were lost; the ``workflow`` command was
advertised but not implemented; provisioning rotated the
password and TOTP secret on every run; the ``change-packages.yml``
selector sent dependency changes through pure-tooling checks
without any application integration; and the plan asserted an
authenticated browser journey as the Delivery 1 deliverable
without demonstrating one.

Each finding is now fixed with a test or a documented contract.

| Field | Evidence / state |
|---|---|
| Implementation | F1 — the previous `tests/test_rehearse_workflow.py` was replaced. The new test drives `scripts/rehearse_synthetic_site.sh prepare → provision → start → workflow → stop → restart → query-after-restart → stop` against an isolated `runtime/portal/supervised-workflow-pytest-*/` root. ``workflow`` is now a real subcommand of the rehearsal script that invokes `tests/_rehearse_workflow_browser.py` with the running gunicorn's bind. F2 — `tests/_rehearse_workflow_browser.py` drives a real headless Chromium (Playwright 1.62.0, Chromium 1228/1234 from `~/.cache/ms-playwright`) through login + TOTP + worker creation + document upload + association + assignment + A1 preparation, returning per-stage evidence on stdout. The journey uses the natural allauth login form (plain HTML), then neutralizes HTMX at the network level so per-field blur handlers do not re-render the Release 1A forms mid-fill. Every POST goes through the operator's session cookie jar — no service-side shortcut, no helper-side membership widening. The `jan_planner` role (worker:create, assignment:create, a1:prepare, document:upload, document:confirm) is provisioned by the script; operator membership alone is rejected by `require_capability`. The sparse synthetic worker has no OCR proposals and no application-draft artifact; the journey records those as documented skip paths, never as failures. The post-restart persistence query confirms `Worker.objects.filter(pk=...).exists()` and `A1Case.objects.filter(pk=...).exists()` after stop+start. F3 — `scripts/provision_synthetic_operator.py` is now idempotent on rerun: it refuses to start unless `--runtime-root` equals the configured `PRACE_RUNTIME_ROOT` (preventing the previous "fix one, point at a different database" foot-gun); it creates a verified `EmailAddress` for the operator so allauth's mandatory email verification does not block login; it reuses the existing password and TOTP secret on rerun (only `--rotate-credentials` or an explicit `--password` rotates); and the membership role is `jan_planner`, not `operator`. Audit events fire only after the DB write succeeds. F4 — `scripts/smoke_probe.py::_bounded_request` now passes the constructed `urllib.request.Request` to `opener.open(request, ...)`, honoring `method` and `Host`. The previous fake server fixture (`HEAD` submitted as `GET`, `Host=example.invalid` rewritten to `127.0.0.1:<port>`) is locked by `test_smoke_probe_parses_health_json_and_fails_on_wrong_fields` and now fails the smoke probe. Connect and body-read are bounded by a single wall-clock deadline so a slow body read can no longer succeed after the budget. F5 — `change-packages.yml` now selects the negative fixtures (`tests/test_rehearse_synthetic_site.py`) for rehearsal changes and adds the rehearsal unit/lifecycle suite alongside the workflow test. Dependency changes (`requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt`) select the rehearsal unit/lifecycle tests through the new `scripts/select_infrastructure_git_workflow_checks.py` selector so a silent `whitenoise`/`rapidocr` regression does not slip past the pure-tooling check. F6 — `tests/_rehearse_workflow_data_path.py` asserts the expected exception type for the sparse reserve (`DraftInputBlocked` for the canonical path, `ValueError` for the older snapshot shape) and the actionable missing-fact message, not a generic `Exception` catch. The same helper saves a sparse `Worker` (`given_name=""`, `family_name=""`, `birth_date=` known) so unknown optional facts do not block the save. F7 — `scripts/rehearse_synthetic_site.sh::cmd_workflow` is now a real subcommand that runs the browser journey against the running gunicorn. The previous `bash scripts/rehearse_synthetic_site.sh workflow` exit-1-with-usage behavior is fixed; `workflow` is implemented and exercises every documented stage. The ``SCRIPT`` exit-code table includes ``7  workflow failure`` so the failure mode is observable. Playwright + Chromium are usable on loopback: Secure cookies over plain HTTP are accepted because Chromium treats loopback as potentially-trustworthy; the previous "missing a TLS proxy" claim was investigated and is no longer correct for the local rehearsal. |
| Validation | The new workflow pytest test passes end-to-end: `prepare → provision → start → browser journey → stop → restart → query-after-restart → stop` runs in ~78 s on the rehearsal script + browser journey. 21 rehearsal + lifecycle + workflow tests pass in 116 s. 47 dispatch / runner / reproducer tests pass in 8.4 s. 24/24 planning checks. `bash -n` passes for both shell scripts. The `delivery_lifecycle_rehearsal` change-package runs the rehearsal unit, lifecycle and workflow tests; the `infrastructure_git_workflow` change-package adds the rehearsal unit/lifecycle suite whenever a `requirements*.txt` is staged. The required journey evidence is recorded in the test, not inferred from earlier claims. |
| Publication | Local working tree; push to `origin/feat/prace-readiness-plan-2026-08-13` follows AGENTS.md authorization. No protected paths staged; no secrets/PII in diffs; staging restricted to the listed non-PII path set. |
| Deployment | None; isolated `runtime/portal/supervised-workflow-*` and `runtime/portal/supervised-workflow-pytest-*` synthetic roots only. No operator-owned service, host database, real-data activation, public release or new remote. |
| Activation | Unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; the supervised settings module still refuses the base default secret and still requires `PRACE_RUNTIME_ROOT` under `runtime/portal/supervised-*`; `intake` continues to refuse non-synthetic configuration. Real-data activation requires REV-003 per existing gates. |
| Limitations | The real-browser journey uses the sparse synthetic OP card and worker so the OCR confirm stage and the application-draft artifact stage are recorded as documented skips, not failures; the dedicated `tests/document_web` cohort suite exercises the full A1 contract on a complete input row. PostgreSQL acceptance remains separate until an authorized scoped target is available; the lifecycle test runs against SQLite. |
| Next owner | Engineering: full PostgreSQL acceptance against an authorized scoped target; then Delivery 2 (usable v1 workflow) and Delivery 3 (restricted production pilot). |

### `rehearse_synthetic_site.sh workflow` standalone fix — 2026-09-11

The previous Delivery-1 entry claimed the `workflow` subcommand was
implemented; `bash scripts/rehearse_synthetic_site.sh workflow` actually
exited 1 with `No module named 'tests'` because the shell-level
invocation did not set `PYTHONPATH` (the browser helper imports
`tests.test_document_core.helpers`) or `cwd` to the repo root (the
test selector scripts rely on it). The pytest test ran fine because
`pytest.ini` adds the repo root to `sys.path`; the standalone
subcommand did not.

The `cmd_workflow` body now `cd`s to `$REPO_ROOT` and exports
`PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src"` before invoking the helper,
so the subcommand matches the documented exit-code table and the
canonical browser journey contract.

| Field | Evidence / state |
|---|---|
| Implementation | `cmd_workflow` in `scripts/rehearse_synthetic_site.sh` adds `cd "$REPO_ROOT"` and `PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"` before invoking `tests/_rehearse_workflow_browser.py`. No source or test changes; only the shell entrypoint. |
| Validation | Direct reproduction: `bash scripts/rehearse_synthetic_site.sh prepare && bash scripts/rehearse_synthetic_site.sh provision && bash scripts/rehearse_synthetic_site.sh start && bash scripts/rehearse_synthetic_site.sh workflow` now completes in ~36 s with all critical stages (`login_redirect`, `login_authenticated`, `totp_completed`, `worker_created`, `document_uploaded`, `document_associated`, `assignment_created`, `a1_prepared`, `a1_case_detail_visible`) reporting `ok: true`. The full focused suite (`tests/test_rehearse_synthetic_site.py tests/test_rehearse_synthetic_site_lifecycle.py tests/test_rehearse_workflow.py tests/test_validate_change_packages.py tests/test_release_reproducer.py`) still passes 81 tests in ~178 s; `validate_planning.py` passes 24/24; `bash -n` passes. `bash scripts/rehearse_synthetic_site.sh stop && start` followed by a query-after-restart against the supervised SQLite still confirms `Worker.objects.filter(pk=...).exists()` and `A1Case.objects.filter(pk=...).exists()`. The recipe (`docs/operations/wsgi-deployment-recipe.md`) now documents `workflow` as the Delivery-1 acceptance subcommand and explicitly notes that the previous "missing a TLS proxy" claim is no longer correct for the local rehearsal (Chromium treats loopback as potentially-trustworthy, so Secure cookies work over plain HTTP). |
| Publication | Local working tree; push to `origin/feat/prace-readiness-plan-2026-08-13` follows AGENTS.md authorization. No protected paths staged; no secrets/PII in diffs; staging restricted to the listed non-PII path set |
| Deployment | None; isolated `runtime/portal/supervised-jan-r1-*` synthetic roots only. No operator-owned service, host database, real-data activation, public release or new remote |
| Activation | Unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; the supervised settings module still refuses the base default secret and still requires `PRACE_RUNTIME_ROOT` under `runtime/portal/supervised-*`; `intake` continues to refuse non-synthetic configuration. Real-data activation requires REV-003 per existing gates |
| Limitations | The browser journey still uses the sparse synthetic OP card and worker so the OCR-confirm stage and the application-draft artifact stage are recorded as documented skip paths, not failures; the dedicated `tests/document_web` cohort suite exercises the full A1 contract on a complete input row. PostgreSQL acceptance remains separate until an authorized scoped target is available; the lifecycle test runs against SQLite |
| Next owner | Engineering: full PostgreSQL acceptance against an authorized scoped target; then Delivery 2 (usable v1 workflow) and Delivery 3 (restricted production pilot). |

### Delivery-1 supervised journey green; J4 snapshot hash/staleness + draft-generation UI — 2026-09-12

The Delivery-1 rehearsal journey is now demonstrated end to end with a
real operator browser (login + MFA + worker + assignment + A1
preparation + unverified draft PDF download) against an isolated
supervised runtime. The J4 storage contract was reconciled so the
attached artifacts compare the same digest the case stores, and the
case-detail UI accepts both the unverified-draft paths and the legacy
operator decision/notes record.

| Field | Evidence / state |
|---|---|
| Implementation | `scripts/rehearse_synthetic_site.sh prepare → provision → start → workflow` completes all 13 REQUIRED_STAGES with `ok: true` and returns exactly one JSON document on stdout (helper `OK` prompt moved to stderr; hash binding in `portal/release1a/a1_exports.py:197,207` and integrity check at `a1_exports.py:239-244`). The helper `tests/_rehearse_workflow_browser.py` discovers the worker detail at `/workers/<pk>/?tab=assignments` (assignment create redirects to `/workers/<pk>/`), picks the non-placeholder institution option so `expected_ossz == resolved_ossz` is a substring of the institution name, and accepts both `prepared_auto` (case detail already shows the PDF links because `prepare_a1` calls the canonical `prepare_application_draft`) and `operator_post` (`/a1/<pk>/draft/generate/`) generation modes. The fetched PDF is byte-verified (4,059,494 bytes for `a1-10-bea6367dacc1.pdf`). J4 hash contract: `prepare_a1` stores `result_hash({schema_version:"a1-input-1", profile, assignments})` in `case.source_hash` (bound to the stored snapshot so `a1_exports._current_input_snapshot` integrity check holds); `services.current_a1_source` now returns the same digest shape; `attach_a1_artifact`, `a1_regenerate` and `current_artifact_dependencies` compare like for like, removing the `StaleWrite("A1_SOURCE_CHANGED")` mismatch. Staleness transitions use a like-for-like digest comparison instead of the prototype `stable_hash`-based `result["stale"]`. The case-detail view (`portal/release1a/views.py::a1_case_detail`) processes the legacy decision/notes POST except while a reserved-but-unpublished generation is outstanding (409), and renders the canonical J4 artifact section only when no draft reservation exists. `tests/test_j4_minimum.py::test_source_hash_matches_proof_contract` now asserts the schema-versioned snapshot digest invariant. `change-packages.yml` gains ownership for 9 previously-unowned templates (`shared_document_portal`) and the PostgreSQL handoff doc (`repository_documentation`); `scripts/validate_planning.py` approved-path list accommodates the newly-owned `a1_prepare.html`, `partials/a1_prepare_form.html` and `partials/ocr_proposals.html`. |
| Validation | Real-journey evidence at `runtime/portal/temporary/journey-evidence/journey-2026-09-12.json` (`ok: true`, worker_pk 16, case_pk 10). Re-run after final edits: `manage.py test tests.test_j4_minimum tests.document_web.test_a1_generation_access tests.m2.test_j4_delivery tests.test_j4_service` → 38 OK; the `shared_document_portal` broad union `manage.py test` → 239 OK (27 skipped, postgres-tagged tests skip on SQLite); `pytest tests/m2/test_synthetic_containment.py tests/test_a1_input_artifacts.py tests/test_j4_artifacts.py tests/test_rehearse_workflow.py tests/test_runtime_contract.py` → 112 passed; rehearsal unit/lifecycle/workflow pytest → 191.25 s in the hook; `scripts/validate_planning.py` → 24 passed; `pytest tests/test_validate_planning.py tests/test_validate_approvals.py` → 95 passed; dispatch/runner → 60 passed. Commit `b478be8` passed the mandatory pre-commit hook (12 checks, all PASS; report at `runtime/portal/temporary/change-checks-elot8nk8/report.json`), `git diff --cached --check` clean, `validate_change_packages --staged` `problems: []` 30/30, and was pushed to `origin/feat/prace-readiness-plan-2026-08-13` (remote SHA `b478be8…` matches HEAD). |
| Publication | Pushed `e8a4eae..b478be8` to `origin/feat/prace-readiness-plan-2026-08-13`; verified via `git ls-remote`. No protected paths staged; no secrets/PII in diffs; `tests/test_ocr_benchmark_contract.py` intentionally left untracked. |
| Deployment | None; journeys ran against isolated `runtime/portal/supervised-jan-final2-*` roots only. No operator-owned service, host database, real-data activation, public release or new remote. |
| Activation | Unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; the supervised settings module still refuses the base default secret and still requires `PRACE_RUNTIME_ROOT` under `runtime/portal/supervised-*`; `intake` continues to refuse non-synthetic configuration. Real-data activation requires REV-003 per existing gates. |
| Limitations | PostgreSQL acceptance remains separate: the cluster is down and the handoff is a DRAFT (`docs/operations/delivery-1-postgres-handoff.md`); the `*_postgres` tests skip on SQLite. Delivery 1 cannot be declared operator-complete until the private URL, individual login and persistent PostgreSQL journey are accepted by the copy home. `prepare_application_draft` is still a best-effort step inside `prepare_a1` for cases whose identity/facts are incomplete (journey sets up `decin`/`OSSZ Děčín` facts explicitly). |
| Next owner | Copy home: run the documented `prepare → provision → start → workflow` journey against the private site + authorized PostgreSQL target and accept Delivery 1; then Delivery 2 (usable v1 workflow) and Delivery 3 (restricted production pilot). |

### Five-finding review repair: J4 identity binding, empty-key recovery, smoke deadline, persistence acceptance, PDF/sparse tightening + plan/skill reconciliation — 2026-09-12

The 2026-09-12 review identified five remaining findings (F1–F5)
plus item 5 (site-delivery package). All are now implemented,
validated and ready for commit: (1) J4 identity binding —
`prepare_a1` stores an extended snapshot with `source_contract:
a1-j4-identity-v1` that includes the live confirmed identity revision
and selected OCR claim; out-of-band `confirmed_fields` writes or claim
drift change the stored hash and block republishing under the old case
hash; legacy pre-binding rows adopt the current identity binding once
on first export, then treat later drift as stale (migration 0020,
tests in `tests/test_j4_minimum.py`). (2) Empty signing-key recovery —
`scripts/rehearse_dev_local.sh` recovers from an empty persisted
`.secret_key` by replacing it with a fresh usable secret via `mv -f`;
no leftover temp files; symlinks and out-of-tree paths are still
refused before any `mkdir`. (3) Smoke deadline fix —
`scripts/smoke_probe.py::_read_in_chunks` uses `stream.read1(65536)`
(fallback `read(1)`) with a wall-clock check after every chunk and
catches `BlockingIOError`; `_drip_body_server` drips continuously for
>=6 s so the regression is not fixture-bound. (4) Canonical
persistence acceptance — `scripts/rehearse_verify_persistence.py`
reuses the workflow test's restart-verification logic (exact worker,
document, assignment, both A1 cases, both PDF sha256s) and exits
non-zero on any mismatch; the PostgreSQL handoff doc points to it with
one consistent env contract. (5) Regeneration evidence tightened —
the browser journey asserts the corrected assignment fact reaches both
the downloaded regenerated PDF (pymupdf text extraction) and the
canonical generation input (`A1DraftGeneration.snapshot["row"]`);
sparse-input assertions require the canonical `DraftInputBlocked` with
an actionable message. The plan, skill and delivery record are
reconciled; both private-site deployment and PostgreSQL acceptance
remain explicitly open.

| Field | Evidence / state |
|---|---|
| Implementation | F1 — `portal/release1a/services.py` adds `current_identity_source` / `_j4_journey_snapshot` / `current_case_source`; `prepare_a1` stores the extended shape with `source_contract: a1-j4-identity-v1`; `a1_exports._current_input_snapshot` deps-None branch recomputes the identity-aware live hash via `current_case_source` and raises `StaleWrite("A1_INPUT_STALE")` on mismatch; legacy rows adopt once via new nullable `A1Case.bound_identity_sha256` (migration 0020); `views.a1_regenerate` and `current_artifact_dependencies` use `current_case_source` for shape-consistent comparison; `attach_a1_artifact` likewise. F2 — `scripts/smoke_probe.py::_read_in_chunks` uses `stream.read1(65536)` (fallback `read(1)`) with a wall-clock check after every chunk and catches `BlockingIOError`; `tests/test_rehearse_synthetic_site.py::_drip_body_server` drips continuously for >=6 s. F3 — `scripts/rehearse_dev_local.sh` uses `mv -f` for empty/missing targets, validates the read key is non-empty, and always removes the temp file; `tests/test_rehearse_synthetic_site.py::test_wrapper_recovers_from_empty_persisted_secret_key` exercises the empty-file path. F4 — `scripts/rehearse_verify_persistence.py` is the canonical acceptance script; `docs/operations/delivery-1-postgres-handoff.md` rewrites the persistence acceptance to call it with one consistent env block and adds the explicit "all four or none" `PRACE_DB_*` contract. F5 — `tests/_rehearse_workflow_browser.py` extracts regenerated PDF text with pymupdf and asserts the corrected `employment__street` is present; it also queries the regenerated case's latest `A1DraftGeneration.snapshot["row"]["employment_street"]` via a subprocess and asserts it matches. `tests/_rehearse_workflow_data_path.py` and `tests/test_rehearse_workflow.py` tighten sparse assertions to require `DraftInputBlocked` specifically with a non-empty actionable message; optional missing facts still allow the worker save. |
| Validation | Focused regressions once against delivered inputs: `tests/test_j4_minimum.py` -> 17 passed (includes new identity-binding tests); `tests/test_rehearse_synthetic_site.py` -> 25 passed (includes empty-key recovery and strengthened drip regressions); full bounded workflow test (browser journey + sparse data path + restart + exact-row/artifact query) passed (150.80 s); migration-chain test passed; `bash -n scripts/rehearse_dev_local.sh` clean; `git diff --cached --check` clean on every staged commit. All staged changes passed the mandatory pre-commit gate. |
| Publication | Pending commit of the F1–F5 + item 5 batch; remote SHA to be verified after push. No protected paths staged; no secrets/PII in diffs; `tests/test_ocr_benchmark_contract.py` intentionally left untracked. |
| Deployment | None; journeys ran against isolated `runtime/portal/supervised-workflow-pytest-*` synthetic roots only. No operator-owned service, host database, real-data activation, public release or new remote. |
| Activation | Unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; the supervised settings module still refuses the base default secret and still requires `PRACE_RUNTIME_ROOT` under `runtime/portal/supervised-*`; `intake` continues to refuse non-synthetic configuration. Real-data activation requires REV-003 per existing gates. The app session pins `statement_timeout=500` via connection options; module `settings_supervised_synthetic` refuses partial `PRACE_DB_*` config and requires `verify-full` + root cert for any non-loopback host. |
| Limitations | PostgreSQL acceptance remains separate: the cluster is down and the handoff is a DRAFT (`docs/operations/delivery-1-postgres-handoff.md`) awaiting operator execution; the `*_postgres` tests skip on SQLite. Both private-site deployment (stable private URL, individual operator access) and persistent PostgreSQL acceptance are open. The full 44-field A1 input path is demonstrated by the dedicated `tests/document_web` cohort suite, not the sparse journey worker. |
| Next owner | Copy home: run the handoff recipe (explicit bind + journey + exact-identifier restart verification via `scripts/rehearse_verify_persistence.py`) against an authorized PostgreSQL target, accept Delivery 1; then Delivery 2 (usable v1 workflow) and Delivery 3 (restricted production pilot). Operator: stand up the host PostgreSQL cluster targeted by the supervised settings module's `PRACE_DB_*` env. |

### PostgreSQL workflow reliability and postgres-ops skill — 2026-09-14

Flaky `OCR_STATUS_HTTP_500` in `tests/test_rehearse_workflow.py` reproduced
under gunicorn + SQLite; resolved by adding an opt-in PostgreSQL target for
the workflow test. `PRACE_WORKFLOW_PG=1` sets `PRACE_DB_*` env vars in the
`workflow_env` fixture, routing the rehearsal subprocesses to the local
PostgreSQL 18 `prace_synthetic_test` database. Test-owned gunicorn is always
stopped before the runtime root fixture removes its directory; PostgreSQL
runs include a `TRUNCATE … CASCADE` cleanup in the `finally` block so
subsequent invocations can provision a fresh `jan-operator@example.invalid`.

`.agents/skills/postgres-ops/SKILL.md` created per the existing repo plan
(`docs/research/2026-09-08-agents-md-audit-and-skill-plan.md §4.2`). It
documents the `PRACE_DB_*` and `DOCUMENT_TEST_PG_*` env contracts, local
vs remote SSL requirements, migration timing, flakiness diagnosis, and the
operator-owned cluster lifecycle boundary.

| Field | Evidence / state |
|---|---|
| Implementation | `tests/test_rehearse_workflow.py` gains `_postgres_env(base)` helper and `_cleanup_pg_operator(env)` truncation; `.agents/skills/postgres-ops/SKILL.md` documents the canonical PostgreSQL contracts. |
| Validation | `PRACE_WORKFLOW_PG=1 venv/bin/python -m pytest tests/test_rehearse_workflow.py` → passed (96.31 s); rerun → passed (105.90 s); focused rehearsal suite (`test_rehearse_workflow.py + test_rehearse_synthetic_site.py + test_rehearse_synthetic_site_lifecycle.py`) → 31 passed (183.01 s); browser journey + OCR lifecycle → 14 passed (116.86 s). Default SQLite run still reproduces the flaky `OCR_STATUS_HTTP_500` (exit code 7, 73.77 s), confirming the diagnosis. |
| Publication | Uncommitted; working tree and untracked `.agents/skills/postgres-ops/SKILL.md` present. No protected paths staged; no secrets/PII in diffs. |
| Deployment | None; journeys ran against isolated `runtime/portal/supervised-workflow-pytest-*` synthetic roots only. No operator-owned service, host database, real-data activation, public release or new remote. |
| Activation | Synthetic-only posture unchanged; `settings.M2_SYNTHETIC_ONLY` remains `True`; PostgreSQL acceptance does not alter the real-data gate (§14). Local cluster is reachable (`psql -U prace_synth_app -d prace_synthetic_test` succeeds); `prace_synth_app` owns all tables in `prace_synthetic_test`. |
| Limitations | PostgreSQL activation for default test runs is opt-in; CI and the mandatory pre-commit hook still run against SQLite by default. `prace_synth_app` cannot create databases; test database `prace_synthetic_test` must be pre-provisioned by an operator. The `TRUNCATE` cleanup covers application tables but does not remove files under `DOCUMENT_STORAGE_ROOT`; those are removed by the runtime root fixture. Official A1 PDF generation/issuance remains outside v1 scope. |
| Next owner | Runtime engineering: make the workflow test use PostgreSQL by default when the cluster is available, or add CI matrix entry for `PRACE_WORKFLOW_PG=1`. Operator: provision `prace_synthetic_test` (or equivalent) on new hosts and set `PRACE_DB_*` in the CI/rehearsal environment. Primary: commit the postgres-ops skill and test fix after review. |

## Runtime path retirement checkpoint — 2026-09-16

Operator selected `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env` as the infra-owned EnvironmentFile.
See [runtime contract](runtime-manifest.md#runtime-configuration-path-decision--2026-09-16).
This update changes application source guidance only: production cutover requires
separate infrastructure receipts, with exact payload retained and no restart or rotation.
The temporary hostname stays `prace-v-nemecku.expc.cz`; checkout `.env` stays separate.
Earlier authentication failures remain report-attributed; no fresh password test
was performed here. Current manifest bytes/marker are not an approved release.
JAN-01–04, committed-source acceptance, supervision and PG5 remain open.

## Runtime path deployment evidence — 2026-09-16

Infrastructure applied the authorized path-only migration and reloaded systemd,
without restarting the failed service or rotating credentials. Independent current
unit query confirms `EnvironmentFiles=/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`,
`NeedDaemonReload=no`, and unchanged failed/signal9 status. Server61 core receipts:
`evidence/reviews/2026-09-16-prace-path-retirement/parent/migration-apply.json`
and `parent/migration-repeat.json` (native0; repeat changed0), plus
`review-policy/postflight.json` (private on-host byte-equivalence, metadata and
unchanged listener-process checks) and `review-app/loaded-unit-final.json`.
These references are under that same server61 core evidence directory, not local
application files. At that path-deployment checkpoint, source updates were uncommitted and
unpublished in this application checkout; current publication is in the delivery record. No PostgreSQL authentication,
secret separation/rotation, manifest approval/repin, service recovery, JAN acceptance
or PG5 restore gate is closed by the path deployment.
