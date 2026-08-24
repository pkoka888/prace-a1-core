from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator, Sequence

from jsonschema import Draft7Validator

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_UNPROVEN = 2
HASH_EMPTY = hashlib.sha256(b"").hexdigest()
HEX64 = re.compile(r"^[a-f0-9]{64}$")
FENCE = re.compile(r"^\s*```", re.MULTILINE)
MODEL_HEADER = re.compile(r"^(opencode/[^\s]+)$")


class EvalFailure(Exception):
    """Confirmed policy, contract, or evidence failure."""


class EvalUnproven(Exception):
    """Environmental or provider condition prevents a conclusion."""


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_ms: int = 0


Runner = Callable[..., subprocess.CompletedProcess[str]]


def resolve_opencode_binary(policy: dict) -> Path:
    if policy.get("opencode_binary") != "default-underlying-binary":
        raise EvalFailure("unsupported OpenCode binary selector")
    return Path.home() / ".opencode/bin/opencode"


def resolve_opencode_auth(policy: dict) -> Path:
    if policy.get("opencode_auth_source") != "default-user-auth-store":
        raise EvalFailure("unsupported OpenCode auth selector")
    return Path.home() / ".local/share/opencode/auth.json"


def resolve_codex_binary(policy: dict) -> Path:
    if policy.get("codex_binary") != "default-pinned-standalone":
        raise EvalFailure("unsupported Codex binary selector")
    version = policy.get("codex_required_version")
    if not version:
        raise EvalFailure("Codex required version missing")
    return Path.home() / ".codex/packages/standalone/releases" / f"{version}-x86_64-unknown-linux-musl/bin/codex"


def resolve_codex_auth(policy: dict, root: Path) -> Path:
    if policy.get("codex_auth_source") != "dedicated-revocable-codex-store":
        raise EvalFailure("unsupported Codex auth selector")
    store = policy.get("codex_auth_store")
    if not store or not safe_relative(store):
        raise EvalFailure("invalid Codex auth store path")
    expected_parent = root / "runtime/free-model-eval/credentials"
    candidate = root / store
    try:
        candidate.relative_to(expected_parent)
    except ValueError as exc:
        raise EvalFailure("Codex auth store must use the dedicated credential directory") from exc
    return candidate


def validate_codex_auth_source(source: Path) -> None:
    if source.is_symlink():
        raise EvalFailure("dedicated Codex auth store must not be a symlink")
    if not source.exists():
        raise EvalUnproven("dedicated Codex auth store unavailable")
    details = source.stat()
    if not stat.S_ISREG(details.st_mode):
        raise EvalFailure("dedicated Codex auth store must be a regular file")
    if details.st_uid != os.getuid():
        raise EvalFailure("dedicated Codex auth store must be owned by the current user")
    if details.st_mode & 0o077:
        raise EvalFailure("dedicated Codex auth store must use owner-only permissions")
    try:
        auth = load_json(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalUnproven("dedicated Codex auth store structure unavailable") from exc
    if not isinstance(auth, dict) or not isinstance(auth.get("tokens"), dict) or not auth["tokens"]:
        raise EvalUnproven("dedicated Codex auth store structure invalid")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvalFailure(f"JSON object required: {path}")
    return value


def validate_schema(instance: object, schema_path: Path) -> None:
    schema = load_json(schema_path)
    errors = sorted(Draft7Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        raise EvalFailure("; ".join(error.message for error in errors))


def safe_relative(path: str) -> bool:
    pure = PurePosixPath(path)
    return bool(path) and not pure.is_absolute() and ".." not in pure.parts


def validate_packet(packet: dict, schema_path: Path, policy: dict) -> None:
    validate_schema(packet, schema_path)
    forbidden = tuple(policy["forbidden_paths"])
    for field in ("allowed_paths", "forbidden_paths"):
        for item in packet[field]:
            if not safe_relative(item):
                raise EvalFailure(f"unsafe {field}: {item}")
    for item in packet["allowed_paths"]:
        if any(item == part or item.startswith(part + "/") for part in forbidden):
            raise EvalFailure(f"protected allowed path: {item}")
    if packet["runner"] == "opencode" and packet["model"] not in policy["free_models"]:
        raise EvalFailure("OpenCode model is not allowlisted")
    if packet["runner"] == "codex" and f"codex/{packet['model']}" != policy["codex_control"]:
        raise EvalFailure("Codex control model mismatch")
    if any(tool in policy["forbidden_tools"] for tool in packet["allowed_tools"]):
        raise EvalFailure("forbidden tool allowed by packet")


def tree_hash(root: Path, *, exclude: Sequence[str] = ()) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return HASH_EMPTY
    excluded = tuple(exclude)
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(item + "/") for item in excluded):
            continue
        if path.is_symlink():
            raise EvalFailure(f"symlink not allowed in hashed tree: {rel}")
        if path.is_file():
            digest.update(rel.encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def repository_snapshot(root: Path) -> str:
    commands = (
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        ["git", "-C", str(root), "diff", "--cached", "--binary"],
        ["git", "-C", str(root), "rev-parse", "HEAD"],
    )
    digest = hashlib.sha256()
    for command in commands:
        proc = subprocess.run(command, capture_output=True, check=False)
        if proc.returncode:
            raise EvalUnproven("repository snapshot command failed")
        digest.update(proc.stdout)
        digest.update(b"\0")
    return digest.hexdigest()


def parse_verbose_models(text: str) -> dict[str, dict]:
    models: dict[str, dict] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = MODEL_HEADER.match(lines[index].strip())
        if not match:
            index += 1
            continue
        model_id = match.group(1)
        index += 1
        while index < len(lines) and not lines[index].lstrip().startswith("{"):
            index += 1
        if index >= len(lines):
            raise EvalFailure(f"metadata missing for {model_id}")
        buf: list[str] = []
        depth = 0
        while index < len(lines):
            line = lines[index]
            depth += line.count("{") - line.count("}")
            buf.append(line)
            index += 1
            if depth == 0:
                break
        try:
            models[model_id] = json.loads("\n".join(buf))
        except json.JSONDecodeError as exc:
            raise EvalFailure(f"invalid metadata for {model_id}") from exc
    return models


def sanitized_preflight(models: dict[str, dict], policy: dict) -> dict:
    selected = {}
    for model_id in policy["free_models"]:
        meta = models.get(model_id)
        if not meta:
            raise EvalUnproven(f"model unavailable: {model_id}")
        cost = meta.get("cost", {})
        cache = cost.get("cache", {})
        if any(cost.get(k) != 0 for k in ("input", "output")) or any(cache.get(k) != 0 for k in ("read", "write")):
            raise EvalFailure(f"non-zero or ambiguous price: {model_id}")
        limit = meta.get("limit", {})
        if limit.get("context", 0) < policy["minimum_context"] or limit.get("output", 0) < policy["minimum_output"]:
            raise EvalFailure(f"insufficient limits: {model_id}")
        if meta.get("status") != "active" or not meta.get("capabilities", {}).get("toolcall"):
            raise EvalFailure(f"inactive or incapable model: {model_id}")
        selected[model_id] = {
            "id": meta.get("id"), "providerID": meta.get("providerID"),
            "status": meta.get("status"), "cost": cost, "limit": limit,
            "toolcall": True, "release_date": meta.get("release_date"),
        }
    return {"schema_version": "1.0", "captured_at": utc_now(), "models": selected,
            "metadata_hash": sha256_bytes(canonical_bytes(selected))}


def run_command(command: Sequence[str], *, cwd: Path | None = None,
                env: dict[str, str] | None = None, timeout: int = 60,
                runner: Runner = subprocess.run) -> CommandResult:
    started = time.monotonic()
    try:
        proc = runner(list(command), cwd=cwd, env=env, text=True, capture_output=True,
                      timeout=timeout, check=False)
        return CommandResult(proc.returncode, proc.stdout, proc.stderr, False,
                             int((time.monotonic() - started) * 1000))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""; stderr = exc.stderr or ""
        if isinstance(stdout, bytes): stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes): stderr = stderr.decode("utf-8", "replace")
        return CommandResult(124, stdout, stderr, True,
                             int((time.monotonic() - started) * 1000))


def parse_jsonl_events(text: str, allowed_types: set[str]) -> list[dict]:
    events = []
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvalFailure(f"malformed JSONL event {number}") from exc
        if not isinstance(event, dict):
            raise EvalFailure(f"JSONL event {number} must be an object")
        event_type = event.get("type")
        if event_type not in allowed_types:
            raise EvalFailure(f"unexpected event type: {event_type}")
        part = event.get("part", {})
        if part is None or not isinstance(part, dict):
            raise EvalFailure(f"event part must be an object: {event_type}")
        events.append(event)
    return events


def parse_events(text: str, policy: dict, packet: dict, *, max_output_bytes: int | None = None) -> tuple[dict, list[dict], dict, float | None]:
    final_texts: list[str] = []
    tools: list[dict] = []
    tokens: dict = {}
    cost: float | None = None
    allowed_types = set(policy["allowed_event_types"])
    for event in parse_jsonl_events(text, allowed_types):
        event_type = event.get("type")
        part = event["part"]
        if event_type == "text":
            final_texts.append(part.get("text", ""))
        elif event_type == "tool_use":
            tool = part.get("tool")
            state = part.get("state") or {}
            if not isinstance(state, dict) or not isinstance(state.get("input") or {}, dict):
                raise EvalFailure(f"invalid tool state: {tool}")
            item = {"tool": tool, "input": state.get("input") or {}, "status": state.get("status")}
            if tool not in packet["allowed_tools"]:
                raise EvalFailure(f"unauthorized tool: {tool}")
            if item["status"] != "completed":
                raise EvalFailure(f"tool did not complete: {tool}")
            payload = json.dumps(item["input"], ensure_ascii=False)
            for forbidden in policy["forbidden_paths"]:
                if forbidden in payload:
                    raise EvalFailure(f"forbidden path in tool event: {forbidden}")
            if tool == "read":
                if set(item["input"]) - {"filePath","path","offset","limit"}:
                    raise EvalFailure("read event contains unexpected input fields")
                value = item["input"].get("filePath") or item["input"].get("path")
                if not value:
                    raise EvalFailure("read event missing path")
                prefix = "/workspace/"
                relative = value[len(prefix):] if value.startswith(prefix) else value
                if relative not in packet["allowed_paths"]:
                    raise EvalFailure(f"read path not allowlisted: {relative}")
            tools.append(item)
        elif event_type == "step_finish":
            observed = part.get("tokens") or {}
            if observed:
                tokens = observed
            if part.get("cost") is not None:
                cost = float(part["cost"])
        elif event_type == "error":
            status = part.get("status") or part.get("statusCode")
            message = str(part.get("message") or "provider error")
            if status in policy["retryable_statuses"]:
                raise EvalUnproven(f"retryable provider error {status}")
            raise EvalFailure(f"provider error: {message[:160]}")
    if len(final_texts) != 1:
        raise EvalFailure(f"exactly one final text required, got {len(final_texts)}")
    final = final_texts[0]
    limit = max_output_bytes if max_output_bytes is not None else policy["max_final_output_bytes"]
    if len(final.encode("utf-8")) > limit:
        raise EvalFailure("final output too large")
    if FENCE.search(final):
        raise EvalFailure("Markdown-wrapped JSON is forbidden")
    output, _, _ = normalized_json_output(final)
    return output, tools, tokens, cost


def final_text_from_events(text: str, policy: dict) -> str:
    finals = [event["part"].get("text", "") for event in
              parse_jsonl_events(text, set(policy["allowed_event_types"]))
              if event["type"] == "text"]
    if len(finals) != 1:
        raise EvalFailure(f"exactly one final text required, got {len(finals)}")
    return finals[0]


def normalized_json_output(text: str) -> tuple[dict, str, str]:
    """Apply only AF2's harmless transport normalizations."""
    original = text.encode("utf-8")
    value = text[1:] if text.startswith("\ufeff") else text
    value = unicodedata.normalize("NFC", value)
    if FENCE.search(value):
        raise EvalFailure("Markdown-wrapped JSON is forbidden")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise EvalFailure("final output is not JSON") from exc
    if not isinstance(parsed, dict):
        raise EvalFailure("final output must be a JSON object")
    def normalize(value):
        if isinstance(value, str): return unicodedata.normalize("NFC", value)
        if isinstance(value, list): return [normalize(item) for item in value]
        if isinstance(value, dict): return {unicodedata.normalize("NFC", key): normalize(item) for key,item in value.items()}
        return value
    parsed = normalize(parsed)
    return parsed, sha256_bytes(original), sha256_bytes(canonical_bytes(parsed))


def sanitize_event_stream(text: str, policy: dict) -> tuple[bytes, str]:
    """Produce diagnostic JSONL without prompts, reasoning, credentials, or unknown fields."""
    sanitized = []
    secret_key = re.compile(r"(?i)^(api[_-]?key|authorization|token|secret|password)$")
    secret_value = re.compile(r"(?i)(\bbearer\s+[a-z0-9._~+/-]{8,}|\bsk-[a-z0-9_-]{8,})")
    hidden = {"reasoning", "thinking", "prompt", "system", "instructions"}
    def credential_rule(value: object) -> str | None:
        if isinstance(value, dict):
            for key, item in value.items():
                if secret_key.fullmatch(str(key)):
                    return "secret-key-name"
                found = credential_rule(item)
                if found: return found
            return None
        if isinstance(value, list):
            return next((found for item in value if (found := credential_rule(item))), None)
        if isinstance(value, str):
            if secret_value.search(value): return "secret-value-shape"
            try: return credential_rule(json.loads(value))
            except (json.JSONDecodeError, TypeError): return None
        return None
    def contains_hidden(value: object) -> bool:
        if isinstance(value, dict):
            return bool(hidden.intersection(value)) or any(contains_hidden(item) for item in value.values())
        if isinstance(value, list): return any(contains_hidden(item) for item in value)
        return False
    for event in parse_jsonl_events(text, set(policy["allowed_event_types"])):
        if hidden.intersection(event):
            raise EvalFailure("hidden or prompt field in event")
        part = event["part"]
        if hidden.intersection(part):
            raise EvalFailure("hidden or prompt field in event part")
        kind = event["type"]
        if kind == "tool_use":
            state = part.get("state") or {}
            if not isinstance(state, dict) or not isinstance(state.get("input") or {}, dict):
                raise EvalFailure("invalid tool state in diagnostic event")
            clean = {"type": kind, "part": {"tool": part.get("tool"), "state": {
                "status": state.get("status"), "input": state.get("input") or {}}}}
        elif kind == "text":
            clean = {"type": kind, "part": {"text": part.get("text", "")}}
        elif kind == "step_finish":
            clean = {"type": kind, "part": {"tokens": part.get("tokens") or {}, "cost": part.get("cost")}}
        elif kind == "error":
            clean = {"type": kind, "part": {"status": part.get("status") or part.get("statusCode"),
                                               "message": str(part.get("message") or "")[:160]}}
        elif kind == "step_start":
            clean = {"type": kind, "part": {}}
        else:
            raise EvalFailure(f"unexpected event type: {kind}")
        untrusted = clean["part"].get("text") if kind == "text" else clean["part"].get("state", {}).get("input") if kind == "tool_use" else clean["part"].get("message") if kind == "error" else None
        if contains_hidden(untrusted):
            raise EvalFailure("hidden or prompt field in diagnostic payload")
        if rule := credential_rule(untrusted):
            raise EvalFailure(f"credential-shaped content in diagnostic event [{rule}]")
        rendered = json.dumps(clean, ensure_ascii=False, sort_keys=True)
        sanitized.append(rendered)
    payload = (("\n".join(sanitized) + "\n") if sanitized else "").encode("utf-8")
    return payload, sha256_bytes(payload)


def validate_contract_echo(output: dict, packet: dict, schema_path: Path) -> None:
    validate_schema(output, schema_path)
    expected = {
        "schema_version": "1.0", "task_id": packet["task_id"],
        "allowed_paths": packet["allowed_paths"],
        "output_schema_version": packet["output_schema_version"],
        "forbidden_actions_acknowledged": True,
    }
    if output != expected:
        raise EvalFailure("contract echo mismatch")


def validate_citations_af2(output: dict, workspace: Path, expected: dict,
                           tools: Sequence[dict]) -> tuple[bool, dict[str, float], list[str], list[str]]:
    errors, codes = [], []
    claims = output.get("claims", [])
    required = {item["fact"]: item for item in expected["required_facts"]}
    seen, valid = set(), 0
    fact_counts: dict[str, int] = {}
    for claim in claims:
        fact = claim.get("fact")
        fact_counts[fact] = fact_counts.get(fact, 0) + 1
        if fact not in required:
            errors.append(f"unsupported fact: {fact}"); codes.append("unsupported_fact"); continue
        path, line, quote = claim.get("path"), claim.get("line"), claim.get("quote")
        if not isinstance(path, str) or not safe_relative(path) or path not in expected["required_reads"]:
            errors.append(f"invalid relative citation path: {path}"); codes.append("invalid_citation_path"); continue
        target = workspace / path
        lines = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
        if not isinstance(line, int):
            errors.append(f"invalid line type: {fact}"); codes.append("invalid_line_type"); continue
        if line < 1 or line > len(lines):
            errors.append(f"invalid line: {path}:{line}"); codes.append("invalid_line"); continue
        if not isinstance(quote, str) or quote not in lines[line - 1]:
            errors.append(f"invalid quotation: {path}:{line}"); codes.append("invalid_quotation"); continue
        item = required[fact]
        if path != item["path"] or item["quote"] not in lines[line - 1]:
            errors.append(f"citation does not prove fact: {fact}"); codes.append("unsupported_citation"); continue
        seen.add(fact); valid += 1
    duplicates = sorted(k for k, count in fact_counts.items() if count > 1)
    if duplicates:
        errors.append("duplicate facts: " + ",".join(duplicates)); codes.append("duplicate_fact")
    missing = set(required) - seen
    if missing:
        errors.append("missing facts: " + ",".join(sorted(missing))); codes.append("missing_fact")
    reads = tool_paths(tools)
    missing_reads = set(expected["required_reads"]) - reads
    if missing_reads:
        errors.append("missing explicit reads: " + ",".join(sorted(missing_reads))); codes.append("missing_read")
    total = max(1, len(required))
    scores = {"factual_accuracy": 30 * len(seen) / total,
              "citation_validity": 30 * valid / total,
              "required_read_evidence": 15 if not missing_reads else 0}
    return not errors, scores, errors, sorted(set(codes))


def tool_paths(tools: Sequence[dict], tool_name: str = "read") -> set[str]:
    paths = set()
    for item in tools:
        if item["tool"] != tool_name:
            continue
        value = item.get("input", {}).get("filePath") or item.get("input", {}).get("path")
        if value:
            paths.add(PurePosixPath(value).name if value.startswith("/") else value)
    return paths


def validate_citations(output: dict, workspace: Path, expected: dict,
                       tools: Sequence[dict]) -> tuple[bool, dict[str, float], list[str]]:
    errors = []
    claims = output.get("claims", [])
    required = {item["fact"]: item for item in expected["required_facts"]}
    seen = set()
    valid = 0
    for claim in claims:
        fact, path, line, quote = (claim.get("fact"), claim.get("path"), claim.get("line"), claim.get("quote"))
        if fact not in required or not isinstance(line, int) or not safe_relative(path or ""):
            errors.append(f"unsupported or malformed claim: {fact}")
            continue
        target = workspace / path
        if not target.is_file():
            errors.append(f"missing citation path: {path}")
            continue
        lines = target.read_text(encoding="utf-8").splitlines()
        if line < 1 or line > len(lines) or quote not in lines[line - 1]:
            errors.append(f"invalid citation: {path}:{line}")
            continue
        expected_item = required[fact]
        if path != expected_item["path"] or expected_item["quote"] not in lines[line - 1]:
            errors.append(f"citation does not prove fact: {fact}")
            continue
        seen.add(fact); valid += 1
    missing = set(required) - seen
    if missing:
        errors.append("missing facts: " + ",".join(sorted(missing)))
    reads = tool_paths(tools)
    missing_reads = set(expected["required_reads"]) - reads
    if missing_reads:
        errors.append("missing explicit reads: " + ",".join(sorted(missing_reads)))
    total = max(1, len(required))
    return not errors, {"factual_accuracy": 30 * len(seen) / total,
                        "citation_validity": 30 * valid / total,
                        "required_read_evidence": 15 if not missing_reads else 0}, errors


def score_review(output: dict, expected: dict) -> tuple[dict[str, float], list[str]]:
    ids = [item.get("id") for item in output.get("findings", [])]
    required = set(expected["required_findings"])
    found = required.intersection(ids)
    false = [item for item in ids if item not in required]
    errors = []
    if found != required:
        errors.append("required findings missing")
    if len(false) > expected["max_false_positives"]:
        errors.append("too many false positives")
    evidence = sum(bool(item.get("evidence") and item.get("repair")) for item in output.get("findings", []))
    count = max(1, len(output.get("findings", [])))
    precision = len(found) / max(1, len(ids))
    return {"required_defect_recall": 30 * len(found) / len(required),
            "finding_precision": 30 * precision, "evidence_quality": 20 * evidence / count}, errors


def score_total(task_class: str, scores: dict[str, float], *, schema_ok: bool,
                tool_ok: bool, acceptance: bool, scope_ok: bool, repeatability: float = 0) -> float:
    value = sum(scores.values())
    if task_class == "trace": value += 15 if schema_ok and tool_ok else 0
    elif task_class == "review": value += 10 if schema_ok and tool_ok else 0
    else: value += (45 if acceptance else 0) + (20 if scope_ok else 0) + (10 if schema_ok else 0) + (10 if tool_ok else 0)
    return min(100.0, value + repeatability)


def safe_cleanup(path: Path, runtime_runs: Path) -> None:
    resolved = path.resolve()
    parent = runtime_runs.resolve()
    if resolved.parent != parent or not resolved.name:
        raise EvalFailure("cleanup target is not an exact run child")
    if resolved.exists():
        shutil.rmtree(resolved)


@contextmanager
def credential_home(policy: dict, runtime: Path) -> Iterator[Path]:
    source = resolve_opencode_auth(policy)
    if not source.is_file():
        raise EvalUnproven("OpenCode auth file unavailable")
    auth = load_json(source)
    provider = policy["opencode_auth_provider"]
    if provider not in auth:
        raise EvalUnproven("free-models credential unavailable")
    home = Path(tempfile.mkdtemp(prefix="credential-", dir=runtime))
    target = home / ".local/share/opencode/auth.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({provider: auth[provider]}), encoding="utf-8")
    target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    try:
        yield home
    finally:
        shutil.rmtree(home)


def codex_credential_home(policy: dict, root: Path, runtime: Path) -> Iterator[Path]:
    source = resolve_codex_auth(policy, root)
    validate_codex_auth_source(source)

    @contextmanager
    def isolated_home() -> Iterator[Path]:
        home = Path(tempfile.mkdtemp(prefix="codex-credential-", dir=runtime))
        target = home / "auth.json"
        shutil.copy2(source, target)
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
        try:
            yield home
        finally:
            shutil.rmtree(home)

    return isolated_home()


def bwrap_command(binary: Path, workspace: Path, home: Path, agent: str,
                  model: str, prompt: str) -> list[str]:
    command = ["bwrap", "--die-with-parent", "--unshare-user", "--unshare-pid",
               "--unshare-uts", "--unshare-ipc", "--ro-bind", "/usr", "/usr",
               "--ro-bind", "/bin", "/bin", "--ro-bind", "/lib", "/lib",
               "--ro-bind", "/lib64", "/lib64", "--ro-bind", "/etc", "/etc",
               "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
               "--bind", str(workspace), "/workspace", "--bind", str(home), "/home/worker",
               "--ro-bind", str(home / ".local/share/opencode/auth.json"), "/home/worker/.local/share/opencode/auth.json",
               "--ro-bind", str(binary), "/opencode", "--chdir", "/workspace",
               "--setenv", "HOME", "/home/worker", "--setenv", "PATH", "/usr/bin:/bin",
               "/opencode", "run", "--pure", "--agent", agent,
               "--model", model, "--format", "json", prompt]
    return command


def codex_capsule_mounts(workspace: Path, home: Path, binary: Path) -> list[str]:
    return ["--die-with-parent", "--unshare-user", "--unshare-pid", "--unshare-uts",
            "--unshare-ipc", "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/etc", "/etc", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--ro-bind", str(workspace), "/workspace",
            "--bind", str(home), "/home/codex", "--ro-bind", str(binary), "/codex",
            "--chdir", "/workspace", "--setenv", "HOME", "/home/codex",
            "--setenv", "CODEX_HOME", "/home/codex", "--setenv", "PATH", "/usr/bin:/bin"]


def codex_bwrap_command(binary: Path, workspace: Path, home: Path, model: str,
                        reasoning_effort: str, prompt: str) -> list[str]:
    return (["bwrap", *codex_capsule_mounts(workspace, home, binary), "/codex",
             "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
             "--json", "--color", "never", "-m", model,
             "-c", f'model_reasoning_effort="{reasoning_effort}"',
             "-s", "read-only", "--output-schema", "/workspace/.output.schema.json",
             "-C", "/workspace", prompt])


def copy_fixture(root: Path, task: str, destination: Path, agent_path: Path) -> None:
    source = root / "tests/fixtures/free_model_eval" / task
    shutil.copytree(source, destination, dirs_exist_ok=True)
    target = destination / ".opencode/agents"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(agent_path, target / agent_path.name)


def task_prompt(task: str) -> str:
    common = "This is public synthetic evaluation data. Use only /workspace. Return one raw JSON object without Markdown fences. "
    if task == "trace":
        return common + "Read README.md and AGENTS.md explicitly. Return {\"claims\":[{\"fact\": one of planning-only, portal-not-implemented, synthetic-only, \"path\": path, \"line\": integer, \"quote\": exact substring}]}."
    if task == "review":
        return common + "Read change.diff. Identify only real defects. Return {\"findings\":[{\"id\": stable defect id, \"severity\": low|medium|high, \"evidence\": exact diff evidence, \"repair\": correction}]} with ids off-by-one and unsafe-path-prefix when supported."
    return common + "Read solution/slugify.py and tests/test_slugify.py. Edit only solution/slugify.py so tests should pass. Return {\"changed_paths\":[\"solution/slugify.py\"],\"summary\":\"...\"}. Do not run commands or edit tests."


def packet_for(root: Path, task: str, runner_name: str, model: str, policy: dict) -> dict:
    allowed = {"trace": ["README.md", "AGENTS.md"], "review": ["change.diff"],
               "code_draft": ["solution/slugify.py", "tests/test_slugify.py"]}[task]
    tools = ["read"] if task != "code_draft" else ["read", "edit", "write", "apply_patch"]
    schema = {"trace": "trace-output.schema.json", "review": "review-output.schema.json",
              "code_draft": "code-output.schema.json"}[task]
    model_slug = re.sub(r"[^a-z0-9_-]+", "-", model.lower()).strip("-")
    manifest = [{"path": item, "sha256": sha256_bytes((root / "tests/fixtures/free_model_eval" / task / item).read_bytes())} for item in allowed]
    return {"schema_version": "1.0", "protocol_version": policy.get("protocol_version", "1.0"),
            "contract_echo_required": bool(policy.get("af2_trace_only", False)),
            "task_id": f"{task}-{runner_name}-{model_slug}",
            "task_class": task, "runner": runner_name, "model": model,
            "reasoning_variant": policy["codex_reasoning_effort"] if runner_name == "codex" else None,
            "prompt_template": task_prompt(task), "allowed_paths": allowed, "file_manifest": manifest,
            "forbidden_paths": policy["forbidden_paths"], "allowed_tools": tools,
            "allowed_commands": [], "required_output_schema": schema, "output_schema_version": "1.0",
            "timeout_seconds": 90, "max_steps": 12, "privacy_class": "public-synthetic",
            "expected_evidence": load_json(root / "tests/fixtures/free_model_eval" / task / "expected.json"),
            "acceptance_command": ["venv/bin/python", "-m", "pytest", "tests/test_slugify.py", "-q"] if task == "code_draft" else [],
            "rollback": "Delete only the exact generated run workspace after containment validation."}
