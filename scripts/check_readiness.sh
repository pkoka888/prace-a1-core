#!/usr/bin/env bash
# Scoped unprivileged diagnostics; never source the service EnvironmentFile.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/venv/bin/python"
exec "$PYTHON_BIN" "$REPO_ROOT/scripts/validate_delivery_readiness.py" "$@"
