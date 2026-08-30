# Operator Action Plan — 2026-08-29

**From:** primary agent (audit + test realignment session)
**Audience:** Pavel (operator) + sysadmin + Jan (where noted)
**Source audit:** branch `feat/prace-readiness-plan-2026-08-13` tip `491a31b`
**Status:** 8 commits pushed this session; 497 tests passing; pre-commit hook
now blocks quarantined paths; PII properly gitignored. This document collects
every remaining **operator input** item that the agent cannot resolve alone,
with target engagement windows, the reason each is needed, the concrete
"how" to act, and the expected outcome once resolved.

The plan is intentionally **non-executable** — none of these items are
auto-actionable. Each requires an explicit operator decision, data entry,
or environment access. Items already resolved this session (R-01, R-02,
L-01, L-02, AC-01 partially) are NOT listed; see `CHANGELOG.md`
`[Unreleased] — 2026-08-29` for those.

---

## 0. Operator input schedule (target dates)

| Window | Items | Why this window |
|---|---|---|
| **2026-08-30 → 2026-09-01** | R-03 (backup cleanup), A1 readiness data entry (batch 1) | Low-risk, deterministic; clears disk and unblocks 5–10 employee regenerations |
| **2026-09-02 → 2026-09-08** | M2 J1–J4 observation, AC-01 Plan AC update | Jan review window (1 week) + Plan AC integrity lane next step |
| **2026-09-09 → 2026-09-15** | K-01 capacity/backup evidence (sysadmin), AE-01 GitLab decision | Sysadmin evidence collection + remote activation paperwork |
| **2026-09-16 → 2026-09-30** | Plan AC Pilot 1 (OSS) + Pilot 2 (Czech) run, A1 regen batch 2 | Live capture blocks until gates pass; second cohort regen |
| **2026-10-01 →** | R-04+ (TBD) and M3+ (TBD) per new roadmap | Gated on the above |

A.1, A.2, and the A.1 readiness work (5) are operator-data entry and can
proceed in parallel with M2 observation; they are independent.

---

## 1. R-03 — Approve archival of `output/provisional.backup-*` directories

**Context (why).** The 25 dated `output/provisional.backup-YYYYMMDD-HHMMSS/`
directories under `output/` are stale snapshots from A1 provisional
regenerations between 2026-08-11 and 2026-08-12. They are listed in
`change-packages.yml` `quarantined_research_artifacts` prefixes
(`output/provisional.backup-*`) and are gitignored. Plan R §8 requires
*inventory by path, timestamp, counts, hashes, and canonical relevance
without opening PII* + *explicit approval before archival*. The audit
recorded the inventory on 2026-08-19; it has not been actioned yet.
Per project convention (`.archive/README.md`), **no item is deleted**;
everything that leaves the live tree moves to `.archive/<relative-path>`
so a future restore is a single `mv` away.

**How.**
1. Run a dry-run inventory (read-only) to confirm hashes match what was
   captured 2026-08-19:
   ```bash
   ls -d output/provisional.backup-* | wc -l                  # 25
   for d in output/provisional.backup-*; do
     echo "$d $(find $d -type f | wc -l) $(sha256sum $d/*.pdf 2>/dev/null | sha256sum)"
   done
   ```
2. Compare against `plans/audits/` and the 2026-08-19 inventory.
3. Confirm canonical 11 PDFs / 33 previews in `output/provisional/`
   (post-`db47b26` run) are sufficient.
4. **Archive** (no delete — per the `.archive/` convention, all moved
   items keep their relative path so future restoration is mechanical).
   The archive convention lives at `.archive/README.md`; the directory
   itself is gitignored (everything inside except its README). Run:
   ```bash
   mkdir -p .archive/output
   for d in output/provisional.backup-*; do
     mv "$d" ".archive/$d"
   done
   ```
5. Optionally keep one snapshot (e.g. `output/provisional.backup-20260812-130748`)
   in its original path as a deliberate archive. The script above
   skips directories that already exist via `mv -n` if needed.
6. Commit the move as a separate commit so the audit trail shows what
   left the live tree and when:
   ```bash
   git add -u output/provisional.backup-*    # records the removal
   git status                                # verify .archive/ entries are NOT staged (gitignored)
   git commit -m "chore: archive 25 output/provisional.backup-* per Plan R §8"
   ```

**Expected goals.**
- 25 stale snapshot directories moved under `.archive/output/` (their
  relative path preserved).
- `.archive/` tree mirrors the live tree for these paths.
- Git history shows the move as one chore commit referencing Plan R §8.
- No real-data loss; the snapshots can be restored with
  `mv .archive/output/provisional.backup-* output/` if ever needed.
- One canonical `output/provisional/` package preserved.
- No re-running of any A1 script needed.
- Disk freed (~225 MB based on 15 × ~9 MB from audit + 10 newer).
- `scripts/finalize_a1.py readiness` and `scripts/a1_quality_gate.py validate`
  continue to behave identically (they only read `output/provisional/`).

---

## 2. A.1 readiness — populate per-row data for the 17 blocked employees

**Context (why).** `scripts/finalize_a1.py readiness` reports 17/17 employees
blocked. The blocker pattern is identical for every row:
`missing activity_name`, `missing activity_address`, `missing document_id`,
`missing start_date`, `missing end_date`, `missing issue_date`,
`missing signed_by`, `missing activity_source`, `activity_source_status is not
AUTHORITATIVE`, same triple for `certificate_source` and `signatory_source`,
plus `certificate_reviewed/approved_for_pdf/validated_by_user` flag values
not equal to `YES` / `1`. The 7 Section 4 employment columns are present and
accepted; *only per-row evidence and operator review flags* are missing.
This is exactly the gap AGENTS.md "Gotcha" calls out (commit `aeef91f`).

**How.** Edit `$A1_PRIVATE_DIR/a1/review.csv` (gitignored PII). For each
employee row, populate:
- `activity_name`, `activity_address` — exact activity text the A1 will
  print in section 4(a) / 4(b).
- `document_id` — real ČSSZ document id (e.g. `N65023S444/2026/DE`); must
  match the `document_ids` map in `a1/cohort.json`.
- `start_date`, `end_date` — DD.MM.YYYY; both required.
- `issue_date` — DD.MM.YYYY; the date the document was issued.
- `signed_by` — exact OSSZ signatory name as it appears on the document.
- `activity_source`, `certificate_source`, `signatory_source` — short
  provenance strings (URL or filename) that prove the source.
- The three `_source_status` columns — set to `AUTHORITATIVE` only when
  the source is the ČSSZ/OSSZ document or equivalent primary evidence;
  otherwise `PROVISIONAL`.
- `certificate_reviewed`, `approved_for_pdf`, `validated_by_user` —
  set to `YES` / `1` only after a human has visually reviewed the
  document and signed off.

After each batch:
```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
venv/bin/python scripts/finalize_a1.py readiness | jq '.employees[] | select(.blockers|length>0) | {id: .employee_id, blockers}'
```

**Expected goals.**
- `readiness` JSON reports `ready: true` once all rows are complete.
- `scripts/a1_quality_gate.py render` + `validate` produce 11 fresh PDFs
  with a hash-bound QA manifest.
- Operator-confirmed employees get promoted to `output/final/` per Plan R
  exit gate (visual review + cleanup pending are the only remaining
  R-track work after data entry).

**Target window.** Batch 1 (5 employees) by **2026-09-01**; remaining
12 by **2026-09-30**. Splitting into batches is fine because per-employee
blockers are independent.

---

## 3. M2 J1–J4 observation — Jan walks the synthetic vertical slice

**Context (why).** Per `roadmap.md` "**Now**" lane and Plan M2
(`2026-08-17-plan-m2-functional-prototype-sprint.md`): the M2 vertical
slice is implemented, code-reviewed, and 495+ tests pass (now 497).
Status: "Jan completes J1–J4 on the synthetic vertical slice." Jan has
not yet observed the J1–J4 journeys end-to-end. The "Now" lane
explicitly lists this as the remaining work for the M2 milestone.

**How.** On the host that runs `portal/release1a/` (`localhost:8000` in
dev), Jan walks:
- **J1** — operator logs in, opens a worker, edits the worker record.
- **J2** — operator uploads a synthetic document scan, triggers OCR
  pipeline, reviews OCR proposals, accepts/rejects.
- **J3** — operator creates an assignment, observes optimistic-locking +
  overlap warnings (DEC-005).
- **J4** — operator prepares an A1 case from the worker record,
  observes the fail-closed gates, and signs off.

Jan records any defects as a markdown note in `docs/operations/` (a
single `j1-j4-observation-2026-MM-DD.md` per session). No PII in the
note — synthetic data only.

**Expected goals.**
- Four journeys pass with synthetic data.
- Any defects filed as a follow-up plan or commit (do NOT auto-fix
  during observation; this is the audit step).
- Plan M2 exit gate opens; M3 / broader Release 1A work can be planned
  against observed behaviour.

**Target window.** **2026-09-02 → 2026-09-08** (1 week Jan review window).

---

## 4. AE-01 — Approve GitLab remote + CI activation (DEC-016)

**Context (why).** Plan AE (`2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md`)
proposes a private GitLab secondary remote plus CI. DEC-016 is the
controlling decision. The local `infrastructure_git_workflow` package
already validates the change-package classifier and the pre-commit hook;
the GitLab-specific files (`.gitlab-ci.yml`, `docs/operations/gitlab-integration.md`)
are already in the `infrastructure_git_workflow` change package.
Activation is *separately gated*: per AGENTS.md, "Do not add a remote,
load credentials, install a runner, enable CI, commit, or push without
the exact separate approval required by Plan AE."

**How.** This is a DEC-016 decision; operator reads Plan AE §"Activation
gates" and DEC-016 evidence, then either:
- **Approve** — operator issues a written approval referencing DEC-016
  and Plan AE. The primary agent can then proceed with the GitLab
  activation checklist (`docs/operations/gitlab-integration.md`).
- **Defer** — keep GitHub as sole remote, mark DEC-016 as
  `awaiting-review`. No code changes; the local workflow files stay
  in the repo.

The activation checklist (per `docs/operations/gitlab-integration.md`)
involves: create private GitLab project, mirror `master`, configure
CI variables (zero paid API keys, see AGENTS.md "AI provider & cost
policy"), enable CI on the mirror only, validate that CI cannot push
back to GitHub. None of those steps run without approval.

**Expected goals.**
- Either GitLab is approved and activated per the checklist, OR
  DEC-016 is formally deferred with a documented reason.
- The "Gated" entry in `roadmap.md` for GitLab/CI (Plan AE) is updated
  with the decision and any follow-up.

**Target window.** Decision needed by **2026-09-15** so activation work
(if approved) can run alongside K-01 (Plan K sysadmin evidence).

---

## 5. K-01 — Capacity / backup / restore evidence for Plan K

**Context (why).** Plan K (`2026-08-12-plan-k-server62-readiness.md`) gates
Release 1A activation on real capacity, repaired edge path, monitoring,
mandatory recovery proof, rollback, permissions, and TLS evidence. The
plan's `Current Blocker`: "Operator/sysadmin recovery and capacity
evidence incomplete." This is sysadmin work, not operator-data entry,
but it is on the operator's coordination plate.

**How.** Sysadmin (or Pavel with sysadmin access) executes the Plan K
acceptance checklist:
1. Capture `df`, `free`, `nproc`, `vmstat 1 5` baseline under expected
   load (1 portal node + 1 cron + 1 OCR worker).
2. Run a synthetic backup → restore cycle on a non-prod dataset and
   record the recovery time + integrity hash.
3. Verify TLS chain (Let's Encrypt or internal CA) for the public host.
4. Capture monitoring endpoints (`/health`, `/metrics`) and confirm
   alerts fire on a synthetic outage.
5. Submit evidence as `docs/operations/sysadmin-readiness-2026-MM-DD.md`
   (mirroring the 2026-08-12 file already in the repo).

**Expected goals.**
- Plan K status moves from `active` → `completed`.
- Release 1A gates M3+ can plan against real capacity numbers, not
  aspirational ones.

**Target window.** **2026-09-09 → 2026-09-15** (parallel to AE-01).

---

## 6. AC-01 — Plan AC integrity lane decision on v12 scripts

**Context (why).** `PROJECT_AUDIT_REPORT.md` §1.2 flags inconsistency:
`scripts/run_collector_proposals_v12.py` and `tests/test_collector_v12.py`
are tracked, but the validator wrapper
`scripts/validate_collector_execution_v12.py` is in
`change-packages.yml` `quarantined_research_artifacts` (per the
"frozen v1.2 baseline" decision). The commit history shows `db47b26`
established the v1.1 wrapper; `ffb5922` later removed it (now restored
in `542b0e8`); the v12 variants were created as frozen research
checkpoints. CHANGELOG records AC-01 as "decision documented",
but the *underlying* Plan AC question — "are v12 scripts frozen
baselines, or quarantined research?" — has never been formally answered
in a plan update.

**How.** Either:
- **Option A — fully quarantine v12.** Move `scripts/run_collector_proposals_v12.py`
  and `tests/test_collector_v12.py` out of the tracked tree (delete +
  reference the SHA from the `quarantined_research_artifacts` lockfile),
  keeping only the v1.1 path live. Requires updating tests that
  import from v12.
- **Option B — fully track v12.** Move
  `scripts/validate_collector_execution_v12.py` from
  `quarantined_research_artifacts` to `plan_ac_integrity` paths in
  `change-packages.yml`. Re-introduces the v12 wrapper as live tooling.

This is a Plan AC plan-update decision. The current 2026-08-29 audit
treats Option A as the implicit default (it's what the quarantine state
already encodes) but Plan AC should ratify it explicitly.

**Expected goals.**
- Plan AC adds a sentence recording the decision (Option A *or* B).
- `change-packages.yml` and (if Option A) the tracked tree are made
  consistent with the decision in a follow-up commit.

**Target window.** Decision needed by **2026-09-08** to feed into
Pilot 1 tooling (item 7).

---

## 7. Plan AC Pilot 1 (OSS) + Pilot 2 (Czech) — unblock live capture

**Context (why).** Per `roadmap.md` "Plan AC integrity lane":
"In 🟡 + synthetic replay 🟡; Pilot 1/2 required before skill activation;
live capture blocked." AGENTS.md:
> It may become operational only after repeatable Pilot 1 (OSS tools) and
> Pilot 2 (Czech products) runs both pass Plan AC's evidence, review,
> safety, and reproducibility gates.

The 8.5 MB of quarantined research artifacts in `research/acquisition/`,
`research/processed/`, `research/benchmark-experimental/`, `research/review/`,
`research/pilot/` are all provisional outputs. Promoting any of them to
the tracked tree requires Pilot 1 + Pilot 2 to pass.

**How.** Per Plan AC and the
`.opencode/skills/market-research-evidence/SKILL.md` workflow:
1. Run Plan AC's canonical Pilot 1 (`scripts/run_collector_fixture.py` +
   `scripts/validate_collector_execution.py`) against the frozen
   `research/query-packs/plan-ac-core-1.1.json` OSS query pack. All
   frozen slots must produce repeatable `proven` results across at
   least 3 runs.
2. Run Pilot 2 with the Czech-product query pack (`vendor-*` queries
   on `fakturoid`, `idoklad`, `ucto.*`, etc.). Same repeatability
   standard.
3. Submit both runs to the operator for review. Operator records the
   pass/fail + hash evidence in a `plans/audits/plan-ac-pilot-N-2026-MM-DD.md`
   note.
4. On operator sign-off, update `change-packages.yml` to move
   `research/{acquisition,processed,review}/` atomic run results from
   `quarantined_research_artifacts` to `plan_ac_integrity` (or a new
   `plan_ac_evidence` package) and commit.

**Expected goals.**
- Plan AC skill activation unblocked.
- Quarantined research can be promoted batch-by-batch.
- The "experimental" caveat in AGENTS.md is updated to "operational
  in [scope]" once both pilots pass.

**Target window.** **2026-09-16 → 2026-09-30** (two-week window for
both pilots, depending on operator availability for review).

---

## 8. Visual review of canonical A1 PDFs

**Context (why).** Per `roadmap.md` Plan R: "**Plan R completed**
(2026-08-20) — 11 PDFs / 33 previews generated, QA passed; **visual
review & backup cleanup pending**." Item 1 (R-03) handles backup cleanup;
visual review is the other half. Until visual review is signed off,
A1 outputs stay provisional and cannot promote to `output/final/`.

**How.** Operator opens the 11 PDFs in `output/provisional/A1_*.pdf`
plus the 33 previews in `output/provisional-previews/A1_*-page-*.png`,
checks:
- Czech diacritics render correctly in every Section 4 box.
- "OSVČ" checkboxes correctly reflect each employee's `status_profile`.
- Address fields do not clip; numbers match the CSV exactly.
- `document_id` matches the ČSSZ document.

Operator records sign-off per employee via
`scripts/a1_quality_gate.py record-review` (hash-bound visual PASS).
The hash binding means each reviewer's PASS is auditable.

**Expected goals.**
- All 11 employee visual reviews recorded.
- `scripts/a1_quality_gate.py validate` exits 0 with hash-bound
  manifest.
- A1 outputs eligible to promote to `output/final/` per Plan R exit.

**Target window.** After item 2 (A1 readiness data) populates the
employees. Reasonable target: **2026-09-30** for the 5-batch-1
employees; **2026-10-15** for the remaining 12.

---

## 9. Out-of-scope but worth flagging

These are not strictly pending but the operator may want to be aware:

- **M3+ planning** — gated on M2 observation (item 3) + K-01 (item 5).
  No work to start yet.
- **Plan L historical-document review** — Plan L exit criterion;
  per CHANGELOG L-01 + L-02 are now satisfied. The remaining Plan L
  work is the "broader exit" (CLI contradictions, experimental-skill
  activation gate), all of which are non-blocking per `plans/INDEX.md`.
- **`docs/security/real-data-rules.md`** — already the sole
  activation gate for new real-data portal use. No edit pending; the
  rule remains the single source of truth.

---

## 10. Cross-references

- CHANGELOG `[Unreleased] — 2026-08-29`: this session's commits + the
  resolved decisions.
- `roadmap.md` "Now / Parallel / Gated" lanes.
- `plans/INDEX.md` controlled-status vocabulary.
- `change-packages.yml` package gating.
- `AGENTS.md` "Critical safety — PII, Git, secrets" + "AI provider
  & cost policy" (governs GitLab activation's zero-cost requirement).
- `docs/security/real-data-rules.md` (governs real-data activation).

---

*Prepared 2026-08-29 by primary agent after the audit + test realignment
session. Next refresh after M2 observation or Plan AC pilot completion.*
