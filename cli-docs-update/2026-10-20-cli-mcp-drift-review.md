# CLI MCP drift review — 2026-10-20

Scope: audit every active CLI's MCP configuration for drift (stale paths,
disabled servers, malformed args, env-interpolation misuse), verify the
pre-commit gate, and document the two-product Kilo architecture.

## What was verified empirically (not assumed)

| Check | Method | Result |
|---|---|---|
| Does kilo substitute `{env:VAR}` in `command` arrays? | isolated `KILO_CONFIG_CONTENT` probe + `kilo mcp list` | **Yes** — `echo brace:RESOLVED ...` (re-verified 2026-10-20) |
| Does opencode substitute `{env:VAR}` in `command` arrays? | isolated `OPENCODE_CONFIG_CONTENT` probe + `opencode mcp list` | **Yes** — same result (re-verified 2026-10-20) |
| Is `${env:VAR}` valid in `command` arrays? | same probes | **No** — the `{env:VAR}` part resolves but a stray `$` remains (`echo ... dollar:$RESOLVED ...`) |
| Which config does the `kilo` CLI read? | `kilo debug paths` + `~/.config/kilo/kilo.json` | `~/.config/kilo/kilo.json` |
| Which config does the kilo-code VS Code extension read? | grep of `dist/extension.js` | `<workspace>/.kilo/mcp.json` |
| Which config does cline read? | cline docs (`/cline/cline`) | `~/.cline/data/settings/cline_mcp_settings.json` |

## Kilo has two products, two configs, no shared file

- **kilo CLI** → `~/.config/kilo/kilo.json` (schema `{"mcp": {...}}`)
- **kilo-code VS Code extension** → `<workspace>/.kilo/mcp.json` (schema `{"mcpServers": {...}}`)

They are independent. A fix in one does not affect the other. The repo
`.kilo/kilo.jsonc` is a project-level CLI config stub and is tracked; the
extension's `mcp.json` is absent from this repo and is reported at `info`
severity, not as a defect.

## Fixes applied

| File | Change | Verified |
|---|---|---|
| `~/.config/kilo/kilo.json` | filesystem MCP: `/workspace/servers-infra-core` → `/var/www/prace-v-nemecku.tvoje.info` | `kilo mcp list` → ✓ connected |
| `~/.opencode/mcp.json` | malformed `args: ["[\"${env:ROOT_DIR}\"]"]` → `["/var/www/prace-v-nemecku.tvoje.info"]` | file parses — but the file is **inert** (see Errata); it never influenced connectivity |
| `~/.cline/data/settings/cline_mcp_settings.json` | empty `mcpServers: {}` → filesystem server with hardcoded path | parses, 1 server |
| `~/.kilo/mcp.json` | removed `disabled: true` from filesystem/git/db/ci/taskmgr; `ROOT_DIR`/`REPO_DIR` → absolute path; `DATABASE_URL` → `${env:OP_EXPC_KEY}` (env value, correct) | parses |

## What was deliberately NOT done

- `${env:ROOT_DIR}` in `command`/`args` arrays was **not** adopted, and the
  outcome was still correct — but for a different reason than recorded on
  2026-10-20. `${env:...}` is not a valid form there: the inner `{env:...}`
  resolves and the leading `$` remains (`$/var/www/...`), so the server fails
  to start. The working alternatives are a hardcoded absolute path (what was
  chosen) or the single-brace `{env:VAR}`, which both CLIs substitute in
  `command`/`args` (verified 2026-10-20). Interpolation inside `environment`
  values was not re-verified in this pass.
- The repo `.kilo/mcp.json` was **not** created. The audit reports its absence
  at `info`; it is not CLI drift and not required for the CLI workflow.

## Audit script (`scripts/audit_agent_dirs.py`)

- `CLI_MCP_CONFIGS` now covers opencode, kilo_cli, kilo_code_extension, cline,
  pi, codex, claude — previously only opencode/kilo/cline/pi/codex/claude, and
  pi was never actually inspected despite being listed.
- New checks: `MCP_STALE_PATH`, `MCP_MALFORMED_ARGS`,
  `MCP_ENV_INTERPOLATION_UNHANDLED`, `MCP_SERVER_DISABLED`,
  `MCP_CONFIG_PARSE_ERROR`.
  The `MCP_ENV_INTERPOLATION_UNHANDLED` finding text originally claimed
  `${env:...}` "is passed through literally" and that the CLIs "only
  interpolate inside `environment` values" — both wrong; the text and the
  module comment were corrected on 2026-10-20 (mechanism and guidance only,
  the regex and severity are unchanged: `${env:...}` in arrays really is
  broken, just not for the stated reason).
- `--check --scope mcp` gates only CLI config drift. The pre-existing
  `INVALID_SKILL_CONTRACT` finding on untracked third-party
  `.opencode/skills/audit/SKILL.md` stays in the report but does not block
  commits — it is not CLI config drift and the file is not being committed.

## Errata — claims corrected on re-verification

Three 2026-10-20 statements did not survive re-checking on the same day and are
corrected above and in the audit script:

1. **`${env:...}` "passed through literally" — wrong.** Isolated
   `OPENCODE_CONFIG_CONTENT` / `KILO_CONFIG_CONTENT` probes (var name
   `PROBE_VAR`, value `RESOLVED`, `echo`), re-run against opencode 1.18.32 and
   kilo 7.7.9, show `echo brace:RESOLVED dollar:$RESOLVED plain`. So
   `{env:VAR}` **is** substituted in `command` arrays, and `${env:VAR}` resolves
   its inner substring leaving a stray `$`. The original probe likely used the
   wrong env-var name, so the token was not replaced.
2. **`~/.opencode/mcp.json` "server connects" — misattributed.** opencode never
   reads that file (0 `mcp.json` references in the binary; servers come from
   `~/.config/opencode/opencode.jsonc`). Editing it changed nothing; the
   connectivity observed in the original session came from `opencode.jsonc`.
   The file is inert.
3. **kilo-code extension config format — wrong.** There is no `{mcpServers}`
   `mcp.json`. Both the CLI and the extension read `~/.config/kilo/kilo.json`
   (flat `mcp.<name>` keys); the repo `.kilo/kilo.jsonc` is a tracked stub.
   The extension's legacy `mcpServers` paths (`.kilocode/mcp.json`,
   `.kilo/mcp.json`) are absent here and therefore inert.

## Re-verified inventory (2026-10-20)

CLI-doc entries and audit rows were reconciled against live configs:

- `~/.config/opencode/opencode.jsonc`: `context7`, `filesystem`, `github`,
  `gitlab`, `netbox`.
- `~/.config/kilo/kilo.json`: `context7`, `filesystem`, `firebase`, `github`,
  `gitlab`, `sequentialthinking`.
- `~/.opencode/mcp.json` (inert): `filesystem`, `git`.
- `~/.kilo/mcp.json` (inert legacy): `ci`, `database`, `filesystem`, `git`,
  `plane`, `taskmgr`.
- `~/.cline/data/settings/cline_mcp_settings.json`: `filesystem` only.

## Pre-commit hook (`.pre-commit-hooks/cli-agent-drift/check.sh`)

- Runs `audit_agent_dirs.py --check --scope mcp`.
- Checks `~/.config/kilo/kilo.json`, `~/.config/kilo/kilo.jsonc`,
  `<repo>/.kilo/mcp.json`, `~/.opencode/mcp.json` and `~/.kilo/mcp.json` for
  stale paths (the legacy `$ROOT/.kilo/mcp.json` branch is non-vacuous: missing
  files are skipped by `grep` rather than silently passing).
- Secret scan uses a case-insensitive pattern (catches `API_KEY=`, `apiKey`,
  `api-key`; see the `-Eqi` fix below) over **MCP/config files only** — opencode
  `opencode.jsonc`, kilo
  `kilo.json`/`kilo.jsonc`, legacy `~/.opencode/mcp.json` & `~/.kilo/mcp.json`,
  `<repo>/.kilo/mcp.json`, cline `cline_mcp_settings.json`, pi `settings.json`.
  These must reference secrets via `{env:VAR}`, so an inline value is drift.
  Dedicated credential stores (opencode `env`/`auth.json`, cline `secrets.json`/
  `providers.json`, pi `auth.json`) are **not** scanned — they hold real keys by
  design and scanning them only false-positives on the operator's own keyring;
  they are reported as an existence/permission inventory in the audit JSON/MD.
- **Passes** on the current tree.

## Audit script — model/skill checks added 2026-10-20

- `HARDCODED_GLOBAL_MODEL` (info): unsanctioned model ids in user-level configs
  (`~/.config/kilo/kilo.jsonc`: `kilo/kilo-auto/free`, `openrouter/openrouter/free`,
  `minimax/MiniMax-M3`, `minimax/MiniMax-M2.7`). Informational only — model
  choice is user preference, not repo drift.
- `PAID_MODEL_IN_PROJECT_CONFIG` (medium): explicitly `"type": "paid"` fallbacks
  in tracked `config/vision_models.json` (`minimax/minimax-01`,
  `minimax/minimax-m3`); `:free` variants skipped. Deliberately **excluded** from
  the `--scope mcp` gate (pre-existing owner decision).
- `MODEL_CONFIG_SECRET_PATTERN` (high): credential-like values in project model
  config; in the `--scope mcp` gate.
- `SECRET_GREP_COVERAGE_GAP` (medium): checks that `check.sh` greps every
  **MCP/config file** that must use `{env:VAR}` (`CLI_MCP_CONFIG_PATHS`);
  reports clean. Dedicated credential stores are inventoried
  (`CLI_CREDENTIAL_STORE_PATHS`) for existence/permission awareness only and are
  intentionally **not** part of this coverage comparison.
- `parse_frontmatter` fixed: YAML **block scalars** (`description: >` / `|`) and
  indented **list blocks** (`triggers:` / `allowed-tools:` with `  - item`) are
  now consumed as one value instead of being misparsed as separate frontmatter
  entries. The earlier `unsupported frontmatter line:` errors on
  `.opencode/skills/{audit,pdf,ponytail-audit,ponytail-debt,make-pdf}` were
  parser false-positives and are gone; the remaining `INVALID_SKILL_CONTRACT`
  entries are genuine and come from two distinct causes: (a) the `name:` field
  differs from the skill's directory name (e.g. `.opencode/skills/audit` → name
  `ponytail-audit`; `.opencode/skills/code-review-and-quality` → name
  `code-review`), and (b) a relative link in the skill body points at a resource
  that does not exist (e.g. `codebase-design/DEEPENING.md`, `make-pdf/arch.png`).
- `check.sh` secret scan now uses `grep -Eqi` (was `-Equ`, where `-u` is the
  obsolete `--unix-byte-offsets`): the pattern's key name is lowercase, so
  without `-i` the documented upper-/camel-case spellings (`API_KEY=`, `apiKey`)
  silently slipped through. Pinned by
  `test_hook_secret_regex_matches_case_variants`.

## Current findings (refreshed 2026-10-20; `--check --scope mcp` passes)

```
high:   1  INVALID_SKILL_CONTRACT  (genuine: name/folder mismatch in
           .opencode/skills/{audit -> ponytail-audit,
           code-review-and-quality -> code-review}; missing linked resources in
           codebase-design, domain-modeling, improve-codebase-architecture,
           make-pdf — all untracked third-party skills)
medium: 4  KILO_VERSION_SKEW (project 7.0.50 vs cli 7.7.9), PAID_MODEL_IN_PROJECT_CONFIG,
           SKILL_PORTABILITY_GAP, UNTRACKED_AGENT_ASSET
low:    1  GROUP_WRITABLE_AGENT_DIRS
info:   5  SENSITIVE_HISTORY_EXCLUDED, ABSENT_TOOL_DIRS, HARDCODED_GLOBAL_MODEL,
           2x MCP_CONFIG_PARSE_ERROR (missing .kilo/mcp.json, ~/.claude/settings.json)
```

No MCP drift remains. All CLI filesystem MCPs connect. The high finding is
informational under `--scope all` only; it does not block commits (skills are
untracked and outside the `--scope mcp` gate). Some codes above reflect the
2026-10-20 re-run and may differ from an earlier snapshot of this document if
the working tree changed in between.