from __future__ import annotations
from django.db import transaction
from django.db.models import Q
from prototypes.architecture.adr001.proof_contract import a1_prepare, stable_hash, validate_upload
from .models import A1Case, Assignment, AuditEvent, Document, Membership, OcrProposal, Worker

class Forbidden(Exception): pass
class StaleWrite(Exception): pass

def require_membership(user, organization, role=None):
    query = Membership.objects.filter(user=user, organization=organization, active=True, mfa_verified=True)
    if role: query = query.filter(role=role)
    if not query.exists(): raise Forbidden("active organization membership and mandatory TOTP required")

@transaction.atomic
def create_worker(user, organization, **fields):
    require_membership(user, organization)
    worker = Worker.objects.create(organization=organization, **fields)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="worker.created", object_ref=f"worker:{worker.pk}", outcome="success")
    return worker

# Form (DocumentUploadForm) allows up to this size; keep both in sync so a file
# that passes the form is not later rejected by the service with a confusing error.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@transaction.atomic
def upload_document(user, organization, worker, filename, content_type, content, limit=MAX_UPLOAD_BYTES):
    require_membership(user, organization)
    if worker.organization_id != organization.id: raise Forbidden("cross-organization worker")
    checked = validate_upload(f"org-{organization.pk}", filename, content_type, content, limit=limit)
    document = Document.objects.create(organization=organization, worker=worker, opaque_key=checked.object_key, sha256=checked.sha256, content_type=checked.content_type, state="proposal_ready")
    OcrProposal.objects.create(organization=organization, document=document, field_name="family_name", proposed_value="Syntetický návrh", confidence="0.9000")
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="document.uploaded", object_ref=f"document:{document.pk}", outcome="success")
    return document

@transaction.atomic
def create_assignment(user, organization, worker, *, start, end, workplace_label, activity_label):
    require_membership(user, organization)
    if worker.organization_id != organization.id: raise Forbidden("cross-organization worker")
    overlap = Assignment.objects.filter(worker=worker).filter(Q(start__lte=end) & Q(end__gte=start)).exists()
    assignment = Assignment.objects.create(organization=organization, worker=worker, start=start, end=end, workplace_label=workplace_label, activity_label=activity_label)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="assignment.created_overlap" if overlap else "assignment.created", object_ref=f"assignment:{assignment.pk}", outcome="warning" if overlap else "success")
    return assignment, overlap

@transaction.atomic
def prepare_a1(user, organization, worker):
    require_membership(user, organization)
    assignments = list(Assignment.objects.filter(worker=worker).values("start", "end"))
    normalized = [{"start": str(a["start"]), "end": str(a["end"])} for a in assignments]
    result = a1_prepare({"given_name": worker.given_name, "family_name": worker.family_name, "birth_date": str(worker.birth_date), "activity_profile": worker.activity_profile}, normalized)
    case = A1Case.objects.create(organization=organization, worker=worker, source_hash=result["source_hash"], readiness="ready" if result["ready"] else "blocked", prepared_artifact_hash=result["artifact_hash"] or "")
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="a1.prepared" if result["ready"] else "a1.blocked", object_ref=f"a1:{case.pk}", outcome="success" if result["ready"] else "denied")
    return case

