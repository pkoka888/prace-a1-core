"""Views for Release 1A M2 vertical slice — J1–J4 journeys."""
from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _

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

def get_user_organization(request):
    """Get the user's active organization with mandatory TOTP."""
    # Anonymous users cannot have organization membership
    if not request.user.is_authenticated:
        return None
    membership = Membership.objects.filter(
        user=request.user, active=True, mfa_verified=True
    ).select_related("organization").first()
    if not membership:
        return None
    return membership.organization


def require_org_membership(view_func):
    """Decorator to ensure user has active org membership with TOTP."""
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated first
        if not request.user.is_authenticated:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(_("Přihlášení je vyžadováno."))
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        org = get_user_organization(request)
        if not org:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(_("Aktivní členství v organizaci s povinným TOTP je vyžadováno."))
            return redirect_to_login(request.get_full_path())
        request.organization = org
        return view_func(request, *args, **kwargs)
    return wrapper


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
    # Handle anonymous users
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