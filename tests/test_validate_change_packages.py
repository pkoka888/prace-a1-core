from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.validate_change_packages import validate


def run(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write_catalog(root: Path, packages: dict, forbidden: list[str] | None = None) -> Path:
    path = root / "change-packages.yml"
    path.write_text(json.dumps({
        "schema_version": 1,
        "accepted_checkpoint": "",
        "packages": packages,
        "forbidden_paths": forbidden or [],
    }), encoding="utf-8")
    return path


def repo(tmp_path: Path) -> Path:
    run(tmp_path, "init", "-q")
    run(tmp_path, "config", "user.email", "synthetic@example.invalid")
    run(tmp_path, "config", "user.name", "Synthetic Test")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    run(tmp_path, "add", "base.txt")
    run(tmp_path, "commit", "-qm", "base")
    return tmp_path


def package(paths: list[str], *, eligible: bool = True) -> dict:
    return {"purpose": "synthetic", "paths": paths, "checks": [], "dependencies": [],
            "rollback": "synthetic", "eligible_for_staging": eligible}


def test_exact_classification_and_unicode_quarantine(tmp_path: Path) -> None:
    root = repo(tmp_path)
    (root / "doc.md").write_text("safe\n", encoding="utf-8")
    (root / "práce.zip").write_bytes(b"synthetic")
    catalog = write_catalog(root, {
        "docs": package(["doc.md"]),
        "quarantine": package(["práce.zip"], eligible=False),
    })
    report, status = validate(root, catalog)
    assert status == 1
    assert report["dirty_path_count"] == 3  # catalog is itself untracked
    # Add the catalog to a package and validate the complete exact set.
    data = json.loads(catalog.read_text())
    data["packages"]["docs"]["paths"].append("change-packages.yml")
    catalog.write_text(json.dumps(data), encoding="utf-8")
    report, status = validate(root, catalog)
    assert status == 0
    assert report["quarantined_path_count"] == 1
    docs = next(item for item in report["package_receipts"] if item["package"] == "docs")
    assert docs["exact_paths"] == ["change-packages.yml", "doc.md"]
    assert docs["privacy_review"] == "pass"


def test_overlap_and_unclassified_fail_closed(tmp_path: Path) -> None:
    root = repo(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "x.md").write_text("x\n", encoding="utf-8")
    (root / "other.txt").write_text("x\n", encoding="utf-8")
    catalog = write_catalog(root, {
        "one": package(["docs/"]),
        "two": package(["docs/x.md", "change-packages.yml"]),
    })
    report, status = validate(root, catalog)
    assert status == 1
    assert any("exactly one package (2): docs/x.md" in p for p in report["problems"])
    assert any("exactly one package (0): other.txt" in p for p in report["problems"])


def test_forbidden_path_fails_even_when_packaged(tmp_path: Path) -> None:
    root = repo(tmp_path)
    (root / "private").mkdir()
    (root / "private" / "person.csv").write_text("synthetic\n", encoding="utf-8")
    catalog = write_catalog(root, {
        "bad": package(["private/", "change-packages.yml"], eligible=False),
    }, ["private/"])
    report, status = validate(root, catalog)
    assert status == 1
    assert any("dirty forbidden path: private/person.csv" == p for p in report["problems"])


def test_publishable_report_with_personal_host_path_fails(tmp_path: Path) -> None:
    root = repo(tmp_path)
    (root / "report.md").write_text("tool: /home/operator/bin/tool\n", encoding="utf-8")
    catalog = write_catalog(root, {
        "docs": package(["report.md", "change-packages.yml"]),
    })
    report, status = validate(root, catalog)
    assert status == 1
    assert any("personal-host-path" in p for p in report["problems"])
