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


def _context(user, organization, proposal_id, *, lock=False, allow_decided=False):
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
    if latest.pk != version.pk or (not allow_decided and FieldDecision.objects.filter(field_proposal=proposal).exists()):
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


ADDRESS_FIELDS = ('street', 'house_number', 'city', 'postal_code', 'country_code')


def _address_context(user, organization, proposal_id, *, lock=False):
    proposal, worker, context = _context(user, organization, proposal_id,
        lock=lock, allow_decided=True)
    if proposal.field_name != 'residence_address' or worker.state == Worker.State.ARCHIVED:
        raise ValueError('ADDRESS_SOURCE_REQUIRED')
    revision = WorkerIdentityRevision.objects.filter(organization=organization,
        worker=worker).order_by('-revision_number', '-pk').first()
    fields = revision.confirmed_fields if revision else {}
    return proposal, worker, {**context, 'values': {f: fields.get(f, '') for f in ADDRESS_FIELDS}}


@transaction.atomic
def address_review_context(user, organization, proposal_id):
    from .identity import _authorize, _lock_organization
    _authorize(user, organization, 'document:confirm')
    _lock_organization(organization)
    return _address_context(user, organization, proposal_id)[2]


@transaction.atomic
def confirm_address_review(user, organization, proposal_id, expected_token, values, *, reason=''):
    """Record explicitly entered source-linked fields; never label them as OCR output."""
    from .identity import _authorize, _lock_organization
    from .document_intake import audit
    from .models import A1Case
    import re
    import unicodedata
    _authorize(user, organization, 'document:confirm')
    _lock_organization(organization)
    proposal, worker, context = _address_context(user, organization, proposal_id, lock=True)
    if (not isinstance(expected_token, str) or not expected_token.isascii()
            or not compare_digest(expected_token, context['token'])):
        raise StaleWrite('ADDRESS_REVIEW_STALE')
    if (not isinstance(values, dict) or set(values) != set(ADDRESS_FIELDS)
            or not isinstance(reason, str)):
        raise ValueError('ADDRESS_FIELDS_REQUIRED')
    limits = dict(street=240, house_number=40, city=120, postal_code=20, country_code=2)
    normalized = {}
    for field, value in values.items():
        if (not isinstance(value, str) or not value.strip() or len(value.strip()) > limits[field]
                or any(unicodedata.category(c).startswith('C') for c in value)):
            raise ValueError('ADDRESS_VALUE_INVALID')
        normalized[field] = value.strip()
    normalized['country_code'] = normalized['country_code'].upper()
    if not re.fullmatch('[A-Z]{2}', normalized['country_code']):
        raise ValueError('ADDRESS_COUNTRY_INVALID')
    if (proposal.validation_findings or any(context['values'][f] and context['values'][f] != normalized[f]
            for f in ADDRESS_FIELDS)) and not reason.strip():
        raise ValueError('CONFLICT_REASON_REQUIRED')
    if context['values'] == normalized:
        return []
    decisions = []
    for field in ADDRESS_FIELDS:
        entered = FieldProposal.objects.create(organization=organization,
            document=proposal.document, version=proposal.version, ocr_run=proposal.ocr_run,
            document_region_id=proposal.document_region_id, field_name=field,
            proposed_value=normalized[field], ocr_engine='operator')
        decisions.append(confirm_field_proposal(user, organization, entered,
            corrected_value=normalized[field], reason=reason))
    A1Case.objects.filter(organization=organization, worker=worker,
        source_snapshot_json__schema_version='a1-input-1').update(is_stale=True)
    audit(user, organization, 'identity.address_confirmed', f'field_proposal:{proposal.pk}')
    return decisions
