# Git delivery safeguards — 2026-09-07

Parent: PLAN-INFRA. Scope: existing GitHub CI and local Git tooling only.
No deployment, new runner/remote, history rewrite or real-data processing.

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
five-minute timeout. Their execution still uses the working tree: final acceptance
must also run from the exported commit snapshot. This is not a full PII detector.

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
