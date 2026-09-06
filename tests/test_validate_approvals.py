import json
from pathlib import Path

from scripts.validate_approvals import validate


ROOT = Path(__file__).resolve().parents[1]


def test_live_approval_register_passes():
    result = validate(ROOT)
    assert result["result"] == "pass"
    assert result["records"] == 9
    assert result["errors"] == []


def test_open_gate_requires_passed_checks(tmp_path):
    (tmp_path / "planning").mkdir()
    (tmp_path / "docs/decisions").mkdir(parents=True)
    (tmp_path / "planning/approvals.schema.json").write_text((ROOT / "planning/approvals.schema.json").read_text())
    (tmp_path / "planning/catalog.json").write_text((ROOT / "planning/catalog.json").read_text())
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["implementation_gate"] = "open"
    data["records"][0]["checks"][0]["status"] = "pending"
    data["records"][0]["validation"] = "pending"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    assert any("cannot open" in item for item in validate(tmp_path)["errors"])


def test_deviation_requires_reason(tmp_path):
    (tmp_path / "planning").mkdir()
    (tmp_path / "docs/decisions").mkdir(parents=True)
    (tmp_path / "planning/approvals.schema.json").write_text((ROOT / "planning/approvals.schema.json").read_text())
    (tmp_path / "planning/catalog.json").write_text((ROOT / "planning/catalog.json").read_text())
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["choices"][0]["selected"] = "different"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    assert any("deviation lacks reason" in item for item in validate(tmp_path)["errors"])
