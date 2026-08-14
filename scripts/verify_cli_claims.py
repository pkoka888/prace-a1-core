#!/usr/bin/env python3
"""Verify local CLI claims and generate sanitized JSON and Markdown reports.

The verifier is read-only. It does not run agent prompts, inspect credential
files, export sessions, update tools, or include raw configuration values.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "cli_verification_claims.json"
DEFAULT_JSON = ROOT / "cli-docs-update" / "current-verification.json"
DEFAULT_MARKDOWN = ROOT / "cli-docs-update" / "current-verification.md"
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SECRET_RE = re.compile(
    r"(?i)(api[-_]?key|access[-_]?token|auth(?:orization)?|bearer|client[-_]?secret|password|cookie)"
)


def clean_text(value: str, root: Path) -> str:
    """Strip terminal control codes and replace machine-specific roots."""
    value = ANSI_RE.sub("", value).replace("\r", "")
    replacements = [(str(root), "<repo>")]
    home = str(Path.home())
    if home:
        replacements.append((home, "~"))
    for original, replacement in sorted(replacements, key=lambda item: -len(item[0])):
        value = value.replace(original, replacement)
    return value.strip()


def safe_excerpt(value: str, root: Path, limit: int = 500) -> str:
    cleaned = clean_text(value, root)
    lines: list[str] = []
    for line in cleaned.splitlines():
        if SECRET_RE.search(line):
            lines.append("<redacted sensitive line>")
        else:
            lines.append(line)
    excerpt = "\n".join(lines)
    if len(excerpt) > limit:
        return excerpt[:limit].rstrip() + "…"
    return excerpt


def run_command(binary: str, args: list[str], cwd: Path, timeout: float) -> dict[str, Any]:
    command = [binary, *args]
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "exit_code": None, "stdout": "", "stderr": ""}
    except OSError as exc:
        return {"status": "error", "exit_code": None, "stdout": "", "stderr": str(exc)}
    return {
        "status": "completed",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_json_output(stdout: str) -> tuple[bool, Any | None]:
    stripped = ANSI_RE.sub("", stdout).strip()
    if not stripped:
        return False, None
    try:
        return True, json.loads(stripped)
    except json.JSONDecodeError:
        return False, None


def json_shape(value: Any) -> dict[str, Any]:
    """Describe JSON without retaining values that might be sensitive."""
    if isinstance(value, dict):
        safe_keys = sorted(key for key in value if not SECRET_RE.search(str(key)))
        return {"type": "object", "keys": safe_keys, "redacted_key_count": len(value) - len(safe_keys)}
    if isinstance(value, list):
        types = sorted({type(item).__name__ for item in value})
        return {"type": "array", "length": len(value), "item_types": types}
    return {"type": type(value).__name__}


def display_command(binary: str, args: list[str]) -> str:
    return " ".join([binary, *args])


def verify_product(spec: dict[str, Any], root: Path, timeout: float) -> dict[str, Any]:
    binary_name = spec["binary"]
    binary = shutil.which(binary_name)
    result: dict[str, Any] = {
        "id": spec["id"],
        "label": spec["label"],
        "binary": binary_name,
        "installed": binary is not None,
        "binary_path": clean_text(binary, root) if binary else None,
        "version": None,
        "help_available": False,
        "probes": [],
        "native_outputs": [],
    }
    if binary is None:
        for probe in spec.get("safe_probes", []):
            result["native_outputs"].append({**probe, "executed": False, "status": "binary_missing"})
        result["_help_text"] = ""
        return result

    version_run = run_command(binary, spec.get("version_args", ["--version"]), root, timeout)
    combined_version = "\n".join([version_run["stdout"], version_run["stderr"]]).strip()
    if version_run["status"] == "completed" and version_run["exit_code"] == 0:
        version_lines = safe_excerpt(combined_version, root, 240).splitlines()
        result["version"] = version_lines[0] if version_lines else None

    help_run = run_command(binary, spec.get("help_args", ["--help"]), root, timeout)
    combined_help = "\n".join([help_run["stdout"], help_run["stderr"]])
    help_text = clean_text(combined_help, root)
    result["help_available"] = help_run["status"] == "completed" and help_run["exit_code"] == 0
    result["_help_text"] = help_text

    for probe in spec.get("safe_probes", []):
        inventory = {
            "id": probe["id"],
            "command": display_command(binary_name, probe["args"]),
            "format": probe["format"],
            "purpose": probe["purpose"],
            "executed": probe.get("run", True),
        }
        if not inventory["executed"]:
            inventory["status"] = "skipped_by_policy"
            inventory["reason"] = probe["reason"]
            result["native_outputs"].append(inventory)
            continue

        probe_run = run_command(binary, probe["args"], root, timeout)
        probe_record: dict[str, Any] = {
            "id": probe["id"],
            "status": probe_run["status"],
            "exit_code": probe_run["exit_code"],
        }
        output = probe_run["stdout"]
        error = probe_run["stderr"]
        if probe["format"] == "json":
            valid, parsed = parse_json_output(output)
            probe_record["valid_json"] = valid
            if valid:
                probe_record["json_shape"] = json_shape(parsed)
            elif error or output:
                probe_record["diagnostic"] = safe_excerpt(error or output, root)
        else:
            probe_record["excerpt"] = safe_excerpt(output or error, root)
        result["probes"].append(probe_record)
        if probe_run["status"] == "completed" and probe_run["exit_code"] == 0:
            inventory["status"] = "succeeded"
        elif probe["format"] == "json" and probe_record.get("valid_json"):
            inventory["status"] = "completed_with_findings"
        else:
            inventory["status"] = "failed"
        result["native_outputs"].append(inventory)
    return result


def evaluate_claim(claim: dict[str, Any], products: dict[str, dict[str, Any]]) -> dict[str, Any]:
    product = products[claim["product"]]
    result = {
        "id": claim["id"],
        "product": claim["product"],
        "statement": claim["statement"],
        "status": "NOT_TESTED",
        "evidence": "",
    }
    if not product["installed"]:
        result["evidence"] = "Binary is not installed or not on PATH."
        return result
    if claim["source"] == "help":
        token = claim["contains"]
        if not product["help_available"]:
            result["evidence"] = "Help command did not complete successfully."
        elif token in product["_help_text"]:
            result["status"] = "VERIFIED_RUNTIME"
            result["evidence"] = f"Built-in help contains {token!r}."
        else:
            result["status"] = "CONTRADICTED"
            result["evidence"] = f"Built-in help does not contain {token!r}."
        return result
    if claim["source"] == "probe":
        probe = next((item for item in product["probes"] if item["id"] == claim["probe"]), None)
        if probe is None:
            result["evidence"] = "Required probe was not executed."
        elif probe["status"] == "timeout":
            result["evidence"] = "Required probe timed out."
        elif claim.get("expect") == "json" and probe.get("valid_json"):
            result["status"] = "VERIFIED_RUNTIME"
            result["evidence"] = "Native command returned valid JSON."
        elif claim.get("expect") == "json":
            result["status"] = "CONTRADICTED"
            result["evidence"] = "Native command did not return valid JSON in this run."
        elif claim.get("expect") == "exit_zero" and probe.get("exit_code") == 0:
            result["status"] = "VERIFIED_RUNTIME"
            result["evidence"] = "Native diagnostic completed with exit code 0."
        elif claim.get("expect") == "exit_zero":
            result["status"] = "CONTRADICTED"
            result["evidence"] = f"Native diagnostic exited {probe.get('exit_code')}; see its sanitized diagnostic."
        elif claim.get("expect") == "contains" and claim.get("contains") in probe.get("excerpt", ""):
            result["status"] = "VERIFIED_RUNTIME"
            result["evidence"] = f"Native diagnostic contains {claim['contains']!r}."
        elif claim.get("expect") == "contains":
            result["status"] = "CONTRADICTED"
            result["evidence"] = f"Native diagnostic does not contain {claim['contains']!r}."
        return result
    if claim["source"] == "manual":
        result["evidence"] = claim["reason"]
        return result
    result["evidence"] = f"Unknown claim source {claim['source']!r}."
    return result


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Current CLI verification",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "> Generated by `scripts/verify_cli_claims.py`. This is the current reproducible report; dated investigation files are historical inputs only.",
        "",
        "## Installed tools",
        "",
        "| Tool | Installed | Version | Safe probes |",
        "|---|---:|---|---:|",
    ]
    for product in report["products"]:
        version = (product["version"] or "—").replace("\n", " ").replace("|", "\\|")
        succeeded = sum(
            1
            for probe in product["native_outputs"]
            if probe["status"] in {"succeeded", "completed_with_findings"}
        )
        lines.append(f"| {product['label']} | {'yes' if product['installed'] else 'no'} | {version} | {succeeded} |")

    lines += ["", "## Claims", "", "| Status | Product | Claim | Evidence |", "|---|---|---|---|"]
    for claim in report["claims"]:
        evidence = claim["evidence"].replace("|", "\\|")
        lines.append(f"| {claim['status']} | {claim['product']} | {claim['statement']} | {evidence} |")

    lines += [
        "",
        "## Native machine-readable output inventory",
        "",
        "Commands marked `skipped_by_policy` are documented but deliberately not executed.",
        "",
        "| Product | Command | Format | Status | Reason/purpose |",
        "|---|---|---|---|---|",
    ]
    for product in report["products"]:
        for item in product["native_outputs"]:
            detail = item.get("reason", item["purpose"]).replace("|", "\\|")
            lines.append(
                f"| {product['id']} | `{item['command']}` | {item['format']} | {item['status']} | {detail} |"
            )

    model_policy = report["model_assistance"]
    sampling = model_policy["sampling"]
    lines += [
        "",
        "## Model-assisted stage",
        "",
        f"Status: **{'enabled' if model_policy['enabled'] else 'disabled'}**; authority: `{model_policy['authority']}`; activation: `{model_policy['activation']}`.",
        "",
        "The deterministic verifier does not need an agent or model. If an operator explicitly enables an advisory stage:",
        "",
        f"- Use temperature `{sampling['temperature']}` or the provider's lowest supported value only when supported.",
        f"- Use reasoning effort `{sampling['reasoning_effort']['extraction']}` for extraction and `{sampling['reasoning_effort']['conflict_analysis']}` for conflict analysis.",
        "- Do not tune `top_p` and temperature together.",
        f"- Compare {sampling['material_claim_samples']} independent outputs for material unresolved claims; disagreement remains `NOT_TESTED`.",
        "- Advisory output may propose follow-up probes but cannot issue runtime verdicts.",
        "- External calls remain disabled by default and may use only verified-free, sanitized inputs under repository policy.",
    ]

    lines += [
        "",
        "## Interpretation rules",
        "",
        "- `VERIFIED_RUNTIME` means the installed binary produced the required evidence during this run.",
        "- File existence alone is not proof that a product discovers or accepts a configuration.",
        "- A non-interactive `run` command and automatic permission approval are separate capabilities.",
        "- Credential files and session exports are intentionally excluded.",
        "- CLI and editor-extension versions must be reported separately.",
        "",
    ]
    return "\n".join(lines)


def build_report(registry: dict[str, Any], root: Path, timeout: float, selected: set[str]) -> dict[str, Any]:
    specs = [item for item in registry["products"] if not selected or item["id"] in selected]
    products = [verify_product(item, root, timeout) for item in specs]
    by_id = {item["id"]: item for item in products}
    claims = [evaluate_claim(item, by_id) for item in registry["claims"] if item["product"] in by_id]
    for product in products:
        product.pop("_help_text", None)
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": "scripts/verify_cli_claims.py",
        "policy": {
            "read_only": True,
            "network_requests_by_verifier": False,
            "subprocess_network_isolation": False,
            "agent_tasks": False,
            "credential_contents": False,
            "raw_config_values": False,
        },
        "model_assistance": registry["model_assistance"],
        "products": products,
        "claims": claims,
        "summary": {
            status: sum(1 for claim in claims if claim["status"] == status)
            for status in ["VERIFIED_RUNTIME", "CONTRADICTED", "NOT_TESTED"]
        },
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--product", action="append", default=[], help="Limit to a product ID; repeatable.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-command timeout in seconds.")
    parser.add_argument("--check", action="store_true", help="Do not write; fail if any tested claim is contradicted.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    known = {item["id"] for item in registry["products"]}
    unknown = set(args.product) - known
    if unknown:
        print(f"unknown product(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    report = build_report(registry, ROOT, args.timeout, set(args.product))
    if not args.check:
        write_text(args.output_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        write_text(args.output_markdown, markdown_report(report))
        print(args.output_json)
        print(args.output_markdown)
    return 1 if report["summary"]["CONTRADICTED"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
