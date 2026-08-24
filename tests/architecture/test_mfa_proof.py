import pytest
from prototypes.architecture.adr001.proof_contract import Denied, RecoveryCodes, Session, totp

def test_privileged_totp_recovery_and_invalidation():
    assert totp(b"synthetic-secret", 1_700_000_000) == totp(b"synthetic-secret", 1_700_000_000)
    session = Session("user-alpha-admin", True, 1)
    with pytest.raises(Denied): session.authorize(1)
    session.mfa_at = 1_700_000_000
    session.authorize(1)
    with pytest.raises(Denied): session.authorize(2)
    codes = RecoveryCodes.issue(["SYNTH-A", "SYNTH-B"])
    assert codes.use("SYNTH-A") and not codes.use("SYNTH-A")

