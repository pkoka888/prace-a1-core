import sys
from prototypes.architecture.adr001.proof_contract import a1_prepare

def test_determinism_staleness_and_prepared_not_official():
    profile = {"given_name": "Syntetický", "family_name": "Pracovník", "birth_date": "1990-01-01", "activity_profile": "employee"}
    assignments = [{"start": "2026-08-01", "end": "2026-08-15"}]
    first = a1_prepare(profile, assignments)
    assert first == a1_prepare(profile, assignments)
    changed = a1_prepare({**profile, "family_name": "Testovací"}, assignments, first["source_hash"])
    assert first["ready"] and first["status"] == "prepared" and not first["official"] and changed["stale"]

