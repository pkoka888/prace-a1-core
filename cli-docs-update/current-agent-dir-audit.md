# Current agent-directory audit

Generated: `2026-10-21T00:37:12+02:00`

> Read-only audit of active project agent/config directories. Sensitive historical and operational-data directories were excluded.

## Findings

| Severity | Code | Finding | Evidence | Recommended action |
|---|---|---|---|---|
| medium | KILO_VERSION_SKEW | Project Kilo plugin and installed Kilo CLI versions differ. | project=7.0.50, cli=7.7.9 | Decide whether the package tracks the extension or CLI; document both explicitly and avoid treating them as one version. |
| medium | SKILL_PORTABILITY_GAP | A reusable skill is stored only in the OpenCode-specific directory. | .opencode/skills/a1-pdf-production/SKILL.md, .opencode/skills/api-and-interface-design/SKILL.md, .opencode/skills/audit/SKILL.md, .opencode/skills/code-review/SKILL.md, .opencode/skills/code-review-and-quality/SKILL.md, .opencode/skills/code-simplification/SKILL.md, .opencode/skills/codebase-design/SKILL.md, .opencode/skills/deprecation-and-migration/SKILL.md, .opencode/skills/documentation-and-adrs/SKILL.md, .opencode/skills/domain-modeling/SKILL.md, .opencode/skills/improve-codebase-architecture/SKILL.md, .opencode/skills/incremental-implementation/SKILL.md, .opencode/skills/make-pdf/SKILL.md, .opencode/skills/market-research-evidence/SKILL.md, .opencode/skills/observability-and-instrumentation/SKILL.md, .opencode/skills/pdf/SKILL.md, .opencode/skills/planning-and-task-breakdown/SKILL.md, .opencode/skills/ponytail-audit/SKILL.md, .opencode/skills/ponytail-debt/SKILL.md, .opencode/skills/postgres-ops/SKILL.md, .opencode/skills/security-and-hardening/SKILL.md, .opencode/skills/source-driven-development/SKILL.md, .opencode/skills/synthetic-portal-delivery/SKILL.md, .opencode/skills/systematic-debugging/SKILL.md, .opencode/skills/verification-before-completion/SKILL.md, .opencode/skills/writing-plans/SKILL.md | If cross-tool use is intended, migrate it to .agents/skills after validating discovery in each target CLI; do not duplicate two writable copies. |
| medium | UNTRACKED_AGENT_ASSET | One or more active agent skills are untracked. | .opencode/skills/a1-pdf-production/SKILL.md, .opencode/skills/api-and-interface-design/SKILL.md, .opencode/skills/audit/SKILL.md, .opencode/skills/code-review/SKILL.md, .opencode/skills/code-review-and-quality/SKILL.md, .opencode/skills/code-simplification/SKILL.md, .opencode/skills/codebase-design/SKILL.md, .opencode/skills/deprecation-and-migration/SKILL.md, .opencode/skills/documentation-and-adrs/SKILL.md, .opencode/skills/domain-modeling/SKILL.md, .opencode/skills/improve-codebase-architecture/SKILL.md, .opencode/skills/incremental-implementation/SKILL.md, .opencode/skills/make-pdf/SKILL.md, .opencode/skills/observability-and-instrumentation/SKILL.md, .opencode/skills/pdf/SKILL.md, .opencode/skills/planning-and-task-breakdown/SKILL.md, .opencode/skills/ponytail-audit/SKILL.md, .opencode/skills/ponytail-debt/SKILL.md, .opencode/skills/postgres-ops/SKILL.md, .opencode/skills/security-and-hardening/SKILL.md, .opencode/skills/source-driven-development/SKILL.md, .opencode/skills/synthetic-portal-delivery/SKILL.md, .opencode/skills/systematic-debugging/SKILL.md, .opencode/skills/verification-before-completion/SKILL.md, .opencode/skills/writing-plans/SKILL.md | Review for secrets and scope, then intentionally track or explicitly ignore each asset; never wildcard-stage. |
| high | INVALID_SKILL_CONTRACT | A skill has invalid metadata or broken local references. | .opencode/skills/audit/SKILL.md: name 'ponytail-audit' does not match folder 'audit'; .opencode/skills/code-review-and-quality/SKILL.md: name 'code-review' does not match folder 'code-review-and-quality'; .opencode/skills/codebase-design/SKILL.md: broken relative link: DEEPENING.md, broken relative link: DESIGN-IT-TWICE.md; .opencode/skills/domain-modeling/SKILL.md: broken relative link: ./CONTEXT-FORMAT.md, broken relative link: ./ADR-FORMAT.md; .opencode/skills/improve-codebase-architecture/SKILL.md: broken relative link: HTML-REPORT.md; .opencode/skills/make-pdf/SKILL.md: broken relative link: data.png, broken relative link: data.png, broken relative link: arch.png, broken relative link: shot.png | Fix the smallest metadata or link issue and rerun this audit. |
| low | GROUP_WRITABLE_AGENT_DIRS | Active agent/config directories are group-writable. | .agents, .opencode, .kilo | Confirm the repository group is an intentional trust boundary; agent instructions are executable policy and should not be writable by unintended accounts. |
| info | SENSITIVE_HISTORY_EXCLUDED | Sensitive historical agent-directory copies were excluded. | .history-remediation contains candidate/fresh-clone agent directories and is sensitive by repository policy. | Keep it ignored and out of generated reports; compare only through an explicitly authorized remediation workflow. |
| info | ABSENT_TOOL_DIRS | Some tool-specific project directories are absent. | .cline, .codex, .claude, .clinerules, .kilocode | Absence is not a defect unless a documented project-specific integration is required; prefer shared AGENTS.md and .agents/skills where supported. |
| info | MCP_CONFIG_PARSE_ERROR | kilo_code_extension MCP config could not be parsed. | <repo>/.kilo/mcp.json: missing | Repair the config so the CLI can load its MCP servers; a parse error silently disables every server. |
| info | MCP_CONFIG_PARSE_ERROR | claude MCP config could not be parsed. | ~/.claude/settings.json: missing | Repair the config so the CLI can load its MCP servers; a parse error silently disables every server. |
| info | HARDCODED_GLOBAL_MODEL | kilo_cli user-level config pins a model not in the sanctioned list. | ~/.config/kilo/kilo.jsonc: kilo/kilo-auto/free, openrouter/openrouter/free, minimax/MiniMax-M3, minimax/MiniMax-M2.7 | Global model choice is a user preference, not repository drift. Confirm the id is intended and, if the project should share a model policy, document it in the CLI docs rather than editing user config. |
| medium | PAID_MODEL_IN_PROJECT_CONFIG | A tracked project config references a paid model endpoint. | <repo>/config/vision_models.json: minimax/minimax-01, minimax/minimax-m3 | AGENTS.md forbids paid model use including fallback. Replace the paid id with a verified-free one or remove it, and confirm with the owner before any use. |

## Directory inventory

| Directory | Exists | Mode | Tracked entries |
|---|---:|---:|---:|
| `.agents` | yes | 0o2775 | 7 |
| `.opencode` | yes | 0o2775 | 4 |
| `.kilo` | yes | 0o2775 | 1 |
| `.cline` | no | — | 0 |
| `.codex` | no | — | 0 |
| `.claude` | no | — | 0 |
| `.clinerules` | no | — | 0 |
| `.kilocode` | no | — | 0 |

## Skill contracts

| Skill | Name | Valid | Tracked |
|---|---|---:|---:|
| `.agents/skills/a1-pdf-production/SKILL.md` | a1-pdf-production | yes | yes |
| `.agents/skills/postgres-ops/SKILL.md` | postgres-ops | yes | yes |
| `.agents/skills/synthetic-portal-delivery/SKILL.md` | synthetic-portal-delivery | yes | yes |
| `.opencode/skills/a1-pdf-production/SKILL.md` | a1-pdf-production | yes | no |
| `.opencode/skills/api-and-interface-design/SKILL.md` | api-and-interface-design | yes | no |
| `.opencode/skills/audit/SKILL.md` | ponytail-audit | no | no |
| `.opencode/skills/code-review/SKILL.md` | code-review | yes | no |
| `.opencode/skills/code-review-and-quality/SKILL.md` | code-review | no | no |
| `.opencode/skills/code-simplification/SKILL.md` | code-simplification | yes | no |
| `.opencode/skills/codebase-design/SKILL.md` | codebase-design | no | no |
| `.opencode/skills/deprecation-and-migration/SKILL.md` | deprecation-and-migration | yes | no |
| `.opencode/skills/documentation-and-adrs/SKILL.md` | documentation-and-adrs | yes | no |
| `.opencode/skills/domain-modeling/SKILL.md` | domain-modeling | no | no |
| `.opencode/skills/improve-codebase-architecture/SKILL.md` | improve-codebase-architecture | no | no |
| `.opencode/skills/incremental-implementation/SKILL.md` | incremental-implementation | yes | no |
| `.opencode/skills/make-pdf/SKILL.md` | make-pdf | no | no |
| `.opencode/skills/market-research-evidence/SKILL.md` | market-research-evidence | yes | yes |
| `.opencode/skills/observability-and-instrumentation/SKILL.md` | observability-and-instrumentation | yes | no |
| `.opencode/skills/pdf/SKILL.md` | pdf | yes | no |
| `.opencode/skills/planning-and-task-breakdown/SKILL.md` | planning-and-task-breakdown | yes | no |
| `.opencode/skills/ponytail-audit/SKILL.md` | ponytail-audit | yes | no |
| `.opencode/skills/ponytail-debt/SKILL.md` | ponytail-debt | yes | no |
| `.opencode/skills/postgres-ops/SKILL.md` | postgres-ops | yes | no |
| `.opencode/skills/security-and-hardening/SKILL.md` | security-and-hardening | yes | no |
| `.opencode/skills/source-driven-development/SKILL.md` | source-driven-development | yes | no |
| `.opencode/skills/synthetic-portal-delivery/SKILL.md` | synthetic-portal-delivery | yes | no |
| `.opencode/skills/systematic-debugging/SKILL.md` | systematic-debugging | yes | no |
| `.opencode/skills/verification-before-completion/SKILL.md` | verification-before-completion | yes | no |
| `.opencode/skills/writing-plans/SKILL.md` | writing-plans | yes | no |

## Runtime discovery

- OpenCode skill discovery: `invalid_json`.
- Kilo active-config probe exit: `0`.

## CLI MCP configurations

| CLI | Config | Servers | Stale paths | Disabled | Uninterpolated env | Parse error |
|---|---|---:|---|---|---|---|
| `opencode` | `~/.config/opencode/opencode.jsonc` | 5 | — | — | — | — |
| `opencode` | `~/.opencode/mcp.json` | 2 | — | — | — | — |
| `kilo_cli` | `~/.config/kilo/kilo.json` | 6 | — | — | — | — |
| `kilo_cli` | `~/.config/kilo/kilo.jsonc` | 0 | — | — | — | — |
| `kilo_code_extension` | `<repo>/.kilo/mcp.json` | 0 | — | — | — | missing |
| `cline` | `~/.cline/data/settings/cline_mcp_settings.json` | 1 | — | — | — | — |
| `pi` | `~/.pi/agent/models-store.json` | 0 | — | — | — | — |
| `pi` | `~/.pi/agent/settings.json` | 0 | — | — | — | — |
| `codex` | `~/.codex/config.toml` | 0 | — | — | — | — |
| `claude` | `~/.claude/settings.json` | 0 | — | — | — | missing |

## Model configuration

| CLI | Config | Model ids | Unexpected |
|---|---|---|---|
| `opencode` | `~/.config/opencode/opencode.jsonc` | — | — |
| `opencode` | `~/.opencode/mcp.json` | — | — |
| `kilo_cli` | `~/.config/kilo/kilo.json` | kilo/auto, kilo/Auto Free | — |
| `kilo_cli` | `~/.config/kilo/kilo.jsonc` | kilo/poolside/laguna-xs-2.1:free, kilo/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free, kilo/nvidia/nemotron-3-ultra-550b-a55b:free, kilo/nvidia/nemotron-3-super-120b-a12b:free, kilo/stepfun/step-3.7-flash:free, kilo/kilo-auto/free, kilo/poolside/laguna-xs-2.1:free, kilo/nvidia/nemotron-3-super-120b-a12b:free, openrouter/openrouter/free, minimax/MiniMax-M3, minimax/MiniMax-M2.7 | kilo/nvidia/nemotron-3-ultra-550b-a55b:free, kilo/nvidia/nemotron-3-super-120b-a12b:free, kilo/stepfun/step-3.7-flash:free, kilo/kilo-auto/free, kilo/nvidia/nemotron-3-super-120b-a12b:free, openrouter/openrouter/free, minimax/MiniMax-M3, minimax/MiniMax-M2.7 |
| `kilo_code_extension` | `<repo>/.kilo/mcp.json` | — | — |
| `cline` | `~/.cline/data/settings/cline_mcp_settings.json` | — | — |
| `pi` | `~/.pi/agent/models-store.json` | — | — |
| `pi` | `~/.pi/agent/settings.json` | MiniMax-M2.7 | — |
| `codex` | `~/.codex/config.toml` | gpt-6-astra | — |
| `claude` | `~/.claude/settings.json` | — | — |

## Credential stores (existence only)

| CLI | Path | Exists |
|---|---|---|
| `opencode` | `~/.config/opencode/env` | yes |
| `opencode` | `~/.local/share/opencode/auth.json` | yes |
| `cline` | `~/.cline/data/secrets.json` | yes |
| `cline` | `~/.cline/data/settings/providers.json` | yes |
| `pi` | `~/.pi/agent/auth.json` | yes |

Credential stores are listed for existence/permission awareness only; their contents are never read and they are intentionally excluded from the inline-secret grep (they hold real keys by design).

## Boundaries

- Kilo has two products: the `kilo` CLI reads `~/.config/kilo/kilo.json`; the `kilo-code` VS Code extension reads `<workspace>/.kilo/mcp.json`. They are independent and fixing one does not affect the other.
- `{env:VAR}` in `command`/`args` arrays is substituted by opencode 1.18.32 and kilo 7.7.9 (verified 2026-10-20); `${env:VAR}` is invalid there — the `{env:VAR}` part resolves and a stray `$` remains. Interpolation inside `environment` values was not re-verified in this pass.
- Missing tool-specific directories are not automatically gaps.
- `.history-remediation` was not inspected.
- No credential, session, raw config value, A1, scan, evidence, OCR, data, or output content was read.
- Findings do not authorize moving skills, repairing global user configuration, or staging files.
