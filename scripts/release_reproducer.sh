#!/bin/bash
# Export exactly the requested Git tree; acceptance state stays outside source.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/venv/bin/python"
exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_release_reproducer.py" "$@"
