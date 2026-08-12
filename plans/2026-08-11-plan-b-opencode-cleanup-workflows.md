# Plan B — OpenCode: safe cleanup and production workflow documentation

> **Status: Historical input.** Useful cleanup evidence was completed, but this is no longer an active execution plan. Repository recovery is governed by [`../roadmap.md`](../roadmap.md) M0 and must remain separate from application implementation.

> Saved from the "Proposed Plan" (Prompts for Kilo Code and OpenCode) on 2026-08-11.
> Execution order position: **Step 2** (OpenCode). Report: `reports/2026-08-11-report-plan-b.md`.

## Objective

Turn the experimental repository into a small, understandable production
workspace with two documented workflows:

1. scans → normalized employee records;
2. employee records → A1 client-confirmation/final forms.

Use subagents for: (1) dependency/reachability analysis; (2) test and command
validation; (3) data/privacy classification; (4) documentation and Mermaid
diagrams; (5) independent final audit. Preserve the dirty worktree and never
overwrite or delete unknown user changes.

This task may clean/archive obsolete files, but must not redesign the future web
application.

## Safety first

- Begin with `git status` and a full inventory.
- Treat scans, identity information, private CSV files and generated PDFs as PII.
- Never print `.env` contents or credentials.
- Never delete files merely because they are untracked.
- Do not delete source scans, current canonical configs, current templates,
  current tests or the latest 11-PDF confirmation package.
- Prefer `archive/` with a manifest over irreversible deletion.
- Do not commit private employee data unless already intentionally tracked.
- Identify concurrent/partial cleanup already present before changing anything.
- Follow the `AGENTS.md` "AI Provider, Model and Cost Policy": free-only external
  model use, no credit purchases, no paid fallbacks; the Codex subscription is
  the only authorized paid AI access and is not reachable from these workflows.
- A litellm gateway may run on the host (owned by other agents/projects); do not
  fix, restart or reconfigure it. Use Context7 MCP for up-to-date library/provider
  docs where configured; otherwise official docs with recorded URL + access date.

## Current problem to resolve

The repository presently appears internally inconsistent:

- `scripts/generate_provisional_a1.py` imports `finalize_a1`;
- active `scripts/finalize_a1.py` may have been moved into `archive/2026-08-11/`;
- `scripts/a1_form_generator.py` looks like an older competing generator;
- `scripts/build_clean_background.py` and the actual active background generation
  need comparison;
- many prior scripts/docs are deleted from their old locations but copied to `archive/`;
- numerous timestamped `output/provisional.backup-*` directories exist;
- old generated PDF directories coexist with the newer provisional workflow.

Do not assume the partial cleanup is correct. Establish the actual executable
dependency graph and repair the canonical workflow.

## Phase 1 — Inventory and classification

Build a machine-readable inventory containing:
`path,type,tracked,generated,contains_pii,referenced_by,classification,
recommended_action,reason`.

Classifications: `production-runtime`, `production-config`,
`production-template`, `production-test`, `private-input`, `generated-current`,
`generated-obsolete`, `documentation-current`, `experimental`, `archived`,
`unknown/manual-review`.

Determine reachability from the two canonical entry points. Execute commands in
a temporary output directory where possible.

## Phase 2 — Canonicalize without losing history

- Select one A1 core/renderer and one generation entry point.
- Eliminate broken imports.
- Remove or archive competing generators only after proving they are unused.
- Keep one clean-background builder if regeneration is required.
- Keep one render/visual-review utility.
- Keep focused tests that exercise the selected production path.
- Archive experiments, debug PDFs, screenshots, temporary overlays, stale reports
  and obsolete generated forms under a dated archive.
- Create `archive/MANIFEST.md` explaining every archived group and its former use.
- Consolidate or remove timestamped provisional backups after preserving the
  latest relevant version and recording hashes.
- Ensure `.gitignore` clearly separates private inputs, generated outputs, review
  images, caches and distributable templates.
- Do not leave imports that depend on archived modules.

## Phase 3 — Current-state map

Create a concise current-state document containing:

- canonical commands;
- canonical source/config/template files;
- generated outputs;
- private inputs;
- archived components;
- known broken or provisional behaviour;
- authoritative vs placeholder data boundaries;
- dependency graph;
- test status.

Every claim must be verified from code or execution.

## Phase 4 — Required operational documentation

Create exactly:

1. `readme-scan-to-employees.md`
2. `readme-employees-to-a1-form.md`

Each document must include: purpose and intended operator; prerequisites and
dependencies; inputs and outputs; exact commands; configuration; step-by-step
data flow; validation and tests; errors/log locations; privacy/security
handling; authoritative vs inferred vs placeholder fields; known gaps;
rollback/recovery; related files and folders with their meaning; Mermaid
flowchart; Mermaid sequence diagram where useful; troubleshooting table; example
using synthetic data only.

`readme-scan-to-employees.md` must explain: scan discovery; OP/ZP
classification; local OCR versus optional OpenRouter OCR; only free models
verified as zero-cost at execution time (for OpenRouter, model IDs ending
exactly `:free`, or an explicitly free router whose returned model is verified
zero-cost; other providers only after verifying official pricing/API metadata);
never purchasing credits, enabling billing or using a paid fallback on rate
limits/429s; deferring work when no free provider is available; API error
logging without key leakage; OCR output quality
classification; normalization and human correction; provenance from scan to
field; duplicate/conflict handling; manual-review gate; how a normalized
employee record becomes eligible for downstream use.

`readme-employees-to-a1-form.md` must explain: normalized employee/review inputs;
OSSZ resolution by exact residence; institution profiles and provenance;
placeholder client-confirmation configuration; Czech display casing; 3.4 and
4.1.2 checkbox policy; DE, CZ activity location; per-person Monday/Thursday
provisional date rule; inclusive one-year validity; unique placeholder
certificate IDs versus OSSZ-issued IDs; bitmap cleanup and overlay rendering;
visual QA loop; manifest/hashes/checklists; difference between
`output/provisional` and authoritative `output/final`.

## Phase 5 — Acceptance

- Both documented workflows run from a clean checkout with documented setup.
- No canonical script imports archived or missing modules.
- Focused tests pass.
- Full test discovery is reported honestly.
- Mermaid diagrams render syntactically.
- No secrets or raw PII appear in new documentation.
- Every retained top-level script has a documented purpose.
- Every archived group appears in `archive/MANIFEST.md`.
- Produce `CLEANUP_REPORT.md` with: retained files; archived files; deleted
  generated duplicates; repaired dependencies; commands/tests executed;
  remaining risks; exact clean git status summary.

Do not start frontend/backend implementation in this task.
