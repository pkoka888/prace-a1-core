# Untracked research/ audit — 2026-09-07

> **Status: triage report only; no files moved or deleted.** Every
> disposition in this report is **retain pending review** following the
> independent session review (2026-09-07). Filename/keyword scans cannot
> establish "no PII" or "public-domain" status; classification needs an
> explicitly scoped, authorized local review; uncertain or sensitive
> cases require escalation per the operator workflow contract. AGENTS.md
> §Critical safety applies.

## Scope

Inventory of `research/` subdirectories outside the tracked root
(`research/DECISION_INPUTS_FOR_CODEX.md`, `research/2026-08-11-…`, and
`research/query-packs/` are already tracked and unchanged). Scope excludes
any path under `a1/`, `scans/`, `evidence/`, `ocr/` (gitignored per AGENTS.md).

```
research/
├── acquisition/   3.4M,  24 tracked, 19 untracked, 103 files
├── benchmark-experimental/   256K,  0 tracked, 31 untracked
├── pilot/          8.0K,  0 tracked, 1 untracked
├── processed/      1000K, 0 tracked, 18 untracked
└── review/         3.4M,  4 tracked, 8 untracked
```

Total untracked in scope: **77 files**, none already in `.gitignore`.

> **Correction (2026-09-07):** the per-directory "tracked/untracked/all/size"
> counts above mix files and directories (e.g. a subdirectory counts as 1
> under `tracked` and contributes ≥1 under `all`). The size column is
> `du -sh` output, which counts directory blocks. Recounting each
> subdirectory separately (e.g. via `find -type f | wc -l` and
> `find -type f -printf '%s\n' | awk '{s+=$1} END{print s}'`) is required
> before any quantitative claim is published.

## Reference map

Cross-references from tracked content (proves downstream dependency):

| Source | References |
|---|---|
| `tests/test_compare_research_runs.py` | `research/acquisition/atomic-run-*.json` |
| `scripts/generate_research_review_queue.py` | `research/review/operator-review.template.json`, `research/review/queue.json` |
| `scripts/normalize_datasets.py` | `research/processed/entities.json` (canonical envelope input) |
| `scripts/check_research_completeness.py` | `research/processed/entities.json` + `completeness_report.json` |
| `scripts/check_evidence_url.py` | `research/processed/evidence_checks*.json` |
| `scripts/compare_research_runs.py` | `research/processed/atomic-*-reproducibility-report.json` |
| `plans/PLAN-INVOICE.md` | `research/benchmark-experimental/` |
| `docs/operations/operator-action-plan-2026-08-29.md` | `research/pilot/README.md`, `research/benchmark-experimental/` |
| `docs/operations/opencode-work-orders/organization-audit.md` | `research/pilot/README.md`, `research/benchmark-experimental/` |

Per AGENTS.md §Skills, `market-research-evidence` is **experimental** and
"may become operational only after repeatable Pilot 1 (OSS tools) and Pilot 2
(Czech products) runs both pass Plan AC's evidence, review, safety, and
reproducibility gates." None of those gates have opened.

## Disposition matrix

> **Correction (2026-09-07):** every disposition below is **retain pending
> review**. Filename scans cannot establish no-PII or public-domain status;
> different `repeat-2026-08-14/` runs are not proven redundant; lack of
> script references does not justify deletion; `research/benchmark-experimental/`
> is directly consumed by `tests/test_benchmark_experimental.py:16` via
> `shutil.copytree` and cannot be archived; the existing organization work
> order explicitly excludes these trees. Counts in the original matrix
> conflated files and directories. The original legend below is retained
> for the reader's benefit; do not act on it.

Original legend (retracted):

- ~~**KEEP** — has ongoing purpose; commit to tracked tree~~
- ~~**ARCHIVE** — historical/reproducibility material; move to `runtime/research-archive/`~~
- ~~**DELETE** — redundant, draft, or regenerable from atomic inputs~~

Effective disposition (2026-09-07): **all 77 entries — retain pending review**.

### `research/acquisition/` — Plan AC atomic pilot outputs

| Path | Count | Effective disposition |
|---|---:|---|
| `synthetic-mini-pilot/{README,fixtures,fixture-set,request}` (already tracked) | 24 tracked | retain pending review (tracked) |
| `atomic-run-{a,b}-2026-08-14.json` | 2 untracked | retain pending review |
| `atomic-v1.1-errata-2026-08-14.json` | 1 untracked | retain pending review |
| `atomic-v1.1-run-{c,d,e,f,g,h,i}-2026-08-14.json` | 7 untracked | retain pending review |
| `collector-executions/{live-mini-2026-08-14,synthetic-mini-v1}.json` | 2 untracked | retain pending review |
| `collector-proposals/live-mini-2026-08-14.json` | 1 untracked | retain pending review |
| `live-mini-pilot/{README.md,request.json}` | 2 untracked | retain pending review |
| `raw/{czech_accounting_firms,czech_individual,czech_invoice_software,oss_invoice,studies_comprehensive}.json` | 5 untracked | retain pending review |
| `repeat-2026-08-14/{czech_accounting_firms,czech_individual,czech_invoice_software,oss_invoice,studies_comprehensive}.json` | 5 untracked | retain pending review — **not proven redundant**; `diff -q` showed differences, not equivalence |
| `source-captures/{live-mini-2026-08-14,synthetic-mini-v1,synthetic-mini-v2}/` | 3 subdirs untracked | retain pending review |
| `synthetic-mini-pilot/manifest.json` | 1 untracked | retain pending review |
| `synthetic-mini-pilot/manifest.json.bak` | 1 untracked | retain pending review |
| `synthetic-mini-pilot/runs/` | 1 subdir untracked | retain pending review |

### `research/benchmark-experimental/` — External validation benchmark

| Path | Count | Effective disposition |
|---|---:|---|
| `README.md` | 1 untracked | retain pending review |
| `STATUS.json` | 1 untracked | retain pending review |
| `schemas/`, `gold-answers/`, `evidence/`, `comparative-runs/`, `scoring/`, `reviewers/`, `run_project_skill.py`, `validate_*.py`, `holdout.json`, `sealed_holdout.json`, `questions.json`, `__pycache__/` | 27 untracked | **retain pending review — cannot be archived**; `tests/test_benchmark_experimental.py:16` `shutil.copytree`s this tree as a test fixture |

`sealed_holdout.json` integrity depends on the file remaining unobserved
by public runners. No archive destination proposed; the existing
`.gitignore` does not enforce isolation. A new isolation mechanism must be
designed before any move.

### `research/pilot/` — Plan AC scope description

| Path | Count | Effective disposition |
|---|---:|---|
| `README.md` | 1 untracked | retain pending review |

### `research/processed/` — Derived research outputs

| Path | Count | Effective disposition |
|---|---:|---|
| `entities.json` | 1 untracked | retain pending review |
| `entities.normalized.json`, `entities.scored.json` | 2 untracked | retain pending review |
| `completeness_report.json`, `normalization_report.json`, `scores.json` | 3 untracked | retain pending review |
| `evidence_checks.json`, `evidence_checks-pilot.json`, `evidence_checks-pilot-live.json`, `evidence_checks-all-live.json` | 4 untracked | retain pending review |
| `field-replay.json` | 1 untracked | retain pending review |
| `atomic-reproducibility-report.json`, `atomic-v1.1-reproducibility-report.json`, `atomic-v1.1-f-g-reproducibility-report.json`, `atomic-v1.1-h-i-reproducibility-report.json`, `reproducibility-report.json` | 5 untracked | retain pending review |
| `model-advisory-run-2026-08-14.json`, `model-advisory-hy3-run-2026-08-14.json` | 2 untracked | retain pending review |

### `research/review/` — Operator review queue

| Path | Count | Effective disposition |
|---|---:|---|
| `README.md`, `operator-review.template.json`, `review-queue.schema.json`, `review-response.schema.json` (already tracked) | 4 tracked | retain pending review (tracked) |
| `queue.json` | 1 untracked | retain pending review |
| `atomic-run-{a,b}-queue.json` | 2 untracked | retain pending review |
| `atomic-v1.1-run-{e,f,g,h,i}-queue.json` | 5 untracked | retain pending review |

## Aggregate

| Effective disposition | Count |
|---|---:|
| retain pending review (tracked) | 28 |
| retain pending review (untracked) | 77 |
| ~~KEEP~~ (retracted) | — |
| ~~ARCHIVE~~ (retracted) | — |
| ~~DELETE~~ (retracted) | — |

## Constraints

1. **PII/public-domain claim withdrawn.** Filename and keyword scans cannot
   establish no-PII or public-domain status. Classification requires an
   **explicitly scoped, authorized local review**; uncertain or sensitive
   cases escalate per the operator workflow contract. Universal
   human inspection of every file is not required and not appropriate.
   Until a scoped review is recorded, retain.
2. **Reproducibility:** atomic-run JSONs and `processed/` outputs bind to
   immutable query packs (`research/query-packs/plan-ac-core-1.{0,1}.json`).
   The packs are tracked; the runs are derived. Any move must preserve
   byte identity (no in-place rewrite).
3. **Sealed holdout integrity:** `benchmark-experimental/sealed_holdout.json`
   must remain unreadable to public benchmark runners; the existing
   `.gitignore` does not enforce isolation. A new isolation mechanism must
   be designed before any move. The tree is also consumed by
   `tests/test_benchmark_experimental.py:16`, so it cannot be relocated
   without rewriting that test.
4. **Organization work order scope:** the existing
   `docs/operations/opencode-work-orders/organization-audit.md` explicitly
   excludes `research/acquisition/`, `research/pilot/`, `research/processed/`,
   `research/benchmark-experimental/`. Any expanded authorization must be
   recorded as a separate work order before any move.

## Next steps (deferred)

All previously proposed actions are deferred until the constraints above
are satisfied and explicit operator approval is recorded:

| # | Action | Status |
|---:|---|---|
| 1 | Add `runtime/research-archive/` to `.gitignore` | deferred |
| 2 | Move any items to `runtime/research-archive/<original-path>/` | deferred |
| 3 | Commit any KEEP items | deferred |
| 4 | Delete any items | deferred |
| 5 | Re-run research validation scripts against the trimmed tree | deferred |

No action taken. This report's role is to record the inventory, the
**retain pending review** posture, and the constraints; the moves,
commits and deletions require your separate explicit authorization per
AGENTS.md §Critical safety.