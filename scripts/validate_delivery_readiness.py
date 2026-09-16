#!/usr/bin/env python3
"""Bounded delivery diagnostics, not deployment or operator acceptance.

Never reads the service EnvironmentFile, password verifiers or service logs.
Exit 0: selected checks passed; 1: observed failure; 2: incomplete evidence/usage.
Full diagnostics retain an explicit unresolved logging-delivery check. Use
--source-only for the independent browser-wait source guard.
"""
from __future__ import annotations

import argparse
from http.client import HTTPException
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import smoke_probe

UNIT = "prace-v-nemecku-gunicorn.service"
SERVICE_ENV = "/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env"
SCAN_PATHS = (
    "tests/_rehearse_workflow_browser.py", "tests/document_web",
    "scripts/axe_check.sh", "scripts/smoke_synthetic_review_ui.mjs",
    "scripts/playwright_smoke.py",
)
WAIT_PATTERN = (
    r"\b(?:wait_until|waitUntil)\s*[:=]\s*['\"]networkidle['\"]"
    r"|\b(?:wait_for_load_state|waitForLoadState)\s*\(\s*['\"]networkidle['\"]"
)


def result(check, status, reason, **details):
    return {"check": check, "status": status, "reason": reason, **details}


def bounded_command(argv, *, root=ROOT):
    # No inherited credentials, shell, startup files, pager or interactive input.
    try:
        process = subprocess.run(
            argv, cwd=root, env={"PATH": os.defpath, "LC_ALL": "C", "SYSTEMD_PAGER": ""},
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=8, check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "", "timeout"
    except OSError:
        return None, "", "tool_unavailable"
    # Callers interpret native status; never print raw stderr or source lines.
    return process.returncode, process.stdout, ""


def scan_browser_waits(root=ROOT):
    for relative in SCAN_PATHS:
        path = root / relative
        if not path.exists() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            return result("browser_wait_source", "blocked", "required_source_missing_or_unsafe")
    # Resolve the operator's installed rg before clearing the child environment.
    # No privilege escalation: this uses the same tool selection as their shell.
    executable = shutil.which("rg")
    if not executable:
        return result("browser_wait_source", "blocked", "tool_unavailable", native_exit=None)
    code, output, error = bounded_command(
        [str(Path(executable).resolve()), "--files-with-matches", "--multiline", "--no-ignore", "--glob", "*.py",
         "--glob", "*.js", "--glob", "*.mjs", "--glob", "*.sh", "--", WAIT_PATTERN,
         *SCAN_PATHS], root=root,
    )
    if error or code not in (0, 1):
        return result("browser_wait_source", "blocked", error or "scan_error", native_exit=code)
    if code == 0:
        return result("browser_wait_source", "failed", "forbidden_wait_found", native_exit=code)
    if output.strip():
        return result("browser_wait_source", "blocked", "inconsistent_scan_result", native_exit=code)
    return result("browser_wait_source", "passed", "reviewed_paths_scanned", native_exit=code)


def unit_checks():
    properties = ("LoadState", "ActiveState", "SubState", "MainPID", "EnvironmentFiles",
                  "NeedDaemonReload", "StandardOutput", "StandardError")
    code, output, error = bounded_command(
        ["systemctl", "show", UNIT, "--no-pager", "--property=" + ",".join(properties)],
    )
    if error or code != 0:
        return [result("selected_unit", "blocked", error or "unit_query_failed", native_exit=code)]
    parsed = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in properties:
            if key in parsed:
                return [result("selected_unit", "blocked", "duplicate_unit_property")]
            parsed[key] = value
    if set(parsed) != set(properties) or not parsed["MainPID"].isdigit():
        return [result("selected_unit", "blocked", "incomplete_unit_properties")]
    active = (parsed["LoadState"] == "loaded" and parsed["ActiveState"] == "active"
              and parsed["SubState"] == "running" and int(parsed["MainPID"]) > 0)
    # Compare loaded metadata only. No stat/open/hash of the EnvironmentFile.
    bound = (parsed["EnvironmentFiles"] == SERVICE_ENV + " (ignore_errors=no)"
             and parsed["NeedDaemonReload"] == "no")
    return [
        result("selected_unit", "passed" if active else "failed",
               "active_process" if active else "unit_not_running", native_exit=code),
        result("environment_file_binding", "passed" if bound else "failed",
               "loaded_path_matches" if bound else "loaded_path_or_reload_mismatch"),
    ]


def asset_contract(base, host_header, path, mime_types, marker):
    status, headers, body = smoke_probe._bounded_request(base + path, host_header)
    mime = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    html = body.lstrip().lower().startswith((b"<!doctype html", b"<html"))
    return {"contract_ok": status == 200 and mime in mime_types and marker in body and not html}


def endpoint_checks(base, host_header, commit, build_id):
    checks = []
    requests = [
        ("health_identity", smoke_probe._check_health, (base, host_header, commit, build_id)),
        ("runtime_readiness", smoke_probe._check_readiness, (base, host_header, commit, build_id)),
        ("static_js_mime_signature", asset_contract,
         (base, host_header, "/static/portal/htmx-1.9.10.min.js",
          {"application/javascript", "text/javascript"}, b"htmx")),
        ("static_css_mime_signature", asset_contract,
         (base, host_header, "/static/portal/tailwind-2.2.19.min.css",
          {"text/css"}, b"tailwindcss")),
    ]
    for name, function, arguments in requests:
        try:
            observed = function(*arguments)
        except (OSError, ValueError, HTTPException):
            checks.append(result(name, "blocked", "bounded_probe_unavailable"))
            continue
        passed = observed.get("contract_ok") is True
        checks.append(result(name, "passed" if passed else "failed",
                             "endpoint_contract" if passed else "endpoint_contract_mismatch"))
    # Suppress response bodies, cookies, endpoint error text and arbitrary values.
    return checks


def summarize(checks, scope):
    counts = {status: sum(check["status"] == status for check in checks)
              for status in ("passed", "failed", "blocked")}
    if not checks or sum(counts.values()) != len(checks):
        raise ValueError("invalid diagnostic coverage")
    status = "failed" if counts["failed"] else "blocked" if counts["blocked"] else "passed"
    return {"schema_version": 1, "scope": scope, "status": status, "counts": counts,
            "checks": checks, "deployment_acceptance": False, "operator_acceptance": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true", help="no host or HTTP checks")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001",
                        help="numeric HTTP(S) origin; avoids unbounded DNS resolution")
    parser.add_argument("--host-header", default="prace-v-nemecku.expc.cz")
    parser.add_argument("--expected-commit", help="independently selected release; never inferred from HTTP")
    parser.add_argument("--expected-build-id")
    args = parser.parse_args(argv)
    if bool(args.expected_commit) != bool(args.expected_build_id):
        parser.error("supply both expected release identities")
    if args.expected_commit and not re.fullmatch(r"[0-9a-f]{40}", args.expected_commit):
        parser.error("expected commit must be a full lowercase Git SHA")
    if args.expected_build_id and not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", args.expected_build_id):
        parser.error("invalid expected build identifier")
    try:
        base = urlsplit(args.base_url)
        ipaddress.ip_address(base.hostname or "")
        valid_base = (base.scheme in {"http", "https"} and base.hostname and not base.username
                      and not base.password and base.path in {"", "/"}
                      and not base.query and not base.fragment and base.port != 0)
    except ValueError:
        valid_base = False
    if not valid_base or not re.fullmatch(r"[A-Za-z0-9.-]+(?::[0-9]+)?", args.host_header):
        parser.error("use a numeric HTTP(S) origin and a plain Host header")
    if args.source_only and args.expected_commit:
        parser.error("source-only mode does not consume release identities")
    checks = [scan_browser_waits()]
    scope = "source-only" if args.source_only else "delivery-diagnostics"
    if not args.source_only:
        checks.extend(unit_checks())
        if args.expected_commit:
            checks.extend(endpoint_checks(args.base_url.rstrip("/"), args.host_header,
                                          args.expected_commit, args.expected_build_id))
        else:
            checks.append(result("runtime_and_route", "blocked", "expected_release_identity_required"))
        checks.append(result("logging_delivery", "blocked", "infrastructure_log_delivery_evidence_required"))
    report = summarize(checks, scope)
    if not args.source_only:
        report["target"] = {"local_unit_host": socket.gethostname(), "unit": UNIT,
                            "origin": args.base_url.rstrip("/"), "host_header": args.host_header,
                            "expected_commit": args.expected_commit, "expected_build_id": args.expected_build_id}
        report["not_proven"] = ["unit_to_http_listener_ownership", "asset_byte_identity",
                                "independent_database_role_tls", "logging_delivery",
                                "authenticated_core_workflow", "restart_persistence", "backup_restore"]
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        for check in checks:
            print(f"{check['status'].upper()} {check['check']}: {check['reason']}")
        print(f"RESULT: {report['status'].upper()} ({scope}); deployment acceptance not established")
    return {"passed": 0, "failed": 1, "blocked": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
