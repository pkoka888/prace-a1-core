from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_cli_claims", ROOT / "scripts" / "verify_cli_claims.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_safe_excerpt_redacts_secrets_and_machine_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    text = f"config {tmp_path}/repo\nAPI_KEY=synthetic-secret\nplain"
    result = module.safe_excerpt(text, tmp_path / "repo")
    assert "<repo>" in result
    assert "synthetic-secret" not in result
    assert "<redacted sensitive line>" in result


def test_json_shape_does_not_retain_values() -> None:
    shape = module.json_shape({"status": "ok", "api_key": "synthetic-secret"})
    assert shape == {"type": "object", "keys": ["status"], "redacted_key_count": 1}
    assert "synthetic-secret" not in json.dumps(shape)


def test_claim_uses_runtime_help() -> None:
    product = {
        "installed": True,
        "help_available": True,
        "_help_text": "usage: demo --auto",
        "probes": [],
    }
    claim = {
        "id": "demo_auto",
        "product": "demo",
        "statement": "Demo supports auto mode.",
        "source": "help",
        "contains": "--auto",
    }
    result = module.evaluate_claim(claim, {"demo": product})
    assert result["status"] == "VERIFIED_RUNTIME"


def test_native_json_probe_records_shape_only(tmp_path: Path, monkeypatch) -> None:
    fake = tmp_path / "demo"
    fake.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then echo 'demo 1.0'; exit; fi\n"
        "if [ \"$1\" = \"--help\" ]; then echo 'usage --auto'; exit; fi\n"
        "echo '{\"status\":\"ok\",\"password\":\"synthetic-secret\"}'\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    spec = {
        "id": "demo",
        "label": "Demo",
        "binary": "demo",
        "version_args": ["--version"],
        "help_args": ["--help"],
        "safe_probes": [
            {"id": "doctor", "args": ["doctor", "--json"], "format": "json", "purpose": "test"}
        ],
    }
    result = module.verify_product(spec, tmp_path, 2)
    probe = result["probes"][0]
    assert probe["valid_json"] is True
    assert probe["json_shape"]["keys"] == ["status"]
    assert "synthetic-secret" not in json.dumps(result)


def test_nonzero_native_json_is_completed_with_findings(tmp_path: Path, monkeypatch) -> None:
    fake = tmp_path / "demo"
    fake.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then echo 'demo 1.0'; exit; fi\n"
        "if [ \"$1\" = \"--help\" ]; then echo 'usage'; exit; fi\n"
        "echo '{\"overallStatus\":\"warning\"}'\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    spec = {
        "id": "demo",
        "label": "Demo",
        "binary": "demo",
        "safe_probes": [{"id": "doctor", "args": ["doctor"], "format": "json", "purpose": "test"}],
    }
    result = module.verify_product(spec, tmp_path, 2)
    assert result["native_outputs"][0]["status"] == "completed_with_findings"


def test_model_policy_is_disabled_and_cannot_issue_runtime_verdicts() -> None:
    registry = json.loads((ROOT / "config" / "cli_verification_claims.json").read_text(encoding="utf-8"))
    policy = registry["model_assistance"]
    assert policy["enabled"] is False
    assert policy["authority"] == "advisory_only"
    assert policy["sampling"]["temperature"] == 0.0
    assert policy["sampling"]["top_p"] is None
    assert {"VERIFIED_RUNTIME", "CONTRADICTED"}.issubset(policy["output_contract"]["forbidden_statuses"])
