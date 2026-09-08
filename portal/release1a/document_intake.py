"""Protected adapter for the shared processor. Synthetic activation only.

No originals, OCR text or exception values enter audit events. Original keys and
run derivative keys are independent. OCR never confirms identity or associations.
"""
from datetime import timedelta
import json
from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction, IntegrityError
from django.db.models import Q, F
from django.utils import timezone
from src.document_core.images import decode_pages
from src.document_core.pipeline import DocumentProcessor
from src.document_core.serialization import canonical_json, content_hash
from src.document_core.cli import error_tag
from .document_storage import document_storage
from .models import (Document, DocumentVersion, DocumentClassification, OcrRun,
                     FieldProposal, FieldDecision, DocumentRegionAssociation, AuditEvent, WorkerIdentityRevision)


def authorize(user, organization, capability):
    from .services import require_capability
    try:
        require_capability(user, organization, capability)
    except Exception:
        audit(user, organization, "document.access_denied", f"organization:{organization.pk}", "denied")
        raise


def audit(user, org, event, obj, outcome="success"):
    AuditEvent.objects.create(organization=org, actor_ref=f"user:{user.pk}",
                             event_type=event, object_ref=obj, outcome=outcome)


def validate_content(content, content_type, filename):
    from src.document_core.ocr_result import ContractError
    types = {b"%PDF-": ("application/pdf", {".pdf"}), b"\x89PNG": ("image/png", {".png"}),
             b"\xff\xd8\xff": ("image/jpeg", {".jpg", ".jpeg"}), b"II*\x00": ("image/tiff", {".tif", ".tiff"}),
             b"MM\x00*": ("image/tiff", {".tif", ".tiff"})}
    detected = next((v for k, v in types.items() if content.startswith(k)), None)
    if not detected or detected[0] != content_type or Path(filename).suffix.lower() not in detected[1]:
        raise ContractError("UPLOAD_TYPE_MISMATCH")
    decode_pages(content)  # Actual structural parse, page/pixel/byte limits.
    scanner = getattr(settings, "DOCUMENT_SCANNER", None)
    if scanner is not None:
        try:
            clean = scanner(content) is True
        except Exception:
            clean = False
        if not clean:
            raise ContractError("SCANNER_REJECTED")
        return "clean"
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise ContractError("SCANNER_UNAVAILABLE")
    return "synthetic_not_scanned"


def intake(user, organization, worker, filename, content_type, content, intake_session=None, *, processor=None):
    from .services import Forbidden
    authorize(user, organization, "document:upload")
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise Forbidden("REAL_DATA_ACTIVATION_REQUIRED")
    if worker is not None and worker.organization_id != organization.pk:
        raise Forbidden("cross-organization worker")
    if intake_session and (intake_session.organization_id != organization.pk or intake_session.worker_id != (worker.pk if worker else None)):
        raise Forbidden("cross-organization intake")
    scanner_result = validate_content(content, content_type, filename)
    digest = content_hash(content)
    storage = document_storage()
    # Duplicate requests return the persisted run/IDs, not newly generated IDs.
    existing = Document.objects.filter(organization=organization, sha256=digest).first()
    if existing:
        if existing.worker_id != (worker.pk if worker else None):
            raise ValueError("DUPLICATE_WITH_DIFFERENT_CONTEXT")
        version = existing.documentversion_set.order_by("-version_number").first()
        run = OcrRun.objects.filter(organization=organization, version=version).order_by("-pk").first()
        if not run:
            raise ValueError("LEGACY_DOCUMENT_REQUIRES_RECONCILIATION")
        if intake_session:
            intake_session.ocr_runs.add(run)
        return existing, version, list(existing.documentclassification_set.all()), run
    key = storage.save(f"documents/{uuid4().hex}.source", ContentFile(content))
    try:
        with transaction.atomic():
            document = Document.objects.create(organization=organization, worker=worker,
                opaque_key=key, sha256=digest, content_type=content_type,
                purpose="worker_intake", retention_review_at=timezone.now()+timedelta(days=90),
                state=Document.State.QUARANTINED)
            version = DocumentVersion.objects.create(organization=organization, document=document,
                version_number=1, opaque_key=key, sha256=digest, content_type=content_type, byte_size=len(content),
                quarantine_result="passed", malware_result=scanner_result, mime_result="ok")
            run = OcrRun.objects.create(organization=organization, document=document, version=version,
                engine=OcrRun.Engine.RAPIDOCR, idempotency_key=f"document:{document.pk}:version:{version.pk}:core:1")
            if intake_session:
                intake_session.ocr_runs.add(run)
            audit(user, organization, "document.uploaded", f"document:{document.pk}")
    except Exception:
        storage.delete(key)
        raise
    run = execute_run(user, organization, run.pk, processor=processor)
    if intake_session:
        intake_session.state = "intake_complete"
        intake_session.save(update_fields=["state"])
    document.refresh_from_db()
    return document, version, list(document.documentclassification_set.all()), run


def read_result(user, organization, run_id):
    authorize(user, organization, "document:read")
    run = OcrRun.objects.get(pk=run_id, organization=organization)
    # Verify all linked tenants before touching storage, including legacy rows.
    if run.document.organization_id != organization.pk or run.version.organization_id != organization.pk or run.version.document_id != run.document_id:
        from .services import Forbidden
        raise Forbidden("cross-organization run")
    if not run.output_key:
        return None
    with document_storage().open(run.output_key, "rb") as stream:
        content = stream.read()
    if content_hash(content) != run.output_sha256:
        raise ValueError("DERIVATIVE_HASH_MISMATCH")
    audit(user, organization, "ocr.result_read", f"ocr:{run.pk}")
    return json.loads(content)


def supersede(user, organization, document_id, filename, content_type, content, *, processor=None):
    """Persist a replacement version, preserving original bytes and run receipts."""
    from .services import Forbidden
    authorize(user, organization, "document:supersede")
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise Forbidden("REAL_DATA_ACTIVATION_REQUIRED")
    # Resolve scope before parsing or writing content.
    Document.objects.get(pk=document_id, organization=organization)
    scanner = validate_content(content, content_type, filename)
    digest = content_hash(content)
    storage, key = document_storage(), None
    try:
        with transaction.atomic():
            document = Document.objects.select_for_update().get(pk=document_id, organization=organization)
            latest = document.documentversion_set.order_by("-version_number").first()
            if latest and latest.organization_id != organization.pk:
                raise Forbidden("cross-organization version")
            if latest and latest.sha256 == digest:
                run = OcrRun.objects.filter(organization=organization, document=document, version=latest).order_by("-pk").first()
                if run is None:
                    raise ValueError("LEGACY_DOCUMENT_REQUIRES_RECONCILIATION")
                version = latest
            else:
                if Document.objects.filter(organization=organization, sha256=digest).exclude(pk=document.pk).exists():
                    raise ValueError("DUPLICATE_WITH_DIFFERENT_CONTEXT")
                key = storage.save(f"documents/{uuid4().hex}.source", ContentFile(content))
                version = DocumentVersion.objects.create(
                    organization=organization, document=document,
                    version_number=latest.version_number + 1 if latest else 1,
                    opaque_key=key, sha256=digest, content_type=content_type, byte_size=len(content),
                    quarantine_result="passed", malware_result=scanner, mime_result="ok")
                run = OcrRun.objects.create(organization=organization, document=document, version=version,
                    engine=OcrRun.Engine.RAPIDOCR,
                    idempotency_key=f"document:{document.pk}:version:{version.pk}:core:1")
                document.opaque_key, document.sha256, document.content_type = key, digest, content_type
                document.state = Document.State.QUARANTINED
                document.save(update_fields=["opaque_key", "sha256", "content_type", "state"])
                audit(user, organization, "document.superseded", f"document:{document.pk}:version:{version.pk}")
    except Exception:
        if key is not None:
            storage.delete(key)
        raise
    run = execute_run(user, organization, run.pk, processor=processor)
    return version, run


def execute_run(user, organization, run_id, *, processor=None):
    authorize(user, organization, "document:upload")
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        from .services import Forbidden
        raise Forbidden("REAL_DATA_ACTIVATION_REQUIRED")
    run = OcrRun.objects.select_related("version", "document").get(pk=run_id, organization=organization)
    if run.version.organization_id != organization.pk or run.document.organization_id != organization.pk or run.version.document_id != run.document_id:
        from .services import Forbidden
        raise Forbidden("cross-organization run")
    if run.state == OcrRun.State.COMPLETED:
        return run
    now, token = timezone.now(), uuid4().hex
    eligible = Q(state__in=[OcrRun.State.PENDING, OcrRun.State.FAILED]) | Q(state=OcrRun.State.RUNNING, lease_expires_at__lte=now)
    claimed = OcrRun.objects.filter(pk=run.pk, organization=organization, retry_count__lt=3).filter(eligible).update(
        state=OcrRun.State.RUNNING, attempt_token=token, lease_expires_at=now+timedelta(minutes=15),
        started_at=now, completed_at=None, failure_reason="", retry_count=F("retry_count")+1)
    if not claimed:
        run.refresh_from_db()
        return run
    storage, keys = document_storage(), []
    def store_crop(digest, content):
        key = f"generated/{token}/{digest}.png"
        if not storage.exists(key):
            keys.append(storage.save(key, ContentFile(content)))
    try:
        with storage.open(run.version.opaque_key, "rb") as stream:
            content = stream.read()
        if content_hash(content) != run.version.sha256:
            raise ValueError("SOURCE_HASH_MISMATCH")
        result = (processor or DocumentProcessor()).process(content, workers=known_workers(organization), artifact_sink=store_crop)
        payload = {"status": "completed", "result": result, "artifact_keys": keys,
                   "source_hash": run.version.sha256, "error_tag": None}
    except Exception as exc:
        payload = {"status": "failed", "error_tag": error_tag(exc), "result": None,
                   "source_hash": run.version.sha256, "artifact_keys": keys}
    encoded = canonical_json(payload).encode()
    key = ""
    try:
        key = storage.save(f"generated/{token}.json", ContentFile(encoded))
        keys.append(key)
    except OSError:
        payload = {"status": "failed", "error_tag": "OUTPUT_STORAGE_FAILED", "result": None}
    with transaction.atomic():
        current = OcrRun.objects.select_for_update().get(pk=run.pk, organization=organization)
        if current.attempt_token != token or current.state != OcrRun.State.RUNNING:
            for orphan in keys:
                storage.delete(orphan)
            return current
        current.state = OcrRun.State.COMPLETED if payload["status"] == "completed" else OcrRun.State.FAILED
        current.output_key, current.output_sha256 = key, content_hash(encoded) if key else ""
        current.failure_reason = payload.get("error_tag") or ""
        current.completed_at, current.lease_expires_at = timezone.now(), None
        if payload["result"]:
            persist_proposals(organization, current, payload["result"])
            docs = payload["result"]["documents"]
            current.engine_version = docs[0]["ocr"]["engine_version"] if docs else ""
            document = Document.objects.select_for_update().get(pk=current.document_id, organization=organization)
            latest = document.documentversion_set.order_by("-version_number").first()
            if latest and latest.pk == current.version_id:
                document.state = Document.State.PROPOSAL_READY
                document.save(update_fields=["state"])
        current.save()
        audit(user, organization, "ocr.completed" if current.state == "completed" else "ocr.failed", f"ocr:{current.pk}:attempt:{token}",
              "success" if current.state == "completed" else "failed")
    return current


def persist_proposals(organization, run, result):
    types = {("op", "front"): "cz_id_front", ("op", "back"): "cz_id_back",
             ("passport", None): "cz_passport", ("zp", None): "cz_health_card_front"}
    for document in result["documents"]:
        c = document["classification"]
        DocumentClassification.objects.create(organization=organization, document=run.document, version=run.version,
            page_index=document["source_page"], side=c["side"] or "", doc_type=types.get((c["type"], c["side"]), "unknown"),
            doc_type_confidence=c["confidence"], side_confidence=c["confidence"] if c["side"] else None)
        if document["duplicate_of"]:
            continue
        regions = {r["region_id"]: r for r in document["ocr"]["regions"]}
        for f in document["fields"]:
            field_findings = f["findings"] + document["findings"] + document["matching_findings"]
            if len(f["value"]) > 240:
                field_findings.append("value_exceeds_form_limit")
            evidence = [regions[e] for e in f["evidence"] if e in regions]
            FieldProposal.objects.create(organization=organization, document=run.document, version=run.version, ocr_run=run,
                document_region_id=document["document_id"], field_name=f["field"], raw_ocr_text=f["raw_text"],
                proposed_value=f["value"][:240], confidence=f["confidence"], doc_class_confidence=c["confidence"],
                source_page=document["source_page"], source_bounding_box=evidence[0]["polygon"] if evidence else None,
                ocr_engine=document["ocr"]["engine"], ocr_model_version=document["ocr"]["engine_version"],
                validation_findings=field_findings,
                state=FieldProposal.State.CONFLICT if field_findings else FieldProposal.State.PROPOSED)


def associate_region(user, organization, run_id, region_id, worker):
    authorize(user, organization, "document:confirm")
    if worker.organization_id != organization.pk:
        from .services import Forbidden
        raise Forbidden("cross-organization worker")
    payload = read_result(user, organization, run_id)
    if not payload or payload["status"] != "completed" or region_id not in {d["document_id"] for d in payload["result"]["documents"]}:
        raise ValueError("REGION_NOT_FOUND")
    classification = next(d["classification"] for d in payload["result"]["documents"] if d["document_id"] == region_id)
    with transaction.atomic():
        run = OcrRun.objects.select_for_update().get(pk=run_id, organization=organization)
        document = Document.objects.select_for_update().get(pk=run.document_id, organization=organization)
        if document.documentversion_set.order_by("-version_number").first().pk != run.version_id:
            raise ValueError("DOCUMENT_VERSION_SUPERSEDED")
        existing = DocumentRegionAssociation.objects.filter(ocr_run_id=run_id, region_id=region_id).first()
        if existing:
            if existing.organization_id != organization.pk or existing.worker_id != worker.pk:
                raise ValueError("ASSOCIATION_ALREADY_DECIDED")
            return existing
        association = DocumentRegionAssociation.objects.create(organization=organization, ocr_run_id=run_id,
                                                               region_id=region_id, worker=worker, decided_by=user,
                                                               document_type=classification["type"] or "", issuer=classification["country"] or "")
        audit(user, organization, "document.region_associated", f"association:{association.pk}")
    return association


def download_original(user, organization, document):
    authorize(user, organization, "document:read")
    if document.organization_id != organization.pk:
        from .services import Forbidden
        raise Forbidden("cross-organization document")
    version = document.documentversion_set.order_by("-version_number").first()
    if not version or version.organization_id != organization.pk:
        raise ValueError("SOURCE_NOT_AVAILABLE")
    with document_storage().open(version.opaque_key, "rb") as stream:
        data = stream.read()
    if content_hash(data) != version.sha256:
        raise ValueError("SOURCE_HASH_MISMATCH")
    audit(user, organization, "document.downloaded", f"document:{document.pk}")
    return data, version.content_type


def known_workers(organization):
    """Only identifiers with an explicit field decision AND region association."""
    workers = {}
    associations = DocumentRegionAssociation.objects.filter(organization=organization, worker__organization=organization, ocr_run__organization=organization)
    for association in associations:
        field = "card_number" if association.document_type == "zp" else "document_number"
        kind = "ehic_card_number" if association.document_type == "zp" else f"{association.document_type}_document_number"
        if association.document_type not in ("op", "zp", "passport"):
            continue
        decisions = FieldDecision.objects.filter(organization=organization, decision="confirmed", field_proposal__organization=organization,
            field_proposal__ocr_run=association.ocr_run, field_proposal__document_region_id=association.region_id,
            field_proposal__field_name=field)
        for decision in decisions:
            workers.setdefault(association.worker_id, {"worker_id": str(association.worker_id), "identifiers": []})["identifiers"].append(
                {"type": kind, "issuer": association.issuer, "value": decision.corrected_value})
    for worker_id, worker in workers.items():
        revision = WorkerIdentityRevision.objects.filter(organization=organization, worker_id=worker_id).order_by("-revision_number").first()
        worker["identity_fields"] = revision.confirmed_fields if revision else {}
    return list(workers.values())


def read_session(user, organization, session):
    """Derived matching view; immutable per-run evidence remains hash-bound."""
    authorize(user, organization, "document:read")
    if session.organization_id != organization.pk:
        from .services import Forbidden
        raise Forbidden("cross-organization intake")
    documents = []
    for run in session.ocr_runs.filter(organization=organization).order_by("pk"):
        if run.document.documentversion_set.order_by("-version_number").first().pk != run.version_id:
            continue
        payload = read_result(user, organization, run.pk)
        if payload and payload.get("result"):
            for doc in payload["result"]["documents"]:
                doc["ocr_run_id"] = run.pk
                doc["source_document_pk"] = run.document_id
                documents.append(doc)
    return DocumentProcessor().combine(documents, known_workers(organization))
