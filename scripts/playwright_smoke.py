#!/usr/bin/env python3
"""HTTP authorization probe and entrypoint for isolated real Chromium tests.

HTTP checks are reported separately from browser checks. The executable delegates
startup/cleanup to Django's isolated test server; it never starts verification DB.
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8743"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def run_checks(base_url: str = BASE_URL) -> dict:
    """Require the precise anonymous redirect and final login destination.

    No cookie jar is used. Open review HTML is always a failure, never interpreted
    as an authenticated session. A bounded redirect chain may contain /login/.
    """
    results = {name: {"status": "NOT_RUN"} for name in (
        "login_page_200", "review_redirects_to_login", "protected_content_absent")}
    opener = urllib.request.build_opener(NoRedirect, urllib.request.ProxyHandler({}))
    def get(path):
        try:
            response = opener.open(base_url + path, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, response.read(1_000_000)
    try:
        status, _, login = get("/accounts/login/")
        login_form = b'name="password"' in login and b'name="login"' in login
        results["login_page_200"] = {"status": "PASS" if status == 200 and login_form else "FAIL"}
        status, headers, body = get("/review/")
        location = urllib.parse.urlsplit(urllib.parse.urljoin(base_url + "/review/", headers.get("Location", "")))
        origin = urllib.parse.urlsplit(base_url)
        target_valid = (location.scheme, location.netloc) == (origin.scheme, origin.netloc) and location.path in ("/login/", "/accounts/login/")
        next_valid = urllib.parse.parse_qs(location.query).get("next") == ["/review/"]
        redirect_valid = status == 302 and target_valid and next_valid
        if redirect_valid:
            final_status, final_headers, final_body = get(location.path + "?" + location.query)
            if location.path == "/login/":
                redirect_valid = final_status == 302 and final_headers.get("Location") == "/accounts/login/"
                final_status, _, final_body = get("/accounts/login/")
            redirect_valid = redirect_valid and final_status == 200 and b'name="password"' in final_body and b'name="login"' in final_body
        results["review_redirects_to_login"] = {"status": "PASS" if redirect_valid else "FAIL"}
        # A redirect response must not itself contain protected HTML.
        results["protected_content_absent"] = {"status": "PASS" if redirect_valid and not body.strip() else "FAIL"}
    except Exception:
        for value in results.values():
            if value["status"] == "NOT_RUN":
                value.update(status="FAIL", reason="HTTP_PROBE_FAILED")
    return results


def main() -> int:
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "portal.settings_browser_tests"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.call([
        str(ROOT / "venv/bin/python"), "-m", "django", "test",
        "tests.document_web.test_browser_journey", "--noinput", "-v", "1",
    ], cwd=ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
