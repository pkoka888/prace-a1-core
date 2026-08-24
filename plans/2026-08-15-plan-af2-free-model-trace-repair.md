# Plan AF2 — Exact-Manifest Trace Protocol Repair

**Status:** blocked — invalid live attempt requires Plan AF2.1
**Priority:** parallel tooling evidence for Plan L
**Owner:** primary agent; Codex integrates and accepts

## Objective

Determine whether Plan AF's Hy3 and DeepSeek trace failures are repairable by
an exact task manifest and schema-constrained protocol without weakening any
privacy, zero-cost, path, citation, isolation, or mutation gate.

## Protocol

Each free candidate must first pass a no-tool contract echo containing the exact
task ID, ordered paths, output schema version, and forbidden-action
acknowledgement. It then receives a prompt-supplied hash manifest and may read
only `README.md` and `AGENTS.md` individually. `/workspace` discovery, list,
glob, grep, shell, web, MCP, skills, subagents, and external directories remain
forbidden. Only BOM removal, Unicode NFC, and insignificant JSON whitespace are
normalized.

AF2 is trace-only. Hy3 and DeepSeek remain the only free candidates. Codex Luna
runs only after one free smoke passes. Review/code tasks, a third model,
LiteLLM, protected data, production, Git publication, and skill activation are
excluded.

## Gates

```bash
venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py tests/test_free_model_eval_af2_protocol.py -q
venv/bin/python scripts/run_free_model_eval.py verify-fixtures --policy config/free-model-eval/policy.json
venv/bin/python scripts/run_free_model_eval.py preflight --policy config/free-model-eval/policy.json --output runtime/free-model-eval/af2/preflight.json
```

The live `run-af2` command is Goal-mode work. A model is a bounded trace
candidate only after three clean runs; any policy or semantic failure stops that
model, while one transient transport retry is allowed and recorded separately.

The 2026-08-15 attempt produced no valid model evidence because the sanitizer
rejected legitimate token-usage metadata. See
[Plan AF2.1](2026-08-15-plan-af2.1-evidence-integrity-repair.md) and the
[review report](../docs/research/2026-08-15-af2-free-model-trace-review-report.md).

## Rollback

Revert AF2 schemas, harness, fixtures, tests, and planning metadata together.
Remove only an exact resolved child of `runtime/free-model-eval/af2/`. Never
touch historical AF evidence, quarantined paths, protected data, or Git state.
