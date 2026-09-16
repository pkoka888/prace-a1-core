"""Exercise Make's execution boundaries without launching databases or services."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def make_probe(tmp_path):
    make = shutil.which("make")
    if make is None:
        pytest.skip("GNU Make is required to exercise the Make entrypoints")
    calls = tmp_path / "calls.jsonl"
    python = tmp_path / "python-probe"
    python.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "with Path(os.environ['AUTOMATION_CALLS']).open('a') as stream:\n"
        "    stream.write(json.dumps({'argv': sys.argv[1:], 'settings': "
        "os.environ.get('DJANGO_SETTINGS_MODULE'), 'pytest_addopts': "
        "os.environ.get('PYTEST_ADDOPTS'), 'pg_keys': sorted(name for name "
        "in os.environ if name.startswith('DOCUMENT_TEST_PG_'))}) + '\\n')\n"
    )
    python.chmod(0o700)
    env = {
        "PATH": os.defpath,
        "HOME": str(tmp_path),
        "AUTOMATION_CALLS": str(calls),
        "PYTEST_ADDOPTS": "-n auto --timeout=1",
        "DJANGO_SETTINGS_MODULE": "synthetic.unwanted_settings",
        "PRACE_WORKFLOW_PG": "1",
        "PRACE_DISPOSABLE_TARGET": "1",
        "PRACE_DB_NAME": "synthetic_unowned_target",
    }
    for name in ("SOCKET", "NAME", "USER", "HOST", "PORT", "PASSWORD"):
        env[f"DOCUMENT_TEST_PG_{name}"] = "synthetic-unowned"

    def run(target):
        result = subprocess.run(
            [make, "--no-print-directory", target, f"PYTHON_BIN={python}"],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=20,
        )
        records = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
        return result, records

    return run


def test_pg_target_uses_owned_cluster_harness_without_target_arguments(make_probe):
    result, calls = make_probe("test-pg")
    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert calls[0]["argv"] == [
        "scripts/test_document_intake.py", "--settings", "portal.settings_browser_tests",
        "tests.document_web.test_browser_journey",
    ]


@pytest.mark.parametrize("target,settings", [
    ("test-integration", "portal.settings_document_tests"),
    ("test-browser", "portal.settings_browser_tests"),
])
def test_django_targets_use_manage_and_remove_inherited_postgres_target(make_probe, target, settings):
    result, calls = make_probe(target)
    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert calls[0]["argv"][:2] == ["manage.py", "test"]
    assert calls[0]["settings"] == settings
    assert calls[0]["pg_keys"] == []
    assert "--parallel" not in calls[0]["argv"]


def test_pg_contract_target_cannot_dispatch_workflow_or_inherit_pytest_flags(make_probe):
    result, calls = make_probe("test-pg-contract")
    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert calls[0]["argv"][:2] == ["-m", "pytest"]
    assert not any("rehearse_workflow" in arg for arg in calls[0]["argv"])
    assert calls[0]["pytest_addopts"] == ""
    assert calls[0]["settings"] is None


def test_pytest_configuration_collects_without_optional_plugins(tmp_path):
    env = {
        "PATH": os.defpath,
        "HOME": str(tmp_path),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-p", "no:cacheprovider",
         "tests/test_automation_entrypoints.py"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "test_pg_target_uses_owned_cluster_harness_without_target_arguments" in result.stdout
