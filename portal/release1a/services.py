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
    ReviewTask, StatusEvent, Worker, Organization
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
    Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
    worker = Worker.objects.create(organization=organization, **fields)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="worker.created", object_ref=f"worker:{worker.pk}", outcome="success")
    return worker

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def upload_document(user, organization, worker, filename, content_type, content, limit=MAX_UPLOAD_BYTES):
    from .document_intake import intake
    if len(content) > limit:
        raise ValueError("INPUT_SIZE_INVALID")
    return intake(user, organization, worker, filename, content_type, content)[0]

@transaction.atomic
def create_assignment(user, organization, worker, *, start, end, workplace_label, activity_label):
    require_capability(user, organization, "assignment:create")
    Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
    if worker.organization_id != organization.id: raise Forbidden("cross-organization worker")
    overlap = Assignment.objects.filter(worker=worker).filter(Q(start__lte=end) & Q(end__gte=start)).exists()
    assignment = Assignment.objects.create(organization=organization, worker=worker, start=start, end=end, workplace_label=workplace_label, activity_label=activity_label)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="assignment.created_overlap" if overlap else "assignment.created", object_ref=f"assignment:{assignment.pk}", outcome="warning" if overlap else "success")
    return assignment, overlap

def current_a1_source(worker, organization):
    """One deterministic source contract for preparation, attachment and access."""
    if worker.organization_id != organization.id:
        raise Forbidden("cross-organization worker")
    assignments = list(Assignment.objects.filter(organization=organization, worker=worker).order_by("pk")
                       .values("id", "start", "end", "workplace_label", "activity_label", "state", "version", "a1_facts_json"))
    normalized = [{**{k: v for k, v in a.items() if k != "a1_facts_json" or v},
                   "start": str(a["start"]), "end": str(a["end"])} for a in assignments]

    profile = {
        "given_name": worker.given_name,
        "family_name": worker.family_name,
        "birth_date": str(worker.birth_date),
        "activity_profile": worker.activity_profile,
    }

    return profile, normalized, a1_prepare(profile, normalized)["source_hash"]


def current_artifact_dependencies(case):
    """Current mutable dependencies; accepted input/QA snapshots stay immutable."""
    from django.conf import settings
    from .j4_artifacts import _hash
    dependencies = dict(case.artifact_dependencies)
    dependencies.update(source_hash=current_a1_source(case.worker, case.organization)[2],
                        template_sha256=_hash((settings.BASE_DIR/'templates/a1_background.pdf').read_bytes()),
                        layout_sha256=_hash((settings.BASE_DIR/'config/a1_layout.json').read_bytes()),
                        renderer_sha256=_hash((settings.BASE_DIR/'scripts/a1_core.py').read_bytes()),
                        qa_code_sha256=_hash((settings.BASE_DIR/'scripts/a1_quality_gate.py').read_bytes()),
                        build_id=getattr(settings, 'PRACE_RELEASE_MANIFEST', {}).get('app_build_id', '')
                                 if isinstance(getattr(settings, 'PRACE_RELEASE_MANIFEST', None), dict) else '')
    return dependencies


@transaction.atomic
def prepare_a1(user, organization, worker):
    require_capability(user, organization, "a1:prepare")
    if worker.organization_id != organization.id:
        raise Forbidden("cross-organization worker")
    profile, normalized, _ = current_a1_source(worker, organization)

    previous_case = A1Case.objects.filter(organization=organization, worker=worker).order_by("-id").first()
    previous_hash = previous_case.source_hash if previous_case else None

    result = a1_prepare(profile, normalized, previous_source_hash=previous_hash)

    # Sync staleness on the latest existing case based on the comparison above.
    if previous_case is not None:
        new_stale = bool(result.get("stale"))
        if previous_case.is_stale != new_stale:
            previous_case.is_stale = new_stale
            previous_case.save(update_fields=["is_stale"])

    # Receipt is bound to the build identity when the supervised manifest is
    # configured; otherwise it falls back to the prototype artifact_hash.
    build_id = ""
    git_commit = ""
    try:
        from django.conf import settings
        manifest = getattr(settings, "PRACE_RELEASE_MANIFEST", None)
        if isinstance(manifest, dict):
            build_id = str(manifest.get("app_build_id") or "")
            git_commit = str(manifest.get("git_commit") or "")
    except Exception:
        pass

    # Application preparation does not contain canonical certificate evidence.
    # Never label a metadata digest as stored PDF evidence. A byte artifact may
    # only be attached after canonical rendering and protected artifact QA.
    receipt_hash = ""

    case = A1Case.objects.create(
        organization=organization,
        worker=worker,
        source_hash=result["source_hash"],
        source_snapshot_json={"profile": profile, "assignments": normalized},
        is_stale=False,
        readiness=A1Case.Readiness.READY if result["ready"] else A1Case.Readiness.BLOCKED,
        prepared_artifact_hash=receipt_hash,
        receipt_build_id=build_id,
        receipt_git_commit=git_commit,
    )
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="a1.prepared" if result["ready"] else "a1.blocked", object_ref=f"a1:{case.pk}", outcome="success" if result["ready"] else "denied")
    return case


@transaction.atomic
def confirm_field_proposal(user, organization, field_proposal, corrected_value=None, reason=""):
    from .models import DocumentRegionAssociation, WorkerIdentityRevision
    from src.document_core.interpretation import valid_value
    require_capability(user, organization, "document:confirm")
    Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
    proposal = FieldProposal.objects.select_for_update().get(pk=field_proposal.pk, organization=organization)
    if proposal.version.organization_id != organization.pk or proposal.document.organization_id != organization.pk:
        raise Forbidden("cross-organization proposal")
    if proposal.version.document_id != proposal.document_id or (proposal.ocr_run_id and
        (proposal.ocr_run.organization_id != organization.pk or proposal.ocr_run.document_id != proposal.document_id or proposal.ocr_run.version_id != proposal.version_id)):
        raise Forbidden("cross-organization proposal source")
    document = Document.objects.select_for_update().get(pk=proposal.document_id, organization=organization)
    if document.documentversion_set.order_by("-version_number").first().pk != proposal.version_id:
        raise ValueError("DOCUMENT_VERSION_SUPERSEDED")
    if FieldDecision.objects.filter(field_proposal=proposal).exists():
        raise ValueError("PROPOSAL_ALREADY_DECIDED")
    if proposal.document_region_id:
        association = DocumentRegionAssociation.objects.filter(organization=organization, ocr_run=proposal.ocr_run,
                                                               region_id=proposal.document_region_id).first()
        if not association:
            raise ValueError("REGION_ASSOCIATION_REQUIRED")
        worker = association.worker
    else:
        worker = proposal.document.worker
    if worker is None or worker.organization_id != organization.pk:
        raise Forbidden("worker association required")
    value = proposal.proposed_value if corrected_value is None else corrected_value
    if not value or not value.strip():
        raise ValueError("EMPTY_VALUE")
    value, findings = valid_value(proposal.field_name, value)
    if findings:
        raise ValueError("INVALID_FIELD_VALUE")
    if proposal.validation_findings and not reason.strip():
        raise ValueError("CONFLICT_REASON_REQUIRED")
    decision = FieldDecision.objects.create(organization=organization, field_proposal=proposal, decision="confirmed",
        corrected_value=value, reason=reason, decided_by=user)
    # Serialize authoritative revisions per worker; never overwrite Worker from OCR.
    Worker.objects.select_for_update().get(pk=worker.pk, organization=organization)
    previous = WorkerIdentityRevision.objects.filter(organization=organization, worker=worker).order_by("-revision_number").first()
    fields = dict(previous.confirmed_fields) if previous else {}
    fields[proposal.field_name] = value
    WorkerIdentityRevision.objects.create(organization=organization, worker=worker, source_document=proposal.document,
        source_version=proposal.version, revision_number=(previous.revision_number+1 if previous else 1),
        confirmed_fields=fields, confirmed_by=user)
    if not FieldProposal.objects.filter(document=proposal.document, version=proposal.version).exclude(fielddecision__decision="confirmed").exists():
        Document.objects.filter(pk=proposal.document_id).update(state=Document.State.CONFIRMED)
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}", event_type="ocr.confirmed",
                              object_ref=f"field_proposal:{proposal.pk}", outcome="success")
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



@transaction.atomic
def attach_a1_artifact(user, organization, case_id, *, expected_source_hash,
                       employee_id, rows, employees_path, profile_dir):
    """Attach canonical evidence only after authorized explicit record association.

    Does not issue a certificate, approve its visual review, or promote a final.
    The caller supplies the authoritative employee ID; filenames/names never match.
    """
    from pathlib import Path
    import tempfile
    from django.conf import settings
    from scripts.finalize_a1 import validate_review, row_to_form
    from scripts.a1_core import generate_a1_pdf
    from scripts.a1_quality_gate import validate_pdf
    from .j4_artifacts import publish_artifact, _root, _hash, _json

    require_capability(user, organization, "a1:approve")
    case = A1Case.objects.select_for_update().get(pk=case_id, organization=organization)
    _, _, live_hash = current_a1_source(case.worker, organization)
    if case.source_hash != expected_source_hash or case.source_hash != live_hash or case.is_stale:
        raise StaleWrite("A1_SOURCE_CHANGED")
    if case.readiness != A1Case.Readiness.READY:
        raise ValueError("A1_CASE_NOT_READY")
    if case.artifact_reference:
        raise StaleWrite("A1_ARTIFACT_ALREADY_ATTACHED")
    validated = validate_review(rows, Path(employees_path), Path(profile_dir))
    matches = [(row, profile) for row, profile in validated if row["employee_id"] == employee_id]
    if len(matches) != 1:
        raise ValueError("A1_ASSOCIATION_INVALID")
    row, profile = matches[0]
    background = settings.BASE_DIR / "templates/a1_background.pdf"
    layout = settings.BASE_DIR / "config/a1_layout.json"
    dependencies = {"source_hash": case.source_hash,
                    "review_sha256": _hash(_json(row)), "institution_sha256": _hash(_json(profile)),
                    "template_sha256": _hash(background.read_bytes()),
                    "layout_sha256": _hash(layout.read_bytes())}
    # Include current renderer/QA/build identities alongside accepted evidence.
    dependencies.update(current_artifact_dependencies(case))
    root = _root(Path(settings.DOCUMENT_STORAGE_ROOT) / "j4")
    with tempfile.TemporaryDirectory(prefix=".render-", dir=root) as temporary:
        output = Path(temporary) / "artifact.pdf"
        generate_a1_pdf(row_to_form(row, profile), background, layout, output)
        output.chmod(0o600)
        qa = validate_pdf(output, row, {r["employee_id"]: r for r, _ in validated}, background, 24)
        if not qa.passed or qa.checks.get("ghostscript") is not True:
            raise ValueError("A1_CANONICAL_QA_FAILED")
        dependencies["qa_sha256"] = _hash(_json({"pdf_sha256": qa.sha256, "checks": qa.checks}))
        reference = publish_artifact(root, output.read_bytes(),
                                     {"case": case.source_snapshot_json, "review": row, "institution": profile,
                                      "canonical_qa": {"pdf_sha256": qa.sha256, "checks": qa.checks}},
                                     dependencies)
    case.artifact_reference = reference
    case.artifact_dependencies = dependencies
    case.prepared_artifact_hash = reference["pdf_sha256"]
    case.save(update_fields=["artifact_reference", "artifact_dependencies", "prepared_artifact_hash"])
    AuditEvent.objects.create(organization=organization, actor_ref=f"user:{user.pk}",
                              event_type="a1.artifact_attached", object_ref=f"a1:{case.pk}", outcome="success")
    return case
