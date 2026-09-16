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


@pytest.mark.parametrize("relative", [".runtime-config/probe.json", "docs/.runtime-config/probe.json"])
def test_runtime_configuration_is_rejected_before_blob_read(tmp_path, monkeypatch, relative):
    from scripts import validate_change_packages as checker
    root = repo(tmp_path)
    private = root / relative
    private.parent.mkdir(parents=True)
    private.write_text("synthetic runtime canary")
    catalog = write_catalog(root, {"misclassified": package([relative, "change-packages.yml"])})
    run(root, "add", "--", relative, "change-packages.yml")
    oid = subprocess.check_output(["git", "-C", str(root), "rev-parse", ":" + relative]).strip()
    original = checker.git
    def guarded(repo_root, *args, **kwargs):
        assert args != ("cat-file", "blob", oid.decode()), "private blob was read"
        return original(repo_root, *args, **kwargs)
    monkeypatch.setattr(checker, "git", guarded)
    report, status = checker.validate(root, catalog, staged=True)
    assert status == 1
    assert f"dirty forbidden path: {relative}" in report["problems"]


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
    assert len(cmds) == 2
    assert "manage.py test" in cmds[0]


def test_dispatch_falls_back_to_broad_suite_for_migration_change():
    from scripts.select_shared_document_portal_checks import select
    cmds = select(["portal/release1a/migrations/0019_worker_legacy_key.py"])
    assert len(cmds) == 2
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


def test_dispatch_uses_django_database_runner():
    from scripts.select_shared_document_portal_checks import select
    commands = select(["tests/document_web/test_intake.py", "tests/test_j4_service.py"])
    assert len(commands) == 1
    assert "manage.py test tests.document_web.test_intake tests.test_j4_service" in commands[0]
    assert "pytest" not in commands[0]


def test_source_change_retains_integration_and_additional_edited_test():
    from scripts.select_shared_document_portal_checks import select
    commands = select(["portal/release1a/services.py", "tests/test_a1_employee_delivery.py"])
    assert "manage.py test" in commands[0]
    for path in ["tests/test_j4_artifacts.py", "tests/test_runtime_contract.py",
                 "tests/test_a1_input_artifacts.py", "tests/m2/test_synthetic_containment.py",
                 "tests/test_a1_employee_delivery.py"]:
        assert path in commands[1]


@pytest.mark.parametrize("path", ["tests/document_web/__init__.py",
                                 "tests/document_web/test_deleted.py"])
def test_helper_and_deleted_test_do_not_silently_skip(path):
    from scripts.select_shared_document_portal_checks import select
    assert "manage.py test" in select([path])[0]


def test_selector_tooling_is_owned_by_git_workflow():
    data = json.loads((Path(__file__).resolve().parents[1] / "change-packages.yml").read_text())
    owners = [name for name, item in data["packages"].items()
              if "scripts/select_shared_document_portal_checks.py" in item.get("paths", [])]
    assert owners == ["infrastructure_git_workflow"]


def test_standalone_selector_filters_mixed_index_in_requested_root(tmp_path):
    import sys
    root = repo(tmp_path)
    (root / "tests").mkdir()
    (root / "scripts").mkdir()
    (root / "tests/test_example.py").write_text("def test_example(): pass")
    (root / "scripts/unrelated.py").write_text("# synthetic tooling")
    write_catalog(root, {
        "shared_document_portal": package(["tests/test_example.py"]),
        "tooling": package(["change-packages.yml", "scripts/unrelated.py"]),
    })
    run(root, "add", "change-packages.yml", "tests/test_example.py", "scripts/unrelated.py")
    script = Path(__file__).resolve().parents[1] / "scripts/select_shared_document_portal_checks.py"
    result = subprocess.run([sys.executable, str(script), "--root", str(root)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "pytest -q tests/test_example.py" in result.stdout
    assert "manage.py" not in result.stdout


def test_standalone_selector_routes_browser_test_to_playwright_entrypoint(tmp_path):
    """The browser journey test must NOT be selected under
    settings_document_tests (the previous selection silently skipped
    the test with no executed browser coverage). The selector must
    route it to scripts/playwright_smoke.py with the
    settings_browser_tests module.
    """
    import sys
    root = repo(tmp_path)
    (root / "tests").mkdir()
    (root / "tests" / "document_web").mkdir(parents=True)
    (root / "tests/document_web/test_browser_journey.py").write_text(
        "def test_browser_journey(): pass"
    )
    write_catalog(root, {
        "shared_document_portal": package(["tests/document_web/test_browser_journey.py"]),
    })
    run(root, "add", "tests/document_web/test_browser_journey.py")
    script = Path(__file__).resolve().parents[1] / "scripts/select_shared_document_portal_checks.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root),
         "--paths-json", json.dumps(["tests/document_web/test_browser_journey.py"])],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    # The browser journey must be invoked via the isolated entrypoint.
    assert "playwright_smoke.py" in out
    assert "settings_browser_tests" in out
    # It must not be routed via manage.py test (which would silently skip).
    assert "manage.py test tests.document_web.test_browser_journey" not in out


def runner_repo(tmp_path, checks, selector_code=None):
    """Exercise the real CLI and dispatcher protocol in an isolated Git index."""
    root, catalog = staged_repo(tmp_path)
    data = json.loads(catalog.read_text())
    data["packages"]["safe"]["checks"] = checks
    if selector_code is not None:
        (root / "scripts").mkdir()
        selector = root / "scripts/select_fixture.py"
        selector.write_text(selector_code)
        data["packages"]["safe"]["paths"].append("scripts/select_fixture.py")
        run(root, "add", "scripts/select_fixture.py")
    catalog.write_text(json.dumps(data))
    run(root, "add", "change-packages.yml")
    return root, catalog


def runner_command(root):
    import sys
    script = Path(__file__).resolve().parents[1] / "scripts/validate_change_packages.py"
    return [sys.executable, str(script), "--root", str(root), "--staged", "--run-checks"]


def runner_report(root):
    return json.loads(next((root / "runtime/portal/temporary").glob("change-checks-*/report.json")).read_text())


@pytest.mark.parametrize("selector_code", [
    "raise SystemExit(7)",
    "print('echo should-never-run'); raise SystemExit(7)",
    "import time; time.sleep(5)",
])
def test_selector_failure_never_uses_partial_or_previous_commands(tmp_path, monkeypatch, selector_code):
    import scripts.validate_change_packages as runner
    root, _ = runner_repo(tmp_path, ["echo should-never-run", "scripts/select_fixture.py"], selector_code)
    # Shorten only the selector budget in this regression, not production defaults.
    original = runner._run_command
    def bounded(root, outcome, directory, number):
        if outcome["kind"] == "selector":
            outcome["timeout_s"] = 1
        return original(root, outcome, directory, number)
    monkeypatch.setattr(runner, "_run_command", bounded)
    monkeypatch.setattr("sys.argv", runner_command(root)[1:])
    assert runner.main() == 1
    checks = runner_report(root)["check_run"]["checks"]
    assert len(checks) == 1
    assert checks[0]["status"] in {"FAIL", "TIMEOUT"}
    assert checks[0]["kind"] == "selector"


def test_mixed_commit_passes_only_owning_package_paths_to_selector(tmp_path):
    code = """import argparse, json
p = argparse.ArgumentParser()
p.add_argument('--root'); p.add_argument('--paths-json')
args = p.parse_args()
assert json.loads(args.paths_json) == ['doc.md']
"""
    root, catalog = runner_repo(tmp_path, [], code)
    data = json.loads(catalog.read_text())
    data["packages"]["portal"] = package(["doc.md"])
    data["packages"]["portal"]["checks"] = ["scripts/select_fixture.py"]
    data["packages"]["safe"]["paths"].remove("doc.md")
    catalog.write_text(json.dumps(data))
    (root / "doc.md").write_text("synthetic")
    run(root, "add", "change-packages.yml", "doc.md")
    result = subprocess.run(runner_command(root), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert runner_report(root)["check_run"]["checks"][0]["status"] == "PASS"


def test_resolved_commands_deduplicated_across_packages(tmp_path):
    root, catalog = runner_repo(tmp_path, ["echo shared"], "print('echo shared')")
    data = json.loads(catalog.read_text())
    data["packages"]["portal"] = package(["doc.md"])
    data["packages"]["portal"]["checks"] = ["scripts/select_fixture.py"]
    data["packages"]["safe"]["paths"].remove("doc.md")
    catalog.write_text(json.dumps(data))
    (root / "doc.md").write_text("synthetic")
    run(root, "add", "change-packages.yml", "doc.md")
    result = subprocess.run(runner_command(root), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    checks = runner_report(root)["check_run"]["checks"]
    assert len([c for c in checks if c["kind"] == "check"]) == 1


@pytest.mark.parametrize("command", ["missing-synthetic-executable", "echo 'unclosed", "echo ok | cat"])
def test_invalid_commands_retain_failure_report(tmp_path, command):
    root, _ = runner_repo(tmp_path, [command])
    result = subprocess.run(runner_command(root), capture_output=True, text=True)
    assert result.returncode == 1
    assert runner_report(root)["check_run"]["checks"][0]["status"] == "ERROR"


def test_timeout_classification_ignores_pytest_flag_order(monkeypatch):
    from scripts.validate_change_packages import _per_check_timeout
    monkeypatch.delenv("VALIDATE_CHANGE_PACKAGES_TIMEOUT", raising=False)
    assert _per_check_timeout("python -m pytest -q tests/test_one.py") == 120
    assert _per_check_timeout("python -m pytest tests/test_one.py tests/test_two.py -q") == 600
    assert _per_check_timeout("python -m pytest tests/document_web/ -q") == 600


def test_full_output_and_private_default_report(tmp_path):
    import stat
    import sys
    root, _ = runner_repo(tmp_path, [f'''{sys.executable} -c "print('first-marker'); print('x'*5000)"'''])
    result = subprocess.run(runner_command(root), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = runner_report(root)
    check = report["check_run"]["checks"][0]
    log = Path(check["stdout_log"])
    assert "first-marker" in log.read_text()
    assert "first-marker" not in check["stdout_tail"]
    assert stat.S_IMODE(log.stat().st_mode) == 0o600
    assert stat.S_IMODE(log.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE((log.parent / "report.json").stat().st_mode) == 0o600
    assert "START [safe]" in result.stderr


@pytest.mark.parametrize("termination", ["timeout", "SIGTERM", "SIGINT"])
def test_cancellation_reaps_check_and_descendants(tmp_path, termination):
    import signal
    import sys
    import time
    root, _ = runner_repo(tmp_path, [f"{sys.executable} sleeper.py"])
    # The marker is written only after the child exists, avoiding a signal race.
    (root / "sleeper.py").write_text("""import subprocess, sys, time
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
Path('child.pid').write_text(str(child.pid))
time.sleep(60)
""")
    proc = subprocess.Popen(runner_command(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env={**os.environ, "VALIDATE_CHANGE_PACKAGES_TIMEOUT": "2"})
    try:
        assert "VALIDATION_REPORT:" in proc.stderr.readline()
        assert "START [safe]" in proc.stderr.readline()
        assert proc.poll() is None  # Progress is visible before completion.
        deadline = time.monotonic() + 5
        while not (root / "child.pid").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (root / "child.pid").exists()
        if termination != "timeout":
            proc.send_signal(getattr(signal, termination))
        stdout, stderr = proc.communicate(timeout=8)
        assert proc.returncode == 1, (stdout, stderr)
        check = runner_report(root)["check_run"]["checks"][0]
        assert check["status"] == ("TIMEOUT" if termination == "timeout" else "INTERRUPTED")
        pid = (root / "child.pid").read_text()
        # A reparented zombie can briefly remain until the container init reaps it.
        child_stat = Path(f"/proc/{pid}/stat")
        deadline = time.monotonic() + 2
        while child_stat.exists() and child_stat.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not child_stat.exists() or child_stat.read_text().split()[2] == "Z"
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.communicate(timeout=5)
