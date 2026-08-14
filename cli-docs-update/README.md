# CLI verification artifacts

The dated investigation files in this directory are historical inputs. They
contain contradictory and outdated claims and must not be treated as current
verification.

The reproducible workflow is:

```bash
python3 scripts/verify_cli_claims.py
```

It reads `config/cli_verification_claims.json` and atomically generates:

- `cli-docs-update/current-verification.json`
- `cli-docs-update/current-verification.md`

The registry is validated against
`config/cli_verification_claims.schema.json`, including product/probe/claim
references. The verifier is deliberately read-only. It runs version/help commands and a
small allowlist of safe diagnostics. It does not run agent prompts, read auth
files, export sessions, call model APIs, update tools, or retain raw config
values. Subprocesses receive only an allowlist of basic execution variables;
provider and credential variables are not inherited. Native outputs that may
contain secrets or private content are listed in the report but skipped.

## Agents and models

The verification run does not invoke an agent or language model. Runtime
facts, JSON parsing, schema checks, and exact string matching are more reliable
and reproducible for this job.

`config/cli_verification_claims.json` contains an optional model-assistance
policy, disabled by default. If an operator explicitly enables a future
advisory adapter, it may only propose searches, classify already-sanitized
evidence, and identify contradictions for follow-up. It cannot assign
`VERIFIED_RUNTIME` or `CONTRADICTED`, execute tools, or inspect private data.

The advisory baseline is temperature `0.0` (or the provider's lowest supported
value), with `top_p` left unset. Reasoning models should use evaluated reasoning
effort instead: `low` for extraction and `medium` for conflict analysis. These
settings reduce avoidable variation but do not make model output deterministic.
See `MODEL_ASSISTANCE_RESEARCH.md` for the research basis and per-tool notes.

Use a narrower run while developing:

```bash
python3 scripts/verify_cli_claims.py --product codex --product opencode
```

Use check mode in CI or a pre-commit workflow. It writes nothing. Exit `0`
means all selected claims are proven, `1` means the registry/invocation is
invalid or a claim is contradicted, and `2` means a required result is
unproven (including missing binaries, timeouts, or policy-skipped probes):

```bash
python3 scripts/verify_cli_claims.py --check
```

Add `--require-complete` when the checkpoint also requires every selected
binary to provide successful version and help discovery:

```bash
python3 scripts/verify_cli_claims.py --check --require-complete
```

Audit the project's active agent/config directories separately:

```bash
python3 scripts/audit_agent_dirs.py
```

This generates `current-agent-dir-audit.json` and
`current-agent-dir-audit.md`. It excludes `.history-remediation` and all
operational A1/private-data directories. Check mode writes nothing and fails on
high-severity findings:

```bash
python3 scripts/audit_agent_dirs.py --check
```
