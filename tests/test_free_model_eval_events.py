import json
from pathlib import Path

import pytest

from src.free_model_eval.core import EvalFailure, load_json, packet_for, parse_events

ROOT = Path(__file__).resolve().parents[1]
POLICY = load_json(ROOT / "config/free-model-eval/policy.json")
PACKET = packet_for(ROOT, "trace", "opencode", POLICY["free_models"][0], POLICY)


def line(event): return json.dumps(event)


def test_parses_one_final_and_observed_read():
    raw = "\n".join([
        line({"type":"tool_use","part":{"tool":"read","state":{"status":"completed","input":{"filePath":"/workspace/README.md"}}}}),
        line({"type":"text","part":{"text":json.dumps({"claims":[]})}}),
    ])
    output, tools, _, cost = parse_events(raw, POLICY, PACKET)
    assert output == {"claims": []}; assert tools[0]["tool"] == "read"; assert cost is None


def test_negative_event_cases():
    cases = [
        ("not-json", "malformed"),
        (line({"type":"text","part":{"text":"```json\n{}\n```"}}), "Markdown"),
        (line({"type":"tool_use","part":{"tool":"bash","state":{"input":{}}}}) + "\n" + line({"type":"text","part":{"text":"{}"}}), "unauthorized"),
        (line({"type":"tool_use","part":{"tool":"read","state":{"status":"completed","input":{"filePath":"/workspace/a1/review.csv"}}}}) + "\n" + line({"type":"text","part":{"text":"{}"}}), "forbidden"),
        (line({"type":"tool_use","part":{"tool":"read","state":{"status":"completed","input":{"filePath":"/workspace/expected.json"}}}}) + "\n" + line({"type":"text","part":{"text":"{}"}}), "allowlisted"),
    ]
    for raw, match in cases:
        with pytest.raises(EvalFailure, match=match): parse_events(raw, POLICY, PACKET)
