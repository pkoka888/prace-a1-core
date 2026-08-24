import json
import shutil
from pathlib import Path

from scripts.run_architecture_proofs import EXIT_FAILURE, EXIT_OK, EXIT_UNPROVEN, preflight, synthetic_upload_samples

ROOT = Path(__file__).resolve().parents[1]


def test_live_release_1a_fixture_contract_passes():
    result, code = preflight(ROOT)
    assert code == EXIT_OK, result
    assert result["files"] == 7


def test_hash_drift_fails(tmp_path):
    target = tmp_path / "tests/fixtures/release_1a"
    shutil.copytree(ROOT / "tests/fixtures/release_1a", target)
    (target / "workers.json").write_text("[]")
    result, code = preflight(tmp_path)
    assert code == EXIT_FAILURE
    assert any("hash mismatch" in error for error in result["errors"])


def test_missing_contract_is_unproven(tmp_path):
    assert preflight(tmp_path)[1] == EXIT_UNPROVEN


def test_upload_samples_cover_bytes_mismatch_duplicate_and_bounded_oversize():
    samples = synthetic_upload_samples(128)
    assert samples["valid.pdf"].startswith(b"%PDF-")
    assert samples["valid.png"].startswith(b"\x89PNG")
    assert not samples["mime-mismatch.pdf"].startswith(b"%PDF-")
    assert samples["duplicate-a.pdf"] == samples["duplicate-b.pdf"]
    assert 128 < len(samples["oversize.pdf"]) < 1024
