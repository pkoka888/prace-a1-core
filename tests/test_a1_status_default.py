"""An unstated A1 status must never become a legal status.

Official Section 3 of the A1 form is a mutually exclusive set: exactly one
status out of 3.1–3.12, and each carries different legal consequences
(different competent institution, different applicable legislation,
different certificate validity). A default that picks one of them asserts a
legal fact nobody stated.

The repository's own rule is that an unknown value stays unknown. These tests
pin the behaviour that follows from it, and pin the fact that the supported
status set is enumerated in one place rather than six.
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.a1_completion_preview import (  # noqa: E402
    PROFILES,
    STATUS_PROFILE_CHOICES,
    build_preview,
)

SECTION_3_BOXES = (
    "status_posted_employee",
    "status_employee_multistate",
    "status_posted_self_employed",
    "status_osv_c_multistate",
)


def _source(status=None, variant=None):
    employee = {
        "id": "fictional",
        "person": {
            "surname": "TESTOVÁ", "given_name": "ALENA", "dob": "01.01.1990",
            "birth_place": "TESTOV", "insurance_number": "9001010007",
            "nationality": "CZ", "sex": "F",
        },
        "residence": {"street": "<PENDING_OPERATOR_REVIEW>", "country_code": "CZ"},
        "employment": {"employer_name": "<PENDING_OPERATOR_REVIEW>"},
        "a1": {},
    }
    if status is not None:
        employee["a1"]["status_profile"] = status
    return build_preview(employee, variant=variant)


def _ticked(form):
    return [box for box in SECTION_3_BOXES if form.get(box)]


@pytest.mark.parametrize(
    "status,variant",
    [
        (None, None),
        (None, "employee"),
        (None, "self_employed"),
        ("employee", None),
        ("zaměstnanec", None),
        ("self_employed", None),
        ("osvč", None),
    ],
)
def test_an_unstated_status_never_ticks_a_section_3_box(status, variant):
    form = _source(status, variant)
    assert _ticked(form) == [], (
        f"an unstated status ticked {_ticked(form)}; a status is a legal "
        "declaration and may not be inferred"
    )
    meta = form.get("meta", {})
    assert "a1.status_profile" in (meta.get("missing_fields") or []), (
        "the undecided status must be reported as a missing field"
    )
    assert meta.get("status_profile_undecided") is True


def test_a_coarse_profile_fixes_the_variant_only():
    form = _source("employee")
    assert form["meta"]["variant"] == "employee"
    form = _source("self_employed")
    assert form["meta"]["variant"] == "self_employed"


def test_a_stated_status_ticks_exactly_one_box():
    for profile, box in (
        ("posted_employee", "status_posted_employee"),
        ("employee_multi_state", "status_employee_multistate"),
        ("self_employed_multi_state", "status_osv_c_multistate"),
    ):
        form = _source(profile)
        assert _ticked(form) == [box], f"{profile} ticked {_ticked(form)}"
        assert "a1.status_profile" not in (form["meta"].get("missing_fields") or [])


def test_the_choices_offered_are_exactly_the_supported_profiles():
    form = _source("employee")
    assert form["meta"]["status_profile_choices"] == STATUS_PROFILE_CHOICES
    assert set(form["meta"]["status_profile_choices"]) == set(PROFILES)


def test_the_supported_profile_set_is_enumerated_consistently():
    """Every site that enumerates the supported set must agree.

    The set is currently written out in six places. This test is the guard
    that makes the duplication safe: change one without the others and it
    fails here rather than silently rejecting a valid row.
    """
    core = (REPO / "scripts" / "a1_core.py").read_text(encoding="utf-8")
    finalize = (REPO / "scripts" / "finalize_a1.py").read_text(encoding="utf-8")
    gate = (REPO / "scripts" / "a1_quality_gate.py").read_text(encoding="utf-8")
    exports = (REPO / "portal" / "release1a" / "a1_exports.py").read_text(encoding="utf-8")
    facts = (REPO / "portal" / "release1a" / "assignment_facts.py").read_text(encoding="utf-8")
    preview = (REPO / "scripts" / "a1_completion_preview.py").read_text(encoding="utf-8")

    supported = set(PROFILES)
    assert supported == set(STATUS_PROFILE_CHOICES)

    for name, text in (("a1_core.py", core), ("finalize_a1.py", finalize),
                       ("a1_quality_gate.py", gate), ("a1_exports.py", exports),
                       ("assignment_facts.py", facts),
                       ("a1_completion_preview.py", preview)):
        found = set(
            re.findall(
                r"""['"](posted_employee|employee_multi_state|self_employed_multi_state)['"]""",
                text,
            )
        )
        assert found == supported, (
            f"{name} enumerates {sorted(found)} but the supported set is "
            f"{sorted(supported)}"
        )


def test_no_module_outside_the_six_enumerates_the_profile_set():
    """A seventh place would be a seventh thing to forget."""
    known = {
        "scripts/a1_core.py", "scripts/finalize_a1.py", "scripts/a1_quality_gate.py",
        "scripts/a1_completion_preview.py", "portal/release1a/a1_exports.py",
        "portal/release1a/assignment_facts.py", "scripts/extract_a1_checkbox_positions.py",
    }
    literals = ("posted_employee", "employee_multi_state", "self_employed_multi_state")
    offenders = []
    for path in list(REPO.glob("scripts/*.py")) + list(REPO.glob("portal/release1a/*.py")):
        rel = str(path.relative_to(REPO))
        if rel in known:
            continue
        text = path.read_text(encoding="utf-8")
        # A file that names all three is enumerating the set. A single
        # membership test against one profile is not an enumeration.
        if all(re.search(rf"""['"]{name}['"]""", text) for name in literals):
            offenders.append(rel)
    assert not offenders, (
        f"the status set is enumerated outside the known sites: {offenders}"
    )
