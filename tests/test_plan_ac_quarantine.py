from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_synthetic_mini_v2_is_explicitly_quarantined_stale() -> None:
    status_path = ROOT / "plans/audits/2026-08-15-synthetic-mini-v2-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["artifact_id"] == "synthetic-mini-v2"
    assert status["state"] == "quarantined-stale-checkpoint"
    assert status["authority"] == "regression-fixture-only-not-market-evidence"
    assert status["live_capture_authorized"] is False
    assert status["skill_activation_authorized"] is False
    assert "Integrity 1.3" in status["successor_gate"]
    assert "without overwriting v2" in status["successor_gate"]

    mismatches = status["known_mismatches"]
    assert len(mismatches) == 2
    assert {item["path"] for item in mismatches} == {
        "research/acquisition/source-captures/synthetic-mini-v2/manifest.json",
        "research/acquisition/synthetic-mini-pilot/runs/synthetic-mini-v2/execution.json",
    }
    for item in mismatches:
        assert item["declared_sha256"] != item["observed_sha256"]
        assert len(item["declared_sha256"]) == 64
        assert len(item["observed_sha256"]) == 64
        artifact = ROOT / item["path"]
        # Quarantined artifacts are intentionally absent from clean clones. If
        # preserved locally, their exact stale bytes must remain unchanged.
        if artifact.is_file():
            assert hashlib.sha256(artifact.read_bytes()).hexdigest() == item["observed_sha256"]
