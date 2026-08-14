#!/usr/bin/env python3
"""Canonical-output isolation regression.

Hashes every canonical research output, runs the entire research/security
suite (which operates only on temporary project-shaped roots), then re-hashes
and proves nothing changed. If any test silently rewrites a canonical file,
this test fails.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Canonical research outputs that must never be mutated by tests.
_TARGETS = [
    ("processed", ["research/processed"]),
    ("raw", ["research/acquisition/raw"]),
    ("cockpit", ["docs/prototypes/research-cockpit"]),
]

_SYNTHETIC_JSON = [
    "research/synthetic/ground_truth.json",
    "research/synthetic/invoices.json",
    "research/synthetic/artifact_manifest.json",
    "research/synthetic/benchmark_results.json",
]

_RESEARCH_TESTS = [
    "tests/test_research_tooling.py",
    "tests/test_gate1_security.py",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot() -> dict:
    snap = {}
    for _name, roots in _TARGETS:
        for root in roots:
            d = REPO / root
            if d.is_dir():
                for p in sorted(d.rglob("*")):
                    if p.is_file():
                        snap[str(p.relative_to(REPO))] = _sha256(p)
    for rel in _SYNTHETIC_JSON:
        p = REPO / rel
        if p.is_file():
            snap[rel] = _sha256(p)
    return snap


def test_research_suite_does_not_mutate_canonical_outputs():
    before = _snapshot()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *_RESEARCH_TESTS],
        cwd=str(REPO), capture_output=True, text=True, timeout=300,
    )
    after = _snapshot()

    assert result.returncode == 0, (
        "research/security suite failed:\n" + result.stdout + "\n" + result.stderr
    )

    assert set(before) == set(after), "canonical output set changed"
    changed = [k for k in before if before[k] != after[k]]
    assert not changed, "canonical research outputs mutated by suite: " + ", ".join(changed)
