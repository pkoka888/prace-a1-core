"""Regression guard: Playwright networkidle must not reappear in test or automation code.

D-1 replaced every ``wait_until="networkidle"`` and
``page.wait_for_load_state("networkidle")`` with ``wait_until="load"`` plus an
explicit selector wait. This test scans the committed-source paths that drive
the browser automation and fails if any Playwright ``networkidle`` literal is
found (matches the API call patterns, not incidental mentions in prose).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# Paths to scan — test helpers, test suites, and browser automation scripts.
# node_modules/.git are excluded by ripgrep's default respects.
# The regression test itself is excluded to avoid self-match.
_SCAN_PATHS = (
    "tests/_rehearse_workflow_browser.py",
    "tests/document_web/",
    "scripts/axe_check.sh",
    "scripts/smoke_synthetic_review_ui.mjs",
    "scripts/playwright_smoke.py",
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_networkidle_in_automation() -> None:
    """Fail if any Playwright networkidle API call is present in scanned paths."""
    hits: list[str] = []
    for rel in _SCAN_PATHS:
        target = _REPO_ROOT / rel
        if not target.exists():
            continue
        try:
            # Match only Playwright API calls: wait_until="networkidle" or
            # wait_for_load_state("networkidle") / waitForLoadState("networkidle")
            result = subprocess.run(
                [
                    "rg",
                    "-n",
                    r'wait_until\s*=\s*"networkidle"|wait_for_load_state\s*\(\s*"networkidle"|waitForLoadState\s*\(\s*"networkidle"',
                    str(target),
                ],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise RuntimeError("ripgrep (rg) is required but not installed")
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"rg scan timed out on {rel}") from exc
        if result.returncode == 0 and result.stdout.strip():
            hits.append(result.stdout.strip())

    assert not hits, (
        "networkidle references found in browser automation code.\n"
        "D-1 requires wait_until='load' plus an explicit selector wait.\n"
        "Offending matches:\n" + "\n".join(hits)
    )
