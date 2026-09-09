"""Synthetic completed-batch adapter; originals stay in the inbox for retention review.

Configure DOCUMENT_INBOX_ROOTS = {organization_pk: private_path} beneath
DOCUMENT_STORAGE_ROOT; each organization must have its own disjoint root. Publish a private
UUID-hex batch directory, then atomically rename ready.json into place last:
{"organization_id": 1, "files": [{"name": "<32-hex>.png", "sha256": "<64-hex>"}]}
Names are opaque; filenames never determine identity. Completed documents/runs
are reused, failed OCR runs follow the existing retry/lease policy. Each invocation
stores a private receipt using the existing generated/<uuid>.json storage contract.
This local coordinator serializes callers sharing the inbox; it is not a distributed
queue and does not change the intake engine's dependency-version reuse contract.
"""
from datetime import timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from src.document_core.images import MAX_BYTES
from .document_intake import authorize, audit, intake, execute_run
from .document_storage import document_storage
from .identity import persist_identity_evaluation, prepare_identity_draft
from .a1_exports import prepare_input_case
from .a1_drafts import prepare_application_draft, DraftInputBlocked
from .models import Document
from .services import Forbidden

TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".tif": "image/tiff", ".tiff": "image/tiff"}
NAME = re.compile(r"[a-f0-9]{32}\.(?:pdf|png|jpe?g|tiff?)")


def _private_fd(name, parent=None, *, directory=False):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    if directory:
        flags |= os.O_DIRECTORY
    fd = os.open(name, flags, dir_fd=parent)
    info = os.fstat(fd)
    if ((not directory and not stat.S_ISREG(info.st_mode)) or
            stat.S_IMODE(info.st_mode) & 0o077 or info.st_uid != os.geteuid()):
        os.close(fd)
        raise ValueError("INBOX_PRIVATE_MODE_REQUIRED")
    return fd


def _read(name, parent, limit):
    fd = _private_fd(name, parent)
    with os.fdopen(fd, "rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("INBOX_SIZE_LIMIT")
    return content


def _manifest(batch_fd, organization):
    manifest_bytes = _read("ready.json", batch_fd, 128 * 1024)
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get("organization_id") != organization.pk:
        raise ValueError("INBOX_ORGANIZATION_MISMATCH")
    files = manifest.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= 100:
        raise ValueError("INBOX_INVALID_MANIFEST")
    seen = set()
    for item in files:
        if (not isinstance(item, dict) or not isinstance(item.get("name"), str)
                or not NAME.fullmatch(item["name"])
                or not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])
                or item["name"] in seen
                or ("activity_profile" in item and item["activity_profile"] not in ("employee", "self_employed"))):
            raise ValueError("INBOX_INVALID_MANIFEST")
        seen.add(item["name"])
    return files, hashlib.sha256(manifest_bytes).hexdigest()


def process_inbox(user, organization, *, processor=None):
    """Return only opaque references/outcomes; never approve identity or create PDFs."""
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise Forbidden("REAL_DATA_ACTIVATION_REQUIRED")
    authorize(user, organization, "document:upload")
    roots = getattr(settings, "DOCUMENT_INBOX_ROOTS", {})
    configured = roots.get(organization.pk)
    if not configured:
        raise ValueError("INBOX_NOT_CONFIGURED")
    root = Path(configured).absolute()
    storage_root = Path(settings.DOCUMENT_STORAGE_ROOT).resolve()
    if root.resolve() != root or not root.is_relative_to(storage_root) or root == storage_root:
        raise ValueError("INBOX_ROOT_OUTSIDE_PRIVATE_STORAGE")
    for owner, other in roots.items():
        other = Path(other).absolute().resolve()
        if owner != organization.pk and (other.is_relative_to(root) or root.is_relative_to(other)):
            raise ValueError("INBOX_ROOTS_MUST_BE_DISJOINT")
    root_fd = _private_fd(root, directory=True)
    try:
        lock_fd = os.open(".process.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                          0o600, dir_fd=root_fd)
        try:
            lock_info = os.fstat(lock_fd)
            if not stat.S_ISREG(lock_info.st_mode) or stat.S_IMODE(lock_info.st_mode) & 0o077 or lock_info.st_uid != os.geteuid():
                raise ValueError("INBOX_PRIVATE_MODE_REQUIRED")
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("INBOX_BUSY") from None
            return _process_batches(root_fd, user, organization, processor)
        finally:
            os.close(lock_fd)
    finally:
        os.close(root_fd)


def _process_batches(root_fd, user, organization, processor):
    receipts = []
    for batch in sorted(os.listdir(root_fd)):
        if not re.fullmatch(r"[a-f0-9]{32}", batch):
            continue
        result = {"batch_ref": batch, "organization_id": organization.pk,
                  "actor_ref": f"user:{user.pk}", "identity_resolution": "requires_review",
                  "purpose": "worker_intake", "retention_review_at": (timezone.now() + timedelta(days=90)).isoformat(),
                  "occurred_at": timezone.now().isoformat(), "items": []}
        batch_fd = None
        try:
            batch_fd = _private_fd(batch, root_fd, directory=True)
            try:
                files, result["manifest_sha256"] = _manifest(batch_fd, organization)
            except FileNotFoundError:
                continue  # No atomically published ready manifest yet.
            for item in files:
                outcome = {"item_ref": item["name"].split(".")[0]}
                try:
                    content = _read(item["name"], batch_fd, MAX_BYTES)
                    if hashlib.sha256(content).hexdigest() != item["sha256"]:
                        raise ValueError("INBOX_HASH_MISMATCH")
                    existing = Document.objects.filter(organization=organization, sha256=item["sha256"]).exists()
                    document, version, _, run = intake(
                        user, organization, None, item["name"], TYPES[Path(item["name"]).suffix],
                        content, processor=processor)
                    if version.sha256 != item["sha256"]:
                        raise ValueError("INBOX_SOURCE_SUPERSEDED")
                    if existing:
                        run = execute_run(user, organization, run.pk, processor=processor)
                    outcome.update(status=run.state, source_sha256=version.sha256,
                                   document_ref=document.pk, version_ref=version.pk, run_ref=run.pk)
                except Exception:
                    # Source content and arbitrary processor exception text must never escape.
                    outcome.update(status="rejected", reason="INTAKE_ITEM_REJECTED")
                audit(user, organization, "inbox.item_processed", f"batch:{batch}:item:{outcome['item_ref']}",
                      "success" if outcome["status"] == "completed" else "failed")
                result["items"].append(outcome)
            completed = [item["run_ref"] for item in result["items"] if item["status"] == "completed"]
            if completed:
                try:
                    evaluation = persist_identity_evaluation(user, organization, completed)
                    result["identity_evaluation"] = {**evaluation.evidence, "evaluation_ref": evaluation.pk}
                    result["drafts"] = []
                    profiles = {outcome["run_ref"]: item.get("activity_profile")
                                for item, outcome in zip(files, result["items"])
                                if outcome["status"] == "completed" and item.get("activity_profile")}
                    # Contradictory business defaults for the same source are unresolved.
                    conflicting = {run_id for run_id in profiles if len({item.get("activity_profile")
                        for item, outcome in zip(files, result["items"])
                        if outcome.get("run_ref") == run_id and item.get("activity_profile")}) > 1}
                    for run_id in conflicting:
                        profiles[run_id] = None  # Preserve conflicts for identifier peers too.
                    for region in evaluation.evidence["regions"]:
                        run_id = region["run_ref"]
                        draft = {"run_ref": run_id, "region_ref": region["region_ref"]}
                        if run_id not in profiles or run_id in conflicting:
                            draft.update(status="requires_review", reason=("ACTIVITY_PROFILE_CONFLICT"
                                         if run_id in conflicting else "ACTIVITY_PROFILE_REQUIRED"))
                        else:
                            draft.update(activity_profile=profiles[run_id], profile_source="batch_manifest")
                            try:
                                draft.update(prepare_identity_draft(user, organization, evaluation.pk,
                                    run_id, region["region_ref"], activity_profile=profiles[run_id], activity_profiles=profiles))
                            except Exception:
                                draft.update(status="requires_review", reason="DRAFT_PREPARATION_UNAVAILABLE")
                        if draft.get("worker_ref"):
                            try:
                                case = prepare_input_case(user, organization, draft["worker_ref"],
                                                          claim_id=draft.get("claim_ref"))
                                draft["a1_input"] = {"case_ref": case.pk, "source_sha256": case.source_hash,
                                                     "blockers": case.source_snapshot_json["blockers"]}
                                try:
                                    rendered = prepare_application_draft(user, organization, case.pk)
                                    draft["a1_draft"] = {"status": "unverified_draft", "case_ref": case.pk,
                                        "generation_ref": rendered.pk, "generation_revision": rendered.revision,
                                        "package_key": rendered.artifact_reference["key"],
                                        "pdf_sha256": rendered.prepared_artifact_hash, "visual_review": "pending"}
                                except DraftInputBlocked as error:
                                    draft["a1_draft"] = {"status": "blocked", "reason": str(error)}
                                except Exception:
                                    draft["a1_draft"] = {"status": "unavailable", "reason": "A1_DRAFT_PUBLICATION_UNAVAILABLE"}
                            except Exception:
                                draft["a1_input"] = {"status": "unavailable", "reason": "A1_INPUT_PREPARATION_UNAVAILABLE"}
                        result["drafts"].append(draft)
                except Exception:
                    result["identity_evaluation"] = {"status": "unavailable", "accepted": False}
            result["status"] = "completed" if (
                all(i["status"] == "completed" for i in result["items"])
                and result.get("identity_evaluation", {}).get("status") != "unavailable"
                and not any((d.get("reason") == "DRAFT_PREPARATION_UNAVAILABLE" or d.get("a1_input", {}).get("status") == "unavailable" or d.get("a1_draft", {}).get("status") == "unavailable")
                            for d in result.get("drafts", []))) else "partial"
        except Exception:
            result["status"] = "rejected"
            result["reason"] = "INBOX_BATCH_REJECTED"
            audit(user, organization, "inbox.batch_rejected", f"batch:{batch}", "failed")
        finally:
            if batch_fd is not None:
                os.close(batch_fd)
        key = document_storage().save(f"generated/{uuid4().hex}.json", ContentFile(json.dumps(result, sort_keys=True).encode()))
        result["receipt_key"] = key
        receipts.append(result)
    return receipts
