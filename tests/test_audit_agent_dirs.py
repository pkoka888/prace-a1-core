from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_agent_dirs", ROOT / "scripts" / "audit_agent_dirs.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_clean_redacts_repo_and_home() -> None:
    value = f"{ROOT}/.agents {Path.home()}/.config"
    cleaned = module.clean(value)
    assert str(ROOT) not in cleaned
    assert str(Path.home()) not in cleaned
    assert "<repo>/.agents" in cleaned


def test_frontmatter_and_relative_link_audit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    skill_dir = tmp_path / ".agents" / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "reference.md").write_text("ok", encoding="utf-8")
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: demo\ndescription: Synthetic test skill.\n---\n[ref](reference.md)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "git_tracked", lambda path: True)
    result = module.audit_skill(skill)
    assert result["valid"] is True
    assert result["relative_links"] == [{"target": "reference.md", "exists": True}]


def test_invalid_skill_name_and_link(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    skill_dir = tmp_path / ".agents" / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: wrong\ndescription: Synthetic test skill.\n---\n[missing](missing.md)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "git_tracked", lambda path: False)
    result = module.audit_skill(skill)
    assert result["valid"] is False
    assert any("does not match folder" in error for error in result["errors"])
    assert any("broken relative link" in error for error in result["errors"])


def test_iter_model_ids_collects_global_agent_and_provider() -> None:
    data = {
        "model": "kilo/auto",
        "small_model": "kilo/Auto Free",
        "agent": {"plan": {"model": "kilo/stepfun/step-3.7-flash:free"}},
        "provider": {"minimax": {"models": {"minimax/MiniMax-M2.7": {"name": "M2.7"}}}},
    }
    ids = module._iter_model_ids(data)
    assert "kilo/auto" in ids
    assert "kilo/Auto Free" in ids
    assert "kilo/stepfun/step-3.7-flash:free" in ids
    assert "minimax/MiniMax-M2.7" in ids


def test_audit_cli_models_flags_unexpected(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "kilo.json"
    cfg.write_text(
        '{"model": "kilo/auto", "agent": {"x": {"model": "other/paid-model"}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "EXPECTED_MODEL_IDS", {"kilo_cli": ("kilo/auto",)})
    entry = module.audit_cli_models("kilo_cli", [str(cfg)])
    assert entry["configs"][0]["unexpected"] == ["other/paid-model"]


def test_project_models_flags_paid_and_skips_free(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    cfgdir = tmp_path / "config"
    cfgdir.mkdir(parents=True)
    payload = {
        "fallback_chain": [
            {"model": "minimax/minimax-m3:free", "type": "free"},
            {"model": "minimax/minimax-m3", "type": "paid"},
        ]
    }
    (cfgdir / "vision_models.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(module, "git_tracked", lambda path: True)
    result = module.audit_project_models()
    assert any("minimax/minimax-m3" in item for item in result["paid"])
    assert not any(":free" in item for item in result["paid"])


def test_secret_grep_coverage_accepts_home_spelling(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    target = Path.home() / ".config" / "opencode" / "opencode.jsonc"
    monkeypatch.setattr(
        module,
        "CLI_MCP_CONFIG_PATHS",
        {"opencode": (str(target),)},
    )
    monkeypatch.setattr(Path, "exists", lambda self: True)
    hook_dir = tmp_path / ".pre-commit-hooks" / "cli-agent-drift"
    hook_dir.mkdir(parents=True)
    (hook_dir / "check.sh").write_text(
        'grep -q x "$HOME/.config/opencode/opencode.jsonc"\n', encoding="utf-8"
    )
    assert module.check_secret_grep_coverage() == []


def test_secret_grep_coverage_reports_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    target = Path.home() / ".pi" / "agent" / "settings.json"
    monkeypatch.setattr(module, "CLI_MCP_CONFIG_PATHS", {"pi": (str(target),)})
    monkeypatch.setattr(Path, "exists", lambda self: True)
    hook_dir = tmp_path / ".pre-commit-hooks" / "cli-agent-drift"
    hook_dir.mkdir(parents=True)
    (hook_dir / "check.sh").write_text("grep -q x unrelated\n", encoding="utf-8")
    gaps = module.check_secret_grep_coverage()
    assert gaps == ["pi:~/.pi/agent/settings.json"]


def test_frontmatter_block_scalar_description(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\n"
        "name: demo\n"
        "description: >\n"
        "  Folded description spanning lines.\n"
        "  Second line with a colon: still the same value.\n"
        "license: Proprietary terms\n"
        "---\n"
        "body\n",
        encoding="utf-8",
    )
    metadata, errors = module.parse_frontmatter(skill)
    assert errors == []
    assert metadata["name"] == "demo"
    assert "colon: still the same value" in metadata["description"]
    assert metadata["license"] == "Proprietary terms"


def test_frontmatter_list_block_is_one_value(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\n"
        "name: demo\n"
        "description: Inline description.\n"
        "triggers:\n"
        "  - markdown to pdf\n"
        "  - generate pdf\n"
        "allowed-tools:\n"
        "  - Bash\n"
        "  - Read\n"
        "---\n",
        encoding="utf-8",
    )
    metadata, errors = module.parse_frontmatter(skill)
    assert errors == []
    assert metadata["triggers"] == "markdown to pdf, generate pdf"
    assert metadata["allowed-tools"] == "Bash, Read"


def test_frontmatter_quoted_scalar(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '---\nname: demo\ndescription: "Quoted: value with a colon."\n---\n',
        encoding="utf-8",
    )
    metadata, errors = module.parse_frontmatter(skill)
    assert errors == []
    assert metadata["description"] == "Quoted: value with a colon."


def _hook_secret_regex_and_flags() -> tuple[str, str]:
    """Extract the shipping SECRET_RE and the grep flags from check.sh."""
    import re

    hook = ROOT / ".pre-commit-hooks" / "cli-agent-drift" / "check.sh"
    text = hook.read_text(encoding="utf-8")
    match = re.search(r"^SECRET_RE='(.*)'$", text, re.MULTILINE)
    assert match, "SECRET_RE assignment not found in check.sh"
    regex = match.group(1)
    # Reproduce the shell single-quote escape `'"'"'` -> `'`.
    regex = regex.replace("'\"'\"'", "'")
    flags_match = re.search(r"grep -E(qi|qu)\b", text)
    assert flags_match, "grep flags not found in check.sh"
    return regex, flags_match.group(1)


def test_hook_secret_regex_matches_case_variants() -> None:
    import subprocess

    regex, flags = _hook_secret_regex_and_flags()
    assert flags == "qi", f"hook must use grep -Eqi (case-insensitive), got {flags!r}"
    secret = "abcdefghijklmnopqrstuvwx0123"
    must_match = [
        f"API_KEY={secret}",
        f"apiKey: {secret}",
        f'api-key = "{secret}"',
        f"Api_Key={secret}",
        f"apikey={secret}",
        f"sk-{secret}",
    ]
    must_not_match = ["plain text without secrets", '"apiKey": "{env:FOO_API_KEY}"']
    for line in must_match:
        proc = subprocess.run(
            ["grep", f"-E{flags}", regex],
            input=line,
            text=True,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, f"expected match for {line!r}"
    for line in must_not_match:
        proc = subprocess.run(
            ["grep", f"-E{flags}", regex],
            input=line,
            text=True,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 1, f"expected no match for {line!r}"
