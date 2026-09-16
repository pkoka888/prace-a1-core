# Agent Workflow, Framework, and Skill Design Research Report

## Project context
- Django 3.2 + PostgreSQL + nginx application with synthetic rehearsal lifecycle
- Existing opencode skills: `a1-pdf-production`, `postgres-ops`, `synthetic-portal-delivery`, `market-research-evidence`
- Change-package validation (`change-packages.yml`) drives scoped CI gates
- Pre-commit hook runs `validate_change_packages.py --staged --run-checks`
- GitLab CI proposed but inactive (DEC-016 pending)

---

## 1. OpenCode/Agent Skills

### Current state in this repo

**Skill storage layout:**
- `.agents/skills/` — Domain-specific operational skills (a1-pdf-production, postgres-ops, synthetic-portal-delivery)
- `.opencode/skills/` — Experimental/research skills (market-research-evidence)

**Skill structure pattern** (all four skills follow the same shape):
```
<skill-name>/
  SKILL.md                    # YAML frontmatter + prose instructions
  references/                 # Optional: schemas, contracts, policy files
  agents/                     # Optional: adapter configs (openai.yaml)
```

**Skill invocation:** Skills are loaded via `skill(name="...")` tool call. The skill injects its full instruction text into the active conversation context. The agent then follows the skill's authority chain (AGENTS.md → skill → plan → scripts).

**What skills provide:**
- Authoritative instruction set that supersedes general knowledge
- Grounding steps (read AGENTS.md, inspect git status, set required env vars)
- Canonical script references (e.g., "use `scripts/generate_provisional_a1.py`")
- Validation contracts and acceptance criteria
- Explicit "avoid" lists that prevent common foot-guns
- Base directory and relative path semantics

**Existing skill inventory:**

| Skill | Location | Status | Purpose |
|---|---|---|---|
| `a1-pdf-production` | `.agents/skills/` | Active production | A1 PDF generation, validation, recovery |
| `postgres-ops` | `.agents/skills/` | Active production | PostgreSQL lifecycle, disposable targets, migrations |
| `synthetic-portal-delivery` | `.agents/skills/` | Active production | Delivery-1 rehearsal lifecycle, browser journey, persistence |
| `market-research-evidence` | `.opencode/skills/` | Experimental (Plan AC) | Research evidence collection, schema validation |

### Best practice from authoritative sources

- Skills are **operational authority documents**, not documentation. They should encode what to do, not explain why (the why lives in ADRs and plans).
- Skills must fail closed on missing prerequisites (e.g., unset `A1_PRIVATE_DIR`).
- Skills reference canonical scripts, never duplicate their logic.
- Skills contain explicit "avoid" lists to prevent the agent from inventing parallel implementations.
- Skills are subordinate to `AGENTS.md`; they cannot override its PII, secrets, or authorization rules.

### Gap analysis

| Gap | Evidence |
|---|---|
| No skill covers the release reproducer workflow end-to-end | `run_release_reproducer.py` is referenced from `change-packages.yml` but has no skill |
| No skill for delivery-readiness diagnostics | `validate_delivery_readiness.py` is a standalone script |
| No skill for change-package authoring/maintenance | `change-packages.yml` is maintained manually |
| Skills don't encode their own test contracts | Each skill mentions "run tests" but doesn't declare which |
| `market-research-evidence` is in `.opencode/skills/` while production skills are in `.agents/skills/` | Inconsistent location suggests unclear ownership boundary |

### Recommended approach

1. **When to create a skill vs a script:**
   - **Skill:** When the workflow requires non-trivial decision-making, has dangerous foot-guns, or encodes operational policy that must not be overridden by general knowledge. Examples: A1 PDF generation, PostgreSQL disposable-target lifecycle, delivery rehearsal.
   - **Script:** When the operation is deterministic, has a narrow input/output contract, and can be unit-tested in isolation. Examples: `smoke_probe.py`, `validate_planning.py`, `disposable_pg_guard.py`.
   - **Neither (just a function):** When the logic is a pure helper called by a script.

2. **Skill design conventions to adopt:**
   - Every skill must declare its own `base directory` and relative path semantics (already done by three of four skills).
   - Every skill must have a "Hand off" section stating what was done and what remains.
   - Every skill must list its governing plan and ADR at the top.
   - Skills that wrap scripts should declare the script's exit codes in the skill body.
   - Skills must not contain executable code; they are instruction-only documents.

3. **Consolidation opportunity:** Move `market-research-evidence` to `.agents/skills/` when Plan AC exits experimental status, or explicitly mark `.opencode/skills/` as the experimental tier in `AGENTS.md`.

---

## 2. Agent Workflow Patterns

### Current state in this repo

**Multi-step automation:** `rehearse_synthetic_site.sh` is the canonical example — a shell script with 7 subcommands (`prepare → provision → start → smoke → workflow → stop → start`), each with documented exit codes.

**Human-in-the-loop patterns:**
- `operator.json` (mode 0600) stores credentials inside the runtime root; the script never prints passwords outside deliberate reads
- Journey stages that require operator approval are explicitly documented in the skill, not encoded in code
- Evidence receipts (`receipt.json`) record what was done; a separate human reads and decides

**Error handling and recovery:**
- `rehearse_synthetic_site.sh` uses `set -euo pipefail` with explicit error messages per step
- `validate_change_packages.py` uses `KeyboardInterrupt` → signal restoration → partial report write
- `run_release_reproducer.py` wraps each command in try/except with timeout (600s) and captures stdout/stderr to files
- ATOMIC writes: `_write_report()` writes to `.pending` then `replace()`

**Logging and audit trails:**
- Receipts are JSON files in `runtime/portal/temporary/<uuid>/`
- `a1_audit.py` uses Django model `AuditEvent` for PII-sensitive actions
- Script logs go to `<package>-stdout.log` and `<package>-stderr.log` with SHA-256 digests in the receipt
- OCR worker logs use sanitized tags and opaque run IDs

### Best practice from authoritative sources

**Multi-step automation:**
- Use a state machine with explicit states (`queued → running → waiting_operator → succeeded/failed/timed_out/cancelled/unknown`)
- Each step should be independently retryable
- Record the terminal reason separately from the exit code

**Human-in-the-loop:**
- Separate "autonomous scope" from "operator wait conditions" in a table
- Use single-use decision tokens with expiry; reject stale decisions
- The waiting state must be observable without re-executing the workflow

**Error handling:**
- Distinguish `OSError` (environment), `subprocess.CalledProcessError` (command failure), `subprocess.TimeoutExpired` (budget exceeded), and `ValueError` (input contract violation)
- Preserve original failure alongside any successful retry
- Use bounded timeouts per check, not global timeouts

**Audit trails:**
- Every automated action needs an `actor_ref`, `target_ref`, `start/end time`, `terminal reason`, and `validator outcome`
- Logs must be append-only and tamper-evident
- Correlation IDs (`run_id`, `message_id`) link related events across scripts

### Gap analysis

| Gap | Evidence |
|---|---|
| No unified receipt schema across scripts | `run_release_reproducer.py` has its own receipt format; `validate_change_packages.py` has a different one; `rehearse_verify_persistence.py` has no machine-readable receipt |
| No correlation ID propagated between lifecycle stages | Each script generates its own identifiers independently |
| No timeout budget propagated between parent/child | `rehearse_synthetic_site.sh` uses env vars, but they aren't passed to subprocess calls |
| Partial success can be advertised | If `run_release_reproducer.py` crashes after some checks pass, the receipt writes `source_integrity_after_checks` but doesn't distinguish "completed N of M" |
| Operator approval state is not tracked | There is no record of whether an operator has approved a specific execution |

### Recommended approach

1. **Adopt a minimal receipt envelope** shared across all scripts:
   ```json
   {
     "schema_version": 1,
     "run_id": "uuid",
     "task_id": "optional-parent",
     "actor_ref": "human-or-agent-id",
     "started_at": "UTC ISO-8601",
     "finished_at": "UTC ISO-8601",
     "terminal_state": "succeeded|failed|timed_out|blocked|waiting_operator|unknown",
     "exit_code": null,
     "terminal_reason": "string",
     "checks": [{"name": "...", "status": "...", "duration_s": ...}],
     "artifacts": [{"ref": "path", "sha256": "..."}],
     "target_ref": "postgres://... or sqlite://...",
     "source_identity": {"commit_sha": "...", "tree_sha": "..."},
     "authorization_ref": "plan-id or explicit-approval-ref"
   }
   ```

2. **Propagate timeout budgets as env vars:** `PRACE_RUN_DEADLINE_MS` — parent sets it, children inherit it, any subprocess that can't complete within budget exits with a specific code.

3. **Add a receipt merge helper:** If a parent process crashes, a child can write its own partial receipt file. The parent's recovery reads all `receipt-*.json` files in the run directory.

4. **Define explicit operator-wait conditions table** in `AGENTS.md` (already partially exists) and encode waiting states as observable files, not just prose.

---

## 3. Existing Frameworks in the Repo

### `rehearse_synthetic_site.sh`

**Pattern: Documented exit-code lifecycle orchestrator**

A single bash script with subcommands forming a pipeline. Each subcommand:
1. Validates preconditions (env vars, directory structure, permissions)
2. Performs the action (provision, start, stop, etc.)
3. Writes a pidfile with ownership metadata (`.gunicorn.pid`, `.gunicorn.started_at`, `.gunicorn.cmdline`)
4. Returns a documented exit code

**Key patterns:**
- **Ownership verification:** `stop` refuses to signal a pidfile whose PID doesn't match the launch record (bind, runtime, start time, cmdline)
- **Process group control:** `start_new_session=True` in Python; `os.killpg()` in cleanup
- **Fail-closed on partial config:** PostgreSQL requires all 4 `PRACE_DB_*` vars or none
- **Atomic key creation:** `mktemp` + `mv -f` + `chmod 0600`

### `run_release_reproducer.py`

**Pattern: Committed-source acceptance runner with source integrity verification**

1. Resolves a commit SHA to a tree
2. Exports the tree to `runtime/portal/temporary/s-<sha>/` with exact permissions (0400/0500)
3. Copies to a working directory with relaxed test permissions (0600/0700)
4. Runs acceptance commands in sequence, each with a 600s timeout
5. Writes a receipt with command results, stdout/stderr digests, and source-integrity-after-checks flag
6. Verifies export integrity after all commands complete

**Key patterns:**
- **Exact-tree integrity:** Export directories are mode 0500 (read-only); test copies are 0600/0700
- **Secret sanitization:** Environment variables with `PASSWORD`/`SECRET`/`TOKEN`/`APIKEY`/`PRIVATE_KEY` markers are recorded as `"set"`/`"unset"` only
- **Dependency recording:** `importlib.metadata.distributions()` captures the full dependency snapshot
- **Subprocess isolation:** Each command runs in a clean env with only forwarded `PRACE_DB_*` vars

### `validate_delivery_readiness.py`

**Pattern: Bounded diagnostic aggregator with explicit not-proven list**

Runs a set of checks (source scan, systemctl query, HTTP probes) and aggregates results into a JSON report with `passed/failed/blocked` counts. Never claims deployment acceptance — explicitly lists `not_proven` items.

**Key patterns:**
- **Bounded subprocess calls:** 8s timeout, `stdin=DEVNULL`, minimal env
- **Source-only mode:** Can run without host access
- **Explicit unproven list:** `not_proven` field enumerates what the check does NOT establish
- **No credential access:** Never reads `gunicorn.env`; only checks `EnvironmentFiles` metadata via `systemctl show`

### `check_m2_scaffold_gate.py`

**Pattern: Machine-readable gate with chained command execution**

Evaluates preconditions (ADR-001 checks pass, catalog frozen, ADR-002/REV-001 approved) then runs a sequence of validation commands. Returns `{"gate": "open"|"blocked", "reasons": [...], "checks": [...]}`.

**Key patterns:**
- **Chained validation:** Each command must pass before the gate opens
- **Reasons accumulate:** Multiple blocking conditions are reported together
- **JSON output:** `--json` flag for machine consumption

### Cross-cutting patterns summary

| Pattern | Scripts using it |
|---|---|
| Exit code contract | `rehearse_synthetic_site.sh`, `rehearse_verify_persistence.py`, `smoke_probe.py` |
| Receipt JSON | `run_release_reproducer.py`, `validate_change_packages.py` (check_run) |
| SHA-256 digest of artifacts | `run_release_reproducer.py`, `rehearse_verify_persistence.py` |
| Atomic file writes (pending → final) | `validate_change_packages.py`, `rehearse_synthetic_site.sh` |
| Process group ownership | `rehearse_synthetic_site.sh`, `validate_change_packages.py` |
| Bounded subprocess with timeout | All scripts |
| Secret name pattern filtering | `run_release_reproducer.py` |
| Staged-path-aware selection | `select_infrastructure_git_workflow_checks.py`, `select_shared_document_portal_checks.py` |
| JSON machine-readable output | Most scripts |

### Recommended approach

1. **Extract common receipt logic** into `scripts/_receipt.py` — a shared helper for creating, merging, and verifying receipts. All scripts should use it rather than ad-hoc dicts.

2. **Standardize exit code semantics:**
   - `0`: success
   - `1`: observed failure
   - `2`: incomplete evidence / usage error / blocked
   - Scripts that don't fit this model should document their own codes clearly

3. **Create a `scripts/_bounded_subprocess.py`** helper that encapsulates the timeout, env sanitization, process-group cleanup, and log-tailing pattern that's duplicated in `validate_change_packages.py` and `run_release_reproducer.py`.

4. **Add `--receipt-path` to all scripts** that don't have it, so the hook can collect all receipts from a run.

---

## 4. CI/CD Integration Patterns

### Current state in this repo

**Pre-commit hook** (`scripts/pre-commit`):
```bash
"$PYTHON_BIN" scripts/validate_change_packages.py --staged --run-checks
git diff --cached --check
```
- Runs on every commit
- Validates that staged paths belong to exactly one change package
- Runs the selected checks for those packages
- Checks for whitespace errors

**Change-package validation** (`validate_change_packages.py`):
- Reads `change-packages.yml` to determine which checks apply to staged paths
- Selector scripts (`select_*.py`) dynamically expand checks based on staged paths
- Deduplicates commands across packages
- Runs each check in a bounded subprocess with timeout
- Writes `VALIDATION_REPORT` to `runtime/portal/temporary/change-checks-<uuid>/report.json`

**GitLab CI** (`.gitlab-ci.yml`): Proposed but inactive (DEC-016 pending). Defines stages: validate → test → gate. Jobs include planning validation, change-package validation, test suites, M2 scaffold gate, and A1 quality gate.

### Best practice from authoritative sources

**CI as a gate, not a replacement for local validation:**
- Local hooks catch issues before they reach CI (faster feedback, lower cost)
- CI validates the committed source, not the working tree
- CI should never have secrets; use environment variables injected by the runner

**Change-package-driven CI:**
- Each change package declares its own checks and dependencies
- CI runs only the checks for packages that have staged path changes
- This scales: a docs-only commit doesn't run the full test suite

**Pre-commit hooks:**
- Must be fast (< 30s for the common case)
- Must not modify files unless `--fix` is explicitly requested
- Must handle `Ctrl-C` gracefully (write partial report before exit)
- Should run in the project's venv, not the system Python

### Gap analysis

| Gap | Evidence |
|---|---|
| No GitHub Actions workflow | `.github/workflows/` directory does not exist; `change-packages.yml` references `.github/workflows/ci.yml` as a path but it doesn't exist |
| GitLab CI is inactive | `.gitlab-ci.yml` header says "Proposed (Inactive until DEC-016 approval)" |
| No CI artifact retention policy | GitLab CI uses `expire_in: 7d` but no policy for `runtime/portal/temporary/` artifacts |
| No scheduled pipeline for rehearsal suite | `rehearse_synthetic_site.sh` is only invoked manually or by tests |
| No automated dependency update checks | `requirements.txt` changes trigger the rehearsal suite but there's no Dependabot or Renovate config |
| No branch protection rules | Not configurable in-file, but the absence of GitHub Actions means no CODEOWNERS or required checks |

### Recommended approach

1. **Create `.github/workflows/ci.yml`** (doesn't exist yet):
   ```yaml
   on: [push, pull_request]
   jobs:
     validate:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: {python-version: "3.13"}
         - run: python -m venv venv && venv/bin/pip install -r requirements.txt
         - run: venv/bin/python scripts/validate_change_packages.py --staged --json
         - run: venv/bin/python scripts/check_m2_scaffold_gate.py --json
         - run: venv/bin/python -m pytest tests/test_validate_change_packages.py -q
   ```

2. **Activate the GitLab CI mirror validation** only after DEC-016 approval; until then, use the GitHub Actions workflow as the authoritative CI.

3. **Add a scheduled nightly pipeline** that runs the `delivery_lifecycle_rehearsal` package checks (not the full rehearsal — just the unit tests that validate the lifecycle logic).

4. **Store CI artifacts in `runtime/portal/temporary/ci-<run-id>/`** with mode 0700, never in the repository.

5. **Add `CODEOWNERS`** to enforce review requirements for sensitive paths:
   ```
   # PII and secrets — never auto-merge
   a1/ scans/ evidence/ ocr/ data/ employees/scans/ output/ runtime/portal/ secrets/ .env .runtime-config/ @jan/operators
   # Infrastructure — operator review
   .gitlab-ci.yml scripts/rehearse_synthetic_site.sh scripts/run_release_reproducer.py @jan/operators
   # Skills — domain expert review
   .agents/skills/ @jan/domain-experts
   ```

---

## 5. File/Functionality Mapping Strategies

### Current state in this repo

**`change-packages.yml`** is the primary mapping mechanism. Each package declares:
- `paths` / `prefixes` — which files it owns
- `checks` — commands to run when those files change
- `dependencies` — other packages that must also pass
- `rollback` — how to undo the change
- `intended_commit` — the conventional commit message

**`scripts/inventory_repository.py`** provides a PII-safe inventory that classifies paths into categories: `production-runtime`, `production-config`, `production-test`, `documentation`, `supporting-or-legacy-config`.

**`scripts/audit_agent_dirs.py`** audits agent directories (`.agents/`, `.opencode/`, `.kilo/`, `.cline/`, `.codex/`) without reading private data.

**`scripts/validate_planning.py`** cross-references plan IDs, roadmap entries, and catalog items.

### Best practice from authoritative sources

**Mapping files to functionality:**
- Single source of truth: one file should declare the mapping; never derive it from directory structure
- Avoid implicit conventions (e.g., "all files in `scripts/a1_*.py` are A1-related") — explicit is safer
- When a script's purpose overlaps with a package, the package's `paths` is the authoritative mapping

**Avoiding duplicate implementations:**
- Before creating a new script, grep for its proposed name pattern and check if a sibling exists
- When extending, prefer adding parameters to existing scripts over creating new ones
- Deprecate by marking in `change-packages.yml` and adding a `DEPRECATED` docstring header, not by deleting

**When to extend vs create:**
- Extend when the new behavior is a strict superset of the existing contract and existing callers still work
- Create when the new behavior requires different env vars, output format, or exit code semantics
- The `select_*.py` pattern shows the right approach: a new selector script for a new package, not a new entry point

### Gap analysis

| Gap | Evidence |
|---|---|
| No canonical script registry | `change-packages.yml` paths are scattered; `inventory_repository.py` has a `CANONICAL` dict but it's hardcoded and small |
| `inventory_repository.py` classifications are incomplete | `CANONICAL` only covers 7 files; the rest fall through to `manual-review` |
| No deprecation workflow | Scripts like `validate_ocr_proposals.py` appear in `quarantined_unrelated` but there's no process for migrating them out |
| `audit_agent_dirs.py` is a one-off, not integrated | It writes to `cli-docs-update/` which is in `quarantined_unrelated` |
| Skill-to-script mapping is implicit | Each skill lists its canonical scripts in prose; there's no programmatic link |

### Recommended approach

1. **Expand `inventory_repository.py`'s `CANONICAL`** to cover all scripts that appear in `change-packages.yml` check commands. This creates a bidirectional map: script → package, package → canonical scripts.

2. **Add a `DEPRECATED` field to `change-packages.yml` packages** — scripts listed there are still valid but will be removed in a future release. The pre-commit hook should warn (not fail) on deprecated paths.

3. **Create `scripts/map_functionality.py`** — a script that reads `change-packages.yml` and produces a markdown table of "functionality → owning script → check command → package". Run it as part of `planning_cockpit` checks.

4. **Skill-to-script linkage:** Add a `canonical_scripts` list to each skill's YAML frontmatter. `audit_agent_dirs.py` can verify that every script listed in a skill is also declared in `change-packages.yml`.

---

## 6. Logging and Observability

### Current state in this repo

**Python script logging:**
- `validate_change_packages.py` writes to stderr with `flush=True` and uses `time.monotonic()` for duration tracking
- `run_release_reproducer.py` writes command output to files with SHA-256 digests in the receipt
- No use of Python's `logging` module anywhere in the scripts directory

**Log files:**
- OCR worker: `logs/ocr-worker.log` (sanitized tags, opaque run IDs)
- Runtime logs: `runtime/portal/supervised-<name>/logs/`
- Check output: `runtime/portal/temporary/change-checks-<uuid>/check-<N>.stdout`

**Receipts:**
- `run_release_reproducer.py`: `receipt.json` with per-check stdout/stderr paths and SHA-256
- `validate_change_packages.py`: `report.json` written atomically to `runtime/portal/temporary/change-checks-<uuid>/`

**Retention:**
- 90-day retention review default (from `AGENTS.md`)
- GitLab CI artifacts: `expire_in: 7d`
- No log rotation for application-level logs (infrastructure owns system log rotation)

### Best practice from authoritative sources

**Structured logging in Python:**
- Use `logging` module with `%(asctime)s %(levelname)s %(name)s %(message)s` format
- Emit JSON for machine-readable logs: `{"timestamp": "...", "level": "INFO", "logger": "...", "message": "...", "extra": {}}`
- Use `extra` dict for structured context (run_id, check_name, duration_ms)
- Never log credentials, cookies, request bodies, or raw OCR text

**JSON logging:**
- One JSON object per line (JSON Lines / NDJSON)
- Include `trace_id` / `span_id` for correlation
- Use `record.factory` to inject context

**Log rotation:**
- Application-level: `RotatingFileHandler` with `maxBytes` and `backupCount`
- Infrastructure-level: `logrotate` (already installed on s62)
- Retention policy: 90 days for operational logs, longer for audit trails (with holds/extensions)

**Correlation across scripts:**
- Propagate `RUN_ID` as an environment variable
- Each script includes `run_id` in every log line
- Parent scripts write a manifest that child scripts read

### Gap analysis

| Gap | Evidence |
|---|---|
| No structured logging | All scripts use `print()` to stderr; no `logging` module usage |
| No JSON log output | No `.jsonl` log files anywhere in `scripts/` |
| No correlation ID propagation | Each script generates its own identifiers independently |
| No log rotation for script logs | `logs/ocr-worker.log` rotates via infrastructure; script check output does not |
| Receipts are the only machine-readable record | If a script crashes before writing a receipt, there's no record |
| Sensitive data leakage risk | `run_release_reproducer.py` sanitizes env vars, but `validate_change_packages.py` doesn't; stderr may contain command output with sensitive data |

### Recommended approach

1. **Create `scripts/_log.py`** — a minimal structured logging helper:
   ```python
   import json, sys, time
   def log(level, msg, **extra):
       entry = {"ts": time.time(), "level": level, "msg": msg, **extra}
       print(json.dumps(entry), file=sys.stderr, flush=True)
   ```

2. **Adopt JSON Lines for all script stderr output.** This enables:
   - Machine parsing by the hook
   - Correlation by `run_id`
   - Filtering by `level`

3. **Propagate `RUN_ID` via environment variable.** The pre-commit hook sets it; all scripts inherit it. Receipts include it.

4. **Add a `--log-format json` flag** to scripts that currently use plain-text output (`validate_change_packages.py`, `validate_delivery_readiness.py`).

5. **Separate log streams:** Scripts that may emit sensitive data (like `run_release_reproducer.py` which handles env vars) should write to a file descriptor that's excluded from the hook's captured output.

6. **Receipts as the primary observability artifact.** Receipts should be queryable: store them in `runtime/portal/temporary/receipts/<date>/<run_id>.json` with a symlink `latest.json`.

---

## Summary of Recommendations

| Priority | Action | Owner | Effort |
|---|---|---|---|
| High | Create shared receipt helper (`scripts/_receipt.py`) | Engineering | 1 session |
| High | Add `--receipt-path` to all scripts | Engineering | 1 session |
| High | Create GitHub Actions CI workflow | Engineering | 1 session |
| Medium | Standardize exit codes across scripts | Engineering | 1 session |
| Medium | Add structured logging helper (`scripts/_log.py`) | Engineering | 1 session |
| Medium | Expand `inventory_repository.py` canonical map | Engineering | 1 session |
| Medium | Create `scripts/map_functionality.py` | Engineering | 1 session |
| Low | Move `market-research-evidence` to `.agents/skills/` | Jan (domain decision) | 1 session |
| Low | Add `DEPRECATED` field to `change-packages.yml` | Engineering | 30 min |
| Low | Add skill-to-script linkage in YAML frontmatter | Engineering | 30 min |
| Tracking | Activate GitLab CI (DEC-016) | Operator approval | Blocked |
