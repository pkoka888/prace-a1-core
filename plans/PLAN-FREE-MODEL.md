# Plan PLAN-FREE-MODEL — Bounded Codex-Led Free-Model Evaluation, Trace Repair, and Capsule Isolation

**Status**: active
**Milestone**: M0–M1A

## Purpose

Single governing plan for the synthetic-only bounded evaluation of named free
OpenCode models with Codex control and deterministic safety gates: the initial
evaluation, the exact-manifest trace protocol repair, the evidence-integrity
repair, and the Luna exact-read adapter with capsule isolation.

Replaces and consolidates the dated plans:

- `plans/2026-08-15-plan-af-free-model-evaluation.md`
- `plans/2026-08-15-plan-af2-free-model-trace-repair.md`
- `plans/2026-08-15-plan-af2.1-evidence-integrity-repair.md`
- `plans/2026-08-16-plan-af2.2-luna-capsule-isolation.md`

The archive of the individual dated plans lives under `.archive/plans/`; the
tracked source of truth is this file plus [`plans/INDEX.md`](INDEX.md).

## Status and governance

- Status: `active` — offline synthetic harness work continues; no live run until
  the offline tests, fixtures, and containment gates are green.
- Decision state: `prototype-required`; evidence: `synthetic-tested`.
- Only free-tier endpoints are authorized; the model ID must end with `:free`
  and zero cost must be verified before any live call. On 429/quota exhaustion,
  defer — never fall back to a paid model.

## Dependency (catalog-recorded)

- `PLAN-INFRA` with gate `evidence-only` — Plan operating rules bound the
  evaluation; this plan cannot accept PLAN-INFRA or activate a skill.

## Contents and exit evidence

- **Exact-manifest traces:** three exact-read, no-command synthetic receipts per
  passing candidate with sanitized diagnostics and independently reviewed
  receipts.
- **Evidence integrity:** green offline integrity tests, full suite, planning
  and package gates, and an exact zero-cost compatibility preflight.
- **Luna capsule isolation:** Bubblewrap capsule exposes only the synthetic
  workspace with `README.md`/`AGENTS.md` plus the output schema; host, repo,
  Git, MCP, plugins, skills, and external writable dirs are unreachable. Only
  strictly parsed, completed read-only `command_execution` items on allowlisted
  exact relative paths become read evidence.
- Policy/config: [`config/free-model-eval/policy.json`](../config/free-model-eval/policy.json).

Exit evidence: three repeated synthetic trace/review/code-draft runs per
model/control with validated receipts and task-class dispositions; no model
promoted and no skill activated.