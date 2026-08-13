# Plan Q — Repository History, Reference, and Privacy Remediation

**Status:** active
**Milestone:** M0
**Owner:** primary agent; Pavel approves exact remote/destructive actions

## Objective

Produce a verified, reversible procedure and repository inventory before any
history replacement, archival, cleanup, or remote publication. This plan does not
itself authorize a force-push, deletion, external-file move, or remote change.

## Reconciled execution context — 2026-08-13

- The 2026-08-12 SHA/no-push snapshot below is superseded. A sanitized checkpoint
  `c01aa2b` was published to both remote branches before this reconciliation; do
  not plan from the former `2250845` premise.
- The working branch at reconciliation is
  `feat/prace-readiness-plan-2026-08-13` at `ba06e05`, ahead of the published
  sanitized checkpoint. Re-resolve all local and remote refs immediately before
  any later publication; these values are evidence, not an authorization.
- Remote visibility remains private. The branch-protection/ruleset API previously
  returned a free-plan 403, so server-side protection must not be assumed.
- The working tree is mixed and dirty: governance/planning, A1 code/config/tests,
  historical/reference material, and untracked documents are present together.
- Reachable objects still contain OP/ZP scans, generated A1 PDFs, employee JSON,
  OCR results, and reports. Deleting them at later tips did not remove exposure
  from history; a normal all-ref Git bundle would duplicate that PII.
- No common private-key, AWS access-key, GitHub token, or password-assignment hit
  was found in the initial path-only scan. Generic `sk-`/`OPENAI_API_KEY` hits were
  false positives in the PDF template and policy prose; this is not a substitute
  for an approved full secret scanner.
- Existing pre-rewrite and rollback refs remain local retention assets. Inventory
  their exact object IDs and expiry before garbage collection; never publish them
  as branches or tags. `git fsck`/reflog evidence must be refreshed before any
  retention or GC decision.
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
9. Merge unique verified facts from the untracked readiness/unblock reports into
   canonical plans or the decision register. Those handoff files are evidence, not
   authority, and must not be committed merely because they exist.
10. Record the already-executed sanitized checkpoint in the decision register,
    including actor/approval evidence if recoverable, resulting refs, scan
    evidence, and remaining rollback-ref retention/GC decision.

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

The executed checkpoint and current refs are reconciled, the remaining procedure
is independently reviewable, rollback retention is explicit, all intended objects
and the final tree have scan criteria, and every archival/deletion candidate has a
consumer/privacy disposition. No further push or GC is implied.

## Exclusions

No commit, push, force-push, history rewrite, branch/remote/visibility change,
external-file relocation, archive move, or deletion without separate exact approval.
