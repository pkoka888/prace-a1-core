from pathlib import Path

import pytest

from src.free_model_eval.core import EvalFailure, load_json, parse_verbose_models, sanitized_preflight

ROOT=Path(__file__).resolve().parents[1]
POLICY=load_json(ROOT/"config/free-model-eval/policy.json")


def metadata(model,cost=0):
    return {"id":model.split("/",1)[1],"providerID":"opencode","status":"active","cost":{"input":cost,"output":0,"cache":{"read":0,"write":0}},"limit":{"context":200000,"output":64000},"capabilities":{"toolcall":True}}


def test_verbose_parser_and_zero_cost_gate():
    text="\n".join(f"{model}\n"+__import__('json').dumps(metadata(model),indent=2) for model in POLICY["free_models"])
    report=sanitized_preflight(parse_verbose_models(text),POLICY)
    assert set(report["models"])==set(POLICY["free_models"])
    assert len(report["metadata_hash"])==64


def test_paid_and_random_or_missing_models_fail_closed():
    models={model:metadata(model) for model in POLICY["free_models"]}
    models[POLICY["free_models"][0]]["cost"]["input"]=0.1
    with pytest.raises(EvalFailure,match="price"): sanitized_preflight(models,POLICY)
