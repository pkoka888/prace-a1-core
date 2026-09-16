"""Shared fail-closed contract for ``DOCUMENT_TEST_PG_*`` test targets.

Both the document test settings and the browser test settings agree on one
rule: the absence of every ``DOCUMENT_TEST_PG_*`` variable selects the
module's local SQLite default, and the presence of ANY one of them requires
a complete, consistent PostgreSQL test target. A lone variable (for example
``DOCUMENT_TEST_PG_HOST``) must never silently fall back to SQLite, and a
TCP target must always carry the password the server expected to see.

The operator database is never a test target: a ``DOCUMENT_TEST_PG_NAME``
that matches the operator database name(s) is refused by exact name.
"""
from __future__ import annotations


# Exact operator database names. Test targets must never point here.
OPERATOR_DB_NAMES = frozenset({"prace_synthetic"})

_VARS = (
    "DOCUMENT_TEST_PG_SOCKET",
    "DOCUMENT_TEST_PG_NAME",
    "DOCUMENT_TEST_PG_USER",
    "DOCUMENT_TEST_PG_HOST",
    "DOCUMENT_TEST_PG_PORT",
    "DOCUMENT_TEST_PG_PASSWORD",
)


def resolve_test_postgres_target(environ: dict, *, runtime_base: str) -> dict | None:
    """Return the DATABASES ``"default"`` mapping for an explicitly
    configured isolated test target, or ``None`` when no test target
    variable is present (caller keeps its SQLite default).

    Raises RuntimeError for a partial, ambiguous or unsafe target. The
    error names the exact variable that caused the refusal so a CI
    operator can correct the exported set.
    """
    if not any(name in environ for name in _VARS):
        return None
    present = [name for name in _VARS if name in environ]
    for name in ("DOCUMENT_TEST_PG_NAME", "DOCUMENT_TEST_PG_USER"):
        if name in present and not (environ.get(name) or "").strip():
            raise RuntimeError(
                f"{name} is present but blank; a test target needs a "
                "non-empty database name and role")
    _require(environ, "DOCUMENT_TEST_PG_NAME", present)
    _require(environ, "DOCUMENT_TEST_PG_USER", present)
    socket_path = (environ.get("DOCUMENT_TEST_PG_SOCKET") or "").strip()
    host = (environ.get("DOCUMENT_TEST_PG_HOST") or "").strip()
    if socket_path and host:
        raise RuntimeError(
            "set DOCUMENT_TEST_PG_SOCKET or DOCUMENT_TEST_PG_HOST, not both")
    if not (socket_path or host):
        raise RuntimeError(
            "DOCUMENT_TEST_PG_SOCKET or DOCUMENT_TEST_PG_HOST is required "
            "with DOCUMENT_TEST_PG_NAME")
    name = environ["DOCUMENT_TEST_PG_NAME"].strip()
    if name in OPERATOR_DB_NAMES:
        raise RuntimeError(
            f"DOCUMENT_TEST_PG_NAME={name!r} is the operator database name; "
            "refused as a test target")
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": environ["DOCUMENT_TEST_PG_USER"].strip(),
    }
    password = environ.get("DOCUMENT_TEST_PG_PASSWORD")
    if password:
        config["PASSWORD"] = password
    if socket_path:
        from pathlib import Path
        path = Path(socket_path).resolve()
        if not path.is_relative_to(Path(runtime_base)):
            raise RuntimeError(
                "test PostgreSQL socket must be inside project runtime")
        config["HOST"] = str(path)
        config["PORT"] = environ.get("DOCUMENT_TEST_PG_PORT") or "55439"
    else:
        config["HOST"] = host
        config["PORT"] = environ.get("DOCUMENT_TEST_PG_PORT") or "5432"
        if not password:
            raise RuntimeError(
                "DOCUMENT_TEST_PG_PASSWORD is required for a TCP test "
                "PostgreSQL target (DOCUMENT_TEST_PG_HOST set); peer/trust "
                "sockets use DOCUMENT_TEST_PG_SOCKET without a password")
    return config


def _require(environ: dict, name: str, present: list) -> None:
    if name not in present:
        has = ", ".join(present) or "none"
        raise RuntimeError(
            f"partial test PostgreSQL target ({name} missing; present: {has}). "
            "Set the complete DOCUMENT_TEST_PG_* set or none")