from django.urls import path
from .views import (
    dashboard as dashboard_view,
    health,
    # J1 — Worker
    worker_list,
    worker_create,
    worker_detail,
    worker_edit,
    worker_delete,
    # J2 — Document / OCR
    document_upload,
    document_detail,
    document_download,
    # J3 — Assignment
    assignment_create,
    assignment_edit,
    # J4 — A1
    a1_prepare,
    a1_case_detail,
    a1_regenerate,
)

urlpatterns = [
    path("health/", health, name="health"),
    path("", dashboard_view, name="dashboard"),

    # J1 — Worker CRUD
    path("workers/", worker_list, name="worker_list"),
    path("workers/new/", worker_create, name="worker_create"),
    path("workers/<int:pk>/", worker_detail, name="worker_detail"),
    path("workers/<int:pk>/edit/", worker_edit, name="worker_edit"),
    path("workers/<int:pk>/delete/", worker_delete, name="worker_delete"),

    # J2 — Document / OCR
    path("workers/<int:worker_pk>/documents/upload/", document_upload, name="document_upload"),
    path("documents/<int:pk>/", document_detail, name="document_detail"),
    path("documents/<int:pk>/download/", document_download, name="document_download"),

    # J3 — Assignment
    path("workers/<int:worker_pk>/assignments/new/", assignment_create, name="assignment_create"),
    path("workers/<int:worker_pk>/assignments/<int:pk>/edit/", assignment_edit, name="assignment_edit"),

    # J4 — A1
    path("workers/<int:worker_pk>/a1/prepare/", a1_prepare, name="a1_prepare"),
    path("a1/<int:pk>/", a1_case_detail, name="a1_case_detail"),
    path("a1/<int:pk>/regenerate/", a1_regenerate, name="a1_regenerate"),
]