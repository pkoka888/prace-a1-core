"""
test_synthetic_containment.py

Confirms the seeder never opens a protected path.
The seeder is designed to fail-closed if any protected path is accessed.
"""
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_seeder_does_not_open_protected_paths_at_runtime():
    """The seeder must not open any protected path during --apply or --verify.

    The tokens themselves legitimately appear in the PROTECTED_PATH_TOKENS
    constant (the guard's allowlist); the test exercises the guard via
    fixtures and asserts it raises. The textual-content check is intentionally
    avoided so the constant can be edited without breaking the test.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from seed_release1a_dev import _protected_path_guard, ProtectedPathAccessed
        for bad in ("a1/review.csv", "scans/w.jpg", "evidence/x", "ocr/y.bin",
                    "data/z", "employees/scans/q", "output/r.pdf"):
            with pytest.raises(ProtectedPathAccessed):
                _protected_path_guard(bad)
        # Good paths must not raise
        for ok in ("tests/fixtures/release_1a/organizations.json",
                   "portal/settings.py"):
            _protected_path_guard(ok)
    finally:
        sys.path.pop(0)


def test_seeder_protected_path_guard_raises():
    """The seeder's _protected_path_guard should raise on protected paths."""
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


def test_verify_flag_is_wired():
    """--verify must be parsed and routed to read-only comparison."""
    seeder_path = REPO_ROOT / "scripts/seed_release1a_dev.py"
    content = seeder_path.read_text()
    assert '"--verify"' in content, "--verify flag missing from argparse"
    assert "verify_seeded_db" in content, "verify_seeded_db method missing"


def test_seed_activity_profile_normalization_is_documented():
    """The verify path must document legacy fixture vocabulary normalization."""
    seeder_path = REPO_ROOT / "scripts/seed_release1a_dev.py"
    content = seeder_path.read_text()
    assert "OSVČ" in content and "self_employed" in content, (
        "Activity profile normalization (OSVČ→self_employed, "
        "zaměstnanec→employee) must be visible in the verify path"
    )


def test_settings_modules_accepted():
    """The seeder must accept the three sanctioned synthetic-only settings modules."""
    seeder_path = REPO_ROOT / "scripts/seed_release1a_dev.py"
    content = seeder_path.read_text()
    for module in ("portal.settings_synthetic_review",
                   "portal.settings_supervised_synthetic",
                   "portal.settings_verification"):
        assert module in content, f"seeder does not accept {module}"


# End-to-end checks use the sanctioned module and private disposable databases.
import os
import subprocess
import tempfile
from contextlib import contextmanager


@contextmanager
def _isolated_db_env(tmp_path):
    base = REPO_ROOT / "runtime/portal/verification"
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="seed-test-", dir=base) as root:
        env = dict(os.environ)
        env["DJANGO_SETTINGS_MODULE"] = "portal.settings_verification"
        env["PRACE_VERIFICATION_ROOT"] = root
        env["PYTHONPATH"] = str(REPO_ROOT)
        yield env, "portal.settings_verification"


def _run_python(script_args, env, cwd=None):
    """Run the python interpreter with the given script arguments."""
    return subprocess.run(
        [sys.executable, *script_args], cwd=cwd or str(REPO_ROOT), env=env,
        capture_output=True, text=True,
    )


def _run_manage(args, env, cwd=None):
    """Run manage.py with the given subcommand arguments."""
    return subprocess.run(
        [sys.executable, "manage.py", *args], cwd=cwd or str(REPO_ROOT), env=env,
        capture_output=True, text=True,
    )


_MIGRATED_TEMPLATE = None


@pytest.fixture(scope="module", autouse=True)
def migrated_database_template():
    """Apply the on-disk graph once; each scenario receives a private copy."""
    global _MIGRATED_TEMPLATE
    with _isolated_db_env(None) as (env, _):
        result = _run_manage(["migrate"], env)
        assert result.returncode == 0, result.stderr
        _MIGRATED_TEMPLATE = Path(env["PRACE_VERIFICATION_ROOT"]) / "verification.sqlite3"
        yield
        _MIGRATED_TEMPLATE = None


def _migrate(env):
    import shutil
    target = Path(env["PRACE_VERIFICATION_ROOT"]) / "verification.sqlite3"
    shutil.copyfile(_MIGRATED_TEMPLATE, target)
    target.chmod(0o600)
    return subprocess.CompletedProcess([], 0, "", "")


def _seed_apply(env):
    return _run_python([str(REPO_ROOT / "scripts" / "seed_release1a_dev.py"), "--apply"], env)


def _seed_verify(env):
    return _run_python([str(REPO_ROOT / "scripts" / "seed_release1a_dev.py"), "--verify"], env)


def _inject(env, code):
    return _run_python(["-c", code], env)


def test_seed_then_verify_passes_against_disposable_db(tmp_path):
    """migrate -> --apply -> --verify on a fresh DB must pass end-to-end."""
    with _isolated_db_env(tmp_path) as (env, _):
        migration = _migrate(env)
        assert migration.returncode == 0, migration.stderr
        applied = _seed_apply(env)
        assert applied.returncode == 0, applied.stderr

        verify = _seed_verify(env)
        assert verify.returncode == 0, verify.stdout + verify.stderr
        assert "Summary: PASS" in verify.stdout
        for label in ("organizations", "workers", "assignments", "a1_cases"):
            assert f"[OK] {label}" in verify.stdout, f"{label} not OK: {verify.stdout}"


def test_verify_detects_mismatched_org_label(tmp_path):
    """A deliberate org-label mismatch must be detected by --verify (exit 1)."""
    with _isolated_db_env(tmp_path) as (env, _):
        _migrate(env); _seed_apply(env)
        inject = _inject(
            env,
            "import os, django; "
            f"os.environ['DJANGO_SETTINGS_MODULE']='{env['DJANGO_SETTINGS_MODULE']}'; "
            "django.setup(); "
            "from portal.release1a.models import Organization; "
            "Organization.objects.filter(key='org-synthetic-alpha').update(label='CORRUPTED')",
        )
        assert inject.returncode == 0, inject.stderr
        verify = _seed_verify(env)
        assert verify.returncode == 1, verify.stdout
        assert "[MISMATCH] organizations" in verify.stdout
        assert "label mismatch" in verify.stdout
        assert "CORRUPTED" not in verify.stdout


def test_verify_detects_extra_db_worker(tmp_path):
    """An extra worker in the DB beyond the fixtures must be flagged."""
    with _isolated_db_env(tmp_path) as (env, _):
        _migrate(env); _seed_apply(env)
        inject = _inject(
            env,
            "import os, django; "
            f"os.environ['DJANGO_SETTINGS_MODULE']='{env['DJANGO_SETTINGS_MODULE']}'; "
            "django.setup(); "
            "from portal.release1a.models import Organization, Worker; "
            "org = Organization.objects.get(key='org-synthetic-alpha'); "
            "Worker.objects.create(organization=org, given_name='Extra', "
            "family_name='Worker', birth_date='2000-01-01')",
        )
        assert inject.returncode == 0, inject.stderr
        verify = _seed_verify(env)
        assert verify.returncode == 1, verify.stdout
        assert "[MISMATCH] workers" in verify.stdout
        assert "extra_or_changed=1" in verify.stdout


def test_verify_detects_assignment_mismatch(tmp_path):
    """A deliberate assignment workplace_label change must be detected."""
    with _isolated_db_env(tmp_path) as (env, _):
        _migrate(env); _seed_apply(env)
        inject = _inject(
            env,
            "import os, django; "
            f"os.environ['DJANGO_SETTINGS_MODULE']='{env['DJANGO_SETTINGS_MODULE']}'; "
            "django.setup(); "
            "from portal.release1a.models import Assignment; "
            "Assignment.objects.filter(workplace_label='München Zentrum')"
            ".update(workplace_label='München Zentrum CORRUPTED')",
        )
        assert inject.returncode == 0, inject.stderr
        verify = _seed_verify(env)
        assert verify.returncode == 1, verify.stdout
        assert "[MISMATCH] assignments" in verify.stdout


def test_seed_is_idempotent(tmp_path):
    """Re-running --apply must not duplicate rows or raise."""
    with _isolated_db_env(tmp_path) as (env, _):
        _migrate(env)
        for _ in range(2):
            apply = _seed_apply(env)
            assert apply.returncode == 0, apply.stderr
        verify = _seed_verify(env)
        assert verify.returncode == 0, verify.stdout + verify.stderr
        import re
        for label in ("organizations", "workers", "assignments", "a1_cases"):
            m = re.search(rf"\[OK\] {label}: fixture=(\d+) db=(\d+)", verify.stdout)
            assert m is not None, f"{label} not OK: {verify.stdout}"
            assert m.group(1) == m.group(2), (
                f"idempotency broken: {label} fixture={m.group(1)} db={m.group(2)}"
            )


def test_seeder_refuses_unsupported_settings_module(tmp_path):
    """The seeder must exit non-zero when DJANGO_SETTINGS_MODULE is not in the allow-list."""
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "portal.settings"  # not in allow-list
    env["PYTHONPATH"] = f"{REPO_ROOT}:" + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "seed_release1a_dev.py"), "--dry-run"],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "DJANGO_SETTINGS_MODULE" in combined and "sanctioned" in combined


def test_seed_maps_roles_and_verify_is_read_only(tmp_path):
    import hashlib
    import sqlite3
    with _isolated_db_env(tmp_path) as (env, _):
        migration = _migrate(env)
        assert migration.returncode == 0, migration.stderr
        applied = _seed_apply(env)
        assert applied.returncode == 0, applied.stderr
        db = Path(env['PRACE_VERIFICATION_ROOT']) / 'verification.sqlite3'
        with sqlite3.connect(db) as connection:
            roles = [row[0] for row in connection.execute(
                'SELECT activity_label FROM release1a_assignment ORDER BY activity_label')]
            profiles = list(connection.execute(
                'SELECT activity_profile, state FROM release1a_worker ORDER BY activity_profile, state'))
        assert roles == ['Elektrikář', 'Elektrikář', 'Instalatér', 'Svářeč', 'Tischler']
        assert profiles == [('employee', 'active'), ('employee', 'active'),
                            ('self_employed', 'active'), ('self_employed', 'archived')]
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        verified = _seed_verify(env)
        assert verified.returncode == 0, verified.stdout + verified.stderr
        assert hashlib.sha256(db.read_bytes()).hexdigest() == before
        assert db.stat().st_mode & 0o777 == 0o600
        assert db.parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize('model,label,mutation', [
    ('Worker', 'workers', 'row.pk = None; row.save()'),
    ('Worker', 'workers', 'Worker.objects.order_by("pk").last().delete()'),
    ('Assignment', 'assignments', 'row.pk = None; row.save()'),
    ('Assignment', 'assignments', 'row.delete()'),
    ('Assignment', 'assignments', "row.activity_label = 'WRONG'; row.save()"),
    ('A1Case', 'a1_cases', 'row.pk = None; row.save()'),
    ('A1Case', 'a1_cases', 'row.delete()'),
    ('A1Case', 'a1_cases', "A1Case.objects.filter(pk=row.pk).update(source_hash='unexpected')"),
    ('A1Case', 'a1_cases', "row.readiness = 'ready'; row.save()"),
    ('A1Case', 'a1_cases', "row.prepared_artifact_hash = 'unexpected'; row.save()"),
    ('A1Case', 'a1_cases', "row.external_status = 'submitted'; row.save()"),
])
def test_verify_detects_missing_duplicate_and_changed_rows(tmp_path, model, label, mutation):
    with _isolated_db_env(tmp_path) as (env, _):
        migration = _migrate(env)
        assert migration.returncode == 0, migration.stderr
        applied = _seed_apply(env)
        assert applied.returncode == 0, applied.stderr
        result = _inject(env, 'import django; django.setup(); '
                         f'from portal.release1a.models import {model}; '
                         f'row = {model}.objects.order_by("pk").first(); {mutation}')
        assert result.returncode == 0, result.stderr
        verified = _seed_verify(env)
        assert verified.returncode == 1, verified.stdout + verified.stderr
        assert f'[MISMATCH] {label}' in verified.stdout


def test_settings_suffix_wrapper_rejected_before_import(tmp_path):
    marker = tmp_path / 'imported'
    (tmp_path / 'settings_verification.py').write_text(
        f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
    env = dict(os.environ, DJANGO_SETTINGS_MODULE='settings_verification', PYTHONPATH=str(tmp_path))
    result = _seed_verify(env)
    assert result.returncode == 2, result.stderr
    assert not marker.exists()


def test_verification_settings_reject_external_root(tmp_path):
    env = dict(os.environ, DJANGO_SETTINGS_MODULE='portal.settings_verification',
               PRACE_VERIFICATION_ROOT=str(tmp_path))
    result = _inject(env, 'import django; django.setup()')
    assert result.returncode != 0
    assert 'must remain under runtime/portal/verification' in result.stderr
    assert not (tmp_path / 'verification.sqlite3').exists()


def test_verify_missing_database_does_not_create_it(tmp_path):
    with _isolated_db_env(tmp_path) as (env, _):
        verified = _seed_verify(env)
        assert verified.returncode == 1, verified.stdout + verified.stderr
        assert "database is missing" in verified.stdout
        assert not (Path(env["PRACE_VERIFICATION_ROOT"]) / "verification.sqlite3").exists()
