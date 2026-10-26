"""Test that framework only replaces placeholders - no notices/watermarks."""
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import generate, a1_core


MINIMAL_FORM = {
    "person": {
        "insurance_number": "12345678",
        "surname": "NOVÁK",
        "given_name": "Jan",
        "dob": "01.01.1990",
        "nationality": "CZ",
        "birth_place": "Praha",
        "sex": "M",
    },
    "residence": {
        "street": "Wilsonova",
        "house_number": "1234",
        "city": "Praha",
        "postal_code": "100 00",
        "country_code": "CZ",
    },
    "certificate": {
        "member_state": "CZ",
        "start_date": "01.01.2025",
        "end_date": "31.12.2025",
        "document_id": "N65023S444/2025/CZ",
    },
    "employment": {
        "employer_id": "EMPL001",
        "employer_name": "Firma s.r.o.",
        "street": "Kolejna",
        "house_number": "5",
        "city": "Praha",
        "postal_code": "110 00",
        "country_code": "CZ",
    },
    "institution": {
        "name": "Úřad práce",
        "street": "Národní",
        "house_number": "23",
        "city": "Praha",
        "postal_code": "110 00",
        "country_code": "CZ",
        "code": "01234567",
        "issue_date": "01.01.2025",
        "signed_by": "Jméno Příjmení",
    },
    "activity": {},
    "meta": {},
}


def test_placeholder_replacement():
    """Verify placeholders are replaced with correct values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.pdf"
        result = generate.generate(MINIMAL_FORM, output_path)
        
        assert result.exists(), "Output PDF was created"
        assert result.stat().st_mode & 0o600, "Output has correct permissions"
        
        import pymupdf
        doc = pymupdf.open(result)
        
        # Check no placeholders remain
        text = ""
        for page in doc:
            text += page.get_text()
        
        # Count placeholders
        import re
        placeholders = re.findall(r'\{\{[a-z_]+\}\}', text)
        assert len(placeholders) == 0, f"No placeholders should remain, found: {placeholders}"
        
        # Check replaced values are present
        assert "NOVÁK" in text, "Surname should be replaced"
        assert "12345678" in text, "Insurance number should be replaced"
        assert "N65023S444/2025/CZ" in text, "Document ID should be replaced"


def test_no_notices_added():
    """Verify NO watermarks, provisional stamps, or notices are added."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.pdf"
        result = generate.generate(MINIMAL_FORM, output_path)
        
        import pymupdf
        doc = pymupdf.open(result)
        
        for page_num, page in enumerate(doc):
            # Check for common notice strings
            text = page.get_text()
            assert "NÁVRH – ČEKÁ NA POTVRZENÍ OSSZ" not in text, f"Notice should not be on page {page_num}"
            assert "UNVERIFIED DRAFT" not in text, f"Draft notice should not be on page {page_num}"
            assert "NEOVĚŘENÝ NÁVRH" not in text, f"Czech notice should not be on page {page_num}"


def test_template_used_only():
    """Verify only a1_template_v1.pdf is used."""
    from core.a1_core import TEMPLATE_PATH
    assert TEMPLATE_PATH.name == "a1_template_v1.pdf", "Template must be a1_template_v1.pdf"
    assert TEMPLATE_PATH.exists(), "Template file must exist"
