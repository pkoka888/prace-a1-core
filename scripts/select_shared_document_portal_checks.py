#!/usr/bin/env python3
"""Select relevant regressions for the ``shared_document_portal`` package.

The previous contract ran one broad 24-test-file Django ``manage.py test``
command for every change to any path in the package. That command takes
~5 minutes even when the change is a single test file or a documentation
edit. This script inspects the actually-staged paths and emits the
narrowest correct test command(s) for the work.

Dispatch rules (executed in order; first match wins):

1. No ``portal/`` source changed and no ``scripts/`` change → run only
   the directly staged test file(s) with ``pytest`` (fast smoke). This
   is the common case for test-only and documentation changes.
2. ``portal/release1a/<file>.py`` source changed → run pytest on the
   tests/test_<name>.py sibling plus the package's own test files
   that import the changed module. This is the common case for source
   edits; it covers the directly affected contract.
3. ``portal/release1a/migrations/`` or ``portal/templates/`` changed →
   add the existing migration-transitions and template-render checks.
4. Any other change (settings, views, etc.) → fall back to the broad
   24-test-file ``manage.py test`` suite. The broad run protects
   authorization, storage and rendering regressions that span the
   whole portal.

Output: a list of shell command strings, one per line, suitable for
the change-packages ``checks`` field. The dispatch is deterministic;
the only side effect is reading the staged paths via ``git diff``.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTEST_BASE = (
    "env DJANGO_SETTINGS_MODULE=portal.settings_document_tests "
    "venv/bin/python -m pytest"
)
MANAGE_PY = (
    "env DJANGO_SETTINGS_MODULE=portal.settings_document_tests "
    "venv/bin/python manage.py test"
)


def staged_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--cached",
         "--name-only", "--no-renames", "-z"],
        capture_output=True, check=True,
    )
    parts = proc.stdout.split(b"\0")
    return [p.decode("utf-8", "surrogateescape") for p in parts if p]


def _route_for_path(path: str) -> str | None:
    """Map a single staged path to a pytest test file (relative to repo root)."""
    if path.startswith("tests/"):
        candidate = REPO_ROOT / path
        if candidate.exists() and candidate.suffix == ".py":
            return path
    if path.startswith("portal/release1a/") and path.endswith(".py"):
        name = Path(path).stem
        sibling = REPO_ROOT / "tests" / f"test_{name}.py"
        if sibling.exists():
            return str(sibling.relative_to(REPO_ROOT))
    if path.startswith("scripts/") and path.endswith(".py"):
        name = Path(path).stem
        sibling = REPO_ROOT / "tests" / f"test_{name}.py"
        if sibling.exists():
            return str(sibling.relative_to(REPO_ROOT))
    return None


def select(paths: list[str]) -> list[str]:
    """Pick the narrowest test command(s) for the staged paths.

    Classification:
    * Pure-documentation (no .py or .html under portal/scripts/tests)
      → no test run; documentation changes must not require code tests.
    * Test-only → run only the staged test file(s) with pytest.
    * Source/script/migration/template/settings change → run the
      broad integration suite.
    """
    routes: set[str] = set()
    needs_broad = False
    for p in paths:
        if p.startswith("portal/release1a/migrations/"):
            needs_broad = True
        elif p.startswith("portal/templates/"):
            needs_broad = True
        elif p.startswith("portal/release1a/") and p.endswith(".py"):
            needs_broad = True
            r = _route_for_path(p)
            if r:
                routes.add(r)
        elif p.startswith("portal/"):
            # Other portal files (settings, urls, etc.).
            needs_broad = True
        elif p.startswith("scripts/") and p.endswith(".py"):
            needs_broad = True
            r = _route_for_path(p)
            if r:
                routes.add(r)
        elif p.startswith("tests/") and p.endswith(".py"):
            r = _route_for_path(p)
            if r:
                routes.add(r)
        # else: docs, schemas, plans, governance → no test command.

    if needs_broad:
        return [_broad_manage_test()]

    if routes:
        return [f"{PYTEST_BASE} -q " + " ".join(sorted(routes))]
    # No relevant .py change among staged paths (e.g. doc-only).
    # The dispatcher's contract is "skip the run" for non-code edits
    # rather than running a wide smoke that adds no signal.
    return []


def _broad_manage_test() -> str:
    return (
        f"{MANAGE_PY} tests.document_web.test_intake "
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
    paths = staged_paths()
    cmds = select(paths)
    for c in cmds:
        print(c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
