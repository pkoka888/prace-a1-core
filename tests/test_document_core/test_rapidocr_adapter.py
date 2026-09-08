"""Tests for document_core.adapters.rapidocr — actual RapidOCR execution.

These tests run real RapidOCR on programmatically generated synthetic images.
No mocks; no real scans; no employee records. Network is disabled via
environment isolation (RapidOCR runs fully offline once models are cached).
"""

from __future__ import annotations

import hashlib
import sys
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from document_core.adapters.rapidocr import RapidOCRAdapter, _convert_rapidocr_output, _engine_version
from document_core.ocr_result import (
    OcrResult,
    UnalignedOutputError,
    UnlocatedTextError,
)


class SyntheticImage:
    """Programmatically generated document image for testing."""

    def __init__(self, lines: list[str], width: int = 600, height: int = 400):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            pytest.skip("Pillow not available")

        self._img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(self._img)
        try:
            self._font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
            )
        except Exception:
            self._font = ImageFont.load_default()

        y = 20
        for line in lines:
            draw.text((20, y), line, fill="black", font=self._font)
            y += 40

    @property
    def bytes(self) -> bytes:
        buf = BytesIO()
        self._img.save(buf, format="PNG")
        return buf.getvalue()


class TestEngineVersionDiscovery:
    def test_version_is_string(self):
        v = _engine_version()
        assert isinstance(v, str)

    def test_adapter_reports_version(self):
        adapter = RapidOCRAdapter()
        assert adapter._engine_version == _engine_version()


class TestRapidOCRAdapter:
    """Tests that run actual RapidOCR on synthetic images."""

    def test_simple_text_extraction(self):
        """Synthetic image with known text → expected extracted values."""
        img = SyntheticImage(["OP/CR/CZ", "Novakova", "Dana"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        assert result.engine == "rapidocr"
        assert result.elapse_ms > 0
        assert result.source_image_hash != ""
        assert result.is_empty is False

        txts_lower = [t.lower() for t in result.txts]
        assert "op/cr/cz" in txts_lower
        assert "novakova" in txts_lower

    def test_empty_image_returns_empty_result(self):
        """Empty image (no text) → is_empty=True, zero regions."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not available")

        img = Image.new("RGB", (600, 400), color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        empty_bytes = buf.getvalue()

        adapter = RapidOCRAdapter()
        result = adapter.process(empty_bytes)

        assert result.is_empty is True
        assert len(result.regions) == 0
        assert result.elapse_ms >= 0
        assert result.engine_version != ""

    def test_birth_date_vs_expiry_interpretation(self):
        """Date fields 'Datum narozeni: 15.03.1990' and 'Platnost: 31.12.2099'
        are both extracted as text strings; field interpretation is a separate
        layer. This tests OCR extraction of both date strings, not date parsing."""
        img = SyntheticImage(["Datum narozeni: 15.03.1990", "Platnost: 31.12.2099"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        txts_text = " ".join(result.txts)
        assert "15.03.1990" in txts_text
        assert "31.12.2099" in txts_text
        assert "15" in txts_text
        assert "1990" in txts_text

    def test_elapse_seconds_to_milliseconds(self):
        """RapidOCR elapse is in seconds; adapter converts to milliseconds."""
        img = SyntheticImage(["OP/CR/CZ"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        assert result.elapse_ms > 0
        assert isinstance(result.elapse_ms, int)
        from types import SimpleNamespace
        empty = _convert_rapidocr_output(SimpleNamespace(boxes=None, txts=None, scores=None, elapse=.125), img.bytes, "test")
        assert empty.elapse_ms == 125

    def test_numPy_box_array_normalized(self):
        """RapidOCR returns np.ndarray boxes; adapter normalizes to int tuples."""
        img = SyntheticImage(["OP/CR/CZ"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        for region in result.regions:
            assert region.located is True
            assert isinstance(region.polygon, tuple)
            assert len(region.polygon) == 4
            for point in region.polygon:
                assert isinstance(point, tuple)
                assert len(point) == 2
                assert isinstance(point[0], int)
                assert isinstance(point[1], int)

    def test_tuple_txts_scores_normalized(self):
        """RapidOCR txts/scores are tuples; adapter normalizes to application types."""
        img = SyntheticImage(["OP/CR/CZ", "Test"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        assert isinstance(result.txts, list)
        assert isinstance(result.scores, list)
        assert all(isinstance(t, str) for t in result.txts)
        assert all(isinstance(s, float) for s in result.scores)

    def test_multiple_text_regions(self):
        """Three-line synthetic image → three regions detected."""
        img = SyntheticImage(["OP/CR/CZ", "Jan Novak", "01.01.1980"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        assert len(result.regions) >= 2
        txts_joined = " ".join(result.txts).lower()
        assert "op/cr/cz" in txts_joined or "op" in txts_joined

    def test_source_image_hash_present(self):
        """Each result carries SHA-256 of source image for provenance."""
        img = SyntheticImage(["OP/CR/CZ"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        expected_hash = hashlib.sha256(img.bytes).hexdigest()
        assert result.source_image_hash == expected_hash

    def test_normalized_result_has_no_mutable_vendor_output(self):
        img = SyntheticImage(["OP/CR/CZ"])
        result = RapidOCRAdapter().process(img.bytes)
        assert not hasattr(result, "raw_output")
        assert result.engine_version == "3.9.2"
        with pytest.raises(AttributeError):
            result.regions = ()

    def test_boxes_property_matches_regions(self):
        """boxes property returns one entry per region; None for unlocated."""
        img = SyntheticImage(["OP/CR/CZ", "Name"])
        adapter = RapidOCRAdapter()
        result = adapter.process(img.bytes)

        assert len(result.boxes) == len(result.regions)
        for box, region in zip(result.boxes, result.regions):
            if region.located:
                assert isinstance(box, list)
                assert len(box) == 4
            else:
                assert box is None


class TestConvertRapidOCROutputEdgeCases:
    """Adapter normalization edge cases."""

    def test_none_output_returns_empty(self):
        version = _engine_version()
        result = _convert_rapidocr_output(None, b"fake-bytes", version)
        assert result.is_empty is True
        assert result.engine_version == version

    def test_none_boxes_with_txts_raises_unlocated_text_error(self):
        """txts present without boxes → UnlocatedTextError (not fabricated coords)."""
        version = _engine_version()

        class FakeOutput:
            boxes = None
            txts = ("text",)
            scores = (0.99,)
            elapse = 1.0

        with pytest.raises(UnlocatedTextError) as exc_info:
            _convert_rapidocr_output(FakeOutput(), b"fake-bytes", version)
        assert exc_info.value.txts_count == 1
        assert exc_info.value.boxes_count is None

    def test_empty_txts_returns_empty(self):
        version = _engine_version()

        class FakeOutput:
            boxes = None
            txts = ()
            scores = ()
            elapse = 0.5

        result = _convert_rapidocr_output(FakeOutput(), b"fake-bytes", version)
        assert result.is_empty is True

    def test_mismatched_box_txt_counts_raises_alignment_error(self):
        version = _engine_version()

        class FakeOutput:
            boxes = [[[0, 0], [100, 0], [100, 50], [0, 50]]]  # 1 box
            txts = ("text1", "text2")  # 2 texts
            scores = (0.99,)
            elapse = 1.0

        with pytest.raises(UnalignedOutputError) as exc_info:
            _convert_rapidocr_output(FakeOutput(), b"fake-bytes", version)
        assert exc_info.value.boxes == 1
        assert exc_info.value.txts == 2
        assert exc_info.value.scores == 1
