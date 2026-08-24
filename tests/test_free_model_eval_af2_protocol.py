import json
from pathlib import Path

import pytest

from src.free_model_eval.core import (
    EvalFailure, load_json, normalized_json_output, parse_events,
    sanitize_event_stream, validate_contract_echo, validate_citations_af2,
)
from src.free_model_eval.engine import af2_packet, copy_af2_worker_workspace

ROOT = Path(__file__).resolve().parents[1]
POLICY = load_json(ROOT / "config/free-model-eval/policy.json")
FIXTURE = ROOT / "tests/fixtures/free_model_eval/trace_v1_1"
PACKET = af2_packet(ROOT, "opencode", POLICY["free_models"][0], POLICY)


def event(kind, part):
    return json.dumps({"type": kind, "part": part})


def exact_echo():
    return {"schema_version":"1.0","task_id":PACKET["task_id"],
            "allowed_paths":["README.md","AGENTS.md"],"output_schema_version":"1.0",
            "forbidden_actions_acknowledged":True}


def test_contract_echo_is_exact_and_ordered():
    schema=ROOT/"config/free-model-eval/contract-echo-output.schema.json"
    validate_contract_echo(exact_echo(),PACKET,schema)
    for mutation in ("task", "order", "ack"):
        value=exact_echo()
        if mutation=="task": value["task_id"]="wrong"
        elif mutation=="order": value["allowed_paths"].reverse()
        else: value["forbidden_actions_acknowledged"]=False
        with pytest.raises(EvalFailure): validate_contract_echo(value,PACKET,schema)


def test_directory_and_undeclared_reads_remain_forbidden():
    for path in ("/workspace", "/workspace/expected.json", "/workspace/task-manifest.json"):
        raw="\n".join([event("tool_use",{"tool":"read","state":{"status":"completed","input":{"filePath":path}}}),event("text",{"text":"{\"claims\":[]}"})])
        with pytest.raises(EvalFailure,match="allowlisted"): parse_events(raw,POLICY,PACKET)


def test_worker_workspace_contains_only_manifest_files(tmp_path):
    copy_af2_worker_workspace(ROOT,tmp_path)
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()) == ["AGENTS.md","README.md"]


def test_relative_citations_pass_and_absolute_or_semantic_errors_fail():
    expected=load_json(FIXTURE/"expected.json")
    output={"claims":expected["required_facts"]}
    tools=[{"tool":"read","input":{"filePath":f"/workspace/{name}"}} for name in expected["required_reads"]]
    valid,scores,errors,codes=validate_citations_af2(output,FIXTURE,expected,tools)
    assert valid and not errors and not codes and sum(scores.values())==75
    bad=json.loads(json.dumps(output)); bad["claims"][0]["path"]="/workspace/README.md"
    valid,_,_,codes=validate_citations_af2(bad,FIXTURE,expected,tools)
    assert not valid and "invalid_citation_path" in codes
    bad=json.loads(json.dumps(output)); bad["claims"][0]["line"]="3"
    valid,_,_,codes=validate_citations_af2(bad,FIXTURE,expected,tools)
    assert not valid and "invalid_line_type" in codes
    bad=json.loads(json.dumps(output)); bad["claims"].append(dict(bad["claims"][0]))
    valid,_,_,codes=validate_citations_af2(bad,FIXTURE,expected,tools)
    assert not valid and "duplicate_fact" in codes


def test_normalization_is_narrow_and_fences_are_not_repaired():
    value,original,normalized=normalized_json_output("\ufeff{\"value\":\"e\\u0301\"}")
    assert value=={"value":"é"} and original!=normalized
    with pytest.raises(EvalFailure,match="Markdown"): normalized_json_output("```json\n{}\n```")


def test_diagnostic_sanitizer_rejects_hidden_and_credential_fields():
    payload,digest=sanitize_event_stream(event("text",{"text":"{\"claims\":[]}"}),POLICY)
    assert payload and len(digest)==64
    with pytest.raises(EvalFailure,match="hidden"):
        sanitize_event_stream(json.dumps({"type":"text","reasoning":"secret","part":{"text":"{}"}}),POLICY)
    with pytest.raises(EvalFailure,match="credential"):
        sanitize_event_stream(event("text",{"text":"{\"token\":\"not-a-real-secret\"}"}),POLICY)


def test_recorded_af2_streams_cover_valid_absolute_and_directory_cases():
    recorded=FIXTURE/"recorded"
    output,tools,_,_=parse_events((recorded/"valid-relative.jsonl").read_text(),POLICY,PACKET)
    valid,_,_,_=validate_citations_af2(output,FIXTURE,load_json(FIXTURE/"expected.json"),tools)
    assert valid
    output,tools,_,_=parse_events((recorded/"absolute-citations.jsonl").read_text(),POLICY,PACKET)
    valid,_,_,codes=validate_citations_af2(output,FIXTURE,load_json(FIXTURE/"expected.json"),tools)
    assert not valid and "invalid_citation_path" in codes
    with pytest.raises(EvalFailure,match="allowlisted"):
        parse_events((recorded/"directory-read.jsonl").read_text(),POLICY,PACKET)
