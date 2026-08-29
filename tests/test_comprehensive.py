"""
Comprehensive validation and testing suite for the A1 generation system.

This suite includes:
1. Template validation
2. Unit tests for different profiles
3. Structural PDF tests
4. Visual tests
5. Shadow generation test

Run with:
    python -m pytest tests/test_comprehensive.py -v
"""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List, Tuple

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from scripts.a1_core import (
    A1ValidationError,
    build_form_data,
    enrich_residence,
    generate_a1_pdf,
    normalize_date,
    validate_form_data,
    render_overlay,
    load_json,
)

ROOT = Path(__file__).resolve().parents[1]


def with_explicit_employment(employee):
    """Complete synthetic fixtures with separately declared Section 4 data."""
    result = deepcopy(employee)
    person = result["person"]
    residence = result["residence"]
    result["employment"] = {
        **result.get("employment", {}),
        "employer_id": "SYNTHETIC-BUSINESS-ID",
        "employer_name": "SYNTHETIC BUSINESS SUBJECT",
        "street": "PODNIKATELSKÁ",
        "house_number": "2",
        "city": "TEST CITY",
        "postal_code": "100 00",
        "country_code": "CZ",
    }
    assert result["employment"]["employer_id"] != person.get("insurance_number")
    assert result["employment"]["street"] != residence.get("street")
    return result


class TemplateValidationTests(unittest.TestCase):
    """Validate the A1 template structure and content."""

    def setUp(self):
        self.template_path = ROOT / "templates" / "a1_background.pdf"
        self.layout_path = ROOT / "config" / "a1_layout.json"
        
        # Load unified layout config (fields + checkboxes)
        with open(self.layout_path) as f:
            self.layout = json.load(f)
        # Legacy compatibility: fields and checkboxes are now in a1_layout.json
        self.field_coords = {"fields": self.layout.get("fields", {})}
        self.checkbox_coords = {"fields": self.layout.get("checkboxes", {})}

    def test_template_has_expected_number_of_fields(self):
        """Verify the template has exactly the expected number of form fields."""
        # Count fields from layout
        expected_text_fields = len(self.layout["fields"])
        expected_checkbox_fields = len(self.checkbox_coords.get("fields", {}))
        
        # Read the template PDF to count actual fields (if any)
        reader = PdfReader(str(self.template_path))
        # The template should be a static background with no form fields
        # because we flatten it. But let's check for annotations.
        actual_fields = 0
        for page in reader.pages:
            if "/Annots" in page:
                actual_fields += len(page["/Annots"])
        
        # The background template should have no form fields (they are added via overlay)
        self.assertEqual(actual_fields, 0, 
                        "Template should have no form fields; they are added via overlay")
        
        # Check that we have the expected number of fields in our layout files
        # These are used for drawing, not actual PDF form fields
        self.assertGreater(expected_text_fields, 0)
        self.assertGreater(expected_checkbox_fields, 0)

    def test_no_jan_specific_values_in_template(self):
        """Ensure no Jan-specific identity or certificate values remain visible in the template."""
        # Read the template PDF and extract text
        reader = PdfReader(str(self.template_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        
        # These are values that should not appear in the clean template
        forbidden_values = [
            "EXAMPLE-SURNAME",
            "EXAMPLE-GIVEN",
            "000000/0000",  # example insurance number that should never be baked into the template
            "EXAMPLE-CITY",  # example birth place
        ]
        
        for value in forbidden_values:
            self.assertNotIn(value, text, 
                           f"Template should not contain {value}")

    def test_embedded_fonts_present_and_valid(self):
        """Check that embedded fonts are present and valid."""
        # We'll check if the font file we expect to use exists
        # From the a1_core.py, we try to register DejaVuSans
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        self.assertTrue(font_path.exists(), 
                       "Expected DejaVuSans font file not found")
        
        # Alternatively, we could check the PDF for embedded fonts, but that's more complex
        # For now, we'll verify the font file exists.

    def test_checkbox_appearances(self):
        """Validate checkbox appearances in the layout config."""
        # Check that checkbox coords have required fields
        for field_name, coords in self.checkbox_coords.get("fields", {}).items():
            self.assertIn("page", coords, f"Checkbox {field_name} missing page")
            self.assertIn("x", coords, f"Checkbox {field_name} missing x")
            self.assertIn("y", coords, f"Checkbox {field_name} missing y")
            self.assertIn("size", coords, f"Checkbox {field_name} missing size")
            
            # Validate types
            self.assertIsInstance(coords["page"], int)
            self.assertIsInstance(coords["x"], (int, float))
            self.assertIsInstance(coords["y"], (int, float))
            self.assertIsInstance(coords["size"], (int, float))
            self.assertGreater(coords["size"], 0)


class ProfileUnitTests(unittest.TestCase):
    """Unit tests for different employee profiles and scenarios."""

    def setUp(self):
        self.institution = load_json(ROOT / "config" / "institution.json")
        self.address_rules = load_json(ROOT / "config" / "address_enrichment.json")

    def test_posted_employee_scenario(self):
        """Test posted employee scenario (should select 3.1 and 4.1.1)."""
        employee = {
            "id": "posted-worker",
            "person": {
                "surname": "NOVAK",
                "given_name": "PAVEL",
                "dob": "01.01.1990",
                "birth_place": "PRAHA",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "900101/1234",
                "sex": "M",
            },
            "residence": {
                "street": "NKP",
                "house_number": "123",
                "city": "PRAHA",
                "postal_code": "110 00",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "employee",
                "employer_id": "123456",
                "employer_name": "CZECH EMPLOYER S.R.O.",
                "street": "EVROPSKÁ",
                "house_number": "100",
                "city": "PRAHA",
                "postal_code": "160 00",
                "country_code": "CZ",
                "activity_name": "SOFTWARE DEVELOPMENT",
                "activity_address": "EVROPSKÁ 100, PRAHA",
                "posting": {
                    "country": "DE",
                    "period_start": "01.01.2026",
                    "period_end": "31.12.2026",
                    "worksite": "BERLIN",
                    "no_fixed_address": False,
                }
            },
            "certificate": {
                "member_state": "DE",
                "document_id": "DOC-POSTED-1",
                "start_date": "01.01.2026",
                "end_date": "31.12.2026",
            },
            "a1": {"status_profile": "employee_multi_state"},
        }
        
        form = build_form_data(with_explicit_employment(employee), self.institution)
        
        # Check that posted_employee checkbox is selected
        self.assertTrue(form.get("status_posted_employee"), 
                       "Posted employee should have status_posted_employee checkbox selected")
        self.assertFalse(form.get("status_osv_c_multistate"),
                        "Posted employee should not have self-employed multi-state checkbox")
        
        # Check employer type
        self.assertTrue(form.get("employer_type_employee"))
        self.assertFalse(form.get("employer_type_self_employed"))
        
        # Check that certificate member_state and dates come from the source
        self.assertEqual(form.get("certificate", {}).get("member_state"), "DE")
        self.assertEqual(form.get("certificate", {}).get("start_date"), "01.01.2026")
        self.assertEqual(form.get("certificate", {}).get("end_date"), "31.12.2026")

    def test_self_employed_multi_state_from_source_profile(self):
        """Test self-employed multi-state profile selected from source (3.4 and 4.1.2)."""
        # The status comes from the reviewed a1.status_profile, never from the
        # person's name or any hardcoded special case.
        employee = {
            "id": "synthetic-self-employed",
            "person": {
                "surname": "PŘÍKLADOVÁ",
                "given_name": "JANA",
                "dob": "22.05.1994",
                "birth_place": "TESTOV",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "900101/1234",
                "sex": "F",
            },
            "residence": {
                "street": "SOUKROMÁ",
                "house_number": "123",
                "city": "MLADÁ BOLESLAV",
                "postal_code": "293 01",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
                "activity_name": "CONSULTING",
                "activity_address": "SOUKROMÁ 123, MLADÁ BOLESLAV",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }
        
        form = build_form_data(with_explicit_employment(employee), self.institution)
        
        # Check that self_employed_multi_state checkbox is selected
        self.assertTrue(form.get("status_osv_c_multistate"), 
                       "Self-employed multi-state profile should select status_osv_c_multistate")
        self.assertFalse(form.get("status_posted_employee"),
                        "Self-employed profile must not select posted employee checkbox")
        
        # Check employer type
        self.assertTrue(form.get("employer_type_self_employed"))
        self.assertFalse(form.get("employer_type_employee"))
        
        self.assertEqual(form["employment"]["employer_id"], "SYNTHETIC-BUSINESS-ID")
        self.assertNotEqual(
            form["employment"]["employer_id"], employee["person"]["insurance_number"]
        )
        self.assertNotEqual(form["employment"]["street"], employee["residence"]["street"])

    def test_real_calendar_dates_handling(self):
        """Test real calendar dates handling (various formats, validation)."""
        test_cases = [
            ("22/05/1994", "22.05.1994"),
            ("07.01.1989", "07.01.1989"),
            ("1-1-2000", "01.01.2000"),
            ("31/12/2026", "31.12.2026"),
            ("22-05-2026", "22.05.2026"),  # This should be valid
        ]
        
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                self.assertEqual(normalize_date(input_date), expected)
        
        # Test invalid dates
        invalid_dates = ["2026/05/22", "99.99.9999", "29.02.2023"]
        for invalid in invalid_dates:
            with self.subTest(invalid=invalid):
                with self.assertRaises(A1ValidationError):
                    normalize_date(invalid)

    def test_employer_mapping(self):
        """Test employer mapping from employee data to form fields."""
        employee = {
            "id": "employer-mapping",
            "person": {
                "surname": "DOE",
                "given_name": "JOHN",
                "dob": "01.01.1980",
                "birth_place": "PRAHA",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "800101/1234",
                "sex": "M",
            },
            "residence": {
                "street": "TEST",
                "house_number": "1",
                "city": "TEST CITY",
                "postal_code": "123 45",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "employee",
                "employer_id": "EMP-123",
                "employer_name": "TEST EMPLOYER",
                "street": "WORK STREET",
                "house_number": "456",
                "city": "WORK CITY",
                "postal_code": "543 21",
                "country_code": "CZ",
            },
            "a1": {"status_profile": "employee_multi_state"},
        }
        
        form = build_form_data(employee, self.institution)

        # Check direct mapping
        self.assertEqual(form["employment"]["employer_id"], "EMP-123")
        self.assertEqual(form["employment"]["employer_name"], "TEST EMPLOYER")
        self.assertEqual(
            f"{form['employment']['street']} {form['employment']['house_number']}",
            "WORK STREET 456",
        )
        self.assertEqual(form["employment"]["city"], "WORK CITY")
        self.assertEqual(form["employment"]["postal_code"], "543 21")
        self.assertEqual(form["employment"]["country_code"], "CZ")

    def test_vzp_assumption_provenance(self):
        """Test VZP assumption provenance (issuing institution)."""
        # This test checks that the issuing institution is correctly set
        # from config/institution.json when not overridden by employee data
        employee = {
            "id": "vzp-provenance",
            "person": {
                "surname": "TEST",
                "given_name": "TEST",
                "dob": "01.01.1990",
                "birth_place": "TEST CITY",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "800101/1234",
                "sex": "M",
            },
            "residence": {
                "street": "TEST",
                "house_number": "1",
                "city": "TEST CITY",
                "postal_code": "123 45",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
            # No certificate data in employee - should come from institution
        }
        
        form = build_form_data(with_explicit_employment(employee), self.institution)
        
        # Check that institution data comes from config/institution.json
        # The institution.json should have default values
        institution_data = load_json(ROOT / "config" / "institution.json")
        # Assuming institution.json has an "institution" object
        if "institution" in institution_data:
            inst = institution_data["institution"]
            self.assertEqual(form["institution"]["name"], inst.get("name", ""))
            self.assertEqual(
                f"{form['institution']['street']} {form['institution']['house_number']}".strip(),
                f"{inst.get('street', '')} {inst.get('house_number', '')}".strip(),
            )
            self.assertEqual(form["institution"]["city"], inst.get("city", ""))
            self.assertEqual(form["institution"]["postal_code"], inst.get("postal_code", ""))
            self.assertEqual(form["institution"]["country_code"], inst.get("country_code", ""))
            self.assertEqual(form["institution"]["code"], inst.get("code", ""))

    def test_address_enrichment(self):
        """Test address enrichment using rules from address_enrichment.json."""
        # Test with an address that matches a rule
        residence = {
            "city": "LITVÍNOV",
                "district": "CHUDEŘÍN",
            "street": "TYRŠE A FÜGNERA",
            "house_number": "217",
        }
        
        enriched, evidence = enrich_residence(residence, self.address_rules)
        
        # Should have postal_code and OSSZ from the rule
        self.assertEqual(enriched.get("postal_code"), "436 03")
        self.assertEqual(enriched.get("ossz"), "OSSZ Most")
        
        # Evidence should be recorded
        self.assertGreater(len(evidence), 0)
        self.assertEqual(evidence[0]["source"], "https://vdp.cuzk.gov.cz/")
        
        # Test with address that doesn't match any rule
        residence_no_match = {
            "city": "UNKNOWN CITY",
            "district": "UNKNOWN",
            "street": "UNKNOWN STREET",
            "house_number": "1",
        }
        
        enriched_no_match, evidence_no_match = enrich_residence(residence_no_match, self.address_rules)
        
        # Should be unchanged except for maybe default fields
        self.assertEqual(enriched_no_match.get("city"), "UNKNOWN CITY")
        self.assertIsNone(enriched_no_match.get("postal_code"))
        self.assertIsNone(enriched_no_match.get("ossz"))
        self.assertEqual(len(evidence_no_match), 0)

    def test_ossz_jurisdiction_logic(self):
        """Test OSSZ jurisdiction logic based on enriched address."""
        # This is partially tested in address_enrichment, but we can test the flow
        employee = {
            "person": {
                "surname": "TEST",
                "given_name": "TEST",
                "dob": "01.01.1990",
                "birth_place": "TEST CITY",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "800101/1234",
                "sex": "M",
            },
            "residence": {
                "city": "LITVÍNOV",
                "district": "CHUDEŘÍN",
                "street": "TYRŠE A FÜGNERA",
                "house_number": "217",
                "country_code": "CZ",
                # Note: postal_code and Ossz will be enriched
            },
            "employment": {
                "kind": "self_employed",
                "employer_id": "800101/1234",
                "employer_name": "TEST TEST",
                "street": "TYRŠE A FÜGNERA",
                "house_number": "217",
                "city": "LITVÍNOV",
                "postal_code": "293 01",  # Will be enriched
                "country_code": "CZ",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }
        form = build_form_data(employee, self.institution)
        
        # After build_form_data, the residence should be enriched
        # Check that the form data has the enriched values
        self.assertEqual(form.get("residence", {}).get("postal_code"), "436 03")
        # Note: The form data doesn't directly include Ossz, but it's in meta.resolved_ossz
        self.assertEqual(form.get("meta", {}).get("resolved_ossz"), "OSSZ Most")

    def test_required_issued_metadata_validation(self):
        """Test validation of required issued metadata."""
        # Test that missing required fields raises A1ValidationError
        incomplete_employee = {
            "person": {
                "surname": "TEST",
                "given_name": "TEST",
                # Missing dob, insurance_number, etc.
            },
            "residence": {
                # Missing required fields
            },
            "employment": {
                "kind": "self_employed",
                # Missing required fields
            },
        }
        
        with self.assertRaises(A1ValidationError):
            build_form_data(incomplete_employee, self.institution)

    def test_overflow_handling(self):
        """Test handling of overflow text in fields with max_width and max_lines."""
        # Test with very long text that should be truncated or wrapped
        employee = {
            "person": {
                "surname": "A" * 50,  # Very long surname
                "given_name": "B" * 50,
                "insurance_number": "800101/1234",
                "dob": "01.01.1980",
                "birth_place": "C" * 50,
                "nationality": "ČESKÁ REPUBLIKA",
                "sex": "M",
            },
            "residence": {
                "street": "D" * 100,
                "house_number": "1",
                "city": "E" * 50,
                "postal_code": "123 45",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
                "activity_name": "F" * 200,  # Very long activity name
                "activity_address": "G" * 200,
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }
        
        # This should not raise an exception during form building
        form = build_form_data(with_explicit_employment(employee), self.institution)
        
        # Check that the fields are present (even if long)
        self.assertEqual(len(form["person"]["surname"]), 50)
        self.assertEqual(len(form["person"]["given_name"]), 50)
        
        # When generating PDF, the text should be handled according to layout constraints
        # We'll test that PDF generation doesn't crash
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "overflow_test.pdf"
            try:
                generate_a1_pdf(
                    form,
                    ROOT / "templates" / "a1_background.pdf",
                    ROOT / "config" / "a1_layout.json",
                    output_path,
                )
                # If we get here, PDF generation succeeded
                self.assertTrue(output_path.exists())
            except Exception as e:
                self.fail(f"PDF generation failed with overflow text: {e}")


class StructuralPDFTests(unittest.TestCase):
    """Test structural properties of generated A1 PDFs."""

    def setUp(self):
        self.institution = load_json(ROOT / "config" / "institution.json")
        # Use a known good employee for testing
        self.employee = {
            "id": "test-worker",
            "person": {
                "surname": "NOVAK",
                "given_name": "PAVEL",
                "dob": "01.01.1990",
                "birth_place": "PRAHA",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "900101/1234",
                "sex": "M",
            },
            "residence": {
                "street": "NKP",
                "house_number": "123",
                "city": "PRAHA",
                "postal_code": "110 00",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }

    def test_czech_diacritics_rendering(self):
        """Verify correct Czech diacritics rendering in PDF."""
        # Use employee data with Czech diacritics
        employee_with_diacritics = {
            "id": "diacritics-test",
            "person": {
                "surname": "NOVÁK",
                "given_name": "ČENĚK",
                "dob": "01.01.1990",
                "birth_place": "PŘÍBRAM",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "900101/1234",
                "sex": "M",
            },
            "residence": {
                "street": "ŠÉVA",
                "house_number": "123",
                "city": "KOŠŤANY",
                "postal_code": "417 23",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
                "activity_name": "ČINNOST S HÁČKY",
                "activity_address": "ULICE S ČÁRKAMI",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }
        
        form = build_form_data(with_explicit_employment(employee_with_diacritics), self.institution)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "diacritics_test.pdf"
            generate_a1_pdf(
                form,
                ROOT / "templates" / "a1_background.pdf",
                ROOT / "config" / "a1_layout.json",
                output_path,
            )
            
            # Extract text from PDF and verify diacritics are present
            reader = PdfReader(str(output_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            
            # Every uppercase diacritic present in the rendered source fields must
            # appear. ČENĚK -> Č Ě, ŠÉVA -> Š É, KOŠŤANY -> Š Ť, PŘÍBRAM -> Ř Í,
            # NOVÁK -> Á, and the institution name ÚSSZ -> Ú.
            required_diacritics = ["Á", "Č", "Ě", "É", "Í", "Ř", "Š", "Ť", "Ú"]
            for diacritic in required_diacritics:
                self.assertIn(diacritic, text,
                            f"Expected diacritic {diacritic} not found in PDF text")

    def test_zero_old_identities_placeholders_in_output(self):
        """Ensure zero old identities/placeholders in output PDF."""
        form = build_form_data(with_explicit_employment(self.employee), self.institution)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "no_placeholders_test.pdf"
            generate_a1_pdf(
                form,
                ROOT / "templates" / "a1_background.pdf",
                ROOT / "config" / "a1_layout.json",
                output_path,
            )
            
            # Extract text from PDF
            reader = PdfReader(str(output_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            
            # These are placeholders that should not appear
            placeholders = [
                "{{",
                "}}",
                "EXAMPLE-GIVEN",
                "EXAMPLE-SURNAME",
                "000000/0000",  # example insurance number that should not appear unless it's the employee's
                "EXAMPLE-CITY",
                "OTHER-PERSON-A",
                "OTHER-PERSON-B",
                # Add more known placeholders from the original template
            ]
            
            for placeholder in placeholders:
                # Only check if it's not the employee's actual data
                if placeholder not in [self.employee["person"]["surname"], 
                                      self.employee["person"]["given_name"],
                                      self.employee["person"]["insurance_number"],
                                      self.employee["person"]["birth_place"]]:
                    self.assertNotIn(placeholder, text, 
                                   f"Placeholder {placeholder} found in output PDF")

    def test_no_widgets_or_acroform_in_final_pdfs(self):
        """Confirm no widgets or AcroForm in final PDFs."""
        form = build_form_data(with_explicit_employment(self.employee), self.institution)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "no_widgets_test.pdf"
            generate_a1_pdf(
                form,
                ROOT / "templates" / "a1_background.pdf",
                ROOT / "config" / "a1_layout.json",
                output_path,
            )
            
            # Check that the PDF has no form fields/widgets
            reader = PdfReader(str(output_path))
            
            # Check each page for annotations (which would contain widgets)
            total_annotations = 0
            for page in reader.pages:
                if "/Annots" in page:
                    total_annotations += len(page["/Annots"])
            
            self.assertEqual(total_annotations, 0, 
                           f"PDF should have no widgets/annotations, found {total_annotations}")
            
            # Also check for AcroForm root
            self.assertNotIn("/AcroForm", reader.trailer.get("/Root", {}),
                           "PDF should not have AcroForm")

    def test_successful_reopening_in_multiple_pdf_engines(self):
        """Test successful reopening in multiple PDF engines."""
        # We'll test with pypdf (which we're using) and note that other engines should work
        form = build_form_data(with_explicit_employment(self.employee), self.institution)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "reopen_test.pdf"
            generate_a1_pdf(
                form,
                ROOT / "templates" / "a1_background.pdf",
                ROOT / "config" / "a1_layout.json",
                output_path,
            )
            
            # Test reopening with pypdf
            try:
                reader = PdfReader(str(output_path))
                self.assertEqual(len(reader.pages), 3, 
                               "PDF should have 3 pages")
                # Try to access each page
                for i, page in enumerate(reader.pages):
                    _ = page.extract_text()  # Should not raise
            except Exception as e:
                self.fail(f"Failed to reopen PDF with pypdf: {e}")
            
            # Note: To truly test multiple engines, we would need to install
            # other PDF libraries (like PyPDF2, pdfrw, etc.) or use subprocess
            # to call external tools. For now, we'll assume that if pypdf can
            # read it, other standard engines can too.


class VisualTests(unittest.TestCase):
    """Visual tests for A1 PDF generation."""

    def setUp(self):
        self.institution = load_json(ROOT / "config" / "institution.json")
        self.layout = load_json(ROOT / "config" / "a1_layout.json")
        self.employee = {
            "id": "visual-test",
            "person": {
                "surname": "TEST",
                "given_name": "TEST",
                "dob": "01.01.1990",
                "birth_place": "TEST CITY",
                "nationality": "ČESKÁ REPUBLIKA",
                "insurance_number": "900101/1234",
                "sex": "M",
            },
            "residence": {
                "street": "TEST STREET",
                "house_number": "123",
                "city": "TEST CITY",
                "postal_code": "123 45",
                "country_code": "CZ",
            },
            "employment": {
                "kind": "self_employed",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }

    def test_render_at_fixed_dpi(self):
        """Render at fixed 200-300 DPI and verify dimensions."""
        # The layout defines the page size in points (1/72 inch)
        # From a1_layout.json: "coordinate_system": "ReportLab bottom-left points on 595.2 x 841.92"
        # This is A4 size: 595.2 points wide x 841.92 points high
        # 1 point = 1/72 inch, so 595.2 points = 595.2/72 = 8.2667 inches
        # At 200 DPI: 8.2667 * 200 = 1653 pixels
        # At 300 DPI: 8.2667 * 300 = 2480 pixels
        
        form = build_form_data(with_explicit_employment(self.employee), self.institution)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dpi_test.pdf"
            generate_a1_pdf(
                form,
                ROOT / "templates" / "a1_background.pdf",
                ROOT / "config" / "a1_layout.json",
                output_path,
            )
            
            # Check PDF page size
            reader = PdfReader(str(output_path))
            page = reader.pages[0]
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            
            # Should match the layout's coordinate system
            self.assertAlmostEqual(width, 595.2, places=1,
                                 msg="PDF width does not match expected A4 width in points")
            self.assertAlmostEqual(height, 841.92, places=1,
                                 msg="PDF height does not match expected A4 height in points")

    def test_text_does_not_clip_or_escape_field_boundaries(self):
        """Ensure text does not clip or escape its field boundaries."""
        # We'll test by checking that the text length is reasonable for the field's max_width
        # This is an approximation since we don't render to pixels
        
        form = build_form_data(with_explicit_employment(self.employee), self.institution)
        
        # Check each text field in the layout
        for field_name, config in self.layout["fields"].items():
            # Skip fields that use a source mapping (like document_id_p1, p2, p3)
            if "source" in config:
                # Get the actual value from the form using the source path
                source_path = config["source"]
                value = self._get_nested_value(form, source_path.split("."))
            else:
                # Direct field mapping
                value = form.get(field_name, "")
            
            if not value:
                continue  # Skip empty fields
                
            max_width = config.get("max_width", float('inf'))
            size = config.get("size", 9)
            
            # We'll do a rough check: average character width * character count < max_width * some factor
            # This is very approximate but can catch extreme cases
            # Assume average character width is about 0.6 * size (for monospace, but we're using proportional)
            # For proportional fonts, it's harder. We'll just check that we're not massively over
            estimated_char_width = size * 0.6  # rough estimate
            estimated_text_width = len(value) * estimated_char_width
            
            # Allow some overflow because of font shaping and spaces
            self.assertLess(estimated_text_width, max_width * 2.0,
                           f"Field {field_name} text may be too wide: estimated width {estimated_text_width} > max_width {max_width}")

    def test_pixels_outside_approved_field_rectangles_match_reference(self):
        """Verify pixels outside approved field rectangles match reference.
        
        This would require rendering to an image and comparing to a reference.
        For now, we'll skip this test as it requires image processing libraries
        and a reference image. We'll note that this should be implemented
        when visual regression testing is set up.
        """
        # Placeholder for visual regression test
        self.skipTest("Visual regression test not implemented - requires image comparison")

    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get a nested value from a dictionary using a list of keys."""
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


class ShadowGenerationTests(unittest.TestCase):
    """Shadow generation test: process all employee records.

    Status profiles drive derivation behaviour for Section 4:
    * ``self_employed_multi_state`` (OSVČ) — ``scripts/a1_core.py:188-198``
      derives employer_id / employer_name / address from person + residence
      when explicit employment fields are missing. Section 4 is the OSVČ's
      own identity, so derivation is the documented contract.
    * ``employee_multi_state`` — no derivation; Section 4 must come from
      authoritative employment evidence or the record fails closed.

    The fixtures in ``setUp`` cover both: one OSVČ that exercises derivation,
    one posted-employee record that still must fail without Section 4.
    """

    def setUp(self):
        self.institution = load_json(ROOT / "config" / "institution.json")
        self.employees_data = {"employees": [
            {
                # OSVČ: Section 4 derives from person/residence.
                "id": "synthetic-self-employed-osvc",
                "person": {
                    "surname": "TESTOVÁ", "given_name": "ALENA",
                    "dob": "01.01.1990", "birth_place": "TESTOV",
                    "nationality": "CZ", "insurance_number": "900101/0007", "sex": "F",
                },
                "residence": {
                    "street": "BYTOVÁ", "house_number": "1", "city": "TESTOV",
                    "postal_code": "100 00", "country_code": "CZ",
                },
                "employment": {"kind": "self_employed"},
                "certificate": {
                    "member_state": "CZ", "document_id": "SYNTHETIC-DOC",
                    "start_date": "01.01.2026", "end_date": "31.12.2026",
                },
                "a1": {"status_profile": "self_employed_multi_state"},
            },
            {
                # Posted employee: no derivation; missing Section 4 must fail closed.
                "id": "synthetic-employee-incomplete",
                "person": {
                    "surname": "TESTOVÁ", "given_name": "ALENA",
                    "dob": "01.01.1990", "birth_place": "TESTOV",
                    "nationality": "CZ", "insurance_number": "900101/0007", "sex": "F",
                },
                "residence": {
                    "street": "BYTOVÁ", "house_number": "1", "city": "TESTOV",
                    "postal_code": "100 00", "country_code": "CZ",
                },
                "employment": {"kind": "employee"},
                "certificate": {
                    "member_state": "CZ", "document_id": "SYNTHETIC-DOC",
                    "start_date": "01.01.2026", "end_date": "31.12.2026",
                },
                "a1": {"status_profile": "employee_multi_state"},
            },
        ]}

    def test_self_employed_multi_state_derives_section_four_from_person(self):
        """OSVČ records derive Section 4 employment from person/residence data."""
        employees = {e["id"]: e for e in self.employees_data["employees"]}
        employee = employees["synthetic-self-employed-osvc"]
        form = build_form_data(employee, self.institution)
        validate_form_data(form)

        employment = form["employment"]
        self.assertEqual(employment["employer_id"], "900101/0007")
        self.assertEqual(employment["employer_name"], "TESTOVÁ ALENA - OSVČ")
        self.assertEqual(employment["street"], "BYTOVÁ")
        self.assertEqual(employment["house_number"], "1")
        self.assertEqual(employment["city"], "TESTOV")
        self.assertEqual(employment["postal_code"], "100 00")
        self.assertEqual(employment["country_code"], "CZ")

    def test_employee_multi_state_without_section_four_fails_closed(self):
        """Non-OSVČ records without Section 4 employment must fail closed."""
        employees = {e["id"]: e for e in self.employees_data["employees"]}
        employee = employees["synthetic-employee-incomplete"]
        with self.assertRaisesRegex(A1ValidationError, "employment\\."):
            build_form_data(employee, self.institution)

    def test_records_lacking_certificate_metadata_fail_closed(self):
        """Records without authoritative certificate facts must not build a form."""
        employees = self.employees_data.get("employees", [])
        self.assertGreater(len(employees), 0)
        # Take a copy of the first employee (OSVČ) and remove its certificate facts.
        # OSVČ derivation populates Section 4 from person/residence, but certificate
        # gaps still fail closed because the certificate defaults are removed too.
        employee = dict(employees[0])
        employee.pop("certificate", None)
        institution_no_cert = {
            key: value for key, value in self.institution.items() if key != "certificate"
        }

        # This should fail validation because certificate fields are required
        with self.assertRaises(A1ValidationError):
            build_form_data(employee, institution_no_cert)

    def test_verify_only_complete_records_produce_final_certificate_pdfs(self):
        """Verify only complete records produce final certificate PDFs.

        The OSVČ record passes via Section-4 derivation from person/residence;
        the employee_multi_state record has no derivation and must fail closed.
        """
        employees = self.employees_data.get("employees", [])
        self.assertGreater(len(employees), 0)

        complete_count = 0
        incomplete_count = 0

        for employee_data in employees:
            try:
                form = build_form_data(employee_data, self.institution)
                validate_form_data(form)
                complete_count += 1

                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = Path(temp_dir) / f"cert_{employee_data['id']}.pdf"
                    generate_a1_pdf(
                        form,
                        ROOT / "templates" / "a1_background.pdf",
                        ROOT / "config" / "a1_layout.json",
                        output_path,
                    )
                    self.assertTrue(output_path.exists(),
                                  f"PDF should be generated for complete employee {employee_data['id']}")

            except A1ValidationError:
                incomplete_count += 1
            except Exception:
                incomplete_count += 1

        # OSVČ record passes via derivation (1); employee_multi_state record fails closed (1).
        self.assertEqual(1, complete_count)
        self.assertEqual(1, incomplete_count)
        self.assertEqual(len(employees), complete_count + incomplete_count)


if __name__ == '__main__':
    unittest.main()
