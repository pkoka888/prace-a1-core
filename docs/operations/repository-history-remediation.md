# Repository History Remediation — Preflight and Rollback Procedure

**Status:** active; independently reviewed, but non-executable until every approval gate below passes
**Owner:** primary agent
**Approver for remote action:** Pavel
**Evidence date:** 2026-08-12

This runbook implements Plan Q. It does not authorize a commit, rewrite, push,
force-push, branch deletion, or remote visibility/default-branch change.

## Current evidence

| Item | Verified local value |
|---|---|
| Project | `/var/www/prace-v-nemecku.tvoje.info` |
| Current branch/HEAD | `codex/unified-a1-core` / `0b86174fe7d842c7860c4d7db59f34b1853b2d15` |
| Feature upstream | `origin/codex/unified-a1-core` / `2250845256f4dda882bc773c56193b03fd161d06` |
| Local and remote-tracking master | `3302934` |
| Feature vs upstream | 12 ahead, 0 behind |
| Feature vs master | 16 feature-side commits, 2 master-side commits |
| Git object store | 346 loose objects, approximately 16.71 MiB |
| Local rollback ref | `refs/rollback/2026-08-12-pre-plan-q-0b86174` → `0b86174fe7d842c7860c4d7db59f34b1853b2d15` |
| Integrity check | `git fsck --no-reflogs --full` completed with no corrupt/missing objects and reported 26 dangling blobs |
| Remote URL | `https://github.com/pkoka888/prace-v-nemecku.git` |
| Live GitHub state | Private repository; remote HEAD/default branch `master`; sole collaborator `pkoka888` with admin access |
| Live branch SHAs | `master=3302934`; `codex/unified-a1-core=2250845`; match local remote-tracking refs |
| Branch guards | Branch-protection/ruleset APIs unavailable on the current free plan (403); no available ruleset guard on either branch |
| Markdown links | Full project scope: 72 Markdown files, zero broken relative links; earlier 48-file result was an active-document subset |

The 12 unpublished commits are coherent privacy/A1 checkpoints, but they are not
safe to publish as ordinary descendants: their reachable ancestry still includes
employee JSON, OCR data, identity scans, generated PDFs, and reports. The working
tree also contains multiple change classes and must not be committed as one unit.

## Required checkpoint split before rewrite work

Review and commit only when explicitly authorized, in this order and with exact
path staging:

1. Governance/planning documentation, including the decision system and Plans Q/R.
2. A1 code, layout/config, skill, and tests, after A1-specific privacy and test gates.
3. Historical/reference banners and derived prototype material.
4. Classification of `scripts/validate_ocr_proposals.py`; default is defer, not run.

The A1 checkpoint must also replace the stale
`private/a1_final_review.csv` canonical-map entry in
`scripts/inventory_repository.py` with the current `A1_PRIVATE_DIR` contract.

Do not stage `a1/`, `scans/`, `ocr/`, `evidence/`, `output/`, runtime, secrets,
`.env`, or any other ignored path. Do not use broad staging commands.

## Safe backup design

Do not create an all-ref bundle, bare clone, archive, or filesystem copy: reachable
history contains PII and those would become prohibited duplicate backups. Before
any rewrite, create a local rollback ref under `refs/rollback/` that points to the
exact approved pre-rewrite commit. A ref preserves already-existing objects without
copying their contents. Record its SHA with `git rev-parse` and verify it with
`git fsck --no-reflogs --full`.

The initial rollback ref protects the current committed HEAD only. Uncommitted work
is protected by leaving it untouched; no rewrite may start until each approved
change class is committed separately and the rollback ref is advanced to the exact
approved source tip. A path/hash manifest may record dirty state, but must not copy
file contents or sensitive values.

The initial ref above was created and resolved successfully on 2026-08-12. It is
local only and was not pushed. The 26 dangling blobs must be included in the local
exposure assessment before any garbage collection; do not inspect them in agent
output, copy them, expire reflogs, prune objects, or run aggressive GC without a
separately approved privacy-safe procedure.

## Rewrite workspace and sanitized source definition

- Use a mode-700, gitignored workspace under the project root only after the dirty
  source tree is checkpointed. Never use the discovered legacy
  `/home/pavel/a1-rewrite.git` or `/home/pavel/a1-backups` as authority or rollback.
- The sanitized source tip is the reviewed checkpoint series plus both independent
  master-side changes if their non-PII intent remains required. Resolve that merge
  or replay explicitly; do not silently drop either side.
- Remove PII-bearing paths and blobs from every ref selected for publication, not
  merely from the final tree. Retain only canonical non-PII source and documentation.
- Compare the rewritten tip tree against the approved source tree and explain every
  intentional SHA/tree difference caused by replay or filtering.

## Master-only commit disposition

Tree-level inspection, without opening report contents, resolved both commits that
exist only on `master`:

| Commit | Actual tree change | Disposition |
|---|---|---|
| `14b52fd` | Deletes only `data/a1_forms_generated/GENERATION_SUMMARY.txt` | Do not replay. The feature line later removes the entire generated-data path and applies the stricter ignored-output policy, so the non-PII intent is already preserved. |
| `3302934` | Adds only `reports/employee_data_validation.md`; contrary to its subject, it has no `.gitignore` delta | Do not replay. Commit `47db3a3` deliberately removes tracked `reports/` as local-only analysis and the current `.gitignore` preserves that policy. |

The sanitized source definition therefore does not merge or cherry-pick either
master-only commit. Preserve their legitimate cleanup intent through the current
feature-tree deletion/ignore state, while excluding the validation report and all
historical generated artifacts from published history.

## Mandatory preflight gates

1. Immediately before execution, reverify the confirmed repository visibility,
   default branch, live branch SHAs, protections/rulesets, open PRs,
   collaborators/deploy keys, and maintenance window; no ruleset currently guards
   an accidental force-push.
2. Freeze exact source refs and expected object IDs; confirm no new remote commits.
3. Run an approved full-history PII and secret scan over every ref to be published.
4. Run tests, `git diff --check`, documentation links/status checks, and staged
   PII/secret checks for every checkpoint commit.
5. Create/verify the rollback ref, sanitized workspace permissions/ignore rule,
   tip-tree comparison, and rollback communication plan.
6. Obtain Pavel's separate written approval naming repository, source SHA,
   destination refs, expected leases, and exact remote commands.

## Remote execution template — deliberately incomplete

Only after approval, replace placeholders with freshly verified full SHAs. Use
one narrow `--force-with-lease=<ref>:<expected-old-sha>` per approved destination;
never use `--force`, `--mirror`, wildcard refspecs, or automatic tag publication.
The exact command is withheld until live remote state and approved targets exist.

## Verification and rollback

- Fetch from a fresh protected workspace and confirm only approved refs exist.
- Fresh-clone the remote, compare the intended tip tree, rerun full-object PII/
  secret scans, tests, links/status checks, and ignored-path checks.
- If verification fails, stop publication and restore only the specifically
  approved ref from the local rollback ref using a newly verified lease. Do not
  delete or rewrite additional refs as part of rollback.
- Keep the rollback ref until Pavel accepts fresh-clone evidence and collaborator
  recovery. Removing it is a separate destructive action.

## Current blockers

- The dirty working tree is not separated into reviewed commits.
- Full approved PII/secret scanner and rewritten-object scan have not run.
- Exact destination refs, lease SHAs, coordination window, and remote approval are absent.

Therefore no history rewrite or remote publication is currently safe to execute.
