# Agent-directory research gaps

This backlog turns the current local audit into bounded documentation research.
It does not authorize configuration changes, skill moves, installs, model calls,
or inspection of `.history-remediation`.

## Priority 1 — blockers and active contradictions

### Kilo global configuration migration

Current runtime evidence rejects `~/.config/kilo/kilo.jsonc` because
`subagent_model` and `sandbox` are unrecognized. The project
`.kilo/kilo.jsonc` is small and structurally valid, so research should identify:

1. Which installed Kilo surface owns those keys: CLI 7.0.50, extension 7.4.21,
   a prior OpenCode-compatible schema, or a newer Kilo schema.
2. The supported replacements or whether the keys must be removed.
3. A native validation/migration command that does not alter the repository.
4. A rollback method before any user-level edit.

Primary starting points:

- [Kilo settings and config locations](https://kilo.ai/docs/getting-started/settings)
- [Kilo custom subagents](https://kilo.ai/docs/customize/custom-subagents)
- [Kilo custom models](https://kilo.ai/docs/code-with-ai/agents/custom-models)

### Kilo version ownership

The project package pins `@kilocode/plugin` 7.4.21 while the installed CLI is
7.0.50. Determine whether the package intentionally follows the VS Code
extension, must follow the CLI, or is only editor tooling. Do not “fix” the
version until its consumer and compatibility contract are documented.

## Priority 2 — portability and discovery

### Shared versus tool-specific skills

The tracked A1 skill lives at `.agents/skills/a1-pdf-production`; the untracked
research skill lives only at `.opencode/skills/market-research-evidence`.
OpenCode currently discovers both. Research should build a compatibility table
for the installed versions of OpenCode, Kilo, Cline, Codex, and Hermes:

| Question | Required evidence |
|---|---|
| Does the tool discover `.agents/skills`? | Native inventory command plus official docs |
| Does it discover its own project skill directory? | Native inventory command |
| What wins on duplicate skill names? | Official precedence rule and synthetic fixture |
| Is metadata-only discovery used? | Official lifecycle documentation |
| Are provider metadata files such as `agents/openai.yaml` understood? | Provider-specific official documentation |

Primary starting points:

- [OpenCode agents](https://dev.opencode.ai/docs/agents/)
- [OpenCode rules and precedence](https://opencode.ai/docs/rules/)
- [Kilo skills](https://kilo.ai/docs/customize/skills)
- [Cline skills](https://docs.cline.bot/customization/skills)

Do not maintain duplicate writable copies of one skill. If portability is
confirmed, migrate once to a shared canonical location and regression-test each
target tool.

## Priority 3 — governance and supply chain

### Tracking decision for `.opencode`

The active research skill and its package scaffolding are untracked. Decide
explicitly which files are project source and which are generated local state.
Before tracking anything:

1. Review exact paths for credentials, private URLs, PII, and generated content.
2. Confirm lockfile/package purpose and version ownership.
3. Stage only an explicit reviewed path list; never wildcard-stage.

### Permission boundary

The active dot-directories are group-writable (`2775`). Confirm that every
member of the repository group is trusted to alter agent instructions and
tooling configuration. This is an operational question, not an automatic chmod
recommendation.

### Historical copies

`.history-remediation` contains candidate/fresh-clone copies of agent/config
directories. It is sensitive by policy and excluded from this audit. Any future
comparison needs a separately authorized history-remediation procedure that
reports hashes and paths without copying content into ordinary reports.

## Acceptance criteria for closing a research gap

- One exact claim per evidence record.
- Installed product and version recorded separately from editor-extension and
  package versions.
- Native runtime evidence plus an official primary source where available.
- Sanitized JSON output; no full configs, tokens, session text, or skill bodies.
- `unknown`/`NOT_TESTED` retained when evidence is insufficient.
- A synthetic regression fixture for precedence, discovery, or migration claims.
