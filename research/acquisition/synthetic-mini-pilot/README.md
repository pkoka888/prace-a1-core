# Synthetic collector mini-pilot

This package is entirely synthetic and must never be presented as market
evidence. It uses no network, model, private data, or real product assertion.
The runner expands 23 lane-level fixture decisions over the frozen 10+10 Plan
AC v1.1 roster into exactly 230 typed inspections.

## Canonical run

`synthetic-mini-v2` is the canonical reproducible run. The former v1 request,
fixture files, capture tree, execution, and prompt/config fixtures remain an
unaltered historical snapshot; they are not inputs to v2 and are excluded from
the canonical artifact inventory.

From a clean project-shaped root containing the files inventoried by
`manifest.json`, generate and verify v2 with:

```bash
venv/bin/python scripts/run_collector_fixture.py \
  --root . \
  --run-id synthetic-mini-v2 \
  --output research/acquisition/synthetic-mini-pilot/runs/synthetic-mini-v2/execution.json

venv/bin/python scripts/validate_collector_execution.py \
  --root . \
  --input research/acquisition/synthetic-mini-pilot/runs/synthetic-mini-v2/execution.json \
  --json

venv/bin/python scripts/evaluate_research_field_fixtures.py \
  --root . \
  --output research/processed/field-replay.json

venv/bin/python scripts/evaluate_research_field_fixtures.py \
  --root . \
  --output research/processed/field-replay.json \
  --check
```

The first command creates both the immutable fixture capture under
`research/acquisition/source-captures/synthetic-mini-v2/` and the collector
execution. All commands must exit `0`. `synthetic_fixture_verified` proves only
the deterministic fixture pipeline and typed bindings; it does not verify a
market claim or replace operator review.

## Manifest policy

`manifest.json` directly inventories every canonical durable v2 input and
output, including the capture manifest and every excerpt. Its `inventory_roots`
define directories that must contain no undeclared files. The manifest cannot
hash itself without a recursive fixed-point problem, so `self_policy` excludes
only its own path. The integration test recalculates every declared SHA-256,
checks the exact path set under those roots, then regenerates the entire run in
a temporary clean-room root.
