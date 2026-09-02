"""Views for Release 1A M2 vertical slice — J1–J4 journeys."""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from hashlib import sha256

from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from allauth.mfa.models import Authenticator

from .forms import (
    WorkerForm,
    DocumentUploadForm,
    OcrConfirmationForm,
    AssignmentForm,
    A1PrepareForm,
    A1ApprovalForm,
)
from .models import (
    Worker,
    Document,
    OcrProposal,
    Assignment,
    A1Case,
    AuditEvent,
    Membership,
    Release1aReview,
    Release1aAcceptance,
)
from .services import (
    create_worker,
    upload_document,
    create_assignment,
    prepare_a1,
)


# =============================================================================
# Helpers
# =============================================================================

REVIEW_SECTIONS = [
    (Release1aReview.Section.WORKER, "Pracovník", "workers/"),
    (Release1aReview.Section.DOCUMENT_OCR, "Dokument a kontrola OCR", "workers/"),
    (Release1aReview.Section.ASSIGNMENT, "Přiřazení", "workers/"),
    (Release1aReview.Section.A1, "Příprava a kontrola A1", "workers/"),
]

REVIEW_SCOPE_TEXT = (
    "Schvaluji uživatelský postup a funkčnost syntetického prototypu Release 1A "
    "pro práci s pracovníkem, dokumentem/OCR, přiřazením a přípravou A1, "
    "včetně uvedených výjimek. Toto schválení nepovoluje použití reálných "
    "osobních údajů, produkční nasazení ani zveřejnění portálu."
)
REVIEW_EXCLUSIONS_TEXT = (
    "Toto schválení nepovoluje: nasazení reálných osobních údajů, produkční "
    "infrastrukturu, veřejné nasazení portálu nebo aktivaci A1 v produkčním režimu."
)

READINESS_FILE = os.environ.get(
    "REVIEW_READINESS_PATH",
    "/var/www/prace-v-nemecku.tvoje.info/runtime/portal/synthetic-review/readiness.json",
)

BUILD_ID_FILE = os.environ.get(
    "REVIEW_BUILD_ID_PATH",
    "/var/www/prace-v-nemecku.tvoje.info/runtime/portal/synthetic-review/build_id.txt",
)


def _get_build_id():
    if os.path.exists(BUILD_ID_FILE):
        return open(BUILD_ID_FILE).read().strip()
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = (
            "dirty" if subprocess.check_output(
                ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            else "clean"
        )
        import sys
        build_id = sha256(
            f"{commit}:{dirty}:{sys.modules['portal.settings'].SETTINGS_MODULE}:{sys.version}".encode()
        ).hexdigest()[:16]
    except Exception:
        build_id = "unknown"
    os.makedirs(os.path.dirname(BUILD_ID_FILE), exist_ok=True)
    with open(BUILD_ID_FILE, "w") as fh:
        fh.write(build_id)
    return build_id


def _require_mfa(user):
    return Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists()


def get_user_organization(request):
    """Get the user's active organization. Requires MFA enrollment via allauth."""
    if not request.user.is_authenticated:
        return None
    if not _require_mfa(request.user):
        return None
    membership = Membership.objects.filter(
        user=request.user, active=True
    ).select_related("organization").first()
    if not membership:
        return None
    return membership.organization


def require_org_membership(view_func):
    """Decorator: requires authenticated user with active org membership AND enrolled MFA."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(_("Přihlášení je vyžadováno."))
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not _require_mfa(request.user):
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(_("Vyžadováno aktivní MFA (TOTP). Dokončete aktivaci účtu a registraci aplikace pro autentifikaci."))
            return redirect("account_mfa_view")
        org = get_user_organization(request)
        if not org:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(_("Aktivní členství v organizaci je vyžadováno."))
            return redirect("dashboard")
        request.organization = org
        return view_func(request, *args, **kwargs)
    return wrapper


def _readiness_passed():
    if not os.path.exists(READINESS_FILE):
        return False, "readiness.json chybí — spusťte verify_synthetic_review_readiness.sh"
    try:
        import time
        stat = os.stat(READINESS_FILE)
        if time.time() - stat.st_mtime > 3600:
            return False, "readiness.json je starší než 1 hodina — přegenerujte"
        data = json.load(open(READINESS_FILE))
        if data.get("verdict") != "passed":
            return False, data.get("summary", "readiness selhalo")
        return True, data.get("summary", "OK")
    except Exception as e:
        return False, str(e)


# =============================================================================
# J1 — Worker CRUD
# =============================================================================

@require_org_membership
def worker_list(request):
    """J1: Worker list with pagination and HTMX support."""
    workers = Worker.objects.filter(organization=request.organization).order_by("-id")
    paginator = Paginator(workers, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/worker_list.html", {"page_obj": page_obj})

    return render(request, "portal/worker_list.html", {"page_obj": page_obj})


@require_org_membership
def worker_create(request):
    """J1: Worker create — success, duplicate, invalid, forbidden, interrupted."""
    if request.method == "POST":
        form = WorkerForm(request.POST, organization=request.organization, user=request.user)
        if form.is_valid():
            try:
                worker = create_worker(request.user, request.organization, **form.cleaned_data)
                if request.headers.get("HX-Request"):
                    return render(request, "portal/partials/worker_row.html", {"worker": worker})
                return redirect("worker_detail", pk=worker.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = WorkerForm(organization=request.organization, user=request.user)

    ctx = {"form": form, "action": "create"}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/worker_form.html", ctx)
    return render(request, "portal/worker_form.html", ctx)


@require_org_membership
def worker_detail(request, pk):
    """J1: Worker detail — shows documents, assignments, A1 cases."""
    worker = get_object_or_404(Worker, pk=pk, organization=request.organization)
    documents = Document.objects.filter(organization=request.organization, worker=worker)
    assignments = Assignment.objects.filter(organization=request.organization, worker=worker)
    a1_cases = A1Case.objects.filter(organization=request.organization, worker=worker)

    ctx = {
        "worker": worker,
        "documents": documents,
        "assignments": assignments,
        "a1_cases": a1_cases,
    }
    return render(request, "portal/worker_detail.html", ctx)


@require_org_membership
def worker_edit(request, pk):
    """J1: Worker edit — interrupted save, validation, duplicate check."""
    worker = get_object_or_404(Worker, pk=pk, organization=request.organization)

    if request.method == "POST":
        form = WorkerForm(request.POST, instance=worker, organization=request.organization, user=request.user)
        if form.is_valid():
            try:
                # Check for duplicate (same name + birth_date in org)
                duplicate = Worker.objects.filter(
                    organization=request.organization,
                    given_name=form.cleaned_data["given_name"],
                    family_name=form.cleaned_data["family_name"],
                    birth_date=form.cleaned_data["birth_date"],
                ).exclude(pk=worker.pk).first()
                if duplicate:
                    form.add_error(None, _("Pracovník se stejným jménem a datem narození už existuje."))
                else:
                    form.save()
                    AuditEvent.objects.create(
                        organization=request.organization,
                        actor_ref=f"user:{request.user.pk}",
                        event_type="worker.updated",
                        object_ref=f"worker:{worker.pk}",
                        outcome="success",
                    )
                    if request.headers.get("HX-Request"):
                        return render(request, "portal/partials/worker_row.html", {"worker": worker})
                    return redirect("worker_detail", pk=worker.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = WorkerForm(instance=worker, organization=request.organization, user=request.user)

    ctx = {"form": form, "worker": worker, "action": "edit"}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/worker_form.html", ctx)
    return render(request, "portal/worker_form.html", ctx)


@require_org_membership
@require_http_methods(["POST", "DELETE"])
def worker_delete(request, pk):
    """J1: Worker delete — blocked when protected records exist."""
    from django.db.models.deletion import ProtectedError
    worker = get_object_or_404(Worker, pk=pk, organization=request.organization)
    worker_pk = worker.pk
    try:
        worker.delete()
    except ProtectedError:
        # Worker has related documents/assignments/A1 cases — keep the record.
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="worker.delete_denied",
            object_ref=f"worker:{worker_pk}",
            outcome="denied",
        )
        message = _("Pracovník má přiřazené dokumenty, přiřazení nebo A1 případy a nelze ho smazat.")
        if request.headers.get("HX-Request"):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest(message)
        return render(request, "portal/worker_delete_denied.html", {"worker": worker, "message": message})
    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="worker.deleted",
        object_ref=f"worker:{worker_pk}",
        outcome="success",
    )
    if request.headers.get("HX-Request"):
        # Empty response so hx-swap="outerHTML" removes the row cleanly
        return HttpResponse("")
    return redirect("worker_list")


# =============================================================================
# J2 — Document / OCR
# =============================================================================

@require_org_membership
def document_upload(request, worker_pk):
    """J2: Document upload — valid, mismatch, executable, oversize, duplicate."""
    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)

    if request.method == "POST":
        form = DocumentUploadForm(
            request.POST, request.FILES,
            organization=request.organization,
            worker=worker,
            user=request.user,
        )
        if form.is_valid():
            try:
                file = form.cleaned_data["file"]
                # upload_document validates content, creates the OCR proposal and
                # the document.uploaded audit event (services layer is authoritative).
                document = upload_document(
                    request.user,
                    request.organization,
                    worker,
                    file.name,
                    file.content_type,
                    file.read(),
                )

                if request.headers.get("HX-Request"):
                    return render(request, "portal/partials/document_row.html", {"document": document})
                return redirect("document_detail", pk=document.pk)

            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = DocumentUploadForm(organization=request.organization, worker=worker, user=request.user)

    ctx = {"form": form, "worker": worker}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/document_upload_form.html", ctx)
    return render(request, "portal/document_upload.html", ctx)


@require_org_membership
def document_detail(request, pk):
    """J2: Document detail — OCR proposals, human confirmation, download."""
    document = get_object_or_404(Document, pk=pk, organization=request.organization)
    proposals = OcrProposal.objects.filter(organization=request.organization, document=document)

    if request.method == "POST":
        form = OcrConfirmationForm(request.POST, proposals=proposals)
        if form.is_valid():
            # Process confirmations
            for proposal in proposals:
                field_name = f"confirm_{proposal.field_name}_{proposal.pk}"
                if form.cleaned_data.get(field_name):
                    proposal.confirmed = True
                    proposal.save()
            AuditEvent.objects.create(
                organization=request.organization,
                actor_ref=f"user:{request.user.pk}",
                event_type="ocr.confirmed",
                object_ref=f"document:{document.pk}",
                outcome="success",
            )
            document.state = "confirmed"
            document.save()
            if request.headers.get("HX-Request"):
                return render(request, "portal/partials/ocr_proposals.html", {"proposals": proposals, "document": document})
            return redirect("document_detail", pk=document.pk)
    else:
        form = OcrConfirmationForm(proposals=proposals)

    ctx = {"document": document, "proposals": proposals, "form": form}
    return render(request, "portal/document_detail.html", ctx)


@require_org_membership
def document_download(request, pk):
    """J2: Protected document delivery — zero-byte for unauthorized."""
    document = get_object_or_404(Document, pk=pk, organization=request.organization)

    # In real implementation, this would return X-Accel-Redirect
    # For synthetic M2, we simulate the check
    if document.state not in ("confirmed", "proposal_ready"):
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="document.download_denied",
            object_ref=f"document:{document.pk}",
            outcome="denied",
        )
        return HttpResponseForbidden(_("Dokument není k dispozici."))

    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="document.downloaded",
        object_ref=f"document:{document.pk}",
        outcome="success",
    )

    # Synthetic response — real would use Nginx X-Accel-Redirect
    return JsonResponse({
        "status": "ok",
        "message": "V produkci by zde byl X-Accel-Redirect na chráněný soubor.",
        "opaque_key": document.opaque_key,
    })


# =============================================================================
# J3 — Assignment
# =============================================================================

@require_org_membership
def assignment_create(request, worker_pk):
    """J3: Assignment create — overlap warning, A1 ambiguity block."""
    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)

    if request.method == "POST":
        form = AssignmentForm(
            request.POST,
            organization=request.organization,
            worker=worker,
            user=request.user,
        )
        if form.is_valid():
            try:
                assignment, overlap = create_assignment(
                    request.user,
                    request.organization,
                    worker,
                    start=form.cleaned_data["start"],
                    end=form.cleaned_data["end"],
                    workplace_label=form.cleaned_data["workplace_label"],
                    activity_label=form.cleaned_data["activity_label"],
                )
                if request.headers.get("HX-Request"):
                    return render(request, "portal/partials/assignment_row.html", {
                        "assignment": assignment,
                        "overlap_warning": overlap or getattr(form, "overlap_warning", False),
                    })
                return redirect("worker_detail", pk=worker.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = AssignmentForm(organization=request.organization, worker=worker, user=request.user)

    ctx = {"form": form, "worker": worker, "action": "create"}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/assignment_form.html", ctx)
    return render(request, "portal/assignment_form.html", ctx)


@require_org_membership
def assignment_edit(request, worker_pk, pk):
    """J3: Assignment edit — stale concurrent edit, overlap, A1 ambiguity."""
    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)
    assignment = get_object_or_404(Assignment, pk=pk, organization=request.organization, worker=worker)

    if request.method == "POST":
        form = AssignmentForm(
            request.POST,
            instance=assignment,
            organization=request.organization,
            worker=worker,
            user=request.user,
        )
        if form.is_valid():
            try:
                # Optimistic locking: reject stale concurrent edits.
                submitted_version = form.cleaned_data.get("version")
                if submitted_version is not None and submitted_version != assignment.version:
                    form.add_error(None, _("Přiřazení bylo změněno jiným uživatelem. Načtěte prosím znovu."))
                else:
                    form.instance.version = assignment.version + 1
                    form.save()
                    AuditEvent.objects.create(
                        organization=request.organization,
                        actor_ref=f"user:{request.user.pk}",
                        event_type="assignment.updated",
                        object_ref=f"assignment:{assignment.pk}",
                        outcome="success",
                    )
                    if request.headers.get("HX-Request"):
                        return render(request, "portal/partials/assignment_row.html", {
                            "assignment": assignment,
                            "overlap_warning": getattr(form, "overlap_warning", False),
                        })
                    return redirect("worker_detail", pk=worker.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        # Include current version for optimistic locking
        initial = {"version": assignment.version}
        form = AssignmentForm(instance=assignment, organization=request.organization, worker=worker, user=request.user, initial=initial)

    ctx = {"form": form, "worker": worker, "assignment": assignment, "action": "edit"}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/assignment_form.html", ctx)
    return render(request, "portal/assignment_form.html", ctx)


# =============================================================================
# J4 — A1
# =============================================================================

@require_org_membership
def a1_prepare(request, worker_pk):
    """J4: A1 readiness & preparation — snapshot, generation trigger, retry, staleness."""
    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)
    existing_cases = A1Case.objects.filter(organization=request.organization, worker=worker)
    assignments = Assignment.objects.filter(organization=request.organization, worker=worker)

    if request.method == "POST":
        form = A1PrepareForm(request.POST)
        if form.is_valid():
            try:
                # prepare_a1 creates the a1.prepared/a1.blocked audit event
                # (services layer is authoritative; no duplicate here).
                case = prepare_a1(request.user, request.organization, worker)
                if request.headers.get("HX-Request"):
                    return render(request, "portal/partials/a1_case_row.html", {"case": case})
                return redirect("a1_case_detail", pk=case.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = A1PrepareForm()

    ctx = {
        "worker": worker,
        "form": form,
        "existing_cases": existing_cases,
        "assignments": assignments,
    }
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/a1_prepare_form.html", ctx)
    return render(request, "portal/a1_prepare.html", ctx)


@require_org_membership
def a1_case_detail(request, pk):
    """J4: A1 case detail — approval denial, manual external status distinction."""
    case = get_object_or_404(A1Case, pk=pk, organization=request.organization)

    if request.method == "POST":
        form = A1ApprovalForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["decision"]
            external_status = form.cleaned_data.get("external_status") or "not_submitted"
            # NOTE: `notes` is collected for operator UX but not persisted — the
            # A1Case model has no notes column yet. Persistence arrives with the
            # M4 approval/review history work (no dead binding here).

            if decision == "approve":
                case.external_status = external_status
                case.save()
                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.approved",
                    object_ref=f"a1:{case.pk}",
                    outcome="success",
                )
            else:
                case.external_status = "denied"
                case.save()
                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.denied",
                    object_ref=f"a1:{case.pk}",
                    outcome="denied",
                )

            if request.headers.get("HX-Request"):
                return render(request, "portal/partials/a1_case_row.html", {"case": case})
            return redirect("a1_case_detail", pk=case.pk)
    else:
        form = A1ApprovalForm()

    ctx = {"case": case, "form": form, "worker": case.worker}
    return render(request, "portal/a1_case_detail.html", ctx)


@require_org_membership
def a1_regenerate(request, pk):
    """J4: A1 regenerate — source-change staleness, job retry."""
    case = get_object_or_404(A1Case, pk=pk, organization=request.organization)

    if case.external_status in ("issued", "submitted"):
        return JsonResponse({"error": "Nelze regenerovat již vydané/předané A1."}, status=400)

    # Re-run preparation (simulates job retry with same source)
    new_case = prepare_a1(request.user, request.organization, case.worker)

    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="a1.regenerated",
        object_ref=f"a1:{new_case.pk}",
        outcome="success",
    )

    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/a1_case_row.html", {"case": new_case})
    return redirect("a1_case_detail", pk=new_case.pk)


# =============================================================================
# Health & Dashboard
# =============================================================================

def health(request):
    return JsonResponse({"status": "synthetic-m2", "real_data": False})


def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "portal/dashboard.html", {"unauthenticated": True})
    org = get_user_organization(request)
    if not org:
        return render(request, "portal/dashboard.html", {"unauthenticated": True})

    worker_count = Worker.objects.filter(organization=org).count()
    document_count = Document.objects.filter(organization=org).count()
    assignment_count = Assignment.objects.filter(organization=org).count()
    a1_case_count = A1Case.objects.filter(organization=org).count()

    recent_workers = Worker.objects.filter(organization=org).order_by("-id")[:5]
    recent_documents = Document.objects.filter(organization=org).order_by("-id")[:5]
    recent_assignments = Assignment.objects.filter(organization=org).order_by("-id")[:5]
    recent_a1_cases = A1Case.objects.filter(organization=org).order_by("-id")[:5]

    ctx = {
        "worker_count": worker_count,
        "document_count": document_count,
        "assignment_count": assignment_count,
        "a1_case_count": a1_case_count,
        "recent_workers": recent_workers,
        "recent_documents": recent_documents,
        "recent_assignments": recent_assignments,
        "recent_a1_cases": recent_a1_cases,
    }
    return render(request, "portal/dashboard.html", ctx)


# =============================================================================
# Kontrola Release 1A — Review Surface
# =============================================================================

def _get_or_create_review(user):
    build_id = _get_build_id()
    session_uuid = user.socialaccount_set.first().extra_data.get("uuid", "") if user.socialaccount_set.exists() else ""
    if not session_uuid:
        session_uuid = str(uuid.uuid4())
    rows = {}
    for section, label, _ in REVIEW_SECTIONS:
        obj, created = Release1aReview.objects.get_or_create(
            user=user, section=section,
            defaults={
                "status": Release1aReview.Status.NOT_STARTED,
                "git_commit_at_visit": build_id[:12],
                "app_build_id_at_visit": build_id,
                "review_session_uuid": session_uuid,
            }
        )
        rows[section] = obj
    return rows, session_uuid


def review_dashboard(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())

    review_rows, session_uuid = _get_or_create_review(request.user)

    ctx = {
        "sections": [
            {
                "key": key,
                "label": label,
                "status": review_rows[key].status,
                "note": review_rows[key].note,
                "url": url,
                "done": review_rows[key].status == Release1aReview.Status.DONE,
                "needs_change": review_rows[key].status == Release1aReview.Status.NEEDS_CHANGE,
            }
            for key, label, url in [
                (Release1aReview.Section.WORKER, "Pracovník", "workers/"),
                (Release1aReview.Section.DOCUMENT_OCR, "Dokument a kontrola OCR", "workers/"),
                (Release1aReview.Section.ASSIGNMENT, "Přiřazení", "workers/"),
                (Release1aReview.Section.A1, "Příprava a kontrola A1", "workers/"),
            ]
        ],
        "review_session_uuid": session_uuid,
        "build_id": _get_build_id(),
    }
    return render(request, "portal/review_dashboard.html", ctx)


@require_http_methods(["POST"])
def review_section_update(request, section):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth"}, status=401)
    status = request.POST.get("status", Release1aReview.Status.NOT_STARTED)
    note = request.POST.get("note", "")[:500]

    valid_statuses = [s[0] for s in Release1aReview.Status.choices]
    if status not in valid_statuses:
        return JsonResponse({"error": "invalid_status"}, status=400)

    valid_sections = [s[0] for s in Release1aReview.Section.choices]
    if section not in valid_sections:
        return JsonResponse({"error": "invalid_section"}, status=400)

    build_id = _get_build_id()
    session_uuid = str(uuid.uuid4())
    obj, _ = Release1aReview.objects.update_or_create(
        user=request.user, section=section,
        defaults={
            "status": status,
            "note": note,
            "git_commit_at_visit": build_id[:12],
            "app_build_id_at_visit": build_id,
            "review_session_uuid": session_uuid,
        }
    )

    event_map = {
        Release1aReview.Status.IN_PROGRESS: f"review.{section}.started",
        Release1aReview.Status.DONE: f"review.{section}.completed",
        Release1aReview.Status.NEEDS_CHANGE: f"review.{section}.needs_change",
    }
    if status in event_map and hasattr(request, "organization"):
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type=event_map[status],
            object_ref=f"review:{obj.pk}",
            outcome="success",
        )

    return JsonResponse({"status": status, "note": note})


def review_check_answers(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())

    review_rows, session_uuid = _get_or_create_review(request.user)
    all_done = all(
        r.status == Release1aReview.Status.DONE
        for r in review_rows.values()
    )
    readiness_passed, readiness_reason = _readiness_passed()

    ctx = {
        "sections": [
            {
                "key": key,
                "label": label,
                "status": review_rows[key].status,
                "status_display": review_rows[key].get_status_display(),
                "note": review_rows[key].note,
            }
            for key, label, _ in [
                (Release1aReview.Section.WORKER, "Pracovník", "workers/"),
                (Release1aReview.Section.DOCUMENT_OCR, "Dokument a kontrola OCR", "workers/"),
                (Release1aReview.Section.ASSIGNMENT, "Přiřazení", "workers/"),
                (Release1aReview.Section.A1, "Příprava a kontrola A1", "workers/"),
            ]
        ],
        "all_done": all_done,
        "readiness_passed": readiness_passed,
        "readiness_reason": readiness_reason,
        "scope_text": REVIEW_SCOPE_TEXT,
        "exclusions_text": REVIEW_EXCLUSIONS_TEXT,
        "build_id": _get_build_id(),
        "review_session_uuid": session_uuid,
        "browser_user_agent": request.headers.get("User-Agent", ""),
    }
    return render(request, "portal/review_check_answers.html", ctx)


@require_http_methods(["POST"])
def review_approve(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth"}, status=401)

    review_rows, session_uuid = _get_or_create_review(request.user)
    all_done = all(
        r.status == Release1aReview.Status.DONE
        for r in review_rows.values()
    )
    readiness_passed, _ = _readiness_passed()

    if not all_done or not readiness_passed:
        return JsonResponse(
            {"error": "preconditions not met"}, status=400
        )

    try:
        exceptions = json.loads(request.POST.get("exceptions_json", "[]"))
    except Exception:
        exceptions = []

    build_id = _get_build_id()
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        git_clean = not subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        git_commit = "unknown"
        git_clean = False

    Release1aAcceptance.objects.create(
        user=request.user,
        git_commit_hash=git_commit,
        git_clean=git_clean,
        app_build_id=build_id,
        review_session_uuid=session_uuid,
        scope_text=REVIEW_SCOPE_TEXT,
        exclusions_text=REVIEW_EXCLUSIONS_TEXT,
        browser_user_agent=request.headers.get("User-Agent", ""),
        exceptions_json=json.dumps(exceptions),
        is_stale=False,
    )

    if hasattr(request, "organization"):
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="review.acceptance.submitted",
            object_ref=f"acceptance:{request.user.pk}",
            outcome="success",
        )

    return redirect("review_receipt")


def review_return(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())

    if request.method == "POST":
        note = request.POST.get("note", "")[:500]
        if note and hasattr(request, "organization"):
            AuditEvent.objects.create(
                organization=request.organization,
                actor_ref=f"user:{request.user.pk}",
                event_type="review.acceptance.returned",
                object_ref=f"user:{request.user.pk}",
                outcome="success",
            )
        return redirect("review_dashboard")

    return render(request, "portal/review_return.html")


def review_receipt(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())

    acceptance = Release1aAcceptance.objects.filter(user=request.user).order_by("-accepted_at").first()
    if not acceptance:
        return redirect("review_dashboard")

    current_build_id = _get_build_id()
    is_stale = current_build_id != acceptance.app_build_id

    ctx = {
        "acceptance": acceptance,
        "is_stale": is_stale,
        "current_build_id": current_build_id,
        "scope_text": acceptance.scope_text,
        "exclusions_text": acceptance.exclusions_text,
        "exceptions": json.loads(acceptance.exceptions_json or "[]"),
    }
    return render(request, "portal/review_receipt.html", ctx)


# =============================================================================
# Reviewer activation (one-time invitation URL)
# =============================================================================

def reviewer_activate(request, token):
    import os
    import time
    import json
    from django.contrib.auth import get_user_model
    from django.contrib.auth.hashers import make_password

    User = get_user_model()

    INVITATIONS_DIR = os.environ.get(
        "REVIEW_INVITATIONS_DIR",
        "/var/www/prace-v-nemecku.tvoje.info/runtime/portal/synthetic-review/invitations",
    )
    token_file = os.path.join(INVITATIONS_DIR, f"{token}.json")

    if request.method == "POST":
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if password1 != password2:
            return render(request, "portal/reviewer_activate.html", {
                "token": token, "error": "Hesla se neshodují."
            })
        if len(password1) < 12:
            return render(request, "portal/reviewer_activate.html", {
                "token": token, "error": "Heslo musí mít alespoň 12 znaků."
            })

        if not os.path.exists(token_file):
            return render(request, "portal/reviewer_activate.html", {
                "token": token, "error": "Odkaz je neplatný nebo již byl použit."
            })

        payload = json.loads(open(token_file).read())
        if payload.get("used") or payload.get("expires_at", 0) < time.time():
            return render(request, "portal/reviewer_activate.html", {
                "token": token, "error": "Odkaz vypršel nebo byl již použit."
            })

        user = User.objects.get(pk=payload["user_pk"])
        user.is_active = True
        user.password = make_password(password1)
        user.save()
        payload["used"] = True
        open(token_file, "w").write(json.dumps(payload))
        os.chmod(token_file, 0o600)

        from django.contrib.auth import login
        login(request, user)
        return redirect("account_mfa_deactivate_totp")  # redirect to allauth TOTP enroll

    if not os.path.exists(token_file):
        return render(request, "portal/reviewer_activate.html", {
            "token": token, "error": "Odkaz je neplatný nebo již byl použit."
        })

    payload = json.loads(open(token_file).read())
    if payload.get("used") or payload.get("expires_at", 0) < time.time():
        return render(request, "portal/reviewer_activate.html", {
            "token": token, "error": "Odkaz vypršel nebo byl již použit."
        })

    return render(request, "portal/reviewer_activate.html", {"token": token, "error": None})