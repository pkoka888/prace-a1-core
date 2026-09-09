# Files and folders: inventory before reorganization

Parent: PLAN-INFRA / PLAN-HISTORY. This task is read-only except its report.

Allowed inventory: `scripts/`, `src/`, `portal/` excluding any runtime/instance DB,
`tests/`, `config/` excluding credentials, `plans/`, `planning/`, `docs/`, `.agents/skills/`,
`.opencode/skills/`, and root non-secret project manifests. Exclude node_modules,
venv, caches, generated test databases, all ignored/private paths, attachments and
backups. Unknown research trees are outside the allowed inventory; do not open
research/acquisition, research/pilot, research/processed or research/benchmark-experimental.
Never inventory private filenames for a remote model, even without content.

Write only `docs/research/opencode-organization-audit-2026-09-06.md` and an optional
sanitized `docs/research/opencode-organization-audit-2026-09-06.json`.

For each proposed change record current path, responsibility, active imports/URLs/
commands, plan owner, consumers, destination, reversible migration steps, tests,
link updates, and expected benefit. Distinguish:

- Canonical runtime sources, framework-independent core, adapters, tests and fixtures.
- Planned/historical documentation and generated catalog assets.
- Duplicate or apparently obsolete helpers, with evidence of actual callers.
- Untracked runtime dependencies needed for a complete future release.
- Candidate stale references to historical counts/statuses. Preserve dated findings;
  correct only statements claiming current state.

Recommendations must be small, dependency-driven moves. Do not reorganize for
cosmetic symmetry, invent a second top-level catalog entry for each child plan,
rename stable task IDs, archive active plans, or remove tests because they look old.
A missing __init__.py is not automatically a defect: check actual Python imports
and CLI execution. Do not run historical scripts to learn their purpose.

No deletes, renames, Git history edits, staging, commits or backup relocation.
The integrator converts accepted rows into explicit path-scoped implementation
work orders later. Private-data retention/incident containment belongs to the
primary/operator, not this inventory agent.
