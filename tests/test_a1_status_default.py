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
from scripts.a1_core import (  # noqa: E402
    A1_STATUS_LABELS,
    A1_STATUS_PROFILES,
    A1_STATUS_VARIANTS,
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


def test_the_supported_set_is_enumerated_exactly_once():
    """The set lives in the core, and nowhere else.

    It used to be written out in six places, and the activation path had to
    name all of them -- sixteen of which failed silently. Now it is
    enumerated once and every site derives from it.
    """
    sites = (
        "scripts/finalize_a1.py",
        "scripts/a1_completion_preview.py",
        "scripts/a1_quality_gate.py",
        "portal/release1a/a1_exports.py",
        "portal/release1a/assignment_facts.py",
    )
    literals = ("posted_employee", "employee_multi_state", "self_employed_multi_state")
    for rel in sites:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert not all(
            re.search(rf"""['"]{name}['"]""", text) for name in literals
        ), f"{rel} still enumerates the supported set"
    core = (REPO / "scripts" / "a1_core.py").read_text(encoding="utf-8")
    assert "A1_STATUS_PROFILES = (" in core
    assert set(A1_STATUS_PROFILES) == {
        "posted_employee", "employee_multi_state", "self_employed_multi_state"
    }
    assert set(A1_STATUS_VARIANTS) == set(A1_STATUS_PROFILES)
    assert set(A1_STATUS_LABELS) == set(A1_STATUS_PROFILES)
    # Every profile maps to a variant, and the variants are the two the
    # application has.
    assert set(A1_STATUS_VARIANTS.values()) == {"employee", "self_employed"}


def test_every_site_reads_the_shared_constant():
    """The supported set is written once, in the core.

    Before the constant, the set was written out in six places and the
    activation path had to name all of them. Now each site reads the
    constant, so a profile cannot be added to one and forgotten in another.
    """
    sites = {
        "scripts/a1_core.py": "A1_STATUS_PROFILES",
        "scripts/finalize_a1.py": "A1_STATUS_PROFILES",
        "scripts/a1_completion_preview.py": "A1_STATUS_PROFILES",
        "scripts/a1_quality_gate.py": "A1_STATUS_VARIANTS",
        "portal/release1a/a1_exports.py": "A1_STATUS_PROFILES",
        "portal/release1a/assignment_facts.py": "A1_STATUS_PROFILES",
    }
    for rel, symbol in sites.items():
        text = (REPO / rel).read_text(encoding="utf-8")
        assert symbol in text, f"{rel} does not read {symbol}"


def test_the_constant_is_defined_once():
    """Only the core defines the set."""
    for rel in (
        "scripts/finalize_a1.py",
        "scripts/a1_completion_preview.py",
        "scripts/a1_quality_gate.py",
        "portal/release1a/a1_exports.py",
        "portal/release1a/assignment_facts.py",
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "A1_STATUS_PROFILES = (" not in text, (
            f"{rel} defines the supported set instead of reading the core"
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
