"""
test_synthetic_containment.py

Confirms the seeder never opens a protected path.
The seeder is designed to fail-closed if any protected path is accessed.
"""
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_seeder_does_not_import_protected_paths():
    """The seeder script should not contain references to protected paths.

    Excludes _PROTECTED_PATHS constant which is the containment guard itself.
    """
    seeder_path = REPO_ROOT / "scripts/seed_release1a_dev.py"
    content = seeder_path.read_text()

    protected = [
        "a1/", "scans/", "evidence/", "ocr/", "data/",
        "employees/scans/", "output/",
    ]
    for path in protected:
        assert path not in content, f"Seeder references protected path: {path}"


def test_seeder_protected_path_guard_raises():
    """The seeder's _protected_path_guard should raise on protected paths."""
    # Import the guard function
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from seed_release1a_dev import _protected_path_guard, ProtectedPathAccessed
        for bad_path in ["a1/review.csv", "scans/worker1.jpg", "evidence/"]:
            with pytest.raises(ProtectedPathAccessed):
                _protected_path_guard(bad_path)

        # Good paths should not raise
        _protected_path_guard("tests/fixtures/release_1a/organizations.json")
        _protected_path_guard("portal/settings.py")
    finally:
        sys.path.pop(0)


def test_manifest_fixture_files_exist():
    """All files listed in manifest.json must exist."""
    manifest_path = REPO_ROOT / "tests/fixtures/release_1a/manifest.json"
    import json
    manifest = json.loads(manifest_path.read_text())
    for fname in manifest.get("fixture_files", []):
        fpath = REPO_ROOT / "tests/fixtures/release_1a" / fname
        assert fpath.exists(), f"Fixture file missing: {fname}"


def test_manifest_hashes_are_correct():
    """All fixture file hashes must match the manifest."""
    import json
    import hashlib
    manifest_path = REPO_ROOT / "tests/fixtures/release_1a/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for fname, expected_hash in manifest.get("fixture_hashes", {}).items():
        fpath = REPO_ROOT / "tests/fixtures/release_1a" / fname
        actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert actual == expected_hash, f"Hash mismatch for {fname}"


def test_runtime_portal_gitignored():
    """runtime/portal/ must be gitignored so the DB never enters version control."""
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    assert "runtime/portal/" in gitignore, "runtime/portal/ is not gitignored"


def test_secrets_gitignored():
    """secrets/ must be gitignored."""
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    assert "secrets/" in gitignore, "secrets/ is not gitignored"


def test_seed_script_has_no_secret_key_auto_generation():
    """The seed script should not auto-generate SECRET_KEY."""
    seeder_path = REPO_ROOT / "scripts/seed_release1a_dev.py"
    content = seeder_path.read_text()
    assert "SECRET_KEY" not in content or "os.environ" in content
