"""Country and territory codes on the A1 form are ISO 3166-1 alpha-2.

The official A1 form labels four fields "Country code" (1.8.4, 1.9.4,
4.4.2 and 6.5) and fixes the domain of a "State" in its own footnote:
"A 'State' or a 'Member State' is any European Union country, plus Iceland,
Liechtenstein, Norway and Switzerland." The United Kingdom is added for the
bilateral forms that the Withdrawal Agreement keeps in force.

Nothing in the repository validated the codes, so a mistyped territory would
render as an unknown country with no diagnostic. These tests pin the
vocabulary and the values actually in use.
"""

import csv
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# The A1's own definition of a "State": EU-27 plus the three EEA/EFTA
# partners it names. Source: the footnote on the official form.
A1_STATES = frozenset({
    # EU-27
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
    "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
    "RO", "SK", "SI", "ES", "SE",
    # named by the footnote
    "IS", "LI", "NO", "CH",
})

# Not a "State" for a coordination certificate, but a country whose records
# exist in the Czech administration and whose bilateral forms remain in force
# under the Withdrawal Agreement.
BILATERAL_ONLY = frozenset({"GB"})

# Every code the two-letter domain may hold, for validating an input.
ACCEPTED = A1_STATES | BILATERAL_ONLY

# The marker the workflow uses for a value that is not yet known. It is
# deliberately visible, so an unknown territory can never be mistaken for a
# reviewed one.
PENDING = "<PENDING_OPERATOR_REVIEW>"


def _iter_country_codes():
    for profile in sorted((REPO / "config" / "institutions").glob("*.json")):
        data = json.loads(profile.read_text(encoding="utf-8"))
        yield profile.name, (data.get("institution") or {}).get("country_code")


def test_every_institution_profile_uses_a_valid_state_code():
    found = 0
    for name, code in _iter_country_codes():
        if code is None:
            continue
        found += 1
        assert code in ACCEPTED, (
            f"{name}: country_code {code!r} is not an A1 State or bilateral code"
        )
    assert found, "no institution profile carried a country_code; the test is vacuous"


def test_institution_profiles_are_issued_by_the_czech_state():
    for name, code in _iter_country_codes():
        if code is None:
            continue
        assert code == "CZ", f"{name}: an issuing institution is in the CZ, not {code}"


def test_policy_default_territory_parses_to_valid_state_codes():
    policy = json.loads((REPO / "config" / "a1_provisional.json").read_text(encoding="utf-8"))
    raw = policy["activity_address"]
    codes = [part.strip() for part in raw.split(",") if part.strip()]
    assert codes, "the policy default carries no territory"
    for code in codes:
        assert code in A1_STATES, f"policy territory {code!r} is not an A1 State"
    # The codes in use are Germany and Czechia. Denmark would be DK, and a
    # mis-typed DE would silently render as an unknown territory.
    assert set(codes) == {"DE", "CZ"}, f"unexpected policy territory {codes}"


def test_de_and_cz_are_unambiguous():
    """DE is Germany and CZ is Czechia. Denmark is DK."""
    # The two codes the repository actually uses are in the domain.
    assert {"DE", "CZ"} <= A1_STATES
    # Denmark is a State in its own right under a different code, so a
    # mis-typed territory cannot silently mean the wrong country.
    assert "DK" in A1_STATES
    assert "DK" not in {"DE", "CZ"}
    # A three-letter or name form would not be a country code.
    for wrong in ("DEU", "Germany", "Deutschland", "CZE", "Czech Republic", "CHE"):
        assert wrong not in ACCEPTED, f"{wrong!r} is not an ISO 3166-1 alpha-2 code"


def test_review_territory_values_are_valid_or_explicitly_pending():
    review = REPO / "a1" / "review.csv"
    if not review.exists():
        pytest.skip("no review.csv in this checkout")
    rows = list(csv.DictReader(review.open(encoding="utf-8")))
    checked = 0
    for row in rows:
        raw = (row.get("activity_address") or "").strip()
        if not raw or raw == PENDING:
            continue
        checked += 1
        for code in (part.strip() for part in raw.split(",") if part.strip()):
            assert code in A1_STATES, f"activity_address territory {code!r} is not an A1 State"
    assert checked, "no review row carried a territory; the test is vacuous"


def test_layout_carries_the_country_code_positions():
    """The official form labels 1.8.4, 1.9.4, 4.4.2 and 6.5 "Country code"."""
    layout = json.loads((REPO / "config" / "a1_layout.json").read_text(encoding="utf-8"))
    sections = {entry["section"] for entry in layout["fields"].values()}
    # Three of the four country-code positions are rendered. 1.9.4 belongs to
    # the 1.9 State-of-stay block, which the project does not render yet; the
    # next test pins that as a declared gap rather than an accident.
    for section in ("1.8.4", "4.4.2", "6.5"):
        assert section in sections, f"the layout no longer carries position {section}"
    assert "1.9.4" not in sections, "1.9.4 is rendered; the declared gap must be updated"


def test_the_unrendered_country_code_position_is_declared():
    """1.9.4 is a known gap, and the field mapping must still declare it."""
    mapping = (REPO / "docs" / "architecture" / "a1-field-source-mapping.md").read_text(
        encoding="utf-8"
    )
    assert "1.9.4" in mapping, "the field mapping no longer mentions position 1.9.4"
