#!/usr/bin/env bash
# scripts/rehearse_dev_local.sh — convenient wrapper for the local
# supervised-synthetic rehearsal. Exports the full env block, keeps
# the signing key stable across ordinary invocations/restarts, and
# forwards to scripts/rehearse_synthetic_site.sh.
#
# Usage:
#   bash scripts/rehearse_dev_local.sh prepare
#   bash scripts/rehearse_dev_local.sh provision
#   bash scripts/rehearse_dev_local.sh start
#   bash scripts/rehearse_dev_local.sh smoke
#   bash scripts/rehearse_dev_local.sh workflow
#   bash scripts/rehearse_dev_local.sh stop
#   bash scripts/rehearse_dev_local.sh logs
#   bash scripts/rehearse_dev_local.sh status
#   bash scripts/rehearse_dev_local.sh rollback
#
# Bind defaults to 127.0.0.1:8001. Override with PRACE_BIND.
# Runtime root defaults to runtime/portal/supervised-development.
# Override with PRACE_RUNTIME_ROOT.
#
# The signing key persists in $PRACE_RUNTIME_ROOT/.secret_key (mode 0600,
# operator-owned) so stop/start does not invalidate existing Django
# sessions. Override with PRACE_SECRET_KEY to rotate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${PRACE_RUNTIME_ROOT:-$REPO_ROOT/runtime/portal/supervised-development}"
export PRACE_RUNTIME_ROOT="$RUNTIME_ROOT"

# Validate the runtime root with the canonical helpers BEFORE any
# mkdir / printf. This rejects symlinks, out-of-tree paths, and
# permissive modes; it is the same confinement check the canonical
# rehearsal script applies.
umask 077
RUNTIME_ROOT_ABS="$(cd "$RUNTIME_ROOT" 2>/dev/null && pwd || true)"
if [ -z "$RUNTIME_ROOT_ABS" ]; then
    mkdir -p "$RUNTIME_ROOT"
    chmod 700 "$RUNTIME_ROOT"
    RUNTIME_ROOT_ABS="$(cd "$RUNTIME_ROOT" && pwd)"
fi
PRACE_RUNTIME_ROOT="$RUNTIME_ROOT_ABS"
export PRACE_RUNTIME_ROOT

if ! "$REPO_ROOT/venv/bin/python" - <<'PY' >/dev/null
from pathlib import Path
import sys
sys.path.insert(0, "$REPO_ROOT")
from portal.release1a.runtime_safety import confined_root
try:
    confined_root("$RUNTIME_ROOT_ABS")
except ValueError as exc:
    print(f"FAIL: runtime root is not inside an approved supervised-* layout: {exc}")
    sys.exit(1)
PY
then
    printf 'FAIL: runtime root %s is not inside an approved supervised-* layout\n' "$RUNTIME_ROOT_ABS" >&2
    exit 1
fi

# Stable signing key across ordinary invocations. The file is
# operator-owned inside the confined runtime root; if it does not
# exist yet, mint a fresh one and persist it with mode 0600.
SECRET_FILE="$PRACE_RUNTIME_ROOT/.secret_key"
if [ -n "${PRACE_SECRET_KEY:-}" ]; then
    : # caller-supplied secret wins
elif [ -s "$SECRET_FILE" ]; then
    PRACE_SECRET_KEY="$(cat "$SECRET_FILE")"
else
    PRACE_SECRET_KEY="$("$REPO_ROOT/venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(50))')"
    printf '%s' "$PRACE_SECRET_KEY" > "$SECRET_FILE"
    chmod 0600 "$SECRET_FILE"
fi
export PRACE_SECRET_KEY

export PRACE_ALLOWED_HOSTS="${PRACE_ALLOWED_HOSTS:-localhost,127.0.0.1}"
export PRACE_BIND="${PRACE_BIND:-127.0.0.1:8001}"

cd "$REPO_ROOT"
bash scripts/rehearse_synthetic_site.sh "$@"