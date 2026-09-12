#!/usr/bin/env python3
"""Bounded strict smoke for the rehearsal script.

Parses /health/, /readiness/, /login/, /review/, /accounts/login/,
and the static assets. Requires the same JSON contract the
supervised-synthetic settings module publishes:

- git_commit is the exact manifest git_commit.
- app_build_id is the exact manifest app_build_id.
- supervised is exactly True (boolean).
- real_data is exactly False (boolean).
- mode is exactly 'settings_supervised_synthetic'.
- /readiness/ status is exactly 'ready'.
- /login/ and /review/ redirect to a same-origin path with the
  expected query (no external host accepted).

Each probe is a single bounded request whose status, headers, and
body are all parsed in one place. The script never accepts a
substring of a JSON key as evidence of a boolean field; the JSON
itself is parsed and the typed field is compared.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _bounded_request(url: str, host_header: str, method: str = "GET",
                    connect_timeout: float = 2.0, read_timeout: float = 5.0,
                    body_cap: int = 8_388_608):
    """One bounded request. Returns (status, headers, body).

    No automatic redirect follow; no cookie jar. ``read_timeout`` is
    the overall request deadline: TCP connect plus response body read
    must both finish within the budget. The opener's ``timeout`` is
    the urllib connect+read timeout; we additionally enforce the same
    budget through wall-clock deadline checks before/after every step
    and arm the underlying socket with the remaining budget before
    each read so a server that holds the body open without delivering
    bytes is interrupted at the OS level. A body that trickles bytes
    slowly is caught by the wall-clock check on the iteration after
    the blocked read completes (manual reads therefore never run
    without a ceiling). The Error-body path reads directly from the
    socket, which returns partial data immediately and honors the
    armed timeout exactly, so a dripping or held error body always
    raises ``TimeoutError`` within the deadline. ``TimeoutError``
    propagates from the success path and from the HTTPError body path
    alike (the error branch only carries a missing-body default).
    ``body_cap``
    bounds the accumulated body size (default 8 MiB so the bundled
    Tailwind CSS survives; the helper raises
    ``ValueError("SMOKE_BODY_CAP_EXCEEDED")`` once the cap is hit so
    a malicious server cannot exhaust memory).

    The configured ``Host`` header and ``method`` are honored by
    sending the ``Request`` object to the opener. The previous
    implementation discarded the Request, which silently rewrote
    ``Host`` and turned ``HEAD`` into ``GET``.
    """
    import time as _time
    request = urllib.request.Request(url, method=method)
    request.add_header("Host", host_header)
    opener = urllib.request.build_opener(
        NoRedirect,
        urllib.request.ProxyHandler({}),
    )
    deadline = _time.monotonic() + read_timeout
    response = None
    http_error_response = None

    def _overrun(label: str) -> None:
        raise TimeoutError(
            f"{label} exceeded {read_timeout:.1f}s budget")

    def _find_socket(stream):
        """Walk the body-stream chain to the real socket object.

        http.client nests the stream: HTTPError/HTTPResponse expose
        ``fp`` (a buffered reader) whose ``raw`` is a SocketIO holding
        the socket. The success body must be read through the reader
        (it may already hold body bytes), but its underlying socket is
        what we arm with the remaining deadline.
        """
        candidate = stream
        for _ in range(6):
            sock = getattr(candidate, "_sock", None)
            if sock is not None and getattr(sock, "fileno", None):
                return sock
            nxt = getattr(candidate, "fp", None) or getattr(candidate, "raw", None)
            if nxt is None or nxt is candidate:
                return None
            candidate = nxt
        return None

    def _arm_socket_timeout(sock, *, label: str) -> None:
        remaining = deadline - _time.monotonic()
        if remaining <= 0:
            _overrun(label)
        try:
            sock.settimeout(min(remaining, read_timeout))
        except (OSError, ValueError):
            pass

    def _read_in_chunks(stream, *, label: str) -> bytes:
        """Read the success body through the http.client reader.

        The reader is required so body bytes that arrived together with
        the response headers (already buffered inside the reader) are
        not lost. The reader's own read does not return partial data
        for large chunk sizes on this stack, so a held-open body is
        interrupted by the armed socket timeout and a slow drip is
        bounded by the wall-clock check on the following iteration.
        """
        chunks = []
        total = 0
        while True:
            sock = _find_socket(stream)
            if sock is not None:
                _arm_socket_timeout(sock, label=label)
            try:
                chunk = stream.read(65536)
            except (TimeoutError, socket.timeout) as exc:
                raise TimeoutError(
                    f"{label} chunk read exceeded {read_timeout:.1f}s "
                    f"budget: {exc}") from exc
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > body_cap:
                raise ValueError(
                    f"SMOKE_BODY_CAP_EXCEEDED ({total} > {body_cap})")
        return b"".join(chunks)

    def _read_error_body_from_socket(stream, *, label: str) -> bytes:
        """Drain an HTTPError body straight from the socket.

        Error bodies are diagnostics only, so bytes still buffered in
        the client reader are irrelevant. Reading at the socket level
        is the one primitive on this stack that returns partial data
        and honors ``settimeout`` precisely, which gives the error
        path a real sub-second deadline even for a slow drip.
        """
        sock = _find_socket(stream)
        if sock is None:
            return b""
        chunks = []
        total = 0
        while True:
            _arm_socket_timeout(sock, label=label)
            try:
                chunk = sock.recv(65536)
            except (TimeoutError, socket.timeout, BlockingIOError) as exc:
                raise TimeoutError(
                    f"{label} read exceeded {read_timeout:.1f}s "
                    f"budget: {exc}") from exc
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > body_cap:
                raise ValueError(
                    f"SMOKE_BODY_CAP_EXCEEDED ({total} > {body_cap})")
        return b"".join(chunks)

    try:
        # Pass the Request object, not the URL string. Use a tighter
        # connect ceiling by passing ``timeout=connect_timeout`` to
        # opener.open so TCP setup respects it; the wall-clock
        # deadline check after open covers any drift.
        response = opener.open(request, timeout=connect_timeout)
        if _time.monotonic() > deadline:
            _overrun("connect+headers")
        raw = _read_in_chunks(response, label="body")
        if _time.monotonic() > deadline:
            _overrun("body read")
        status = response.status
        headers = response.headers
        body = raw
    except urllib.error.HTTPError as exc:
        http_error_response = exc
        if _time.monotonic() > deadline:
            _overrun("error body")
        try:
            raw = _read_error_body_from_socket(exc, label="error body")
        except AttributeError:
            raw = b""
        status = exc.code
        headers = exc.headers
        body = raw
    finally:
        for r in (response, http_error_response):
            if r is not None:
                try:
                    r.close()
                except Exception:
                    pass
    return status, headers, body


def _parse_json_safely(body: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(body.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _check_health(base: str, host_header: str, expected_commit: str,
                  expected_build_id: str) -> dict[str, Any]:
    status, headers, body = _bounded_request(f"{base}/health/", host_header)
    payload = _parse_json_safely(body) or {}
    body_commit = payload.get("git_commit")
    body_build = payload.get("build_id")
    body_super = payload.get("supervised")
    body_real = payload.get("real_data")
    body_mode = payload.get("mode")
    contract_ok = (
        status == 200
        and body_commit == expected_commit
        and body_build == expected_build_id
        and body_super is True
        and body_real is False
        and body_mode == "settings_supervised_synthetic"
    )
    result = {
        "path": "/health/",
        "status": status,
        "contract_ok": contract_ok,
        "expected": {
            "http_status": 200,
            "git_commit": expected_commit,
            "build_id": expected_build_id,
            "supervised": True,
            "real_data": False,
            "mode": "settings_supervised_synthetic",
        },
        "observed": {
            "http_status": status,
            "git_commit_eq": body_commit == expected_commit,
            "build_id_eq": body_build == expected_build_id,
            "supervised_eq": body_super is True,
            "real_data_eq": body_real is False,
            "mode_eq": body_mode == "settings_supervised_synthetic",
        },
    }
    return result


def _check_readiness(base: str, host_header: str, expected_commit: str,
                     expected_build_id: str) -> dict[str, Any]:
    status, headers, body = _bounded_request(f"{base}/readiness/", host_header)
    payload = _parse_json_safely(body) or {}
    result = {
        "path": "/readiness/",
        "status": status,
        "contract_ok": (
            status == 200
            and payload.get("status") == "ready"
            and payload.get("git_commit") == expected_commit
            and payload.get("build_id") == expected_build_id
            and payload.get("supervised") is True
            and payload.get("real_data") is False
        ),
        "expected": {
            "http_status": 200,
            "body_status": "ready",
            "git_commit": expected_commit,
            "build_id": expected_build_id,
            "supervised": True,
            "real_data": False,
        },
        "observed": {
            "http_status": status,
            "body": payload,
        },
    }
    return result


def _check_redirect_same_origin(base: str, host_header: str, path: str,
                                expected_path: str,
                                expected_query: dict[str, str] | None = None
                                ) -> dict[str, Any]:
    status, headers, body = _bounded_request(f"{base}{path}", host_header)
    location = headers.get("Location", "")
    target = urllib.parse.urlsplit(urllib.parse.urljoin(f"{base}{path}", location))
    origin = urllib.parse.urlsplit(base)
    target_query = urllib.parse.parse_qs(target.query)
    expected_query = expected_query or {}
    query_ok = all(target_query.get(k) == [v] for k, v in expected_query.items())
    same_origin = (target.scheme, target.netloc) == (origin.scheme, origin.netloc)
    contract_ok = (
        status == 302
        and same_origin
        and target.path == expected_path
        and query_ok
    )
    return {
        "path": path,
        "status": status,
        "contract_ok": contract_ok,
        "expected": {
            "status": 302,
            "target_path": expected_path,
            "same_origin": True,
            "query": expected_query,
        },
        "observed": {
            "location": location,
            "target_scheme": target.scheme,
            "target_netloc": target.netloc,
            "target_path": target.path,
            "target_query": target_query,
            "same_origin": same_origin,
        },
    }


def _check_login_form(base: str, host_header: str) -> dict[str, Any]:
    status, headers, body = _bounded_request(f"{base}/accounts/login/", host_header)
    text = body.decode("utf-8", errors="replace")
    has_password = 'name="password"' in text
    has_login = 'name="login"' in text
    has_csrf = "csrfmiddlewaretoken" in text or "csrf_token" in text
    return {
        "path": "/accounts/login/",
        "status": status,
        "contract_ok": (
            status == 200
            and has_password
            and has_login
            and has_csrf
        ),
        "expected": {
            "status": 200,
            "has_password_field": True,
            "has_login_field": True,
            "has_csrf_token": True,
        },
        "observed": {
            "has_password": has_password,
            "has_login": has_login,
            "has_csrf": has_csrf,
            "body_len": len(text),
        },
    }


def _check_static_asset(base: str, host_header: str, asset_path: str) -> dict[str, Any]:
    status, headers, body = _bounded_request(f"{base}{asset_path}", host_header)
    return {
        "path": asset_path,
        "status": status,
        "contract_ok": status == 200 and len(body) > 0,
        "expected": {"status": 200, "body_len_gt": 0},
        "observed": {"body_len": len(body)},
    }


def run_smoke(base: str, host_header: str, manifest_path: Path) -> dict[str, Any]:
    """Run all bounded smoke probes. Return a structured report."""
    if not manifest_path.is_file():
        return {"contract_ok": False, "reason": f"manifest not found: {manifest_path}"}
    try:
        manifest = json.loads(manifest_path.read_text())
    except (ValueError, OSError) as exc:
        return {"contract_ok": False, "reason": f"manifest unreadable: {exc}"}
    expected_commit = manifest.get("git_commit", "")
    # The /health/ contract uses the key "build_id" (not "app_build_id"
    # which is the manifest's filename-friendly form). We compare to
    # whichever the contract returns.
    expected_build_id = manifest.get("app_build_id", "")

    checks: list[dict[str, Any]] = []
    checks.append(_check_health(base, host_header, expected_commit, expected_build_id))
    checks.append(_check_redirect_same_origin(
        base, host_header, "/login/", "/accounts/login/"))
    checks.append(_check_login_form(base, host_header))
    checks.append(_check_redirect_same_origin(
        base, host_header, "/review/", "/accounts/login/",
        expected_query={"next": "/review/"}))
    checks.append(_check_readiness(base, host_header, expected_commit, expected_build_id))
    for asset in (
        "/static/portal/htmx-1.9.10.min.js",
        "/static/portal/tailwind-2.2.19.min.css",
    ):
        checks.append(_check_static_asset(base, host_header, asset))

    contract_ok = all(c["contract_ok"] for c in checks)
    return {
        "contract_ok": contract_ok,
        "expected_commit": expected_commit,
        "expected_build_id": expected_build_id,
        "base": base,
        "host_header": host_header,
        "checks": checks,
    }


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: smoke_probe.py BASE HOST_HEADER MANIFEST_PATH", file=sys.stderr)
        return 2
    base = sys.argv[1].rstrip("/")
    host_header = sys.argv[2]
    manifest_path = Path(sys.argv[3])
    report = run_smoke(base, host_header, manifest_path)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("contract_ok") else 6


if __name__ == "__main__":
    raise SystemExit(main())
