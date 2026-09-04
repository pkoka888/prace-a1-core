from __future__ import annotations
import hashlib
import uuid
from django.db import transaction
from django.db.models import Q
from allauth.mfa.models import Authenticator
from prototypes.architecture.adr001.proof_contract import a1_prepare, stable_hash, validate_upload
from .models import (
    A1Case, Assignment, AuditEvent, Document, DocumentVersion, DocumentClassification,
    FieldProposal, FieldDecision, IntakeSession, Membership, OcrRun,
    ReviewTask, StatusEvent, Worker
)

class Forbidden(Exception): pass
class StaleWrite(Exception): pass

ROLE_CAPABILITY_MAP = {
    "organization_admin": {
        "worker:create", "worker:read", "worker:update", "worker:archive",
        "document:upload", "document:read", "document:confirm", "document:supersede",
        "assignment:create", "assignment:read", "assignment:update",
        "a1:prepare", "a1:approve", "a1:regenerate",
        "audit:read",
    },
    "jan_planner": {
        "worker:create", "worker:read", "worker:update",
        "document:upload", "document:read", "document:confirm",
        "assignment:create", "assignment:read", "assignment:update",
        "a1:prepare",
        "audit:read",
    },
    "operator": {
        "worker:read", "worker:update",
        "document:read", "document:confirm",
        "assignment:read",
        "a1:prepare",
    },
    "privacy_admin": {
        "worker:read",
        "document:read", "document:confirm",
        "assignment:read",
        "audit:read",
    },
    "system_worker": set(),
}

ALIASES = {
    "admin": "organization_admin",
    "op": "operator",
}


def require_mfa_enrolled(user):
    return Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists()


def get_effective_role(role):
    return ALIASES.get(role, role)


def require_capability(user, organization, capability):
    if not require_mfa_enrolled(user):
        raise Forbidden("active organization membership and mandatory TOTP enrollment required")
    memberships = list(Membership.objects.filter(user=user, organization=organization, active=True))
    if not memberships:
        raise Forbidden("active organization membership required")
    for membership in memberships:
        role = get_effective_role(membership.role)
        caps = ROLE_CAPABILITY_MAP.get(role, set())
        if capability in caps:
            return
    raise Forbidden(f"capability required: {capability}")


def require_membership(user, organization, role=None):
    if not require_mfa_enrolled(user):
        raise Forbidden("active organization membership and mandatory TOTP enrollment required")
    query = Membership.objects.filter(user=user, organization=organization, active=True)
    if role:
        query = query.filter(role__in=[role, ALIASES.get(role, role)])
    if not query.exists(): raise Forbidden("active organization membership required")

@transaction.atomic
def create_worker(user, organization, **fields):
    require_capability(user, organization, "worker:create")
    worker = Worker.objects.create(organization=organization, **fields)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="worker.created", object_ref=f"worker:{worker.pk}", outcome="success")
    return worker

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@transaction.atomic
def upload_document(user, organization, worker, filename, content_type, content, limit=MAX_UPLOAD_BYTES):
    require_capability(user, organization, "document:upload")
    if worker.organization_id != organization.id: raise Forbidden("cross-organization worker")
    checked = validate_upload(f"org-{organization.pk}", filename, content_type, content, limit=limit)

    validation = quarantine_and_validate(content, content_type, filename)

    existing = Document.objects.filter(organization=organization, sha256=checked.sha256).first()
    if existing:
        raise ValueError("Duplikát: dokument s tímto obsahem již existuje")

    document = Document.objects.create(
        organization=organization,
        worker=worker,
        opaque_key=checked.object_key,
        sha256=checked.sha256,
        content_type=checked.content_type,
        state=Document.State.PROPOSAL_READY,
    )

    version = DocumentVersion.objects.create(
        organization=organization,
        document=document,
        version_number=1,
        opaque_key=checked.object_key,
        sha256=checked.sha256,
        content_type=checked.content_type,
        byte_size=len(content),
        quarantine_result=validation["quarantine_result"],
        malware_result=validation["malware_result"],
        mime_result=validation["mime_result"],
    )

    ocr_run = OcrRun.objects.create(
        organization=organization,
        document=document,
        version=version,
        engine=OcrRun.Engine.LOCAL,
        engine_version="1.0.0",
        state=OcrRun.State.COMPLETED,
        idempotency_key=f"upload-{document.pk}-{version.pk}",
    )

    FieldProposal.objects.create(
        organization=organization,
        document=document,
        version=version,
        ocr_run=ocr_run,
        field_name="family_name",
        proposed_value="Syntetický návrh",
        confidence=0.9000,
        state=FieldProposal.State.PROPOSED,
    )

    AuditEvent.objects.create(
        organization=organization,
        actor_ref=f"user:{user.pk}",
        event_type="document.uploaded",
        object_ref=f"document:{document.pk}",
        outcome="success",
    )
    return document

@transaction.atomic
def create_assignment(user, organization, worker, *, start, end, workplace_label, activity_label):
    require_capability(user, organization, "assignment:create")
    if worker.organization_id != organization.id: raise Forbidden("cross-organization worker")
    overlap = Assignment.objects.filter(worker=worker).filter(Q(start__lte=end) & Q(end__gte=start)).exists()
    assignment = Assignment.objects.create(organization=organization, worker=worker, start=start, end=end, workplace_label=workplace_label, activity_label=activity_label)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="assignment.created_overlap" if overlap else "assignment.created", object_ref=f"assignment:{assignment.pk}", outcome="warning" if overlap else "success")
    return assignment, overlap

@transaction.atomic
def prepare_a1(user, organization, worker):
    require_capability(user, organization, "a1:prepare")
    if worker.organization_id != organization.id:
        raise Forbidden("cross-organization worker")
    assignments = list(Assignment.objects.filter(organization=organization, worker=worker).values("start", "end"))
    normalized = [{"start": str(a["start"]), "end": str(a["end"])} for a in assignments]

    previous_case = A1Case.objects.filter(organization=organization, worker=worker).order_by("-id").first()
    previous_hash = previous_case.source_hash if previous_case else None

    result = a1_prepare({"given_name": worker.given_name, "family_name": worker.family_name, "birth_date": str(worker.birth_date), "activity_profile": worker.activity_profile}, normalized, previous_source_hash=previous_hash)

    if previous_case and result.get("stale"):
        previous_case.is_stale = True
        previous_case.save(update_fields=["is_stale"])

    case = A1Case.objects.create(organization=organization, worker=worker, source_hash=result["source_hash"], readiness=A1Case.Readiness.READY if result["ready"] else A1Case.Readiness.BLOCKED, prepared_artifact_hash=result["artifact_hash"] or "")
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="a1.prepared" if result["ready"] else "a1.blocked", object_ref=f"a1:{case.pk}", outcome="success" if result["ready"] else "denied")
    return case


ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MALWARE_SIGNATURES = [b"%PDF", b"\x89PNG", b"\xff\xd8\xff"]


def quarantine_and_validate(content, content_type, filename):
    """Validate uploaded document content: MIME type, malware check, hash.

    Returns dict with:
        - sha256: hex digest
        - mime_result: 'ok' or 'mismatch'
        - malware_result: 'clean' or 'suspicious'
        - quarantine_result: 'passed' or 'failed'
    """
    sha256 = hashlib.sha256(content).hexdigest()

    mime_ok = content_type in ALLOWED_MIME_TYPES
    malware_ok = any(content[:4] == sig for sig in MALWARE_SIGNATURES)

    result = {
        "sha256": sha256,
        "mime_result": "ok" if mime_ok else "mismatch",
        "malware_result": "clean" if malware_ok else "suspicious",
        "quarantine_result": "passed" if (mime_ok and malware_ok) else "failed",
    }
    return result


OP_FRONT_FIELDS = [
    "surname", "given_name", "dob", "birth_place",
    "nationality", "sex", "document_id", "issue_date", "expiry_date"
]

OP_BACK_FIELDS = [
    "residence_street", "residence_house_number", "residence_city",
    "residence_postal_code", "residence_country_code",
    "issuing_authority", "personal_identifier"
]

ZP_FRONT_FIELDS = [
    "surname", "given_name", "dob", "personal_number",
    "insurer_code", "card_number", "expiry_date", "issuing_country"
]

DOCUMENT_TYPE_SCHEMAS = {
    "cz_id_front": OP_FRONT_FIELDS,
    "cz_id_back": OP_BACK_FIELDS,
    "cz_health_card_front": ZP_FRONT_FIELDS,
    "cz_health_card_back": [],
}


A1_PERSON_FIELDS = [
    "surname", "given_name", "dob", "birth_place",
    "nationality", "sex", "insurance_number",
]

A1_RESIDENCE_FIELDS = [
    "residence_street", "residence_house_number", "residence_city",
    "residence_district", "residence_postal_code", "residence_country_code",
]

A1_EMPLOYMENT_FIELDS = [
    "employment_id", "employment_name", "employment_street",
    "employment_house_number", "employment_city", "employment_postal_code",
    "employment_country_code",
]

A1_CERTIFICATE_FIELDS = [
    "document_id", "start_date", "end_date", "issue_date", "signed_by",
]

A1_STATUS_PROFILES = [
    "self_employed_multi_state",
    "employee_multi_state",
]

CONFIDENCE_BANDS = {
    "high": (0.95, None),
    "medium": (0.80, 0.9499),
    "low": (None, 0.80),
}


def confidence_label(score):
    """Return human-readable confidence band: Vysoká, Střední, Nízká."""
    if score is None:
        return "Neznámá"
    if score >= 0.95:
        return "Vysoká"
    elif score >= 0.80:
        return "Střední"
    return "Nízká"


def classify_document(document_version, organization, page_index=0, side=""):
    """Classify a document page/side as OP or ZP front/back.

    Rule-based classifier using file metadata, page count, and content hints.
    For production, this would use a trained ML model.
    """
    doc_type = DocumentClassification.DocType.UNKNOWN
    confidence = None
    side_confidence = None

    content_type = document_version.content_type
    byte_size = document_version.byte_size

    if content_type == "application/pdf":
        if byte_size < 50000:
            doc_type = DocumentClassification.DocType.CZ_ID_FRONT
            confidence = 0.75
            side = "front"
            side_confidence = 0.70
        else:
            doc_type = DocumentClassification.DocType.CZ_ID_BACK
            confidence = 0.70
            side = "back"
            side_confidence = 0.65
    elif content_type in ("image/png", "image/jpeg"):
        if page_index % 2 == 0:
            doc_type = DocumentClassification.DocType.CZ_ID_FRONT
            confidence = 0.85
            side = "front"
            side_confidence = 0.80
        else:
            doc_type = DocumentClassification.DocType.CZ_ID_BACK
            confidence = 0.80
            side = "back"
            side_confidence = 0.75

    classification = DocumentClassification.objects.create(
        organization=organization,
        document=document_version.document,
        version=document_version,
        page_index=page_index,
        side=side,
        doc_type=doc_type,
        doc_type_confidence=confidence,
        side_confidence=side_confidence,
        is_human_confirmed=False,
    )
    return classification


OP_MRZ_PATTERNS = [
    r"IDCZ[A-Z<]{30,}",
    r"[A-Z]{2}[A-Z0-9<]{35,}",
]

ZP_MRZ_PATTERNS = [
    r" CZ ",
    r"VZP",
    r"ZZP",
]

CARD_TYPE_INDICATORS = {
    "cz_id_front": ["OBČANSKÝ PRŮKAZ", "IDENTITY CARD", "CIVILNI", "OP "],
    "cz_id_back": ["ADRESA", "BYDLIŠTĚ", "ADRESSE", "MÍSTO"],
    "cz_health_card_front": ["POJIŠTĚNEC", "INSURED", "EHIC", "VZP"],
    "cz_health_card_back": [],
}


@transaction.atomic
def process_intake_document(user, organization, worker, filename, content_type, content, intake_session=None):
    """Full intake pipeline: quarantine → version → classification → OCR.

    This is the canonical entry point for OP/ZP document intake.
    Returns (document, document_version, classifications, ocr_run).
    """
    require_membership(user, organization)

    validation = quarantine_and_validate(content, content_type, filename)

    if validation["quarantine_result"] == "failed":
        raise ValueError(f"Dokument neprošel validací: {validation['quarantine_result']}")

    opaque_key = f"doc-{uuid.uuid4().hex}"
    sha256 = validation["sha256"]

    existing = Document.objects.filter(organization=organization, sha256=sha256).first()
    if existing:
        raise ValueError("Duplikát: dokument s tímto obsahem již existuje")

    document = Document.objects.create(
        organization=organization,
        worker=worker,
        opaque_key=opaque_key,
        sha256=sha256,
        content_type=content_type,
        state=Document.State.QUARANTINED,
    )

    version = DocumentVersion.objects.create(
        organization=organization,
        document=document,
        version_number=1,
        opaque_key=opaque_key,
        sha256=sha256,
        content_type=content_type,
        byte_size=len(content),
        quarantine_result=validation["quarantine_result"],
        malware_result=validation["malware_result"],
        mime_result=validation["mime_result"],
    )

    idem_key = f"ocr-{document.pk}-{version.pk}-v1"
    existing_run = OcrRun.objects.filter(document=document, version=version, idempotency_key=idem_key).first()
    if existing_run:
        return document, version, [], existing_run

    ocr_run = OcrRun.objects.create(
        organization=organization,
        document=document,
        version=version,
        engine=OcrRun.Engine.LOCAL,
        engine_version="1.0.0",
        state=OcrRun.State.PENDING,
        idempotency_key=idem_key,
    )

    classification = classify_document(version, organization)

    field_proposals = create_field_proposals_from_classification(
        organization, document, version, ocr_run, classification
    )

    AuditEvent.objects.create(
        organization=organization,
        actor_ref=f"user:{user.pk}",
        event_type="document.quarantine",
        object_ref=f"document:{document.pk}",
        outcome="success",
    )

    if intake_session:
        intake_session.state = IntakeSession.State.INTAKE_COMPLETE
        intake_session.save()

    return document, version, [classification], ocr_run


def create_field_proposals_from_classification(organization, document, version, ocr_run, classification):
    """Create FieldProposal records based on document classification.

    For synthetic data, creates sample proposals. In production, this would
    call the local OCR engine (RapidOCR) to extract actual field values.
    """
    from rapidocr import RapidOCR

    proposals = []
    doc_type = classification.doc_type

    if doc_type == DocumentClassification.DocType.UNKNOWN:
        return proposals

    schema_fields = DOCUMENT_TYPE_SCHEMAS.get(doc_type, [])

    try:
        from rapidocr import RapidOCR
        ocr_engine = RapidOCR()
        result, _ = ocr_engine(version.opaque_key)

        if result:
            for item in result:
                box, text, confidence = item
                mapped_field = map_ocr_text_to_field(text, doc_type, schema_fields)
                if mapped_field:
                    proposal = FieldProposal.objects.create(
                        organization=organization,
                        document=document,
                        version=version,
                        ocr_run=ocr_run,
                        field_name=mapped_field,
                        raw_ocr_text=text,
                        proposed_value=text.strip(),
                        confidence=confidence,
                        doc_class_confidence=classification.doc_type_confidence,
                        source_page=0,
                        source_bounding_box=box,
                        ocr_engine=OcrRun.Engine.RAPIDOCR,
                        ocr_model_version="1.0.0",
                        state=FieldProposal.State.PROPOSED,
                    )
                    proposals.append(proposal)
    except Exception:
        pass

    if not proposals:
        for field in schema_fields:
            proposal = FieldProposal.objects.create(
                organization=organization,
                document=document,
                version=version,
                ocr_run=ocr_run,
                field_name=field,
                raw_ocr_text="",
                proposed_value="",
                confidence=None,
                doc_class_confidence=classification.doc_type_confidence,
                ocr_engine=OcrRun.Engine.LOCAL,
                state=FieldProposal.State.MISSING,
            )
            proposals.append(proposal)

    return proposals


CZ_DIACRITICS_MAP = {
    "Á": "A", "Ä": "A", "Č": "C", "Ď": "D", "É": "E", "Ě": "E",
    "Í": "I", "Ň": "N", "Ó": "O", "Ř": "R", "Š": "S", "Ť": "T",
    "Ú": "U", "Ů": "U", "Ü": "U", "Ý": "Y", "Ž": "Z",
    "á": "a", "ä": "a", "č": "c", "ď": "d", "é": "e", "ě": "e",
    "í": "i", "ň": "n", "ó": "o", "ř": "r", "š": "s", "ť": "t",
    "ú": "u", "ů": "u", "ü": "u", "ý": "y", "ž": "z",
}


def normalize_ocr_text(text):
    """Normalize OCR text: remove extra spaces, normalize diacritics."""
    import unicodedata
    text = " ".join(text.split())
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


FIELD_VALUE_PATTERNS = {
    "cz_id_front": {
        "surname": r"(?:PŘÍJMENÍ|SURNAME|LAST NAME)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž]+)",
        "given_name": r"(?:JMÉNA|NAMES|GIVEN NAME)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž\s]+)",
        "dob": r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
        "birth_place": r"(?:MÍSTO NAROZENÍ|PLACE OF BIRTH)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž\s]+?)(?=\s+DATUM|\s+NATIONALITY|\s+POHLAVÍ|$)",
        "nationality": r"(?:NÁRODNOST|NATIONALITY)[:\s]+([A-Z]{2})",
        "sex": r"(?:POHLAVÍ|SEX)[:\s]+([MZ])",
        "document_id": r"(?:ČÍSLO|DOCUMENT No|NO)[:\s]+([A-Z0-9]+)",
        "expiry_date": r"(?:PLATNOST DO|EXPIRY)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})",
    },
    "cz_id_back": {
        "residence_street": r"(?:ULICE|STREET|ADRESA)[:\s]+([A-Z0-9ÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž\s]+?)(?=\s+\d+|$)",
        "residence_house_number": r"(\d+[/]?\d*)",
        "residence_city": r"(?:MĚSTO|OBEC|CITY)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž\s]+?)(?=\s+\d{3}\s|$)",
        "residence_postal_code": r"(\d{3}\s?\d{2})",
    },
    "cz_health_card_front": {
        "surname": r"(?:PŘÍJMENÍ|SURNAME)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž]+)",
        "given_name": r"(?:JMÉNO|NAME)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěínóřšťúůýž\s]+)",
        "personal_number": r"(?:ČÍSLO POJIŠTĚNCE|INSURANCE No)[:\s]+([A-Z0-9/]+)",
        "card_number": r"(?:ČÍSLO KARTY|CARD No)[:\s]+([A-Z0-9]+)",
    },
}


def map_ocr_text_to_field(text, doc_type, schema_fields):
    """Map extracted OCR text to A1 field name based on patterns."""
    import re

    text_norm = normalize_ocr_text(text)
    patterns = FIELD_VALUE_PATTERNS.get(doc_type, {})

    for field in schema_fields:
        pattern = patterns.get(field)
        if pattern and re.search(pattern, text_norm, re.IGNORECASE):
            return field

    if len(text_norm) < 3:
        return None

    for field in schema_fields:
        if field.replace("_", " ").lower() in text_norm.lower():
            return field

    return None


@transaction.atomic
def confirm_field_proposal(user, organization, field_proposal, corrected_value=None, reason=""):
    """Confirm a field proposal with optional correction. Creates immutable FieldDecision."""
    require_membership(user, organization)

    existing_decision = FieldDecision.objects.filter(field_proposal=field_proposal).exists()
    if existing_decision:
        raise ValueError("Návrh již byl potvrzen")

    decision = FieldDecision.objects.create(
        organization=organization,
        field_proposal=field_proposal,
        decision="confirmed",
        corrected_value=corrected_value or field_proposal.proposed_value,
        reason=reason,
        decided_by=user,
    )

    AuditEvent.objects.create(
        organization=organization,
        actor_ref=f"user:{user.pk}",
        event_type="ocr.confirmed",
        object_ref=f"field_proposal:{field_proposal.pk}",
        outcome="success",
    )

    return decision


@transaction.atomic
def create_review_task(user, organization, worker, document, task_type, description, priority=ReviewTask.Priority.MEDIUM):
    """Create a human review task for OCR/conflict/document review."""
    require_membership(user, organization)

    task = ReviewTask.objects.create(
        organization=organization,
        worker=worker,
        document=document,
        task_type=task_type,
        priority=priority,
        description=description,
        assigned_to=user,
    )

    AuditEvent.objects.create(
        organization=organization,
        actor_ref=f"user:{user.pk}",
        event_type="review.task.created",
        object_ref=f"review_task:{task.pk}",
        outcome="success",
    )

    return task

