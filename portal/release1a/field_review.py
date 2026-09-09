"""Revision-bound human field review; OCR remains a proposal until explicit POST."""
import json
from hmac import compare_digest

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from src.document_core.interpretation import valid_value
from src.document_core.serialization import result_hash
from .document_intake import authorize, read_result
from .models import (Document, DocumentRegionAssociation, FieldDecision,
                     FieldProposal, OcrRun, Organization, Worker, WorkerIdentityRevision)
from .services import Forbidden, StaleWrite, confirm_field_proposal


def _record(instance):
    if instance is None:
        return None
    values = {field.attname: getattr(instance, field.attname)
              for field in instance._meta.concrete_fields}
    return json.loads(json.dumps(values, cls=DjangoJSONEncoder))


def _context(user, organization, proposal_id, *, lock=False):
    query = FieldProposal.objects.filter(organization=organization)
    if lock:
        query = query.select_for_update()
    try:
        proposal = query.get(pk=proposal_id)
    except (FieldProposal.DoesNotExist, ValueError, TypeError):
        raise StaleWrite("FIELD_REVIEW_UNAVAILABLE") from None
    version, run = proposal.version, proposal.ocr_run
    if version.organization_id != organization.pk or version.document_id != proposal.document_id:
        raise Forbidden("cross-organization proposal source")
    if run is not None:
        if (run.organization_id != organization.pk or run.document_id != proposal.document_id
                or run.version_id != version.pk):
            raise Forbidden("cross-organization OCR source")
        if lock:
            # Match OCR completion's run-before-document lock order.
            run = OcrRun.objects.select_for_update().get(pk=run.pk, organization=organization)
    documents = Document.objects.filter(organization=organization)
    if lock:
        documents = documents.select_for_update()
    try:
        document = documents.get(pk=proposal.document_id)
    except Document.DoesNotExist:
        raise Forbidden("cross-organization proposal source") from None
    latest = document.documentversion_set.order_by("-version_number").first()
    if latest is None or latest.organization_id != organization.pk:
        raise Forbidden("cross-organization version")
    if latest.pk != version.pk or FieldDecision.objects.filter(field_proposal=proposal).exists():
        raise StaleWrite("FIELD_REVIEW_STALE")
    if proposal.state not in (FieldProposal.State.PROPOSED, FieldProposal.State.CONFLICT):
        raise ValueError("FIELD_PROPOSAL_NOT_REVIEWABLE")
    if run is not None:
        if (run.organization_id != organization.pk or run.document_id != document.pk
                or run.version_id != version.pk):
            raise Forbidden("cross-organization OCR source")
        if run.state != OcrRun.State.COMPLETED or not run.output_key:
            raise StaleWrite("OCR_SOURCE_NOT_READY")
        payload = read_result(user, organization, run.pk)
        if payload.get("status") != "completed" or payload.get("source_hash") != version.sha256:
            raise StaleWrite("OCR_SOURCE_NOT_READY")
    association = None
    if proposal.document_region_id:
        association = DocumentRegionAssociation.objects.filter(
            organization=organization, ocr_run=run,
            region_id=proposal.document_region_id).first()
        if association is None:
            raise ValueError("REGION_ASSOCIATION_REQUIRED")
        worker_id = association.worker_id
    else:
        worker_id = document.worker_id
    if worker_id is None:
        raise ValueError("WORKER_ASSOCIATION_REQUIRED")
    workers = Worker.objects.filter(organization=organization)
    if lock:
        workers = workers.select_for_update()
    try:
        worker = workers.get(pk=worker_id)
    except Worker.DoesNotExist:
        raise Forbidden("cross-organization worker") from None
    revision = WorkerIdentityRevision.objects.filter(
        organization=organization, worker=worker).order_by("-revision_number", "-pk").first()
    snapshot = {"contract": "field-review-v1", "organization_id": organization.pk,
                "proposal": _record(proposal), "document": _record(document),
                "version": _record(version), "run": _record(run),
                "association": _record(association), "worker": _record(worker),
                "identity_revision": _record(revision)}
    confirmed = revision.confirmed_fields.get(proposal.field_name) if revision else None
    return proposal, worker, {"token": result_hash(snapshot), "confirmed_value": confirmed}


def review_context(user, organization, proposal_ids):
    """Return opaque review tokens and currently confirmed values for scoped proposals."""
    if not user.is_active:
        raise Forbidden("ACTIVE_OPERATOR_REQUIRED")
    authorize(user, organization, "document:confirm")
    return {proposal_id: _context(user, organization, proposal_id)[2]
            for proposal_id in proposal_ids}


@transaction.atomic
def confirm_review_batch(user, organization, selections, *, reason=""):
    """Validate the whole displayed revision before applying any human decisions."""
    if not user.is_active:
        raise Forbidden("ACTIVE_OPERATOR_REQUIRED")
    authorize(user, organization, "document:confirm")
    Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
    if not isinstance(selections, list) or not selections or not isinstance(reason, str):
        raise ValueError("INVALID_FIELD_REVIEW_SELECTION")
    if any(not isinstance(item, dict) or type(item.get("proposal_id")) is not int
           for item in selections):
        raise ValueError("INVALID_FIELD_REVIEW_SELECTION")
    # Acquire every run before any document: a second run may be completing for
    # the same document while this batch covers several of its proposals.
    run_ids = FieldProposal.objects.filter(
        organization=organization, pk__in=[item["proposal_id"] for item in selections]
    ).values_list("ocr_run_id", flat=True)
    list(OcrRun.objects.select_for_update().filter(
        organization=organization, pk__in=run_ids).order_by("pk"))
    prepared, seen, values = [], set(), {}
    for selection in selections:
        if not isinstance(selection, dict):
            raise ValueError("INVALID_FIELD_REVIEW_SELECTION")
        proposal_id = selection.get("proposal_id")
        token, value = selection.get("expected_token"), selection.get("value")
        if type(proposal_id) is not int or proposal_id in seen or not isinstance(value, str):
            raise ValueError("INVALID_FIELD_REVIEW_SELECTION")
        seen.add(proposal_id)
        proposal, worker, context = _context(user, organization, proposal_id, lock=True)
        if not isinstance(token, str) or not token.isascii() or not compare_digest(token, context["token"]):
            raise StaleWrite("FIELD_REVIEW_STALE")
        if not value.strip():
            raise ValueError("EMPTY_VALUE")
        normalized, findings = valid_value(proposal.field_name, value)
        if findings:
            raise ValueError("INVALID_FIELD_VALUE")
        key = (worker.pk, proposal.field_name)
        if key in values and values[key] != normalized:
            raise ValueError("CONFLICTING_FIELD_SELECTIONS")
        values[key] = normalized
        confirmed = context["confirmed_value"]
        if (proposal.validation_findings or (confirmed is not None and confirmed != normalized)) and not reason.strip():
            raise ValueError("CONFLICT_REASON_REQUIRED")
        prepared.append((proposal, normalized))
    return [confirm_field_proposal(user, organization, proposal, corrected_value=value, reason=reason)
            for proposal, value in prepared]
