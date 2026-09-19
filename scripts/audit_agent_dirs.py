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
ACTIVE_DIRS = [".agents", ".opencode", ".kilo", ".cline", ".codex", ".claude", ".clinerules", ".kilocode"]
SENSITIVE_EXCLUDED = [".history-remediation", "a1", "scans", "evidence", "ocr", "data", "output"]
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
    return ANSI_RE.sub("", value).replace(str(ROOT), "<repo>").replace(str(Path.home()), "~").strip()


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
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"unsupported frontmatter line: {line}")
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"\'')
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
            for expected in ("interface:", "display_name:", "short_description:", "default_prompt:"):
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
        return {"status": "failed", "skills": [], "diagnostic": clean(result.stderr)[:400]}
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


def add_finding(findings: list[dict[str, str]], severity: str, code: str, title: str, evidence: str, action: str) -> None:
    findings.append({"severity": severity, "code": code, "title": title, "evidence": evidence, "action": action})


def build_audit() -> dict[str, Any]:
    dirs = []
    for name in ACTIVE_DIRS:
        path = ROOT / name
        dirs.append({
            "path": name,
            "exists": path.is_dir(),
            "tracked_entries": len(run(["git", "ls-files", f"{name}/**"], 5).stdout.splitlines()) if path.exists() else 0,
            "mode": oct(path.stat().st_mode & 0o7777) if path.exists() else None,
            "group_writable": bool(path.stat().st_mode & 0o020) if path.exists() else False,
        })
    skill_paths = sorted(
        [*ROOT.glob(".agents/skills/*/SKILL.md"), *ROOT.glob(".opencode/skills/*/SKILL.md"), *ROOT.glob(".kilo/skills/*/SKILL.md")]
    )
    skills = [audit_skill(path) for path in skill_paths]
    opencode_discovery = discovered_opencode_skills()
    kilo_probe = active_probe("kilo", ["debug", "paths"])
    package_versions = {}
    for product, package_path, binary, dependency_name in (
        ("opencode", ROOT / ".opencode/package.json", "opencode", "@opencode-ai/plugin"),
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
    opencode_only = [skill for skill in skills if skill["path"].startswith(".opencode/")]
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
            "; ".join(f"{skill['path']}: {', '.join(skill['errors'])}" for skill in invalid_skills),
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
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "scope": {"root": "<repo>", "active_dirs": ACTIVE_DIRS, "excluded": SENSITIVE_EXCLUDED},
        "directories": dirs,
        "skills": skills,
        "runtime": {"opencode_skill_discovery": opencode_discovery, "kilo_active_config": kilo_probe},
        "package_versions": package_versions,
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
        cells = [finding[key].replace("|", "\\|").replace("\n", " ") for key in ("severity", "code", "title", "evidence", "action")]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "## Directory inventory", "", "| Directory | Exists | Mode | Tracked entries |", "|---|---:|---:|---:|"]
    for item in audit["directories"]:
        lines.append(f"| `{item['path']}` | {'yes' if item['exists'] else 'no'} | {item['mode'] or '—'} | {item['tracked_entries']} |")
    lines += ["", "## Skill contracts", "", "| Skill | Name | Valid | Tracked |", "|---|---|---:|---:|"]
    for skill in audit["skills"]:
        lines.append(f"| `{skill['path']}` | {skill['name'] or '—'} | {'yes' if skill['valid'] else 'no'} | {'yes' if skill['tracked'] else 'no'} |")
    lines += [
        "",
        "## Runtime discovery",
        "",
        f"- OpenCode skill discovery: `{audit['runtime']['opencode_skill_discovery']['status']}`.",
        f"- Kilo active-config probe exit: `{audit['runtime']['kilo_active_config']['exit_code']}`.",
        "",
        "## Boundaries",
        "",
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
    parser.add_argument("--check", action="store_true", help="Write nothing; fail when high-severity findings exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_audit()
    if not args.check:
        atomic_write(args.output_json, json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
        atomic_write(args.output_markdown, markdown(audit))
        print(args.output_json)
        print(args.output_markdown)
    return 1 if audit["summary"]["high"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
