# Plan Q — Repository History, Reference, and Privacy Remediation

**Status:** accepted
**Milestone:** M0
**Owner:** primary agent; Pavel approves exact remote/destructive actions

## Objective

Reconcile and accept the verified sanitized publication while preserving explicit
authorization boundaries for local PII-bearing recovery objects, archival,
deletion, garbage collection, and any later remote publication.

## Reconciled execution context — 2026-08-13

- The 2026-08-12 SHA/no-push snapshot below is superseded. A sanitized checkpoint
  `c01aa2b` was published to both remote branches before this reconciliation; do
  not plan from the former `2250845` premise.
- The accepted sanitized baseline is `c01aa2b`. The current planning branch and
  its remote are later descendants; re-resolve all refs before any future action.
- Remote visibility remains private. The branch-protection/ruleset API previously
  returned a free-plan 403, so server-side protection must not be assumed.
- Published refs and the fresh-clone tree were verified against the sanitized
  checkpoint. PII-bearing history remains only in local pre-rewrite/rollback refs,
  reflogs, and unreachable objects; an all-ref bundle would duplicate that PII.
- A checksum-verified Gitleaks scan with a positive-control canary reported no
  findings in the candidate or fresh-clone trees. Protected evidence remains in
  the gitignored remediation workspace.
- Existing pre-rewrite and rollback refs remain local retention assets. Inventory
  their exact object IDs and expiry before garbage collection; never publish them
  as branches or tags. `git fsck`/reflog evidence must be refreshed before any
  retention or GC decision.
- A full project-scope check covered 72 Markdown files with zero broken relative
  links. The earlier 48-file result was a valid active-document subset only.
- `scripts/inventory_repository.py` now records the `A1_PRIVATE_DIR` contract.

## Completed checkpoint

1. Published refs were replaced with sanitized checkpoint `c01aa2b` and verified
   by fresh clone, intended-tree comparison, full-object path scans, Gitleaks, and
   a positive-control canary.
2. The private repository, published refs, default branch, and absence of published
   rollback/pre-rewrite refs were independently checked.
3. DEC-014 records Pavel's acceptance of the sanitized baseline.

## Separately gated follow-up

1. Audit Markdown links and repository-relative bare paths, tracked/ignored privacy
   boundaries, `.gitignore`, dead scripts/configs, and all consumers/tests before
   moving or deleting any historical material.
2. Inventory legacy home-directory rewrite/backup material read-only. It
   is not project authority and must not be used for future work.
3. If a replacement workspace is later required, create it protected and
   gitignored under this project root, keep it only for the approved procedure, and
   remove it only with explicit destructive-action approval.
4. After the audit, propose an archive manifest and a `paddleocr` subdirectory in
   the future documentation archive; preserve existing non-executable banners until the
   separately approved move. Never create a root `archive/` to satisfy stale text.
5. Keep future publication, rollback, retention, reflog expiry, pruning, garbage
   collection, and deletion subject to separate exact approval.
6. **Completed 2026-08-13:** The sibling workspace `/var/www/prace-v-nemecku.tvoje.info` was inventoried, semantically compared, and deleted under Pavel's explicit instruction alone (not under Plan Q authorization). The tvoje.info catalog/validator are authoritative; tvoje.info is no longer accessible. No four-file SHA-256 inventory was preserved from the cleanup; this is explicitly noted.

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

Acceptance closes the publication checkpoint only. It authorizes no commit, push,
history rewrite, branch/remote/visibility change, recovery-ref deletion, reflog
expiry, garbage collection, external-file relocation, archive move, or deletion.
