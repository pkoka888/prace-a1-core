"""Real Chromium against an isolated live Django server; no existing accounts.

Run only through portal.settings_browser_tests. No screenshots/traces/storage
state or raw browser exceptions are captured. Network routes allow loopback only;
run under an isolated network namespace for OS-level outbound denial as well.
"""
import os
import logging
import re
import secrets
import time
import threading
from unittest import skipUnless
from datetime import date
from urllib.parse import urlsplit

from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret, hotp_value, format_hotp_value
from portal.release1a.models import Organization, Membership, Worker, Document
from scripts.playwright_smoke import run_checks


@skipUnless(os.environ.get("DJANGO_SETTINGS_MODULE") == "portal.settings_browser_tests", "Run scripts/playwright_smoke.py with isolated browser settings")
class BrowserJourneyTests(StaticLiveServerTestCase):
    host = "127.0.0.1"

    @classmethod
    def setUpClass(cls):
        if os.environ.get("DJANGO_SETTINGS_MODULE") != "portal.settings_browser_tests":
            raise RuntimeError("BROWSER_TEST_REQUIRES_ISOLATED_SETTINGS")
        super().setUpClass()

    def setUp(self):
        previous_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, previous_logging)
        self.pwd = secrets.token_urlsafe(24)
        self.user = get_user_model().objects.create_user("synthetic-browser", password=self.pwd)
        EmailAddress.objects.create(user=self.user, email="synthetic-browser@example.invalid", primary=True, verified=True)
        self.secret = generate_totp_secret()
        TOTP.activate(self.user, self.secret)
        alpha = Organization.objects.create(key="browser-alpha", label="Synthetic Alpha")
        beta = Organization.objects.create(key="browser-beta", label="Synthetic Beta")
        Membership.objects.create(user=self.user, organization=alpha, role="jan_planner")
        self.own = Worker.objects.create(organization=alpha, given_name="Synthetic", family_name="VisibleBrowserWorker", birth_date=date(1990, 1, 2), activity_profile="employee")
        self.foreign_document = Document.objects.create(organization=beta, opaque_key="documents/" + secrets.token_hex(16) + ".source", sha256="b" * 64, content_type="image/png")
        self.other = Worker.objects.create(organization=beta, given_name="Synthetic", family_name="OtherBrowserWorker", birth_date=date(1990, 1, 2), activity_profile="employee")

    def start_ocr_worker(self):
        # Test-owned sequential consumer; HTTP still persists the actual job.
        # The rehearsal suite separately exercises the worker subprocess.
        from django.db import close_old_connections, connections
        from portal.release1a.document_intake import process_pending
        stop = threading.Event()
        errors = []
        actor_pk, org_pk = self.user.pk, self.own.organization_id
        def consume():
            try:
                while not stop.is_set():
                    close_old_connections()
                    actor = get_user_model().objects.get(pk=actor_pk)
                    org = Organization.objects.get(pk=org_pk)
                    process_pending(actor, org)
                    stop.wait(0.2)
            except Exception:
                errors.append("OCR_TEST_WORKER_FAILED")
            finally:
                connections.close_all()
        worker = threading.Thread(target=consume, name="synthetic-test-ocr")
        worker.start()
        def cleanup():
            stop.set()
            worker.join(timeout=90)
            self.assertFalse(worker.is_alive(), "OCR_TEST_WORKER_STOP_TIMEOUT")
            self.assertFalse(errors, "OCR_TEST_WORKER_FAILED")
        self.addCleanup(cleanup)
        return errors

    def test_desktop_mobile_totp_org_isolation_logout(self):
        from playwright.sync_api import sync_playwright, expect
        worker_errors = self.start_ocr_worker()
        from unittest import mock
        from pathlib import Path
        self.assertTrue(all(item["status"] == "PASS" for item in run_checks(self.live_server_url).values()), "HTTP_AUTHORIZATION_CONTRACT")
        # Route browser profile and subprocess temporary files to this disposable
        # project-owned test root. No persistent browser authentication is saved.
        with mock.patch.dict(os.environ, {"TMPDIR": str(Path(settings.DOCUMENT_STORAGE_ROOT).parent)}):
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="cs-CZ", service_workers="block")
                errors = []
                blocked = []
                origin = urlsplit(self.live_server_url)
                def route(request):
                    target = urlsplit(request.request.url)
                    if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
                        request.continue_()
                    else:
                        blocked.append("EXTERNAL_REQUEST")
                        request.abort()
                context.route("**/*", route)
                page = context.new_page()
                def response_status(response):
                    if response.status >= 400:
                        allowed = {'documents', 'workers', 'crop', 'crops', 'original', 'enhanced', 'static', 'portal', 'review', 'health', 'readiness', 'favicon.ico'}
                        route = "_".join(part if part in allowed else "id" for part in urlsplit(response.url).path.split('/') if part)
                        errors.append("HTTP_" + str(response.status) + "_" + route)
                page.on("response", response_status)
                from django.core.signals import got_request_exception
                def server_exception(sender, **kwargs):
                    import sys
                    kind, error, trace = sys.exc_info()
                    cause = getattr(error, "__cause__", None)
                    sqlite_code = getattr(cause, "sqlite_errorname", "")
                    if sqlite_code in {"SQLITE_BUSY", "SQLITE_LOCKED", "SQLITE_BUSY_SNAPSHOT"}:
                        errors.append(sqlite_code)
                    while trace and trace.tb_next:
                        trace = trace.tb_next
                    errors.append('SERVER_' + (kind.__name__ if kind else 'unknown') + '_' + (trace.tb_frame.f_code.co_name if trace else 'unknown'))
                got_request_exception.connect(server_exception, weak=False)
                self.addCleanup(lambda: got_request_exception.disconnect(server_exception))
                page.on("pageerror", lambda _: errors.append("PAGE_ERROR"))
                page.on("console", lambda message: errors.append("CONSOLE_ERROR") if message.type == "error" else None)
                page.set_default_timeout(12000)
                stage = "HEALTH"
                try:
                    health = context.request.get(self.live_server_url + "/health/").json()
                    stage = "HEALTH_STATUS"
                    self.assertEqual(health["status"], "synthetic-m2")
                    stage = "HEALTH_REAL_DATA"
                    self.assertIs(health["real_data"], False)
                    stage = "HEALTH_SUPERVISED"
                    self.assertIs(health["supervised"], False)
                    stage = "HEALTH_MODE"
                    self.assertEqual(health["mode"], "settings_browser_tests")
                    stage = "READINESS"
                    ready_response = context.request.get(self.live_server_url + "/readiness/")
                    if ready_response.status != 200:
                        stage = "READINESS_" + "_".join(c["name"] for c in ready_response.json().get("checks", []) if c["status"] != "ok")
                    self.assertEqual(ready_response.status, 200)
                    stage = "LOGIN"
                    page.goto(self.live_server_url + "/review/")
                    self.assertEqual(urlsplit(page.url).path, "/accounts/login/")
                    self.assertEqual(page.locator('a[href*="signup"]').count(), 0)
                    stage = "LOGIN_FORM"
                    page.locator('input[name="login"]').fill(self.user.username)
                    page.locator('input[name="password"]').fill(self.pwd)
                    page.locator('button[type="submit"]').click()
                    stage = "TOTP_REDIRECT"
                    page.wait_for_url("**/accounts/2fa/authenticate/**")
                    code = format_hotp_value(hotp_value(self.secret, int(time.time()) // 30))
                    page.locator('input[name="code"]').fill(code)
                    page.locator('button[type="submit"]').click()
                    stage = "TOTP_CONFIRM"
                    page.wait_for_url("**/review/**")
                    stage = "LAYOUT"
                    for width, height in ((1440, 1000), (390, 844)):
                        page.set_viewport_size({"width": width, "height": height})
                        page.goto(self.live_server_url + "/review/")
                        self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"), "REVIEW_HORIZONTAL_OVERFLOW")
                        page.goto(self.live_server_url + "/workers/")
                        self.assertIn("VisibleBrowserWorker", page.locator("body").inner_text())
                        self.assertNotIn("OtherBrowserWorker", page.locator("body").inner_text())
                    stage = "UPLOAD"
                    from tests.test_document_core.helpers import OP, card, png
                    source = png(card(OP))
                    page.goto(self.live_server_url + "/documents/intake/")
                    page.locator('input[name="file1"]').set_input_files({"name": "synthetic.png", "mimeType": "image/png", "buffer": source})
                    page.get_by_role("button", name="Nahrát a rozpoznat").click()
                    stage = "UPLOAD_REDIRECT"
                    if urlsplit(page.url).path == "/documents/intake/":
                        raise AssertionError("UPLOAD_NOT_REDIRECTED_ALERTS_" + str(page.locator('[role="alert"]').count()) + "_FORM_ERRORS_" + str(page.locator('.errorlist').count()))
                    page.wait_for_url(re.compile(r"/documents/\d+/$"))
                    document_id = int(urlsplit(page.url).path.strip("/").split("/")[1])
                    stage = "OCR_COMPLETION"
                    deadline = time.monotonic() + 90
                    while True:
                        status = page.locator("[data-ocr-state]").get_attribute("data-ocr-state")
                        if status == "completed":
                            break
                        self.assertNotEqual(status, "failed", "OCR_PROCESSING_FAILED")
                        self.assertFalse(worker_errors, "OCR_WORKER_FAILED")
                        if time.monotonic() >= deadline:
                            raise AssertionError("OCR_PROCESSING_TIMEOUT_" + str(status))
                        time.sleep(0.25)  # Bounded observation interval, not a completion assumption.
                        page.get_by_role("link", name="Obnovit stav").click(timeout=5000)
                    review_url = reverse("ocr_field_review", kwargs={"document_pk": document_id})
                    self.assertEqual(page.goto(self.live_server_url + review_url).status, 200, "OCR_REVIEW_ROUTE")
                    stage = "ASSOCIATION"
                    page.locator('input[name="reason"]').fill("Synthetic test association")
                    option_value = page.locator(f'select[name="worker_choice"] option[data-worker-pk="{self.own.pk}"]').get_attribute("value")
                    page.locator('select[name="worker_choice"]').select_option(option_value)
                    with page.expect_navigation(wait_until="load"):
                        page.get_by_role("button", name="Přiřadit tento dokument").click()
                    # Confirm one explicit synthetic field through the real UI;
                    # other OCR proposals remain unaccepted.
                    stage = "FIELD"
                    given = page.locator('input[name^="value_given_name_"]')
                    expect(given).to_have_count(1)
                    self.assertEqual(given.input_value(), "ALFA", "OCR_EXACT_SYNTHETIC_FIELD")
                    field_id = given.get_attribute("name").rsplit("_", 1)[1]
                    page.locator(f'input[name="confirm_{field_id}"]').check()
                    stage = "CONFIRM"
                    with page.expect_navigation(wait_until="load"):
                        page.get_by_role("button", name="Potvrdit vybrané údaje").click()
                    expect(page.locator('input[name^="value_given_name_"]')).to_have_count(0)
                    source_response = context.request.get(self.live_server_url + f"/documents/{document_id}/download/")
                    stage = "DOWNLOAD_HTTP_" + str(source_response.status)
                    self.assertEqual(source_response.status, 200)
                    self.assertEqual(source_response.body(), source)
                    stage = "DOWNLOAD"
                    with page.expect_download() as download_event:
                        page.get_by_role("link", name="Stáhnout původní soubor").click()
                    download = download_event.value
                    stage = "DOWNLOAD_BYTES"
                    self.assertEqual(Path(download.path()).read_bytes(), source, "ORIGINAL_BYTES_PRESERVED")
                    stage = "CONSOLE_" + "_".join(errors)
                    self.assertFalse(errors, "BROWSER_CONSOLE_OR_PAGE_ERROR")
                    stage = "PROTECTED_DENIALS"
                    denied = context.request.get(self.live_server_url + f"/documents/{self.foreign_document.pk}/download/")
                    self.assertEqual(denied.status, 404)
                    # Expected HTTP 404 emits browser network console error; check
                    # UI error cleanliness before these intentional denial probes.
                    response = page.goto(self.live_server_url + f"/workers/{self.other.pk}/")
                    self.assertEqual(response.status, 404)
                    self.assertNotIn("OtherBrowserWorker", page.locator("body").inner_text())
                    page.goto(self.live_server_url + "/accounts/logout/")
                    page.locator('button[type="submit"]').click()
                    page.goto(self.live_server_url + "/review/")
                    self.assertEqual(urlsplit(page.url).path, "/accounts/login/")
                    anonymous_download = context.request.get(self.live_server_url + f"/documents/{document_id}/download/", max_redirects=0)
                    self.assertEqual(anonymous_download.status, 302)
                    self.assertTrue(anonymous_download.headers["location"].startswith("/login/?next="))
                    self.assertFalse(blocked, "UNEXPECTED_EXTERNAL_RESOURCE")
                except Exception as exc:
                    # Playwright errors include DOM excerpts and filled values.
                    raise AssertionError("SYNTHETIC_BROWSER_JOURNEY_FAILED_" + stage + "_" + type(exc).__name__ + "_" + "_".join(errors)) from None
                finally:
                    context.close()
                    browser.close()
