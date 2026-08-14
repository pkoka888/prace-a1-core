"""Immutable contracts for the Plan AD invoice-ingestion boundary.

The module intentionally has no database, web-framework, OCR-engine, tax, or
accounting-system dependency.  Adapters must enforce authorization before they
read content or perform extraction/export; domain objects merely carry the
scope and provenance required to make that enforcement auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Protocol, runtime_checkable


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_OPAQUE_REF = re.compile(r"^[a-z][a-z0-9_.-]{1,31}:[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
_PROTECTED_REF = re.compile(r"^opaque://(?:documents|exports)/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DOCUMENT_MEDIA_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png", "image/tiff"})
_EXPORT_MEDIA_TYPES = frozenset({"text/csv", "text/plain", "application/json"})


class ContractError(ValueError):
    """Base error for a rejected domain-contract operation."""


class ScopeMismatch(ContractError):
    pass


class InvalidTransition(ContractError):
    pass


class RevisionConflict(ContractError):

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"revision conflict: expected {expected}, actual {actual}")
        self.expected = expected
        self.actual = actual


class IdempotencyConflict(ContractError):
    pass


class FieldState(str, Enum):
    MISSING = "missing"
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CONFLICT = "conflict"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class FindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ReviewOutcome(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    CONFLICT = "conflict"


class AuthorizationAction(str, Enum):
    READ_DOCUMENT = "read_document"
    EXTRACT = "extract"
    REVIEW = "review"
    EXPORT = "export"


class AuditAction(str, Enum):
    EXTRACTION_STARTED = "invoice.extraction_started"
    PROPOSAL_REVIEWED = "invoice.proposal_reviewed"
    RECORD_VERSION_CREATED = "invoice.record_version_created"
    EXPORTED = "invoice.exported"


class AuditResult(str, Enum):
    SUCCEEDED = "succeeded"
    REPLAYED = "replayed"


@dataclass(frozen=True, slots=True)
class Scope:
    tenant_id: str
    organization_id: str

    def __post_init__(self) -> None:
        _identity(self.tenant_id, self.organization_id)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.page < 1 or self.x0 < 0 or self.y0 < 0:
            raise ContractError("page is one-based and bounding-box coordinates are non-negative")
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ContractError("bounding box must have positive area")


@dataclass(frozen=True, slots=True)
class Provenance:
    document_version_id: str
    source_sha256: str
    engine: str
    engine_version: str
    config_sha256: str
    locations: tuple[BoundingBox, ...] = ()

    def __post_init__(self) -> None:
        _nonempty("document_version_id", self.document_version_id)
        _hash("source_sha256", self.source_sha256)
        _nonempty("engine", self.engine)
        _nonempty("engine_version", self.engine_version)
        _hash("config_sha256", self.config_sha256)


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    scope: Scope
    declared_purpose: str
    created_by: str
    created_at: datetime
    retention_review_at: datetime

    def __post_init__(self) -> None:
        _identity(self.id, self.created_by)
        _nonempty("declared_purpose", self.declared_purpose)
        _aware(self.created_at)
        _aware(self.retention_review_at)
        if self.retention_review_at <= self.created_at:
            raise ContractError("retention review must follow document creation")


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    id: str
    document_id: str
    scope: Scope
    version: int
    source_sha256: str
    media_type: str
    size_bytes: int
    protected_storage_ref: str
    created_by: str
    created_at: datetime
    predecessor_id: str | None = None

    def __post_init__(self) -> None:
        _identity(self.id, self.document_id, self.created_by)
        _hash("source_sha256", self.source_sha256)
        _media_type(self.media_type, _DOCUMENT_MEDIA_TYPES)
        _protected_ref(self.protected_storage_ref)
        _aware(self.created_at)
        if self.version < 1 or self.size_bytes < 1:
            raise ContractError("document version and size must be positive")
        if self.version > 1 and not self.predecessor_id:
            raise ContractError("later document versions require a predecessor")


@dataclass(frozen=True, slots=True)
class ExtractionRun:
    id: str
    scope: Scope
    document_version_id: str
    source_sha256: str
    engine: str
    engine_version: str
    config_sha256: str
    idempotency_key: str
    input_fingerprint: str
    status: RunStatus
    created_at: datetime

    def __post_init__(self) -> None:
        _identity(self.id, self.document_version_id)
        _hash("source_sha256", self.source_sha256)
        _hash("config_sha256", self.config_sha256)
        _hash("input_fingerprint", self.input_fingerprint)
        _nonempty("engine", self.engine)
        _nonempty("engine_version", self.engine_version)
        _idempotency(self.idempotency_key)
        _enum("status", self.status, RunStatus)
        _aware(self.created_at)


@dataclass(frozen=True, slots=True)
class FieldProposal:
    id: str
    scope: Scope
    extraction_run_id: str
    field_name: str
    value: Any
    state: FieldState
    confidence: float | None
    provenance: Provenance
    created_at: datetime
    revision: int = 1
    supersedes_id: str | None = None

    def __post_init__(self) -> None:
        _identity(self.id, self.extraction_run_id)
        _nonempty("field_name", self.field_name)
        _json_value(self.value)
        _enum("state", self.state, FieldState)
        _aware(self.created_at)
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ContractError("confidence must be between 0 and 1")
        if self.revision < 1:
            raise ContractError("proposal revision must be positive")
        if self.state not in {FieldState.MISSING, FieldState.PROPOSED, FieldState.CONFLICT}:
            raise ContractError("extractors may construct only missing/proposed/conflict proposals")
        if self.state is FieldState.MISSING and self.value is not None:
            raise ContractError("missing proposals cannot carry a value")
        if self.state is not FieldState.MISSING and self.value is None:
            raise ContractError("non-missing proposals require a value")


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    id: str
    scope: Scope
    proposal_id: str
    rule_id: str
    rule_version: str
    severity: FindingSeverity
    code: str
    message_key: str
    created_at: datetime

    def __post_init__(self) -> None:
        _identity(self.id, self.proposal_id)
        for name in ("rule_id", "rule_version", "code", "message_key"):
            _nonempty(name, getattr(self, name))
        _enum("severity", self.severity, FindingSeverity)
        _aware(self.created_at)


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    id: str
    scope: Scope
    proposal_id: str
    proposal_state_before: FieldState
    outcome: ReviewOutcome
    reviewer_id: str
    decided_at: datetime
    reason_code: str
    expected_record_revision: int
    expected_proposal_revision: int
    proposal_fingerprint: str
    idempotency_key: str
    input_fingerprint: str
    replacement_value: Any | None = None

    def __post_init__(self) -> None:
        _identity(self.id, self.proposal_id, self.reviewer_id)
        _reason_code(self.reason_code)
        _enum("proposal state", self.proposal_state_before, FieldState)
        _enum("review outcome", self.outcome, ReviewOutcome)
        _aware(self.decided_at)
        if self.expected_record_revision < 0 or self.expected_proposal_revision < 1:
            raise ContractError("expected revisions are invalid")
        _hash("proposal_fingerprint", self.proposal_fingerprint)
        _idempotency(self.idempotency_key)
        _hash("input_fingerprint", self.input_fingerprint)
        _json_value(self.replacement_value)
        if self.outcome is ReviewOutcome.CONFIRM and self.proposal_state_before not in {
            FieldState.PROPOSED,
            FieldState.CONFLICT,
        }:
            raise InvalidTransition("only proposed/conflict fields can be confirmed")
        if self.outcome is not ReviewOutcome.CONFIRM and self.replacement_value is not None:
            raise ContractError("only confirmation may carry a replacement value")


@dataclass(frozen=True, slots=True)
class InvoiceRecordVersion:
    id: str
    invoice_record_id: str
    scope: Scope
    revision: int
    predecessor_id: str | None
    source_document_version_ids: tuple[str, ...]
    source_hashes: tuple[str, ...]
    confirmed_fields: tuple[tuple[str, Any], ...]
    review_decision_ids: tuple[str, ...]
    idempotency_key: str
    input_fingerprint: str
    created_by: str
    created_at: datetime

    def __post_init__(self) -> None:
        _identity(self.id, self.invoice_record_id, self.created_by)
        _aware(self.created_at)
        if self.revision < 1:
            raise ContractError("invoice revision must be positive")
        if self.revision > 1 and not self.predecessor_id:
            raise ContractError("later invoice revisions require a predecessor")
        _idempotency(self.idempotency_key)
        _hash("input_fingerprint", self.input_fingerprint)
        if not self.source_document_version_ids or not self.source_hashes:
            raise ContractError("confirmed records require source versions and hashes")
        if len(self.source_document_version_ids) != len(self.source_hashes):
            raise ContractError("every source document version requires exactly one source hash")
        if len(set(self.source_document_version_ids)) != len(self.source_document_version_ids):
            raise ContractError("source document version IDs must be unique")
        for digest in self.source_hashes:
            _hash("source_hash", digest)
        names = [name for name, _ in self.confirmed_fields]
        if not names or not self.review_decision_ids:
            raise ContractError("confirmed records require fields and review decisions")
        if len(set(self.review_decision_ids)) != len(self.review_decision_ids):
            raise ContractError("review decision IDs must be unique")
        if len(set(names)) != len(names):
            raise ContractError("confirmed field names must be unique")
        for name, value in self.confirmed_fields:
            _nonempty("confirmed field name", name)
            _immutable_json_value(value)


@dataclass(frozen=True, slots=True)
class ExportProfile:
    id: str
    scope: Scope
    version: int
    adapter_name: str
    adapter_version: str
    config_sha256: str
    created_at: datetime

    def __post_init__(self) -> None:
        _identity(self.id)
        _nonempty("adapter_name", self.adapter_name)
        _nonempty("adapter_version", self.adapter_version)
        _hash("config_sha256", self.config_sha256)
        _aware(self.created_at)
        if self.version < 1:
            raise ContractError("export profile version must be positive")


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    source_record_count: int
    exported_record_count: int
    rejected_record_count: int
    source_total_fingerprint: str
    exported_total_fingerprint: str
    finding_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for count in (self.source_record_count, self.exported_record_count, self.rejected_record_count):
            if count < 0:
                raise ContractError("reconciliation counts cannot be negative")
        _hash("source_total_fingerprint", self.source_total_fingerprint)
        _hash("exported_total_fingerprint", self.exported_total_fingerprint)
        if self.source_record_count != self.exported_record_count + self.rejected_record_count:
            raise ContractError("source count must equal exported plus rejected count")
        if self.rejected_record_count == 0 and self.source_total_fingerprint != self.exported_total_fingerprint:
            raise ContractError("lossless reconciliation requires matching source/export fingerprints")
        if self.rejected_record_count and not self.finding_codes:
            raise ContractError("rejected records require reconciliation finding codes")


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    media_type: str
    content_sha256: str
    byte_length: int
    protected_storage_ref: str

    def __post_init__(self) -> None:
        _media_type(self.media_type, _EXPORT_MEDIA_TYPES)
        _hash("content_sha256", self.content_sha256)
        _protected_ref(self.protected_storage_ref)
        if self.byte_length < 0:
            raise ContractError("artifact size cannot be negative")


@dataclass(frozen=True, slots=True)
class ExportRun:
    id: str
    scope: Scope
    invoice_record_version_id: str
    export_profile_id: str
    export_profile_version: int
    idempotency_key: str
    input_fingerprint: str
    status: RunStatus
    created_by: str
    created_at: datetime
    artifact: ExportArtifact | None = None
    reconciliation: ReconciliationResult | None = None

    def __post_init__(self) -> None:
        _identity(self.id, self.invoice_record_version_id, self.export_profile_id, self.created_by)
        _idempotency(self.idempotency_key)
        _hash("input_fingerprint", self.input_fingerprint)
        _enum("status", self.status, RunStatus)
        _aware(self.created_at)
        if self.export_profile_version < 1:
            raise ContractError("export profile version must be positive")
        if self.status is RunStatus.SUCCEEDED and (not self.artifact or not self.reconciliation):
            raise ContractError("successful export requires artifact and reconciliation")
        if self.status is not RunStatus.SUCCEEDED and (self.artifact or self.reconciliation):
            raise ContractError("non-successful export cannot claim an artifact or reconciliation")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: str
    scope: Scope
    actor_id: str
    action: AuditAction
    opaque_object_ref: str
    occurred_at: datetime
    result: AuditResult
    correlation_id: str
    reason_code: str | None = None

    def __post_init__(self) -> None:
        _identity(self.id, self.actor_id)
        _enum("audit action", self.action, AuditAction)
        _enum("audit result", self.result, AuditResult)
        _opaque_ref(self.opaque_object_ref)
        _nonempty("correlation_id", self.correlation_id)
        if self.reason_code is not None:
            _reason_code(self.reason_code)
        _aware(self.occurred_at)


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    actor_id: str
    scope: Scope
    correlation_id: str

    def __post_init__(self) -> None:
        _identity(self.actor_id)
        _identity(self.correlation_id)
        if not isinstance(self.scope, Scope):
            raise ContractError("authorization context requires a Scope")


@runtime_checkable
class AuthorizationBoundary(Protocol):
    def authorize(
        self,
        context: AuthorizationContext,
        action: AuthorizationAction,
        resource_scope: Scope,
        opaque_resource_ref: str,
    ) -> None:
        """Return None when allowed; raise and audit at this boundary on denial.

        A denial audit must contain only the controlled action, opaque reference,
        scope, actor, correlation ID, result, and a content-free reason code.
        """


@runtime_checkable
class ExtractionAdapter(Protocol):
    def extract(
        self, context: AuthorizationContext, document_version: DocumentVersion
    ) -> tuple[ExtractionRun, tuple[FieldProposal, ...], tuple[ValidationFinding, ...]]:
        """Produce proposals only; never mutate a confirmed invoice version."""


@runtime_checkable
class ExportAdapter(Protocol):
    def export(
        self,
        context: AuthorizationContext,
        invoice: InvoiceRecordVersion,
        profile: ExportProfile,
        idempotency_key: str,
    ) -> ExportRun:
        """Export one immutable invoice/profile version with reconciliation."""


@dataclass(frozen=True, slots=True)
class OperationResult:
    value: Any
    audit_event: AuditEvent
    replayed: bool = False


def start_extraction(
    authorization: AuthorizationBoundary,
    context: AuthorizationContext,
    document_version: DocumentVersion,
    *,
    run_id: str,
    engine: str,
    engine_version: str,
    config_sha256: str,
    idempotency_key: str,
    occurred_at: datetime,
    audit_event_id: str,
    existing: ExtractionRun | None = None,
) -> OperationResult:
    """Authorize and create/replay an extraction-run boundary object."""
    require_same_scope(context, document_version)
    _idempotency(idempotency_key)
    input_fingerprint = fingerprint_json(
        {
            "document_version_id": document_version.id,
            "source_sha256": document_version.source_sha256,
            "engine": engine,
            "engine_version": engine_version,
            "config_sha256": config_sha256,
        }
    )
    _authorize(authorization, context, AuthorizationAction.EXTRACT, document_version.scope, f"document:{document_version.id}")
    replayed = existing is not None
    if existing is not None:
        require_same_scope(context, existing)
        if existing.document_version_id != document_version.id or existing.source_sha256 != document_version.source_sha256:
            raise ContractError("existing extraction is not bound to this document version")
        if existing.idempotency_key != idempotency_key:
            raise IdempotencyConflict("existing extraction has a different idempotency key")
        check_idempotent(existing.input_fingerprint, input_fingerprint)
        value = existing
    else:
        value = ExtractionRun(
            run_id,
            context.scope,
            document_version.id,
            document_version.source_sha256,
            engine,
            engine_version,
            config_sha256,
            idempotency_key,
            input_fingerprint,
            RunStatus.PENDING,
            occurred_at,
        )
    return OperationResult(
        value,
        _audit(
            audit_event_id,
            context,
            AuditAction.EXTRACTION_STARTED,
            f"extraction:{value.id}",
            occurred_at,
            AuditResult.REPLAYED if replayed else AuditResult.SUCCEEDED,
        ),
        replayed,
    )


def review_proposal(
    authorization: AuthorizationBoundary,
    context: AuthorizationContext,
    proposal: FieldProposal,
    *,
    decision_id: str,
    outcome: ReviewOutcome,
    reason_code: str,
    expected_record_revision: int,
    actual_record_revision: int,
    expected_proposal_revision: int,
    idempotency_key: str,
    replacement_value: Any | None,
    occurred_at: datetime,
    audit_event_id: str,
    existing: ReviewDecision | None = None,
) -> OperationResult:
    """Authorize a human decision and bind it to exact proposal/record revisions."""
    require_same_scope(context, proposal)
    ensure_expected_revision(expected_record_revision, actual_record_revision)
    ensure_expected_revision(expected_proposal_revision, proposal.revision)
    next_state = transition_field_state(proposal.state, outcome)
    _authorize(authorization, context, AuthorizationAction.REVIEW, proposal.scope, f"proposal:{proposal.id}")
    proposal_fingerprint = fingerprint_json(to_json_dict(proposal))
    input_fingerprint = fingerprint_json(
        {
            "proposal_fingerprint": proposal_fingerprint,
            "outcome": outcome.value,
            "reason_code": reason_code,
            "expected_record_revision": expected_record_revision,
            "expected_proposal_revision": expected_proposal_revision,
            "replacement_value": replacement_value,
        }
    )
    replayed = existing is not None
    if existing is not None:
        require_same_scope(context, existing)
        if existing.idempotency_key != idempotency_key or existing.proposal_id != proposal.id:
            raise IdempotencyConflict("existing review is not bound to this key and proposal")
        check_idempotent(existing.input_fingerprint, input_fingerprint)
        decision = existing
    else:
        decision = ReviewDecision(
            decision_id,
            context.scope,
            proposal.id,
            proposal.state,
            outcome,
            context.actor_id,
            occurred_at,
            reason_code,
            expected_record_revision,
            expected_proposal_revision,
            proposal_fingerprint,
            idempotency_key,
            input_fingerprint,
            replacement_value,
        )
    return OperationResult(
        (decision, next_state),
        _audit(
            audit_event_id,
            context,
            AuditAction.PROPOSAL_REVIEWED,
            f"proposal:{proposal.id}",
            occurred_at,
            AuditResult.REPLAYED if replayed else AuditResult.SUCCEEDED,
            reason_code,
        ),
        replayed,
    )


def create_invoice_record_version(
    authorization: AuthorizationBoundary,
    context: AuthorizationContext,
    proposals: tuple[FieldProposal, ...],
    decisions: tuple[ReviewDecision, ...],
    *,
    invoice_record_id: str,
    version_id: str,
    idempotency_key: str,
    expected_record_revision: int,
    current: InvoiceRecordVersion | None,
    occurred_at: datetime,
    audit_event_id: str,
    existing_idempotent: InvoiceRecordVersion | None = None,
) -> OperationResult:
    """Create an immutable reviewed record from fingerprint-bound confirmations."""
    if not proposals or len(proposals) != len(decisions):
        raise ContractError("one confirmation decision is required for every proposal")
    require_same_scope(context, *proposals, *decisions)
    actual_revision = current.revision if current else 0
    if current is not None:
        require_same_scope(context, current)
        if current.invoice_record_id != invoice_record_id:
            raise ContractError("current version belongs to another invoice record")
    ensure_expected_revision(expected_record_revision, actual_revision)
    _authorize(authorization, context, AuthorizationAction.REVIEW, context.scope, f"invoice:{invoice_record_id}")
    decision_by_proposal = {decision.proposal_id: decision for decision in decisions}
    if len(decision_by_proposal) != len(decisions):
        raise ContractError("duplicate review decisions for one proposal")
    confirmed_fields: list[tuple[str, Any]] = []
    source_pairs: list[tuple[str, str]] = []
    for proposal in proposals:
        decision = decision_by_proposal.get(proposal.id)
        if decision is None or decision.outcome is not ReviewOutcome.CONFIRM:
            raise ContractError("every record field requires a confirmation decision")
        if decision.expected_record_revision != actual_revision:
            raise RevisionConflict(decision.expected_record_revision, actual_revision)
        ensure_expected_revision(decision.expected_proposal_revision, proposal.revision)
        if decision.proposal_fingerprint != fingerprint_json(to_json_dict(proposal)):
            raise ContractError("review decision does not bind to the supplied proposal")
        confirmed_fields.append(
            (proposal.field_name, decision.replacement_value if decision.replacement_value is not None else proposal.value)
        )
        source_pairs.append((proposal.provenance.document_version_id, proposal.provenance.source_sha256))
    # Preserve first-seen order while retaining the version/hash pairing.
    unique_source_pairs = tuple(dict.fromkeys(source_pairs))
    payload = {
        "invoice_record_id": invoice_record_id,
        "revision": actual_revision + 1,
        "predecessor_id": current.id if current else None,
        "sources": unique_source_pairs,
        "fields": confirmed_fields,
        "decisions": [decision.id for decision in decisions],
    }
    input_fingerprint = fingerprint_json(payload)
    replayed = existing_idempotent is not None
    if existing_idempotent is not None:
        require_same_scope(context, existing_idempotent)
        if (
            existing_idempotent.invoice_record_id != invoice_record_id
            or existing_idempotent.revision != actual_revision + 1
        ):
            raise ContractError("existing record is not bound to the requested record revision")
        if existing_idempotent.idempotency_key != idempotency_key:
            raise IdempotencyConflict("existing record has a different idempotency key")
        check_idempotent(existing_idempotent.input_fingerprint, input_fingerprint)
        value = existing_idempotent
    else:
        value = InvoiceRecordVersion(
            version_id,
            invoice_record_id,
            context.scope,
            actual_revision + 1,
            current.id if current else None,
            tuple(pair[0] for pair in unique_source_pairs),
            tuple(pair[1] for pair in unique_source_pairs),
            tuple(confirmed_fields),
            tuple(decision.id for decision in decisions),
            idempotency_key,
            input_fingerprint,
            context.actor_id,
            occurred_at,
        )
    return OperationResult(
        value,
        _audit(
            audit_event_id,
            context,
            AuditAction.RECORD_VERSION_CREATED,
            f"invoice:{invoice_record_id}",
            occurred_at,
            AuditResult.REPLAYED if replayed else AuditResult.SUCCEEDED,
        ),
        replayed,
    )


def authorized_export(
    authorization: AuthorizationBoundary,
    adapter: ExportAdapter,
    context: AuthorizationContext,
    invoice: InvoiceRecordVersion,
    profile: ExportProfile,
    *,
    idempotency_key: str,
    expected_invoice_revision: int,
    occurred_at: datetime,
    audit_event_id: str,
    existing: ExportRun | None = None,
) -> OperationResult:
    """Authorize before invoking an exporter and validate its bound result."""
    require_same_scope(context, invoice, profile)
    ensure_expected_revision(expected_invoice_revision, invoice.revision)
    _idempotency(idempotency_key)
    expected_fingerprint = fingerprint_json(
        {
            "invoice_record_version_id": invoice.id,
            "invoice_input_fingerprint": invoice.input_fingerprint,
            "export_profile_id": profile.id,
            "export_profile_version": profile.version,
            "export_config_sha256": profile.config_sha256,
        }
    )
    _authorize(authorization, context, AuthorizationAction.EXPORT, invoice.scope, f"invoice:{invoice.invoice_record_id}")
    replayed = existing is not None
    if existing is not None:
        require_same_scope(context, existing)
        if existing.idempotency_key != idempotency_key:
            raise IdempotencyConflict("existing export has a different idempotency key")
        check_idempotent(existing.input_fingerprint, expected_fingerprint)
        value = existing
    else:
        value = adapter.export(context, invoice, profile, idempotency_key)
        require_same_scope(context, value)
    if (
        value.invoice_record_version_id != invoice.id
        or value.export_profile_id != profile.id
        or value.export_profile_version != profile.version
        or value.created_by != context.actor_id
        or value.status is not RunStatus.SUCCEEDED
    ):
        raise ContractError("export result is unbound or unsuccessful")
    check_idempotent(value.input_fingerprint, expected_fingerprint)
    return OperationResult(
        value,
        _audit(
            audit_event_id,
            context,
            AuditAction.EXPORTED,
            f"export:{value.id}",
            occurred_at,
            AuditResult.REPLAYED if replayed else AuditResult.SUCCEEDED,
        ),
        replayed,
    )


def require_same_scope(*scoped: Any) -> Scope:
    if not scoped:
        raise ContractError("at least one scoped object is required")
    expected = scoped[0].scope
    if any(item.scope != expected for item in scoped[1:]):
        raise ScopeMismatch("cross-tenant or cross-organization operation denied")
    return expected


def ensure_expected_revision(expected: int, actual: int) -> None:
    if expected != actual:
        raise RevisionConflict(expected, actual)


def transition_field_state(current: FieldState, outcome: ReviewOutcome) -> FieldState:
    allowed = {
        (FieldState.PROPOSED, ReviewOutcome.CONFIRM): FieldState.CONFIRMED,
        (FieldState.PROPOSED, ReviewOutcome.REJECT): FieldState.REJECTED,
        (FieldState.PROPOSED, ReviewOutcome.CONFLICT): FieldState.CONFLICT,
        (FieldState.CONFLICT, ReviewOutcome.CONFIRM): FieldState.CONFIRMED,
        (FieldState.CONFLICT, ReviewOutcome.REJECT): FieldState.REJECTED,
    }
    try:
        return allowed[(current, outcome)]
    except KeyError as exc:
        raise InvalidTransition(f"cannot apply {outcome.value} to {current.value}") from exc


def check_idempotent(existing_fingerprint: str, requested_fingerprint: str) -> bool:
    """Return True for a safe replay; raise when one key represents other input."""
    _hash("existing_fingerprint", existing_fingerprint)
    _hash("requested_fingerprint", requested_fingerprint)
    if existing_fingerprint != requested_fingerprint:
        raise IdempotencyConflict("idempotency key was already used for different input")
    return True


def _authorize(
    boundary: AuthorizationBoundary,
    context: AuthorizationContext,
    action: AuthorizationAction,
    resource_scope: Scope,
    opaque_ref: str,
) -> None:
    _opaque_ref(opaque_ref)
    result = boundary.authorize(context, action, resource_scope, opaque_ref)
    if result is not None:
        raise ContractError("authorization boundary must explicitly allow by returning None")


def _audit(
    event_id: str,
    context: AuthorizationContext,
    action: AuditAction,
    opaque_ref: str,
    occurred_at: datetime,
    result: AuditResult,
    reason_code: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id,
        context.scope,
        context.actor_id,
        action,
        opaque_ref,
        occurred_at,
        result,
        context.correlation_id,
        reason_code,
    )


def fingerprint_json(value: Any) -> str:
    """Return a stable digest for a JSON-compatible request or configuration."""
    _json_value(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def to_json_dict(value: Any) -> dict[str, Any]:
    """Strict, deterministic JSON-compatible representation of a contract object."""
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError("a dataclass instance is required")
    result = {field.name: _to_json(getattr(value, field.name)) for field in fields(value)}
    # A type discriminator avoids ambiguous persistence/event envelopes.
    return {"type": value.__class__.__name__, **result}


def _to_json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        _aware(value)
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _to_json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_to_json(item) for item in value]
    if isinstance(value, list):
        return [_to_json(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _to_json(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _identity(*values: str) -> None:
    for value in values:
        if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
            raise ContractError("identifier must be an opaque safe token")


def _nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} must be a non-empty string")


def _hash(name: str, value: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ContractError(f"{name} must be a lowercase SHA-256 digest")


def _idempotency(value: str) -> None:
    if not isinstance(value, str) or not _IDEMPOTENCY_KEY.fullmatch(value):
        raise ContractError("invalid idempotency key")


def _opaque_ref(value: str) -> None:
    if not isinstance(value, str) or not _OPAQUE_REF.fullmatch(value):
        raise ContractError("object reference must be opaque and contain no path or content")


def _reason_code(value: str) -> None:
    if not isinstance(value, str) or not _REASON_CODE.fullmatch(value):
        raise ContractError("reason must be a controlled content-free code")


def _protected_ref(value: str) -> None:
    if not isinstance(value, str) or not _PROTECTED_REF.fullmatch(value):
        raise ContractError("storage reference must use an allowed opaque protected namespace")


def _media_type(value: str, allowed: frozenset[str]) -> None:
    if value not in allowed:
        raise ContractError(f"unsupported media type: {value!r}")


def _enum(name: str, value: Any, expected: type[Enum]) -> None:
    if not isinstance(value, expected):
        raise ContractError(f"{name} must be a {expected.__name__}")


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("timestamps must be timezone-aware")


def _json_value(value: Any) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractError("value must be strictly JSON-compatible") from exc


def _immutable_json_value(value: Any) -> None:
    """Accept JSON-shaped scalar/tuple data without mutable nested containers."""
    if isinstance(value, (dict, list, set)):
        raise ContractError("immutable record values must not contain mutable containers")
    if isinstance(value, tuple):
        for item in value:
            _immutable_json_value(item)
    _json_value(value)


__all__ = [name for name in globals() if not name.startswith("_") and name not in {"Any", "Mapping", "Protocol"}]
