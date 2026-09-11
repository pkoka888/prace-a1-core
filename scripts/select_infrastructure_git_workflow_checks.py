#!/usr/bin/env python3
"""Select checks for the infrastructure_git_workflow package.

Detects whether the staged scope changes runtime dependencies
(``requirements.txt`` / ``requirements-dev.txt`` / ``requirements-lock.txt``).
A dependency change must also exercise the live application so a
silent regression in, say, ``whitenoise`` or ``rapidocr`` does not
silently slip past the pure-tooling tests.

When no dependency is staged, the selector returns the narrow
tooling checks. When a dependency is staged, it returns the same
narrow checks plus the supervised-synthetic rehearsal journey (the
cheapest runnable evidence that the live application boots and
serves its documented contracts) so a missing or broken dependency
is reported as a hook failure rather than silently passing.

Selection never imports app code.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_change_packages import git, matches, nul_paths


REPO_ROOT = Path(__file__).resolve().parents[1]

DEPENDENCY_PATTERNS = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-lock.txt",
)
APPLICATION_CHECK = (
    "venv/bin/python -m pytest tests/test_rehearse_synthetic_site.py "
    "tests/test_rehearse_synthetic_site_lifecycle.py -q"
)


def staged_paths(root: Path = REPO_ROOT) -> list[str]:
    catalog = json.loads(git(root, "show", ":change-packages.yml"))
    package = catalog["packages"]["infrastructure_git_workflow"]
    paths = nul_paths(git(root, "diff", "--cached", "--name-only",
                          "--no-renames", "-z"))
    return sorted(p for p in paths if
                  any(matches(p, r) for r in package.get("paths", [])) or
                  any(matches(p, r, prefix=True) for r in package.get("prefixes", [])))


def has_dependency_change(paths: list[str]) -> bool:
    return any(
        Path(p).name in DEPENDENCY_PATTERNS
        or any(p.endswith("/" + name) for name in DEPENDENCY_PATTERNS)
        for p in paths
    )


def select(paths: list[str], root: Path = REPO_ROOT) -> list[str]:
    commands = []
    # Always run the narrow tooling checks declared by the package.
    # The dispatch layer in ``scripts/validate_change_packages.py``
    # already invokes the selector; the narrow tooling checks are
    # declared in the package itself and we do not duplicate them
    # here. We only add the dependency-application fallback when a
    # dependency file is staged.
    if has_dependency_change(paths):
        commands.append(APPLICATION_CHECK)
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--paths-json",
                        help="Exact paths supplied by the owning package receipt")
    args = parser.parse_args()
    paths = json.loads(args.paths_json) if args.paths_json is not None \
        else staged_paths(args.root)
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        parser.error("paths must be a JSON array of strings")
    for command in select(paths, args.root):
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())