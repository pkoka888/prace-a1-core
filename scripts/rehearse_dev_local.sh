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
#
# Confinement contract: the runtime root is validated against the RAW
# path before any mkdir / chmod / write. Values reach canonical
# helpers exclusively through argv/environment — never through shell
# interpolation into Python source. A pre-existing symlink root, a
# symlinked .secret_key, a traversal, or a path outside the approved
# runtime/portal/supervised-* subtree is refused without mutating
# anything.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/venv/bin/python"
RUNTIME_ROOT="${PRACE_RUNTIME_ROOT:-$REPO_ROOT/runtime/portal/supervised-development}"
APPROVED_RUNTIME_PARENT="$REPO_ROOT/runtime/portal"

# Private creation policy for the wrapper's own files (.secret_key).
umask 077

# True when the raw path is a symlink (does not follow the link).
raw_is_symlink() {
    [ -L "$1" ]
}

# Reject any raw-path symlink component. Mirrors the canonical
# confinement contract (portal.release1a.runtime_safety.no_symlinks,
# expressed for shell) that scripts/rehearse_synthetic_site.sh uses:
# a mid-path or leaf symlink must be refused before mkdir/write so the
# script cannot silently follow a link and mutate a foreign target.
reject_path_symlinks() {
    local target="$1"
    local -a parts
    IFS='/' read -r -a parts <<< "$target"
    local current=""
    local part
    for part in "${parts[@]}"; do
        if [ -z "$part" ]; then
            current="/"
            continue
        fi
        if [ -z "$current" ] || [ "$current" = "/" ]; then
            current="/$part"
        else
            current="$current/$part"
        fi
        if [ -L "$current" ]; then
            echo "FAIL: $target contains symlink component $current" >&2
            return 1
        fi
    done
    return 0
}

# Raw-path layout contract, evaluated BEFORE any mkdir / chmod / write.
validate_runtime_root_layout() {
    case "$RUNTIME_ROOT" in
        /*) ;;
        *) echo "FAIL: $RUNTIME_ROOT must be an absolute path" >&2; exit 1 ;;
    esac
    case "$RUNTIME_ROOT" in
        *"/../"*|*"/.."|*"../"*)
            echo "FAIL: $RUNTIME_ROOT contains a parent-directory traversal" >&2
            exit 1
            ;;
    esac
    reject_path_symlinks "$RUNTIME_ROOT" || exit 1
    if raw_is_symlink "$RUNTIME_ROOT"; then
        echo "FAIL: $RUNTIME_ROOT is a symlink" >&2
        exit 1
    fi
    local parent leaf
    parent="$(dirname "$RUNTIME_ROOT")"
    leaf="$(basename "$RUNTIME_ROOT")"
    if [ "$parent" != "$APPROVED_RUNTIME_PARENT" ] \
            || [ "${leaf#supervised-}" = "$leaf" ]; then
        echo "FAIL: $RUNTIME_ROOT must be $APPROVED_RUNTIME_PARENT/supervised-* (got parent=$parent leaf=$leaf)" >&2
        exit 1
    fi
    if [ -e "$RUNTIME_ROOT" ] && [ ! -d "$RUNTIME_ROOT" ]; then
        echo "FAIL: $RUNTIME_ROOT exists and is not a directory" >&2
        exit 1
    fi
    # Pre-existing child symlinks are refused before any mkdir, mirroring
    # the canonical F2 guard.
    local child
    for child in storage media static cache tmp logs; do
        if [ -L "$RUNTIME_ROOT/$child" ]; then
            echo "FAIL: $RUNTIME_ROOT/$child is a pre-existing symlink" >&2
            exit 1
        fi
    done
}

validate_runtime_root_layout

# Create the confined root only AFTER the raw-path layout passed. The
# canonical confined_root helper (invoked below via argv) re-validates
# owner + 0700 mode.
if [ ! -d "$RUNTIME_ROOT" ]; then
    mkdir -p "$RUNTIME_ROOT"
    chmod 700 "$RUNTIME_ROOT"
fi

# Canonical confinement validation. Values travel through argv so the
# quoted heredoc never interpolates shell variables. confined_root
# re-runs no_symlinks, parent/name, owner and 0700-mode checks.
if ! "$PYTHON_BIN" - "$REPO_ROOT" "$RUNTIME_ROOT" <<'PY' >/dev/null
import sys
sys.path.insert(0, sys.argv[1])
from portal.release1a.runtime_safety import confined_root
try:
    confined_root(sys.argv[2])
except ValueError as exc:
    print(f"FAIL: runtime root is not inside an approved supervised-* layout: {exc}")
    sys.exit(1)
PY
then
    printf 'FAIL: runtime root %s is not inside an approved supervised-* layout\n' "$RUNTIME_ROOT" >&2
    exit 1
fi

export PRACE_RUNTIME_ROOT="$RUNTIME_ROOT"

# Stable signing key across ordinary invocations. The file is
# operator-owned inside the confined runtime root. A symlinked
# .secret_key is refused (the canonical settings module refuses one
# too); creation is atomic via a unique temp name + rename and never
# clobbers an existing or concurrent file.
SECRET_FILE="$PRACE_RUNTIME_ROOT/.secret_key"
if [ -n "${PRACE_SECRET_KEY:-}" ]; then
    : # caller-supplied secret wins
else
    if [ -L "$SECRET_FILE" ]; then
        echo "FAIL: $SECRET_FILE is a symlink; refusing to write through it" >&2
        exit 1
    fi
    if [ -s "$SECRET_FILE" ]; then
        PRACE_SECRET_KEY="$(cat "$SECRET_FILE")"
    else
        PRACE_SECRET_KEY="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_urlsafe(50))')"
        key_tmp="$(mktemp -p "$PRACE_RUNTIME_ROOT" ".secret_key.XXXXXX")"
        chmod 0600 "$key_tmp"
        printf '%s' "$PRACE_SECRET_KEY" > "$key_tmp"
        if ! mv -n "$key_tmp" "$SECRET_FILE"; then
            rm -f "$key_tmp"
            echo "FAIL: could not publish $SECRET_FILE (concurrent creation?)" >&2
            exit 1
        fi
        chmod 0600 "$SECRET_FILE"
    fi
fi
export PRACE_SECRET_KEY

export PRACE_ALLOWED_HOSTS="${PRACE_ALLOWED_HOSTS:-localhost,127.0.0.1}"
export PRACE_BIND="${PRACE_BIND:-127.0.0.1:8001}"

cd "$REPO_ROOT"
bash scripts/rehearse_synthetic_site.sh "$@"