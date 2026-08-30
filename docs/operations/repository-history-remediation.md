# Repository History Remediation — Executed Checkpoint and Retention Controls

**Status:** accepted checkpoint; destructive follow-up separately gated
**Owner:** primary agent
**Approver for remote action:** Pavel
**Evidence date:** 2026-08-13

This record implements PLAN-A1 (formerly Plan Q) and documents the already-executed sanitized
publication. Acceptance does not authorize another commit/push, history rewrite,
recovery-ref deletion, reflog expiry, garbage collection, or visibility change.

## Current evidence

| Item | Verified local value |
|---|---|
| Project | `/var/www/prace-v-nemecku.tvoje.info` |
| Accepted sanitized baseline | `c01aa2b5139e15518b02b09e1296e1377e034cea` |
| Published baseline refs at verification | `master` and `codex/unified-a1-core` → `c01aa2b` |
| Current planning branch at 2026-08-13 checkpoint | `feat/prace-readiness-plan-2026-08-13`; resolve again before any future action |
| Local recovery assets | `pre-rewrite/*`, `refs/rollback/*`, reflogs, and unreachable objects; never publish or delete without exact approval |
| Integrity and scans | Fresh clone/tree comparison passed; Gitleaks candidate and remote-clone reports were empty after a successful canary detection |
| Remote URL | `https://github.com/pkoka888/prace-v-nemecku.git` |
| Live GitHub state | Private repository; remote HEAD/default branch `master`; sole collaborator `pkoka888` with admin access |
| Live branch SHAs at publication verification | `master=c01aa2b`; `codex/unified-a1-core=c01aa2b` |
| Branch guards | Branch-protection/ruleset APIs unavailable on the current free plan (403); no available ruleset guard on either branch |
| Markdown links | Full project scope: 72 Markdown files, zero broken relative links; earlier 48-file result was an active-document subset |

The accepted remote baseline excludes the PII-bearing ancestry. That history still
exists locally through recovery refs, reflogs, and unreachable objects. A normal
all-ref bundle or publication of those refs would duplicate or re-expose PII.

## Change separation after the checkpoint

Review and commit only when explicitly authorized, in this order and with exact
path staging:

1. Governance/planning documentation, including the decision system and Plans Q/R.
2. A1 code, layout/config, skill, and tests, after A1-specific privacy and test gates.
3. Historical/reference banners and derived prototype material.
4. Classification of `scripts/validate_ocr_proposals.py`; default is defer, not run.

The A1 inventory now uses the `A1_PRIVATE_DIR` contract. Do not reintroduce the
removed `private/a1_final_review.csv` mapping.

Do not stage `a1/`, `scans/`, `ocr/`, `evidence/`, `output/`, runtime, secrets,
`.env`, or any other ignored path. Do not use broad staging commands.

## Safe backup design

Do not create an all-ref bundle, bare clone, archive, or filesystem copy: reachable
history contains PII and those would become prohibited duplicate backups. Before
any rewrite, create a local rollback ref under `refs/rollback/` that points to the
exact approved pre-rewrite commit. A ref preserves already-existing objects without
copying their contents. Record its SHA with `git rev-parse` and verify it with
`git fsck --no-reflogs --full`.

Existing rollback refs are local only and were not published. Local unreachable
objects must be included in the exposure assessment before any garbage collection;
do not copy them, expire reflogs, prune objects, or run GC without a separately
approved privacy-safe procedure.

## Rewrite workspace and sanitized source definition

- Use a mode-700, gitignored workspace under the project root only after the dirty
  source tree is checkpointed. Never use the discovered legacy
  legacy home-directory rewrite/backup paths as authority or rollback.
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

## Mandatory gates for any later publication

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

## Future remote execution template — deliberately incomplete

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

## Remaining separately authorized decisions

- Pavel must approve the exact retention period and disposal procedure for local
  pre-rewrite branches, rollback refs, reflogs, and unreachable objects.
- Any later publication requires freshly resolved refs, leases, scan evidence,
  coordination, and exact remote approval.
- Historical archive moves or deletions require the reference/privacy disposition
  described by PLAN-A1 (formerly Plan Q); acceptance of the checkpoint does not approve them.
