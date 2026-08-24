from dataclasses import FrozenInstanceError
import pytest
from prototypes.architecture.adr001.proof_contract import AuditEvent, AuditLog

def test_non_content_append_only_audit_coverage():
    log = AuditLog()
    required = ("authentication", "authorization_denied", "document_view", "document_download", "review", "approval", "status_transition")
    for event_type in required: log.append(AuditEvent(event_type, "user-synth", "org-alpha", "opaque-ref", "success"))
    assert {e.event_type for e in log.events} == set(required)
    payload = repr([e.__dict__ for e in log.events]).lower()
    assert "synthetic person" not in payload and "%pdf" not in payload and "secret" not in payload
    with pytest.raises(FrozenInstanceError): log.events[0].outcome = "changed"
