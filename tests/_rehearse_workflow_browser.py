#!/usr/bin/env python3
"""Real-browser authenticated workflow journey for the supervised rehearsal.

Drives a real headless Chromium against the gunicorn that
``scripts/rehearse_synthetic_site.sh start`` launches, with the
operator credentials written by ``provision`` and the supervised-
synthetic settings module loaded. The journey exercises the shipped
frontend end-to-end:

    login + TOTP -> create worker -> upload synthetic OP card
    -> confirm OCR proposals (family_name, given_name, birth_date,
       residence_address) -> confirm missing identity facts
       (birth_place, nationality, sex, insurance_number)
    -> confirm structured residence address (5 parts)
    -> create assignment -> prepare A1 case -> generate unverified
       A1 draft PDF -> download protected PDF

Every stage uses real HTTP requests with the operator's session
cookies. We never substitute service calls, force-login, inject
sessions, add helper-side role memberships, or modify the shipped
frontend. The browser's cookie jar is populated through the natural
allauth login form; the TOTP code is computed from the secret in
operator.json exactly as the operator would in a TOTP authenticator
app. The journey does not redirect through a TLS proxy: Chromium
treats loopback as potentially-trustworthy, so Secure cookies work
over plain HTTP locally.

The script prints a structured evidence document on stdout. The CLI
exit code is non-zero when any required stage fails. The same
outcome contract is reused by the pytest test in
``tests/test_rehearse_workflow.py``.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import json
import re
import secrets
import struct
import sys
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


REPO_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_TOTP_PERIOD = 30


# Stages whose failure must propagate as a non-zero exit through the CLI.
REQUIRED_STAGES = (
    "login_redirect",
    "login_authenticated",
    "totp_completed",
    "worker_created",
    "document_uploaded",
    "document_associated",
    "ocr_proposals_confirmed",
    "missing_identity_confirmed",
    "address_confirmed",
    "assignment_created",
    "a1_prepared",
    "a1_draft_generated",
    "a1_pdf_downloaded",
)


# Stages whose outcome documents an expected operation-specific block
# (e.g. sparse-input 44-field A1 contract) rather than a real failure.
EXPECTED_BLOCK_OUTCOMES = {
    "sparse_reserve_blocked",
}


def _hotp_token(secret: bytes, counter: int, digits: int = 6) -> str:
    msg = struct.pack(">Q", counter)
    digest = hmac.new(secret, msg, "sha1").digest()
    offset = digest[-1] & 0x0F
    code = (
        (digest[offset] & 0x7F) << 24
        | (digest[offset + 1] & 0xFF) << 16
        | (digest[offset + 2] & 0xFF) << 8
        | (digest[offset + 3] & 0xFF)
    )
    return str(code % (10 ** digits)).zfill(digits)


def _current_totp(secret_b32: str, at_unix: int | None = None,
                  period: int = SYSTEM_TOTP_PERIOD) -> str:
    pad = "=" * (-len(secret_b32) % 8)
    secret = base64.b32decode(secret_b32 + pad)
    counter = (at_unix if at_unix is not None else int(time.time())) // period
    return _hotp_token(secret, counter)


def _safe_origin(base: str) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(base)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"invalid base URL: {base!r}")
    return parsed.scheme, parsed.netloc


def _load_operator(runtime_root: Path) -> dict:
    path = runtime_root / "operator.json"
    if not path.is_file():
        raise SystemExit(f"FAIL: operator.json missing at {path}")
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise SystemExit(f"FAIL: {path} mode {oct(mode)} is not operator-only")
    try:
        payload = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise SystemExit(f"FAIL: {path} unreadable: {exc}") from exc
    for required in ("email", "password", "mfa", "organization_id"):
        if required not in payload:
            raise SystemExit(f"FAIL: operator.json missing {required}")
    return payload


def _wait_for_url(page, pattern, *, timeout_ms: int = 20000) -> None:
    try:
        page.wait_for_url(pattern, timeout=timeout_ms)
    except PWTimeout as exc:
        raise SystemExit(
            f"FAIL: navigation timeout waiting for {pattern}; current "
            f"url={page.url!r}, title={page.title()!r}") from exc


def _wait_networkidle(page, *, timeout_ms: int = 20000) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PWTimeout as exc:
        raise SystemExit(
            f"FAIL: networkidle timeout; current url={page.url!r}, "
            f"title={page.title()!r}") from exc


def _set_field(page, *, name: str, value: str) -> None:
    """Set a form input/select by name. Raises when the field is absent."""
    selector = (
        f'input[name="{name}"], select[name="{name}"], '
        f'textarea[name="{name}"]'
    )
    locator = page.locator(selector).first
    if locator.count() == 0:
        raise SystemExit(
            f"FAIL: form field {name!r} not present (url={page.url!r}, "
            f"selector={selector!r})")
    matched_name = locator.get_attribute("name")
    if matched_name != name:
        raise SystemExit(
            f"FAIL: selector for {name!r} matched an element with name="
            f"{matched_name!r} instead (url={page.url!r})")
    tag = locator.evaluate("el => el.tagName.toLowerCase()")
    if tag == "select":
        locator.select_option(value)
    else:
        input_type = (locator.get_attribute("type") or "").lower()
        if input_type == "checkbox":
            if value in ("on", "true", "1"):
                locator.check()
            else:
                locator.uncheck()
        elif input_type == "hidden":
            raise SystemExit(
                f"FAIL: form field {name!r} is a hidden input "
                f"(url={page.url!r})")
        else:
            locator.fill(value)
    readback = locator.input_value()
    if readback != value:
        raise SystemExit(
            f"FAIL: field {name!r} read back {readback!r} after fill, "
            f"expected {value!r} (url={page.url!r})")


def _submit_form(page, *, action: str | None = None,
                 submit_selector: str = 'button[type="submit"]') -> None:
    """Click a submit button on the page; let the form post naturally."""
    if action is not None:
        button = page.locator(
            f'button[name="action"][value="{action}"]').first
        if button.count() == 0:
            raise SystemExit(
                f"FAIL: submit button with name=action value={action!r} "
                f"not present (url={page.url!r})")
    else:
        button = page.locator(submit_selector).first
        if button.count() == 0:
            raise SystemExit(
                f"FAIL: submit button not present (url={page.url!r})")
    button.click()


def _stage_ok(stage: str, **payload) -> dict:
    """Build a successful stage entry without leaking secrets."""
    return {"stage": stage, "ok": True, **payload}


def _stage_fail(stage: str, *, reason: str, **payload) -> dict:
    """Build a failed stage entry without leaking secrets."""
    return {"stage": stage, "ok": False, "reason": reason, **payload}


def _synthesize_op_card(tmpdir: Path) -> Path:
    """Render a synthetic OP card with the residence_address label so the
    address review form appears after upload."""
    from tests.test_document_core.helpers import OP, card, png
    lines = list(OP) + [
        "TRVALY POBYT: Testovaci 12, 12345 Testov",
        f"NONCE: {secrets.token_hex(8)}",
    ]
    png_bytes = png(card(lines))
    path = tmpdir / f"synthetic-op-{secrets.token_hex(6)}.png"
    path.write_bytes(png_bytes)
    return path


def run_journey(base_url: str, runtime_root: Path, tmpdir: Path) -> dict:
    """Execute the full Delivery-1 acceptance journey in a real browser."""
    operator = _load_operator(runtime_root)
    password = operator["password"]
    secret_b32 = operator["mfa"]["secret"]
    evidence: dict = {
        "base_url": base_url,
        "operator_email": operator["email"],
        "organization_id": operator["organization_id"],
        "mfa": "enrolled",  # opaque reference, never the code itself
        "stages": {},
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, locale="cs-CZ",
            service_workers="block",
        )
        page = context.new_page()
        page.set_default_timeout(20000)

        try:
            # Stage 1: login. allauth renders a plain <form method="post">;
            # click the submit button. No HTMX neutralization, no form
            # attribute injection — the shipped frontend must accept the
            # real submit path.
            page.goto(base_url + "/review/", wait_until="domcontentloaded")
            _wait_for_url(page, "**/accounts/login/**")
            evidence["stages"]["login_redirect"] = _stage_ok(
                "login_redirect", url=page.url)

            page.locator('input[name="login"]').fill(operator["email"])
            page.locator('input[name="password"]').fill(password)
            page.locator('button[type="submit"]').click()
            _wait_for_url(page, "**/accounts/2fa/authenticate/**")
            evidence["stages"]["login_authenticated"] = _stage_ok(
                "login_authenticated", url=page.url)

            # Stage 2: TOTP. Compute the code right before submit so a
            # slow login (browser startup, navigation, screenshot work)
            # does not push it out of its 30-second window.
            code = _current_totp(secret_b32)
            page.locator('input[name="code"]').fill(code)
            page.locator('button[type="submit"]').click()
            _wait_for_url(page, re.compile(r"/review/?($|\?|#|/)"))
            evidence["stages"]["totp_completed"] = _stage_ok(
                "totp_completed", url=page.url)

            # Stage 3: create worker.
            page.goto(base_url + "/workers/new/",
                      wait_until="domcontentloaded")
            _set_field(page, name="family_name", value="Testerova")
            _set_field(page, name="given_name", value="Alfa")
            _set_field(page, name="birth_date", value="1990-03-15")
            _set_field(page, name="activity_profile", value="employee")
            _submit_form(page)
            try:
                page.wait_for_url(re.compile(r"/workers/\d+/$"), timeout=20000)
            except PWTimeout:
                body = page.evaluate(
                    "() => document.body && document.body.innerText.slice(0, 400)")
                raise SystemExit(
                    f"FAIL: worker create did not redirect; "
                    f"final url={page.url!r}, body={body!r}")
            worker_pk = int(re.search(r"/workers/(\d+)/", page.url).group(1))
            evidence["stages"]["worker_created"] = _stage_ok(
                "worker_created", worker_pk=worker_pk, url=page.url)

            # Stage 4: upload synthetic OP card with residence_address.
            page.goto(base_url + f"/workers/{worker_pk}/documents/upload/",
                      wait_until="domcontentloaded")
            png_path = _synthesize_op_card(tmpdir)
            page.locator('input[name="file"]').set_input_files(str(png_path))
            _submit_form(page)
            _wait_for_url(page, re.compile(r"/documents/\d+/$"))
            document_pk = int(re.search(
                r"/documents/(\d+)/", page.url).group(1))
            evidence["stages"]["document_uploaded"] = _stage_ok(
                "document_uploaded", document_pk=document_pk, url=page.url)

            # Stage 5: document detail page. The upload sets
            # Document.worker, but the per-region DocumentRegionAssociation
            # is created only when the operator submits the association
            # form on this page. OCR proposals are only rendered when
            # the association_record exists. Until then the page shows
            # the worker dropdown and the "Přiřadit tento dokument"
            # button. We submit the association explicitly so the
            # journey exercises the real path.
            page.goto(base_url + f"/documents/{document_pk}/",
                      wait_until="networkidle")
            worker_choice = page.locator('select[name="worker_choice"]')
            if worker_choice.count() > 0:
                options = worker_choice.evaluate(
                    """el => Array.from(el.options).map(
                        o => ({token: o.value,
                              text: o.textContent.trim(),
                              workerPk: o.dataset.workerPk || null}))""")
                match = next(
                    (o for o in options if o.get("workerPk")
                     and int(o["workerPk"]) == worker_pk),
                    None)
                if match is None:
                    raise SystemExit(
                        f"FAIL: worker_pk={worker_pk} not in association "
                        f"options: {options!r}")
                worker_choice.select_option(match["token"])
                # The OCR engine did not propose this worker (no prior
                # associations exist on a fresh synthetic OP), so
                # resolve_identity_evaluation requires a non-empty
                # override reason. The association is explicit; the
                # reason is documented as a synthetic rehearsal note.
                reason_input = page.locator('input[name="reason"]')
                if reason_input.count() > 0 and not reason_input.input_value():
                    reason_input.fill(
                        "synthetic rehearsal: worker bound to upload")
                _submit_form(page, action="associate")
                page.wait_for_load_state("networkidle")
            # The association submit redirects back; verify the worker
            # name now appears in the page body so a 500 or wrong
            # submit cannot pass.
            page.goto(base_url + f"/documents/{document_pk}/",
                      wait_until="networkidle")
            body_text = page.evaluate(
                "() => document.body && document.body.innerText")
            if not body_text or "Testerova" not in body_text \
                    or "Alfa" not in body_text:
                raise SystemExit(
                    f"FAIL: document detail page did not show the "
                    f"associated worker (url={page.url!r}, "
                    f"contains Testerova={'Testerova' in (body_text or '')}, "
                    f"contains Alfa={'Alfa' in (body_text or '')})")
            evidence["stages"]["document_associated"] = _stage_ok(
                "document_associated", url=page.url)

            # Stage 6: confirm OCR proposals. The synthetic OP card
            # produces family_name, given_name, birth_date and
            # residence_address proposals. We confirm them all in one
            # batch so the readiness gate moves forward.
            confirm_boxes = page.locator(
                'input[type="checkbox"][name^="confirm_"]')
            initial_count = confirm_boxes.count()
            if initial_count == 0:
                raise SystemExit(
                    f"FAIL: no OCR confirm checkboxes on document detail "
                    f"page (url={page.url!r}); the synthetic OP card is "
                    f"expected to yield at least family_name, given_name, "
                    f"birth_date, residence_address")
            # Capture every box name once so HTMX-driven re-renders do
            # not shift the index mid-loop.
            box_names = confirm_boxes.evaluate_all(
                "els => els.map(el => el.name)")
            for name in box_names:
                page.locator(
                    f'input[type="checkbox"][name="{name}"]').check()
            _submit_form(page, action="confirm")
            _wait_networkidle(page)
            page.reload(wait_until="domcontentloaded")
            remaining = page.locator(
                'input[type="checkbox"][name^="confirm_"]').count()
            if remaining >= initial_count:
                raise SystemExit(
                    f"FAIL: OCR proposals confirmation did not reduce "
                    f"checkbox count (was={initial_count}, now={remaining}); "
                    f"the form may have rejected the batch (url={page.url!r})")
            evidence["stages"]["ocr_proposals_confirmed"] = _stage_ok(
                "ocr_proposals_confirmed",
                confirmed=initial_count - remaining,
                url=page.url)

            # Stage 7: missing-identity form appears because the worker
            # is missing birth_place, nationality, sex and
            # insurance_number. Fill them through the missing-identity
            # form; the source/tokens come from server-rendered hidden
            # inputs.
            identity_inputs = page.locator(
                'input[name^="identity_"]:not([name="identity_source"])'
                ':not([name="identity_token"])')
            if identity_inputs.count() < 4:
                raise SystemExit(
                    f"FAIL: missing-identity form did not render the "
                    f"expected four inputs (count={identity_inputs.count()}, "
                    f"url={page.url!r})")
            for field, value in (
                ("identity_birth_place", "Praha"),
                ("identity_nationality", "CZ"),
                ("identity_sex", "F"),
                ("identity_insurance_number", "INS000001"),
            ):
                _set_field(page, name=field, value=value)
            _submit_form(page, action="confirm_missing_identity")
            _wait_networkidle(page)
            page.reload(wait_until="domcontentloaded")
            if page.locator(
                    'input[name^="identity_"]:not([name="identity_source"])'
                    ':not([name="identity_token"])').count() > 0:
                raise SystemExit(
                    f"FAIL: missing-identity form still rendered after "
                    f"confirmation (url={page.url!r})")
            evidence["stages"]["missing_identity_confirmed"] = _stage_ok(
                "missing_identity_confirmed", url=page.url)

            # Stage 8: address review form appears because the OP card
            # contains the residence_address label. Fill the five
            # structured parts. The form is rendered with confirmed
            # values after submission, so verify the persistence by
            # checking the inputs hold the values we submitted.
            expected_address = {
                "address_street": "Testovaci",
                "address_house_number": "12",
                "address_city": "Testov",
                "address_postal_code": "12345",
                "address_country_code": "CZ",
            }
            for field, value in expected_address.items():
                _set_field(page, name=field, value=value)
            _submit_form(page, action="confirm_address")
            _wait_networkidle(page)
            page.reload(wait_until="domcontentloaded")
            actual_address = page.evaluate('''() => {
                const inputs = ['address_street', 'address_house_number',
                                'address_city', 'address_postal_code',
                                'address_country_code'];
                const out = {};
                for (const n of inputs) {
                    const el = document.querySelector(`[name="${n}"]`);
                    out[n] = el ? el.value : null;
                }
                return out;
            }''')
            missing = {k: v for k, v in expected_address.items()
                        if actual_address.get(k) != v}
            if missing:
                raise SystemExit(
                    f"FAIL: address review form did not persist the "
                    f"submitted values (missing={missing!r}, "
                    f"observed={actual_address!r}, url={page.url!r})")
            evidence["stages"]["address_confirmed"] = _stage_ok(
                "address_confirmed", url=page.url)

            # Stage 9: create assignment.
            page.goto(base_url + f"/workers/{worker_pk}/assignments/new/",
                      wait_until="domcontentloaded")
            _set_field(page, name="workplace_label",
                       value="Acme GmbH Mnichov")
            _set_field(page, name="activity_label",
                       value="Montážní práce")
            _set_field(page, name="start", value="2026-09-01")
            _set_field(page, name="end", value="2026-09-30")
            _submit_form(page)
            try:
                page.wait_for_url(re.compile(r"/workers/\d+/(?!.*assignments/new)"),
                                  timeout=20000)
            except PWTimeout:
                raise SystemExit(
                    f"FAIL: assignment create did not redirect "
                    f"(url={page.url!r})")
            evidence["stages"]["assignment_created"] = _stage_ok(
                "assignment_created", url=page.url)

            # Stage 9b: fill the assignment's pending A1 facts
            # (employment, activity, institution). The canonical
            # ``prepare_application_draft`` validator requires these
            # fields when ``status_profile != self_employed_multi_state``,
            # so a synthetic minimum keeps the worker-employee path
            # within policy. Without this step the A1 row stays
            # blocked on missing institution / employment facts and
            # the downstream render fails.
            # assignment_create redirects to /workers/<pk>/ so the URL
            # no longer carries the assignment pk. Discover the most
            # recent assignment for this worker from the
            # ``?tab=assignments`` listing — it shows an
            # ``assignment_edit`` link per row.
            page.goto(base_url + f"/workers/{worker_pk}/?tab=assignments",
                      wait_until="networkidle")
            detail_links = page.evaluate(
                """() => Array.from(
                    document.querySelectorAll(
                        'a[href*="/assignments/"][href$="/edit/"]'))
                    .map(a => a.href)""")
            apk_match = None
            for href in detail_links:
                m = re.search(r"/assignments/(\d+)/edit/", href)
                if m:
                    apk_match = m.group(1)
                    break
            if apk_match is None:
                raise SystemExit(
                    f"FAIL: could not discover the new assignment pk "
                    f"from worker detail links (url={page.url!r})")
            assignment_pk = int(apk_match)
            page.goto(base_url
                      + f"/workers/{worker_pk}/assignments/{assignment_pk}/a1-inputs/",
                      wait_until="networkidle")
            assignment_facts_values = {
                "status_profile": "employee_multi_state",
                "employment__employer_id": "12345678",
                "employment__employer_name": "Acme GmbH",
                "employment__street": "Pracovní",
                "employment__house_number": "1",
                "employment__city": "Mnichov",
                "employment__postal_code": "12345",
                "employment__country_code": "DE",
                "activity__name": "Montážní práce",
                "activity__address": "DE, CZ",
                "institution__resolved_ossz": "OSSZ Děčín",
            }
            # Pick the verifiable institution profile that matches the
            # resolved OSSZ above. ``validate_application_draft_row``
            # requires ``expected_ossz`` to equal ``resolved_ossz`` and
            # ``resolved_ossz`` to appear in the institution name, so
            # decin (OSSZ Děčín) satisfies both checks.
            page.locator(
                'select[name="institution__profile_key"]'
            ).select_option("decin")
            for field, value in assignment_facts_values.items():
                _set_field(page, name=field, value=value)
            _submit_form(page)
            page.wait_for_load_state("networkidle")
            chosen_profile = page.evaluate(
                """() => {
                    const sel = document.querySelector(
                        'select[name="institution__profile_key"]');
                    if (!sel || sel.selectedIndex < 0) return null;
                    return sel.options[sel.selectedIndex].value || null;
                }""")
            if chosen_profile != "decin":
                raise SystemExit(
                    f"FAIL: assignment facts did not keep the decin "
                    f"institution_profile (url={page.url!r})")
            evidence["stages"]["assignment_facts_saved"] = _stage_ok(
                "assignment_facts_saved",
                url=page.url, institution_profile=chosen_profile)

            # Stage 10: prepare A1 case. The /a1/prepare form posts
            # back to /a1/<pk>/ with confirm_prepare=on. The case is
            # ready (not blocked) only when identity, residence and
            # assignment are complete.
            page.goto(base_url + f"/workers/{worker_pk}/a1/prepare/",
                      wait_until="domcontentloaded")
            _set_field(page, name="confirm_prepare", value="on")
            _submit_form(page)
            _wait_for_url(page, re.compile(r"/a1/\d+/$"))
            case_pk = int(re.search(r"/a1/(\d+)/", page.url).group(1))
            body_text = page.evaluate(
                "() => document.body && document.body.innerText")
            if "blocked" in body_text.lower():
                raise SystemExit(
                    f"FAIL: A1 case detail shows blocked status; "
                    f"identity/residence/assignment facts are incomplete "
                    f"(url={page.url!r})")
            evidence["stages"]["a1_prepared"] = _stage_ok(
                "a1_prepared", case_pk=case_pk, url=page.url)

            # Stage 11: unverified A1 draft PDF. When the case is
            # prepared, ``prepare_a1`` already runs the canonical
            # ``prepare_application_draft`` path, so the detail page
            # usually exposes the protected PDF links immediately and
            # hides the "Vygenerovat PDF" form. If the auto render did
            # not complete, the form is shown instead and the operator
            # (here the journey) triggers the POST explicitly. Record
            # which path actually produced the artifact.
            generate_form = page.locator(
                'form[action$="/draft/generate/"]')
            generate_status = 200
            generate_mode = "prepared_auto"
            if generate_form.count():
                generate_mode = "operator_post"
                try:
                    with page.expect_response(
                            lambda r: r.url.endswith("/draft/generate/")
                            and r.request.method == "POST",
                            timeout=30000) as resp_info:
                        page.locator(
                            'form[action$="/draft/generate/"] '
                            'button[type="submit"]'
                        ).click()
                    generate_response = resp_info.value
                    generate_status = generate_response.status
                    generate_body = generate_response.body()[:300]
                except PWTimeout:
                    generate_status = 0
                    generate_body = b"(no response captured before timeout)"
                if generate_status != 200:
                    raise SystemExit(
                        f"FAIL: draft generate returned HTTP "
                        f"{generate_status}; body={generate_body!r} "
                        f"(url={page.url!r})")
            page.wait_for_load_state("networkidle")
            download_link = page.locator('a[href*="/artifact/"]').first
            if download_link.count() == 0:
                raise SystemExit(
                    f"FAIL: a1 artifact download link not visible after "
                    f"draft generation (url={page.url!r}, "
                    f"status={generate_status})")
            evidence["stages"]["a1_draft_generated"] = _stage_ok(
                "a1_draft_generated",
                url=page.url, http_status=generate_status,
                generation_mode=generate_mode)

            # Stage 12: download the protected PDF and verify it
            # begins with the %PDF- magic.
            with page.expect_download(timeout=20000) as event:
                download_link.click()
            download = event.value
            pdf_path = tmpdir / f"a1-{case_pk}-{secrets.token_hex(6)}.pdf"
            download.save_as(str(pdf_path))
            pdf_bytes = pdf_path.read_bytes()
            if pdf_bytes[:5] != b"%PDF-":
                raise SystemExit(
                    f"FAIL: downloaded artifact does not begin with %PDF- "
                    f"magic (size={len(pdf_bytes)}, path={pdf_path})")
            evidence["stages"]["a1_pdf_downloaded"] = _stage_ok(
                "a1_pdf_downloaded",
                path=str(pdf_path), size=len(pdf_bytes))

            evidence["worker_pk"] = worker_pk
            evidence["case_pk"] = case_pk
            evidence["document_pk"] = document_pk
        except SystemExit:
            raise
        except Exception as exc:
            evidence.setdefault("stages", {})["unexpected"] = _stage_fail(
                "unexpected",
                reason=f"{type(exc).__name__}: {exc}")
            raise SystemExit(f"FAIL: journey aborted: {exc}")
        finally:
            context.close()
            browser.close()

    required_failed = [
        name for name in REQUIRED_STAGES
        if not evidence["stages"].get(name, {}).get("ok")
    ]
    evidence["required_stages"] = list(REQUIRED_STAGES)
    evidence["ok"] = not required_failed
    if required_failed:
        evidence["failed_stages"] = required_failed
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True,
                        help="Gunicorn base URL (e.g. http://127.0.0.1:8001)")
    parser.add_argument("--runtime-root", type=Path, required=True,
                        help="Operator-owned runtime root with operator.json")
    parser.add_argument("--tmpdir", type=Path, required=True,
                        help="Private disposable directory for uploaded and "
                             "downloaded bytes; created if missing")
    args = parser.parse_args()
    args.tmpdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        evidence = run_journey(args.base_url, args.runtime_root, args.tmpdir)
    except SystemExit as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    # Required-stage failure must propagate as a non-zero exit. Sparse
    # cases are separate journeys that record their own blocked outcome
    # without being declared "ok".
    return 0 if evidence.get("ok") else 7


if __name__ == "__main__":
    raise SystemExit(main())