from scripts.check_m2_scaffold_gate import evaluate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_live_gate_is_machine_readable():
    result = evaluate(ROOT)
    assert result["gate"] in {"open", "blocked"}
    assert isinstance(result["reasons"], list)
