#!/usr/bin/env python3
"""Audit active project agent/config directories without reading private data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "cli-docs-update" / "current-agent-dir-audit.json"
DEFAULT_MARKDOWN = ROOT / "cli-docs-update" / "current-agent-dir-audit.md"
ACTIVE_DIRS = [
    ".agents",
    ".opencode",
    ".kilo",
    ".cline",
    ".codex",
    ".claude",
    ".clinerules",
    ".kilocode",
]
SENSITIVE_EXCLUDED = [
    ".history-remediation",
    "a1",
    "scans",
    "evidence",
    "ocr",
    "data",
    "output",
]
LINK_RE = re.compile(r"\[[^]]+\]\(([^)]+)\)")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def run(args: list[str], timeout: float = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def clean(value: str) -> str:
    return (
        ANSI_RE.sub("", value)
        .replace(str(ROOT), "<repo>")
        .replace(str(Path.home()), "~")
        .strip()
    )


def git_tracked(path: Path) -> bool:
    relative = str(path.relative_to(ROOT))
    return run(["git", "ls-files", "--error-unmatch", relative], 5).returncode == 0


def parse_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, ["missing YAML frontmatter"]
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError:
        return {}, ["unterminated YAML frontmatter"]
    data: dict[str, str] = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # An indented line with no key of its own is a continuation of the
        # previous value (e.g. a block scalar); it is not a new entry.
        if line[:1].isspace():
            errors.append(f"unsupported frontmatter line: {line}")
            continue
        if ":" not in line:
            errors.append(f"unsupported frontmatter line: {line}")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        # YAML block scalars (`>` folded, `|` literal) carry their value on the
        # following more-indented lines; consume them instead of misparsing each
        # continuation line as its own frontmatter entry.
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            block: list[str] = []
            while index < len(lines):
                following = lines[index]
                if following.strip() and not following[:1].isspace():
                    break
                block.append(following.strip())
                index += 1
            value = " ".join(part for part in block if part).strip()
        # An empty value followed by indented `- item` lines is a YAML list
        # (e.g. `triggers:` / `allowed-tools:`); the items are part of this
        # key's value, not new frontmatter entries.
        elif not value and index < len(lines) and lines[index][:1].isspace():
            items: list[str] = []
            while index < len(lines):
                following = lines[index]
                if not following.strip():
                    index += 1
                    continue
                if not following[:1].isspace():
                    break
                if following.lstrip().startswith("- "):
                    items.append(following.lstrip()[2:].strip())
                    index += 1
                else:
                    break
            if items:
                value = ", ".join(items)
        data[key] = value.strip("\"'")
    return data, errors


def audit_skill(path: Path) -> dict[str, Any]:
    metadata, errors = parse_frontmatter(path)
    folder = path.parent.name
    for required in ("name", "description"):
        if not metadata.get(required):
            errors.append(f"missing required {required}")
    if metadata.get("name") and metadata["name"] != folder:
        errors.append(f"name {metadata['name']!r} does not match folder {folder!r}")
    links = []
    for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        # A "#fragment" names an anchor inside the target file, not a file name.
        fragment = ""
        path_part = target
        if "#" in target:
            path_part, fragment = target.split("#", 1)
            fragment = f"#{fragment}"
        resolved = (path.parent / path_part).resolve()
        exists = resolved.exists()
        links.append({"target": target, "exists": exists})
        if not exists:
            errors.append(f"broken relative link: {target}")
    provider_metadata = []
    agents_dir = path.parent / "agents"
    if agents_dir.is_dir():
        for metadata_path in sorted(agents_dir.glob("*.yaml")):
            metadata_text = metadata_path.read_text(encoding="utf-8")
            metadata_errors = []
            for expected in (
                "interface:",
                "display_name:",
                "short_description:",
                "default_prompt:",
            ):
                if expected not in metadata_text:
                    metadata_errors.append(f"missing {expected.rstrip(':')}")
            provider_metadata.append(
                {
                    "path": str(metadata_path.relative_to(ROOT)),
                    "valid_shallow_contract": not metadata_errors,
                    "errors": metadata_errors,
                }
            )
            errors.extend(f"{metadata_path.name}: {error}" for error in metadata_errors)
    return {
        "path": str(path.relative_to(ROOT)),
        "name": metadata.get("name"),
        "description_present": bool(metadata.get("description")),
        "tracked": git_tracked(path),
        "relative_links": links,
        "provider_metadata": provider_metadata,
        "valid": not errors,
        "errors": errors,
    }


def parse_version(text: str) -> str | None:
    match = re.search(r"\d+\.\d+\.\d+", text)
    return match.group(0) if match else None


def installed_version(binary: str) -> str | None:
    executable = shutil.which(binary)
    if not executable:
        return None
    result = run([executable, "--version"])
    return parse_version(result.stdout + result.stderr)


def package_dependency(path: Path, expected: str) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    dependencies = data.get("dependencies", {})
    if expected not in dependencies:
        return None, None
    return expected, str(dependencies[expected])


def active_probe(binary: str, args: list[str]) -> dict[str, Any]:
    executable = shutil.which(binary)
    if not executable:
        return {"available": False, "exit_code": None, "diagnostic": "binary missing"}
    result = run([executable, *args])
    diagnostic = clean(result.stderr or result.stdout)
    return {
        "available": True,
        "exit_code": result.returncode,
        "diagnostic": diagnostic[:600] + ("…" if len(diagnostic) > 600 else ""),
    }


def discovered_opencode_skills() -> dict[str, Any]:
    executable = shutil.which("opencode")
    if not executable:
        return {"status": "binary_missing", "skills": []}
    result = run([executable, "debug", "skill"], 20)
    if result.returncode != 0:
        return {
            "status": "failed",
            "skills": [],
            "diagnostic": clean(result.stderr)[:400],
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "invalid_json", "skills": []}
    skills = []
    for item in payload:
        location = clean(str(item.get("location", "")))
        if location == "<built-in>" or location.startswith("<repo>/"):
            skills.append({"name": item.get("name"), "location": location})
    return {"status": "succeeded", "skills": skills}


# Per-CLI MCP config locations. Each entry maps a CLI to the config files that
# declare its MCP servers, so drift (stale paths, disabled servers, malformed
# args, duplicated entries) can be detected without reading private data.
#
# Kilo has two products with separate config schemas and no shared file:
#   * kilo CLI  -> ~/.config/kilo/kilo.json  (schema: {"mcp": {...}})
#   * kilo-code VS Code extension -> <workspace>/.kilo/mcp.json (schema: {"mcpServers": {...}})
# They are independent; a fix in one does not affect the other.
CLI_MCP_CONFIGS: dict[str, list[str]] = {
    "opencode": [
        str(Path.home() / ".config" / "opencode" / "opencode.jsonc"),
        str(Path.home() / ".opencode" / "mcp.json"),
    ],
    "kilo_cli": [
        str(Path.home() / ".config" / "kilo" / "kilo.json"),
        str(Path.home() / ".config" / "kilo" / "kilo.jsonc"),
    ],
    "kilo_code_extension": [
        str(ROOT / ".kilo" / "mcp.json"),
    ],
    "cline": [
        str(Path.home() / ".cline" / "data" / "settings" / "cline_mcp_settings.json"),
    ],
    "pi": [
        str(Path.home() / ".pi" / "agent" / "models-store.json"),
        str(Path.home() / ".pi" / "agent" / "settings.json"),
    ],
    "codex": [
        str(Path.home() / ".codex" / "config.toml"),
    ],
    "claude": [
        str(Path.home() / ".claude" / "settings.json"),
    ],
}

STALE_PATH_MARKERS = (
    "/workspace/servers-infra-core",
    "/workspace/",
    "/home/user/",
    "/tmp/repo",
)

# Global model selection is hardcoded in user-level CLI configs. These are the
# project's sanctioned model identifiers; a value seen here but not below is a
# deliberate user preference and is reported at info, never as drift. Do not
# treat a personal CLI model choice as a repository defect.
EXPECTED_MODEL_IDS: dict[str, tuple[str, ...]] = {
    "opencode": ("opencode/big-pickle",),
    "kilo_cli": (
        "kilo/poolside/laguna-xs-2.1:free",
        "kilo/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "kilo/auto",
        "kilo/Auto Free",
    ),
    "pi": (
        "MiniMax-M2.7",
        "minimax/MiniMax-M2.7",
    ),
    "cline": (
        "MiniMax-M2.7",
        "minimax/MiniMax-M2.7",
    ),
}

# Model keys that pin a default/small model in a user-level CLI config. Agent
# role overrides (e.g. kilo `agent.<role>.model`) also select models but are
# intentionally excluded from this probe to keep it deterministic.
GLOBAL_MODEL_KEYS = ("defaultModel", "default_model", "model", "small_model")

# Provider configuration blocks that may embed a model id in `models.<id>`.
PROVIDER_BLOCK_KEYS = ("provider", "providers")

# MCP/config files that must reference secrets via `{env:VAR}` placeholders,
# never inline values. `check.sh` must grep every one of these for inline
# secret patterns; a gap is reported so the scan cannot silently skip a file.
CLI_MCP_CONFIG_PATHS: dict[str, tuple[str, ...]] = {
    "opencode": (str(Path.home() / ".config" / "opencode" / "opencode.jsonc"),),
    "kilo_cli": (
        str(Path.home() / ".config" / "kilo" / "kilo.json"),
        str(Path.home() / ".config" / "kilo" / "kilo.jsonc"),
    ),
    "kilo_code": (str(ROOT / ".kilo" / "mcp.json"),),
    "opencode_legacy": (str(Path.home() / ".opencode" / "mcp.json"),),
    "kilo_legacy": (str(Path.home() / ".kilo" / "mcp.json"),),
    "cline": (
        str(Path.home() / ".cline" / "data" / "settings" / "cline_mcp_settings.json"),
    ),
    "pi": (str(Path.home() / ".pi" / "agent" / "settings.json"),),
}

# Dedicated credential stores under each provider directory. These hold real
# keys by design and are NOT scanned for inline-secret patterns (doing so can
# only false-positive on the operator's own keyring); they are reported only as
# an existence/permission inventory.
CLI_CREDENTIAL_STORE_PATHS: dict[str, tuple[str, ...]] = {
    "opencode": (
        str(Path.home() / ".config" / "opencode" / "env"),
        str(Path.home() / ".local" / "share" / "opencode" / "auth.json"),
    ),
    "kilo_cli": (),
    "cline": (
        str(Path.home() / ".cline" / "data" / "secrets.json"),
        str(Path.home() / ".cline" / "data" / "settings" / "providers.json"),
    ),
    "pi": (str(Path.home() / ".pi" / "agent" / "auth.json"),),
}

# Model id prefix that declares a paid endpoint. AGENTS.md forbids paid
# fallback; a paid id in a *tracked* project config is a high-severity
# policy conflict, while the same id in a user-level config is only info.
PAID_MODEL_MARKERS = ("minimax/minimax-m3", "minimax/minimax-01", "minimax-01")

# A provider block entry whose key ends in `:free` is explicitly free; its
# absence on a kilo-style id (`provider/model`) is reported at info, never
# treated as drift, because kilo's own router (`kilo/auto`) is free.
KILO_FREE_SUFFIX = ":free"

# Kilo emits a one-time TUI migration prompt when the well-known opencode
# config directory is present; the repository keeps `.opencode/` for the
# opencode CLI, so the notice is expected here and is informational only.
KILO_MIGRATION_NOTICE_ENV = "OPENCODE_NOTIFICATION_ID"


# `${env:VAR}` is invalid inside `command`/`args` arrays (verified 2026-10-20
# with isolated probes against opencode 1.18.32 and kilo 7.7.9): the inner
# `{env:VAR}` substring is substituted, but the leading `$` remains
# (`${env:ROOT_DIR}` -> `$/var/www/...`), so the invocation starts with `$`
# and the server fails to start. The single-brace `{env:VAR}` form IS
# substituted in `command`/`args` by both CLIs and is not flagged here.
# Interpolation inside `environment` values was not re-verified in this pass.
ENV_INTERPOLATION_RE = re.compile(r"\$\{env:[A-Z_][A-Z0-9_]*\}")


def strip_jsonc(text: str) -> str:
    """Remove // comments and trailing commas so JSONC can be parsed as JSON."""
    lines: list[str] = []
    for line in text.splitlines():
        in_string = False
        out: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"' and (i == 0 or line[i - 1] != "\\"):
                in_string = not in_string
                out.append(ch)
            elif (
                not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/"
            ):
                break
            else:
                out.append(ch)
            i += 1
        lines.append("".join(out))
    cleaned = "\n".join(lines)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    return cleaned


def parse_config_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"unreadable: {exc}"
    if path.suffix == ".jsonc" or path.name == "kilo.jsonc":
        try:
            return json.loads(strip_jsonc(text)), None
        except json.JSONDecodeError as exc:
            return None, f"invalid jsonc: {exc}"
    if path.suffix == ".toml":
        try:
            import tomllib
        except ModuleNotFoundError:
            return None, "toml parsing unavailable"
        try:
            return tomllib.loads(text), None
        except tomllib.TOMLDecodeError as exc:
            return None, f"invalid toml: {exc}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"invalid json: {exc}"


def audit_cli_mcp(cli: str, config_paths: list[str]) -> dict[str, Any]:
    """Validate each CLI's MCP configuration for drift."""
    entry: dict[str, Any] = {"cli": cli, "configs": []}
    for raw in config_paths:
        path = Path(raw).expanduser()
        data, error = parse_config_file(path)
        servers: dict[str, Any] = {}
        if data is not None:
            servers = data.get("mcpServers") or data.get("mcp") or {}
            if not isinstance(servers, dict):
                servers = {}
        stale_markers: list[str] = []
        disabled: list[str] = []
        malformed_args: list[str] = []
        uninterpolated_env: list[str] = []
        for name, server in servers.items():
            if not isinstance(server, dict):
                continue
            blob = json.dumps(server)
            for marker in STALE_PATH_MARKERS:
                if marker in blob:
                    stale_markers.append(f"{name}:{marker}")
            if server.get("disabled") is True:
                disabled.append(name)
            args = server.get("args")
            if isinstance(args, list):
                for arg in args:
                    if (
                        isinstance(arg, str)
                        and arg.startswith('["')
                        and arg.endswith('"]')
                    ):
                        malformed_args.append(f"{name}:literal-bracket-string-arg")
                    if ENV_INTERPOLATION_RE.search(arg):
                        uninterpolated_env.append(f"{name}:{arg}")
            command = server.get("command")
            if isinstance(command, list):
                for piece in command:
                    if isinstance(piece, str) and ENV_INTERPOLATION_RE.search(piece):
                        uninterpolated_env.append(f"{name}:{piece}")
        entry["configs"].append(
            {
                "path": clean(raw),
                "exists": path.exists(),
                "parse_error": error,
                "server_count": len(servers),
                "stale_markers": stale_markers,
                "disabled": disabled,
                "malformed_args": malformed_args,
                "uninterpolated_env": uninterpolated_env,
            }
        )
    return entry


def _iter_model_ids(data: dict[str, Any]) -> list[str]:
    """Collect model ids from a parsed CLI config without reading credentials."""
    ids: list[str] = []
    for key in GLOBAL_MODEL_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            ids.append(value.strip())

    def _walk_agent(node: Any) -> None:
        if not isinstance(node, dict):
            return
        for value in node.values():
            if isinstance(value, dict):
                model = value.get("model")
                if isinstance(model, str) and model.strip():
                    ids.append(model.strip())
                _walk_agent(value)

    _walk_agent(data.get("agent"))

    for block_key in PROVIDER_BLOCK_KEYS:
        block = data.get(block_key)
        if not isinstance(block, dict):
            continue
        for provider in block.values():
            if not isinstance(provider, dict):
                continue
            models = provider.get("models")
            if not isinstance(models, dict):
                continue
            for model_id in models:
                if isinstance(model_id, str) and model_id.strip():
                    ids.append(model_id.strip())
    return ids


def audit_cli_models(cli: str, config_paths: list[str]) -> dict[str, Any]:
    """Report hardcoded model ids in a CLI's user-level configuration."""
    entry: dict[str, Any] = {"cli": cli, "configs": []}
    expected = EXPECTED_MODEL_IDS.get(cli, ())
    for raw in config_paths:
        path = Path(raw).expanduser()
        data, error = parse_config_file(path)
        if data is None:
            entry["configs"].append(
                {"path": clean(raw), "models": [], "unexpected": []}
            )
            continue
        models = _iter_model_ids(data)
        unexpected = [m for m in models if expected and m not in expected]
        entry["configs"].append(
            {
                "path": clean(raw),
                "models": models,
                "unexpected": unexpected,
                "parse_error": error,
            }
        )
    return entry


def audit_project_models() -> dict[str, Any]:
    """Scan tracked project config for hardcoded model lists and paid ids."""
    entry: dict[str, Any] = {"files": [], "paid": []}
    for path in sorted(ROOT.glob("config/*model*.json")):
        if ".cache" in path.name:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ids = _collect_project_model_ids(data)
        paid = sorted(
            {
                model_id
                for model_id, explicit_paid in ids
                if explicit_paid
                and not model_id.endswith(KILO_FREE_SUFFIX)
                and any(marker in model_id.lower() for marker in PAID_MODEL_MARKERS)
            }
        )
        tracked = git_tracked(path) if path.exists() else False
        entry["files"].append(
            {
                "path": clean(str(path)),
                "tracked": tracked,
                "model_count": len(ids),
                "secret_like": _contains_secret_pattern(path),
            }
        )
        if paid and tracked:
            entry["paid"].append(f"{clean(str(path))}: {', '.join(paid)}")
    return entry


def _collect_project_model_ids(node: Any) -> list[tuple[str, bool]]:
    """Collect (model_id, explicit_paid_flag) pairs from tracked config."""
    ids: list[tuple[str, bool]] = []
    if isinstance(node, dict):
        explicit_paid = node.get("type") == "paid"
        for key, value in node.items():
            if key in ("model", "model_id") and isinstance(value, str):
                ids.append((value, explicit_paid))
            else:
                ids.extend(_collect_project_model_ids(value))
    elif isinstance(node, list):
        for item in node:
            ids.extend(_collect_project_model_ids(item))
    return ids


SECRET_VALUE_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_./+-]{20,}"
)


def _contains_secret_pattern(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(SECRET_VALUE_RE.search(text))


def check_secret_grep_coverage() -> list[str]:
    """Report MCP/config files the pre-commit inline-secret grep does not cover.

    Credential stores are intentionally excluded: they hold real keys by design,
    so scanning them can only false-positive, and they are not part of this gap.
    """
    hook = ROOT / ".pre-commit-hooks" / "cli-agent-drift" / "check.sh"
    try:
        hook_text = hook.read_text(encoding="utf-8")
    except OSError:
        return []
    gaps: list[str] = []
    for cli, paths in CLI_MCP_CONFIG_PATHS.items():
        for raw in paths:
            path = Path(raw).expanduser()
            if not path.exists():
                continue
            # The hook may spell the path with `$HOME/`, `~/`, or `$ROOT/`;
            # accept any spelling via a suffix match on the relative tail.
            tail = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else None
            home_suffix = raw[len(str(Path.home())) :]
            spellings = (
                f"$HOME{home_suffix}",
                f"~{home_suffix}",
                f"$ROOT/{tail}" if tail is not None else "",
            )
            if not any(spelling and spelling in hook_text for spelling in spellings):
                gaps.append(f"{cli}:{clean(raw)}")
    return gaps


def add_finding(
    findings: list[dict[str, str]],
    severity: str,
    code: str,
    title: str,
    evidence: str,
    action: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "code": code,
            "title": title,
            "evidence": evidence,
            "action": action,
        }
    )


def build_audit() -> dict[str, Any]:
    dirs = []
    for name in ACTIVE_DIRS:
        path = ROOT / name
        dirs.append(
            {
                "path": name,
                "exists": path.is_dir(),
                "tracked_entries": len(
                    run(["git", "ls-files", f"{name}/**"], 5).stdout.splitlines()
                )
                if path.exists()
                else 0,
                "mode": oct(path.stat().st_mode & 0o7777) if path.exists() else None,
                "group_writable": bool(path.stat().st_mode & 0o020)
                if path.exists()
                else False,
            }
        )
    skill_paths = sorted(
        [
            *ROOT.glob(".agents/skills/*/SKILL.md"),
            *ROOT.glob(".opencode/skills/*/SKILL.md"),
            *ROOT.glob(".kilo/skills/*/SKILL.md"),
        ]
    )
    skills = [audit_skill(path) for path in skill_paths]
    opencode_discovery = discovered_opencode_skills()
    kilo_probe = active_probe("kilo", ["debug", "paths"])
    package_versions = {}
    for product, package_path, binary, dependency_name in (
        (
            "opencode",
            ROOT / ".opencode/package.json",
            "opencode",
            "@opencode-ai/plugin",
        ),
        ("kilo", ROOT / ".kilo/package.json", "kilo", "@kilocode/plugin"),
    ):
        dependency, declared = package_dependency(package_path, dependency_name)
        cli_version = installed_version(binary)
        package_versions[product] = {
            "dependency": dependency,
            "declared": declared,
            "installed_cli": cli_version,
            "matches": declared == cli_version if declared else None,
        }

    findings: list[dict[str, str]] = []
    if kilo_probe["available"] and kilo_probe["exit_code"] != 0:
        add_finding(
            findings,
            "high",
            "KILO_GLOBAL_CONFIG_BLOCKS_PROJECT",
            "Kilo cannot load the active configuration chain.",
            kilo_probe["diagnostic"],
            "Repair or migrate the user-level Kilo config first; retain the valid project .kilo/kilo.jsonc.",
        )
    if package_versions["kilo"]["declared"] and not package_versions["kilo"]["matches"]:
        add_finding(
            findings,
            "medium",
            "KILO_VERSION_SKEW",
            "Project Kilo plugin and installed Kilo CLI versions differ.",
            f"project={package_versions['kilo']['declared']}, cli={package_versions['kilo']['installed_cli']}",
            "Decide whether the package tracks the extension or CLI; document both explicitly and avoid treating them as one version.",
        )
    opencode_only = [
        skill for skill in skills if skill["path"].startswith(".opencode/")
    ]
    if opencode_only:
        add_finding(
            findings,
            "medium",
            "SKILL_PORTABILITY_GAP",
            "A reusable skill is stored only in the OpenCode-specific directory.",
            ", ".join(skill["path"] for skill in opencode_only),
            "If cross-tool use is intended, migrate it to .agents/skills after validating discovery in each target CLI; do not duplicate two writable copies.",
        )
    untracked_skills = [skill for skill in skills if not skill["tracked"]]
    if untracked_skills:
        add_finding(
            findings,
            "medium",
            "UNTRACKED_AGENT_ASSET",
            "One or more active agent skills are untracked.",
            ", ".join(skill["path"] for skill in untracked_skills),
            "Review for secrets and scope, then intentionally track or explicitly ignore each asset; never wildcard-stage.",
        )
    invalid_skills = [skill for skill in skills if not skill["valid"]]
    if invalid_skills:
        add_finding(
            findings,
            "high",
            "INVALID_SKILL_CONTRACT",
            "A skill has invalid metadata or broken local references.",
            "; ".join(
                f"{skill['path']}: {', '.join(skill['errors'])}"
                for skill in invalid_skills
            ),
            "Fix the smallest metadata or link issue and rerun this audit.",
        )
    group_writable = [item["path"] for item in dirs if item["group_writable"]]
    if group_writable:
        add_finding(
            findings,
            "low",
            "GROUP_WRITABLE_AGENT_DIRS",
            "Active agent/config directories are group-writable.",
            ", ".join(group_writable),
            "Confirm the repository group is an intentional trust boundary; agent instructions are executable policy and should not be writable by unintended accounts.",
        )
    add_finding(
        findings,
        "info",
        "SENSITIVE_HISTORY_EXCLUDED",
        "Sensitive historical agent-directory copies were excluded.",
        ".history-remediation contains candidate/fresh-clone agent directories and is sensitive by repository policy.",
        "Keep it ignored and out of generated reports; compare only through an explicitly authorized remediation workflow.",
    )
    missing = [item["path"] for item in dirs if not item["exists"]]
    add_finding(
        findings,
        "info",
        "ABSENT_TOOL_DIRS",
        "Some tool-specific project directories are absent.",
        ", ".join(missing) if missing else "none",
        "Absence is not a defect unless a documented project-specific integration is required; prefer shared AGENTS.md and .agents/skills where supported.",
    )
    cli_mcp = {cli: audit_cli_mcp(cli, paths) for cli, paths in CLI_MCP_CONFIGS.items()}
    for cli, entry in cli_mcp.items():
        for config in entry["configs"]:
            if config["stale_markers"]:
                add_finding(
                    findings,
                    "high",
                    "MCP_STALE_PATH",
                    f"{cli} MCP config references a stale path.",
                    f"{config['path']}: {', '.join(config['stale_markers'])}",
                    "Point the MCP server at the current repository root; stale paths fail closed and expose nothing.",
                )
            if config["malformed_args"]:
                add_finding(
                    findings,
                    "high",
                    "MCP_MALFORMED_ARGS",
                    f"{cli} MCP config has malformed server arguments.",
                    f"{config['path']}: {', '.join(config['malformed_args'])}",
                    "args must be a JSON array of plain strings, never a single bracket-escaped string.",
                )
            if config["disabled"]:
                add_finding(
                    findings,
                    "medium",
                    "MCP_SERVER_DISABLED",
                    f"{cli} MCP server is explicitly disabled.",
                    f"{config['path']}: {', '.join(config['disabled'])}",
                    "Enable only servers that are authorized for this workspace; document why each remains disabled.",
                )
            if config["parse_error"]:
                severity = "info" if config["parse_error"] == "missing" else "medium"
                add_finding(
                    findings,
                    severity,
                    "MCP_CONFIG_PARSE_ERROR",
                    f"{cli} MCP config could not be parsed.",
                    f"{config['path']}: {config['parse_error']}",
                    "Repair the config so the CLI can load its MCP servers; a parse error silently disables every server.",
                )
            if config["uninterpolated_env"]:
                add_finding(
                    findings,
                    "high",
                    "MCP_ENV_INTERPOLATION_UNHANDLED",
                    f"{cli} MCP config uses ${{env:...}} in a command/args array, which resolves incorrectly.",
                    f"{config['path']}: {', '.join(config['uninterpolated_env'])}",
                    "The {env:VAR} substring resolves but the leading $ remains, so the invocation starts with $ and fails. Use the single-brace {env:VAR} form (verified substituted in command/args by opencode 1.18.32 and kilo 7.7.9 on 2026-10-20) or hardcode the literal value.",
                )
    cli_models = {
        cli: audit_cli_models(cli, paths) for cli, paths in CLI_MCP_CONFIGS.items()
    }
    for cli, entry in cli_models.items():
        for config in entry["configs"]:
            unexpected = [
                m for m in config["unexpected"] if not m.endswith(KILO_FREE_SUFFIX)
            ]
            if unexpected:
                add_finding(
                    findings,
                    "info",
                    "HARDCODED_GLOBAL_MODEL",
                    f"{cli} user-level config pins a model not in the sanctioned list.",
                    f"{config['path']}: {', '.join(unexpected)}",
                    "Global model choice is a user preference, not repository drift. Confirm the id is intended and, if the project should share a model policy, document it in the CLI docs rather than editing user config.",
                )
    project_models = audit_project_models()
    for record in project_models["files"]:
        if record["secret_like"]:
            add_finding(
                findings,
                "high",
                "MODEL_CONFIG_SECRET_PATTERN",
                "A tracked model config contains a credential-like value.",
                record["path"],
                "Remove the secret from the tracked config and load it from the environment; rotate the exposed value.",
            )
    if project_models["paid"]:
        add_finding(
            findings,
            "medium",
            "PAID_MODEL_IN_PROJECT_CONFIG",
            "A tracked project config references a paid model endpoint.",
            "; ".join(project_models["paid"]),
            "AGENTS.md forbids paid model use including fallback. Replace the paid id with a verified-free one or remove it, and confirm with the owner before any use.",
        )
    secret_gaps = check_secret_grep_coverage()
    if secret_gaps:
        add_finding(
            findings,
            "medium",
            "SECRET_GREP_COVERAGE_GAP",
            "The pre-commit inline-secret grep does not cover every MCP/config file.",
            ", ".join(secret_gaps),
            "Extend the check.sh inline-secret grep to these MCP/config paths (dedicated credential stores are excluded by design), or document why they are skipped, so an inline secret cannot be committed unnoticed.",
        )
    credential_inventory = [
        {
            "cli": cli,
            "path": clean(path),
            "exists": Path(path).expanduser().exists(),
        }
        for cli, paths in CLI_CREDENTIAL_STORE_PATHS.items()
        for path in paths
    ]
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "scope": {
            "root": "<repo>",
            "active_dirs": ACTIVE_DIRS,
            "excluded": SENSITIVE_EXCLUDED,
        },
        "directories": dirs,
        "skills": skills,
        "runtime": {
            "opencode_skill_discovery": opencode_discovery,
            "kilo_active_config": kilo_probe,
        },
        "package_versions": package_versions,
        "cli_mcp": cli_mcp,
        "cli_models": cli_models,
        "project_models": project_models,
        "credential_inventory": credential_inventory,
        "findings": findings,
        "summary": {
            severity: sum(item["severity"] == severity for item in findings)
            for severity in ("high", "medium", "low", "info")
        },
    }


def markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Current agent-directory audit",
        "",
        f"Generated: `{audit['generated_at']}`",
        "",
        "> Read-only audit of active project agent/config directories. Sensitive historical and operational-data directories were excluded.",
        "",
        "## Findings",
        "",
        "| Severity | Code | Finding | Evidence | Recommended action |",
        "|---|---|---|---|---|",
    ]
    for finding in audit["findings"]:
        cells = [
            finding[key].replace("|", "\\|").replace("\n", " ")
            for key in ("severity", "code", "title", "evidence", "action")
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Directory inventory",
        "",
        "| Directory | Exists | Mode | Tracked entries |",
        "|---|---:|---:|---:|",
    ]
    for item in audit["directories"]:
        lines.append(
            f"| `{item['path']}` | {'yes' if item['exists'] else 'no'} | {item['mode'] or '—'} | {item['tracked_entries']} |"
        )
    lines += [
        "",
        "## Skill contracts",
        "",
        "| Skill | Name | Valid | Tracked |",
        "|---|---|---:|---:|",
    ]
    for skill in audit["skills"]:
        lines.append(
            f"| `{skill['path']}` | {skill['name'] or '—'} | {'yes' if skill['valid'] else 'no'} | {'yes' if skill['tracked'] else 'no'} |"
        )
    lines += [
        "",
        "## Runtime discovery",
        "",
        f"- OpenCode skill discovery: `{audit['runtime']['opencode_skill_discovery']['status']}`.",
        f"- Kilo active-config probe exit: `{audit['runtime']['kilo_active_config']['exit_code']}`.",
        "",
        "## CLI MCP configurations",
        "",
        "| CLI | Config | Servers | Stale paths | Disabled | Uninterpolated env | Parse error |",
        "|---|---|---:|---|---|---|---|",
    ]
    for cli, entry in audit.get("cli_mcp", {}).items():
        for config in entry["configs"]:
            lines.append(
                f"| `{cli}` | `{config['path']}` | {config['server_count']} | "
                f"{', '.join(config['stale_markers']) or '—'} | "
                f"{', '.join(config['disabled']) or '—'} | "
                f"{', '.join(config['uninterpolated_env']) or '—'} | "
                f"{config['parse_error'] or '—'} |"
            )
    lines += [
        "",
        "## Model configuration",
        "",
        "| CLI | Config | Model ids | Unexpected |",
        "|---|---|---|---|",
    ]
    for cli, entry in audit.get("cli_models", {}).items():
        for config in entry["configs"]:
            lines.append(
                f"| `{cli}` | `{config['path']}` | "
                f"{', '.join(config['models']) or '—'} | "
                f"{', '.join(config['unexpected']) or '—'} |"
            )
    lines += [
        "",
        "## Credential stores (existence only)",
        "",
        "| CLI | Path | Exists |",
        "|---|---|---|",
    ]
    for record in audit.get("credential_inventory", []):
        lines.append(
            f"| `{record['cli']}` | `{record['path']}` | "
            f"{'yes' if record['exists'] else 'no'} |"
        )
    lines += [
        "",
        "Credential stores are listed for existence/permission awareness only; their contents are never read and they are intentionally excluded from the inline-secret grep (they hold real keys by design).",
        "",
        "## Boundaries",
        "",
        "- Kilo has two products: the `kilo` CLI reads `~/.config/kilo/kilo.json`; the `kilo-code` VS Code extension reads `<workspace>/.kilo/mcp.json`. They are independent and fixing one does not affect the other.",
        "- `{env:VAR}` in `command`/`args` arrays is substituted by opencode 1.18.32 and kilo 7.7.9 (verified 2026-10-20); `${env:VAR}` is invalid there — the `{env:VAR}` part resolves and a stray `$` remains. Interpolation inside `environment` values was not re-verified in this pass.",
        "- Missing tool-specific directories are not automatically gaps.",
        "- `.history-remediation` was not inspected.",
        "- No credential, session, raw config value, A1, scan, evidence, OCR, data, or output content was read.",
        "- Findings do not authorize moving skills, repairing global user configuration, or staging files.",
        "",
    ]
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; fail when high-severity findings exist.",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "mcp"),
        default="all",
        help="When --check is set, only count findings in this scope. 'mcp' scopes the gate to CLI MCP "
        "configuration drift, which is what the pre-commit hook prevents; skill-contract findings remain "
        "in the report but do not block commits for untracked third-party skills.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_audit()
    if not args.check:
        atomic_write(
            args.output_json, json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
        )
        atomic_write(args.output_markdown, markdown(audit))
        print(args.output_json)
        print(args.output_markdown)
        return 0
    if args.scope == "mcp":
        mcp_codes = {
            "MCP_STALE_PATH",
            "MCP_MALFORMED_ARGS",
            "MCP_ENV_INTERPOLATION_UNHANDLED",
            "MCP_CONFIG_PARSE_ERROR",
            "MCP_SERVER_DISABLED",
            "MODEL_CONFIG_SECRET_PATTERN",
        }
        blocking = [
            f
            for f in audit["findings"]
            if f["severity"] == "high" and f["code"] in mcp_codes
        ]
    else:
        blocking = [f for f in audit["findings"] if f["severity"] == "high"]
    if blocking:
        for finding in blocking:
            print(f"BLOCKING: [{finding['code']}] {finding['evidence'][:200]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
