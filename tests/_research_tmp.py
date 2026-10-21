"""Shared helpers for research tests: build a temporary project-shaped root.

Every research/security test must run against an isolated copy of the repo so it
can never mutate canonical outputs under ``research/``, ``docs/prototypes/
research-cockpit/``, or ``tests/fixtures/``. ``build_tmp_root`` copies only the
subtrees the research scripts touch (never private/gitignored data).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"

# Subtrees copied into the temp project root. None of these contain private or
# gitignored research data (a1/, scans/, evidence/, etc.).
_COPY_REL = [
    "scripts",
    "research/schemas",
    "research/processed",
    "research/acquisition",
    "research/review",
    "research/query-packs",
    "research/synthetic",
    "docs/prototypes/research-cockpit",
]


def build_tmp_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir(parents=True, exist_ok=True)
    for rel in _COPY_REL:
        src = REPO / rel
        if not src.exists():
            continue
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    return root


def run_script(root: Path, name: str, *args: str) -> subprocess.CompletedProcess:
    """Run a research script from the temp root copy (so its output paths land
    inside the temp root, never the canonical repo)."""
    script = root / "scripts" / name
    env = dict(os.environ)
    cmd = [sys.executable, str(script), "--root", str(root), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_input(root: Path, data: dict) -> Path:
    p = root / "research" / "processed" / "entities.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def processed(root: Path) -> Path:
    return root / "research" / "processed"


def raw_dir(root: Path) -> Path:
    d = root / "research" / "acquisition" / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d
