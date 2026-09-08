# Git delivery safeguards — 2026-09-08

Parent: PLAN-INFRA. Scope: source-delivery policy and bounded delivery evidence.
No deployment, new runner/remote, history rewrite or real-data processing.

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

### Consolidation documentation delivery

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
work is excluded. Catalog checks run with argument arrays, no shell eval, and a
five-minute timeout. Their execution still uses the working tree, so match evidence
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
