# Current agent-directory audit

Generated: `2026-08-14T04:46:40+02:00`

> Read-only audit of active project agent/config directories. Sensitive historical and operational-data directories were excluded.

## Findings

| Severity | Code | Finding | Evidence | Recommended action |
|---|---|---|---|---|
| high | KILO_GLOBAL_CONFIG_BLOCKS_PROJECT | Kilo cannot load the active configuration chain. | Error: Configuration is invalid at ~/.config/kilo/kilo.jsonc ↳ Unrecognized keys: "subagent_model", "sandbox" | Repair or migrate the user-level Kilo config first; retain the valid project .kilo/kilo.jsonc. |
| medium | KILO_VERSION_SKEW | Project Kilo plugin and installed Kilo CLI versions differ. | project=7.4.21, cli=7.0.50 | Decide whether the package tracks the extension or CLI; document both explicitly and avoid treating them as one version. |
| medium | SKILL_PORTABILITY_GAP | A reusable skill is stored only in the OpenCode-specific directory. | .opencode/skills/market-research-evidence/SKILL.md | If cross-tool use is intended, migrate it to .agents/skills after validating discovery in each target CLI; do not duplicate two writable copies. |
| medium | UNTRACKED_AGENT_ASSET | One or more active agent skills are untracked. | .opencode/skills/market-research-evidence/SKILL.md | Review for secrets and scope, then intentionally track or explicitly ignore each asset; never wildcard-stage. |
| low | GROUP_WRITABLE_AGENT_DIRS | Active agent/config directories are group-writable. | .agents, .opencode, .kilo | Confirm the repository group is an intentional trust boundary; agent instructions are executable policy and should not be writable by unintended accounts. |
| info | SENSITIVE_HISTORY_EXCLUDED | Sensitive historical agent-directory copies were excluded. | .history-remediation contains candidate/fresh-clone agent directories and is sensitive by repository policy. | Keep it ignored and out of generated reports; compare only through an explicitly authorized remediation workflow. |
| info | ABSENT_TOOL_DIRS | Some tool-specific project directories are absent. | .cline, .codex, .claude, .clinerules, .kilocode | Absence is not a defect unless a documented project-specific integration is required; prefer shared AGENTS.md and .agents/skills where supported. |

## Directory inventory

| Directory | Exists | Mode | Tracked entries |
|---|---:|---:|---:|
| `.agents` | yes | 0o2775 | 5 |
| `.opencode` | yes | 0o2775 | 0 |
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
| `.opencode/skills/market-research-evidence/SKILL.md` | market-research-evidence | yes | no |

## Runtime discovery

- OpenCode skill discovery: `succeeded`.
- Kilo active-config probe exit: `1`.

## Boundaries

- Missing tool-specific directories are not automatically gaps.
- `.history-remediation` was not inspected.
- No credential, session, raw config value, A1, scan, evidence, OCR, data, or output content was read.
- Findings do not authorize moving skills, repairing global user configuration, or staging files.
