# AF2 Free-Model Trace Review

**Status:** evidence review; no provider, production, protected-data, Git, LiteLLM, or skill authority
**Reviewed:** 2026-08-15

## Verdict

The first AF2 live attempt is invalid as model evidence. Hy3 and DeepSeek
returned from contract-echo calls with process exit zero, but the harness
rejected both because its sanitizer treated the legitimate typed
`step_finish.tokens` usage field as a credential key. No trace or Luna call
ran. Both models are **unproven due to a harness defect**, not rejected for
model behavior.

The immutable invalid receipts remain under
`runtime/free-model-eval/af2/latest/receipts/`. Both prove unchanged repository
state and contain `contract_echo_failed`; their empty/sentinel hashes cannot
prove the returned echo content.

## Confirmed defects

- Recursive substring matching of `token` rejected the sanitizer's own typed
  `tokens` field.
- Echo failure discarded sanitized evidence and mixed zero sentinels with the
  canonical empty SHA-256.
- Independent JSONL reparsing and `part: null` could abort without a controlled
  receipt.
- The Codex adapter did not provide exact-read evidence or fail closed on every
  command, MCP, or file-change event.
- Validation could report success after a free promotion without Luna.
- Several declared limits, retry rules, and compatibility gates were unenforced.

## Rejected recommendation

Do not add `--unshare-net` to the provider worker: it must reach the selected
inference endpoint. The relevant boundaries remain filesystem isolation, a
two-file synthetic workspace, a read-only single-provider credential capsule,
and default-deny worker tools. Network isolation remains mandatory for local
acceptance tests, not provider inference.

## Repair decision

Plan AF2.1 uses a fixed diagnostic schema and scans only untrusted tool inputs,
final text, and provider error messages. It hashes retained sanitized bytes,
uses one strict event adapter, pins OpenCode 1.18.18, creates immutable AF2.1
run directories, and requires the Luna arm after a free candidate passes.
Historical AF2 evidence is never overwritten or reinterpreted.

## Verified findings (2026-08-15, AF2.1 offline validation)

### Canonical empty hash sentinel

`src/free_model_eval/engine.py` now imports `HASH_EMPTY` from `core` and uses it
for the `metadata_hash` fallback at both preflight and run completion sites,
replacing the `"0"*64` string. The free-model receipt schema
(`config/free-model-eval/free-model-receipt.schema.json`) only requires a 64-char
hex `hash`, so `HASH_EMPTY` is schema-valid. No free-model-eval test asserts the
literal `"0"*64` sentinel (only research-collector tests in another scope do).

Verification: focused AF2.1 test files pass (26 passed), full suite passes
(429 passed, 1 skipped, 12 subtests) after the change.

### Luna adapter defect (verified against Codex 0.147 source)

Verified against the openai/codex source at commit
`be6e8eac029b183056b7e4402879f15d2c85f61b`
(`codex-rs/exec/src/exec_events.rs` and the JSONL-output processor).

Real `codex exec --json` emits top-level `ThreadEvent` lines typed exactly
`thread.started`, `turn.started`, `turn.completed`, `turn.failed`,
`item.started`, `item.updated`, `item.completed`, `error`. Item types are
`agent_message`, `reasoning`, `command_execution`, `file_change`,
`mcp_tool_call`, `collab_tool_call`, `web_search`, `todo_list`, `error`.

Critical consequences for the current Luna adapter in `engine.py::_codex_events`:

- **No `file_read` item type exists.** Reads surface as `command_execution`
  items whose raw `command` string is a shell read (e.g.
  `sed -n '1,260p' README.md`). The `command_actions`/structured read shape
  exists only in the app-server protocol (`codex_app_server_protocol`), not in
  `codex exec --json` output.
- `item.started` is not emitted for `agent_message`/`reasoning`; it is emitted
  for `command_execution`. `item.completed` is emitted for non-empty
  `reasoning` and for `command_execution`.
- The current adapter only accepts `file_read` reads (never emitted) and
  rejects every other completed item type (`reasoning`, `command_execution`)
  and any unexpected `item.started` kind, raising
  `unauthorized Codex item` / `unexpected Codex event type`.

**Result:** on any real Codex run the adapter fails closed (EvalFailure), so
Luna is structurally guaranteed to be **unproven**. This is safe but means the
Luna arm can never pass, so a bounded run-af21 cannot reach overall success as
the plan currently requires Luna receipts after three free passes. The plan's
Required behavior line "accept only observed exact-manifest `file_read`
events" was based on a false premise and needs a design decision before the
next live run:

- **Option A — Codex-specific exact-read adapter:** parse `command_execution`
  items; record read evidence only when the command string is a pure read of an
  allowlisted manifest file; reject non-read commands, MCP, file changes,
  external reads, and unknown events; treat non-empty `reasoning` as benign;
  add recorded Codex-shaped JSONL fixtures and tests. Matches the earlier
  mandate ("accept only observed reads of the two allowlisted files; reject
  command execution, MCP, file changes, or reads outside the manifest").
- **Option B — keep fail-closed:** Luna stays unproven by design; document that
  overall run-af21 success is then unattainable and the control gate is
  effectively void.

### Codex exec harness flags (verified against codex-cli 0.147.0 `--help`)

`--ephemeral`, `--ignore-user-config`, `--skip-git-repo-check`, `--json`,
`--color never`, `-m`, `-c`, `-s read-only`, `--output-schema <FILE>`,
`-C/--cd`, `--add-dir`, `-o/--output-last-message`, `--approve-for-me`,
`--dangerously-bypass-approvals-and-sandbox`,
`--dangerously-bypass-hook-trust`, `--ignore-rules`, `-h`, `-V` all exist.

## Deferred backlog

- **Decided and implemented 2026-08-16:** Option A with preventive OS isolation is
  selected and [Plan AF2.2](../../plans/2026-08-16-plan-af2.2-luna-capsule-isolation.md)
  is executed. A strict `command_execution` exact-read adapter inside a Bubblewrap
  capsule now handles the Codex control run: synthetic workspace read-only mounted
  with only `README.md`/`AGENTS.md` plus `.output.schema.json`; isolated
  `CODEX_HOME=/home/codex` with a mode-600 copy of `auth.json`; pinned Codex
  0.147.0 mounted at `/codex` invoked with `--ephemeral`, `--ignore-user-config`,
  `-s read-only`, `--json`, `--output-schema`; no `--unshare-net` (provider
  networking), no repo/Git/MCP/plugins/skills/external dirs. The adapter accepts
  only strictly parsed completed `command_execution` items whose command is
  exactly `cat <allowlisted relative file>` or `sed -n '<N>,<M>p' <allowlisted
  relative file>`; `reasoning` items are permitted protocol metadata and never
  persisted; pipelines, redirections, substitutions, globs, compound commands,
  absolute paths, traversal, writes, interpreters, unknown commands, `file_change`,
  MCP/other items, `turn.failed`, and stream `error` events all fail closed.
  Recorded Codex-shaped JSONL fixtures (pinned to
  `openai/codex@be6e8eac029b183056b7e4402879f15d2c85f61b`,
  `codex-rs/exec/src/exec_events.rs`) cover valid reads and 19 negative classes;
  a real bwrap containment probe proves host and repository paths are unreadable
  from the capsule. Policy pins `codex_required_version=0.147.0` and
  `codex_reader_commands=["cat","sed"]`; preflight now gates the pinned binary and
  version. Gates green: focused AF tests, full suite (452 passed, 1 skipped),
  `validate_planning.py`, `generate_planning_asset.py --check`,
  `validate_change_packages.py --json`, `git diff --check`. No live invocation and
  no Goal-mode switch until a new immutable run passes these gates.
- Replace the brace-count metadata parser if OpenCode changes its verbose form.
- Review a new compatibility adapter before accepting new binary/event versions.
- Expand CLI and credential-capsule integration tests without reading secrets.
- Keep alternative models, LiteLLM, review/code tasks, and skill activation in
  later plans.
