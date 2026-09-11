#!/usr/bin/env bash
# scripts/rehearse_dev_local.sh — convenient wrapper for local
# single-operator rehearsal. Generates a fresh synthetic secret on
# every invocation, exports the full supervised-synthetic env
# block, and forwards to scripts/rehearse_synthetic_site.sh.
#
# Usage:
#   bash scripts/rehearse_dev_local.sh prepare
#   bash scripts/rehearse_dev_local.sh provision
#   bash scripts/rehearse_dev_local.sh start
#   bash scripts/rehearse_dev_local.sh smoke
#   bash scripts/rehearse_dev_local.sh stop
#   bash scripts/rehearse_dev_local.sh logs
#   bash scripts/rehearse_dev_local.sh status
#
# The bind defaults to 127.0.0.1:8001. Override with PRACE_BIND.
# The runtime root defaults to runtime/portal/supervised-development.
# Override with PRACE_RUNTIME_ROOT.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${PRACE_RUNTIME_ROOT:-$REPO_ROOT/runtime/portal/supervised-development}"
export PRACE_RUNTIME_ROOT="$RUNTIME_ROOT"
export PRACE_SECRET_KEY="${PRACE_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')}"
export PRACE_ALLOWED_HOSTS="${PRACE_ALLOWED_HOSTS:-localhost,127.0.0.1}"
export PRACE_BIND="${PRACE_BIND:-127.0.0.1:8001}"

cd "$REPO_ROOT"
bash scripts/rehearse_synthetic_site.sh "$@"
