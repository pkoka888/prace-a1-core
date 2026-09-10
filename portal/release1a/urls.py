from django.urls import path
from .views import (
    dashboard as dashboard_view,
    health,
    readiness,
    synthetic_contract,
    attention_queue,
    # J1 — Worker
    worker_list,
    worker_create,
    worker_detail,
    worker_edit,
    worker_delete,
    worker_archive,
    # J2 — Document / OCR
    document_upload,
    document_intake_unassigned,
    document_crop,
    document_detail,
    document_download,
    document_list,
    document_supersede,
    # OCR Review
    ocr_review_queue,
    ocr_field_review,
    # J3 — Assignment
    assignment_create,
    assignment_edit,
    assignment_list,
    assignment_conflicts,
    # J4 — A1
    a1_prepare,
    a1_case_detail,
    a1_regenerate,
    a1_artifact_download,
    a1_artifact_confirm,
    a1_evidence_intake,
    a1_list,
    # Intake wizard
    intake_wizard,
    intake_upload,
    intake_paste,
    # Review surface
    review_dashboard,
    review_section_update,
    review_check_answers,
    review_approve,
    review_return,
    review_receipt,
    # Budget (Jan's proposal — static mockup)
    budget_week,
    # Planned future modules
    planned_page,
)

from .input_bundle_views import input_bundle_publish, input_bundle_download

urlpatterns = [
    path("a1/<int:pk>/inputs/", input_bundle_publish, name="input_bundle_publish"),
    path("a1/<int:pk>/inputs/<str:manifest_hash>/download/", input_bundle_download, name="input_bundle_download"),
    path("health/", health, name="health"),
    path("readiness/", readiness, name="readiness"),
    path("synthetic/", synthetic_contract, name="synthetic_contract"),
    path("", dashboard_view, name="dashboard"),
    path("attention/", attention_queue, name="attention_queue"),

    # J1 — Worker CRUD
    path("workers/", worker_list, name="worker_list"),
    path("workers/new/", worker_create, name="worker_create"),
    path("workers/new/intake/", intake_wizard, name="intake_wizard"),
    path("workers/<int:worker_pk>/intake/upload/", intake_upload, name="intake_upload"),
    path("workers/new/intake/paste/", intake_paste, name="intake_paste"),
    path("workers/<int:pk>/", worker_detail, name="worker_detail"),
    path("workers/<int:pk>/edit/", worker_edit, name="worker_edit"),
    path("workers/<int:pk>/delete/", worker_delete, name="worker_delete"),
    path("workers/<int:pk>/archive/", worker_archive, name="worker_archive"),

    # J2 — Document / OCR
    path("documents/intake/", document_intake_unassigned, name="document_intake_unassigned"),
    path("documents/ocr/<int:run_id>/<uuid:region_id>/<str:variant>/", document_crop, name="document_crop"),
    path("documents/", document_list, name="document_list"),
    path("workers/<int:worker_pk>/documents/upload/", document_upload, name="document_upload"),
    path("documents/<int:pk>/", document_detail, name="document_detail"),
    path("documents/<int:pk>/download/", document_download, name="document_download"),
    path("documents/<int:pk>/supersede/", document_supersede, name="document_supersede"),
    path("documents/<int:document_pk>/ocr-review/", ocr_field_review, name="ocr_field_review"),
    path("ocr-review/", ocr_review_queue, name="ocr_review_queue"),

    # J3 — Assignment
    path("assignments/", assignment_list, name="assignment_list"),
    path("assignments/conflicts/", assignment_conflicts, name="assignment_conflicts"),
    path("workers/<int:worker_pk>/assignments/new/", assignment_create, name="assignment_create"),
    path("workers/<int:worker_pk>/assignments/<int:pk>/edit/", assignment_edit, name="assignment_edit"),

    # J4 — A1
    path("a1/", a1_list, name="a1_list"),
    path("workers/<int:worker_pk>/a1/prepare/", a1_prepare, name="a1_prepare"),
    path("a1/<int:pk>/", a1_case_detail, name="a1_case_detail"),
    path("a1/<int:pk>/artifact/", a1_artifact_download, name="a1_artifact_download"),
    path("a1/<int:pk>/preview/<int:page>/", a1_artifact_download, name="a1_artifact_preview"),
    path("a1/<int:pk>/confirm/", a1_artifact_confirm, name="a1_artifact_confirm"),
    path("a1/<int:pk>/evidence/", a1_evidence_intake, name="a1_evidence_intake"),
    path("a1/<int:pk>/regenerate/", a1_regenerate, name="a1_regenerate"),

    # Planned future modules
    path("partners/", planned_page, name="planned_partners"),
    path("jobs/", planned_page, name="planned_jobs"),
    path("candidates/", planned_page, name="planned_candidates"),
    path("requests/", planned_page, name="planned_requests"),
    path("capacity/", planned_page, name="planned_capacity"),
    path("attendance/", planned_page, name="planned_attendance"),
    path("communications/", planned_page, name="planned_communications"),
    path("finance/", planned_page, name="planned_finance"),
    path("invoices/", planned_page, name="planned_invoices"),
    path("payroll-cz/", planned_page, name="planned_payroll_cz"),
    path("payroll-de/", planned_page, name="planned_payroll_de"),
    path("integrations/", planned_page, name="planned_integrations"),
    path("privacy/", planned_page, name="planned_privacy"),
    path("admin/", planned_page, name="planned_admin"),

    # Kontrola Release 1A
    path("review/", review_dashboard, name="review_dashboard"),
    path("review/section/<str:section>/update/", review_section_update, name="review_section_update"),
    path("review/check-answers/", review_check_answers, name="review_check_answers"),
    path("review/approve/", review_approve, name="review_approve"),
    path("review/return/", review_return, name="review_return"),
    path("review/receipt/", review_receipt, name="review_receipt"),

    # Budget — týdenní rozpočet (Jan)
    path("budget/week/", budget_week, name="budget_week"),
]
