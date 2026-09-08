import subprocess
from io import BytesIO
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
import pytest
from src.document_core.adapters.tesseract import TesseractAdapter
from src.document_core.ocr_result import ContractError


def test_missing_binary():
    with patch("shutil.which", return_value=None), pytest.raises(ContractError, match="UNAVAILABLE"):
        TesseractAdapter()


def test_missing_language():
    with patch.object(TesseractAdapter, "_call", side_effect=[b"tesseract 5\n", b"eng\n"]), pytest.raises(ContractError, match="LANGUAGES"):
        TesseractAdapter()


def test_timeout_and_failed_engine_are_sanitized():
    with patch.object(TesseractAdapter, "_call", side_effect=[b"tesseract 5\n", b"ces\ndeu\neng\n"]):
        adapter = TesseractAdapter()
    for error, code in ((subprocess.TimeoutExpired("private", 1), "TIMEOUT"),
                        (subprocess.CalledProcessError(1, "private", stderr=b"secret"), "FAILED")):
        with patch("subprocess.run", side_effect=error), pytest.raises(ContractError, match="TESSERACT_"+code) as caught:
            adapter.process(b"synthetic")
        assert "private" not in str(caught.value) and "secret" not in str(caught.value)


def test_real_tesseract_normalized_output():
    image = Image.new("RGB", (900, 140), "white")
    ImageDraw.Draw(image).text((30, 30), "SYNTHETIC 15.03.1990 TEST123456", fill="black",
                              font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32))
    stream = BytesIO()
    image.save(stream, format="PNG")
    result = TesseractAdapter().process(stream.getvalue())
    assert "15.03.1990" in result.txts and "TEST123456" in result.txts
    assert result.engine == "tesseract" and result.engine_version
    assert all(r.located and len(r.polygon) == 4 and 0 <= r.confidence <= 1 for r in result.regions)


def test_malformed_geometry_rejected():
    with patch.object(TesseractAdapter, "_call", side_effect=[b"tesseract 5\n", b"ces\ndeu\neng\n"]):
        adapter = TesseractAdapter()
    with patch.object(adapter, "_call", return_value=b"text\tleft\ttop\twidth\theight\tconf\nword\t0\t0\t-1\t10\t90\n"), pytest.raises(ContractError, match="OUTPUT_INVALID"):
        adapter.process(b"synthetic")
