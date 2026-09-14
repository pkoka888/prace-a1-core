#!/usr/bin/env python3
"""Select checks from this package's staged paths, never the whole commit.

Test-only edits use the owning test runner. Source, fixture and deleted-test
changes retain the existing integration checks. Tooling belongs to the Git
workflow package and is tested there. Selection itself never imports app code.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_change_packages import git, matches, nul_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTEST_BASE = (
    "env DJANGO_SETTINGS_MODULE=portal.settings_document_tests "
    "venv/bin/python -m pytest"
)
MANAGE_PY = (
    "env DJANGO_SETTINGS_MODULE=portal.settings_document_tests "
    "venv/bin/python manage.py test"
)
# Browser journey is a real-browser test that requires a different
# settings module and Playwright/Chromium to be installed. The
# isolated entrypoint is scripts/playwright_smoke.py.
BROWSER_TESTS = {
    "tests/document_web/test_browser_journey.py",
}
BROWSER_PY = (
    "env DJANGO_SETTINGS_MODULE=portal.settings_browser_tests "
    "venv/bin/python scripts/playwright_smoke.py"
)
PURE_INTEGRATION_TESTS = {
    "tests/test_j4_artifacts.py", "tests/test_runtime_contract.py",
    "tests/test_a1_input_artifacts.py", "tests/m2/test_synthetic_containment.py",
}


def staged_paths(root: Path = REPO_ROOT) -> list[str]:
    catalog = json.loads(git(root, "show", ":change-packages.yml"))
    package = catalog["packages"]["shared_document_portal"]
    paths = nul_paths(git(root, "diff", "--cached", "--name-only", "--no-renames", "-z"))
    return sorted(p for p in paths if
                  any(matches(p, r) for r in package.get("paths", [])) or
                  any(matches(p, r, prefix=True) for r in package.get("prefixes", [])))


def django_test(path: str) -> bool:
    return (path.startswith("tests/document_web/") or
            path.startswith("tests/m2/") and path != "tests/m2/test_synthetic_containment.py" or
            path in {"tests/test_j4_minimum.py", "tests/test_j4_service.py"})


def select(paths: list[str], root: Path = REPO_ROOT) -> list[str]:
    django_routes: set[str] = set()
    pytest_routes: set[str] = set()
    browser_routes: set[str] = set()
    needs_broad = False
    for path in paths:
        # Documentation outside application templates has no runtime behavior.
        if path.startswith(("docs/", "plans/")) or path.endswith(".md"):
            continue
        candidate = root / path
        if (path.startswith("tests/") and candidate.name.startswith("test_")
                and candidate.suffix == ".py" and candidate.is_file()):
            if path in BROWSER_TESTS:
                browser_routes.add(path)
            elif django_test(path):
                django_routes.add(path[:-3].replace("/", "."))
            else:
                pytest_routes.add(path)
        else:
            # Includes helpers/__init__, fixtures, deleted tests and owned source.
            needs_broad = True

    commands = []
    if needs_broad:
        broad = _broad_manage_test()
        commands.append(broad)
        django_routes.difference_update(shlex.split(broad))
        pytest_routes.update(PURE_INTEGRATION_TESTS)
    if django_routes:
        commands.append(f"{MANAGE_PY} " + shlex.join(sorted(django_routes)) + " --noinput -v 1")
    if pytest_routes:
        commands.append(f"{PYTEST_BASE} -q " + shlex.join(sorted(pytest_routes)))
    if browser_routes:
        # Browser tests run via their isolated entrypoint so the
        # current settings module matches the test (settings_browser_tests)
        # and unavailable browsers are reported as a separate exit
        # rather than masked by an all-skipped run.
        commands.append(BROWSER_PY)
    return commands


def _broad_manage_test() -> str:
    return (
        f"{MANAGE_PY} tests.document_web.test_intake tests.document_web.test_ocr_worker "
        "tests.document_web.test_field_review tests.document_web.test_identity_review "
        "tests.document_web.test_legacy_reconciliation tests.document_web.test_inbox "
        "tests.document_web.test_identity tests.document_web.test_a1_exports "
        "tests.document_web.test_a1_cohort_exports "
        "tests.document_web.test_a1_input_publication tests.document_web.test_input_bundle_bo "
        "tests.document_web.test_a1_drafts tests.document_web.test_a1_generation_access "
        "tests.document_web.test_a1_generation_confirmation "
        "tests.document_web.test_a1_drafts_postgres "
        "tests.document_web.test_a1_exports_postgres "
        "tests.document_web.test_identity_postgres tests.m2.test_views "
        "tests.m2.test_release1a_vertical tests.m2.test_review_fixes "
        "tests.m2.test_j4_delivery tests.test_j4_minimum tests.m2.test_readiness "
        "--noinput -v 1"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--paths-json", help="Exact paths supplied by the owning package receipt")
    args = parser.parse_args()
    paths = json.loads(args.paths_json) if args.paths_json is not None else staged_paths(args.root)
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        parser.error("paths must be a JSON array of strings")
    for command in select(paths, args.root):
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
