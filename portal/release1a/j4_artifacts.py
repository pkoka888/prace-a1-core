"""Protected byte evidence for canonical renderer outputs.

This module does not authorize rendering, certificate issuance, or publication to
final destinations. Callers must first satisfy the canonical A1 acceptance gate.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pymupdf


class ArtifactError(ValueError):
    pass


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _root(root):
    root = Path(root)
    if not root.is_absolute():
        raise ArtifactError("ARTIFACT_ROOT_INVALID")
    for component in (root, *root.parents):
        if component.is_symlink():
            raise ArtifactError("ARTIFACT_SYMLINK")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077:
        raise ArtifactError("ARTIFACT_ROOT_PERMISSIONS")
    return root


def _write(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _pages(content, dpi):
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            if pdf.page_count != 3 or pdf.is_encrypted:
                raise ArtifactError("ARTIFACT_PDF_INVALID")
            for page in pdf:
                if next(page.widgets(), None) is not None:
                    raise ArtifactError("ARTIFACT_PDF_INVALID")
                pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
                yield pixmap
    except ArtifactError:
        raise
    except Exception:
        raise ArtifactError("ARTIFACT_PDF_INVALID") from None


def publish_artifact(root, pdf_bytes, snapshot, dependencies, *, dpi=150, operation_key=None):
    """Atomically preserve an already-authorized PDF and every-page evidence.

    Snapshot and dependencies are deep-copied through canonical serialization.
    The returned key is opaque; no public URL is produced. QA here proves byte
    and preview integrity, not authoritative evidence or visual acceptance.
    """
    if dpi not in (150, 300):
        raise ArtifactError("ARTIFACT_DPI_INVALID")
    root = _root(root)
    operation = uuid.uuid4().hex if operation_key is None else operation_key
    if not isinstance(operation, str) or len(operation) != 32 or any(c not in "0123456789abcdef" for c in operation):
        raise ArtifactError("ARTIFACT_KEY_INVALID")
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{operation}-", dir=root))
    try:
        _write(stage / "artifact.pdf", pdf_bytes)
        snapshot_bytes, dependency_bytes = _json(snapshot), _json(dependencies)
        _write(stage / "snapshot.json", snapshot_bytes)
        pages = []
        for index, pixmap in enumerate(_pages(pdf_bytes, dpi), 1):
            name = f"page-{index}.png"
            png = pixmap.tobytes("png")
            _write(stage / name, png)
            pages.append({"name": name, "width": pixmap.width, "height": pixmap.height,
                          "pixel_sha256": _hash(pixmap.samples)})
        receipt = {"schema": 1, "operation_id": operation, "pdf_sha256": _hash(pdf_bytes),
                   "snapshot_sha256": _hash(snapshot_bytes),
                   "dependencies": json.loads(dependency_bytes),
                   "dependency_sha256": _hash(dependency_bytes), "dpi": dpi,
                   "pages": pages, "qa": "byte_and_preview_integrity", "visual_acceptance": "not_recorded"}
        _write(stage / "receipt.json", _json(receipt))
        # Serialize cooperating publishers and reject even an empty existing target.
        stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)
        lock = os.open(root / '.publication.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if (root / operation).exists() or (root / operation).is_symlink():
                if operation_key is None:
                    raise ArtifactError('ARTIFACT_DESTINATION_EXISTS')
                existing = root / operation
                if existing.is_symlink() or (existing / "receipt.json").is_symlink():
                    raise ArtifactError("ARTIFACT_SYMLINK")
                old_receipt = (existing / "receipt.json").read_bytes()
                reference = {"key": operation, "pdf_sha256": _hash(pdf_bytes),
                             "receipt_sha256": _hash(old_receipt)}
                verified = verify_artifact(root, reference, dependencies)
                if (verified["stale"] or (existing / "snapshot.json").read_bytes() != snapshot_bytes
                        or json.loads(old_receipt)["dpi"] != dpi):
                    raise ArtifactError("ARTIFACT_RETRY_MISMATCH")
                return reference
            os.rename(stage, root / operation)
        finally:
            os.close(lock)
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {"key": operation, "pdf_sha256": receipt["pdf_sha256"],
                "receipt_sha256": _hash(_json(receipt))}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def current_artifact_dependencies(case):
    """Return the current dependency descriptor for an A1Case artifact.

    The returned dict is canonicalized through JSON serialization, so its hash
    can be compared against the dependency hash stored in the artifact receipt.
    Any change to source fields, worker reference, or snapshot invalidates it.
    """
    return {
        "source_hash": case.source_hash,
        "source_snapshot": case.source_snapshot_json,
        "worker_id": case.worker_id,
    }
def verify_artifact(root, reference, current_dependencies):
    """Verify stored bytes and fresh decoded pixels; report dependency staleness."""
    root = _root(root)
    key = reference.get("key", "")
    if len(key) != 32 or any(c not in "0123456789abcdef" for c in key):
        raise ArtifactError("ARTIFACT_KEY_INVALID")
    package = root / key
    try:
        if package.is_symlink() or any(p.is_symlink() for p in package.iterdir()):
            raise ArtifactError("ARTIFACT_SYMLINK")
        receipt_bytes = (package / "receipt.json").read_bytes()
        if _hash(receipt_bytes) != reference["receipt_sha256"]:
            raise ArtifactError("ARTIFACT_RECEIPT_CHANGED")
        receipt = json.loads(receipt_bytes)
        pdf = (package / "artifact.pdf").read_bytes()
        if _hash(pdf) != reference["pdf_sha256"] or _hash(pdf) != receipt["pdf_sha256"]:
            raise ArtifactError("ARTIFACT_PDF_CHANGED")
        if _hash((package / "snapshot.json").read_bytes()) != receipt["snapshot_sha256"]:
            raise ArtifactError("ARTIFACT_SNAPSHOT_CHANGED")
        fresh = list(_pages(pdf, receipt["dpi"]))
        if len(fresh) != len(receipt["pages"]):
            raise ArtifactError("ARTIFACT_PAGE_COUNT_CHANGED")
        for index, (pixmap, expected) in enumerate(zip(fresh, receipt["pages"]), 1):
            try:
                stored = pymupdf.Pixmap(str(package / f"page-{index}.png"))
            except pymupdf.mupdf.FzErrorBase as e:
                raise ArtifactError("ARTIFACT_PREVIEW_CHANGED") from e
            if (stored.width, stored.height, stored.n, _hash(stored.samples)) != (
                    pixmap.width, pixmap.height, pixmap.n, expected["pixel_sha256"]):
                raise ArtifactError("ARTIFACT_PREVIEW_CHANGED")
            if _hash(pixmap.samples) != expected["pixel_sha256"]:
                raise ArtifactError("ARTIFACT_PREVIEW_CHANGED")
        return {"integrity": "verified", "stale": _hash(_json(current_dependencies)) != receipt["dependency_sha256"]}
    except ArtifactError:
        raise
    except Exception:
        raise ArtifactError("ARTIFACT_UNAVAILABLE") from None
