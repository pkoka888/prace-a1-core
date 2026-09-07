#!/bin/bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$(git rev-parse --git-path hooks)"
CONFIGURED="$(git config --get core.hooksPath || test "$?" -eq 1)"
if [[ -n "$CONFIGURED" ]]; then
    echo "HOOK_PATH_ALREADY_CONFIGURED" >&2
    exit 1
fi
mkdir -p "$HOOK_DIR"
# Preserve a previous installation before replacing it.
if [[ -f "$HOOK_DIR/pre-commit" ]] && ! cmp -s "$ROOT/scripts/pre-commit" "$HOOK_DIR/pre-commit"; then
    BACKUP="$(mktemp "$HOOK_DIR/pre-commit.previous.XXXXXXXX")"
    cp "$HOOK_DIR/pre-commit" "$BACKUP"
fi
install -m 755 "$ROOT/scripts/pre-commit" "$HOOK_DIR/pre-commit"
echo "Repository pre-commit hook installed."
