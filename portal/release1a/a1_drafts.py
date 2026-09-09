"""Synthetic unverified application drafts through the canonical A1 publisher."""
import hashlib
import importlib.metadata
import json
import random
import tempfile
import subprocess
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from scripts.a1_core import FONT_CANDIDATES, generate_provisional_document_id
from scripts.finalize_a1 import _slug, validate_profile, validate_application_draft_row
from scripts.generate_provisional_a1 import render_application_draft
from src.document_core.serialization import result_hash
from .a1_exports import export_input_case
from .document_intake import audit
from .identity import _authorize, _lock_organization
from .j4_artifacts import _root, publish_artifact, verify_artifact
from .models import A1Case, A1DraftReservation
from .services import StaleWrite


_CODE_FILES = ("scripts/a1_core.py", "scripts/finalize_a1.py", "scripts/generate_provisional_a1.py",
               "scripts/a1_quality_gate.py", "scripts/pdf_named_fields.py", "portal/release1a/a1_exports.py",
               "portal/release1a/a1_drafts.py", "portal/release1a/j4_artifacts.py")
_LOADED_CODE_HASHES = {name: hashlib.sha256((Path(settings.BASE_DIR) / name).read_bytes()).hexdigest()
                       for name in _CODE_FILES}


class DraftInputBlocked(ValueError):
    pass


def _profile(row):
    root = Path(getattr(settings, "A1_DRAFT_PROFILE_ROOT", settings.BASE_DIR / "config/institutions"))
    path = root / (_slug(row["institution_profile"]) + ".json")
    raw = path.read_bytes()
    profile = json.loads(raw)
    validate_profile(profile, row["institution_profile"], provisional=True)
    return profile, path, hashlib.sha256(raw).hexdigest()


def _dependencies(case, profile_path):
    root = Path(settings.BASE_DIR)
    files = ["templates/a1_background.pdf", "config/a1_layout.json", "config/address_enrichment.json",
             "scripts/a1_core.py", "scripts/finalize_a1.py", "scripts/generate_provisional_a1.py",
             "scripts/a1_quality_gate.py", "scripts/pdf_named_fields.py", "portal/release1a/a1_exports.py",
             "portal/release1a/a1_drafts.py", "portal/release1a/j4_artifacts.py"]
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
    if any(hashes[name] != digest for name, digest in _LOADED_CODE_HASHES.items()):
        raise StaleWrite("A1_DRAFT_PROCESS_RESTART_REQUIRED")
    hashes["institution_profile"] = hashlib.sha256(profile_path.read_bytes()).hexdigest()
    font = next((p for p in FONT_CANDIDATES if p.exists()), None)
    if font is None:
        raise DraftInputBlocked("A1_DRAFT_FONT_UNAVAILABLE")
    hashes["font"] = hashlib.sha256(font.read_bytes()).hexdigest()
    versions = {name: importlib.metadata.version(name) for name in ("pypdf", "reportlab", "pymupdf", "Pillow", "Django")}
    versions["ghostscript"] = subprocess.run(["gs", "--version"], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    manifest = getattr(settings, "PRACE_RELEASE_MANIFEST", {})
    return {"mode": "unverified_application_draft", "source_hash": case.source_hash,
            "files": hashes, "versions": versions,
            "build": {key: manifest.get(key, "") for key in ("app_build_id", "git_commit")} if isinstance(manifest, dict) else {}}


def _current(user, organization, case):
    exported = export_input_case(user, organization, case.pk)
    source = json.loads(exported["json"])
    if any(b.startswith("conflict:") or b in ("activity_profile_mismatch", "assignment_missing")
           for b in source["blockers"]):
        raise DraftInputBlocked("A1_DRAFT_SOURCE_CONFLICT_OR_ASSIGNMENT_MISSING")
    return source


def _verify_reservation(reservation):
    if (result_hash(reservation.snapshot) != reservation.snapshot_sha256 or
            reservation.snapshot["row"]["document_id"] != reservation.document_id):
        raise StaleWrite("A1_DRAFT_RESERVATION_CORRUPT")


@transaction.atomic
def reserve_application_draft(user, organization, case_id):
    """Commit the machine identifier before rendering; failed publication reuses it."""
    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    case = A1Case.objects.select_for_update().get(pk=case_id, organization=organization,
                                                worker__organization=organization)
    source = _current(user, organization, case)
    row = dict(source["row"])
    try:
        profile, profile_path, profile_hash = _profile(row)
        dependencies = _dependencies(case, profile_path)
        if dependencies["files"]["institution_profile"] != profile_hash:
            raise StaleWrite("A1_DRAFT_PROFILE_CHANGED")
        # Validate before allocating a scarce number. A temporary candidate is never persisted or rendered.
        checked = dict(row, document_id=row["document_id"] or "N00000S001/2000/DE")
        validate_application_draft_row(checked, profile)
    except (ValueError, OSError, KeyError):
        raise DraftInputBlocked("A1_DRAFT_INPUTS_INCOMPLETE_OR_INVALID") from None
    previous = A1DraftReservation.objects.filter(case=case, organization=organization).first()
    if previous:
        _verify_reservation(previous)
        if previous.dependencies != dependencies or previous.snapshot.get("input") != source:
            raise StaleWrite("A1_DRAFT_DEPENDENCIES_CHANGED")
        return previous
    reference_date = timezone.localdate()
    number_date = row["issue_date"] or reference_date.strftime("%d.%m.%Y")
    rng = random.Random(case.source_hash)
    for attempt in range(4096):
        number = row["document_id"] or generate_provisional_document_id(
            number_date, office_code=int(profile["institution"]["code"]), rng=rng)
        frozen_row = dict(row, document_id=number)
        snapshot = {"mode": "unverified_application_draft", "input": source, "row": frozen_row,
                    "profile": profile, "identity_verification": "pending", "visual_review": "pending",
                    "number_provenance": "input_unverified" if row["document_id"] else "machine_reservation",
                    "reference_date": reference_date.isoformat()}
        try:
            with transaction.atomic():
                reservation = A1DraftReservation.objects.create(organization=organization, case=case,
                    document_id=number, reference_date=reference_date, snapshot=snapshot, snapshot_sha256=result_hash(snapshot), dependencies=dependencies)
            audit(user, organization, "a1.draft_reserved", f"a1:{case.pk}")
            return reservation
        except IntegrityError:
            if row["document_id"]:
                raise DraftInputBlocked("A1_DRAFT_NUMBER_CONFLICT") from None
    raise DraftInputBlocked("A1_DRAFT_NUMBER_CAPACITY")


@transaction.atomic
def _publish_reserved(user, organization, reservation_id):
    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    reservation = A1DraftReservation.objects.select_for_update().get(pk=reservation_id,
        organization=organization, case__organization=organization, case__worker__organization=organization)
    _verify_reservation(reservation)
    case = A1Case.objects.select_for_update().get(pk=reservation.case_id)
    source = _current(user, organization, case)
    profile, profile_path, profile_hash = _profile(source["row"])
    dependencies = _dependencies(case, profile_path)
    if (reservation.snapshot.get("input") != source or reservation.dependencies != dependencies or
            reservation.snapshot["profile"] != profile or dependencies["files"]["institution_profile"] != profile_hash):
        raise StaleWrite("A1_DRAFT_DEPENDENCIES_CHANGED")
    root = _root(Path(settings.DOCUMENT_STORAGE_ROOT) / "j4")
    if case.artifact_reference:
        if case.artifact_reference.get("key") != reservation.package_key.hex:
            raise StaleWrite("A1_DRAFT_ARTIFACT_MISMATCH")
        current = dict(dependencies, reservation_sha256=result_hash(reservation.snapshot))
        if verify_artifact(root, case.artifact_reference, current)["stale"]:
            raise StaleWrite("A1_DRAFT_ARTIFACT_STALE")
        audit(user, organization, "a1.draft_reused", f"a1:{case.pk}")
        return case
    with tempfile.TemporaryDirectory(prefix=".draft-render-", dir=root) as temporary:
        pdf, checks = render_application_draft(reservation.snapshot["row"], reservation.snapshot["profile"], Path(temporary))
        # Recheck files after rendering; source rows remain locked throughout this transaction.
        if _dependencies(case, profile_path) != dependencies:
            raise StaleWrite("A1_DRAFT_DEPENDENCIES_CHANGED")
        artifact_dependencies = dict(dependencies, reservation_sha256=result_hash(reservation.snapshot))
        reference = publish_artifact(root, pdf, {"reservation": reservation.snapshot, "checks": checks},
            artifact_dependencies, operation_key=reservation.package_key.hex)
    case.artifact_reference = reference
    case.artifact_dependencies = artifact_dependencies
    case.prepared_artifact_hash = reference["pdf_sha256"]
    # Readiness/issuance/human confirmation are deliberately untouched.
    case.save(update_fields=["artifact_reference", "artifact_dependencies", "prepared_artifact_hash"])
    audit(user, organization, "a1.draft_published", f"a1:{case.pk}")
    return case


def prepare_application_draft(user, organization, case_id):
    reservation = reserve_application_draft(user, organization, case_id)
    return _publish_reserved(user, organization, reservation.pk)
