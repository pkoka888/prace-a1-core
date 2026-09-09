# AGENTS.md — Práce v Německu

Private Czech/German A1 and recruitment-portal repository handling real PII.
Use existing Python core/services and keep routine engineering moving.

## Authority and task start

`AGENTS.md` → [real-data rules](docs/security/real-data-rules.md) →
[A1 skill](.agents/skills/a1-pdf-production/SKILL.md) → approved ADRs →
[roadmap](roadmap.md) → `prd.md` → [plan index](plans/INDEX.md).
Research is context, not execution authority. Explicit user scope takes precedence.
At task start read the roadmap, index and relevant plan/ADR/skill; inspect branch,
upstream and working-tree/staging changes. Reuse unchanged context during the task.

## Proceed, ask, and preserve

- Implement requested in-project fixes, code, tests and documentation autonomously.
  Choose the next bounded unblocked task; complete its relevant acceptance evidence.
  Review-only requests stay reviews. Do not silently activate a blocked environment.
- Engineering chooses engines, paths, retries and technical defaults. Jan supplies
  missing business facts and consolidated confirmation, not routine engineering approvals.
- Keep blockers local: missing deployment prerequisites do not block synthetic work;
  an unrelated failing check does not block a safe independent change. Record its
  affected scope and next owner. Never claim acceptance for a failing required check.
- Routine scoped commits and pushes to the existing private GitHub `origin` feature
  branch are authorized. Explicit task-specific no-commit/no-push limits override this.
- Ask only for missing authorization: deployment, new real-data portal activation,
  host changes, new remotes/CI, or other actions outside the authorized scope.
  Existing authorization persists; do not ask again for each edit or test.
- No force-push, Git history rewrite, branch deletion, protected/default-branch merge,
  public release or new-remote publication without separate exact authorization.
- Preserve inherited edits and staging. Never reset or stash another task's work.
  Use isolated checkouts where needed. Keep real-data operations out of source commits.

## PII, secrets and workspace

- Durable project workspace: `/var/www/prace-v-nemecku.tvoje.info` only.
  Host services, system databases, networking, certificates and off-server backups
  are sysadmin-owned. Host reads are permitted for necessary diagnostics.
- Never commit, force-add or copy outside the repo (including `/tmp`): `a1/`,
  `scans/`, `evidence/`, `ocr/`, `data/`, `employees/scans/`, `output/`,
  `runtime/portal/`, `secrets/`, `.env`, or `.history-remediation/`.
  Gitignore is not access control. `/tmp` is disposable non-PII only.
- Tests, fixtures, docs, screenshots and model prompts use synthetic data. Never
  disguise an actual employee record by lightly changing names or identifiers.
- Real-data access is default-deny by organization, record, role and action.
  Audit sensitive actions with opaque references and outcomes, never source values.
  Reuse `portal/release1a/models.py::AuditEvent` and `scripts/a1_audit.py` in their
  respective paths; do not invent a second audit schema in instructions.
- Private storage defaults: directories `0700`, files `0600`; the documented
  dedicated-group alternative is `0750`/`0640`. No public sensitive-file URLs.
- OCR is a proposal. Never silently overwrite confirmed facts or mark machine work
  as human confirmation. Record the confirming actor, time and exact source revision.
- Apply the existing 90-day retention-review default and documented holds/extensions.
  Keep working PDF packages; archive only individually classified obsolete material.
  `.archive/` is for non-sensitive history; private retained artifacts remain under
  `runtime/portal/temporary/retained/<uuid>/`, with provenance and retention review.
- [Real-data rules §14](docs/security/real-data-rules.md#14-real-data-activation-gate)
  is the portal activation gate. Existing authorized operator-only A1 work may
  continue; production gates do not block synthetic implementation.

## Parallel work and ownership

- The primary agent may delegate bounded non-PII research, implementation, tests or
  review in named source/documentation directories with explicit file ownership.
  Exclude secrets, protected data and unreviewed fixtures/reports; no whole-repo grants.
- Directory scope is an instruction, not a sandbox. Never pass scans, employee data
  or credentials to subagents. Only the primary integrates, accesses authorized real
  data and publishes Git changes. Use isolation when actual access containment is needed.
- Parallelize independent reads/tests. Avoid concurrent edits to the same files;
  use isolated test databases for migrations, schema changes, transactions or cleanup.

## Validation proportional to the change

| Change | Required evidence |
|---|---|
| Documentation | Relevant links/status consistency, whitespace, staged-content review |
| Ordinary code | Focused regression checks once against the delivered inputs |
| Migrations, storage, authorization, shared rendering, dependencies | Relevant integration checks |
| Release candidate | One reproducible committed-source acceptance run |
| Generated A1 package | Artifact-specific deterministic checks and local all-page visual review |

- Reuse evidence only when tested source, dependencies and configuration match.
  Changed inputs or failures require affected checks again, not every unrelated suite.
- Migration transition tests use Django historical states through `MigrationExecutor`;
  never simulate history by manually dropping/recreating columns.
- Verify delivered Git objects and scoped completeness. `git diff-tree HEAD` proves
  contents, not runtime behavior. Test a committed-source export for integration/release
  acceptance; do not mandate both working-tree and export runs for each small change.
- Existing mandatory hooks remain effective until deliberately updated. Never bypass
  them. Keep check failures and structural acceptance distinct from runtime acceptance.
- Avoid tests that merely mirror trivial edits. Record genuine limitations explicitly.

## Git delivery and planning checkpoint

1. Review an explicit non-PII path list; never `git add -A`, `git add .` or wildcard-stage.
   Inspect the full staged diff for secrets, PII, unknown artifacts and unintended edits.
2. Deliver coherent batches: code, required migrations, tests and supporting docs may
   share a commit. Keep unrelated work separate; do not publish missing dependencies.
3. Run relevant checks and `git diff --cached --check`; use existing hooks/catalog tools.
   Match test evidence to delivered bytes. Preserve unrelated unstaged changes.
4. Commit, inspect the resulting object and check scoped completeness. Inspect all
   outgoing commits before pushing with an explicit `origin` feature-branch refspec.
   Verify remote SHA before claiming publication. Never force on divergence/auth failure.
5. Update [one delivery record](docs/operations/git-delivery.md): implementation,
   validation, publication, deployment, activation, limitations and next owner.
   Keep detailed receipts/logs in protected runtime, not repeated Git reports.

Update parent/child plans and roadmap at meaningful checkpoints, not every edit.
Preserve task IDs and the 34 top-level catalog entries; regenerate derived assets
only when their sources change. Publication is not deployment or activation.
GitLab/CI proposals remain governed by [existing setup rules](docs/operations/gitlab-integration.md).

## Environment and canonical A1 path

Python 3.13; pinned dependencies in `requirements.txt`; setup once:
```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```
Run focused tests with `venv/bin/python -m pytest <relevant-paths> -q`.
Shell scripts invoking Python define `PYTHON_BIN` or `PYTEST` at their top:
```bash
PYTHON_BIN="$(cd "$(dirname "$0")/.." && pwd)/venv/bin/python"
```
Use that interpreter consistently; JSON-only parsing without Django is the exception.
For A1 work set `A1_PRIVATE_DIR` to the repository root; unset must fail closed:
```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
```

- Use the [A1 production skill](.agents/skills/a1-pdf-production/SKILL.md).
  Canonical commands: `scripts/generate_provisional_a1.py` (atomic publisher),
  `scripts/finalize_a1.py` (input/readiness contract), `scripts/a1_core.py`
  (policy/renderer), `scripts/a1_quality_gate.py` (render/validate/record-review).
  Inspect `--help` before operational use; do not create alternate generators.
- Synthetic DB drafts use `manage.py a1_prepare_draft` through the same publisher/core
  and protected J4 packages; explicit unverified mode never sets human review flags.
- Baseline inputs are `$A1_PRIVATE_DIR/a1/review.csv` and `a1/cohort.json`.
  Reconcile explicitly selected scoped snapshots before use; record hashes and
  cohort identity. Never choose authority by modification time or output counts.
  `config/a1_provisional.json` contains policy, never identities or cohort authority.
- Keep both [A1 frameworks](docs/architecture/A1_FRAMEWORKS.md). Coordinate overlay
  serves the current template; placeholder rendering remains the vector-template
  alternative. Use `generate_a1_pdf()` and `build_form_data()` on the canonical path.
  Dates, provisional numbers, casing, flattening and validation belong in `a1_core.py`.
- Preserve Section 5 policy: self-employed multi-state provisional 5.1 defaults blank;
  5.2 defaults `DE, CZ`, retaining explicitly reviewed row-specific territory overrides.
- Use `templates/a1_background.pdf` and `config/a1_layout.json`; never legacy
  `data/a1_forms/`, `a1_field_coords.json`, `a1_checkbox_coords.json` or ad-hoc templates.
  Generate data-first; never copy values from one generated employee PDF into another.
- Keep provisional artifacts in `output/provisional/`. Final promotion remains separate:
  authoritative certificate/signatory evidence, `validated_by_user=1` and receipt-bound
  artifact approval are required. Generated numbers/dates never imply official issuance.
- Current evidence lives in PLAN-A1 and the delivery record, not hardcoded cohort counts
  here. Renderer internals live in source and the [pipeline guide](docs/architecture/readme-a1-forms.md).

## Providers, skills and conventions

- Prefer deterministic/local processing. Only verified-free endpoints are authorized;
  OpenRouter IDs must end exactly `:free`. Existing keys never authorize paid use.
  No billing, paid trials or paid fallback; on quota exhaustion use verified-free or defer.
- External models receive at most an authorized minimal redacted crop when local
  processing is insufficient, never full scans/forms/datasets or secrets. Record
  provider/model/purpose/date. External visual results are advisory, not A1 acceptance.
- Keep reusable procedures in existing skills and logic in canonical scripts/services.
  New skills, MCPs and client hooks are optional improvements, not delivery prerequisites.
- `.opencode/skills/market-research-evidence/` remains experimental under Plan AC;
  operational use still needs both pilots' evidence, review, safety and reproducibility.
- New scripts use the most specific existing prefix: `a1_*`, `validate_*`, `run_*`,
  `seed_*`, `research_*`; shared OCR belongs in `src/document_core/`, portal adapters
  in `portal/release1a/`. Existing `release1a_*` helpers are legacy adapters.
