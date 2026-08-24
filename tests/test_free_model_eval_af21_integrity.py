import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.free_model_eval.core import (
    CommandResult, EvalFailure, EvalUnproven, load_json, packet_for, parse_events,
    sanitize_event_stream, sha256_bytes,
)
from src.free_model_eval.engine import (
    _codex_events, _write_af2_diagnostics, af2_packet, run_af2_one,
    validate_af2_run,
)

ROOT=Path(__file__).resolve().parents[1]
POLICY=load_json(ROOT/"config/free-model-eval/policy.json")
PACKET=packet_for(ROOT,"trace","opencode",POLICY["free_models"][0],POLICY)
EMPTY=sha256_bytes(b"")


def line(value): return json.dumps(value)


def test_real_shaped_token_usage_is_safe_but_real_secret_shapes_fail():
    stream="\n".join([
        line({"type":"step_start","part":{}}),
        line({"type":"step_finish","part":{"tokens":{"input":74,"output":125,"reasoning":412,"total":1571,"cache":{"read":960,"write":0}},"cost":0.0}}),
        line({"type":"text","part":{"text":"{\"claims\":[]}"}}),
    ])
    payload,digest=sanitize_event_stream(stream,POLICY)
    assert b'"tokens"' in payload and len(digest)==64
    for text,rule in [('{"token":"synthetic-value"}',"secret-key-name"),
                      ('Bearer abcdefghijklmnop',"secret-value-shape"),
                      ('sk-synthetic123456',"secret-value-shape")]:
        with pytest.raises(EvalFailure,match=rule):
            sanitize_event_stream(line({"type":"text","part":{"text":text}}),POLICY)
    for benign in ('{"tokens":123}', '{"token_count":2}', '{"public_key":"fixture"}'):
        sanitize_event_stream(line({"type":"text","part":{"text":benign}}),POLICY)


def test_event_parser_rejects_null_parts_and_classifies_provider_errors():
    with pytest.raises(EvalFailure,match="part must be an object"):
        parse_events(line({"type":"text","part":None}),POLICY,PACKET)
    with pytest.raises(EvalUnproven,match="429"):
        parse_events(line({"type":"error","part":{"status":429,"message":"rate limited"}}),POLICY,PACKET)
    with pytest.raises(EvalFailure,match="provider error"):
        parse_events(line({"type":"error","part":{"status":400,"message":"bad request"}}),POLICY,PACKET)


def test_diagnostic_hash_is_hash_of_retained_sanitized_artifact(tmp_path):
    raw="\n".join([
        line({"type":"step_finish","part":{"tokens":{"total":2},"cost":0}}),
        line({"type":"text","part":{"text":"{\"claims\":[]}"}}),
    ])
    event_hash,output_hash=_write_af2_diagnostics(tmp_path,raw,{"claims":[]},POLICY)
    assert event_hash==sha256_bytes((tmp_path/"events.jsonl").read_bytes())
    assert output_hash==sha256_bytes((tmp_path/"final-output.json").read_bytes())


SYNTHETIC_CODEX = ROOT / "tests/fixtures/free_model_eval/trace_v1_1/synthetic-codex"


def synthetic_codex(name):
    return (SYNTHETIC_CODEX / name).read_text(encoding="utf-8")


def test_codex_adapter_accepts_only_source_shaped_pure_reads():
    packet = packet_for(ROOT, "trace", "codex", "gpt-5.6-luna", POLICY)
    for name in ("valid-sed-reads.jsonl", "valid-cat-reads.jsonl"):
        output, tools, tokens, cost = _codex_events(synthetic_codex(name), packet)
        assert output == {"claims": [
            {"fact": "planning-only", "path": "README.md", "line": 3, "quote": "planning-only synthetic fixture"},
            {"fact": "portal-not-implemented", "path": "README.md", "line": 4, "quote": "No production portal is implemented"},
            {"fact": "synthetic-only", "path": "AGENTS.md", "line": 3, "quote": "Use only fictional records"}]}
        assert {x["input"]["filePath"] for x in tools} == {"/workspace/README.md", "/workspace/AGENTS.md"}
        assert all(x["status"] == "completed" for x in tools)
        assert tokens and tokens.get("output_tokens", 0) > 0
        assert cost is None
    assert "Never persisted" not in json.dumps(output)


@pytest.mark.parametrize("name", sorted(path.name for path in SYNTHETIC_CODEX.glob("reject-*.jsonl")))
def test_codex_adapter_rejects_source_shaped_unsafe_or_unexpected_events(name):
    packet = packet_for(ROOT, "trace", "codex", "gpt-5.6-luna", POLICY)
    with pytest.raises(EvalFailure):
        _codex_events(synthetic_codex(name), packet)


def test_codex_adapter_negative_fixture_coverage_is_pinned():
    negative = sorted(path.name for path in SYNTHETIC_CODEX.glob("reject-*.jsonl"))
    assert len(negative) == 26
    for required in ("reject-unsafe-item-started.jsonl", "reject-changed-command-on-update.jsonl",
                     "reject-changed-command-on-completion.jsonl", "reject-duplicate-terminal.jsonl",
                     "reject-missing-completion.jsonl", "reject-completion-without-start.jsonl",
                     "reject-duplicate-start.jsonl"):
        assert required in negative


def test_codex_adapter_rejects_malformed_or_non_object_events():
    packet = packet_for(ROOT, "trace", "codex", "gpt-5.6-luna", POLICY)
    with pytest.raises(EvalFailure, match="malformed"):
        _codex_events('{"type":"thread.started","thread_id":"x"}\nnot-json\n', packet)
    with pytest.raises(EvalFailure, match="must be an object"):
        _codex_events('{"type":"thread.started"}\n["a", "b"]\n', packet)
    with pytest.raises(EvalFailure, match="exactly one Codex final text"):
        _codex_events('{"type":"thread.started","thread_id":"x"}\n{"type":"turn.completed","usage":{}}\n', packet)


def receipt(model,runner,repetition):
    return {"schema_version":"1.0","protocol_version":"1.1","repetition":repetition,"attempt":1,
      "task_id":f"trace-{runner}-{model}","task_class":"trace","runner":runner,"requested_model":model,
      "reported_model":model,"reported_provider":"opencode" if runner=="opencode" else "openai-codex",
      "packet_hash":EMPTY,"fixture_hash":EMPTY,"metadata_hash":EMPTY,"started_at":"2026-08-15T00:00:00Z",
      "finished_at":"2026-08-15T00:00:01Z","duration_ms":1,"event_hash":EMPTY,"tool_events":[],
      "tokens":{},"reported_cost":0,"process_exit":0,"timed_out":False,"output_valid":True,
      "citations_valid":True,"workspace_before":EMPTY,"workspace_after":EMPTY,"repository_before":EMPTY,
      "repository_after":EMPTY,"acceptance_passed":True,"hard_gates":{"all":True},"scores":{"trace":90},
      "total_score":90,"disposition":"candidate","errors":[],"next_action":"Codex review"}


def test_validation_requires_luna_after_a_free_candidate(tmp_path):
    directory=tmp_path/"receipts"; directory.mkdir()
    for rep in (1,2,3):
        (directory/f"free-{rep}.json").write_text(json.dumps(receipt(POLICY["free_models"][0],"opencode",rep)))
    result,status=validate_af2_run(ROOT,tmp_path)
    assert status==2 and result["free_candidate_proven"] and not result["control_promoted"]
    for rep in (1,2,3):
        (directory/f"luna-{rep}.json").write_text(json.dumps(receipt("gpt-5.6-luna","codex",rep)))
    result,status=validate_af2_run(ROOT,tmp_path)
    assert status==0 and result["control_promoted"]


def test_run_af21_one_retains_hash_bound_echo_and_trace_evidence(monkeypatch,tmp_path):
    packet=af2_packet(ROOT,"opencode",POLICY["free_models"][0],POLICY)
    echo={"schema_version":"1.0","task_id":packet["task_id"],"allowed_paths":packet["allowed_paths"],
          "output_schema_version":"1.0","forbidden_actions_acknowledged":True}
    expected=packet["expected_evidence"]
    trace={"claims":expected["required_facts"]}
    def stream(output,reads=()):
        events=[{"type":"step_start","part":{}}]
        events += [{"type":"tool_use","part":{"tool":"read","state":{"status":"completed","input":{"filePath":f"/workspace/{path}"}}}} for path in reads]
        events += [{"type":"step_finish","part":{"tokens":{"input":10,"output":5,"total":15},"cost":0}},
                   {"type":"text","part":{"text":json.dumps(output)}}]
        return "\n".join(map(json.dumps,events))
    def fake_run(root,policy,run_root,workspace,agent_name,model,prompt,timeout):
        raw=stream(echo) if agent_name=="free-eval-contract-echo" else stream(trace,("README.md","AGENTS.md"))
        return CommandResult(0,raw,"",False,1)
    monkeypatch.setattr("src.free_model_eval.engine._run_opencode_af2",fake_run)
    run_root=tmp_path/"run"
    receipt,status=run_af2_one(ROOT,POLICY,{"metadata_hash":EMPTY},"opencode",POLICY["free_models"][0],1,run_root)
    assert status==0 and receipt["disposition"]=="candidate"
    assert receipt["contract_echo"]["diagnostic_retained"]
    assert receipt["event_hash"]==receipt["sanitized_event_artifact_hash"]
    event_file=next(path for path in (run_root/"diagnostics").glob("af2-trace-*/events.jsonl") if not path.parent.name.endswith("-echo"))
    assert receipt["event_hash"]==sha256_bytes(event_file.read_bytes())


def test_af21_cli_rejects_non_immutable_runtime_path_before_preflight():
    proc=subprocess.run([sys.executable,str(ROOT/"scripts/run_free_model_eval.py"),"run-af21",
        "--policy","config/free-model-eval/policy.json","--models",*POLICY["free_models"],
        "--output","runtime/free-model-eval/af2.1/latest"],cwd=ROOT,capture_output=True,text=True)
    assert proc.returncode==1 and "named direct child" in proc.stdout
