# CLI Documentation Investigation Workflow Update

## Process Used (2026-08-14)

### 1. Installation Verification
```bash
which opencode cline codex hermes kilo
binary_path --version
# Verified all installations were functional
```

### 2. Documentation Source Discovery
For each CLI, checked:
- **Official websites/documentation** (external)
- **Installed local files** (source code, configs)
- **Built-in help commands** (--help, doctor, etc.)
- **VS Code extensions** (if applicable)

### 3. JSON/YAML Configuration Analysis
- Read actual config files from installations
- Analyzed source code for structure definitions
- Identified format differences (JSON vs TOML vs YAML vs JSONC)

### 4. Yolo Mode Investigation
- Searched CLI source code for `--yolo` or equivalent flags
- Checked configuration files for auto-mode settings
- Used `grep` on compiled JS/Rust code

### 5. Documentation Quality Assessment
Scoring criteria:
- Completeness (0-10)
- Local accessibility (YES/NO)
- JSON/YAML structure coverage
- Yolo mode documentation clarity

---

## Best Documentation Sources by CLI

### cline (Score: 9.5/10)
**Primary: Installed source code**
- `~/.npm-global/lib/node_modules/cline/dist/cli.mjs`
- Contains actual `--yolo` flag definition at line ~2000+
- Settings.json structure visible in type definitions

**Secondary: Official docs**
- https://docs.cline.bot/getting-started/for-new-coders

### hermes (Score: 9.8/10)
**Primary: Local documentation**
- `~/.hermes/hermes-agent/website/docs/`
- Complete documentation for all features
- Skills.md specifically covers SKILL.md format

### kilo-code (Score: 9.0/10)
**Primary: Extension docs**
- `~/.vscode-server/extensions/kilocode.kilo-code-7.4.21-linux-x64/docs/`
- opencode-migration-plan.md has JSON structure examples

**Secondary: Actual config**
- `~/.config/kilo/kilo.jsonc`

### codex (Score: 8.0/10)
**Primary: Local config**
- `~/.codex/config.toml` and `auth.json`

**Secondary: GitHub source**
- https://github.com/openai/codex

### opencode (Score: 8.5/10)
**Primary: Local mcp.json**
- `~/.opencode/mcp.json` (actual working file)

**Secondary: Website**
- https://opencode.ai/docs (remote access limited)

---

## Key Findings

### JSON Configuration Formats
| CLI | Format | Note |
|-----|--------|------|
| opencode | JSON | Standard JSON |
| cline | JSON | Standard JSON |
| codex | TOML | NOT JSON but equivalent |
| hermes | YAML | NOT JSON but equivalent |
| kilo | JSONC | JSON with comments |

### Yolo Mode Support
| CLI | Flag/Setting | Documentation |
|-----|--------------|---------------|
| cline | `--yolo` | ✅ CLEAR in source code |
| codex | `--dangerously-bypass-approvals-and-sandbox` | ✅ Documented |
| hermes | `terminal.auto_mode` | ✅ In YAML config docs |
| kilo | Via Hermes | ✅ Inherits from backend |
| opencode | N/A (uses `run`) | Not applicable |

### Authority Chain (Best to Worst)
1. **Installed local files** - Actual working configs and source
2. **Local documentation** - Website docs bundled with installation
3. **Runtime verification** - `command --version`, `command doctor`
4. **External documentation** - Websites (when network available)

---

## Workflow for Future Updates

1. Check installation status with `which <cli>` and `--version`
2. Locate config files in standard paths
3. Read source code for flag/option discovery
4. Check local documentation bundles
5. Verify with built-in commands (`doctor`, `--help`)
6. Cross-reference with external docs when network available
7. Document actual working paths and their last verification date

---

## Files Generated

- `2026-08-14-comprehensive-cli-investigation.json` - Machine-readable results
- `2026-08-14-summary.md` - Human-readable summary
- `2026-08-14-documentation-comparison.json` - Source comparison matrix
- `2026-08-14-workflow-update.md` - This workflow documentation
