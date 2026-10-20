"""Views for Release 1A M2 vertical slice — J1–J4 journeys."""

from __future__ import annotations

from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
import json
import os
import subprocess
import uuid
from pathlib import Path

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from allauth.mfa.models import Authenticator

from .forms import (
    WorkerForm,
    DocumentUploadForm,
    AssignmentForm,
    A1PrepareForm,
    A1ApprovalForm,
    IntakeWizardForm,
)
from .models import (
    Worker,
    Document,
    Assignment,
    A1Case,
    AuditEvent,
    Membership,
    Release1aReview,
    Release1aReviewSession,
    Release1aAcceptance,
    FieldProposal,
    StatusEvent,
)
from . import security_audit
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

BUILD_MANIFEST_FILE = os.environ.get(
    "REVIEW_BUILD_MANIFEST_PATH",
    "/var/www/prace-v-nemecku.tvoje.info/runtime/portal/synthetic-review/build_manifest.json",
)

READINESS_FILE = os.environ.get(
    "REVIEW_READINESS_PATH",
    "/var/www/prace-v-nemecku.tvoje.info/runtime/portal/synthetic-review/readiness.json",
)


def _current_git_commit() -> str:
    """Return the current HEAD git commit hash, or empty string on failure."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def _current_build_id() -> str:
    """Return the current app build ID from settings manifest, or empty string."""
    try:
        manifest = getattr(settings, "PRACE_RELEASE_MANIFEST", None)
        if isinstance(manifest, dict):
            return str(manifest.get("app_build_id") or "")
    except Exception:
        pass
    return ""


def _eng001_gate_open():
    """
    Check whether the ENG-001 engineering readiness gate is open.

    The runtime approval button depends on ENG-001, not REV-002.
    This is a fail-closed runtime gate: it requires a clean review scope,
    matching HEAD, and matching approvals hash before it will open.

    Returns (open, reason) using the shared approval_register module.
    """
    from planning.approval_register import check_gate, approvals_hash

    root = Path(__file__).resolve().parents[2]

    head = None
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return False, "cannot read HEAD for receipt binding"

    approv_hash = approvals_hash(root)

    return check_gate(
        root,
        "ENG-001",
        gate="implementation_gate",
        require_clean=True,
        expected_commit=head,
        expected_approvals_hash=approv_hash,
    )


REVIEW_SCOPE_PATTERNS = [
    "portal/",
    "requirements.txt",
    "requirements-dev.txt",
    "planning/",
    "plans/",
    "docs/prototypes/",
    "scripts/verify_synthetic_review_readiness.sh",
    "scripts/seed_release1a_dev.py",
    "scripts/release_verifier.py",
    "scripts/seed_verification_db.py",
    "scripts/validate_approvals.py",
    "scripts/validate_planning.py",
    "tests/",
    "runtime/portal/verification/",
    "runtime/portal/synthetic-review/",
    "roadmap.md",
]


def _get_build_id():
    """Read build identity from the manifest written by the readiness script. No caching."""
    try:
        if os.path.exists(BUILD_MANIFEST_FILE):
            data = json.load(open(BUILD_MANIFEST_FILE))
            return data.get("app_build_id", "unknown")
    except Exception:
        pass
    return "unknown"


def _scoped_tree_clean():
    """
    Re-verify that the review-scope tree is clean at approval time.

    Returns (clean, detail) where detail is empty if clean, otherwise a
    description of what changed.
    """
    try:
        tracked = subprocess.check_output(
            ["git", "status", "--porcelain", "--"] + REVIEW_SCOPE_PATTERNS,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        untracked_out = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--"]
            + REVIEW_SCOPE_PATTERNS,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if tracked or untracked_out:
            detail = "\n".join(filter(None, [tracked, "# Untracked:", untracked_out]))
            return False, detail
        return True, ""
    except subprocess.CalledProcessError:
        return False, "git status failed"


def _require_mfa(request):
    """Check that the session has passed allauth TOTP challenge AND user has an enrolled device."""
    if not request.user.is_authenticated:
        return False
    session_methods = request.session.get("account_authentication_methods", [])
    mfa_passed = any(
        isinstance(r, dict) and r.get("method") == "mfa" for r in session_methods
    )
    if not mfa_passed:
        return False
    return Authenticator.objects.filter(
        user=request.user, type=Authenticator.Type.TOTP
    ).exists()


def get_user_organization(request):
    """Get the user's active organization from session membership.

    Returns (organization, error_code) tuple:
    - Exactly one active membership: (org, None)
    - Zero active memberships: (None, "no_membership")
    - Multiple active memberships: (None, "multiple_memberships")

    Requires MFA-authenticated session.
    """
    if not request.user.is_authenticated:
        return None, "not_authenticated"
    memberships = list(
        Membership.objects.filter(user=request.user, active=True).select_related(
            "organization"
        )
    )
    if len(memberships) == 0:
        return None, "no_membership"
    if len(memberships) > 1:
        return None, "multiple_memberships"
    return memberships[0].organization, None


def require_org_membership(view_func):
    """Decorator: requires authenticated user with active org membership AND allauth TOTP session.

    Records authorization denials via security_audit (loop-protected).
    Anonymous redirects to login are not recorded (ordinary auth-required behavior).
    """

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(_("Přihlášení je vyžadováno."))
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        if not _require_mfa(request):
            security_audit.record_authorization_denial(
                request,
                request.user,
                reason_code="mfa_required",
                object_ref=request.path,
            )
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(
                    _(
                        "Vyžadováno aktivní MFA (TOTP). Dokončete aktivaci účtu a registraci aplikace pro autentifikaci."
                    )
                )
            return redirect("mfa_index")
        org, org_error = get_user_organization(request)
        if org_error == "no_membership":
            security_audit.record_authorization_denial(
                request,
                request.user,
                reason_code="membership_inactive",
                object_ref=request.path,
            )
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(
                    _("Aktivní členství v organizaci je vyžadováno.")
                )
            return redirect("dashboard")
        if org_error == "multiple_memberships":
            security_audit.record_authorization_denial(
                request,
                request.user,
                reason_code="multiple_memberships",
                object_ref=request.path,
            )
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(
                    _("Více aktivních členství v organizaci není povoleno.")
                )
            return redirect("dashboard")
        request.organization = org
        return view_func(request, *args, **kwargs)

    return wrapper


def _readiness_passed():
    if not os.path.exists(READINESS_FILE):
        return (
            False,
            "readiness.json chybí — spusťte verify_synthetic_review_readiness.sh",
        )
    try:
        import time

        stat = os.stat(READINESS_FILE)
        if time.time() - stat.st_mtime > 3600:
            return False, "readiness.json je starší než 1 hodina — přegenerujte"
        data = json.load(open(READINESS_FILE))
        if data.get("verdict") != "passed":
            return False, data.get("summary", "readiness selhalo")
        current_build = _get_build_id()
        stored_build = data.get("app_build_id", "")
        if stored_build != current_build:
            return (
                False,
                f"build mismatch: readiness je pro {stored_build[:12]}, aktuální {current_build[:12]}",
            )
        return True, data.get("summary", "OK")
    except Exception as e:
        return False, str(e)


# =============================================================================
# J1 — Worker CRUD
# =============================================================================


@require_org_membership
def worker_list(request):
    """J1: Worker list with pagination and HTMX support."""
    from .services import require_capability, Forbidden

    try:
        require_capability(request.user, request.organization, "worker:read")
    except Forbidden:
        return HttpResponse(status=403)
    workers = Worker.objects.filter(organization=request.organization).order_by("-id")
    paginator = Paginator(workers, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.headers.get("HX-Request"):
        return render(
            request, "portal/partials/worker_list.html", {"page_obj": page_obj}
        )

    return render(request, "portal/worker_list.html", {"page_obj": page_obj})


@require_org_membership
def worker_create(request):
    """J1: Worker create — success, duplicate, invalid, forbidden, interrupted."""
    from .services import Forbidden

    if request.method == "POST":
        form = WorkerForm(
            request.POST, organization=request.organization, user=request.user
        )
        if form.is_valid():
            try:
                worker = create_worker(
                    request.user, request.organization, **form.cleaned_data
                )
                if request.headers.get("HX-Request"):
                    return render(
                        request, "portal/partials/worker_row.html", {"worker": worker}
                    )
                return redirect("worker_detail", pk=worker.pk)
            except Forbidden:
                return HttpResponse(status=403)
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
    """J1: Worker detail — shows documents, assignments, A1 cases with tabbed interface."""
    from .services import require_capability, Forbidden
    from .models import WorkerIdentityRevision
    from .document_labels import FIELD_LABELS

    try:
        require_capability(request.user, request.organization, "worker:read")
    except Forbidden:
        return HttpResponse(status=403)
    worker = get_object_or_404(Worker, pk=pk, organization=request.organization)
    documents = (
        Document.objects.filter(organization=request.organization)
        .filter(Q(worker=worker) | Q(ocrrun__documentregionassociation__worker=worker))
        .distinct()
        .order_by("-id")
    )
    assignments = Assignment.objects.filter(
        organization=request.organization, worker=worker
    ).order_by("-id")
    a1_cases = A1Case.objects.filter(
        organization=request.organization, worker=worker
    ).order_by("-id")
    tab = request.GET.get("tab", "")

    a1_readiness = worker_a1_readiness(worker, request.organization)

    revision = (
        WorkerIdentityRevision.objects.filter(
            organization=request.organization, worker=worker
        )
        .order_by("-revision_number")
        .first()
    )
    ctx = {
        "accepted_identity": [
            (FIELD_LABELS.get(k, k), v) for k, v in revision.confirmed_fields.items()
        ]
        if revision
        else [],
        "worker": worker,
        "documents": documents,
        "assignments": assignments,
        "a1_cases": a1_cases,
        "tab": tab,
        "a1_readiness": a1_readiness,
    }
    return render(request, "portal/worker_detail.html", ctx)


@require_org_membership
@transaction.atomic
def worker_edit(request, pk):
    """J1: Worker edit — interrupted save, validation, duplicate check."""
    from .services import require_capability, Forbidden

    try:
        require_capability(request.user, request.organization, "worker:update")
    except Forbidden:
        return HttpResponse(status=403)
    workers = (
        Worker.objects.select_for_update()
        if request.method == "POST"
        else Worker.objects.all()
    )
    worker = get_object_or_404(workers, pk=pk, organization=request.organization)
    # ModelForm validation mutates its instance before save; retain persisted state.
    original_state = worker.state

    if request.method == "POST":
        form = WorkerForm(
            request.POST,
            instance=worker,
            organization=request.organization,
            user=request.user,
        )
        if form.is_valid():
            try:
                new_state = form.cleaned_data.get("state")
                if new_state != original_state and Worker.State.ARCHIVED in (
                    original_state,
                    new_state,
                ):
                    try:
                        require_capability(
                            request.user, request.organization, "worker:archive"
                        )
                    except Forbidden:
                        return HttpResponse(status=403)
                duplicate = (
                    Worker.objects.filter(
                        organization=request.organization,
                        given_name=form.cleaned_data["given_name"],
                        family_name=form.cleaned_data["family_name"],
                        birth_date=form.cleaned_data["birth_date"],
                    )
                    .exclude(pk=worker.pk)
                    .first()
                )
                if duplicate:
                    form.add_error(
                        None,
                        _("Pracovník se stejným jménem a datem narození už existuje."),
                    )
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
                        return render(
                            request,
                            "portal/partials/worker_row.html",
                            {"worker": worker},
                        )
                    return redirect("worker_detail", pk=worker.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = WorkerForm(
            instance=worker, organization=request.organization, user=request.user
        )

    ctx = {"form": form, "worker": worker, "action": "edit"}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/worker_form.html", ctx)
    return render(request, "portal/worker_form.html", ctx)


@require_org_membership
@require_http_methods(["POST", "DELETE"])
def worker_delete(request, pk):
    """Hard deletion stays disabled until a scoped retention/deletion policy is wired."""
    from .services import require_capability, Forbidden

    try:
        require_capability(request.user, request.organization, "worker:read")
    except Forbidden:
        return HttpResponse(status=403)
    worker = get_object_or_404(Worker, pk=pk, organization=request.organization)
    # worker:archive authorizes a reversible state change, never permanent erasure.
    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="worker.delete_denied",
        object_ref=f"worker:{worker.pk}",
        outcome="denied",
    )
    return HttpResponse(
        _(
            "Trvalé smazání není dostupné. Požádejte správce o řízené vyřízení žádosti o výmaz."
        ),
        status=403,
        content_type="text/plain; charset=utf-8",
    )


# =============================================================================
# J2 — Document / OCR
# =============================================================================


@require_org_membership
def document_upload(request, worker_pk):
    """J2: Document upload — valid, mismatch, executable, oversize, duplicate."""
    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)

    if request.method == "POST":
        form = DocumentUploadForm(
            request.POST,
            request.FILES,
            organization=request.organization,
            worker=worker,
            user=request.user,
        )
        if form.is_valid():
            try:
                file = form.cleaned_data["file"]
                # upload_document validates content, queues durable OCR work and
                # the document.uploaded audit event (services layer is authoritative).
                document = upload_document(
                    request.user,
                    request.organization,
                    worker,
                    file.name,
                    file.content_type,
                    file.read(),
                    _sync=False,
                )

                if request.headers.get("HX-Request"):
                    return render(
                        request,
                        "portal/partials/document_row.html",
                        {"document": document},
                    )
                return redirect("document_detail", pk=document.pk)

            except Exception:
                form.add_error(
                    None, _("Dokument nelze přijmout. Zkontrolujte formát a oprávnění.")
                )
    else:
        form = DocumentUploadForm(
            organization=request.organization, worker=worker, user=request.user
        )

    ctx = {"form": form, "worker": worker}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/document_upload_form.html", ctx)
    return render(request, "portal/document_upload.html", ctx)


@require_org_membership
def document_detail(request, pk):
    from .intake_views import detail

    return detail(request, pk)


@require_org_membership
def document_download(request, pk):
    from .intake_views import original

    return original(request, pk)


@require_org_membership
def document_intake_unassigned(request):
    from .intake_views import upload_unassigned

    return upload_unassigned(request)


@require_org_membership
def document_crop(request, run_id, region_id, variant):
    from .intake_views import crop

    return crop(request, run_id, region_id, variant)


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
                    return render(
                        request,
                        "portal/partials/assignment_row.html",
                        {
                            "assignment": assignment,
                            "overlap_warning": overlap
                            or getattr(form, "overlap_warning", False),
                        },
                    )
                return redirect("worker_detail", pk=worker.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = AssignmentForm(
            organization=request.organization, worker=worker, user=request.user
        )

    ctx = {"form": form, "worker": worker, "action": "create"}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/assignment_form.html", ctx)
    return render(request, "portal/assignment_form.html", ctx)


@require_org_membership
@transaction.atomic
def assignment_edit(request, worker_pk, pk):
    """J3: Assignment edit — stale concurrent edit, overlap, A1 ambiguity."""
    from .identity import _authorize, _lock_organization
    from .services import Forbidden

    try:
        _authorize(request.user, request.organization, "assignment:update")
    except Forbidden:
        return HttpResponseForbidden("ACCESS_DENIED")
    _lock_organization(request.organization)
    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)
    assignment = get_object_or_404(
        Assignment, pk=pk, organization=request.organization, worker=worker
    )

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
                if submitted_version is None or submitted_version != assignment.version:
                    form.add_error(
                        None,
                        _(
                            "Přiřazení bylo změněno jiným uživatelem. Načtěte prosím znovu."
                        ),
                    )
                else:
                    with transaction.atomic():
                        form.instance.version = assignment.version + 1
                        form.save()
                        AuditEvent.objects.create(
                            organization=request.organization,
                            actor_ref=f"user:{request.user.pk}",
                            event_type="assignment.updated",
                            object_ref=f"assignment:{assignment.pk}",
                            outcome="success",
                        )
                        A1Case.objects.filter(
                            organization=request.organization, worker=worker
                        ).update(is_stale=True)
                    if request.headers.get("HX-Request"):
                        return render(
                            request,
                            "portal/partials/assignment_row.html",
                            {
                                "assignment": assignment,
                                "overlap_warning": getattr(
                                    form, "overlap_warning", False
                                ),
                            },
                        )
                    return redirect("worker_detail", pk=worker.pk)
            except Exception:
                form.add_error(
                    None, _("Změnu nelze uložit. Obnovte formulář a zkuste to znovu.")
                )
    else:
        # Include current version for optimistic locking
        initial = {"version": assignment.version}
        form = AssignmentForm(
            instance=assignment,
            organization=request.organization,
            worker=worker,
            user=request.user,
            initial=initial,
        )

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
    existing_cases = A1Case.objects.filter(
        organization=request.organization, worker=worker
    )
    assignments = Assignment.objects.filter(
        organization=request.organization, worker=worker
    )

    if request.method == "POST":
        form = A1PrepareForm(request.POST)
        if form.is_valid():
            try:
                # prepare_a1 creates the a1.prepared/a1.blocked audit event
                # (services layer is authoritative; no duplicate here).
                case = prepare_a1(request.user, request.organization, worker)
                if request.headers.get("HX-Request"):
                    return render(
                        request, "portal/partials/a1_case_row.html", {"case": case}
                    )
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

    # An "application draft" is any case that has been prepared through
    # the prepare_a1 path. The draft_reservation may not exist yet —
    # it is created on demand by the a1_draft_generate view. Show the
    # application-draft UI (current-generation + draft-generation form)
    # as soon as the case is ready, so the operator does not have to
    # click through the legacy approve/reject form before generating
    # the unverified draft.
    is_application_draft = (
        hasattr(case, "draft_reservation") or case.readiness == A1Case.Readiness.READY
    )

    # A reserved-but-not-yet-published generation is a protected intermediate
    # stage: the legacy operator decision form and any confirmation stay
    # blocked until the protected draft bytes exist. ``reserve_application_generation``
    # creates the generation row together with the reservation; publication is
    # what stamps ``artifact_reference`` onto it.
    from .models import A1DraftGeneration, A1DraftReservation

    has_reservation = A1DraftReservation.objects.filter(case=case).exists()
    has_published_generation = (
        A1DraftGeneration.objects.filter(reservation__case=case)
        .exclude(prepared_artifact_hash="")
        .exists()
    )
    pending_draft = has_reservation and not has_published_generation
    if is_application_draft and request.method == "POST" and pending_draft:
        return JsonResponse(
            {"error": "GENERATION_CONFIRMATION_NOT_AVAILABLE"}, status=409
        )

    if request.method == "POST":
        form = A1ApprovalForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["decision"]
            external_status = (
                form.cleaned_data.get("external_status") or "not_submitted"
            )
            notes = (form.cleaned_data.get("notes") or "").strip()

            if decision == "approve":
                case.external_status = external_status
                case.notes = notes
                case.save(update_fields=["external_status", "notes"])
                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.approved",
                    object_ref=f"a1:{case.pk}",
                    outcome="success",
                )
            else:
                case.external_status = "denied"
                case.notes = notes
                case.save(update_fields=["external_status", "notes"])
                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.denied",
                    object_ref=f"a1:{case.pk}",
                    outcome="denied",
                )

            if request.headers.get("HX-Request"):
                return render(
                    request, "portal/partials/a1_case_row.html", {"case": case}
                )
            return redirect("a1_case_detail", pk=case.pk)
    else:
        form = A1ApprovalForm()

    if is_application_draft:
        from django.core.exceptions import ObjectDoesNotExist
        from .a1_generation_access import current_generation
        from .services import Forbidden, StaleWrite
        from .j4_artifacts import ArtifactError

        generation = None
        try:
            generation = current_generation(request.user, request.organization, case.pk)
        except Forbidden:
            return HttpResponseForbidden("ACCESS_DENIED")
        except (ObjectDoesNotExist, StaleWrite, ValueError, OSError, ArtifactError):
            pass
        response = render(
            request,
            "portal/a1_case_detail.html",
            {
                "case": case,
                "worker": case.worker,
                "is_application_draft": True,
                "generation": generation,
                "has_reservation": has_reservation,
            },
        )
        from django.utils.cache import add_never_cache_headers

        add_never_cache_headers(response)
        return response

    ctx = {"case": case, "form": form, "worker": case.worker}
    return render(request, "portal/a1_case_detail.html", ctx)


@require_org_membership
@require_http_methods(["POST"])
def a1_regenerate(request, pk):
    """J4: A1 regenerate — source-change staleness, job retry.

    Idempotent: if the worker's source state has not changed since this case
    was prepared, the existing case is reused (and is_stale is cleared). When
    the source differs, a new A1Case is created via prepare_a1().
    """

    case = get_object_or_404(A1Case, pk=pk, organization=request.organization)

    if hasattr(case, "draft_reservation"):
        return JsonResponse(
            {"error": "GENERATION_CONFIRMATION_NOT_AVAILABLE"}, status=409
        )

    if case.external_status in ("issued", "submitted"):
        return JsonResponse(
            {"error": "Nelze regenerovat již vydané/předané A1."}, status=400
        )

    worker = case.worker
    from .services import current_artifact_dependencies, current_case_source

    current_hash = current_case_source(case)
    artifact_changed = (
        bool(case.artifact_reference)
        and current_artifact_dependencies(case) != case.artifact_dependencies
    )

    if current_hash == case.source_hash and not artifact_changed:
        was_stale = case.is_stale
        if case.is_stale:
            case.is_stale = False
            case.save(update_fields=["is_stale"])
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.regenerated_no_change",
            object_ref=f"a1:{case.pk}",
            outcome="success" if not was_stale else "stale_cleared",
        )
        if request.headers.get("HX-Request"):
            return render(request, "portal/partials/a1_case_row.html", {"case": case})
        return redirect("a1_case_detail", pk=case.pk)

    new_case = prepare_a1(request.user, request.organization, worker)
    if artifact_changed:
        case.is_stale = True
        case.save(update_fields=["is_stale"])
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


@require_org_membership
@require_http_methods(["POST"])
def a1_draft_generate(request, pk):
    """Generate the unverified A1 draft PDF (canonical unverified publisher).

    The reservation may not exist yet; this view creates it through the
    canonical unverified publisher (``prepare_application_draft``) and
    redirects back to the case detail page, where the download links
    become visible. A reservation-less case therefore represents a
    prepared-but-not-yet-rendered state, not an error.
    """
    from .a1_drafts import prepare_application_draft, DraftInputBlocked
    from .services import Forbidden, StaleWrite

    case = get_object_or_404(A1Case, pk=pk, organization=request.organization)
    try:
        generation = prepare_application_draft(
            request.user, request.organization, case.pk
        )
    except DraftInputBlocked as exc:
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.draft_blocked",
            object_ref=f"a1:{case.pk}",
            outcome="blocked",
        )
        return JsonResponse(
            {"error": "A1_DRAFT_BLOCKED", "reason": str(exc)}, status=409
        )
    except (Forbidden, StaleWrite, ValueError, OSError) as exc:
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.draft_failed",
            object_ref=f"a1:{case.pk}",
            outcome="failed",
        )
        return JsonResponse(
            {"error": "A1_DRAFT_FAILED", "reason": str(exc)}, status=409
        )
    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="a1.draft_generated",
        object_ref=f"generation:{generation.pk}",
        outcome="success",
    )
    return redirect("a1_case_detail", pk=case.pk)


# =============================================================================
# Health & Dashboard
# =============================================================================


@never_cache
@require_safe
def health(request):
    """Static synthetic liveness marker; makes no dependency readiness claim.

    Synthetic-only posture is always exposed. No DB queries, no FS probes,
    no secrets. The infra team's edge probes use this to confirm the
    service is alive AND that it is the synthetic posture (never real data).
    """
    from . import runtime_contract

    return JsonResponse(runtime_contract.health_payload())


@never_cache
@require_safe
def synthetic_contract(request):
    """Synthetic-only contract for infra edge probes.

    Returns the full public-facing runtime contract: mode, supervised
    posture, build identity, database engine basename, storage root
    basename, MFA requirement. Sanitized: no secrets, no full paths, no
    identifiers, no PII. The contract never includes information that
    would change between a synthetic posture and a real-data posture, so
    its shape is stable enough for the infra layer to diff against an
    expected fixture.
    """
    from . import runtime_contract

    return JsonResponse(runtime_contract.synthetic_contract_payload())


@never_cache
@require_safe
def readiness(request):
    """Supervised runtime: killable process deadline. Legacy test mode: direct checks."""
    import time
    from django.conf import settings
    from . import readiness_runner, runtime_contract

    started = time.monotonic()
    budget = int(getattr(settings, "PRACE_READINESS_BUDGET_MS", 2000))
    if getattr(settings, "PRACE_SUPERVISED", False):
        body = readiness_runner.supervised_probe(budget)
    else:
        # In-memory test DBs cannot be inspected from a separate process.
        # These settings are never supported supervised service targets.
        body = readiness_runner.collect_checks()
    elapsed = round((time.monotonic() - started) * 1000)
    if elapsed > budget:
        body.update(status="not_ready", reason="deadline_exceeded")
    body.update(
        mode=runtime_contract.runtime_mode(),
        supervised=runtime_contract.is_supervised(),
        synthetic_only=runtime_contract.synthetic_only(),
        real_data=False,
        build_id=runtime_contract.build_identity()[0],
        git_commit=runtime_contract.build_identity()[1],
        budget_ms=budget,
        elapsed_ms=elapsed,
    )
    return JsonResponse(body, status=200 if body["status"] == "ready" else 503)


def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "portal/dashboard.html", {"unauthenticated": True})
    org, org_error = get_user_organization(request)
    if org_error:
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


@require_org_membership
def attention_queue(request):
    """Dashboard attention queue: documents awaiting review, incomplete workers,
    assignment conflicts, stale/blocked A1 cases, expiring documents."""

    docs_awaiting_review = (
        Document.objects.filter(
            organization=request.organization, state=Document.State.QUARANTINED
        )
        .select_related("worker")
        .order_by("-id")[:10]
    )

    incomplete_workers = Worker.objects.filter(
        organization=request.organization, state=Worker.State.DRAFT
    ).order_by("-id")[:10]

    workers_without_docs = (
        Worker.objects.filter(organization=request.organization)
        .exclude(
            id__in=Document.objects.filter(
                organization=request.organization
            ).values_list("worker_id", flat=True)
        )
        .order_by("-id")[:10]
    )

    a1_blocked = (
        A1Case.objects.filter(
            organization=request.organization, readiness=A1Case.Readiness.BLOCKED
        )
        .select_related("worker")
        .order_by("-id")[:10]
    )

    ctx = {
        "docs_awaiting_review": docs_awaiting_review,
        "incomplete_workers": incomplete_workers,
        "workers_without_docs": workers_without_docs,
        "a1_blocked": a1_blocked,
    }
    return render(request, "portal/attention_queue.html", ctx)


@require_org_membership
def document_list(request):
    """Global document list with filters."""
    documents = (
        Document.objects.filter(organization=request.organization)
        .select_related("worker")
        .order_by("-id")
    )
    state_filter = request.GET.get("state")
    if state_filter:
        documents = documents.filter(state=state_filter)
    paginator = Paginator(documents, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    ctx = {
        "page_obj": page_obj,
        "state_filter": state_filter,
        "state_choices": Document._meta.get_field("state").choices,
    }
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/document_list.html", ctx)
    return render(request, "portal/document_list.html", ctx)


@require_org_membership
def assignment_list(request):
    """Global assignment list with filters and grouping."""
    import datetime

    today = datetime.date.today()

    state_filter = request.GET.get("state")
    group = request.GET.get("group")

    base_qs = Assignment.objects.filter(
        organization=request.organization
    ).select_related("worker")

    if state_filter:
        base_qs = base_qs.filter(state=state_filter)

    if group == "current":
        base_qs = base_qs.filter(start__lte=today, end__gte=today)
    elif group == "upcoming":
        base_qs = base_qs.filter(start__gt=today)
    elif group == "history":
        base_qs = base_qs.filter(end__lt=today)

    assignments = base_qs.order_by("-id")
    paginator = Paginator(assignments, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    current_count = Assignment.objects.filter(
        organization=request.organization, start__lte=today, end__gte=today
    ).count()
    upcoming_count = Assignment.objects.filter(
        organization=request.organization, start__gt=today
    ).count()
    history_count = Assignment.objects.filter(
        organization=request.organization, end__lt=today
    ).count()

    ctx = {
        "page_obj": page_obj,
        "state_filter": state_filter,
        "state_choices": Assignment._meta.get_field("state").choices,
        "group": group,
        "current_count": current_count,
        "upcoming_count": upcoming_count,
        "history_count": history_count,
    }
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/assignment_list.html", ctx)
    return render(request, "portal/assignment_list.html", ctx)


@require_org_membership
def a1_list(request):
    """Global A1 case list with filters."""
    cases = (
        A1Case.objects.filter(organization=request.organization)
        .select_related("worker")
        .order_by("-id")
    )
    readiness_filter = request.GET.get("readiness")
    if readiness_filter:
        cases = cases.filter(readiness=readiness_filter)
    paginator = Paginator(cases, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    ctx = {
        "page_obj": page_obj,
        "readiness_filter": readiness_filter,
    }
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/a1_list.html", ctx)
    return render(request, "portal/a1_list.html", ctx)


@require_org_membership
def a1_variant_counts(request):
    from .services import count_workers_by_variant, require_capability

    require_capability(request.user, request.organization, "a1:prepare")
    data = count_workers_by_variant(request.organization)
    return JsonResponse(data)


@require_org_membership
def intake_wizard(request):
    """Unified Přidat pracovníka wizard with three paths: Upload, Paste, Manual.

    Upload and Paste require an existing worker. Manual creates a new worker.
    """
    if request.method == "POST":
        form = IntakeWizardForm(
            request.POST, organization=request.organization, user=request.user
        )
        if form.is_valid():
            intake_type = form.cleaned_data.get("intake_type")
            if intake_type == "upload":
                return redirect("worker_list")
            elif intake_type == "paste":
                return redirect("intake_paste")
            else:
                return redirect("worker_create")
    else:
        form = IntakeWizardForm(organization=request.organization, user=request.user)
    ctx = {"form": form}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/intake_wizard_form.html", ctx)
    return render(request, "portal/intake_wizard.html", ctx)


@require_org_membership
def intake_upload(request, worker_pk):
    from .intake_views import upload_unassigned

    worker = get_object_or_404(Worker, pk=worker_pk, organization=request.organization)
    return upload_unassigned(request, worker)


@require_org_membership
def intake_paste(request):
    """Paste text for OCR processing."""
    if request.method == "POST":
        pasted_text = request.POST.get("pasted_text", "")
    else:
        pasted_text = ""
    ctx = {"pasted_text": pasted_text}
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/intake_paste_form.html", ctx)
    return render(request, "portal/intake_paste.html", ctx)


# =============================================================================
# Kontrola Release 1A — Review Surface
# =============================================================================


def _get_or_create_review_session(request):
    """Find or create a review session for (user, org, build_id)."""
    build_id = _get_build_id()
    session, _ = Release1aReviewSession.objects.get_or_create(
        user=request.user,
        organization=request.organization,
        build_id=build_id,
    )
    return session


def _get_review_session_readonly(request):
    """Get existing review session or None (no creation for GET)."""
    build_id = _get_build_id()
    return Release1aReviewSession.objects.filter(
        user=request.user,
        organization=request.organization,
        build_id=build_id,
    ).first()


def _get_section_rows(session):
    """Get or create section rows for a session (for POST use)."""
    rows = {}
    for section_key, _label, _url in REVIEW_SECTIONS:
        row, _ = Release1aReview.objects.get_or_create(
            session=session,
            section=section_key,
            defaults={"status": Release1aReview.Status.NOT_STARTED},
        )
        rows[section_key] = row
    return rows


def _get_section_rows_readonly(session):
    """Get existing section rows (for GET use, no creation)."""
    rows = {}
    for section_key, _label, _url in REVIEW_SECTIONS:
        row = Release1aReview.objects.filter(
            session=session, section=section_key
        ).first()
        if row:
            rows[section_key] = row
    return rows


@require_org_membership
def review_dashboard(request):
    session = _get_review_session_readonly(request)
    if session:
        review_rows = _get_section_rows_readonly(session)
    else:
        review_rows = {}

    sections_data = []
    for key, label, url in [
        (Release1aReview.Section.WORKER, "Pracovník", "workers/"),
        (Release1aReview.Section.DOCUMENT_OCR, "Dokument a kontrola OCR", "workers/"),
        (Release1aReview.Section.ASSIGNMENT, "Přiřazení", "workers/"),
        (Release1aReview.Section.A1, "Příprava a kontrola A1", "workers/"),
    ]:
        if session and key in review_rows:
            row = review_rows[key]
            sections_data.append(
                {
                    "key": key,
                    "label": label,
                    "status": row.status,
                    "status_display": row.get_status_display(),
                    "note": row.note,
                    "url": url,
                    "done": row.status == Release1aReview.Status.DONE,
                    "needs_change": row.status == Release1aReview.Status.NEEDS_CHANGE,
                }
            )
        else:
            sections_data.append(
                {
                    "key": key,
                    "label": label,
                    "status": None,
                    "status_display": "Nezahájeno",
                    "note": "",
                    "url": url,
                    "done": False,
                    "needs_change": False,
                }
            )

    ctx = {
        "sections": sections_data,
        "review_session_pk": session.pk if session else None,
        "build_id": _get_build_id(),
    }
    return render(request, "portal/review_dashboard.html", ctx)


@require_org_membership
@require_http_methods(["POST"])
def review_section_update(request, section):
    status = request.POST.get("status", Release1aReview.Status.NOT_STARTED)
    note = request.POST.get("note", "")[:500]

    valid_statuses = [s[0] for s in Release1aReview.Status.choices]
    if status not in valid_statuses:
        return JsonResponse({"error": "invalid_status"}, status=400)

    valid_sections = [s[0] for s in Release1aReview.Section.choices]
    if section not in valid_sections:
        return JsonResponse({"error": "invalid_section"}, status=400)

    session = _get_or_create_review_session(request)
    obj, _ = Release1aReview.objects.update_or_create(
        session=session,
        section=section,
        defaults={"status": status, "note": note},
    )

    event_map = {
        Release1aReview.Status.IN_PROGRESS: f"review.{section}.started",
        Release1aReview.Status.DONE: f"review.{section}.completed",
        Release1aReview.Status.NEEDS_CHANGE: f"review.{section}.needs_change",
    }
    if status in event_map:
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type=event_map[status],
            object_ref=f"review:{obj.pk}",
            outcome="success",
        )

    return JsonResponse({"status": status, "note": note})


@require_org_membership
def review_check_answers(request):
    session = _get_or_create_review_session(request)
    review_rows = _get_section_rows(session)
    all_done = all(
        r.status == Release1aReview.Status.DONE for r in review_rows.values()
    )
    readiness_passed, readiness_reason = _readiness_passed()
    gate_open, gate_reason = _eng001_gate_open()

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
                (
                    Release1aReview.Section.DOCUMENT_OCR,
                    "Dokument a kontrola OCR",
                    "workers/",
                ),
                (Release1aReview.Section.ASSIGNMENT, "Přiřazení", "workers/"),
                (Release1aReview.Section.A1, "Příprava a kontrola A1", "workers/"),
            ]
        ],
        "all_done": all_done,
        "readiness_passed": readiness_passed,
        "readiness_reason": readiness_reason,
        "gate_open": gate_open,
        "gate_reason": gate_reason,
        "scope_text": REVIEW_SCOPE_TEXT,
        "exclusions_text": REVIEW_EXCLUSIONS_TEXT,
        "build_id": _get_build_id(),
        "review_session_pk": session.pk,
        "browser_user_agent": request.headers.get("User-Agent", ""),
    }
    return render(request, "portal/review_check_answers.html", ctx)


@require_org_membership
@require_http_methods(["POST"])
def review_approve(request):
    session = _get_or_create_review_session(request)

    existing = Release1aAcceptance.objects.filter(session=session).first()
    if existing:
        return redirect("review_receipt")

    review_rows = _get_section_rows(session)
    all_done = all(
        r.status == Release1aReview.Status.DONE for r in review_rows.values()
    )
    readiness_passed, readiness_reason = _readiness_passed()

    build_id = _get_build_id()
    scoped_clean, scoped_detail = _scoped_tree_clean()

    if not all_done or not readiness_passed:
        return JsonResponse(
            {"error": "preconditions not met", "detail": readiness_reason}, status=400
        )

    if not scoped_clean:
        return JsonResponse(
            {
                "error": "tree not clean at approval time — commit scoped changes first",
                "detail": scoped_detail,
            },
            status=400,
        )

    gate_open, gate_reason = _eng001_gate_open()
    if not gate_open:
        return JsonResponse(
            {"error": "REV-002 engineering gate is blocked", "detail": gate_reason},
            status=403,
        )

    exceptions = [
        {"section": key, "note": row.note}
        for key, row in review_rows.items()
        if row.note
    ]

    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        git_clean = True
    except Exception:
        git_commit = "unknown"
        git_clean = False

    Release1aAcceptance.objects.create(
        user=request.user,
        organization=request.organization,
        session=session,
        git_commit_hash=git_commit,
        git_clean=git_clean,
        app_build_id=build_id,
        scope_text=REVIEW_SCOPE_TEXT,
        exclusions_text=REVIEW_EXCLUSIONS_TEXT,
        browser_user_agent=request.headers.get("User-Agent", ""),
        exceptions_json=json.dumps(exceptions),
        is_stale=False,
    )

    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="review.acceptance.submitted",
        object_ref=f"acceptance:{request.user.pk}",
        outcome="success",
    )

    return redirect("review_receipt")


@require_org_membership
def review_return(request):
    if request.method == "POST":
        note = request.POST.get("note", "")[:500]
        if note:
            AuditEvent.objects.create(
                organization=request.organization,
                actor_ref=f"user:{request.user.pk}",
                event_type="review.acceptance.returned",
                object_ref=f"user:{request.user.pk}",
                outcome="success",
            )
        return redirect("review_dashboard")

    return render(request, "portal/review_return.html")


@require_org_membership
def review_receipt(request):
    acceptance = (
        Release1aAcceptance.objects.filter(
            user=request.user, organization=request.organization
        )
        .order_by("-accepted_at")
        .first()
    )
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
            return render(
                request,
                "portal/reviewer_activate.html",
                {"token": token, "error": "Hesla se neshodují."},
            )
        if len(password1) < 12:
            return render(
                request,
                "portal/reviewer_activate.html",
                {"token": token, "error": "Heslo musí mít alespoň 12 znaků."},
            )

        if not os.path.exists(token_file):
            return render(
                request,
                "portal/reviewer_activate.html",
                {"token": token, "error": "Odkaz je neplatný nebo již byl použit."},
            )

        payload = json.loads(open(token_file).read())
        if payload.get("used") or payload.get("expires_at", 0) < time.time():
            return render(
                request,
                "portal/reviewer_activate.html",
                {"token": token, "error": "Odkaz vypršel nebo byl již použit."},
            )

        user = User.objects.get(pk=payload["user_pk"])
        user.is_active = True
        user.password = make_password(password1)
        user.save()
        payload["used"] = True
        open(token_file, "w").write(json.dumps(payload))
        os.chmod(token_file, 0o600)

        from django.contrib.auth import logout

        logout(request)
        return redirect("mfa_activate_totp")  # redirect to allauth TOTP enrollment

    if not os.path.exists(token_file):
        return render(
            request,
            "portal/reviewer_activate.html",
            {"token": token, "error": "Odkaz je neplatný nebo již byl použit."},
        )

    payload = json.loads(open(token_file).read())
    if payload.get("used") or payload.get("expires_at", 0) < time.time():
        return render(
            request,
            "portal/reviewer_activate.html",
            {"token": token, "error": "Odkaz vypršel nebo byl již použit."},
        )

    return render(
        request, "portal/reviewer_activate.html", {"token": token, "error": None}
    )


def budget_week(request):
    """Static mockup of the weekly budget sheet (Jan's proposal).

    Pivot grid computed from entries — single source of truth. Entries are
    one-expense-per-row; the pivot rolls them up by (worker × category).
    Real persistence requires a separate plan.
    """
    import datetime
    from collections import defaultdict

    today = datetime.date.today()
    iso = today.isocalendar()
    week_start = today - datetime.timedelta(days=iso.weekday - 1)
    week_end = week_start + datetime.timedelta(days=6)
    week = {"iso_week": iso[1], "year": iso[0], "start": week_start, "end": week_end}

    categories = [
        {"key": "ubyt", "label": "Ubytování"},
        {"key": "zal", "label": "Zálohy"},
        {"key": "naf", "label": "Nafta"},
        {"key": "pok", "label": "Pokuty"},
        {"key": "jid", "label": "Jídlo"},
        {"key": "myt", "label": "Mýto"},
        {"key": "mzd", "label": "Mzda"},
        {"key": "opv", "label": "Opravy"},
        {"key": "ost", "label": "Ostatní"},
    ]
    cat_keys = [c["key"] for c in categories]
    cat_label = {c["key"]: c["label"] for c in categories}

    sample_workers = _SYNTHETIC_WORKERS

    raw = [
        ("Novák Jan", today, "ubyt", 85, "Ubytování Mnichov"),
        ("Novák Jan", today, "zal", 200, "Záloha na cestu"),
        ("Novák Jan", today, "naf", 120, "Tankování Hannover"),
        ("Novák Jan", today + datetime.timedelta(1), "ubyt", 85, ""),
        ("Novák Jan", today + datetime.timedelta(1), "naf", 95.4, "Diesel DE"),
        ("Novák Jan", today + datetime.timedelta(2), "jid", 35, "Oběd"),
        ("Dvořák Pavel", today, "ubyt", 85, ""),
        ("Dvořák Pavel", today, "zal", 150, ""),
        ("Dvořák Pavel", today, "pok", 120, "Překročení rychlosti"),
        ("Dvořák Pavel", today, "jid", 30, ""),
        ("Dvořák Pavel", today, "myt", 12.5, "Mýto A9"),
        ("Dvořák Pavel", today + datetime.timedelta(3), "mzd", 1250, "Týdenní výplata"),
        ("Svoboda Tomáš", today, "ubyt", 85, ""),
        ("Svoboda Tomáš", today, "zal", 100, ""),
        ("Svoboda Tomáš", today, "naf", 110, ""),
        (
            "Svoboda Tomáš",
            today + datetime.timedelta(2),
            "opv",
            85,
            "Servis brzdy Augsburg",
        ),
    ]

    pivot = defaultdict(lambda: {k: 0.0 for k in cat_keys})
    entries_for_js = []
    for name, d, cat, amt, note in raw:
        pivot[name][cat] += amt
        entries_for_js.append(
            {
                "worker_name": name,
                "category": cat,
                "category_label": cat_label[cat],
                "amount": amt,
                "date_iso": d.isoformat(),
                "date_label": d.strftime("%-d.%-m."),
                "note": note,
            }
        )

    def fmt(n):
        return f"{n:,.2f}".replace(",", " ").replace(".", ",")

    pivot_rows = []
    for w in sample_workers:
        name = f"{w.family_name} {w.given_name}"
        cells = pivot.get(name, {k: 0.0 for k in cat_keys})
        total = sum(cells.values())
        pivot_rows.append(
            {
                "worker_name": name,
                "cells": {k: (fmt(v) if v else "") for k, v in cells.items()},
                "total": fmt(total),
                "_cells_num": cells,
            }
        )

    col_totals_num = {k: 0.0 for k in cat_keys}
    for row in pivot_rows:
        for k in cat_keys:
            col_totals_num[k] += row["_cells_num"][k]
    grand = sum(col_totals_num.values())
    col_totals = {k: fmt(v) for k, v in col_totals_num.items()}
    col_totals["grand"] = fmt(grand)

    pivot_for_js = [
        {
            "worker_name": r["worker_name"],
            "cells": r["_cells_num"],
            "total": sum(r["_cells_num"].values()),
        }
        for r in pivot_rows
    ]

    expenses_no_wages = sum(v for k, v in col_totals_num.items() if k != "mzd")

    ctx = {
        "week": week,
        "today": today,
        "workers": sample_workers,
        "categories": categories,
        "pivot_rows": pivot_rows,
        "col_totals": col_totals,
        "entries_for_js": entries_for_js,
        "pivot_for_js": pivot_for_js,
        "totals": {
            "expenses": fmt(expenses_no_wages),
            "advances": fmt(col_totals_num["zal"]),
            "wages": fmt(col_totals_num["mzd"]),
            "fines": fmt(col_totals_num["pok"]),
            "fuel": fmt(col_totals_num["naf"]),
            "grand": fmt(grand),
        },
        "week_notes": "",
    }
    return render(request, "portal/budget_week.html", ctx)


PLANNED_MODULES = {
    "partners": {
        "title": "Partneři",
        "description": "Správa německých partnerů a jejich kontaktních údajů.",
        "target_release": "M2B",
        "dependencies": ["M1A infrastructure gates", "ADR-001 Plan AE approval"],
    },
    "jobs": {
        "title": "Zakázky / pracovní nabídky",
        "description": "Evidence zakázek a pracovních nabídek v Německu.",
        "target_release": "M2B",
        "dependencies": ["M1A infrastructure gates"],
    },
    "candidates": {
        "title": "Kandidáti",
        "description": "Kandidáti na pracovní pozice.",
        "target_release": "M2B",
        "dependencies": ["M1A infrastructure gates"],
    },
    "requests": {
        "title": "Žádosti a rezervace",
        "description": "Žádosti zaměstnanců a rezervace.",
        "target_release": "M3",
        "dependencies": ["M2B completion"],
    },
    "capacity": {
        "title": "Kapacity a plánování",
        "description": "Plánování kapacit a směn.",
        "target_release": "M3",
        "dependencies": ["M2B completion"],
    },
    "attendance": {
        "title": "Docházka a pracovní čas",
        "description": "Evidence docházky a pracovního času.",
        "target_release": "M3",
        "dependencies": ["M2B completion"],
    },
    "communications": {
        "title": "Komunikace a oznámení",
        "description": "Interní komunikace a oznámení.",
        "target_release": "M3",
        "dependencies": ["M2B completion"],
    },
    "finance": {
        "title": "Provozní finance",
        "description": "Týdenní rozpočty a finanční přehledy.",
        "target_release": "M4",
        "dependencies": ["M3 completion", "Finance plan approval"],
    },
    "invoices": {
        "title": "Přijaté doklady / faktury",
        "description": "Příjem a evidence faktur.",
        "target_release": "M4",
        "dependencies": ["M3 completion"],
    },
    "payroll-cz": {
        "title": "Czech payroll",
        "description": "Mzdové podklady pro CZ.",
        "target_release": "M5",
        "dependencies": ["M4 completion", "Payroll specialist gates"],
    },
    "payroll-de": {
        "title": "German payroll",
        "description": "Mzdové podklady pro DE.",
        "target_release": "M5",
        "dependencies": ["M4 completion", "Payroll specialist gates"],
    },
    "integrations": {
        "title": "Integrace",
        "description": "Integrace s externími systémy.",
        "target_release": "M5",
        "dependencies": ["M4 completion", "Security review"],
    },
    "privacy": {
        "title": "Privacy requests",
        "description": "Žádosti o výmaz, export a další privacy operace.",
        "target_release": "M2B",
        "dependencies": ["GDPR compliance review"],
    },
    "admin": {
        "title": "System administration",
        "description": "Správa systému, uživatelů a rolí.",
        "target_release": "M1A",
        "dependencies": ["Infrastructure gates"],
    },
}


def planned_page(request):
    """Planned landing page for future modules - shows purpose, target release,
    dependencies and inactive status message."""
    module_key = request.resolver_match.url_name.replace("planned_", "")
    module = PLANNED_MODULES.get(
        module_key,
        {
            "title": "Modul",
            "description": "Funkce zatím není aktivní.",
            "target_release": "Plánováno",
            "dependencies": [],
        },
    )
    ctx = {
        "module": module,
        "module_key": module_key,
    }
    return render(request, "portal/planned_page.html", ctx)


OCR_TO_CANONICAL = {
    "surname": "family_name",
    "dob": "birth_date",
}


def _canonical_field(ocr_field):
    """Map OCR field name to canonical Worker field name, or return same if not mapped."""
    return OCR_TO_CANONICAL.get(ocr_field, ocr_field)


WORKER_COMPLETION_REQUIRED_FIELDS = [
    "given_name",
    "family_name",
    "birth_date",
    "activity_profile",
    "state",
]

WORKER_A1_REQUIRED_FIELDS = [
    "surname",
    "given_name",
    "dob",
    "birth_place",
    "nationality",
    "sex",
    "insurance_number",
    "street",
    "house_number",
    "city",
    "postal_code",
    "country_code",
]


def worker_completion_score(worker):
    """Calculate worker completeness score based on required fields.

    Returns dict with:
        - required_present: list of required fields that are filled
        - required_missing: list of required fields that are missing
        - completeness_pct: percentage of required fields filled
    """
    required = set(WORKER_COMPLETION_REQUIRED_FIELDS)
    present = set()
    for field in required:
        value = getattr(worker, field, None)
        if value and str(value).strip():
            present.add(field)

    missing = required - present
    pct = (len(present) / len(required)) * 100 if required else 100

    return {
        "required_present": list(present),
        "required_missing": list(missing),
        "completeness_pct": round(pct, 1),
    }


def worker_a1_readiness(worker, organization):
    """Check if worker has all fields required for A1 readiness.

    Checks both Worker model fields and confirmed FieldProposals.
    Returns dict with:
        - ready: bool
        - missing_fields: list of missing A1-critical fields
        - has_assignment: bool
        - has_confirmed_identity: bool
    """

    from .models import WorkerIdentityRevision

    revision = (
        WorkerIdentityRevision.objects.filter(organization=organization, worker=worker)
        .order_by("-revision_number")
        .first()
    )
    confirmed_fields = set(revision.confirmed_fields) if revision else set()
    confirmed_fields |= {
        key
        for key, canonical in OCR_TO_CANONICAL.items()
        if canonical in confirmed_fields
    }

    missing = []
    for field in WORKER_A1_REQUIRED_FIELDS:
        if field not in confirmed_fields:
            canonical = _canonical_field(field)
            worker_value = getattr(worker, canonical, None)
            if not worker_value or (
                isinstance(worker_value, str) and not worker_value.strip()
            ):
                missing.append(field)

    has_assignment = Assignment.objects.filter(
        organization=organization, worker=worker
    ).exists()
    has_confirmed_doc = bool(
        revision
        and all(
            revision.confirmed_fields.get(k)
            for k in ("family_name", "given_name", "birth_date")
        )
    )

    return {
        "ready": len(missing) == 0 and has_assignment and has_confirmed_doc,
        "missing_fields": missing,
        "has_assignment": has_assignment,
        "has_confirmed_identity": has_confirmed_doc,
    }


@require_org_membership
def ocr_review_queue(request):
    """Queue of documents with OCR proposals pending human review."""
    from .models import DocumentClassification

    pending_proposals = (
        FieldProposal.objects.filter(
            organization=request.organization,
            state__in=[FieldProposal.State.PROPOSED, FieldProposal.State.CONFLICT],
        )
        .select_related("document", "document__worker")
        .order_by("-id")[:50]
    )

    classified_docs = (
        DocumentClassification.objects.filter(
            organization=request.organization, is_human_confirmed=False
        )
        .select_related("document", "document__worker")
        .order_by("-id")[:50]
    )

    ctx = {
        "pending_proposals": pending_proposals,
        "classified_docs": classified_docs,
    }
    if request.headers.get("HX-Request"):
        return render(request, "portal/partials/ocr_review_queue.html", ctx)
    return render(request, "portal/ocr_review_queue.html", ctx)


@require_org_membership
def ocr_field_review(request, document_pk):
    from .intake_views import detail

    return detail(request, document_pk)


@require_org_membership
def document_supersede(request, pk):
    """Create a new version of an existing document."""
    document = get_object_or_404(Document, pk=pk, organization=request.organization)

    from .document_intake import authorize, supersede
    from .services import Forbidden, MAX_UPLOAD_BYTES

    try:
        authorize(request.user, request.organization, "document:supersede")
    except Forbidden:
        return HttpResponse(status=403)
    if request.method == "POST":
        new_file = request.FILES.get("new_file")
        if not new_file:
            return JsonResponse({"error": "Chybí soubor."}, status=400)
        if new_file.size > MAX_UPLOAD_BYTES:
            return JsonResponse({"error": "Soubor je příliš velký."}, status=400)
        try:
            supersede(
                request.user,
                request.organization,
                document.pk,
                new_file.name,
                new_file.content_type,
                new_file.read(MAX_UPLOAD_BYTES + 1),
                _sync=False,
            )
        except Forbidden:
            return HttpResponse(status=403)
        except (ValueError, OSError):
            return JsonResponse(
                {
                    "error": "Dokument se nepodařilo uložit. Zkontrolujte soubor a opakujte akci."
                },
                status=400,
            )
        return redirect("document_detail", pk=document.pk)

    ctx = {"document": document}
    return render(request, "portal/document_supersede.html", ctx)


@require_org_membership
def assignment_conflicts(request):
    """Assignment overlap conflicts requiring resolution.

    Fetches all assignments once, then detects overlapping pairs in Python
    to avoid N+1 query pattern. Each unordered pair is reported once.
    """
    assignments = list(
        Assignment.objects.filter(organization=request.organization)
        .select_related("worker")
        .order_by("pk")
    )

    seen_pairs = set()
    conflicts = []
    for i, a in enumerate(assignments):
        for b in assignments[i + 1 :]:
            if a.worker_id != b.worker_id:
                continue
            if a.start <= b.end and a.end >= b.start:
                pair_key = (min(a.pk, b.pk), max(a.pk, b.pk))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    first = a if a.pk < b.pk else b
                    second = b if a.pk < b.pk else a
                    conflicts.append({"assignment": first, "overlaps": [second]})

    ctx = {"conflicts": conflicts}
    return render(request, "portal/assignment_conflicts.html", ctx)


@require_org_membership
def worker_archive(request, pk):
    """Archive a worker - soft delete that preserves audit trail."""
    from .services import require_capability, Forbidden

    try:
        require_capability(request.user, request.organization, "worker:archive")
    except Forbidden:
        return HttpResponse(status=403)
    worker = get_object_or_404(Worker, pk=pk, organization=request.organization)

    if request.method == "POST":
        worker.state = Worker.State.ARCHIVED
        worker.save()

        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="worker.archived",
            object_ref=f"worker:{worker.pk}",
            outcome="success",
        )

        StatusEvent.objects.create(
            organization=request.organization,
            event_type=StatusEvent.EventType.WORKER_ARCHIVED,
            actor_ref=f"user:{request.user.pk}",
            object_ref=f"worker:{worker.pk}",
            outcome="success",
        )

        return redirect("worker_list")

    return render(request, "portal/worker_archive.html", {"worker": worker})


_SYNTHETIC_WORKERS = [
    type("_W", (), {"pk": 1, "family_name": "Novák", "given_name": "Jan"})(),
    type("_W", (), {"pk": 2, "family_name": "Dvořák", "given_name": "Pavel"})(),
    type("_W", (), {"pk": 3, "family_name": "Svoboda", "given_name": "Tomáš"})(),
]


@never_cache
@require_safe
@require_org_membership
def a1_artifact_download(request, pk, page=None):
    """Protected review copy; never an issuance or final-promotion endpoint."""
    from django.conf import settings
    from django.http import HttpResponse, Http404
    from .services import require_capability, current_artifact_dependencies, Forbidden
    from .j4_artifacts import verify_artifact, ArtifactError, _hash

    try:
        require_capability(request.user, request.organization, "a1:prepare")
    except Forbidden:
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.artifact_read",
            object_ref=f"a1:{pk}",
            outcome="denied",
        )
        return HttpResponseForbidden("ACCESS_DENIED")
    case = A1Case.objects.filter(pk=pk, organization=request.organization).first()
    if case is None:
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.artifact_read",
            object_ref=f"a1:{pk}",
            outcome="denied",
        )
        raise Http404()
    if page is not None and page not in (1, 2, 3):
        raise Http404()
    if hasattr(case, "draft_reservation"):
        from django.core.exceptions import ObjectDoesNotExist
        from .a1_generation_access import read_generation
        from .services import StaleWrite

        generation_id = None
        if "generation" in request.GET:
            raw = request.GET.getlist("generation")
            if (
                len(raw) != 1
                or not raw[0].isascii()
                or not raw[0].isdigit()
                or len(raw[0]) > 19
                or int(raw[0]) < 1
                or int(raw[0]) > 9223372036854775807
            ):
                return JsonResponse({"error": "INVALID_GENERATION"}, status=400)
            generation_id = int(raw[0])
        try:
            generation, data = read_generation(
                request.user,
                request.organization,
                case.pk,
                generation_id=generation_id,
                page=page,
            )
        except (
            Forbidden,
            ObjectDoesNotExist,
            StaleWrite,
            ValueError,
            OSError,
            ArtifactError,
        ) as exc:
            AuditEvent.objects.create(
                organization=request.organization,
                actor_ref=f"user:{request.user.pk}",
                event_type="a1.artifact_read",
                object_ref=f"a1:{case.pk}",
                outcome="denied",
            )
            if isinstance(exc, Forbidden):
                return HttpResponseForbidden("ACCESS_DENIED")
            if isinstance(exc, ObjectDoesNotExist):
                raise Http404() from None
            return JsonResponse({"error": "ARTIFACT_UNAVAILABLE_OR_STALE"}, status=409)
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.artifact_read",
            object_ref=f"a1:{case.pk}",
            outcome="success",
        )
        name = f"page-{page}.png" if page else "artifact.pdf"
        response = HttpResponse(
            data, content_type="image/png" if page else "application/pdf"
        )
        response["Content-Disposition"] = (
            f'{"inline" if page else "attachment"}; filename="review-{name}"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
    if not case.artifact_reference or (page is not None and page not in (1, 2, 3)):
        raise Http404()
    dependencies = current_artifact_dependencies(case)
    root = Path(settings.DOCUMENT_STORAGE_ROOT) / "j4"
    try:
        verified = verify_artifact(root, case.artifact_reference, dependencies)
        if case.is_stale or verified["stale"]:
            raise ArtifactError("ARTIFACT_STALE")
        name = f"page-{page}.png" if page else "artifact.pdf"
        data = (root / case.artifact_reference["key"] / name).read_bytes()
        if page is None and _hash(data) != case.prepared_artifact_hash:
            raise ArtifactError("ARTIFACT_CHANGED")
    except (ArtifactError, OSError):
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.artifact_read",
            object_ref=f"a1:{case.pk}",
            outcome="denied",
        )
        return JsonResponse({"error": "ARTIFACT_UNAVAILABLE_OR_STALE"}, status=409)
    AuditEvent.objects.create(
        organization=request.organization,
        actor_ref=f"user:{request.user.pk}",
        event_type="a1.artifact_read",
        object_ref=f"a1:{case.pk}",
        outcome="success",
    )
    response = HttpResponse(
        data, content_type="image/png" if page else "application/pdf"
    )
    response["Content-Disposition"] = (
        f'{"inline" if page else "attachment"}; filename="review-{name}"'
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


# =============================================================================
# J4 Visual Confirmation & Evidence Intake
# =============================================================================


def _a1_generation_confirm(request, case):
    from django.core.exceptions import ObjectDoesNotExist
    from .a1_generation_confirmation import confirmation_context, confirm_generation
    from .j4_artifacts import ArtifactError
    from .services import Forbidden, StaleWrite

    class InvalidConfirmation(ValueError):
        pass

    def denied(status, code):
        AuditEvent.objects.create(
            organization=request.organization,
            actor_ref=f"user:{request.user.pk}",
            event_type="a1.generation_visual_confirmed",
            object_ref=f"a1:{case.pk}",
            outcome="denied",
        )
        return JsonResponse({"error": code}, status=status)

    try:
        values = request.POST if request.method == "POST" else request.GET
        key = "generation_id" if request.method == "POST" else "generation"
        raw = values.getlist(key)
        generation_id = None
        if raw:
            if (
                len(raw) != 1
                or not raw[0].isascii()
                or not raw[0].isdigit()
                or len(raw[0]) > 19
                or not 1 <= int(raw[0]) <= 9223372036854775807
            ):
                raise InvalidConfirmation("INVALID_GENERATION")
            generation_id = int(raw[0])
        if request.method == "POST":
            if generation_id is None:
                raise InvalidConfirmation("GENERATION_REQUIRED")
            tokens = {}
            for field in ("source_hash", "fingerprint", "receipt_sha256", "pdf_sha256"):
                entries = values.getlist("expected_" + field)
                if (
                    len(entries) != 1
                    or len(entries[0]) != 64
                    or any(c not in "0123456789abcdef" for c in entries[0])
                ):
                    raise InvalidConfirmation("INVALID_CONFIRMATION_TOKEN")
                tokens["expected_" + field] = entries[0]
            if any(values.getlist(f"check_{page}") != ["on"] for page in (1, 2, 3)):
                raise InvalidConfirmation("ALL_PAGES_REQUIRED")
            confirm_generation(
                request.user,
                request.organization,
                case.pk,
                generation_id=generation_id,
                pages=[1, 2, 3],
                **tokens,
            )
            return redirect("a1_case_detail", pk=case.pk)
        generation, expected = confirmation_context(
            request.user, request.organization, case.pk, generation_id=generation_id
        )
        return render(
            request,
            "portal/a1_generation_confirm.html",
            {
                "case": case,
                "generation": generation,
                "expected": expected,
                "pages": [1, 2, 3],
            },
        )
    except Forbidden:
        return denied(403, "ACCESS_DENIED")
    except ObjectDoesNotExist:
        return denied(404, "GENERATION_NOT_FOUND")
    except InvalidConfirmation:
        return denied(400, "INVALID_CONFIRMATION_INPUT")
    except (StaleWrite, ArtifactError, ValueError, OSError):
        return denied(409, "ARTIFACT_UNAVAILABLE_OR_STALE")


@never_cache
@require_http_methods(["GET", "POST"])
@require_org_membership
def a1_artifact_confirm(request, pk):
    """Visual confirmation of A1 artifact by operator.

    Operator reviews all pages of the generated A1 PDF and confirms
    that the visual content matches the expected certificate.
    This creates an immutable confirmation receipt.
    """
    case = get_object_or_404(A1Case, pk=pk, organization=request.organization)

    if hasattr(case, "draft_reservation"):
        return _a1_generation_confirm(request, case)

    if not case.artifact_reference:
        return JsonResponse({"error": "No artifact attached to this case"}, status=400)

    if case.external_status in ("issued", "submitted"):
        return JsonResponse(
            {"error": "Cannot confirm already issued/submitted A1"}, status=400
        )

    from django.conf import settings
    from .services import require_capability, current_artifact_dependencies
    from .j4_artifacts import (
        verify_artifact,
        ArtifactError,
        _hash,
        _root,
        _write,
        _json,
    )

    require_capability(request.user, request.organization, "document:confirm")

    try:
        dependencies = current_artifact_dependencies(case)
        root = Path(settings.DOCUMENT_STORAGE_ROOT) / "j4"
        verified = verify_artifact(root, case.artifact_reference, dependencies)

        if case.is_stale or verified.get("stale"):
            return JsonResponse(
                {"error": "Artifact is stale, source has changed"}, status=409
            )
    except (ArtifactError, OSError):
        return JsonResponse({"error": "Artifact verification failed"}, status=409)

    if request.method == "POST":
        action = request.POST.get("action")
        notes = request.POST.get("notes", "").strip()

        if action == "confirm":
            # Server-side validation of required confirmation checkboxes
            if not all(request.POST.get(f"check_{i}") for i in (1, 2, 3)):
                return JsonResponse(
                    {"error": "All three confirmation checkboxes must be ticked"},
                    status=400,
                )

            # Build receipt and persist atomically with case update + audit
            with transaction.atomic():
                case = A1Case.objects.select_for_update().get(pk=case.pk)

                receipt_data = {
                    "schema": 2,
                    "case_id": case.pk,
                    "case_source_hash": case.source_hash,
                    "artifact_key": case.artifact_reference["key"],
                    "pdf_sha256": case.prepared_artifact_hash,
                    "confirmed_by": f"user:{request.user.pk}",
                    "confirmed_at": timezone.now().isoformat(),
                    "git_commit": _current_git_commit(),
                    "build_id": _current_build_id(),
                    "notes": notes,
                    "visual_confirmation": True,
                }

                confirmation_dir = (
                    _root(Path(settings.DOCUMENT_STORAGE_ROOT) / "j4")
                    / "confirmations"
                    / uuid.uuid4().hex
                )
                confirmation_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                _write(confirmation_dir / "confirmation.json", _json(receipt_data))
                _write(
                    confirmation_dir / "receipt.json",
                    _json({"confirmation_sha256": _hash(_json(receipt_data))}),
                )

                case.visual_confirmed = True
                case.visual_confirmed_at = timezone.now()
                case.visual_confirmed_by = request.user
                case.visual_confirmation_notes = notes
                case.visual_confirmation_receipt = str(confirmation_dir)
                case.save(
                    update_fields=[
                        "visual_confirmed",
                        "visual_confirmed_at",
                        "visual_confirmed_by",
                        "visual_confirmation_notes",
                        "visual_confirmation_receipt",
                    ]
                )

                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.visual_confirmed",
                    object_ref=f"a1:{case.pk}",
                    outcome="success",
                )

            if request.headers.get("HX-Request"):
                return render(
                    request, "portal/partials/a1_case_row.html", {"case": case}
                )
            return redirect("a1_case_detail", pk=case.pk)

        elif action == "reject":
            with transaction.atomic():
                case = A1Case.objects.select_for_update().get(pk=case.pk)
                case.visual_confirmed = False
                case.visual_confirmed_at = timezone.now()
                case.visual_confirmed_by = request.user
                case.visual_confirmation_notes = f"REJECTED: {notes}"
                case.save(
                    update_fields=[
                        "visual_confirmed",
                        "visual_confirmed_at",
                        "visual_confirmed_by",
                        "visual_confirmation_notes",
                    ]
                )

                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.visual_rejected",
                    object_ref=f"a1:{case.pk}",
                    outcome="rejected",
                )

            if request.headers.get("HX-Request"):
                return render(
                    request, "portal/partials/a1_case_row.html", {"case": case}
                )
            return redirect("a1_case_detail", pk=case.pk)

        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    # GET: show confirmation page
    return render(
        request,
        "portal/a1_artifact_confirm.html",
        {
            "case": case,
            "pages": [1, 2, 3],
        },
    )


@require_org_membership
def a1_evidence_intake(request, pk):
    """Operator evidence intake for A1 case.

    Allows operators to upload supporting evidence documents
    and record notes for the A1 case.
    """
    case = get_object_or_404(A1Case, pk=pk, organization=request.organization)

    from django import forms
    from .services import require_capability

    class EvidenceForm(forms.Form):
        document = forms.FileField(required=False)
        note = forms.CharField(widget=forms.Textarea, required=False)
        evidence_type = forms.ChoiceField(
            choices=[
                ("supporting", "Supporting document"),
                ("correction", "Correction"),
                ("institution_verification", "Institution verification"),
                ("other", "Other"),
            ],
            required=True,
        )

    if request.method == "POST":
        form = EvidenceForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.cleaned_data.get("document")
            note = form.cleaned_data.get("note", "").strip()
            evidence_type = form.cleaned_data.get("evidence_type")

            # Document upload requires explicit capability; note-only does not.
            if document:
                require_capability(
                    request.user, request.organization, "document:upload"
                )

            with transaction.atomic():
                case = A1Case.objects.select_for_update().get(pk=case.pk)

                if document:
                    from .document_intake import intake

                    doc, version, classifications, run = intake(
                        user=request.user,
                        organization=request.organization,
                        worker=case.worker,
                        filename=document.name,
                        content_type=document.content_type,
                        content=document.read(),
                        _sync=False,
                    )

                    case.evidence_documents = list(case.evidence_documents or [])
                    case.evidence_documents.append(
                        {
                            "document_id": doc.id,
                            "evidence_type": evidence_type,
                            "note": note,
                            "uploaded_by": request.user.pk,
                            "uploaded_at": timezone.now().isoformat(),
                        }
                    )
                    case.save(update_fields=["evidence_documents"])

                if note:
                    case.evidence_notes = list(case.evidence_notes or [])
                    case.evidence_notes.append(
                        {
                            "note": note,
                            "evidence_type": evidence_type,
                            "added_by": request.user.pk,
                            "added_at": timezone.now().isoformat(),
                        }
                    )
                    case.save(update_fields=["evidence_notes"])

                AuditEvent.objects.create(
                    organization=request.organization,
                    actor_ref=f"user:{request.user.pk}",
                    event_type="a1.evidence_added",
                    object_ref=f"a1:{case.pk}",
                    outcome="success",
                )

            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "portal/partials/a1_evidence_list.html",
                    {"case": case},
                )
            return redirect("a1_evidence_intake", pk=case.pk)

    else:
        form = EvidenceForm()

    return render(
        request, "portal/a1_evidence_intake.html", {"case": case, "form": form}
    )
