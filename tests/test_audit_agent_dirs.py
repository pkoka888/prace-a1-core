from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_agent_dirs", ROOT / "scripts" / "audit_agent_dirs.py")
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
