"""Resolve operational A1 inputs outside the Git working tree."""

from __future__ import annotations

import os
from pathlib import Path


class A1PrivateInputError(RuntimeError):
    """Raised when the required private input root is unavailable."""


def private_root() -> Path:
    value = os.environ.get("A1_PRIVATE_DIR", "").strip()
    if not value:
        raise A1PrivateInputError(
            "A1_PRIVATE_DIR is required; operational records have no tracked fallback"
        )
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise A1PrivateInputError(f"A1_PRIVATE_DIR is not a directory: {root}")
    return root


def private_path(relative: str) -> Path:
    path = private_root() / relative
    if not path.is_file():
        raise A1PrivateInputError(f"required private A1 input is missing: {relative}")
    return path
