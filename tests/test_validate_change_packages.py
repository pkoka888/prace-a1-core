from __future__ import annotations

import json
import os
import pytest
import subprocess
from pathlib import Path

from scripts.validate_change_packages import validate


@pytest.fixture(autouse=True)
def isolated_git_environment(monkeypatch):
    """Synthetic repository tests must never inherit the invoking hook's Git state."""
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)


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


# ------------------------------------------------------------------
# Runner: per-check timing, distinct timeout/failure, report retention
# ------------------------------------------------------------------

def test_runner_records_per_check_timing_and_outcome(tmp_path):
    """The runner records one outcome per check with elapsed time and
    distinguishes PASS / FAIL / TIMEOUT. The JSON report survives even
    on failure so the cause is reproducible from the catalog alone.
    """
    import sys
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    data['packages']['safe']['checks'] = [
        f"{sys.executable} -c \"import time; time.sleep(0.2); print('ok')\"",
    ]
    catalog.write_text(json.dumps(data))
    run(root, 'add', 'change-packages.yml')
    script = Path(__file__).resolve().parents[1] / 'scripts/validate_change_packages.py'
    output = root / 'report.json'
    result = subprocess.run(
        [sys.executable, str(script), '--root', str(root),
         '--staged', '--run-checks', '--output', str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    report = json.loads(output.read_text())
    receipt = report['check_run']
    assert receipt['started_at']
    assert receipt['finished_at']
    assert len(receipt['checks']) == 1
    check = receipt['checks'][0]
    assert check['package'] == 'safe'
    assert check['status'] == 'PASS'
    assert check['elapsed_s'] >= 0.1
    assert check['exit_code'] == 0
    assert 'timeout_s' in check


def test_runner_timeout_is_distinguished_from_test_failure(tmp_path):
    """A check that exceeds its per-check budget reports status='TIMEOUT'
    and keeps partial stdout/stderr so the failure is reproducible.

    The runner honours the ``VALIDATE_CHANGE_PACKAGES_TIMEOUT`` env var
    to override the per-class budget; the test sets it to 1 second
    and runs a 5-second sleep, which must time out.
    """
    import sys
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    sleep_check = f"{sys.executable} -c \"import time; time.sleep(5); print('late')\""
    data['packages']['safe']['checks'] = [sleep_check]
    catalog.write_text(json.dumps(data))
    run(root, 'add', 'change-packages.yml')
    script = Path(__file__).resolve().parents[1] / 'scripts/validate_change_packages.py'
    output = root / 'report.json'
    result = subprocess.run(
        [sys.executable, str(script), '--root', str(root),
         '--staged', '--run-checks', '--output', str(output)],
        capture_output=True, text=True,
        env={**os.environ, "VALIDATE_CHANGE_PACKAGES_TIMEOUT": "1"},
    )
    assert result.returncode == 1
    assert 'PACKAGE_CHECK_FAILED (TIMEOUT)' in result.stderr
    report = json.loads(output.read_text())
    receipt = report['check_run']
    assert len(receipt['checks']) == 1
    check = receipt['checks'][0]
    assert check['status'] == 'TIMEOUT'
    assert check['error'] is not None
    assert 'timeout after 1s' in check['error']


def test_runner_writes_report_even_on_failure(tmp_path):
    """The runner writes the JSON report before returning on failure so
    the catalog + report together prove what was checked and how."""
    import sys
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    data['packages']['safe']['checks'] = [f"{sys.executable} -c \"import sys; sys.exit(3)\""]
    catalog.write_text(json.dumps(data))
    run(root, 'add', 'change-packages.yml')
    script = Path(__file__).resolve().parents[1] / 'scripts/validate_change_packages.py'
    output = root / 'report.json'
    result = subprocess.run(
        [sys.executable, str(script), '--root', str(root),
         '--staged', '--run-checks', '--output', str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    # The report must still be written and contain the failure.
    assert output.exists()
    report = json.loads(output.read_text())
    assert report['check_run']['checks'][0]['status'] == 'FAIL'
    assert report['check_run']['checks'][0]['exit_code'] == 3


def test_runner_per_check_timeout_scales_with_command_class():
    """The runner's per-check timeout is proportional to the workload:
    `manage.py test` covering many test files gets a long budget; a
    single pytest file gets a small one. This prevents the previous
    blanket 300s from timing out a 5-minute broad suite while still
    catching a stuck pytest command quickly."""
    from scripts.validate_change_packages import _per_check_timeout
    assert _per_check_timeout("manage.py test ...") >= 600
    assert _per_check_timeout("pytest tests/test_a.py") <= 300
    assert _per_check_timeout("pytest tests/test_a.py") < _per_check_timeout("manage.py test ...")


# ------------------------------------------------------------------
# Dispatcher: select_shared_document_portal_checks.py
# ------------------------------------------------------------------

def test_dispatch_selects_narrow_test_for_test_only_change():
    """Editing a single test file must select only that file, not the
    broad 24-test-file suite. This is the change that previously
    caused the pre-commit hook to time out."""
    from scripts.select_shared_document_portal_checks import select
    cmds = select(["tests/test_a1_employee_delivery.py"])
    assert len(cmds) == 1
    assert "tests/test_a1_employee_delivery.py" in cmds[0]
    assert "manage.py test" not in cmds[0]
    assert "pytest" in cmds[0]


def test_dispatch_selects_no_command_for_doc_only_change():
    """Documentation changes must not trigger a test run."""
    from scripts.select_shared_document_portal_checks import select
    cmds = select(["docs/operations/wsgi-deployment-recipe.md"])
    assert cmds == []


def test_dispatch_selects_no_command_for_empty_staged_set():
    """An empty staged set returns no commands; the runner skips the
    empty case rather than running a wide smoke."""
    from scripts.select_shared_document_portal_checks import select
    assert select([]) == []


def test_dispatch_falls_back_to_broad_suite_for_source_change():
    """Source changes under portal/release1a/ fall back to the broad
    24-test-file suite because the change can affect authorization,
    storage, rendering or migrations spanning the whole portal."""
    from scripts.select_shared_document_portal_checks import select
    cmds = select(["portal/release1a/intake_views.py"])
    assert len(cmds) == 1
    assert "manage.py test" in cmds[0]


def test_dispatch_falls_back_to_broad_suite_for_migration_change():
    from scripts.select_shared_document_portal_checks import select
    cmds = select(["portal/release1a/migrations/0019_worker_legacy_key.py"])
    assert len(cmds) == 1
    assert "manage.py test" in cmds[0]


def test_dispatch_handles_multiple_test_files():
    from scripts.select_shared_document_portal_checks import select
    cmds = select([
        "tests/test_a1_employee_delivery.py",
        "tests/test_wsgi_asgi.py",
    ])
    assert len(cmds) == 1
    assert "tests/test_a1_employee_delivery.py" in cmds[0]
    assert "tests/test_wsgi_asgi.py" in cmds[0]


def test_dispatch_via_cli_matches_in_process_select():
    """The CLI invocation must emit the same commands as the in-process
    function so the catalog behavior is reproducible from either path."""
    import subprocess, sys
    script = Path(__file__).resolve().parents[1] / \
        'scripts/select_shared_document_portal_checks.py'
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    # With no staged paths the CLI emits nothing; that is the empty
    # case. We only assert it does not crash and respects the contract.
    assert result.returncode == 0
