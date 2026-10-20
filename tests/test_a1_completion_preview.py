"""Synthetic employee/OSVČ completion previews and source propagation."""
import json
from copy import deepcopy

import pytest
from pypdf import PdfReader

from scripts.a1_completion_preview import build_preview
from scripts.a1_core import (APPLICATION_DRAFT_NOTICE, A1ValidationError, ROOT,
                             build_form_data, generate_a1_pdf, validate_form_data)
from scripts.finalize_a1 import prepare_review, read_review


def source(status="posted_employee"):
    return {"id": "fictional-preview", "person": {
        "surname": "TESTOVÁ", "given_name": "ALENA", "dob": "01.01.1990",
        "birth_place": "TESTOV", "insurance_number": "9001010007", "nationality": "CZ", "sex": "F"},
        "residence": {"street": "<PENDING>", "country_code": "CZ"},
        "employment": {"employer_name": "<PENDING>"}, "a1": {"status_profile": status}}


def test_employee_missing_facts_remain_blank_and_do_not_gain_approval(tmp_path):
    employee = source()
    before = deepcopy(employee)
    form = build_preview(employee, variant="employee")
    assert employee == before
    assert form["status_posted_employee"] and form["employer_type_employee"]
    assert not form["status_osv_c_multistate"] and not form["employer_type_self_employed"]
    assert form["employment"]["employer_name"] == ""
    assert form["activity"] == {} and form["certificate"]["document_id"] == ""
    assert "employment.employer_name" in form["meta"]["missing_fields"]
    path = tmp_path / "preview.pdf"
    generate_a1_pdf(form, ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json", path)
    pdf = PdfReader(path)
    assert len(pdf.pages) == 3 and not pdf.get_fields()
    assert all(APPLICATION_DRAFT_NOTICE in page.extract_text() for page in pdf.pages)
    assert not any("<PENDING>" in page.extract_text() for page in pdf.pages)
    form["meta"]["application_draft"] = False
    with pytest.raises(A1ValidationError):
        validate_form_data(form)
    with pytest.raises(A1ValidationError):
        build_form_data(employee, {})


def test_variant_default_conflicts_and_multistate_are_explicit():
    # An empty status is an undecided situation, never a default. No Section 3
    # box is ticked, the status is reported as missing, and the worksheet
    # asserts nothing about the employment kind either.
    undecided = build_preview(source(""))
    assert not any((undecided["status_posted_employee"],
                    undecided["status_employee_multistate"],
                    undecided["status_osv_c_multistate"],
                    undecided["status_posted_self_employed"]))
    assert not undecided["employer_type_employee"]
    assert not undecided["employer_type_self_employed"]
    assert "a1.status_profile" in undecided["meta"]["missing_fields"]
    assert undecided["meta"]["status_profile_undecided"] is True
    form = build_preview(source("employee_multi_state"), variant="employee")
    assert form["status_employee_multistate"] and not form["status_posted_employee"]
    with pytest.raises(ValueError, match="CONFLICT"):
        build_preview(source(), variant="self_employed")
    with pytest.raises(ValueError, match="UNSUPPORTED_STATUS"):
        build_preview(source("not_employee"))


def test_coarse_employee_profile_renders_undecided_worksheet(tmp_path):
    employee = source("employee")
    form = build_preview(employee)
    assert form["meta"]["variant"] == "employee"
    assert form["meta"]["status_profile"] == ""
    assert form["meta"]["status_profile_undecided"] is True
    assert form["meta"]["status_profile_choices"] == ["posted_employee", "employee_multi_state", "self_employed_multi_state"]
    assert not any((form["status_posted_employee"], form["status_employee_multistate"],
                    form["status_osv_c_multistate"], form["status_posted_self_employed"]))
    assert not form["employer_type_employee"] and not form["employer_type_self_employed"]
    assert form["employment"]["kind"] == "employee"
    assert "a1.status_profile" in form["meta"]["missing_fields"]
    assert build_preview(source("employee"), variant="employee")["meta"]["variant"] == "employee"
    with pytest.raises(ValueError, match="VARIANT_CONFLICT"):
        build_preview(source("employee"), variant="self_employed")
    path = tmp_path / "undecided.pdf"
    generate_a1_pdf(form, ROOT / "templates/a1_background.pdf", ROOT / "config/a1_layout.json", path)
    pdf = PdfReader(path)
    assert len(pdf.pages) == 3 and not pdf.get_fields()
    assert all(APPLICATION_DRAFT_NOTICE in page.extract_text() for page in pdf.pages)


def test_undecided_status_stays_fail_closed_outside_preview(tmp_path):
    for raw in ("", "employee"):
        with pytest.raises(A1ValidationError, match="Missing or unsupported a1.status_profile"):
            build_form_data(source(raw), {})
    form = build_preview(source("employee"))
    form["meta"]["completion_preview"] = False
    with pytest.raises(A1ValidationError):
        validate_form_data(form)
    with pytest.raises(A1ValidationError):
        generate_a1_pdf(form, ROOT / "templates/a1_background.pdf",
                        ROOT / "config/a1_layout.json", tmp_path / "closed.pdf")
    tampered = build_preview(source("employee"))
    tampered["meta"]["status_profile"] = "employee"
    with pytest.raises(A1ValidationError, match="Unsupported status_profile"):
        validate_form_data(tampered)


def test_prepare_retains_supplied_assignment_facts(tmp_path):
    employee = source()
    employee.update(employment={"employer_id": "TEST-EMPLOYER", "employer_name": "Fictional Employer",
                                "street": "Test Street", "house_number": "2", "city": "Test City",
                                "postal_code": "10000", "country_code": "CZ"},
                    activity={"name": "Fictional posting", "address": "Fictional workplace"},
                    certificate={"document_id": "TEST-DOC", "start_date": "01.01.2026", "end_date": "31.12.2026"},
                    institution={"issue_date": "01.01.2026", "signed_by": "Test Signatory"})
    employee["a1"]["institution_profile"] = "synthetic-office"
    source_path = tmp_path / "employees.json"
    source_path.write_text(json.dumps({"employees": [employee]}))
    current = tmp_path / "current.json"
    current.write_text("{}")
    review = tmp_path / "review.csv"
    prepare_review(source_path, ROOT / "config/address_enrichment.json", current, review)
    row = read_review(review)[0]
    assert row["employment_name"] == "Fictional Employer"
    assert row["employment_id"] == "TEST-EMPLOYER"
    assert row["employment_country_code"] == "CZ"
    assert row["activity_address"] == "Fictional workplace"
    assert row["institution_profile"] == "synthetic-office"
    assert row["document_id"] == "TEST-DOC"
    assert row["start_date"] == "01.01.2026"


def test_czech_posting_scenario_separates_employer_from_workplace():
    employee = source()
    employee["employment"]["country_code"] = "DE"
    original = deepcopy(employee)
    form = build_preview(employee, variant="employee", posting_scenario="cz_employee_to_de")
    assert employee == original
    assert form["certificate"]["member_state"] == "CZ"
    assert form["employment"]["country_code"] == "CZ"
    assert form["activity"]["address"] == "DE"
    assert "activity.workplace_address" in form["meta"]["missing_fields"]
    assert form["status_posted_employee"] and form["employer_type_employee"]
    assert build_preview(employee)["employment"]["country_code"] == "DE"
    for status in ("employee_multi_state", "self_employed_multi_state"):
        with pytest.raises(ValueError, match="SCENARIO_PROFILE_CONFLICT"):
            build_preview(source(status), posting_scenario="cz_employee_to_de")


def test_shared_osvc_baseline_keeps_employee_and_excludes_issuance_identity():
    defaults = {"institution": {"name": "SYNTHETIC OFFICE", "code": "12345", "signed_by": "Excluded"},
                "certificate": {"member_state": "CZ", "start_date": "01.01.2026",
                                "end_date": "31.12.2026", "document_id": "DO-NOT-COPY",
                                "document_id_prefix": "DO-NOT-COPY"},
                "issue_date": "01.01.2026", "signed_by": "DO-NOT-COPY"}
    form = build_preview(source(), variant="employee", posting_scenario="cz_employee_to_de", shared_defaults=defaults)
    assert form["status_posted_employee"] and form["employer_type_employee"]
    assert form["certificate"]["start_date"] == "01.01.2026"
    assert form["certificate"]["end_date"] == "31.12.2026"
    assert form["certificate"]["document_id"] == ""
    assert form["institution"]["name"] == "SYNTHETIC OFFICE"
    assert form["institution"]["issue_date"] == form["institution"]["signed_by"] == ""
    assert "certificate.start_date" not in form["meta"]["missing_fields"]
    assert "residence.street" in form["meta"]["missing_fields"]
