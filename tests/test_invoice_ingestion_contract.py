from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from src.invoice_ingestion.contracts import (
    AuditAction,
    AuditEvent,
    AuditResult,
    AuthorizationAction,
    AuthorizationContext,
    BoundingBox,
    ContractError,
    Document,
    DocumentVersion,
    ExportArtifact,
    ExportProfile,
    ExportRun,
    FieldProposal,
    FieldState,
    IdempotencyConflict,
    InvoiceRecordVersion,
    InvalidTransition,
    Provenance,
    ReconciliationResult,
    ReviewDecision,
    ReviewOutcome,
    RevisionConflict,
    RunStatus,
    Scope,
    ScopeMismatch,
    authorized_export,
    check_idempotent,
    create_invoice_record_version,
    ensure_expected_revision,
    fingerprint_json,
    require_same_scope,
    review_proposal,
    start_extraction,
    to_json_dict,
    transition_field_state,
)


NOW = datetime(2026, 8, 14, 10, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64
SCOPE = Scope("tenant-synthetic", "org-synthetic")


def document_version(**changes):
    base = DocumentVersion(
        id="dv-1",
        document_id="doc-1",
        scope=SCOPE,
        version=1,
        source_sha256=HASH_A,
        media_type="application/pdf",
        size_bytes=123,
        protected_storage_ref="opaque://documents/dv-1",
        created_by="actor-1",
        created_at=NOW,
    )
    return replace(base, **changes)


def provenance():
    return Provenance(
        document_version_id="dv-1",
        source_sha256=HASH_A,
        engine="synthetic-extractor",
        engine_version="1",
        config_sha256=HASH_B,
        locations=(BoundingBox(1, 1, 2, 10, 20),),
    )


def proposal(**changes):
    base = FieldProposal(
        id="fp-1",
        scope=SCOPE,
        extraction_run_id="run-1",
        field_name="invoice.reference",
        value="SYNTH-001",
        state=FieldState.PROPOSED,
        confidence=0.8,
        provenance=provenance(),
        created_at=NOW,
    )
    return replace(base, **changes)


def invoice(**changes):
    base = InvoiceRecordVersion(
        id="iv-1",
        invoice_record_id="invoice-1",
        scope=SCOPE,
        revision=1,
        predecessor_id=None,
        source_document_version_ids=("dv-1",),
        source_hashes=(HASH_A,),
        confirmed_fields=(("invoice.reference", "SYNTH-001"),),
        review_decision_ids=("review-1",),
        idempotency_key="record:synthetic:0001",
        input_fingerprint=HASH_B,
        created_by="reviewer-1",
        created_at=NOW,
    )
    return replace(base, **changes)


def test_document_requires_purpose_retention_and_aware_timestamps():
    doc = Document("doc-1", SCOPE, "synthetic contract test", "actor-1", NOW, NOW + timedelta(days=90))
    assert doc.retention_review_at > doc.created_at
    with pytest.raises(ContractError):
        replace(doc, declared_purpose="")
    with pytest.raises(ContractError):
        replace(doc, created_at=NOW.replace(tzinfo=None))


def test_document_version_binds_content_and_is_immutable():
    value = document_version()
    assert value.source_sha256 == HASH_A
    with pytest.raises(FrozenInstanceError):
        value.version = 2
    with pytest.raises(ContractError):
        document_version(source_sha256="not-a-hash")
    with pytest.raises(ContractError):
        document_version(version=2)


def test_proposal_provenance_and_field_invariants():
    assert proposal().provenance.locations[0].page == 1
    with pytest.raises(ContractError):
        proposal(confidence=1.01)
    with pytest.raises(ContractError):
        proposal(state=FieldState.MISSING)
    assert proposal(state=FieldState.MISSING, value=None).value is None
    with pytest.raises(ContractError):
        proposal(state=FieldState.CONFIRMED)
    with pytest.raises(ContractError):
        proposal(state=FieldState.REJECTED)


@pytest.mark.parametrize(
    ("before", "outcome", "after"),
    [
        (FieldState.PROPOSED, ReviewOutcome.CONFIRM, FieldState.CONFIRMED),
        (FieldState.PROPOSED, ReviewOutcome.REJECT, FieldState.REJECTED),
        (FieldState.PROPOSED, ReviewOutcome.CONFLICT, FieldState.CONFLICT),
        (FieldState.CONFLICT, ReviewOutcome.CONFIRM, FieldState.CONFIRMED),
    ],
)
def test_review_state_machine(before, outcome, after):
    assert transition_field_state(before, outcome) is after


def test_terminal_field_states_cannot_be_reviewed_again():
    for state in (FieldState.CONFIRMED, FieldState.REJECTED, FieldState.SUPERSEDED):
        with pytest.raises(InvalidTransition):
            transition_field_state(state, ReviewOutcome.CONFIRM)


def test_review_decision_records_actor_reason_and_expected_revision():
    decision = ReviewDecision(
        "review-1", SCOPE, "fp-1", FieldState.PROPOSED, ReviewOutcome.CONFIRM,
        "reviewer-1", NOW, "matched_source", 0, 1, HASH_A,
        "review:synthetic:0001", HASH_B,
    )
    assert decision.reviewer_id == "reviewer-1"
    with pytest.raises(InvalidTransition):
        replace(decision, proposal_state_before=FieldState.CONFIRMED)


def test_optimistic_concurrency_rejects_stale_review():
    ensure_expected_revision(2, 2)
    with pytest.raises(RevisionConflict) as error:
        ensure_expected_revision(1, 2)
    assert (error.value.expected, error.value.actual) == (1, 2)


def test_scope_is_tenant_and_organization_bound():
    require_same_scope(document_version(), invoice())
    other = invoice(scope=Scope("tenant-synthetic", "other-org"))
    with pytest.raises(ScopeMismatch):
        require_same_scope(document_version(), other)


def test_invoice_versions_are_immutable_and_revision_linked():
    first = invoice()
    second = invoice(id="iv-2", revision=2, predecessor_id=first.id)
    assert second.predecessor_id == first.id
    with pytest.raises(ContractError):
        invoice(revision=2)
    with pytest.raises(ContractError):
        invoice(confirmed_fields=(("x", 1), ("x", 2)))
    with pytest.raises(ContractError):
        invoice(confirmed_fields=(("mutable", {"nested": "value"}),))
    with pytest.raises(ContractError):
        invoice(confirmed_fields=())
    with pytest.raises(ContractError):
        invoice(review_decision_ids=())
    with pytest.raises(ContractError):
        invoice(source_hashes=(HASH_A, HASH_B))


def test_idempotency_replay_and_collision():
    assert check_idempotent(HASH_A, HASH_A)
    with pytest.raises(IdempotencyConflict):
        check_idempotent(HASH_A, HASH_B)
    assert fingerprint_json({"b": 2, "a": 1}) == fingerprint_json({"a": 1, "b": 2})


def test_successful_export_requires_artifact_and_reconciliation():
    profile = ExportProfile("ep-1", SCOPE, 1, "generic", "1", HASH_A, NOW)
    artifact = ExportArtifact("text/plain", HASH_B, 10, "opaque://exports/e-1")
    reconciliation = ReconciliationResult(1, 1, 0, HASH_A, HASH_A)
    run = ExportRun(
        "export-1", SCOPE, "iv-1", profile.id, profile.version,
        "export:synthetic:0001", HASH_A, RunStatus.SUCCEEDED, "actor-1", NOW,
        artifact, reconciliation,
    )
    assert run.reconciliation.exported_record_count == 1
    with pytest.raises(ContractError):
        replace(run, artifact=None)
    with pytest.raises(ContractError):
        replace(run, status=RunStatus.FAILED)


def test_audit_event_has_only_opaque_reference_and_serializes_strictly():
    event = AuditEvent(
        "audit-1", SCOPE, "actor-1", AuditAction.PROPOSAL_REVIEWED, "invoice:opaque-1",
        NOW, AuditResult.SUCCEEDED, "corr-1", "human_confirmed",
    )
    encoded = to_json_dict(event)
    assert encoded["type"] == "AuditEvent"
    assert encoded["scope"] == {"tenant_id": "tenant-synthetic", "organization_id": "org-synthetic"}
    assert encoded["occurred_at"].endswith("+00:00")
    assert "SYNTH-001" not in str(encoded)


def test_adversarial_values_fail_closed():
    with pytest.raises(ContractError):
        Scope("", "org")
    with pytest.raises(ContractError):
        proposal(value=float("nan"))
    with pytest.raises(ContractError):
        ReconciliationResult(-1, 0, 0, HASH_A, HASH_A)
    with pytest.raises(ContractError):
        ReconciliationResult(2, 1, 0, HASH_A, HASH_A)
    with pytest.raises(ContractError):
        ReconciliationResult(1, 1, 0, HASH_A, HASH_B)
    with pytest.raises(ContractError):
        document_version(protected_storage_ref="file:///private/invoice.pdf")
    with pytest.raises(ContractError):
        document_version(media_type="text/html")
    with pytest.raises(ContractError):
        AuthorizationContext("", SCOPE, "corr-1")


class RecordingAuthorization:
    def __init__(self, denied=False, return_value=None):
        self.denied = denied
        self.return_value = return_value
        self.calls = []

    def authorize(self, context, action, resource_scope, opaque_resource_ref):
        self.calls.append((context, action, resource_scope, opaque_resource_ref))
        if self.denied:
            raise PermissionError("denied")
        return self.return_value


def context(scope=SCOPE):
    return AuthorizationContext("reviewer-1", scope, "correlation-1")


def reviewed_confirmation(auth=None, *, replacement_value=None):
    auth = auth or RecordingAuthorization()
    return review_proposal(
        auth,
        context(),
        proposal(),
        decision_id="review-1",
        outcome=ReviewOutcome.CONFIRM,
        reason_code="matched_source",
        expected_record_revision=0,
        actual_record_revision=0,
        expected_proposal_revision=1,
        idempotency_key="review:synthetic:factory1",
        replacement_value=replacement_value,
        occurred_at=NOW,
        audit_event_id="audit-review-1",
    )


def test_start_extraction_authorizes_before_outcome_and_replays_safely():
    auth = RecordingAuthorization()
    kwargs = dict(
        run_id="extract-1",
        engine="synthetic",
        engine_version="1",
        config_sha256=HASH_B,
        idempotency_key="extract:synthetic:0001",
        occurred_at=NOW,
        audit_event_id="audit-extract-1",
    )
    first = start_extraction(auth, context(), document_version(), **kwargs)
    assert auth.calls[0][1] is AuthorizationAction.EXTRACT
    assert first.audit_event.result is AuditResult.SUCCEEDED
    replay = start_extraction(auth, context(), document_version(), existing=first.value, **kwargs)
    assert replay.value is first.value and replay.replayed
    with pytest.raises(IdempotencyConflict):
        start_extraction(
            auth,
            context(),
            document_version(),
            existing=first.value,
            **{**kwargs, "engine_version": "2"},
        )


def test_denied_review_produces_no_decision_or_audit():
    auth = RecordingAuthorization(denied=True)
    with pytest.raises(PermissionError):
        reviewed_confirmation(auth)
    assert len(auth.calls) == 1


def test_review_service_binds_fingerprint_revision_and_replacement_semantics():
    result = reviewed_confirmation(replacement_value="SYNTH-CORRECTED")
    decision, state = result.value
    assert state is FieldState.CONFIRMED
    assert decision.proposal_fingerprint == fingerprint_json(to_json_dict(proposal()))
    assert decision.replacement_value == "SYNTH-CORRECTED"
    replay = review_proposal(
        RecordingAuthorization(), context(), proposal(), decision_id="ignored-on-replay",
        outcome=ReviewOutcome.CONFIRM, reason_code="matched_source",
        expected_record_revision=0, actual_record_revision=0,
        expected_proposal_revision=1, idempotency_key="review:synthetic:factory1",
        replacement_value="SYNTH-CORRECTED", occurred_at=NOW,
        audit_event_id="audit-review-replay", existing=decision,
    )
    assert replay.replayed and replay.value[0] is decision
    with pytest.raises(IdempotencyConflict):
        review_proposal(
            RecordingAuthorization(), context(), proposal(), decision_id="collision",
            outcome=ReviewOutcome.CONFIRM, reason_code="matched_source",
            expected_record_revision=0, actual_record_revision=0,
            expected_proposal_revision=1, idempotency_key="review:synthetic:factory1",
            replacement_value="DIFFERENT", occurred_at=NOW,
            audit_event_id="audit-review-collision", existing=decision,
        )
    with pytest.raises(RevisionConflict):
        review_proposal(
            RecordingAuthorization(), context(), proposal(), decision_id="r-2",
            outcome=ReviewOutcome.CONFIRM, reason_code="matched_source",
            expected_record_revision=1, actual_record_revision=0,
            expected_proposal_revision=1, idempotency_key="review:synthetic:stale1",
            replacement_value=None,
            occurred_at=NOW, audit_event_id="audit-r-2",
        )
    with pytest.raises(ContractError):
        ReviewDecision(
            "r-3", SCOPE, "fp-1", FieldState.PROPOSED, ReviewOutcome.REJECT,
            "reviewer-1", NOW, "not_applicable", 0, 1, HASH_A,
            "review:synthetic:reject1", HASH_B, "forbidden",
        )


def test_record_factory_requires_authorized_fingerprint_bound_confirmations():
    auth = RecordingAuthorization()
    decision, _ = reviewed_confirmation().value
    result = create_invoice_record_version(
        auth,
        context(),
        (proposal(),),
        (decision,),
        invoice_record_id="invoice-1",
        version_id="iv-factory-1",
        idempotency_key="record:synthetic:factory1",
        expected_record_revision=0,
        current=None,
        occurred_at=NOW,
        audit_event_id="audit-record-1",
    )
    assert result.value.confirmed_fields == (("invoice.reference", "SYNTH-001"),)
    assert auth.calls[0][1] is AuthorizationAction.REVIEW
    with pytest.raises(ContractError):
        create_invoice_record_version(
            auth, context(), (proposal(value="TAMPERED"),), (decision,),
            invoice_record_id="invoice-1", version_id="iv-tampered",
            idempotency_key="record:synthetic:tampered", expected_record_revision=0,
            current=None, occurred_at=NOW, audit_event_id="audit-tampered",
        )


class SyntheticExporter:
    def __init__(self, *, wrong_scope=False):
        self.called = False
        self.wrong_scope = wrong_scope

    def export(self, ctx, inv, profile, idempotency_key):
        self.called = True
        export_scope = Scope("tenant-synthetic", "other-org") if self.wrong_scope else ctx.scope
        input_fingerprint = fingerprint_json(
            {
                "invoice_record_version_id": inv.id,
                "invoice_input_fingerprint": inv.input_fingerprint,
                "export_profile_id": profile.id,
                "export_profile_version": profile.version,
                "export_config_sha256": profile.config_sha256,
            }
        )
        return ExportRun(
            "export-factory-1", export_scope, inv.id, profile.id, profile.version,
            idempotency_key, input_fingerprint, RunStatus.SUCCEEDED, ctx.actor_id, NOW,
            ExportArtifact("text/plain", HASH_B, 10, "opaque://exports/export-factory-1"),
            ReconciliationResult(1, 1, 0, HASH_A, HASH_A),
        )


def test_export_service_authorizes_before_adapter_and_rejects_unbound_output():
    profile = ExportProfile("ep-1", SCOPE, 1, "generic", "1", HASH_A, NOW)
    auth = RecordingAuthorization(denied=True)
    adapter = SyntheticExporter()
    with pytest.raises(PermissionError):
        authorized_export(
            auth, adapter, context(), invoice(), profile,
            idempotency_key="export:synthetic:factory1", expected_invoice_revision=1,
            occurred_at=NOW, audit_event_id="audit-export-1",
        )
    assert not adapter.called
    with pytest.raises(ScopeMismatch):
        authorized_export(
            RecordingAuthorization(), SyntheticExporter(wrong_scope=True), context(), invoice(), profile,
            idempotency_key="export:synthetic:factory1", expected_invoice_revision=1,
            occurred_at=NOW, audit_event_id="audit-export-2",
        )
    good = authorized_export(
        RecordingAuthorization(), SyntheticExporter(), context(), invoice(), profile,
        idempotency_key="export:synthetic:factory1", expected_invoice_revision=1,
        occurred_at=NOW, audit_event_id="audit-export-3",
    )
    assert good.audit_event.action is AuditAction.EXPORTED


def test_ambiguous_authorization_return_fails_closed_before_adapter():
    profile = ExportProfile("ep-1", SCOPE, 1, "generic", "1", HASH_A, NOW)
    adapter = SyntheticExporter()
    with pytest.raises(ContractError, match="authorization boundary"):
        authorized_export(
            RecordingAuthorization(return_value=False), adapter, context(), invoice(), profile,
            idempotency_key="export:synthetic:factory2", expected_invoice_revision=1,
            occurred_at=NOW, audit_event_id="audit-export-false",
        )
    assert not adapter.called


def test_audit_and_reconciliation_are_content_free_and_explicit():
    with pytest.raises(ContractError):
        AuditEvent(
            "audit-2", SCOPE, "actor-1", AuditAction.EXPORTED,
            "invoice:/path/or content", NOW, AuditResult.SUCCEEDED, "corr-1",
        )
    with pytest.raises(ContractError):
        AuditEvent(
            "audit-3", SCOPE, "actor-1", "custom.action", "invoice:opaque-1",
            NOW, AuditResult.SUCCEEDED, "corr-1",
        )
    partial = ReconciliationResult(2, 1, 1, HASH_A, HASH_B, ("record_rejected",))
    assert partial.rejected_record_count == 1
    with pytest.raises(ContractError):
        ExportArtifact("text/html", HASH_A, 1, "opaque://exports/x")
