# Plan Q — Repository History, Reference, and Privacy Remediation

**Status:** active
**Milestone:** M0
**Owner:** primary agent; Pavel approves exact remote/destructive actions

## Objective

Produce a verified, reversible procedure and repository inventory before any
history replacement, archival, cleanup, or remote publication. This plan does not
itself authorize a force-push, deletion, external-file move, or remote change.

## Verified starting context — 2026-08-12

- Local branch `codex/unified-a1-core` is at `0b86174`, tracks
  `origin/codex/unified-a1-core`, and is 12 commits ahead / 0 behind that ref.
- Against `origin/master`, the feature side has 16 commits and master has two;
  this is a divergence, not a fast-forward replacement.
- Local `master` and `origin/master` are both at `3302934`; the feature upstream is
  at `2250845`. Independent live GitHub verification confirmed those SHAs, remote
  HEAD/default branch `master`, private visibility, and sole collaborator
  `pkoka888` with admin access. Branch-protection/ruleset APIs return the expected
  free-plan 403, so neither branch has an available server-side ruleset guard.
- The working tree is mixed and dirty: governance/planning, A1 code/config/tests,
  historical/reference material, and untracked documents are present together.
- Reachable objects still contain OP/ZP scans, generated A1 PDFs, employee JSON,
  OCR results, and reports. Deleting them at later tips did not remove exposure
  from history; a normal all-ref Git bundle would duplicate that PII.
- No common private-key, AWS access-key, GitHub token, or password-assignment hit
  was found in the initial path-only scan. Generic `sk-`/`OPENAI_API_KEY` hits were
  false positives in the PDF template and policy prose; this is not a substitute
  for an approved full secret scanner.
- Local rollback ref `refs/rollback/2026-08-12-pre-plan-q-0b86174` now anchors the
  committed HEAD. `git fsck --no-reflogs --full` found no corruption or missing
  objects and reported 26 dangling blobs, which remain uninspected and undeleted.
- A full project-scope check covered 72 Markdown files with zero broken relative
  links. The earlier 48-file result was a valid active-document subset only.
- `scripts/inventory_repository.py` still maps the removed
  `private/a1_final_review.csv`; correct it to the `A1_PRIVATE_DIR` contract in the
  separate A1 code/config/test checkpoint, not in this governance commit.

## Work

1. Resolve exact local/remote refs, upstreams, protected branches, collaborators,
   and the intended sanitized tip tree. Define which source tree is authoritative.
2. Inventory suspected PII/secret exposure by path and reachable Git object without
   copying sensitive values into reports. Run full-object scans, not tip-only scans.
3. Define the replacement/rewrite toolchain, exact refspecs, rollback refs,
   collaborator coordination, maintenance window, and narrow `--force-with-lease`
   command. Obtain separate approval for those exact targets before execution.
4. Compare the intended tip tree byte-for-byte with the approved sanitized source,
   scan all rewritten objects, and specify a fresh-clone verification from the
   remote after publication.
5. Audit Markdown links and repository-relative bare paths, tracked/ignored privacy
   boundaries, `.gitignore`, dead scripts/configs, and all consumers/tests before
   moving or deleting any historical material.
6. Inventory legacy rewrite/backup material under `/home/pavel/...` read-only. It
   is not project authority and must not be used for future work.
7. If a replacement workspace is later required, create it protected and
   gitignored under this project root, keep it only for the approved procedure, and
   remove it only with explicit destructive-action approval.
8. After the audit, propose an archive manifest and a `paddleocr` subdirectory in
   the future documentation archive; preserve existing non-executable banners until the
   separately approved move. Never create a root `archive/` to satisfy stale text.

## Deliverables

- Exact ref and remote-state inventory with access date.
- Sanitized source-tree definition and exposure inventory.
- Full-object scan report, intended-tip comparison, rollback/coordination runbook,
  exact force-with-lease proposal, and fresh-clone verification checklist.
- Link/bare-path reachability, tracked/ignored privacy, `.gitignore`, and
  dead-script/config consumer audit.
- Read-only inventory of legacy external rewrite/backup material.
- Explicit keep/move/delete proposals with privacy classification and approvals
  required; no PII-bearing artifact enters a tracked archive.
- Exact preflight and rollback procedure in
  [`../docs/operations/repository-history-remediation.md`](../docs/operations/repository-history-remediation.md).

## Exit gate

The procedure is independently reviewable, exact targets and rollback are known,
all intended objects and the final tree have scan criteria, and every archival or
deletion candidate has a consumer/privacy disposition. M0 requires this verified
procedure, not execution of remote replacement.

## Exclusions

No commit, push, force-push, history rewrite, branch/remote/visibility change,
external-file relocation, archive move, or deletion without separate exact approval.
