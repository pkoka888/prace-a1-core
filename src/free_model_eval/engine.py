from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from .core import (
    EXIT_FAILURE,
    EXIT_OK,
    EXIT_UNPROVEN,
    EvalFailure,
    EvalUnproven,
    HASH_EMPTY,
    bwrap_command,
    canonical_bytes,
    codex_bwrap_command,
    codex_credential_home,
    copy_fixture,
    credential_home,
    load_json,
    packet_for,
    parse_events,
    parse_verbose_models,
    repository_snapshot,
    resolve_codex_auth,
    resolve_codex_binary,
    resolve_opencode_binary,
    resolve_opencode_auth,
    run_command,
    safe_cleanup,
    safe_relative,
    sanitized_preflight,
    score_review,
    score_total,
    sha256_bytes,
    task_prompt,
    tree_hash,
    utc_now,
    validate_citations,
    validate_packet,
    validate_schema,
    normalized_json_output,
    sanitize_event_stream,
    validate_contract_echo,
    validate_citations_af2,
    validate_codex_auth_source,
    final_text_from_events,
)


def af2_packet(root: Path, runner_name: str, model: str, policy: dict) -> dict:
    packet = packet_for(root, "trace", runner_name, model, policy)
    fixture = root / "tests/fixtures/free_model_eval/trace_v1_1"
    packet["protocol_version"] = "1.1"
    packet["contract_echo_required"] = True
    packet["file_manifest"] = [
        {"path": path, "sha256": sha256_bytes((fixture / path).read_bytes())}
        for path in packet["allowed_paths"]
    ]
    packet["expected_evidence"] = load_json(fixture / "expected.json")
    packet["prompt_template"] = af2_trace_prompt(packet, runner_name)
    return packet


def af2_echo_prompt(packet: dict) -> str:
    expected = {
        "schema_version": "1.0",
        "task_id": packet["task_id"],
        "allowed_paths": packet["allowed_paths"],
        "output_schema_version": packet["output_schema_version"],
        "forbidden_actions_acknowledged": True,
    }
    return (
        "PUBLIC SYNTHETIC CONTRACT ECHO. Use no tools. Return exactly this raw JSON object "
        "with no Markdown and no extra keys: "
        + json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
    )


def af2_trace_prompt(packet: dict, runner_name: str = "opencode") -> str:
    manifest = json.dumps(
        packet["file_manifest"], ensure_ascii=False, separators=(",", ":")
    )
    if runner_name == "codex":
        reads = (
            "Read exactly README.md and AGENTS.md individually using relative paths from the "
            "workspace root with a single pure reader command per file (for example: "
            "sed -n '1,260p' README.md). Never prefix a command with /workspace and do not "
            "discover, list, glob, grep, pipe, redirect, substitute, or read any other path."
        )
    else:
        reads = (
            "Read exactly /workspace/README.md and /workspace/AGENTS.md individually. Do not "
            "read /workspace itself and do not discover, list, glob, grep, or read any other path."
        )
    return (
        "PUBLIC SYNTHETIC TRACE PROTOCOL 1.1. Task ID: " + packet["task_id"] + ". "
        "Exact ordered file manifest: " + manifest + ". " + reads + " "
        "Output citation paths MUST be exactly README.md or "
        "AGENTS.md: relative, case-sensitive, without /workspace, ./, URI syntax, or normalization. "
        "Return one raw JSON object, no Markdown fences and no extra keys. Each fact must occur exactly "
        "once and be one of planning-only, portal-not-implemented, synthetic-only. Shape example only "
        '(values are deliberately not answers): {"claims":[{"fact":"planning-only",'
        '"path":"README.md","line":1,"quote":"EXACT SUBSTRING FROM THAT LINE"}]}'
    )


def copy_af2_worker_workspace(root: Path, destination: Path) -> None:
    fixture = root / "tests/fixtures/free_model_eval/trace_v1_1"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "AGENTS.md"):
        shutil.copy2(fixture / name, destination / name)


def _run_opencode_af2(
    root: Path,
    policy: dict,
    run_root: Path,
    workspace: Path,
    agent_name: str,
    model: str,
    prompt: str,
    timeout: int,
):
    runtime = run_root / "credentials"
    runtime.mkdir(parents=True, exist_ok=True)
    with credential_home(policy, runtime) as home:
        agent_source = root / ".opencode/agents" / f"{agent_name}.md"
        agent_target = home / ".config/opencode/agents"
        agent_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_source, agent_target / agent_source.name)
        command = bwrap_command(
            resolve_opencode_binary(policy), workspace, home, agent_name, model, prompt
        )
        return run_command(command, timeout=timeout)


def _write_af2_diagnostics(
    directory: Path, stdout: str, output: dict, policy: dict
) -> tuple[str, str]:
    event_hash = _write_af2_events(directory, stdout, policy)
    output_hash = _write_af2_output(directory, output)
    return event_hash, output_hash


def _write_af2_events(directory: Path, stdout: str, policy: dict) -> str:
    payload, event_hash = sanitize_event_stream(stdout, policy)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "events.jsonl").write_bytes(payload)
    return event_hash


def _write_af2_output(directory: Path, output: dict) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    output_bytes = canonical_bytes(output)
    (directory / "final-output.json").write_bytes(output_bytes)
    return sha256_bytes(output_bytes)


def _write_codex_diagnostics(
    directory: Path, tools: list[dict], tokens: dict, output: dict, policy: dict
) -> tuple[str, str]:
    events = []
    for tool in tools:
        events.append(
            {
                "type": "tool_use",
                "part": {
                    "tool": "read",
                    "state": {"status": "completed", "input": tool["input"]},
                },
            }
        )
    events.append({"type": "step_finish", "part": {"tokens": tokens, "cost": None}})
    events.append(
        {
            "type": "text",
            "part": {
                "text": json.dumps(output, ensure_ascii=False, separators=(",", ":"))
            },
        }
    )
    raw = "\n".join(json.dumps(event, ensure_ascii=False) for event in events)
    return _write_af2_diagnostics(directory, raw, output, policy)


def run_af2_one(
    root: Path,
    policy: dict,
    preflight_report: dict,
    runner_name: str,
    model: str,
    repetition: int,
    run_root: Path,
    attempt: int = 1,
) -> tuple[dict, int]:
    packet = af2_packet(root, runner_name, model, policy)
    validate_packet(
        packet,
        root / "config/free-model-eval/free-model-task-packet.schema.json",
        policy,
    )
    run_id = f"af2-trace-{runner_name}-{model.replace('/', '-')}-{repetition}-attempt-{attempt}-{uuid.uuid4().hex[:8]}"
    workspace = run_root / "runs" / run_id
    copy_af2_worker_workspace(root, workspace)
    repo_before = repository_snapshot(root)
    workspace_before = tree_hash(workspace, exclude=(".opencode",))
    started = utc_now()
    errors = []
    failure_codes = []
    tools = []
    tokens = {}
    cost = None
    empty_hash = sha256_bytes(b"")
    echo_result = None
    echo_output = {}
    echo_event_hash = empty_hash
    echo_output_hash = empty_hash
    if runner_name == "opencode":
        echo_space = run_root / "runs" / (run_id + "-echo")
        copy_af2_worker_workspace(root, echo_space)
        echo_packet = dict(packet)
        echo_packet["allowed_tools"] = []
        echo_result = _run_opencode_af2(
            root,
            policy,
            run_root,
            echo_space,
            "free-eval-contract-echo",
            model,
            af2_echo_prompt(packet),
            policy["contract_echo_timeout_seconds"],
        )
        try:
            if echo_result.returncode or echo_result.timed_out:
                raise EvalUnproven("contract echo transport unavailable")
            echo_directory = run_root / "diagnostics" / (run_id + "-echo")
            echo_event_hash = _write_af2_events(
                echo_directory, echo_result.stdout, policy
            )
            echo_output, echo_tools, _, echo_cost = parse_events(
                echo_result.stdout,
                policy,
                echo_packet,
                max_output_bytes=policy["contract_echo_max_output_bytes"],
            )
            if echo_tools or echo_cost not in (None, 0.0):
                raise EvalFailure("contract echo tool or cost violation")
            validate_contract_echo(
                echo_output,
                packet,
                root / "config/free-model-eval/contract-echo-output.schema.json",
            )
            echo_output_hash = _write_af2_output(echo_directory, echo_output)
            echo_passed = True
        except EvalUnproven as exc:
            errors.append(str(exc))
            failure_codes.append("echo_unproven")
            echo_passed = False
        except EvalFailure as exc:
            errors.append(str(exc))
            failure_codes.append("contract_echo_failed")
            echo_passed = False
        safe_cleanup(echo_space, run_root / "runs")
    else:
        echo_passed = True
        echo_event_hash = sha256_bytes(b"codex-control-no-separate-echo\n")
        echo_output_hash = sha256_bytes(b"codex-control-no-separate-echo\n")

    trace_result = None
    output = {}
    output_valid = False
    citations_valid = False
    diagnostic = False
    scores = {}
    original_hash = empty_hash
    normalized_hash = empty_hash
    sanitized_event_hash = empty_hash
    hard = {
        "privacy": True,
        "preflight": True,
        "credential": True,
        "contract_echo": echo_passed,
        "events": False,
        "schema": False,
        "read_contract": False,
        "fact_contract": False,
        "citation_contract": False,
        "scope": False,
        "repository_unchanged": False,
        "acceptance": True,
    }
    if echo_passed:
        if runner_name == "opencode":
            trace_result = _run_opencode_af2(
                root,
                policy,
                run_root,
                workspace,
                "free-eval-read",
                model,
                packet["prompt_template"],
                packet["timeout_seconds"],
            )
        else:
            _copy_codex_schema(root, "trace", workspace)
            runtime = run_root / "credentials"
            runtime.mkdir(parents=True, exist_ok=True)
            with codex_credential_home(policy, root, runtime) as home:
                command = codex_bwrap_command(
                    resolve_codex_binary(policy),
                    workspace,
                    home,
                    model,
                    policy["codex_reasoning_effort"],
                    packet["prompt_template"],
                )
                trace_result = run_command(command, timeout=packet["timeout_seconds"])
        if trace_result.returncode or trace_result.timed_out:
            errors.append("trace transport unavailable")
            failure_codes.append("trace_unproven")
        else:
            try:
                trace_directory = run_root / "diagnostics" / run_id
                if runner_name == "opencode":
                    sanitized_event_hash = _write_af2_events(
                        trace_directory, trace_result.stdout, policy
                    )
                    diagnostic = True
                    output, tools, tokens, cost = parse_events(
                        trace_result.stdout, policy, packet
                    )
                    final_text = final_text_from_events(trace_result.stdout, policy)
                else:
                    output, tools, tokens, cost = _codex_events(
                        trace_result.stdout, packet
                    )
                    final_text = json.dumps(output, ensure_ascii=False)
                    sanitized_event_hash, _ = _write_codex_diagnostics(
                        trace_directory, tools, tokens, output, policy
                    )
                    diagnostic = True
                _, original_hash, normalized_hash = normalized_json_output(final_text)
                if cost not in (None, 0.0):
                    raise EvalFailure("non-zero reported free-model cost")
                hard["events"] = True
                validate_schema(
                    output, root / "config/free-model-eval/trace-output.schema.json"
                )
                output_valid = hard["schema"] = True
                citations_valid, scores, citation_errors, codes = (
                    validate_citations_af2(
                        output, workspace, packet["expected_evidence"], tools
                    )
                )
                errors.extend(citation_errors)
                failure_codes.extend(codes)
                read_codes = {"missing_read"}
                fact_codes = {"unsupported_fact", "duplicate_fact", "missing_fact"}
                citation_codes = {
                    "invalid_citation_path",
                    "invalid_line_type",
                    "invalid_line",
                    "invalid_quotation",
                    "unsupported_citation",
                }
                hard["read_contract"] = not read_codes.intersection(codes)
                hard["fact_contract"] = not fact_codes.intersection(codes)
                hard["citation_contract"] = not citation_codes.intersection(codes)
                _write_af2_output(trace_directory, output)
            except EvalUnproven as exc:
                errors.append(str(exc))
                failure_codes.append("trace_unproven")
            except EvalFailure as exc:
                errors.append(str(exc))
                failure_codes.append("event_or_schema_failure")
    workspace_after = tree_hash(workspace, exclude=(".opencode", ".output.schema.json"))
    hard["scope"] = workspace_before == workspace_after
    repo_after = repository_snapshot(root)
    hard["repository_unchanged"] = repo_before == repo_after
    if not hard["repository_unchanged"]:
        errors.append("main repository changed")
        failure_codes.append("repository_mutation")
    total = score_total(
        "trace",
        scores,
        schema_ok=output_valid,
        tool_ok=hard["events"],
        acceptance=True,
        scope_ok=hard["scope"],
    )
    candidate = all(hard.values()) and citations_valid and not errors and total >= 90
    unproven = any(code.endswith("_unproven") for code in failure_codes)
    disposition = "candidate" if candidate else ("unproven" if unproven else "rejected")
    _trace_stdout = trace_result.stdout if trace_result else ""
    receipt = {
        "schema_version": "1.0",
        "protocol_version": "1.1",
        "repetition": repetition,
        "attempt": attempt,
        "task_id": packet["task_id"],
        "task_class": "trace",
        "runner": runner_name,
        "requested_model": model,
        "reported_model": model,
        "reported_provider": "opencode"
        if runner_name == "opencode"
        else "openai-codex",
        "packet_hash": sha256_bytes(canonical_bytes(packet)),
        "fixture_hash": tree_hash(root / "tests/fixtures/free_model_eval/trace_v1_1"),
        "metadata_hash": preflight_report.get("metadata_hash", HASH_EMPTY),
        "started_at": started,
        "finished_at": utc_now(),
        "duration_ms": sum(x.duration_ms for x in (echo_result, trace_result) if x),
        "event_hash": sanitized_event_hash,
        "tool_events": tools,
        "tokens": tokens,
        "reported_cost": cost,
        "process_exit": trace_result.returncode
        if trace_result
        else (echo_result.returncode if echo_result else 0),
        "timed_out": bool(
            (trace_result and trace_result.timed_out)
            or (echo_result and echo_result.timed_out)
        ),
        "output_valid": output_valid,
        "citations_valid": citations_valid,
        "workspace_before": workspace_before,
        "workspace_after": workspace_after,
        "repository_before": repo_before,
        "repository_after": repo_after,
        "acceptance_passed": True,
        "hard_gates": hard,
        "scores": scores,
        "total_score": total,
        "disposition": disposition,
        "errors": errors,
        "next_action": "Codex review" if candidate else "Do not promote",
        "contract_echo": {
            "passed": echo_passed,
            "event_hash": echo_event_hash,
            "output_hash": echo_output_hash,
            "diagnostic_retained": echo_event_hash != empty_hash,
        },
        "failure_codes": sorted(set(failure_codes)),
        "diagnostic_artifacts_retained": diagnostic,
        "sanitized_event_artifact_hash": sanitized_event_hash,
        "original_output_hash": original_hash,
        "normalized_output_hash": normalized_hash,
    }
    validate_schema(
        receipt, root / "config/free-model-eval/free-model-receipt.schema.json"
    )
    path = run_root / "receipts" / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(receipt))
    safe_cleanup(workspace, run_root / "runs")
    return receipt, EXIT_OK if candidate else (
        EXIT_UNPROVEN if disposition == "unproven" else EXIT_FAILURE
    )


def verify_fixtures(root: Path, policy: dict) -> dict:
    schema = root / "config/free-model-eval/free-model-task-packet.schema.json"
    hashes = {}
    for task in policy["tasks"]:
        fixture = root / "tests/fixtures/free_model_eval" / task
        if not fixture.is_dir():
            raise EvalFailure(f"fixture missing: {task}")
        expected = load_json(fixture / "expected.json")
        if task == "trace" and not expected.get("required_facts"):
            raise EvalFailure("trace truth set empty")
        if task == "review" and set(expected.get("required_findings", [])) != {
            "off-by-one",
            "unsafe-path-prefix",
        }:
            raise EvalFailure("review truth set changed")
        if task == "code_draft" and expected.get("editable_paths") != [
            "solution/slugify.py"
        ]:
            raise EvalFailure("code edit boundary changed")
        hashes[task] = tree_hash(fixture)
        for runner, model in (
            ("opencode", policy["free_models"][0]),
            ("codex", policy["codex_control"].removeprefix("codex/")),
        ):
            validate_packet(
                packet_for(root, task, runner, model, policy), schema, policy
            )
    af2 = root / "tests/fixtures/free_model_eval/trace_v1_1"
    manifest = load_json(af2 / "task-manifest.json")
    expected_files = [
        {"path": name, "sha256": sha256_bytes((af2 / name).read_bytes())}
        for name in ("README.md", "AGENTS.md")
    ]
    if (
        manifest.get("protocol_version") != "1.1"
        or manifest.get("files") != expected_files
    ):
        raise EvalFailure("AF2 trace manifest hash drift")
    if policy.get("permitted_normalizations") != [
        "utf8-bom",
        "unicode-nfc",
        "json-whitespace",
    ]:
        raise EvalFailure("AF2 normalization policy drift")
    if policy.get("directory_reads_forbidden") is not True:
        raise EvalFailure("AF2 directory-read policy weakened")
    if policy.get("transient_retry_count") != 1:
        raise EvalFailure("AF2 retry count must remain exactly one")
    if policy.get("codex_required_version") != "0.147.0":
        raise EvalFailure("AF2 Codex version pin drift")
    if policy.get("codex_reader_commands") != ["cat", "sed"]:
        raise EvalFailure("AF2 Codex reader grammar drift")
    if policy.get(
        "codex_auth_source"
    ) != "dedicated-revocable-codex-store" or not policy.get("codex_auth_store"):
        raise EvalFailure("AF2 Codex auth must use a dedicated revocable store")
    recorded = af2 / "synthetic-codex"
    recorded_manifest = load_json(recorded / "MANIFEST.json")
    if (
        recorded_manifest.get("codex_commit")
        != "be6e8eac029b183056b7e4402879f15d2c85f61b"
    ):
        raise EvalFailure("AF2 synthetic-codex source pin drift")
    for name, steps in (
        ("free-eval-read.md", 12),
        ("free-eval-contract-echo.md", policy["contract_echo_max_steps"]),
    ):
        text = (root / ".opencode/agents" / name).read_text(encoding="utf-8")
        if f"steps: {steps}" not in text:
            raise EvalFailure(f"agent step limit drift: {name}")
    hashes["trace_v1_1"] = tree_hash(af2)
    return {"schema_version": "1.0", "fixtures": hashes}


def preflight(root: Path, policy: dict) -> tuple[dict, int]:
    opencode_binary = resolve_opencode_binary(policy)
    codex_binary = resolve_codex_binary(policy)
    required = ["bwrap", "unshare", str(opencode_binary), str(codex_binary)]
    missing = [
        item
        for item in required
        if not (Path(item).is_file() if "/" in item else shutil.which(item))
    ]
    if missing:
        return {
            "status": "unproven",
            "errors": ["missing: " + ", ".join(missing)],
        }, EXIT_UNPROVEN
    auth_path = resolve_opencode_auth(policy)
    try:
        auth = load_json(auth_path)
    except (OSError, EvalFailure, json.JSONDecodeError):
        return {
            "status": "unproven",
            "errors": ["OpenCode auth structure unavailable"],
        }, EXIT_UNPROVEN
    if policy["opencode_auth_provider"] not in auth:
        return {
            "status": "unproven",
            "errors": ["free-model provider auth entry unavailable"],
        }, EXIT_UNPROVEN
    codex_auth_path = resolve_codex_auth(policy, root)
    try:
        validate_codex_auth_source(codex_auth_path)
        codex_auth = load_json(codex_auth_path)
    except (OSError, EvalFailure, EvalUnproven, json.JSONDecodeError):
        return {
            "status": "unproven",
            "errors": ["dedicated Codex auth store unavailable"],
        }, EXIT_UNPROVEN
    if not isinstance(codex_auth, dict) or "tokens" not in codex_auth:
        return {
            "status": "unproven",
            "errors": ["dedicated Codex auth store structure invalid"],
        }, EXIT_UNPROVEN
    result = run_command(
        [str(opencode_binary), "models", "opencode", "--refresh", "--verbose"],
        timeout=60,
    )
    if result.timed_out or result.returncode:
        return {"status": "unproven", "errors": ["model refresh failed"]}, EXIT_UNPROVEN
    try:
        report = sanitized_preflight(parse_verbose_models(result.stdout), policy)
    except EvalUnproven as exc:
        return {"status": "unproven", "errors": [str(exc)]}, EXIT_UNPROVEN
    except EvalFailure as exc:
        return {"status": "failed", "errors": [str(exc)]}, EXIT_FAILURE
    versions = {}
    for name, command in {
        "opencode": [str(opencode_binary), "--version"],
        "codex": [str(codex_binary), "--version"],
        "bwrap": ["bwrap", "--version"],
        "unshare": ["unshare", "--version"],
    }.items():
        probe = run_command(command, timeout=10)
        if probe.returncode:
            return {
                "status": "unproven",
                "errors": [f"version probe failed: {name}"],
            }, EXIT_UNPROVEN
        versions[name] = (probe.stdout or probe.stderr).strip().splitlines()[0]
    if versions["opencode"] != policy["required_opencode_version"]:
        return {
            "status": "unproven",
            "errors": ["OpenCode version requires compatibility review"],
            "observed_version": versions["opencode"],
            "required_version": policy["required_opencode_version"],
        }, EXIT_UNPROVEN
    expected_codex_version = "codex-cli " + policy.get("codex_required_version", "")
    if versions["codex"] != expected_codex_version:
        return {
            "status": "unproven",
            "errors": ["Codex version requires compatibility review"],
            "observed_version": versions["codex"],
            "required_version": expected_codex_version,
        }, EXIT_UNPROVEN
    report.update(
        {
            "status": "pass",
            "versions": versions,
            "codex_control": policy["codex_control"],
            "codex_cost_gate": "control-not-free-api-candidate",
            "codex_auth_source": "dedicated-revocable-codex-store",
            "codex_auth_store": policy.get("codex_auth_store"),
        }
    )
    return report, EXIT_OK


_CODEX_SHELL_META = re.compile(r"[|;&<>`$()!*?{}\[\]#~]")
_CODEX_SED_RANGE = re.compile(r"^['\"]?[0-9]+,[0-9]+p['\"]?$")


def _parse_codex_read_command(command: str, allowed_paths: set[str]) -> str | None:
    """Strict pure-read grammar: one approved reader command and one declared file at a time."""
    if not command or command != command.strip():
        return None
    if _CODEX_SHELL_META.search(command):
        return None
    parts = command.split()
    if not parts:
        return None
    reader = parts[0]
    if reader == "cat":
        if len(parts) != 2:
            return None
        path = parts[1]
    elif reader == "sed":
        if len(parts) != 4 or parts[1] != "-n" or not _CODEX_SED_RANGE.match(parts[2]):
            return None
        path = parts[3]
    else:
        return None
    if path.startswith(".") or "/" in path or not safe_relative(path):
        return None
    if path not in allowed_paths:
        return None
    return path


def _codex_start_command(item: dict, allowed_paths: set[str]) -> str:
    command = item.get("command")
    if not isinstance(command, str) or not command:
        raise EvalFailure("Codex command_execution missing command")
    if _parse_codex_read_command(command, allowed_paths) is None:
        raise EvalFailure(f"unsafe or non-read Codex command: {command!r}")
    return command


def _codex_read_evidence(item: dict, allowed_paths: set[str]) -> dict:
    if item.get("status") != "completed":
        raise EvalFailure(f"Codex command did not complete: {item.get('status')}")
    if item.get("exit_code") != 0:
        raise EvalFailure(f"Codex command exit code: {item.get('exit_code')}")
    command = item.get("command")
    if not isinstance(command, str) or not command:
        raise EvalFailure("Codex command_execution missing command")
    path = _parse_codex_read_command(command, allowed_paths)
    if path is None:
        raise EvalFailure(f"unsafe or non-read Codex command: {command!r}")
    return {
        "tool": "read",
        "input": {"filePath": f"/workspace/{path}"},
        "status": "completed",
    }


def _codex_events(
    text: str, packet: dict
) -> tuple[dict, list[dict], dict, float | None]:
    finals = []
    tools = []
    tokens = {}
    allowed_paths = set(packet["allowed_paths"])
    started: dict[str, str] = {}
    completed: set[str] = set()
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvalFailure(f"malformed Codex JSONL event {number}") from exc
        if not isinstance(event, dict):
            raise EvalFailure(f"Codex event {number} must be an object")
        kind = event.get("type")
        if kind in {"thread.started", "turn.started"}:
            continue
        if kind == "turn.completed":
            usage = event.get("usage")
            if isinstance(usage, dict) and usage:
                tokens = usage
            continue
        if kind == "turn.failed":
            error = event.get("error") or {}
            message = str(error.get("message") or "turn failed")
            raise EvalFailure(f"Codex turn failed: {message[:160]}")
        if kind == "error":
            message = str(event.get("message") or "stream error")
            raise EvalFailure(f"Codex stream error: {message[:160]}")
        if kind in {"item.started", "item.updated", "item.completed"}:
            item = event.get("item")
            if not isinstance(item, dict):
                raise EvalFailure(f"invalid Codex item in {kind}")
            item_type = item.get("type")
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                raise EvalFailure(f"Codex {kind} item missing id")
            if kind == "item.started":
                if item_type == "command_execution":
                    if item_id in started:
                        raise EvalFailure(f"duplicate Codex item start: {item_id}")
                    started[item_id] = _codex_start_command(item, allowed_paths)
                elif item_type != "reasoning":
                    raise EvalFailure(f"unauthorized Codex item: {item_type}")
                continue
            if kind == "item.updated":
                if item_type not in {"command_execution", "reasoning"}:
                    raise EvalFailure(f"unauthorized Codex item: {item_type}")
                if item_type == "command_execution":
                    if item_id in completed:
                        raise EvalFailure(
                            f"Codex command update after completion: {item_id}"
                        )
                    if (
                        item_id not in started
                        or item.get("command") != started[item_id]
                    ):
                        raise EvalFailure(f"Codex command changed on update: {item_id}")
                continue
            if item_type == "agent_message":
                finals.append(item.get("text", ""))
            elif item_type == "reasoning":
                continue
            elif item_type == "command_execution":
                if item_id not in started:
                    raise EvalFailure(
                        f"Codex command completed without item.started: {item_id}"
                    )
                if item_id in completed:
                    raise EvalFailure(f"duplicate Codex command completion: {item_id}")
                if item.get("command") != started[item_id]:
                    raise EvalFailure(f"Codex command changed on completion: {item_id}")
                tools.append(_codex_read_evidence(item, allowed_paths))
                completed.add(item_id)
            else:
                raise EvalFailure(f"unauthorized Codex item: {item_type}")
            continue
        raise EvalFailure(f"unexpected Codex event type: {kind}")
    incomplete = sorted(set(started) - completed)
    if incomplete:
        raise EvalFailure(f"Codex commands never completed: {','.join(incomplete)}")
    if len(finals) != 1:
        raise EvalFailure(f"exactly one Codex final text required, got {len(finals)}")
    text_value = finals[0]
    if text_value.lstrip().startswith("```"):
        raise EvalFailure("Markdown-wrapped JSON is forbidden")
    output, _, _ = normalized_json_output(text_value)
    return output, tools, tokens, None


def _copy_codex_schema(root: Path, task: str, workspace: Path) -> Path:
    name = {
        "trace": "trace-output.schema.json",
        "review": "review-output.schema.json",
        "code_draft": "code-output.schema.json",
    }[task]
    target = workspace / ".output.schema.json"
    shutil.copy2(root / "config/free-model-eval" / name, target)
    return target


def run_one(
    root: Path,
    policy: dict,
    preflight_report: dict,
    task: str,
    runner_name: str,
    model: str,
    repetition: int,
    run_root: Path,
) -> tuple[dict, int]:
    schema_root = root / "config/free-model-eval"
    packet = packet_for(root, task, runner_name, model, policy)
    validate_packet(packet, schema_root / "free-model-task-packet.schema.json", policy)
    run_id = f"{task}-{runner_name}-{model.replace('/', '-')}-{repetition}-{uuid.uuid4().hex[:8]}"
    workspace = run_root / "runs" / run_id
    workspace.mkdir(parents=True)
    agent = (
        root
        / ".opencode/agents"
        / ("free-eval-code-draft.md" if task == "code_draft" else "free-eval-read.md")
    )
    copy_fixture(root, task, workspace, agent)
    packet_path = workspace / "task-packet.json"
    packet_path.write_bytes(canonical_bytes(packet))
    repo_before = repository_snapshot(root)
    workspace_before = tree_hash(workspace, exclude=(".opencode", "task-packet.json"))
    protected_before = tree_hash(
        workspace, exclude=(".opencode", "task-packet.json", "solution")
    )
    started = utc_now()
    if runner_name == "opencode":
        runtime = run_root / "credentials"
        runtime.mkdir(parents=True, exist_ok=True)
        with credential_home(policy, runtime) as home:
            command = bwrap_command(
                resolve_opencode_binary(policy),
                workspace,
                home,
                "free-eval-code-draft" if task == "code_draft" else "free-eval-read",
                model,
                task_prompt(task),
            )
            result = run_command(command, timeout=packet["timeout_seconds"])
    else:
        output_schema = _copy_codex_schema(root, task, workspace)
        command = [
            str(resolve_codex_binary(policy)),
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--json",
            "--color",
            "never",
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{policy["codex_reasoning_effort"]}"',
            "-s",
            "workspace-write" if task == "code_draft" else "read-only",
            "--output-schema",
            str(output_schema),
            "-C",
            str(workspace),
            task_prompt(task),
        ]
        result = run_command(command, timeout=packet["timeout_seconds"])
    finished = utc_now()
    errors = []
    disposition = "rejected"
    output_valid = citations_valid = acceptance = False
    scores = {}
    tools = []
    tokens = {}
    cost = None
    hard = {
        "privacy": True,
        "preflight": True,
        "credential": True,
        "events": False,
        "schema": False,
        "scope": False,
        "repository_unchanged": False,
        "acceptance": task != "code_draft",
    }
    if result.timed_out or result.returncode:
        errors.append(
            "timeout" if result.timed_out else f"worker exit {result.returncode}"
        )
        disposition = (
            "unproven"
            if result.timed_out or result.returncode in policy["retryable_statuses"]
            else "rejected"
        )
    else:
        try:
            if runner_name == "opencode":
                output, tools, tokens, cost = parse_events(
                    result.stdout, policy, packet
                )
                if cost not in (None, 0.0):
                    raise EvalFailure("non-zero reported free-model cost")
            else:
                output, tools, tokens, cost = _codex_events(result.stdout, packet)
            hard["events"] = True
            validate_schema(output, schema_root / packet["required_output_schema"])
            output_valid = hard["schema"] = True
            if task == "trace":
                citations_valid, component, citation_errors = validate_citations(
                    output, workspace, packet["expected_evidence"], tools
                )
                scores.update(component)
                errors.extend(citation_errors)
            elif task == "review":
                component, review_errors = score_review(
                    output, packet["expected_evidence"]
                )
                scores.update(component)
                errors.extend(review_errors)
                citations_valid = not review_errors
            else:
                changed = set(output.get("changed_paths", []))
                citations_valid = changed == {"solution/slugify.py"}
                if not citations_valid:
                    errors.append("changed_paths contract mismatch")
        except EvalFailure as exc:
            errors.append(str(exc))
    workspace_after = tree_hash(
        workspace, exclude=(".opencode", "task-packet.json", ".output.schema.json")
    )
    if task == "code_draft":
        fixture = root / "tests/fixtures/free_model_eval/code_draft"
        tests_equal = (workspace / "tests/test_slugify.py").read_bytes() == (
            fixture / "tests/test_slugify.py"
        ).read_bytes()
        unexpected = [
            p.relative_to(workspace).as_posix()
            for p in workspace.rglob("*")
            if p.is_file()
            and not (
                p.relative_to(workspace)
                .as_posix()
                .startswith(("solution/", "tests/", ".opencode/"))
                or p.name
                in {"expected.json", "task-packet.json", ".output.schema.json"}
            )
        ]
        protected_after = tree_hash(
            workspace,
            exclude=(
                ".opencode",
                "task-packet.json",
                ".output.schema.json",
                "solution",
            ),
        )
        hard["scope"] = (
            tests_equal and not unexpected and protected_before == protected_after
        )
        if output_valid and hard["scope"]:
            test_env = {
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str(workspace),
                "HOME": str(workspace),
            }
            test = run_command(
                [
                    "unshare",
                    "--user",
                    "--map-root-user",
                    "--net",
                    "--",
                    str(root / "venv/bin/python"),
                    "-m",
                    "pytest",
                    "tests/test_slugify.py",
                    "-q",
                ],
                cwd=workspace,
                env=test_env,
                timeout=30,
            )
            acceptance = test.returncode == 0
            if not acceptance:
                errors.append("acceptance test failed")
        hard["acceptance"] = acceptance
    else:
        hard["scope"] = workspace_before == workspace_after
        acceptance = True
    repo_after = repository_snapshot(root)
    hard["repository_unchanged"] = repo_before == repo_after
    if not hard["repository_unchanged"]:
        errors.append("main repository changed during trial")
    total = score_total(
        task,
        scores,
        schema_ok=output_valid,
        tool_ok=hard["events"],
        acceptance=acceptance,
        scope_ok=hard["scope"],
    )
    # Per-run score excludes the aggregate repeatability component. Promotion is
    # decided only by validate_run after all three repetitions are present.
    threshold = {"trace": 90, "review": 88, "code_draft": 85}[task]
    if all(hard.values()) and citations_valid and not errors and total >= threshold:
        disposition = "candidate"
    receipt = {
        "schema_version": "1.0",
        "protocol_version": packet.get("protocol_version", "1.0"),
        "task_id": packet["task_id"],
        "task_class": task,
        "runner": runner_name,
        "requested_model": model,
        "reported_model": model,
        "reported_provider": "opencode"
        if runner_name == "opencode"
        else "openai-codex",
        "packet_hash": sha256_bytes(canonical_bytes(packet)),
        "fixture_hash": tree_hash(root / "tests/fixtures/free_model_eval" / task),
        "metadata_hash": preflight_report.get("metadata_hash", HASH_EMPTY),
        "started_at": started,
        "finished_at": finished,
        "duration_ms": result.duration_ms,
        "event_hash": sha256_bytes(result.stdout.encode()),
        "tool_events": tools,
        "tokens": tokens,
        "reported_cost": cost,
        "process_exit": result.returncode,
        "timed_out": result.timed_out,
        "output_valid": output_valid,
        "citations_valid": citations_valid,
        "workspace_before": workspace_before,
        "workspace_after": workspace_after,
        "repository_before": repo_before,
        "repository_after": repo_after,
        "acceptance_passed": acceptance,
        "hard_gates": hard,
        "scores": scores,
        "total_score": total,
        "disposition": disposition,
        "errors": errors,
        "next_action": "Codex review"
        if disposition == "candidate"
        else "Do not promote",
    }
    validate_schema(receipt, schema_root / "free-model-receipt.schema.json")
    receipt_path = run_root / "receipts" / f"{run_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(canonical_bytes(receipt))
    safe_cleanup(workspace, run_root / "runs")
    return receipt, EXIT_OK if disposition == "candidate" else (
        EXIT_UNPROVEN if disposition == "unproven" else EXIT_FAILURE
    )


def validate_run(root: Path, run_dir: Path) -> tuple[dict, int]:
    schema = root / "config/free-model-eval/free-model-receipt.schema.json"
    receipts = []
    for path in sorted((run_dir / "receipts").glob("*.json")):
        receipt = load_json(path)
        validate_schema(receipt, schema)
        receipts.append(receipt)
    if not receipts:
        return {"status": "unproven", "errors": ["no receipts"]}, EXIT_UNPROVEN
    invalid = [r["task_id"] for r in receipts if r["disposition"] != "candidate"]
    groups = {}
    for receipt in receipts:
        key = (receipt["runner"], receipt["requested_model"], receipt["task_class"])
        groups.setdefault(key, []).append(receipt)
    promotions = {}
    for key, items in groups.items():
        repeat_bonus = (
            {"trace": 10, "review": 10, "code_draft": 15}[key[2]]
            if len(items) == 3
            else 0
        )
        promoted = len(items) == 3 and all(
            item["disposition"] == "candidate" for item in items
        )
        promotions["/".join(key)] = {
            "runs": len(items),
            "repeatability_bonus": repeat_bonus,
            "promoted": promoted,
            "minimum_aggregate_score": min(
                (item["total_score"] + repeat_bonus for item in items), default=0
            ),
        }
    complete = len(receipts) == 27 and len(promotions) == 9
    passed = (
        complete
        and not invalid
        and all(value["promoted"] for value in promotions.values())
    )
    return {
        "status": "pass" if passed else "failed",
        "receipt_count": len(receipts),
        "matrix_complete": complete,
        "non_candidates": invalid,
        "promotions": promotions,
    }, EXIT_OK if passed else EXIT_FAILURE


def validate_af2_run(root: Path, run_dir: Path) -> tuple[dict, int]:
    schema = root / "config/free-model-eval/free-model-receipt.schema.json"
    receipts = []
    for path in sorted((run_dir / "receipts").glob("*.json")):
        value = load_json(path)
        validate_schema(value, schema)
        if value.get("protocol_version") != "1.1" or value.get("task_class") != "trace":
            raise EvalFailure("non-AF2 receipt in AF2 run")
        receipts.append(value)
    if not receipts:
        return {"status": "unproven", "errors": ["no AF2 receipts"]}, EXIT_UNPROVEN
    latest = {}
    for item in receipts:
        key = (item["runner"], item["requested_model"], item.get("repetition", 1))
        if key not in latest or item.get("attempt", 1) > latest[key].get("attempt", 1):
            latest[key] = item
    effective = list(latest.values())
    groups = {}
    for item in effective:
        groups.setdefault((item["runner"], item["requested_model"]), []).append(item)
    promotions = {}
    for key, items in groups.items():
        promoted = len(items) == 3 and all(
            x["disposition"] == "candidate" for x in items
        )
        promotions["/".join(key)] = {
            "runs": len(items),
            "promoted": promoted,
            "aggregate_score": min((x["total_score"] + 10 for x in items), default=0)
            if len(items) == 3
            else 0,
        }
    free_promoted = any(
        name.startswith("opencode/") and value["promoted"]
        for name, value in promotions.items()
    )
    control_promoted = promotions.get("codex/gpt-5.6-luna", {}).get("promoted", False)
    rejected = [x["task_id"] for x in effective if x["disposition"] == "rejected"]
    unproven = [x["task_id"] for x in effective if x["disposition"] == "unproven"]
    if free_promoted and control_promoted:
        status = "pass"
    elif free_promoted and not control_promoted:
        status = "unproven"
    else:
        status = "unproven" if unproven and not rejected else "failed"
    return {
        "status": status,
        "receipt_count": len(receipts),
        "effective_receipt_count": len(effective),
        "free_candidate_proven": free_promoted,
        "control_required": free_promoted,
        "control_promoted": control_promoted,
        "promotions": promotions,
        "rejected": rejected,
        "unproven": unproven,
    }, {"pass": EXIT_OK, "failed": EXIT_FAILURE, "unproven": EXIT_UNPROVEN}[status]
