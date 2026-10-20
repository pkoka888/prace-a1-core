#!/bin/bash
set -euo pipefail
ROOT="$(pwd)"
PYTHON_BIN="${ROOT}/venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then PYTHON_BIN="python3"; fi
# Validate all active CLI agent dirs (opencode, kilo CLI, kilo-code extension, cline, pi, codex, claude, .agents)
echo "Checking CLI/agent dir configurations for drifts..."
if [[ -f "$ROOT/scripts/audit_agent_dirs.py" ]]; then
  "$PYTHON_BIN" "$ROOT/scripts/audit_agent_dirs.py" --check --scope mcp || {
    echo "DRIFT DETECTED: agent-dir audit failed (high-severity MCP/config finding)"
    exit 1
  }
else
  echo "SKIP: audit_agent_dirs.py not found (not required for this repo)"
fi
# Kilo has two products with separate config files; both must be drift-free.
#   kilo CLI            -> ~/.config/kilo/kilo.json (+ .jsonc overlay)
#   kilo-code extension -> <workspace>/.kilo/mcp.json
# Missing files are skipped by grep (2>/dev/null), so a legacy path that does
# not exist is simply not scanned rather than silently passing as "clean".
for config in \
  "$HOME/.config/kilo/kilo.json" \
  "$HOME/.config/kilo/kilo.jsonc" \
  "$ROOT/.kilo/mcp.json" \
  "$HOME/.opencode/mcp.json" \
  "$HOME/.kilo/mcp.json"; do
  if grep -q "servers-infra-core" "$config" 2>/dev/null; then
    echo "DRIFT DETECTED: stale path in $config"
    exit 1
  fi
done
# Verify no inline secret patterns in CLI MCP/config files.
# These files must reference secrets via `{env:VAR}` placeholders, never inline
# values, so an inline `sk-...`/`apiKey=` here is drift. The pattern is matched
# case-insensitively (`-i`), so `API_KEY=`, `apiKey` and `api-key` are all
# caught: the key name in the regex is lowercase and the char classes only cover
# the value, so without `-i` the upper- and camel-case spellings would slip
# through. (`-q` = quiet, `-E` = ERE; note `-Equ` was a bug — `-u` is the
# obsolete `--unix-byte-offsets` and only emitted a warning.)
# Dedicated credential stores (opencode env/auth.json, cline secrets.json,
# pi auth.json) intentionally contain real keys and are NOT scanned here — they
# are tracked as an existence/permission inventory in audit_agent_dirs.py
# instead, so this hook cannot false-positive on the operator's own keyring.
SECRET_RE='sk-[A-Za-z0-9_-]{20,}|api[_-]?key[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_./+-]{20,}'
SECRET_PATHS=(
  "$HOME/.config/opencode/opencode.jsonc"
  "$HOME/.config/kilo/kilo.json"
  "$HOME/.config/kilo/kilo.jsonc"
  "$HOME/.opencode/mcp.json"
  "$HOME/.kilo/mcp.json"
  "$ROOT/.kilo/mcp.json"
  "$HOME/.cline/data/settings/cline_mcp_settings.json"
  "$HOME/.pi/agent/settings.json"
)
if grep -Eqi "$SECRET_RE" "${SECRET_PATHS[@]}" 2>/dev/null; then
  echo "DRIFT DETECTED: inline secret pattern in CLI MCP config (use {env:VAR})"
  exit 1
fi
echo "PASS: CLI agent-dir configurations validated."
