"""Synthetic identity proposals and decisions; machine drafts never confirm facts.

Identity writes serialize per organization, then source runs/documents and workers.
Evaluation hashes are checked again under these locks before any decision is made.
"""
from django.conf import settings
from django.db import transaction
from src.document_core.interpretation import normalized, valid_value
from src.document_core.serialization import result_hash
from .document_intake import (authorize, audit, evaluate_identity_proposals,
                              read_result, associate_region)
from .models import (Organization, Worker, Document, OcrRun, IdentityEvaluation,
                     WorkerIdentityClaim, IdentityResolution, WorkerIdentityRevision,
                     DocumentRegionAssociation)
from .services import Forbidden, StaleWrite, create_worker


def _authorize(user, organization, capability):
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise Forbidden("REAL_DATA_ACTIVATION_REQUIRED")
    if not user.is_active:
        raise Forbidden("ACTIVE_OPERATOR_REQUIRED")
    authorize(user, organization, capability)


def _lock_organization(organization):
    Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)


def _lock_sources(organization, run_ids):
    runs = list(OcrRun.objects.select_for_update().filter(
        organization=organization, pk__in=run_ids).order_by("pk"))
    if len(runs) != len(set(run_ids)):
        raise ValueError("IDENTITY_SOURCE_UNAVAILABLE")
    docs = list(Document.objects.select_for_update().filter(
        organization=organization, pk__in={r.document_id for r in runs}).order_by("pk"))
    if {d.pk for d in docs} != {r.document_id for r in runs}:
        raise Forbidden("CROSS_ORGANIZATION_SOURCE")


@transaction.atomic
def persist_identity_evaluation(user, organization, run_ids):
    _authorize(user, organization, "document:upload")
    _lock_organization(organization)
    _lock_sources(organization, run_ids)
    evidence = evaluate_identity_proposals(user, organization, run_ids)
    record, created = IdentityEvaluation.objects.get_or_create(
        organization=organization, evaluation_sha256=evidence["evaluation_sha256"],
        defaults={"evidence": evidence})
    if record.evidence != evidence:
        raise ValueError("IDENTITY_EVALUATION_CORRUPT")
    if created:
        audit(user, organization, "identity.evaluated", f"identity_evaluation:{record.pk}")
    return record


def _current_evaluation(user, organization, evaluation_id):
    record = IdentityEvaluation.objects.get(pk=evaluation_id, organization=organization)
    evidence = record.evidence
    if (evidence.get("evaluation_sha256") != record.evaluation_sha256 or
            result_hash({k: v for k, v in evidence.items() if k != "evaluation_sha256"}) != record.evaluation_sha256):
        raise ValueError("IDENTITY_EVALUATION_CORRUPT")
    run_ids = [source["run_ref"] for source in evidence["sources"]]
    _lock_sources(organization, run_ids)
    current = evaluate_identity_proposals(user, organization, run_ids)
    if current["evaluation_sha256"] != record.evaluation_sha256:
        raise StaleWrite("IDENTITY_EVALUATION_STALE")
    return record


def _region(record, run_id, region_id):
    for region in record.evidence["regions"]:
        if region["run_ref"] == run_id and region["region_ref"] == region_id:
            return region
    raise ValueError("IDENTITY_REGION_UNAVAILABLE")


def _latest_revision(organization, worker):
    return WorkerIdentityRevision.objects.filter(organization=organization, worker=worker).order_by("-revision_number", "-pk").first()


@transaction.atomic
def resolve_identity_evaluation(user, organization, evaluation_id, run_id, region_id,
                                worker_id, *, expected_worker_version, expected_revision_id, reason=""):
    """Explicit human association only; field confirmation remains a separate action."""
    _authorize(user, organization, "document:confirm")
    _lock_organization(organization)
    record = _current_evaluation(user, organization, evaluation_id)
    region = _region(record, run_id, region_id)
    worker = Worker.objects.select_for_update().get(pk=worker_id, organization=organization)
    revision = _latest_revision(organization, worker)
    if (type(expected_worker_version) is not int or worker.version != expected_worker_version or
            (expected_revision_id is not None and type(expected_revision_id) is not int) or
            (revision.pk if revision else None) != expected_revision_id):
        raise StaleWrite("WORKER_REVISION_STALE")
    if worker.state == Worker.State.ARCHIVED:
        raise ValueError("WORKER_ARCHIVED")
    existing = DocumentRegionAssociation.objects.filter(ocr_run_id=run_id, region_id=region_id).first()
    if existing:
        resolution = IdentityResolution.objects.filter(organization=organization, evaluation=record,
                                                       association=existing).first()
        if resolution and existing.worker_id == worker.pk:
            return resolution
        raise ValueError("ASSOCIATION_ALREADY_DECIDED")
    if not (region["status"] == "proposed" and region["worker_id"] == str(worker.pk)) and not reason.strip():
        raise ValueError("IDENTITY_OVERRIDE_REASON_REQUIRED")
    association = associate_region(user, organization, run_id, region_id, worker)
    resolution = IdentityResolution.objects.create(organization=organization, evaluation=record,
        association=association, worker_version=worker.version, worker_revision=revision, reason=reason.strip())
    audit(user, organization, "identity.resolved", f"identity_resolution:{resolution.pk}")
    return resolution


def _fields(document):
    fields = {}
    for field in document["fields"]:
        if field["findings"]:
            continue
        value, findings = valid_value(field["field"], field["value"])
        if not findings:
            fields.setdefault(field["field"], set()).add(value)
    return {key: next(iter(values)) for key, values in fields.items() if len(values) == 1}


def _identifier_key(organization, document):
    classification = document["classification"]
    kind, issuer = classification["type"], classification["country"]
    field = "card_number" if kind == "zp" else "document_number"
    value = _fields(document).get(field)
    if kind not in ("op", "zp", "passport") or not issuer or not value:
        return None
    return result_hash({"organization": organization.pk, "type": kind, "issuer": issuer,
                        "value": normalized(value)})


@transaction.atomic
def prepare_identity_draft(user, organization, evaluation_id, run_id, region_id, *, activity_profile, activity_profiles=None):
    """Reuse a claim or create a draft from complete, consistent identity proposals.

    activity_profile is an explicit batch business fact, never inferred from a scan.
    A claim is a deduplication record; known_workers deliberately excludes it.
    """
    _authorize(user, organization, "worker:create")
    if activity_profile not in {"employee", "self_employed"}:
        raise ValueError("ACTIVITY_PROFILE_REQUIRED")
    _lock_organization(organization)
    record = _current_evaluation(user, organization, evaluation_id)
    region = _region(record, run_id, region_id)
    # Lock current worker rows after documents, matching confirmation lock order.
    workers = list(Worker.objects.select_for_update().filter(organization=organization).order_by("pk"))
    if region["status"] == "proposed":
        worker = next((w for w in workers if str(w.pk) == region["worker_id"]), None)
        if worker is None or worker.state == Worker.State.ARCHIVED:
            return {"status": "requires_review", "reason": "WORKER_UNAVAILABLE"}
        return {"status": "proposed", "worker_ref": worker.pk, "accepted": False}
    if region["status"] != "unassigned" or region.get("findings"):
        return {"status": "requires_review", "reason": "IDENTITY_CONFLICT"}
    documents = []
    target = None
    for source in record.evidence["sources"]:
        payload = read_result(user, organization, source["run_ref"])
        for doc in payload["result"]["documents"]:
            doc["ocr_run_id"] = source["run_ref"]
            documents.append(doc)
            if source["run_ref"] == run_id and doc["document_id"] == region_id:
                target = doc
    if target is None:
        raise ValueError("IDENTITY_REGION_UNAVAILABLE")
    facts = _fields(target)
    required = ("given_name", "family_name", "birth_date")
    key = _identifier_key(organization, target)
    if not key or any(not facts.get(f) for f in required) or any(len(facts[f]) > 80 for f in required[:2]):
        return {"status": "requires_review", "reason": "IDENTITY_INCOMPLETE"}
    for doc in documents:
        if _identifier_key(organization, doc) == key:
            if (activity_profiles or {}).get(doc["ocr_run_id"], activity_profile) != activity_profile:
                return {"status": "requires_review", "reason": "ACTIVITY_PROFILE_CONFLICT"}
            other = _fields(doc)
            if (any(f["findings"] for f in doc["fields"] if f["field"] in (*required, "document_number", "card_number"))
                    or any(other.get(f) and normalized(other[f]) != normalized(facts[f]) for f in required)):
                return {"status": "requires_review", "reason": "IDENTITY_CONFLICT"}
    claim = WorkerIdentityClaim.objects.filter(organization=organization, identifier_sha256=key).first()
    if claim:
        if claim.evaluation.organization_id != organization.pk or claim.ocr_run.organization_id != organization.pk:
            raise Forbidden("CROSS_ORGANIZATION_CLAIM")
        worker = next((w for w in workers if w.pk == claim.worker_id), None)
        if (worker is None or worker.state == Worker.State.ARCHIVED or worker.activity_profile != activity_profile or
                any(normalized(str(getattr(worker, f))) != normalized(facts[f]) for f in required)):
            return {"status": "requires_review", "reason": "DRAFT_IDENTITY_CONFLICT"}
        revision = _latest_revision(organization, worker)
        if revision and any(revision.confirmed_fields.get(f) and
                normalized(str(revision.confirmed_fields[f])) != normalized(facts[f]) for f in required):
            return {"status": "requires_review", "reason": "CONFIRMED_IDENTITY_CONFLICT"}
        return {"status": "draft" if worker.state == Worker.State.DRAFT else "proposed",
                "worker_ref": worker.pk, "claim_ref": claim.pk, "accepted": False}
    # Similar identity is a review candidate, never permission to auto-merge/create a duplicate.
    if any(str(w.birth_date) == facts["birth_date"] and
           (normalized(w.family_name) == normalized(facts["family_name"]) or
            normalized(w.given_name) == normalized(facts["given_name"])) for w in workers):
        return {"status": "requires_review", "reason": "POSSIBLE_EXISTING_WORKER"}
    worker = create_worker(user, organization, **{f: facts[f] for f in required},
                           activity_profile=activity_profile, state=Worker.State.DRAFT)
    claim = WorkerIdentityClaim.objects.create(organization=organization, identifier_sha256=key,
        worker=worker, evaluation=record, ocr_run_id=run_id, region_id=region_id)
    audit(user, organization, "identity.draft_created", f"identity_claim:{claim.pk}")
    return {"status": "draft", "worker_ref": worker.pk, "claim_ref": claim.pk, "accepted": False}
