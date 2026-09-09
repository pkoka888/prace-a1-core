"""The HTTP check must reject accidental anonymous access, not follow it away."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from scripts.playwright_smoke import run_checks


@contextmanager
def server(review_status=302, destination="/login/?next=/review/", body=b""):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.path == "/review/":
                self.send_response(review_status)
                self.send_header("Location", destination)
                response_body = body
            elif self.path.startswith("/login/"):
                self.send_response(302)
                self.send_header("Location", "/accounts/login/")
                response_body = b""
            else:
                self.send_response(200)
                response_body = b'<form><input name="login"><input name="password"></form>'
            self.end_headers()
            self.wfile.write(response_body)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join()


def test_precise_login_redirect_passes():
    with server() as base:
        assert all(check["status"] == "PASS" for check in run_checks(base).values())


@pytest.mark.parametrize("status,destination,body", [
    (200, "", b"private review"),
    (302, "https://example.invalid/accounts/login/?next=/review/", b""),
    (302, "/workers/", b""),
    (302, "/login/?next=/wrong/", b""),
    (302, "/login/?next=/review/", b"private review"),
])
def test_anonymous_leak_or_wrong_redirect_fails(status, destination, body):
    with server(status, destination, body) as base:
        assert run_checks(base)["protected_content_absent"]["status"] == "FAIL"
