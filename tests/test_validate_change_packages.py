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


def staged_repo(tmp_path):
    root = repo(tmp_path)
    catalog = write_catalog(root, {'safe': package(['change-packages.yml', 'doc.md'])})
    run(root, 'add', 'change-packages.yml')
    run(root, 'commit', '-qm', 'catalog')
    return root, catalog


def test_staged_secret_cannot_be_hidden_by_clean_worktree(tmp_path):
    root, catalog = staged_repo(tmp_path)
    (root / 'doc.md').write_text('sk-' + 'A' * 24)
    run(root, 'add', 'doc.md')
    (root / 'doc.md').write_text('clean')
    report, status = validate(root, catalog, staged=True)
    assert status == 1
    assert any('credential-pattern' in p for p in report['problems'])


def test_unstaged_secret_and_unrelated_files_are_not_read(tmp_path):
    root, catalog = staged_repo(tmp_path)
    (root / 'doc.md').write_text('safe')
    run(root, 'add', 'doc.md')
    (root / 'doc.md').write_text('sk-' + 'B' * 24)
    (root / 'unknown.txt').write_text('unrelated')
    report, status = validate(root, catalog, staged=True)
    assert status == 0
    assert [e['path'] for e in report['entries']] == ['doc.md']


def test_unstaged_catalog_cannot_admit_unknown_path(tmp_path):
    root, catalog = staged_repo(tmp_path)
    (root / 'unknown.txt').write_text('safe')
    run(root, 'add', 'unknown.txt')
    data = json.loads(catalog.read_text())
    data['packages']['safe']['paths'].append('unknown.txt')
    catalog.write_text(json.dumps(data))
    assert validate(root, catalog, staged=True)[1] == 1


def test_staged_symlink_rejected_without_reading_target(tmp_path):
    root, catalog = staged_repo(tmp_path)
    (root / 'doc.md').symlink_to('missing-target')
    run(root, 'add', 'doc.md')
    report, status = validate(root, catalog, staged=True)
    assert status == 1
    assert 'unsupported-index-entry' in report['entries'][0]['privacy_indicators']


def test_staged_deletion_allowed(tmp_path):
    root, catalog = staged_repo(tmp_path)
    (root / 'doc.md').write_text('safe')
    run(root, 'add', 'doc.md')
    run(root, 'commit', '-qm', 'document')
    run(root, 'rm', 'doc.md')
    assert validate(root, catalog, staged=True)[1] == 0


def test_staged_quarantine_fails(tmp_path):
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    data['packages']['safe']['eligible_for_staging'] = False
    catalog.write_text(json.dumps(data))
    run(root, 'add', 'change-packages.yml')
    assert validate(root, catalog, staged=True)[1] == 1


def test_malformed_catalog_cli_fails_sanitized(tmp_path):
    root, catalog = staged_repo(tmp_path)
    catalog.write_text('{')
    run(root, 'add', 'change-packages.yml')
    import sys
    script = Path(__file__).resolve().parents[1] / 'scripts/validate_change_packages.py'
    result = subprocess.run([sys.executable, str(script), '--root', str(root), '--staged'], capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stderr.strip() == 'CHANGE_PACKAGE_VALIDATION_FAILED'


def test_github_bash_pipeline_preserves_failure():
    result = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', 'exit 7 | tail -1'])
    assert result.returncode == 7


def test_failed_package_command_blocks_cli(tmp_path):
    import sys
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    data['packages']['safe']['checks'] = [sys.executable + ' -c "raise SystemExit(9)"']
    catalog.write_text(json.dumps(data))
    run(root, 'add', 'change-packages.yml')
    script = Path(__file__).resolve().parents[1] / 'scripts/validate_change_packages.py'
    result = subprocess.run([sys.executable, str(script), '--root', str(root), '--staged', '--run-checks'], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'PACKAGE_CHECK_FAILED' in result.stderr


def test_environment_variant_blocked_even_when_packaged(tmp_path):
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    data['packages']['safe']['paths'].append('.env.production')
    catalog.write_text(json.dumps(data))
    (root / '.env.production').write_text('synthetic')
    run(root, 'add', 'change-packages.yml', '.env.production')
    assert validate(root, catalog, staged=True)[1] == 1


def test_ci_contract_has_no_success_fallbacks():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / '.github/workflows/ci.yml').read_text()
    assert 'shell: bash' in workflow
    assert '|| true' not in workflow
    assert 'continue-on-error: true' not in workflow
    assert '| tail' not in workflow
    assert "refs/heads/master" in workflow
    assert 'contents: read' in workflow


def test_credential_scanner_checks_committed_bytes_without_values(tmp_path):
    import sys
    root = repo(tmp_path)
    secret = 'ghp_' + 'X' * 30
    (root / 'fixture.txt').write_text(secret)
    run(root, 'add', 'fixture.txt')
    run(root, 'commit', '-qm', 'synthetic signature')
    (root / 'fixture.txt').write_text('safe worktree')
    script = Path(__file__).resolve().parents[1] / 'scripts/check_git_content.py'
    result = subprocess.run([sys.executable, str(script)], cwd=root, capture_output=True, text=True)
    assert result.returncode == 1
    assert 'CREDENTIAL_SIGNATURE' in result.stdout
    assert secret not in result.stdout + result.stderr
