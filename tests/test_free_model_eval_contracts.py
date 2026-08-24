import json
from pathlib import Path

import pytest

from src.free_model_eval.core import EvalFailure, load_json, packet_for, validate_packet, validate_schema
from src.free_model_eval.engine import verify_fixtures

ROOT = Path(__file__).resolve().parents[1]
POLICY = load_json(ROOT / "config/free-model-eval/policy.json")


def test_fixtures_and_packets_are_valid_and_hash_bound():
    result = verify_fixtures(ROOT, POLICY)
    assert set(result["fixtures"]) == {"trace", "review", "code_draft", "trace_v1_1"}
    assert all(len(value) == 64 for value in result["fixtures"].values())


def test_protected_path_and_unapproved_model_fail_closed():
    schema = ROOT / "config/free-model-eval/free-model-task-packet.schema.json"
    packet = packet_for(ROOT, "trace", "opencode", POLICY["free_models"][0], POLICY)
    packet["allowed_paths"].append("a1/review.csv")
    with pytest.raises(EvalFailure, match="protected"):
        validate_packet(packet, schema, POLICY)
    packet = packet_for(ROOT, "trace", "opencode", "openrouter/free", POLICY)
    with pytest.raises(EvalFailure, match="allowlisted"):
        validate_packet(packet, schema, POLICY)


def test_receipt_schema_rejects_secret_or_missing_contract_fields():
    schema = ROOT / "config/free-model-eval/free-model-receipt.schema.json"
    with pytest.raises(EvalFailure):
        validate_schema({"schema_version": "1.0", "secret": "sk-synthetic-not-real"}, schema)
