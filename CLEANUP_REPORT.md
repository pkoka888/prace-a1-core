# Cleanup and Repository State Report

> **Status: Historical snapshot — do not execute.** Paths, counts, branch state,
> and pipeline statements below may be stale. Current authority is `AGENTS.md`,
> `roadmap.md`, `plans/INDEX.md`, and the canonical workflow READMEs. Retained in
> place until Plan L's later reference/privacy audit; no archive manifest is
> currently assumed to exist.

**Verified:** 2026-08-11  
**Branch:** `codex/unified-a1-core` at `864fc4b` before this working change

## Git state

- Worktree was clean at audit start.
- Local branch is five commits ahead of `origin/codex/unified-a1-core`.
- `master` equals `origin/master` at `3302934`.
- After a fresh fetch, the feature branch and `origin/master` diverge after
  `d247bb0`: master has two unique commits and the local feature branch has nine.
  Relative to its own remote feature ref, the local branch is exactly five commits
  ahead and zero behind.
- Remote `origin` is `https://github.com/pkoka888/prace-v-nemecku.git` and GitHub's
  public API reports visibility **public**, default branch `master`.
- GitHub CLI has no authenticated session. No push, PR, branch deletion, history
  rewrite or visibility change was performed.

## Privacy incident boundary

Earlier public remote commits contain tracked normalized/employee JSON, OCR and
processing results, generated A1 PDFs and a generation manifest. `.env` has no
tracked history. Stop pushing until the owner assesses exposure. Recommended
operator actions are:

1. make the repository private immediately if it should never have been public;
2. inventory exposed fields across all remote commits without redistributing them;
3. obtain privacy/security advice and notify affected parties where required;
4. rotate/replace exposed identifiers where feasible;
5. rewrite remote history only after an approved backup and coordination plan;
6. re-clone/expire old clones and caches after any rewrite.

These are intentionally not automated here because visibility changes and history
rewrites are external/destructive actions requiring explicit authority.

## Canonical retained path

`private/a1_final_review.csv` + `config/a1_provisional.json` → institution profiles
→ `scripts/generate_provisional_a1.py` → `scripts/finalize_a1.py` helpers →
`scripts/a1_core.py` → `templates/a1_background.pdf` +
`config/a1_layout.json` → `scripts/a1_quality_gate.py`.

The cleanup checkpoint archived competing historical generators and deleted old
tracked final PDFs. `archive/MANIFEST.md` now documents the archive groups.

## Changes completed in this follow-up

- Added pinned `requirements.txt`.
- Added a non-mutating `--help`/argument parser to the provisional generator.
- Aligned provisional issue-date validation to 61–180 days.
- Added female birth-number month-offset validation.
- Corrected institution provenance to the selected profile URL.
- Extended deterministic text checks to birth place, nationality and residence.
- Added both operator workflow READMEs and archive manifest.
- Documented the public-remote privacy boundary and branch topology.

## Verification

- `venv/bin/python -m pytest -q`: 55 passed, one skipped, 20 subtests; 27 pypdf
  deprecation warnings.
- Current final-readiness check: nine of nine reviewed rows blocked as intended;
  authoritative activity/certificate/signatory evidence and user approval are
  absent.
- Existing provisional package contains 11 PDFs and 33 previews, but its page-2
  self-employed business details were populated without the newly required
  separate Section 4 review columns. It must not receive a current QA PASS or be
  promoted; preserve it only as provisional evidence until regenerated from
  reviewed Section 4 values.
- The current quality gate writes a fail-closed report and removes any PASS
  manifest when those Section 4 columns are absent.

## Remaining known gaps

- Public-history privacy remediation requires owner action.
- The two additional provisional people are not part of the nine-row final review
  CSV and cannot enter the final path yet.
- The nine-row CSV needs explicit reviewed `employment_*` columns. They must not be
  inferred from identity/residence or populated from another person's form.
- Employee-multi-state checkbox geometry is not implemented; the current cohort is
  self-employed multi-state only.
- The scan-to-employee adapter has not been rebuilt for RapidOCR v3.
- A Czech-capable font is host-provided rather than bundled and hash-locked.
- The skipped visual-regression test needs an approved golden baseline.
- Historical PaddleOCR plans and unreachable active-tree utilities still require a
  final archive decision; they are not production fallbacks.
- Product/market/legal/architecture research in Plan C remains incomplete.

## Reachability audit

Direct code/test imports retain `a1_core.py`, `finalize_a1.py`,
`generate_provisional_a1.py`, `a1_quality_gate.py`, and the tested
`build_clean_background.py`. The following active-tree utilities have no code/test
consumer and remain manual archive candidates: `a1_form_generator.py`,
`create_final_archive.py`, `create_verification_artifacts.py`,
`detect_row_geometry.py`, `generate_corrected_a1.py`,
`reconstruct_checkboxes.py`, and `validate_corrected_a1.py`. They were not moved in
this pass because their recovery value and concurrent changes require an explicit
operator decision.
