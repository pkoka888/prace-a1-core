# Backup-first project separation — 2026-09-18

Status: directory map prepared; whole-project backup pending; archiving not started.
Parent: [PLAN-INFRA](PLAN-INFRA.md), existing REL-02–REL-06 ownership.
This is a child work breakdown, not a new top-level catalog entry.
Decision input: [comparison and selected solution](../docs/research/2026-09-18-project-separation.md).

## Working status report — 2026-10-20

This section is the current-task checkpoint for the plan above. It records what
is actually done, what is not done, and the problems that repeat across
unrelated tasks. It describes documentation and commit preparation only; no
backup, restore, file move, publication, deployment or activation happened.

### Planned (this task)

1. Commit the child plan and its supporting evidence as one coherent
   governance package.
2. Commit the already staged `a1form_generator` validator/documentation
   increment separately, without mixing it into the governance package.
3. Re-run `tests/test_validate_planning.py` against the updated `HEAD` export.

### Done

- The plan was read together with its linked evidence, the planning
  validator, the change-package catalog and the pre-commit hook. No secrets,
  credentials, employee records or protected paths were found in the plan or
  in the five supporting documents.
- The plan is a child breakdown of PLAN-INFRA and adds no new top-level
  `planning/catalog.json` entry. The 34 required catalog IDs are unchanged.
- Package ownership was determined per file. `plans/2026-09-18-backup-and-project-separation.md`
  is owned by `governance_truth` through the `plans/2026-` prefix.
  `docs/operations/git-delivery.md` is owned by `infrastructure_git_workflow`.
- The working-tree planning validator passes 24/24 checks
  (`venv/bin/python scripts/validate_planning.py`, exit 0).
- The exact broken-link set in `HEAD` was measured, not guessed: 21 distinct
  relative Markdown links in committed files resolve to targets absent from
  `HEAD`. Six of them belong to this task's plan and evidence set:
  `plans/2026-09-18-backup-and-project-separation.md` (linked from
  `plans/INDEX.md`, `plans/PLAN-INFRA.md`, `roadmap.md`,
  `docs/operations/git-delivery.md`),
  `docs/research/2026-09-18-project-separation.md` and
  `docs/research/2026-09-18-git-extraction-evidence.md` (both linked from
  `docs/operations/git-delivery.md`).
- The cause of those broken links is identified: commit `ffe903b`
  ("docs: record backup-first separation and working checkpoint status",
  2026-09-19) added the index, PLAN-INFRA, roadmap and delivery-record
  references but did not add the plan file itself. `git log -S` shows `ffe903b`
  is the only commit that ever introduced the reference.

### Not done

- The governance package is **not yet staged or committed**. `HEAD` still has
  the broken links listed above.
- The `a1form_generator` increment is still staged and uncommitted; its
  `change-packages.yml` entry and `protected_path_exceptions` addition are
  part of that pending increment.
- The isolated-restore checkpoint, the exact per-file manifest, the archive
  batch move and the product demonstration are all still open, exactly as the
  phases above describe. Nothing in this report closes any of them.
- No publication to `origin`, no deployment, no portal activation, no backup
  and no restore were performed. `/tmp` had been reported full earlier in the
  session; at report time it measured 7.9 GB free, so the
  `TMPDIR=/var/tmp/cline-scratch` workaround was no longer required, but the
  scratch path remains in use for test output.

### Recurring problems and how they repeat

These are not specific to this plan. Each one has already forced rework in
unrelated tasks and will do so again unless the ownership rule changes.

| # | Problem | How it repeats | Recurrence evidence | Owner |
|---|---|---|---|---|
| R1 | Documentation is referenced from a committed index before the referenced file is committed | Any new plan, research note or evidence file is linked from `plans/INDEX.md`, `plans/PLAN-INFRA.md`, `roadmap.md` or the delivery record in one commit, while the target file stays untracked. The next `HEAD` export fails the Markdown relative-link check and the failure surfaces far from the change that caused it | `ffe903b` added four referencing files without the plan; `HEAD` now carries 21 broken relative links. `tests/test_validate_planning.py::test_valid_full_catalog_passes` fails with exactly `[FAIL] Markdown relative-link validation — INDEX.md / PLAN-INFRA.md / roadmap.md` | engineering |
| R2 | A new document has no owning change package | `change-packages.yml` lists individual `docs/research/*.md` paths and one `plans/2026-` prefix. Any new file in `docs/research/` or `docs/architecture/` matches neither, so it cannot be staged coherently and the package selector rejects the commit | The four evidence files `docs/research/2026-09-18-project-separation.md`, `docs/research/2026-09-18-git-extraction-evidence.md`, `docs/research/2026-09-18-comprehensive-gap-analysis.md`, `docs/research/2026-09-18-gap-analysis-evidence.json` and `docs/architecture/project-directory-map.md` currently match **no** package | engineering |
| R3 | The package catalog and the staged-path allow-list are two separate registries that drift | `scripts/validate_planning.py` keeps its own `APPROVED_STAGED_*` sets while `change-packages.yml` keeps package paths. A path allowed by one is not automatically allowed by the other, so a file is repeatedly "approved" in one place and missing in the other | `scripts/validate_planning.py` lines 97–231 hold `APPROVED_STAGED_PATH_PREFIXES`, `APPROVED_STAGED_DOC_DIR_PREFIXES`, `APPROVED_STAGED_DOCUMENT_PATHS`, `APPROVED_STAGED_SKILL_PATHS`, `APPROVED_STAGED_SCRIPT_PATHS`, `APPROVED_STAGED_SETTINGS_PATHS`, `APPROVED_STAGED_TEST_PATHS` and `APPROVED_STAGED_FIXTURE_PATHS`, separately from the package catalog | engineering |
| R4 | The staged-path check reads the live index, so unrelated staged work leaks into an unrelated commit | `check_staged_forbidden_and_pii` calls `get_staged_paths(root)`, which reads the real index rather than the paths of the commit being built. A package with its own files staged cannot be validated in isolation while another package is staged | The current index holds the `a1form_generator` increment (`.gitignore`, `change-packages.yml`, `docs/architecture/A1_FRAMEWORKS.md`, `scripts/validate_change_packages.py`, `scripts/validate_planning.py`, `tests/test_validate_change_packages.py`, `tests/test_validate_planning.py`, `workflows/a1/CHANGELOG.md`, `workflows/a1/README.md`, `workflows/a1/a1form-generator-PLAN.md`) while the governance package is being prepared | engineering |
| R5 | Documentation-only deliveries are validated by the working tree, not by committed source | `scripts/validate_planning.py` passes against the working tree, where the untracked plan exists, while `tests/test_validate_planning.py` builds its fixture from `git archive HEAD`. Two runs of "the same" check disagree, and the passing one is the one that hides the defect | Working tree: 24/24 checks pass, exit 0. `HEAD` export: `test_valid_full_catalog_passes` and `test_valid_full_catalog_json` fail, with 23 passed / 1 failed inside the exported validator | engineering |
| R6 | Research documents are committed as reader-visible evidence while being marked "unpublished local material" elsewhere | The index lists several entries as unpublished local material, so a document can be simultaneously a committed link target and an unregistered local artifact, which keeps the link check and the catalog check disagreeing | `plans/INDEX.md` contains 7 "unpublished local material" markers, the same count as in `HEAD` | primary agent |
| R7 | Broken links accumulate in `HEAD` because only catalog-referenced Markdown is link-checked | `check_markdown_links` covers catalog-referenced files. Other committed Markdown is never checked, so a broken link survives until some later check happens to load that file into the export fixture | 21 broken relative links exist in `HEAD`; the 15 not in this task's set include `docs/research/2026-09-16-jansa1-framework-audit.md`, `docs/research/2026-09-17-script-validation-research/README.md` and `decisions/ADR-001-jan-portal-architecture.md` | engineering |
| R8 | Application-side PostgreSQL defects stay open across plan updates | `AGENTS.md` records four known application-side defects (target forwarding, disposable cleanup verification, migration credential scope, effective statement timeout) as tracked in the active child plan. Prose in `AGENTS.md` alone does not close them | `plans/2026-09-14-delivery-reliability-and-jan-v1.md` line 159 records the reproduced `psql -Atc` lock-probe defect; P0 JAN-04 at line 215 still requires review and integration of the unstaged forwarding/normalization repairs | runtime engineering |
| R9 | Unrelated dirty work shares the checkout and the index | Every commit in this repository must be built from an explicit path list. Untracked plans, `temp_orig`, `temp_orig.py`, `test_output/`, per-worker scratch
directories and scratch review CSVs sit beside the deliverables and are easy to stage by accident | `git status --short` currently lists 52 untracked paths under `docs/research` and `docs/architecture` plus unrelated scratch files at the repository root | engineering |

### Decision needed from the owner

R1 and R2 block a coherent governance commit today. The proposed minimal
resolution is to register the five supporting evidence files explicitly under
`governance_truth` in `change-packages.yml`, and to add the same paths to the
matching `APPROVED_STAGED_*` set in `scripts/validate_planning.py` so that the
two registries agree (R3). This does not add a catalog ID, does not change
any gate and does not authorize any backup, move, publication or deployment.
The broader fix for R7 — link-checking all committed Markdown rather than only
catalog-referenced files — is a separate, larger change and is deliberately not
attempted here.

## Current user outcome: archive unrelated work, keep a functional product

The latest user clarification prioritizes a navigable, functional sites/FO/BO/OCR/A1
project with recoverable archived extras, not development of a separate tooling
product. The [complete directory map](../docs/architecture/project-directory-map.md)
lists all 37 top-level directories and keep/mixed/private/archive boundaries.
It is name/source-level classification, not inspection of protected content or
authorization to bulk-move mixed directories.

This queue supersedes the fresh-history independent-tooling destination proposed
below. Keep the older research as optional context; no new repo is required now.

- [x] Enumerate all top-level directories, including hidden ones, without traversing
  protected contents; define product architecture and archive categories.
- [ ] Complete source dependency delivery: `9a11260` omitted four required export
  support files. Deliver a forward commit (no amend/history rewrite), reinstate
  verifier/workflow coverage, and perform one committed-source entrypoint run.
- [ ] Prepare one explicit first-batch file manifest for general CLI documentation
  tooling. Include dependencies/tests/configs and restore paths; unknown consumers
  remain keep/review. Do not grow an independent tooling product.
- [ ] Infrastructure returns concrete encrypted destination, key custodian,
  retention, RPO/RTO and alert owner; capture the full consistent recovery set and
  prove isolated restore. A PostgreSQL-only backup is not whole-project recovery.
- [ ] After restore acceptance, move that reviewed non-sensitive batch into
  `.archive/project-separation/<batch-id>/` with provenance and restore instructions;
  deliberately exclude it from active discovery/build/test walks. Preserve checks.
- [ ] Run affected product checks with original locations absent, and rehearse
  restoring the archived batch. Then apply the same procedure to generic model
  evaluation/AC/AF experiments and superseded non-product research.
- [ ] Reconcile the actual served FO route with infrastructure; static FO presently
  reported unserved. Keep intended-host and Jan acceptance separate from synthetic.

Do not introduce Celery/Redis, Docker, new systemd units, secret rotation, SLSA or
new deployment tooling merely because an agent calls the current approach
non-standard. Existing architecture and infrastructure contracts remain the
baseline. New mechanisms need a concrete product problem and separate scope.
Dates help order historical documentation; they do not establish authority or
justify deletion. Private inputs/outputs/receipts remain in approved storage and
retention procedures, never ordinary `.archive/`.

Authoritative follow-up: [Git extraction tools, synthetic evidence and plan audit](../docs/research/2026-09-18-git-extraction-evidence.md).
Select reviewed current-file transfer with fresh history; use filter-repo only if
historical continuity becomes required and the historical source is separately
authorized and reviewed. Destination blame starts at extraction; preserve licenses,
attribution and sanitized provenance. Eight synthetic mechanism assertions passed;
they do not satisfy the application or recovery checkpoints below.

## Evidence checkpoint - 2026-09-18

The read-only gap analysis and sanitized receipt are
[`docs/research/2026-09-18-comprehensive-gap-analysis.md`](../docs/research/2026-09-18-comprehensive-gap-analysis.md)
and
[`docs/research/2026-09-18-gap-analysis-evidence.json`](../docs/research/2026-09-18-gap-analysis-evidence.json).
They add a reproduced protected-storage verifier mismatch (subsequently fixed
with a matching `document_storage()` regression), a confirmed `FieldDecision` ORM
invariant gap, current CI/scanner/permission/documentation findings, a
requirements-only CI bootstrap reproduction, and a reconciled history/worktree
inventory. They do not change the backup, extraction, deployment, or activation
gates.

Current state remains research prepared, whole-project backup pending, isolated
restore not run, source transfer not started, and relocation not started. Existing
inherited modified and untracked files remain preserved and unstaged.

## Outcome and order

First prove recovery of the current project, including uncommitted work and
protected state. Then separate everything unrelated to sites, FO, BO, OCR and A1.
Keep the existing product architecture and canonical paths throughout the first
extraction. FO means front office; BO means back office pending correction.

Research and writing this plan can proceed before backup. Source moves, removals,
dependency pruning and configuration changes wait for the backup/restore checkpoint.
No reset, stash, force push, history rewrite, new remote, deployment or activation
is implied. Existing inherited changes remain owned by their original work.

## Phase 1 — recoverable whole-project checkpoint

Owner: infrastructure for backup operations; primary agent for a sanitized receipt.

1. Resolve the existing approved encrypted destination, key custodian, retention,
   recovery objectives and failure-alert owner. Use existing working infrastructure
   where available. Do not send credentials through chat. Do not create an ad-hoc
   unencrypted ZIP, tar archive, Git bundle or duplicate private tree.
2. Freeze the capture boundary: coordinate editors, uploads, OCR workers, A1
   publishers and document deletion. Infrastructure chooses a consistent capture
   mechanism or authorized maintenance window. Record capture time and selected
   source revision; a traversal of changing files is not an atomic snapshot.
3. Capture the following as one recovery set, with private manifests and explicit
   coverage/exclusion records. A missing component leaves “whole project” incomplete.

| Component | Required coverage and handling |
|---|---|
| Working source | Tracked, staged, unstaged and untracked files; symlinks, permissions and executable bits; do not substitute HEAD export |
| Git metadata/history | Preserve index, refs and local recovery state only inside the approved encrypted backup; treat historical objects as potentially sensitive; never publish them as a split repository |
| Protected project files | Authorized A1 inputs, scans, OCR, evidence, output, data, retained artifacts, private runtime and holds; original paths remain authoritative |
| Database | Consistent dump of the selected application database; identify schema and recovery role/extension prerequisites; no ordinary copy of a running PostgreSQL data directory |
| Runtime configuration and secrets | Infrastructure captures separately under its protected procedure, including `.runtime-config/gunicorn.env`; application inventory must not read, print, hash or package this payload |
| Reproduction/runtime dependencies | Cover local assets/models, native and Python dependency identities, necessary ignored assets and existing release exports; explicitly record any reproducible exclusions |
| Host recovery dependencies | Infrastructure records required service/routing/storage bindings without copying unrelated tenants; recovery evidence must identify external prerequisites |

4. Infrastructure measures source and restore capacity privately before capture.
   Preserve modes/ownership requirements. Avoid backing up the backup destination
   recursively. Treat logs and file lists as sensitive; only opaque receipt IDs and
   aggregate outcomes enter tracked documentation. Record the sensitive backup
   action through the existing applicable audit path, not a new audit schema.
5. Run the selected tool's integrity check, including stored data verification.
   Then actually restore to an exclusively owned isolated target. Private restored
   project files stay under an authorized protected in-project location; database
   restore target must meet the PostgreSQL operations skill's ownership rules.
   Infrastructure owns off-host encrypted custody under the recovery policy.
6. Verify recovered uncommitted source/index, representative protected file bytes,
   database queries/relationships and application file references. Preserve secret
   custody without printing values. Compare elapsed restore time with agreed RTO
   and capture age with RPO. Record failures rather than accepting a partial backup.

Exit: encrypted backup receipt, independently recoverable key, complete coverage,
off-host custody and a successful isolated restore. Current state: **not met**.
Policy: [real-data rules §12](../docs/security/real-data-rules.md#12-mandatory-recovery-before-real-data-activation)
and [existing infrastructure request](../docs/operations/servers-infra-core-postgresql-request.md).
The user has requested backup; the missing facts are its safe concrete target and
custody, not another generic permission to perform a backup.

## Phase 2 — exact source classification

Owner: engineering. Produce a reviewed per-file manifest from explicit non-private
paths, with current path, keep/extract/review decision, reason, dependencies,
destination, owner and source digest. Reject unreviewed symlinks or private content.
Do not traverse protected paths or infer safe contents from Git tracking alone.

| Initial group | Candidate disposition |
|---|---|
| `public-site/`, `portal/`, product templates/static assets | Keep; site routes, login/TOTP, workers, document review, assignments and downloads |
| `src/document_core/`, canonical A1 scripts, `templates/`, A1 configs, `frameworks/jansa1_v1/` | Keep; preserve both A1 frameworks and shared local OCR |
| Product tests, dependencies, deployment/recovery docs, relevant skills | Keep the full supporting dependency closure |
| `cli-docs-update/`, CLI claims configs, `scripts/verify_cli_claims.py`, general agent investigations | Extract as a coherent tooling unit after checking consumers |
| `src/free_model_eval/`, its runner/tests/fixtures/configs, `workflows/af/` | Extract candidate; retain any demonstrated product dependency until replaced |
| General collector/research engines, `workflows/ac/`, associated tests/schemas | Extract mechanism; assess recruitment-domain findings separately |
| `src/invoice_ingestion/`, prototypes, generic skills and mixed research docs | Review individually; do not remove a BO feature or a product decision record by directory name |
| `planning/`, `plans/`, `roadmap.md`, validation hooks and catalog | Retain governance, 34 catalog IDs and historical approvals; update references at the extraction checkpoint |
| Protected data, `.runtime-config/`, `.history-remediation/`, ignored reports | Exclude from source transfer; remain governed in place and covered by approved recovery |

Scan imports, runtime path reads, template/static references, shell callers, build
inputs, `change-packages.yml`, fixtures and documentation links. Include untracked
work in classification without silently staging it. Unknown files remain in review.
Do not treat package membership as a move list: `cli_agent_tooling` mixes generic
verification with retained site/release/A1 helpers. Its declared paths omit the
CLI verifier's consumed `config/cli_verification_claims.json`; include that file
and its schema in the verifier unit. Free-model evaluation spans source, runner,
policy, fixtures and tests, so a single-directory subtree split is insufficient.
Exit: every candidate file has one disposition and no unresolved product dependency
is scheduled for removal. A directory-level table alone does not satisfy this exit.

## Phase 3 — independent tooling source

Owner: engineering; new external workspace/remote selection requires exact authority.

Prepare a local reviewed transfer under the durable project root, using a dedicated
ignored non-product workspace whose exact path is selected after Phase 1. This is
an intermediate location, not a claim of completed repository separation.
Copy only reviewed non-PII files from Phase 2; initialize fresh source history rather
than copying `.git` or filtering old objects. Include their tests, licenses,
dependencies, entrypoints, setup guide and provenance mapping.

Proposed logical name: `prace-tooling-research`. No remote URL is invented or
created. A later separately selected private repository/location provides the final
ownership boundary. Do not make the application depend on that checkout's presence.
Validate the tooling unit standalone before removing any original source files.

Exit: matching reviewed source manifest and standalone tests; external publication
remains separately recorded. Keep source rollback available until acceptance.

## Phase 4 — remove application coupling in coherent batches

Owner: engineering. Start with general CLI investigations as the smallest candidate,
then evaluation tooling, then collectors and generic agent experiments.
Keep `release_verifier.py`, `playwright_smoke.py`, readiness checks and
`repair_a1_template_checkboxes.py` with the application despite their current
`cli_agent_tooling` package membership. Repartition package checks by the actual
retained/extracted dependencies in the same reviewed batch.
For each batch, remove only transferred reviewed files; update imports/path reads,
test selectors, dependency declarations and supporting docs together. Keep product
research and operational safeguards. Deliberately update hooks where necessary;
never bypass a mandatory hook merely because the old selector references moved code.

Reconcile the locally observed upstream commit without overwriting inherited work.
Review exact staged paths and the full staged diff. Let existing hooks select checks
once; inspect their private reports. Commit coherent source batches, inspect outgoing
objects, and only push the authorized existing origin feature branch with an explicit
refspec. New tooling-remote publication needs its own authorization.

Exit: clean application setup/build/test does not need extracted tools or their
packages. No accidental runtime import or dynamic file dependency remains.

## Phase 5 — demonstrate the retained application

Owner: engineering, then Jan. Use the existing reproducible acceptance entrypoint
on committed source and an exclusively owned synthetic database. Consult the
synthetic-portal and PostgreSQL skills before executing that workflow.

- Open the public site and check expected assets/routes.
- Complete normal login/TOTP; save an incomplete synthetic worker.
- Upload a synthetic document, process local OCR and correct/confirm its proposal.
- Create/correct an assignment and download the protected original.
- Demonstrate denied access and persistence of the same records/file bytes across
  an authorized test-service restart.
- Run separate synthetic A1 regression through canonical scripts; inspect every
  generated page using the A1 skill when generation is exercised. A1 remains
  maintained in scope but official issuance is not a core-v1 acceptance gate.
- Repeat required product checks with the tooling workspace unavailable to prove
  that extraction is real. Do not substitute a grep-only check for execution.

Exit: reproducible demo, matching source/dependency/settings evidence, documented
limitations, and separately recorded Jan acceptance. Deployment remains a separate
operation; no production restart or migration is scheduled by this plan.

## Rollback and completion record

Before acceptance, stop a failing batch and restore only its source changes from
the identified pre-extraction source state, preserving subsequent unrelated edits.
Do not overwrite the live database or documents for a source-only failure. Whole
recovery is an infrastructure operation using the tested recovery set and explicit
target; prove it isolated before any live recovery decision.

Maintain [one delivery record](../docs/operations/git-delivery.md) for research,
backup, classification, implementation, validation, publication, deployment and
acceptance. Completion means all phase exits passed, a final destination is selected,
and no unclassified out-of-scope files remain in the application delivery tree.
Old Git history and protected operational data intentionally retain their governed
locations; their deletion is not part of source separation.

## Present limitations

No backup, restored database, file move, source deletion, installation, commit,
publication or deployment has been performed for this task. Endpoint/key custody
and recovery coordination are unresolved. The mapping above is preliminary; it
does not certify every untracked artifact or third-party skill. Work estimates
depend on measured backup volume and the exact dependency manifest.
