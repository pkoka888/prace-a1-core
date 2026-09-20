#!/bin/bash
# Export exactly the requested Git tree; acceptance state stays outside source.
set -euo pipefail
if [ "$#" -lt 1 ]; then
    echo "Usage: release_reproducer.sh <commit-sha> [--include-a1]" >&2
    exit 2
fi
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/venv/bin/python"
exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_release_reproducer.py" "$@"
