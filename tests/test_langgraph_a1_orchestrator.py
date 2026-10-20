"""LangGraph A1 orchestrator: dry-run purity and state-schema compatibility.

A dry run must be side-effect free. It must not create, replace or remove any
file in the protected output tree: the canonical publisher keeps its
``generation_manifest.json`` at the package level and the quality gate reads
it, so a dry run that rewrites it destroys the evidence that a real generation
completed.
"""
import json
from pathlib import Path


from scripts import langgraph_a1_orchestrator as orchestrator


def _snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): path.stat().st_size
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_dry_run_writes_nothing_into_the_output_tree(tmp_path, monkeypatch, capsys):
    output = tmp_path / "output" / "provisional"
    output.mkdir(parents=True)
    (output / "generation_manifest.json").write_text("published-manifest", encoding="utf-8")
    review = tmp_path / "review.csv"
    review.write_text("employee_id,status_profile\n", encoding="utf-8")
    cohort = tmp_path / "cohort.json"
    cohort.write_text(json.dumps({"issue_dates": {}, "document_ids": {}}), encoding="utf-8")
    config = tmp_path / "provisional.json"
    config.write_text(json.dumps({"notice": "CLIENT_CONFIRMATION_COPY"}), encoding="utf-8")

    before = _snapshot(tmp_path)

    monkeypatch.setattr(
        orchestrator, "a1_private_dir", lambda: tmp_path)
    exit_code = orchestrator.cmd_run(type("Args", (), {
        "review": review, "cohort": cohort, "config": config,
        "employees": None, "profiles": None, "output_dir": output,
        "postgres_url": None, "dry_run": True, "max_retries": 0,
        "resume": None, "rollback": None,
    })())

    assert exit_code == 0
    assert _snapshot(tmp_path) == before, "dry run modified the output tree"
    assert (output / "generation_manifest.json").read_text(encoding="utf-8") == "published-manifest"
    assert "Simulated manifest (not written to disk)" in capsys.readouterr().out


def test_dry_run_does_not_create_a_missing_output_tree(tmp_path, monkeypatch):
    output = tmp_path / "output" / "provisional"
    review = tmp_path / "review.csv"
    review.write_text("employee_id,status_profile\n", encoding="utf-8")
    cohort = tmp_path / "cohort.json"
    cohort.write_text(json.dumps({"issue_dates": {}, "document_ids": {}}), encoding="utf-8")
    config = tmp_path / "provisional.json"
    config.write_text(json.dumps({"notice": "CLIENT_CONFIRMATION_COPY"}), encoding="utf-8")

    monkeypatch.setattr(orchestrator, "a1_private_dir", lambda: tmp_path)
    exit_code = orchestrator.cmd_run(type("Args", (), {
        "review": review, "cohort": cohort, "config": config,
        "employees": None, "profiles": None, "output_dir": output,
        "postgres_url": None, "dry_run": True, "max_retries": 0,
        "resume": None, "rollback": None,
    })())

    assert exit_code == 0
    assert not output.exists(), "dry run created the protected output tree"


def test_state_schema_avoids_langgraph_reserved_channels():
    from langgraph._internal._constants import RESERVED

    assert not set(orchestrator.A1State.__annotations__) & set(RESERVED)


def test_state_carries_a_workflow_run_identifier():
    state = orchestrator.create_initial_state(
        orchestrator.WorkflowConfig(
            review_path=Path("a1/review.csv"),
            cohort_path=Path("a1/cohort.json"),
            config_path=Path("config/a1_provisional.json"),
            employees_path=Path("a1/employees_normalized.json"),
            profiles_path=Path("config/institutions"),
            output_dir=Path("output/provisional")))
    assert isinstance(state["workflow_run_id"], str)
    assert state["workflow_run_id"]
