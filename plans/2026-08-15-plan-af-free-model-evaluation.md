# Plan AF — Bounded Codex-Led Free-Model Evaluation

**Status:** active
**Priority:** Parallel tooling evidence for Plan L
**Milestone:** M0–M1A
**Owner:** primary agent; Codex owns integration and acceptance

## Objective

Evaluate `opencode/hy3-free` and `opencode/deepseek-v4-flash-free` against an
ephemeral `gpt-5.6-luna` control on three synthetic task classes. Free-model
output is provisional; the harness and Codex independently enforce evidence,
permissions, workspace integrity, tests, scoring, and promotion.

## Boundaries

- Public/synthetic fixtures only. Never expose employee, A1, invoice, credential,
  protected runtime, production, or quarantined research content.
- Workers see a minimal copied workspace, never the repository or its `.git`.
- OpenCode runs through its underlying binary with a single-provider credential
  capsule, `--pure`, default-deny agents, and Bubblewrap filesystem isolation.
- LiteLLM, random routers, paid fallback, Git publication, production, live
  capture, portal/database work, and skill activation are excluded.
- Runtime workspaces and raw receipts live only under ignored
  `runtime/free-model-eval/`.

## Phases and gates

1. Freeze schemas, policy, fixtures, expected truth, and negative cases.
2. Prove the offline parser, citation validator, isolation builder, scoring, and
   worktree snapshots without provider calls or credential reads.
3. Refresh and validate exact zero-cost OpenCode metadata; unavailable or
   ambiguous infrastructure exits `2`.
4. Run one safe trace smoke per free model, then the 27-run matrix only if smoke
   gates pass. Policy failures exit `1` without retry; transient failures retry
   once then remain `unproven`.
5. Codex reviews receipts and records promotion separately for trace, review,
   and code-draft work. No autonomous integration worker is created.

## Acceptance

```bash
venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py -q
venv/bin/python scripts/run_free_model_eval.py verify-fixtures --policy config/free-model-eval/policy.json
venv/bin/python scripts/run_free_model_eval.py preflight --policy config/free-model-eval/policy.json --output runtime/free-model-eval/preflight.json
```

Plan L and Plan M remain active regardless of this experiment. Plan AF evidence
may close only the bounded free-worker question; it cannot accept the operating
model, cockpit, product architecture, or any protected-data activation.

## Execution result — 2026-08-15

- Offline harness gates pass and exact zero-cost preflight passed for both named
  models (`hy3-free` 190K/64K; `deepseek-v4-flash-free` 200K/128K).
- The final trace smoke rejected Hy3 for failing the exact fact/citation contract
  despite reading only the two permitted files.
- The final trace smoke rejected DeepSeek before scoring because it attempted to
  read `/workspace`, which is outside the packet's two exact read paths.
- Both receipts report zero free-model cost and no repository mutation. The
  27-run matrix and Codex control were not run because both free-model smoke gates
  did not pass.
- No model or task class is promoted. A successor experiment must change its
  packet/agent design explicitly and may not reinterpret these failures as
  environmental success.
- The accepted successor is [Plan AF2](2026-08-15-plan-af2-free-model-trace-repair.md),
  which adds an exact manifest and contract echo while preserving the original
  AF evidence and every safety gate.

## Rollback

Revert Plan AF tracked files together. Delete only a resolved child of
`runtime/free-model-eval/runs/` after containment validation. Never use Git
clean/reset/checkout, mutate quarantined artifacts, or remove credential sources.
