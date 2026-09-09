"""Synthetic pending-application contract and canonical renderer regression."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from scripts.a1_core import A1ValidationError, APPLICATION_DRAFT_NOTICE, validate_form_data
from scripts.finalize_a1 import CSV_FIELDS, FinalizationError, validate_application_draft_row, validate_review
from scripts.generate_provisional_a1 import render_application_draft


def pending_row():
    row = dict.fromkeys(CSV_FIELDS, "")
    row.update(employee_id="synthetic-application", surname="Zkouškový", given_name="Alex",
               dob="02.03.1991", birth_place="Testov", nationality="CZ", sex="M",
               insurance_number="910302/0000", street="Zkušební", house_number="12",
               city="Testov", postal_code="123 45", country_code="CZ",
               status_profile="self_employed_multi_state", activity_address="DE, CZ",
               employment_id="SYNTHETIC-001", employment_name="Zkouškový Alex",
               employment_street="Zkušební", employment_house_number="12", employment_city="Testov",
               employment_postal_code="123 45", employment_country_code="CZ", resolved_ossz="OSSZ Testov",
               institution_profile="synthetic", document_id="999/026/001/CZ",
               identity_reviewed="NO", certificate_reviewed="NO", approved_for_pdf="NO", validated_by_user="0")
    return row


def synthetic_profile():
    return {"review_status": "VERIFIED", "source_url": "https://example.invalid/synthetic-office",
            "verified_on": "01.01.2026", "expected_ossz": "OSSZ Testov",
            "institution": {"name": "OSSZ Testov", "street": "Testovací", "house_number": "2",
                            "city": "Testov", "postal_code": "123 45", "country_code": "CZ", "code": "999"}}


class ApplicationDraftTests(unittest.TestCase):
    def test_pending_mode_preserves_unknown_dates_and_flags(self):
        row = pending_row()
        original = deepcopy(row)
        form = validate_application_draft_row(row, synthetic_profile())
        self.assertEqual(row, original)
        self.assertTrue(form["meta"]["application_draft"])
        self.assertEqual(form["certificate"]["start_date"], "")
        self.assertEqual(form["institution"]["issue_date"], "")
        self.assertEqual(form["activity"], {"name": "", "address": "DE, CZ"})
        self.assertFalse(form["valid_duration"])
        form["meta"]["application_draft"] = False
        with self.assertRaises(A1ValidationError):
            validate_form_data(form)

    def test_default_review_still_requires_human_flags(self):
        row = pending_row()
        row["issue_date"] = "01.01.2026"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_text(json.dumps({"employees": [{"id": row["employee_id"]}]}))
            with self.assertRaisesRegex(FinalizationError, "identity_reviewed must be YES"):
                validate_review([row], source, root, provisional=True)

    def test_invalid_or_incomplete_inputs_rejected(self):
        for key, value in (("surname", ""), ("dob", "31.02.1991"), ("issue_date", "bad"),
                           ("sex", "X"), ("document_id", ""), ("employment_id", "")):
            with self.subTest(key=key):
                row = pending_row()
                row[key] = value
                with self.assertRaises(FinalizationError):
                    validate_application_draft_row(row, synthetic_profile())
        row = pending_row()
        row.update(start_date="02.01.2026", end_date="01.01.2026")
        with self.assertRaisesRegex(FinalizationError, "DATE_ORDER"):
            validate_application_draft_row(row, synthetic_profile())
        profile = synthetic_profile()
        profile["expected_ossz"] = "OSSZ Other"
        with self.assertRaisesRegex(FinalizationError, "INSTITUTION_MISMATCH"):
            validate_application_draft_row(pending_row(), profile)

    def test_office_code_stays_within_core_number_format(self):
        for code in ("0", "100000", "-1"):
            with self.subTest(code=code):
                profile = synthetic_profile()
                profile["institution"]["code"] = code
                with self.assertRaisesRegex(FinalizationError, "CODE_INVALID"):
                    validate_application_draft_row(pending_row(), profile)

    def test_three_page_notice_and_deterministic_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            first, checks = render_application_draft(pending_row(), synthetic_profile(), workspace)
            second, _ = render_application_draft(pending_row(), synthetic_profile(), workspace)
            self.assertEqual(first, second)
            self.assertEqual(list(workspace.iterdir()), [])
        self.assertTrue(checks["notice_on_all_pages"])
        self.assertEqual(checks["visual_review"], "pending")
        self.assertFalse(checks["issued"])
        pages = PdfReader(BytesIO(first)).pages
        self.assertEqual(len(pages), 3)
        self.assertTrue(all(APPLICATION_DRAFT_NOTICE in page.extract_text() for page in pages))

    def test_unprotected_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            workspace.chmod(0o755)
            with self.assertRaisesRegex(FinalizationError, "PROTECTED_WORKSPACE"):
                render_application_draft(pending_row(), synthetic_profile(), workspace)

    def test_cached_font_must_match_current_bytes(self):
        from scripts.a1_core import _register_font
        _register_font(require_current=True)
        with patch("scripts.a1_core._A1_FONT_SIGNATURE", ("changed", "0" * 64)):
            with self.assertRaisesRegex(A1ValidationError, "FONT_CACHE_CHANGED"):
                _register_font(require_current=True)
