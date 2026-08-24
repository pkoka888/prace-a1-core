# Free Model Evaluation Workflow (WF-AF)

## Overview

WF-AF evaluates free-tier models (`opencode/hy3-free`, `opencode/deepseek-v4-flash-free`) against synthetic task classes using an isolated Bubblewrap workspace. The harness enforces evidence, permissions, workspace integrity, tests, and scoring without autonomous promotion. **No paid APIs, no live capture, no production data.**

**Status:** experimental — initial trace smoke rejected both free models; successor Plan AF2 is active.

---

## File Map

| File | Purpose |
|------|---------|
| `scripts/run_free_model_eval.py` | Canonical evaluation engine. Subcommands: `verify-fixtures`, `preflight`, `run`. |
| `scripts/run_collector_proposals.py` | Builds non-authoritative collector execution from frozen capture decisions. Exit 2 always (proposal only). |
| `scripts/run_collector_proposals_v12.py` | Creates capture-bound v1.2 proposal scaffold from v1.1 capture contract + v1.0 normalization rules. |
| `scripts/run_collector_fixture.py` | Runs canonical synthetic Plan AC collector mini-pilot. Produces immutable artifacts; not market evidence. |

---

## Evaluation Phases

### Phase 1 — Schema & Policy Freeze
- Freeze schemas, policy, fixtures, expected truth, and negative cases

### Phase 2 — Offline Harness Proof
- Prove parser, citation validator, isolation builder, scoring, and worktree snapshots **without provider calls or credential reads**

### Phase 3 — Preflight (Zero-Cost)
- Validate exact zero-cost OpenCode metadata; unavailable infrastructure exits `2`

### Phase 4 — Trace Smoke
- One safe trace per free model; proceed to full matrix only if smoke gates pass
- Policy failures exit `1` without retry; transient failures retry once then `unproven`

### Phase 5 — Full Matrix (27 runs)
- Run only after smoke gates pass; Codex reviews receipts separately for trace, review, and code-draft work

---

## Key Constraints

- **Public/synthetic fixtures only** — never employee, A1, invoice, credential, or quarantined research content
- **Workers see minimal copied workspace** — never the repository or `.git`
- **Single-provider credential capsule** with `--pure`, default-deny agents, Bubblewrap isolation
- **No LiteLLM, random routers, paid fallback, Git publication, production, or live capture**
- Receipts and workspaces live only under ignored `runtime/free-model-eval/`

---

## Quick Reference

```bash
# Verify fixtures and policy
venv/bin/python scripts/run_free_model_eval.py verify-fixtures --policy config/free-model-eval/policy.json

# Preflight check (zero-cost)
venv/bin/python scripts/run_free_model_eval.py preflight --policy config/free-model-eval/policy.json --output runtime/free-model-eval/preflight.json

# Run evaluation
venv/bin/python scripts/run_free_model_eval.py run --policy config/free-model-eval/policy.json --models hy3-free deepseek-v4-flash-free --repetitions 3 --output runtime/free-model-eval/run-001/

# Contract tests
venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py -q
```
