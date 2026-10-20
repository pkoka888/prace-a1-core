"""Debug the browser test OCR polling.

Scratch diagnostic, not a regression guard: the polling loop prints its state
and never asserts, so the test cannot fail on a broken OCR path. It launches a
real Chromium and sleeps up to 60 s, which put it in every directory-level
sweep of ``tests/document_web``.

It therefore stays opt-in. Run it explicitly with::

    A1_BROWSER_DEBUG=1 venv/bin/python -m pytest tests/document_web/test_browser_debug5.py
"""

import os
import time
import re
import secrets
import unittest
from datetime import date
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import (
    TOTP,
    generate_totp_secret,
    hotp_value,
    format_hotp_value,
)
from portal.release1a.models import Organization, Membership, Worker


@unittest.skipUnless(
    os.environ.get("A1_BROWSER_DEBUG"),
    "scratch OCR-polling diagnostic; set A1_BROWSER_DEBUG=1 to run",
)
class DebugOCRTest(StaticLiveServerTestCase):
    host = "127.0.0.1"

    def setUp(self):
        self.pwd = secrets.token_urlsafe(24)
        self.user = get_user_model().objects.create_user(
            "debug-ocr-" + str(time.time()), password=self.pwd
        )
        EmailAddress.objects.create(
            user=self.user, email="debug@example.invalid", primary=True, verified=True
        )
        self.secret = generate_totp_secret()
        TOTP.activate(self.user, self.secret)
        alpha = Organization.objects.create(key="debug-ocr-org", label="Debug OCR")
        Membership.objects.create(
            user=self.user, organization=alpha, role="jan_planner"
        )
        self.own = Worker.objects.create(
            organization=alpha,
            given_name="Debug",
            family_name="Worker",
            birth_date=date(1990, 1, 2),
            activity_profile="employee",
        )

    def test_debug_ocr_polling(self):
        from playwright.sync_api import sync_playwright
        from tests.test_document_core.helpers import OP, card, png

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                locale="cs-CZ",
                service_workers="block",
            )
            page = context.new_page()
            page.set_default_timeout(12000)

            # Login
            page.goto(self.live_server_url + "/review/")
            page.locator('input[name="login"]').fill(self.user.username)
            page.locator('input[name="password"]').fill(self.pwd)
            page.locator('button[type="submit"]').click()
            page.wait_for_url("**/accounts/2fa/authenticate/**")
            code = format_hotp_value(hotp_value(self.secret, int(time.time()) // 30))
            page.locator('input[name="code"]').fill(code)
            page.locator('button[type="submit"]').click()
            page.wait_for_url("**/review/**")

            # Upload
            source = png(card(OP))
            page.goto(self.live_server_url + "/documents/intake/")
            page.locator('input[name="file1"]').set_input_files(
                {"name": "debug.png", "mimeType": "image/png", "buffer": source}
            )
            page.get_by_role("button", name="Nahrát a rozpoznat").click()
            page.wait_for_load_state("load")
            page.wait_for_url(re.compile(r"/documents/\d+/$"), timeout=30000)
            document_id = int(urlsplit(page.url).path.strip("/").split("/")[1])
            print(f"Uploaded document_id={document_id}")

            # Poll for OCR completion
            for i in range(60):
                content = page.content()
                status_match = re.search(r"Stav zpracování: ([^<]+)", content)
                if status_match:
                    status = status_match.group(1)
                    print(f"Poll {i}: status={status}")
                    if "Dokončeno" in status or "completed" in content.lower():
                        print("OCR complete!")
                        break
                else:
                    print(f"Poll {i}: no status found")
                time.sleep(1)
            else:
                print("OCR timeout")
                print("Page content snippet:")
                print(content[:2000])

            browser.close()
