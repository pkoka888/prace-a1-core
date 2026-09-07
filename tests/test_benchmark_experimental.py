from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/fixtures/benchmark-experimental"
VALIDATOR = "validate_and_score.py"
RUNNER = "run_project_skill.py"


@pytest.fixture()
def benchmark(tmp_path: Path) -> Path:
    target = tmp_path / "benchmark-experimental"
    shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def run(script: str, bench: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(bench / script), *args, "--benchmark-dir", str(bench)],
        text=True,
        capture_output=True,
        check=False,
    )


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_canonical_draft_is_structurally_valid_but_unproven(benchmark: Path) -> None:
    result = run(VALIDATOR, benchmark)
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["errors"] == []
    assert payload["status"] == "unproven"


def test_public_questions_are_exact_and_have_no_embedded_gold() -> None:
    corpus = json.loads((SOURCE / "questions.json").read_text(encoding="utf-8"))
    assert len(corpus["public_questions"]) == 18
    assert len({q["id"] for q in corpus["public_questions"]}) == 18
    assert all(not ({"gold_answer", "answer", "atomic_claims", "evidence_refs"} & q.keys()) for q in corpus["public_questions"])


def test_embedded_gold_is_rejected(benchmark: Path) -> None:
    path = benchmark / "questions.json"
    corpus = json.loads(path.read_text(encoding="utf-8"))
    corpus["public_questions"][0]["gold_answer"] = {"answer": "leak"}
    write(path, corpus)
    result = run(VALIDATOR, benchmark)
    assert result.returncode == 1
    assert "gold_answer" in result.stdout or "embeds gold" in result.stdout


def test_extra_gold_answer_is_rejected(benchmark: Path) -> None:
    path = benchmark / "gold-answers/merged-answers.json"
    gold = json.loads(path.read_text(encoding="utf-8"))
    gold["answers"]["q-extra"] = {"atomic_claims": [{"claim_id": "c-extra", "value": "x"}], "evidence": []}
    write(path, gold)
    result = run(VALIDATOR, benchmark)
    assert result.returncode == 1
    assert "extra=['q-extra']" in result.stdout


def test_duplicate_public_id_is_rejected(benchmark: Path) -> None:
    path = benchmark / "questions.json"
    corpus = json.loads(path.read_text(encoding="utf-8"))
    corpus["public_questions"][1]["id"] = corpus["public_questions"][0]["id"]
    write(path, corpus)
    assert run(VALIDATOR, benchmark).returncode == 1


def test_status_flip_cannot_bypass_missing_external_evidence(benchmark: Path) -> None:
    path = benchmark / "STATUS.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["status"] = "scoring-ready"
    write(path, state)
    result = run(VALIDATOR, benchmark)
    assert result.returncode == 1
    assert "contradicts incomplete" in result.stdout


def test_invalid_date_is_rejected_by_format_checker(benchmark: Path) -> None:
    path = benchmark / "questions.json"
    corpus = json.loads(path.read_text(encoding="utf-8"))
    corpus["cutoff_date"] = "2026-99-77"
    write(path, corpus)
    result = run(VALIDATOR, benchmark)
    assert result.returncode == 1
    assert "date" in result.stdout


def test_dangling_and_extra_evidence_is_rejected(benchmark: Path) -> None:
    raw = benchmark / "evidence/raw"
    raw.mkdir(parents=True, exist_ok=True)
    write(raw / "extra.json", {
        "evidence_id": "ev-extra", "question_id": "q-does-not-exist", "claim_ids": ["c-does-not-exist"],
        "source_url": "https://example.invalid/source", "final_url": "https://example.invalid/source",
        "retrieved_at": "2026-08-14T00:00:00Z", "effective_date": None, "source_type": "secondary",
        "content_hash": "0" * 64, "supported_excerpt": "synthetic adversarial evidence"
    })
    result = run(VALIDATOR, benchmark)
    assert result.returncode == 1
    assert "dangling" in result.stdout and "unreferenced evidence" in result.stdout


def test_runner_dry_run_has_no_gold_and_refuses_draft(benchmark: Path) -> None:
    result = run(RUNNER, benchmark, "dry-run")
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert len(payload["prompts"]) == 18
    assert "gold" not in result.stdout.lower()


def test_runner_prepare_refuses_draft_and_writes_nothing(benchmark: Path) -> None:
    output = benchmark / "comparative-runs/prepared.json"
    result = run(RUNNER, benchmark, "prepare", "--output", str(output))
    assert result.returncode == 2
    assert not output.exists()


def test_runner_status_string_cannot_bypass_canonical_readiness(benchmark: Path) -> None:
    state_path = benchmark / "STATUS.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "scoring-ready"
    write(state_path, state)
    output = benchmark / "comparative-runs/prepared.json"
    result = run(RUNNER, benchmark, "prepare", "--output", str(output))
    assert result.returncode == 1
    assert "REFUSE" in result.stderr
    assert not output.exists()


def test_runner_has_no_skill_document_execution() -> None:
    source = (SOURCE / RUNNER).read_text(encoding="utf-8")
    assert "SKILL.md" not in source
    assert "subprocess" not in source


def test_scorer_returns_unproven_without_human_labels(benchmark: Path) -> None:
    dummy = benchmark / "comparative-runs/dummy.json"
    dummy.parent.mkdir(parents=True, exist_ok=True)
    write(dummy, {})
    result = run(VALIDATOR, benchmark, "--score", str(dummy))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "unproven"


def test_manual_comparator_manifest_templates_are_schema_valid_and_unexecuted() -> None:
    runs = SOURCE / "comparative-runs"
    schema = json.loads((runs / "run-manifest.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    paths = [
        runs / "openai-deep-research/run-manifest.template.json",
        runs / "gemini-deep-research/run-manifest.template.json",
        runs / "perplexity-research/run-manifest.template.json",
        runs / "notebooklm-control/run-manifest.template.json",
    ]
    assert all(not list(validator.iter_errors(json.loads(path.read_text(encoding="utf-8")))) for path in paths)
    for path in paths:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["record_state"] == "template"
        assert manifest["access_basis"]["kind"] == "unverified"
        assert manifest["cost"]["amount_incremental"] is None
        assert manifest["outputs"]["canonical_result_sha256"] is None


def test_completed_manual_manifest_fails_closed_without_attestations() -> None:
    runs = SOURCE / "comparative-runs"
    schema = json.loads((runs / "run-manifest.schema.json").read_text(encoding="utf-8"))
    payload = json.loads((runs / "openai-deep-research/run-manifest.template.json").read_text(encoding="utf-8"))
    payload["record_state"] = "completed"
    errors = list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(payload))
    assert errors


def test_manual_manifest_rejects_included_paid_entitlement() -> None:
    runs = SOURCE / "comparative-runs"
    schema = json.loads((runs / "run-manifest.schema.json").read_text(encoding="utf-8"))
    payload = json.loads((runs / "openai-deep-research/run-manifest.template.json").read_text(encoding="utf-8"))
    payload["access_basis"]["kind"] = "included-interactive-entitlement"
    assert list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(payload))


def test_manual_comparator_package_contains_no_evaluator_payload() -> None:
    runs = SOURCE / "comparative-runs"
    for path in runs.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert '"gold_answer"' not in text
        assert '"atomic_claims"' not in text
        assert '"evidence_refs"' not in text


def load_runner():
    spec = importlib.util.spec_from_file_location("benchmark_runner_for_test", SOURCE / RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SOURCE))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SOURCE))
    return module


def valid_import_files(benchmark: Path):
    runner = load_runner()
    public = runner.prompts(benchmark)
    runs = benchmark / "comparative-runs/openai-deep-research"
    runs.mkdir(parents=True, exist_ok=True)
    prepared_path = runs / "prepared.json"
    prepared = runner.prepared_payload(public)
    prepared_path.write_bytes(runner.canonical_bytes(prepared) + b"\n")
    prompt_hash = runner.sha256(runner.canonical_bytes(prepared))
    ids = [item["question_id"] for item in public]
    payload = {
        "result_id": "openai-audit-run",
        "benchmark_version": "0.2.0",
        "system_info": {
            "system_name": "ChatGPT Deep Research", "provider": "OpenAI",
            "mode": "manual-export", "model": "operator-recorded-model",
            "cost_verified_zero": True,
        },
        "questions_processed": ids,
        "results": [{"question_id": qid, "claims": [], "abstained": True} for qid in ids],
        "processing_metadata": {
            "started_at": "2026-08-14T10:00:00Z", "completed_at": "2026-08-14T10:01:00Z",
            "input_hash": prompt_hash, "output_hash": "0" * 64,
        },
    }
    payload["processing_metadata"]["output_hash"] = runner.detached_result_hash(payload)
    source = runs / "raw-result.json"
    source.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    canonical_hash = runner.sha256(runner.canonical_bytes(payload))
    manifest = {
        "schema_version": "1.0", "record_state": "completed", "run_id": payload["result_id"],
        "benchmark_version": "0.2.0", "provider": "OpenAI", "product": "ChatGPT Deep Research",
        "research_mode": "open-web", "operation": "operator-mediated-manual-export",
        "model": payload["system_info"]["model"], "run_date": "2026-08-14",
        "access_basis": {"kind": "verified-free-interactive", "verified_on": "2026-08-14", "operator_note": "verified in provider UI"},
        "cost": {"currency": "CZK", "amount_incremental": 0, "paid_api_used": False, "paid_fallback_enabled": False},
        "privacy": {"public_prompts_only": True, "evaluator_material_excluded": True, "pii_excluded": True, "credentials_excluded": True},
        "inputs": {"public_prompt_sha256": prompt_hash, "question_count": 18, "source_bundle": []},
        "outputs": {"raw_export_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "canonical_result_sha256": canonical_hash},
    }
    manifest_path = runs / "run-manifest.json"
    write(manifest_path, manifest)
    return runner, public, source, manifest_path, prepared_path, payload, manifest


def test_import_contract_accepts_fully_bound_complete_manual_result(benchmark: Path) -> None:
    runner, public, source, manifest, prepared, payload, _ = valid_import_files(benchmark)
    actual, encoded = runner.validate_import(benchmark, source, manifest, prepared, public)
    assert actual == payload
    assert encoded == runner.canonical_bytes(payload)


@pytest.mark.parametrize("mutation", ["partial", "bad_abstention", "duplicate_claim", "private_citation", "bad_hash", "bad_provider"])
def test_import_contract_rejects_semantic_identity_and_hash_bypasses(benchmark: Path, mutation: str) -> None:
    runner, public, source, manifest_path, prepared, payload, manifest = valid_import_files(benchmark)
    if mutation == "partial":
        payload["questions_processed"] = payload["questions_processed"][:1]
        payload["results"] = payload["results"][:1]
    elif mutation == "bad_abstention":
        payload["results"][0]["abstained"] = False
    elif mutation == "duplicate_claim":
        claim = {"claim_id": "sc-duplicate", "text": "synthetic", "citation_urls": ["https://example.invalid/source"]}
        payload["results"][0] = {"question_id": payload["results"][0]["question_id"], "claims": [claim], "abstained": False}
        payload["results"][1] = {"question_id": payload["results"][1]["question_id"], "claims": [claim], "abstained": False}
    elif mutation == "private_citation":
        claim = {"claim_id": "sc-private", "text": "synthetic", "citation_urls": ["https://user:secret@127.0.0.1/source"]}
        payload["results"][0] = {"question_id": payload["results"][0]["question_id"], "claims": [claim], "abstained": False}
    elif mutation == "bad_hash":
        payload["processing_metadata"]["input_hash"] = "f" * 64
    else:
        manifest["provider"] = "Google"
        write(manifest_path, manifest)
    if mutation != "bad_provider":
        payload["processing_metadata"]["output_hash"] = runner.detached_result_hash(payload)
        source.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["outputs"]["raw_export_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest["outputs"]["canonical_result_sha256"] = runner.sha256(runner.canonical_bytes(payload))
        write(manifest_path, manifest)
    with pytest.raises(ValueError):
        runner.validate_import(benchmark, source, manifest_path, prepared, public)


def test_import_contract_contains_every_path(benchmark: Path, tmp_path: Path) -> None:
    runner, public, source, manifest, prepared, _, _ = valid_import_files(benchmark)
    outside = tmp_path / "outside.json"
    outside.write_bytes(source.read_bytes())
    with pytest.raises(ValueError, match="comparative-runs"):
        runner.validate_import(benchmark, outside, manifest, prepared, public)
