# Plan PLAN-HISTORY — Superseded and Historical Plans Archive

**Status**: historical
**Milestone**: historical

## Purpose

Single archive-style reference for the superseded and historical planning
documents that have no further active execution. It exists so the governance
surface (catalog, INDEX, dependency graph, validator) has one stable node for
"read-only history" instead of many.

Replaces and consolidates the dated plans:

- `plans/2026-08-11-consolidated-roadmap.md`
- `plans/2026-08-11-plan-b-opencode-cleanup-workflows.md`
- `plans/2026-08-11-plan-c-opencode-research.md`
- `plans/2026-08-12-plan-d-product-research-and-deployment.md`

The individual dated files are preserved under `.archive/plans/` and remain
available from git history; they are context only and are never executed.
PII-bearing outputs are never moved into a tracked archive.

## Status and governance

- Status: `historical`; decision state: `not-applicable`; evidence: `none`.
- Executable: **no**; successor: `PLAN-INFRA` (the consolidated active plan set
  that inherits any still-relevant context from the dated files).
- This node is intentionally a leaf: it has no dependencies and is excluded from
  active queues and dependency paths.

Exit evidence: historical context only — no execution, no promotion, no
re-activation without a new explicit plan and separate operator approval.