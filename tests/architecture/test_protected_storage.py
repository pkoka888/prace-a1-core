import pytest
from prototypes.architecture.adr001.proof_contract import Denied, InvalidUpload, download_headers, validate_upload

def test_quarantine_validation_opaque_key_and_authorized_delivery():
    doc = validate_upload("org-alpha", "synthetic.pdf", "application/pdf", b"%PDF-1.4\n%%EOF")
    assert "synthetic" not in doc.object_key and "org-alpha" not in doc.object_key
    assert download_headers("org-alpha", doc)["X-Accel-Redirect"].startswith("/_protected/objects/")
    with pytest.raises(Denied): download_headers("org-beta", doc)
    for name, mime, body in [("../x.pdf", "application/pdf", b"%PDF-x"), ("x.pdf", "application/pdf", b"MZ"), ("x.pdf", "image/png", b"%PDF-x")]:
        with pytest.raises(InvalidUpload): validate_upload("org-alpha", name, mime, body)

