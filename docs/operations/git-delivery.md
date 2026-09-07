# Git delivery safeguards — 2026-09-07

Parent: PLAN-INFRA. Scope: existing GitHub CI and local Git tooling only.
No deployment, new runner/remote, history rewrite or real-data processing.

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
