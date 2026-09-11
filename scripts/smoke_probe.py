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
                    connect_timeout: float = 2.0, read_timeout: float = 5.0):
    """One bounded request. Returns (status, headers, body, content_type).

    No automatic redirect follow; no cookie jar. Read timeout applies
    to the body read; connect timeout applies to the TCP connect.
    """
    request = urllib.request.Request(url, method=method)
    request.add_header("Host", host_header)
    opener = urllib.request.build_opener(
        NoRedirect,
        urllib.request.ProxyHandler({}),
    )
    try:
        response = opener.open(url, timeout=read_timeout)
        raw = response.read(1_000_000)
        status = response.status
        headers = response.headers
    except urllib.error.HTTPError as exc:
        raw = exc.read(1_000_000) if hasattr(exc, "read") else b""
        status = exc.code
        headers = exc.headers
    return status, headers, raw


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
