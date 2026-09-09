"""Read the applicable unverified generation without creating or approving drafts."""
import copy
import hashlib
import json
import os
import stat
from pathlib import Path

import pymupdf
from django.conf import settings
from django.db import transaction
from src.document_core.serialization import result_hash
from .a1_drafts import _current, _dependencies, _profile, _verify_generation, _verify_reservation
from .identity import _authorize, _lock_organization
from .j4_artifacts import ArtifactError, _root, verify_artifact
from .models import A1Case, A1DraftReservation, A1DraftGeneration
from .services import StaleWrite


def _select(user, organization, case_id, generation_id=None):
    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    case = A1Case.objects.select_for_update().get(pk=case_id, organization=organization,
                                                worker__organization=organization)
    if case.is_stale:
        raise StaleWrite("A1_DRAFT_SOURCE_CHANGED")
    reservation = A1DraftReservation.objects.get(case=case, organization=organization)
    _verify_reservation(reservation)
    source = _current(user, organization, case)
    profile, path, profile_hash = _profile(source["row"])
    dependencies = _dependencies(case, path)
    if source != reservation.snapshot.get("input") or dependencies["files"]["institution_profile"] != profile_hash:
        raise StaleWrite("A1_DRAFT_SOURCE_OR_PROFILE_CHANGED")
    snapshot = copy.deepcopy(reservation.snapshot)
    snapshot["profile"] = profile
    fingerprint = result_hash({"snapshot": snapshot, "dependencies": dependencies})
    candidates = A1DraftGeneration.objects.filter(organization=organization, reservation=reservation)
    if generation_id is not None:
        generation = candidates.get(pk=generation_id)
        if generation.fingerprint != fingerprint:
            raise StaleWrite("A1_DRAFT_GENERATION_STALE")
    else:
        generation = candidates.filter(fingerprint=fingerprint).first()
        if generation is None:
            raise StaleWrite("A1_DRAFT_GENERATION_REQUIRED")
    _verify_generation(generation)
    expected = dict(dependencies, reservation_sha256=generation.snapshot_sha256)
    reference = generation.artifact_reference
    if (not reference or reference.get("key") != generation.package_key.hex or
            generation.artifact_dependencies != expected or
            generation.prepared_artifact_hash != reference.get("pdf_sha256")):
        raise StaleWrite("A1_DRAFT_ARTIFACT_UNAVAILABLE")
    return generation, case, path, dependencies, expected


@transaction.atomic
def current_generation(user, organization, case_id):
    """Select by current fingerprint, not highest revision; never reserve on GET."""
    generation, _, _, _, expected = _select(user, organization, case_id)
    if verify_artifact(_root(Path(settings.DOCUMENT_STORAGE_ROOT) / "j4"),
                       generation.artifact_reference, expected)["stale"]:
        raise StaleWrite("A1_DRAFT_ARTIFACT_STALE")
    return generation


def _bytes(directory_fd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ArtifactError("ARTIFACT_FILE_REQUIRED")
        return stream.read()


@transaction.atomic
def read_generation(user, organization, case_id, generation_id=None, page=None):
    """Verify the exact returned bytes and current inputs under organization locks."""
    if page is not None and page not in (1, 2, 3):
        raise ValueError("A1_DRAFT_PAGE_INVALID")
    generation, case, path, dependencies, expected = _select(user, organization, case_id, generation_id)
    root = _root(Path(settings.DOCUMENT_STORAGE_ROOT) / "j4")
    reference = generation.artifact_reference
    if verify_artifact(root, reference, expected)["stale"]:
        raise StaleWrite("A1_DRAFT_ARTIFACT_STALE")
    fd = os.open(root / generation.package_key.hex, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        receipt_bytes = _bytes(fd, "receipt.json")
        if hashlib.sha256(receipt_bytes).hexdigest() != reference["receipt_sha256"]:
            raise ArtifactError("ARTIFACT_RECEIPT_CHANGED")
        data = _bytes(fd, f"page-{page}.png" if page else "artifact.pdf")
    finally:
        os.close(fd)
    if page is None:
        if hashlib.sha256(data).hexdigest() != generation.prepared_artifact_hash:
            raise ArtifactError("ARTIFACT_PDF_CHANGED")
    else:
        receipt = json.loads(receipt_bytes)
        try:
            pixels = pymupdf.Pixmap(data)
            expected_page = receipt["pages"][page - 1]
            if (not data.startswith(b"\x89PNG\r\n\x1a\n") or
                    (pixels.width, pixels.height, pixels.n, pixels.alpha) !=
                    (expected_page["width"], expected_page["height"], 3, 0) or
                    hashlib.sha256(pixels.samples).hexdigest() != expected_page["pixel_sha256"]):
                raise ArtifactError("ARTIFACT_PREVIEW_CHANGED")
        except ArtifactError:
            raise
        except Exception:
            raise ArtifactError("ARTIFACT_PREVIEW_CHANGED") from None
    if _dependencies(case, path) != dependencies:
        raise StaleWrite("A1_DRAFT_DEPENDENCIES_CHANGED")
    return generation, data
