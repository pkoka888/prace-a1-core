"""Document intake presentation; all content access delegates to scoped services."""
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.db import transaction
from .models import Document, OcrRun, Worker, FieldProposal, DocumentRegionAssociation, IntakeSession
from .document_intake import (authorize, intake, read_result, execute_run, associate_region,
                              download_original, audit, read_session)
from .services import Forbidden, confirm_field_proposal
from .document_labels import FIELD_LABELS


def detail(request, pk):
    try:
        authorize(request.user, request.organization, "document:read")
    except Forbidden:
        return HttpResponse(status=403)
    document = get_object_or_404(Document, pk=pk, organization=request.organization)
    run = OcrRun.objects.filter(organization=request.organization, document=document).order_by("-pk").first()
    session = run.intake_sessions.filter(organization=request.organization).order_by("-pk").first() if run else None
    error = None
    if request.method == "POST":
        try:
            if request.POST.get("action") == "retry" and run:
                execute_run(request.user, request.organization, run.pk)
            elif request.POST.get("action") == "associate" and run:
                worker = get_object_or_404(Worker, organization=request.organization, pk=request.POST.get("worker_id"))
                allowed_runs = session.ocr_runs.filter(organization=request.organization) if session else OcrRun.objects.filter(pk=run.pk, organization=request.organization)
                target_run = get_object_or_404(allowed_runs, pk=request.POST.get("run_id", run.pk))
                associate_region(request.user, request.organization, target_run.pk, request.POST.get("region_id"), worker)
            else:
                selected = []
                proposals = FieldProposal.objects.filter(organization=request.organization)
                proposals = proposals.filter(ocr_run__in=session.ocr_runs.all()) if session else proposals.filter(ocr_run=run)
                for proposal in proposals:
                    if request.POST.get(f"confirm_{proposal.pk}") or request.POST.get(f"confirm_{proposal.field_name}_{proposal.pk}"):
                        selected.append(proposal)
                if not selected:
                    raise ValueError("NO_FIELDS_SELECTED")
                with transaction.atomic():
                    for proposal in selected:
                        confirm_field_proposal(request.user, request.organization, proposal,
                            corrected_value=request.POST.get(f"value_{proposal.field_name}_{proposal.pk}", proposal.proposed_value),
                            reason=request.POST.get("reason", ""))
            return redirect("document_detail", pk=document.pk)
        except Forbidden:
            return HttpResponse(status=403)
        except (ValueError, OcrRun.DoesNotExist):
            error = "Změnu nelze uložit. Zkontrolujte přiřazení pracovníka, vybraná pole a důvod opravy."
    payload = None
    if run and run.output_key:
        try:
            payload = read_result(request.user, request.organization, run.pk)
        except (ValueError, OSError):
            error = "Výsledek není dostupný nebo neprošel kontrolou integrity."
    regions = []
    if payload and payload.get("result"):
        analysis = read_session(request.user, request.organization, session) if session else payload["result"]
        for region in analysis["documents"]:
            region_run = region.get("ocr_run_id", run.pk)
            region["ocr_run_id"] = region_run
            region["proposals"] = FieldProposal.objects.filter(organization=request.organization, ocr_run_id=region_run,
                                                               document_region_id=region["document_id"]).exclude(fielddecision__decision="confirmed")
            for proposal in region["proposals"]:
                proposal.display_label = FIELD_LABELS.get(proposal.field_name, proposal.field_name)
            region["missing_labels"] = [FIELD_LABELS.get(f, f) for f in region["completeness"]["field_sufficiency"]["missing"]]
            candidate = region["association"].get("worker_id")
            region["suggested_worker"] = Worker.objects.filter(organization=request.organization, pk=candidate).first() if candidate else None
            region["association_record"] = DocumentRegionAssociation.objects.filter(organization=request.organization,
                ocr_run_id=region_run, region_id=region["document_id"]).select_related("worker").first()
            region["type_label"] = {"op": "Občanský průkaz", "zp": "Průkaz pojištěnce", "passport": "Cestovní pas"}.get(region["classification"]["type"], "Neurčený dokument")
            region["side_label"] = {"front": "přední strana", "back": "zadní strana"}.get(region["classification"]["side"], "")
            regions.append(region)
    return render(request, "portal/document_intake_detail.html", {"document": document, "ocr_run": run,
        "regions": regions, "error": error, "workers": Worker.objects.filter(organization=request.organization)})


def upload_unassigned(request, worker=None):
    from .forms import MultiDocumentUploadForm
    try:
        authorize(request.user, request.organization, "document:upload")
    except Forbidden:
        return HttpResponse(status=403)
    form = MultiDocumentUploadForm(request.POST or None, request.FILES or None,
                                   organization=request.organization, user=request.user)
    documents, errors = [], []
    if request.method == "POST" and form.is_valid():
        session = IntakeSession.objects.create(organization=request.organization, worker=worker, purpose=IntakeSession.Purpose.A1)
        for i in range(1, 5):
            file = form.cleaned_data.get(f"file{i}")
            if file:
                try:
                    doc, _, _, _ = intake(request.user, request.organization, worker, file.name, file.content_type, file.read(), session)
                    documents.append(doc)
                except Forbidden:
                    return HttpResponse(status=403)
                except (ValueError, OSError):
                    errors.append("Soubor neprošel kontrolou. Ostatní soubory byly zpracovány samostatně.")
        if len(documents) == 1 and not errors:
            return redirect("document_detail", pk=documents[0].pk)
    return render(request, "portal/document_intake_upload.html", {"form": form, "documents": documents, "errors": errors})


def original(request, pk):
    document = get_object_or_404(Document, pk=pk, organization=request.organization)
    try:
        data, mime = download_original(request.user, request.organization, document)
    except Forbidden:
        return HttpResponse(status=403)
    except (OSError, ValueError):
        return HttpResponse(status=404)
    response = HttpResponse(data, content_type=mime)
    response["Content-Disposition"] = 'attachment; filename="document"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def crop(request, run_id, region_id, variant):
    from .document_storage import document_storage
    from src.document_core.serialization import content_hash
    try:
        payload = read_result(request.user, request.organization, run_id)
        if not payload or payload["status"] != "completed" or variant not in ("original", "enhanced"):
            return HttpResponse(status=404)
        region = next((d for d in payload["result"]["documents"] if d["document_id"] == str(region_id)), None)
        if not region:
            return HttpResponse(status=404)
        digest = region[variant + "_crop_hash"]
        key = next((k for k in payload["artifact_keys"] if k.endswith("/"+digest+".png")), None)
        if not key:
            return HttpResponse(status=404)
        with document_storage().open(key, "rb") as stream:
            data = stream.read()
        if content_hash(data) != digest:
            return HttpResponse(status=404)
        audit(request.user, request.organization, "ocr.crop_read", f"ocr:{run_id}")
        response = HttpResponse(data, content_type="image/png")
        response["Cache-Control"] = "no-store"
        return response
    except Forbidden:
        return HttpResponse(status=403)
    except (OcrRun.DoesNotExist, OSError, ValueError):
        return HttpResponse(status=404)
