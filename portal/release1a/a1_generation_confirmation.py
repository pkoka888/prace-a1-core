"""Receipt-bound visual review, separate from identity facts and issuance."""
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .a1_generation_access import _select
from .a1_drafts import _dependencies
from .document_intake import audit
from .identity import _authorize
from .j4_artifacts import _root, verify_artifact
from .models import A1GenerationConfirmation
from .services import StaleWrite


def _context(user, organization, case_id, generation_id):
    _authorize(user, organization, "document:confirm")
    generation, case, path, dependencies, expected = _select(
        user, organization, case_id, generation_id)
    root = _root(Path(settings.DOCUMENT_STORAGE_ROOT) / "j4")
    if verify_artifact(root, generation.artifact_reference, expected)["stale"]:
        raise StaleWrite("A1_DRAFT_ARTIFACT_STALE")
    if _dependencies(case, path) != dependencies:
        raise StaleWrite("A1_DRAFT_DEPENDENCIES_CHANGED")
    tokens = {
        "source_hash": case.source_hash,
        "fingerprint": generation.fingerprint,
        "receipt_sha256": generation.artifact_reference["receipt_sha256"],
        "pdf_sha256": generation.prepared_artifact_hash,
    }
    return generation, tokens


@transaction.atomic
def confirmation_context(user, organization, case_id, generation_id=None):
    return _context(user, organization, case_id, generation_id)


@transaction.atomic
def confirm_generation(user, organization, case_id, *, generation_id,
                       expected_source_hash, expected_fingerprint,
                       expected_receipt_sha256, expected_pdf_sha256, pages):
    if (type(generation_id) is not int or generation_id < 1 or
            type(pages) is not list or any(type(page) is not int for page in pages) or
            pages != [1, 2, 3]):
        raise ValueError("A1_GENERATION_CONFIRMATION_INPUT_INVALID")
    generation, expected = _context(user, organization, case_id, generation_id)
    submitted = dict(source_hash=expected_source_hash, fingerprint=expected_fingerprint,
                     receipt_sha256=expected_receipt_sha256, pdf_sha256=expected_pdf_sha256)
    if submitted != expected:
        raise StaleWrite("A1_GENERATION_CONFIRMATION_STALE")
    existing = A1GenerationConfirmation.objects.filter(
        generation=generation, organization=organization).first()
    if existing:
        if any(getattr(existing, field) != value for field, value in expected.items()):
            raise StaleWrite("A1_GENERATION_CONFIRMATION_CORRUPT")
        return existing
    confirmation = A1GenerationConfirmation.objects.create(
        organization=organization, generation=generation, actor=user, **expected)
    # Keep package and dependency validation inside the write transaction, including
    # a final check after insertion so a changed package rolls the receipt back.
    _, latest = _context(user, organization, case_id, generation_id)
    if latest != expected:
        raise StaleWrite("A1_GENERATION_CONFIRMATION_STALE")
    audit(user, organization, "a1.generation_visual_confirmed", f"generation:{generation.pk}")
    return confirmation
