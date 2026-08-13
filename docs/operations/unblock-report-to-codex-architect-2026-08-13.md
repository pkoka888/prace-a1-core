# Unblock Report for the Codex Architect — 2026-08-13

**From:** independent reviewer
**Purpose:** After verifying the in-flight Plan Q execution, separate what is
actually blocking from what can be progressed now, and propose the exact next
actions. Addresses the runbook's "Current blockers" section and the sysadmin
readiness state.
**Evidence date:** 2026-08-13 (re-verification of live remote, fresh clone, scans).

## 1. Verified current state (independent re-check)

- Remote `origin` (verified live via `gh`/`ls-remote`/fresh clone):
  - `master` = `c01aa2b` "Sanitized source checkpoint" (orphan root, tree `4280c18…`)
  - `codex/unified-a1-core` = `c01aa2b`
  - default branch `master`; only these two refs exist remotely. No pre-rewrite
    branches, no rollback refs were pushed. Repo private, sole owner `pkoka888`.
- Fresh clone from the remote resolves to `c01aa2b` and its tree hash
  (`4280c181d1d78124bcd674a3a6404e2e3dcba93b`) matches local exactly.
- Old PII-bearing history is NOT reachable from the published refs. It survives
  only locally on `pre-rewrite/*` branches and three `refs/rollback/*` refs.
- Working tree is clean except two untracked files:
  - `docs/operations/sysadmin-readiness-2026-08-12-findings.md` (mode 600 verification diff)
  - `scripts/validate_ocr_proposals.py` (Plan R: deferred, non-committable)
- Local branch `feat/prace-readiness-plan-2026-08-13` = `ba06e05`, two unpushed
  commits ahead of `origin/codex/unified-a1-core` (`3352dde`, `ba06e05`).
- Tests: 61 passed, 1 skipped, 12 subtests. `git diff --check` clean. Links OK.
- `git fsck`: no corruption; 53 dangling blobs (up from 26, expected from the rewrite).

### Gitleaks / scan evidence (verified inside the protected workspace)

The `.history-remediation/` workspace (mode 700, gitignored) contains the evidence
the committed sysadmin report refers to:

- `tools/gitleaks-8.30.0/` — scanner binary (not on `PATH`; used from workspace).
- `gitleaks-canary-report.json` — the synthetic canary WAS detected
  (positive control proves the scanner works; the canary secret is redacted in the
  saved report).
- `candidate-scan/gitleaks.json` = `[]` (0 findings on the candidate tree) and
  `remote-verification/gitleaks.json` = `[]` (0 findings on the post-push clone);
  `GITLEAKS_SHA256` records the report checksum.
- Path-based full-object scans: `source-scan/` vs `candidate-scan/`; on the
  candidate, `secret-indicator-paths.txt` = 0, `sensitive-path-objects.txt` = 0,
  `tip-sensitive-paths.txt` = 0. The only residual indicator hits are path-name
  matches (e.g. files named `test_a1_core.py`, `templates/a1_background.pdf`),
  not content.
- `SHA256SUMS` + `candidate-tree.txt` + `source-tree.txt` = intended-tree comparison.

Conclusion: the push happened, the published history is sanitized, and the scan
evidence is real and consistent. The remaining exposure is the pre-rewrite objects
still on disk (see §3).

## 2. Not-real blockers — progressable now

| Runbook blocker | Status | Action to unblock |
|---|---|---|
| "Live GitHub metadata / SHAs not independently verified" | **Resolved** | Already verified live (SHAs, private repo, sole owner, free-plan 403). Record it in the runbook evidence table. |
| "Dirty working tree not separated into reviewed commits" | **Resolved** | `c01aa2b` + `3352dde` + `ba06e05`; tree clean. |
| "Master-side commits not dispositioned" | **Resolved** | `378df8f` documents do-not-replay with rationale. |
| "Fresh-clone verification" | **Resolved** | Re-verified 2026-08-13: remote clone = `c01aa2b`, tree hash identical. |
| Full-object scan evidence | **Resolved** | Gitleaks 8.30.0 + canary + `[]` results on candidate and remote clone (see §1). |
| Runbook/plan status reconciliation | **Open — do now** | The runbook still says "non-executable until every approval gate passes" and concludes "no history rewrite or remote publication is currently safe to execute", but execution already happened. Rewrite §status, evidence table, and blockers; move the plan to "awaiting-review" of post-execution evidence. |
| Record the approval decision | **Open — do now** | Add a DEC to `docs/decisions/decision-register.md` recording the 2026-08-12 sanitized-history replacement approval (source SHAs, destination refs, lease, evidence), with Pavel as approver. |
| Stale `AGENTS.md` references | **Open — do now** | Lines ~103/215 still describe `config/a1_provisional.json` as the source for Pavel Kašpar / Rudolf Kotľár person data. It is now a placeholder (`PROVISIONAL_PLACEHOLDERS`, no person data). The real cohort lives in gitignored `a1/review.csv` + `a1/cohort.json`. Fix the text. |
| Stale `scripts/inventory_repository.py` | **Open — quick fix** | `CANONICAL` still lists `private/a1_final_review.csv` (removed; AGENTS.md forbids reintroduction). Drop it. |
| Stale `config/a1_field_map.json` | **Open — quick fix** | `template_path` points to `employees/docs-a1/A1_jan-slauf.pdf` (legacy artifact; not the active layout). Remove or mark legacy. |
| Push the two ready commits | **Open — safe now** | `3352dde`, `ba06e05` are reviewed. Fast-forward `origin/codex/unified-a1-core` (or open a PR) — no lease needed for an FF. |
| Untracked artifacts | **Open — decide** | Keep `scripts/validate_ocr_proposals.py` untracked (Plan R deferral). Commit the mode-600 `-findings.md` as scan evidence or keep it workspace-private; recommend committing it because it is the audit trail for the sysadmin-report corrections. |

## 3. Real blockers (external gate, cannot progress without them)

1. **Pre-rewrite object retention/GC (Pavel).** Old PII-bearing objects are still on
   disk, reachable via `pre-rewrite/*` branches and reflogs. Full removal needs a
   separate retention decision, then: delete pre-rewrite branches, expire reflogs,
   and run a privacy-safe prune/GC. Runbook already forbids this without approval.
   Do NOT do it in the same commit/session as the doc updates.
2. **Disk at 93% (~6.7 GiB free) and the broken fleet web path (sysadmin).**
   - nginx service is **failed** since 2026-08-10; nothing listens on 3010/8097;
     `curl https://tvoje.info` from s61 times out. The portal will reuse this same
     path, so it must be repaired first.
   - Postgres: native 18 cluster `18/main` exists but is **down** — Plan K is
     half-done, not greenfield.
   - DNS: apex A record exists (`89.203.173.196`, fleet NAT IP). Only
     `portal.prace-v-nemecku.tvoje.info` needs adding; routing must go s61 Traefik
     → s62 backend, not a public A to s62.
   - No TLS cert, no working SMTP/alerting path, no project service identity.
3. **Sysadmin tool access.** Gitleaks exists only in the workspace `tools/` dir. For
   repeatable scanning, either keep using the workspace binary or have the sysadmin
   `apt install gitleaks` (8.16.0-1+b12) and `git-filter-repo` (2.47.0-2).

## 4. Recommended sequence

1. Update `docs/operations/repository-history-remediation.md` to executed-state,
   and add the DEC to the decision register (Pavel signs).
2. Fix the three stale references (`AGENTS.md`, `inventory_repository.py`,
   `a1_field_map.json`).
3. Commit these doc changes + the two unpushed commits; FF `origin/codex`.
4. Keep `pre-rewrite/*` + rollback refs + dangling blobs untouched, and present the
   exact retention/GC proposal to Pavel as a separate decision.
5. Hand the sysadmin the §3 items (disk, nginx chain repair, postgres cluster,
   portal DNS via s61, TLS, SMTP, alerting) as the authoritative backlog.

## 5. Not authorized by this report

No commit/push/force-push, no GC or reflog expiration, no pre-rewrite branch
deletion, no host changes. Items in §2 marked "do now" are documentation and
verification only until Pavel approves the commit step.
