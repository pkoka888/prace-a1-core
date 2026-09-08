"""Tests for document_core.ocr_result — normalization utilities and OcrResult type."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from document_core.ocr_result import (
    OcrRegion,
    OcrResult,
    UnalignedOutputError,
    UnlocatedTextError,
    _normalize_box,
    _normalize_scores,
    _normalize_txts,
    _to_elapse_ms,
)


class TestNormalizeBox:
    def test_list_of_lists(self):
        box = [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]]
        result = _normalize_box(box)
        assert result == ((0, 0), (100, 0), (100, 50), (0, 50))

    def test_tuple_of_tuples(self):
        box = ((0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0))
        result = _normalize_box(box)
        assert result == ((0, 0), (100, 0), (100, 50), (0, 50))

    def test_numpy_array_float32(self):
        import numpy as np

        box = np.array([[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]], dtype=np.float32)
        result = _normalize_box(box)
        assert result == ((0, 0), (100, 0), (100, 50), (0, 50))

    def test_numpy_array_2d(self):
        import numpy as np

        box = np.array([[44.0, 41.0], [203.0, 41.0], [203.0, 89.0], [44.0, 89.0]], dtype=np.float32)
        result = _normalize_box(box)
        assert result == ((44, 41), (203, 41), (203, 89), (44, 89))

    def test_empty_box_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _normalize_box([])

    def test_none_raises(self):
        with pytest.raises(ValueError, match="cannot be None"):
            _normalize_box(None)


class TestNormalizeTxts:
    def test_tuple_of_strings(self):
        txts = ("foo", "bar")
        result = _normalize_txts(txts)
        assert result == ("foo", "bar")

    def test_list_of_strings(self):
        txts = ["foo", "bar"]
        result = _normalize_txts(txts)
        assert result == ("foo", "bar")

    def test_numpy_array(self):
        import numpy as np

        txts = np.array(["OP/CR/CZ", "Novakova"], dtype=object)
        result = _normalize_txts(txts)
        assert result == ("OP/CR/CZ", "Novakova")

    def test_none_returns_empty(self):
        result = _normalize_txts(None)
        assert result == ()

    def test_mixed_types(self):
        txts = ["text", 123, None]
        result = _normalize_txts(txts)
        assert result == ("text", "123", "None")


class TestNormalizeScores:
    def test_tuple_of_floats(self):
        scores = (0.99, 0.95)
        result = _normalize_scores(scores)
        assert result == (0.99, 0.95)

    def test_list_of_floats(self):
        scores = [0.99, 0.95]
        result = _normalize_scores(scores)
        assert result == (0.99, 0.95)

    def test_numpy_array(self):
        import numpy as np

        scores = np.array([0.99993, 0.99993], dtype=np.float32)
        result = _normalize_scores(scores)
        assert len(result) == 2

    def test_none_returns_empty(self):
        result = _normalize_scores(None)
        assert result == ()

    def test_int_values(self):
        scores = [1, 0]
        result = _normalize_scores(scores)
        assert result == (1.0, 0.0)


class TestToElapseMs:
    def test_float_seconds_to_ms(self):
        assert _to_elapse_ms(3.014) == 3014

    def test_int_seconds_to_ms(self):
        assert _to_elapse_ms(3) == 3000

    def test_zero(self):
        assert _to_elapse_ms(0) == 0

    def test_none_returns_zero(self):
        assert _to_elapse_ms(None) == 0


class TestOcrRegion:
    def test_valid_located_region(self):
        poly = ((0, 0), (100, 0), (100, 50), (0, 50))
        region = OcrRegion(
            region_id=str(uuid4()),
            source_page=0,
            polygon=poly,
            text="OP/CR/CZ",
            confidence=0.999,
            located=True,
            transform="none",
        )
        assert region.text == "OP/CR/CZ"
        assert region.confidence == 0.999
        assert region.located is True

    def test_unlocated_region(self):
        region = OcrRegion(
            region_id=str(uuid4()),
            source_page=0,
            polygon=None,
            text="unlocated text",
            confidence=0.5,
            located=False,
            transform="none",
        )
        assert region.located is False
        assert region.polygon is None

    def test_located_with_none_polygon_raises(self):
        with pytest.raises(ValueError, match="cannot be None when located"):
            OcrRegion(
                region_id=str(uuid4()),
                source_page=0,
                polygon=None,
                text="x",
                confidence=0.5,
                located=True,
            )

    def test_unlocated_with_polygon_raises(self):
        poly = ((0, 0), (100, 0), (100, 50), (0, 50))
        with pytest.raises(ValueError, match="must be None when located=False"):
            OcrRegion(
                region_id=str(uuid4()),
                source_page=0,
                polygon=poly,
                text="x",
                confidence=0.5,
                located=False,
            )

    def test_wrong_polygon_length_raises(self):
        with pytest.raises(ValueError, match="4-point"):
            OcrRegion(
                region_id=str(uuid4()),
                source_page=0,
                polygon=((0, 0), (100, 0)),
                text="test",
                confidence=0.5,
                located=True,
            )


class TestOcrResult:
    def test_boxes_property_located(self):
        poly = ((0, 0), (100, 0), (100, 50), (0, 50))
        region = OcrRegion(
            region_id=str(uuid4()),
            source_page=0,
            polygon=poly,
            text="test",
            confidence=0.99,
            located=True,
        )
        result = OcrResult(
            regions=(region,),
            elapse_ms=3000,
            engine="rapidocr",
            engine_version="3.9.2",
            source_image_hash="abc",
        )
        assert result.boxes == [[[0, 0], [100, 0], [100, 50], [0, 50]]]
        assert result.txts == ["test"]
        assert result.scores == [0.99]
        assert result.is_empty is False

    def test_boxes_property_unlocated(self):
        region = OcrRegion(
            region_id=str(uuid4()),
            source_page=0,
            polygon=None,
            text="unlocated",
            confidence=0.5,
            located=False,
        )
        result = OcrResult(
            regions=(region,),
            elapse_ms=0,
            engine="rapidocr",
            engine_version="3.9.2",
            source_image_hash="abc",
        )
        assert result.boxes == [None]
        assert result.txts == ["unlocated"]

    def test_empty_result(self):
        result = OcrResult(
            regions=(),
            elapse_ms=0,
            engine="rapidocr",
            engine_version="3.9.2",
            source_image_hash="abc",
        )
        assert result.is_empty is True
        assert result.boxes == []
        assert result.txts == []
        assert result.scores == []

    def test_frozen_immutable(self):
        region = OcrRegion(
            region_id=str(uuid4()),
            source_page=0,
            polygon=((0, 0), (100, 0), (100, 50), (0, 50)),
            text="test",
            confidence=0.99,
            located=True,
        )
        result = OcrResult(
            regions=(region,),
            elapse_ms=3000,
            engine="rapidocr",
            engine_version="3.9.2",
            source_image_hash="abc",
        )
        with pytest.raises(AttributeError):
            result.elapse_ms = 5000


class TestErrorTypes:
    def test_unaligned_output_error(self):
        err = UnalignedOutputError(boxes=2, txts=3, scores=2)
        assert err.boxes == 2
        assert err.txts == 3
        assert "boxes=2" in str(err)
        assert "txts=3" in str(err)

    def test_unlocated_text_error(self):
        err = UnlocatedTextError(txts_count=5, boxes_count=None)
        assert err.txts_count == 5
        assert err.boxes_count is None
        assert "5 text(s)" in str(err)
        assert "None box(es)" in str(err)
