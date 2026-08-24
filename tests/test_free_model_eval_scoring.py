from pathlib import Path

from src.free_model_eval.core import score_review, score_total, validate_citations

ROOT=Path(__file__).resolve().parents[1]


def test_trace_citations_require_real_lines_and_observed_reads():
    workspace=ROOT/"tests/fixtures/free_model_eval/trace"
    expected=__import__('json').loads((workspace/"expected.json").read_text())
    output={"claims":expected["required_facts"]}
    tools=[{"tool":"read","input":{"filePath":f"/workspace/{p}"}} for p in expected["required_reads"]]
    valid,scores,errors=validate_citations(output,workspace,expected,tools)
    assert valid and not errors and sum(scores.values())==75
    output["claims"][0]["line"]=126
    valid,_,errors=validate_citations(output,workspace,expected,tools)
    assert not valid and any("invalid citation" in e for e in errors)


def test_review_and_code_threshold_components():
    output={"findings":[{"id":"off-by-one","evidence":"< instead of <=","repair":"restore <="},{"id":"unsafe-path-prefix","evidence":"string prefix","repair":"use is_relative_to"}]}
    expected={"required_findings":["off-by-one","unsafe-path-prefix"],"max_false_positives":1}
    scores,errors=score_review(output,expected)
    assert not errors and sum(scores.values())==80
    assert score_total("review",scores,schema_ok=True,tool_ok=True,acceptance=True,scope_ok=True)==90
    assert score_total("code_draft",{},schema_ok=True,tool_ok=True,acceptance=True,scope_ok=True)==85
