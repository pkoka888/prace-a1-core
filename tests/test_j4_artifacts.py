"""Synthetic stored byte evidence; no employee files or service database."""
import hashlib
import os
import tempfile
from pathlib import Path

import pymupdf
import pytest

from portal.release1a.j4_artifacts import ArtifactError, publish_artifact, verify_artifact


def pdf():
    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page(width=144, height=144)
        page.insert_text((10, 40), f"SYNTHETIC {i}")
    return doc.tobytes()


@pytest.fixture
def root():
    parent = Path(__file__).resolve().parents[1] / "runtime/portal"
    with tempfile.TemporaryDirectory(prefix="j4-synthetic-test-", dir=parent) as temporary:
        path = Path(temporary) / "protected"
        path.mkdir(mode=0o700)
        yield path


def test_all_pages_bytes_snapshot_and_staleness(root):
    data = pdf()
    snapshot = {"synthetic": True}
    dependencies = {"source": "revision-1"}
    ref = publish_artifact(root, data, snapshot, dependencies)
    snapshot["synthetic"] = False
    assert ref["pdf_sha256"] == hashlib.sha256(data).hexdigest()
    assert len(list((root / ref["key"]).glob("page-*.png"))) == 3
    assert all(p.stat().st_mode & 0o077 == 0 for p in (root / ref["key"]).iterdir())
    assert verify_artifact(root, ref, dependencies) == {"integrity": "verified", "stale": False}
    assert verify_artifact(root, ref, {"source": "revision-2"})["stale"]


@pytest.mark.parametrize("name", ["artifact.pdf", "snapshot.json", "receipt.json", "page-3.png"])
def test_modified_artifacts_rejected(root, name):
    ref = publish_artifact(root, pdf(), {}, {})
    (root / ref["key"] / name).write_bytes(b"changed")
    with pytest.raises(ArtifactError):
        verify_artifact(root, ref, {})


def test_invalid_pdf_leaves_no_package(root):
    with pytest.raises(ArtifactError):
        publish_artifact(root, b"%PDF-invalid", {}, {})
    assert list(root.iterdir()) == []


def test_symlink_root_rejected(root):
    link = root.parent / "link"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(ArtifactError, match="SYMLINK"):
        publish_artifact(link, pdf(), {}, {})


def test_packages_are_exclusive(root):
    one = publish_artifact(root, pdf(), {}, {})
    two = publish_artifact(root, pdf(), {}, {})
    assert one["key"] != two["key"]
    assert verify_artifact(root, one, {})["integrity"] == "verified"


@pytest.mark.parametrize("profile_name", ["posted_employee", "employee_multi_state", "self_employed_multi_state"])
def test_canonical_renderer_all_pages(root, profile_name):
    from test_finalize_a1 import employee, review_row
    from scripts.finalize_a1 import row_to_form
    from scripts.a1_core import generate_a1_pdf
    row = review_row(employee("synthetic", "TESTOVA", "ANNA", "01.02.1990", "900201/1234"), "SYNTHETIC-DOC")
    row["status_profile"] = profile_name
    profile = {"source_url": "https://example.invalid/synthetic", "institution": {"name": "SYNTHETIC", "street": "SYNTHETIC", "house_number": "1",
                               "city": "SYNTHETIC", "postal_code": "10000", "country_code": "CZ", "code": "TEST"}}
    project = Path(__file__).resolve().parents[1]
    output = root / "canonical.pdf"
    generate_a1_pdf(row_to_form(row, profile), project / "templates/a1_background.pdf",
                    project / "config/a1_layout.json", output)
    original = output.read_bytes()
    reference = publish_artifact(root, original, row, {"profile": profile_name})
    assert verify_artifact(root, reference, {"profile": profile_name})["integrity"] == "verified"
    assert output.read_bytes() == original


def test_existing_empty_destination_is_not_replaced(root, monkeypatch):
    import portal.release1a.j4_artifacts as module
    class Fixed: hex = 'f' * 32
    target = root / Fixed.hex
    target.mkdir()
    monkeypatch.setattr(module.uuid, 'uuid4', lambda: Fixed())
    with pytest.raises(ArtifactError, match='DESTINATION_EXISTS'):
        publish_artifact(root, pdf(), {}, {})
    assert target.is_dir() and not list(target.iterdir())
    assert not list(root.glob('.stage-*'))


def test_reserved_key_recovers_published_package_and_rejects_changed_inputs(root):
    key = "a" * 32
    data = pdf()
    ref = publish_artifact(root, data, {"synthetic": True}, {"revision": 1}, operation_key=key)
    assert publish_artifact(root, data, {"synthetic": True}, {"revision": 1}, operation_key=key) == ref
    assert len([p for p in root.iterdir() if p.is_dir()]) == 1
    with pytest.raises(ArtifactError, match="RETRY_MISMATCH"):
        publish_artifact(root, data, {"synthetic": False}, {"revision": 1}, operation_key=key)
    with pytest.raises(ArtifactError, match="RETRY_MISMATCH"):
        publish_artifact(root, data, {"synthetic": True}, {"revision": 2}, operation_key=key)
    with pytest.raises(ArtifactError, match="KEY_INVALID"):
        publish_artifact(root, data, {}, {}, operation_key="../escape")
