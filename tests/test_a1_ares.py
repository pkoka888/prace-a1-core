"""The ARES client, the reviewed import and the LegalEntity record.

Decisions D11a and D11b (2026-10-20). The registry is public, free and
key-free, so the capability needs no provider decision; what it does need is
a client that degrades rather than fails, an import that puts a human
between the lookup and the stored fact, and a record that carries where it
came from.

These tests never reach the network. The registry's response shape is
recorded in a fixture, so the parsing is tested against the real shape
without depending on the register being up.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from portal.release1a.ares import (  # noqa: E402
    AresUnavailable,
    enabled,
    fetch_legal_entity,
    write_review_record,
)

# The shape the registry actually answers with: the subject at the top
# level, the address nested under "sidlo", the legal form as a code, and the
# activities in "czNace2008". The personal name is omitted here.
ARES_RESPONSE = {
    "ico": "00000000",
    "obchodniJmeno": "SYNTHETICKY OBCHODNIK",
    "sidlo": {
        "kodStatu": "CZ",
        "nazevStatu": "Česká republika",
        "kodObce": "5678",
        "nazevObce": "SYNTHETICKÁ OBC",
        "nazevUlice": "SYNTHETICKÁ ULICE",
        "cisloDomovni": "12",
        "cisloOrientacni": "3",
        "psc": "41501",
        "textovaAdresa": "SYNTHETICKÁ ULICE 12/3, 415 01 SYNTHETICKÁ OBC",
    },
    "pravniForma": "101",
    "datumVzniku": "2022-01-01",
    "datumAktualizace": "2024-12-04",
    "czNace2008": ["43120", "81290"],
    "seznamRegistraci": {"stavZdrojeRos": "AKTIVNI"},
}

ARES_RES_RESPONSE = {
    "icoId": "00000000",
    "zaznamy": [
        {"czNace": ["81230"], "czNace2008": ["81230", "43120"]}
    ],
}


@pytest.fixture
def registry(monkeypatch):
    """Stand in for the register, so no test depends on the network."""
    from portal.release1a import ares

    calls = []

    def fake_get_json(url, *, timeout):
        calls.append(url)
        if url.endswith("/ekonomicke-subjekty-res/00000000"):
            return ARES_RES_RESPONSE
        return ARES_RESPONSE

    monkeypatch.setattr(ares, "_get_json", fake_get_json)
    monkeypatch.setattr(ares, "DEFAULT_TIMEOUT_SECONDS", 1.0)
    return calls


def test_the_record_carries_its_source_and_its_dates(registry):
    record = fetch_legal_entity("00000000")
    assert record["registration_id"] == "00000000"
    assert record["legal_form"] == "sole_trader"
    assert record["country_code"] == "CZ"
    assert record["registry_updated_on"] == "2024-12-04"
    assert record["founded_on"] == "2022-01-01"
    assert record["verified_on"]
    assert record["source"].endswith("/ekonomicke-subjekty/00000000")


def test_the_address_is_taken_from_the_registered_seat(registry):
    address = fetch_legal_entity("00000000")["registered_address"]
    assert address["street"] == "SYNTHETICKÁ ULICE"
    assert address["house_number"] == "12/3"
    assert address["city"] == "SYNTHETICKÁ OBC"
    assert address["postal_code"] == "41501"
    assert address["municipality_code"] == "5678"


def test_the_activities_include_the_predominant_one(registry):
    nace = fetch_legal_entity("00000000")["nace_codes"]
    assert "43120" in nace and "81290" in nace
    assert "81230" in nace


def test_a_registration_number_that_is_not_a_number_is_refused():
    with pytest.raises(AresUnavailable, match="ARES_REGISTRATION_ID_INVALID"):
        fetch_legal_entity("not-a-number")


def test_a_subject_that_is_not_in_the_register_is_refused(monkeypatch):
    from portal.release1a import ares

    monkeypatch.setattr(ares, "_get_json", lambda url, timeout: {})
    with pytest.raises(AresUnavailable, match="ARES_SUBJECT_NOT_FOUND"):
        fetch_legal_entity("00000000")


def test_an_unreachable_register_is_reported_as_such(monkeypatch):
    from portal.release1a import ares

    def unreachable(url, *, timeout):
        raise AresUnavailable("ARES_UNREACHABLE")

    monkeypatch.setattr(ares, "_get_json", unreachable)
    with pytest.raises(AresUnavailable, match="ARES_UNREACHABLE"):
        fetch_legal_entity("00000000")


def test_the_lookup_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("A1_ARES_LOOKUP_ENABLED", "0")
    assert enabled() is False
    monkeypatch.setenv("A1_ARES_LOOKUP_ENABLED", "1")
    assert enabled() is True


def test_the_review_record_is_written_privately(tmp_path):
    record = {"registration_id": "00000000", "legal_name": "SYNTHETICKY"}
    destination = tmp_path / "review.json"
    write_review_record(record, destination)
    assert json.loads(destination.read_text())["registration_id"] == "00000000"
    assert destination.stat().st_mode & 0o777 == 0o600


def test_the_registration_numbers_are_discovered_from_the_review_data(tmp_path):
    """The import does not guess which employer to look up.

    It reads the registration numbers the reviewed rows already carry and
    skips the ones still pending, so a bare run does something useful
    without inventing a subject.
    """
    from scripts.import_ares_legal_entity import _discover

    review = tmp_path / "review.csv"
    review.write_text(
        "employee_id,employment_id\n"
        "one,11111111\n"
        "two,22222222\n"
        "three,<PENDING_OPERATOR_REVIEW>\n"
        "four,11111111\n",
        encoding="utf-8",
    )
    assert _discover(review) == ["11111111", "22222222"]


def test_a_missing_review_file_yields_no_registrations(tmp_path):
    from scripts.import_ares_legal_entity import _discover

    assert _discover(tmp_path / "absent.csv") == []


def test_the_stored_record_keeps_the_review_step_between(monkeypatch, tmp_path):
    """Nothing is stored by the retrieval step."""
    from scripts import import_ares_legal_entity as importer

    written = []
    monkeypatch.setattr(
        importer, "_retrieve_one", lambda registration_id, out: written.append(registration_id) or True
    )
    review = tmp_path / "review.csv"
    review.write_text(
        "employee_id,employment_id\none,11111111\n", encoding="utf-8"
    )
    assert importer.main(["--all-reviewed", "--review", str(review), "--out", str(tmp_path / "out")]) == 0
    assert written == ["11111111"]


def test_the_review_csv_is_annotated_with_the_register_comparison(monkeypatch, tmp_path):
    """The file path learns the divergence too.

    The generator reads a review CSV and must not reach the network or the
    database, so this is how a hand-written row learns that its employer
    disagrees with the register.
    """
    from scripts import import_ares_legal_entity as importer

    review = tmp_path / "review.csv"
    review.write_text(
        "employee_id,employment_id,employment_name,employment_street,"
        "employment_city,employment_postal_code\n"
        "one,00000000,SYNTHETICKY OBCHODNIK,SYNTHETICKÁ ULICE,"
        "SYNTHETICKÁ OBC,41501\n"
        "two,00000000,JINÝ ZAMĚSTNAVATEL,SYNTHETICKÁ ULICE,"
        "SYNTHETICKÁ OBC,41501\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        importer, "_discover", lambda path: ["00000000"]
    )

    class _FakeRegister:
        def fetch_legal_entity(self, registration_id, **kwargs):
            return {
                "registration_id": registration_id,
                "legal_name": "SYNTHETICKY OBCHODNIK",
                "registered_address": {
                    "street": "SYNTHETICKÁ ULICE",
                    "city": "SYNTHETICKÁ OBC",
                    "postal_code": "41501",
                },
            }

    monkeypatch.setattr(
        "portal.release1a.ares.fetch_legal_entity",
        _FakeRegister().fetch_legal_entity,
    )
    assert importer.main(["--annotate", str(review)]) == 0
    import csv

    rows = list(csv.DictReader(review.open(encoding="utf-8-sig")))
    assert rows[0]["employment_source_status"] == "REGISTRY_VERIFIED"
    assert rows[1]["employment_source_status"] == "DIVERGES_FROM_REGISTER"


def test_the_verification_seeder_refuses_a_database_outside_its_own():
    """It seeds the isolated verification database and nothing else.

    The working database holds real client identities, so a seeder that
    follows an inherited DJANGO_SETTINGS_MODULE would put synthetic rows
    among them.
    """
    import re
    from pathlib import Path as _Path

    source = (
        _Path(__file__).resolve().parent.parent
        / "scripts"
        / "seed_verification_db.py"
    ).read_text(encoding="utf-8")
    assert 'os.environ["DJANGO_SETTINGS_MODULE"] = "portal.settings_verification"' in source
    assert "refusing to seed" in source
    # It must not merely default the setting, which an inherited value would
    # override.
    assert "setdefault" not in source
    assert re.search(r"target != DB_PATH", source)
