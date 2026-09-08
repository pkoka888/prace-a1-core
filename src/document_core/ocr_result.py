"""Immutable OCR domain types — framework-independent.

No Django, Flask, network, or external-OCR dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
import math


class ContractError(ValueError):
    """Base error for a rejected contract operation."""


class UnalignedOutputError(ContractError):
    """Raised when OCR engine returns mismatched boxes/txts/scores counts."""

    def __init__(self, boxes: int | None, txts: int | None, scores: int | None) -> None:
        self.boxes = boxes
        self.txts = txts
        self.scores = scores
        super().__init__(
            f"RapidOCR output misalignment: "
            f"boxes={boxes!r}, txts={txts!r}, scores={scores!r}; "
            f"all must be equal when present"
        )


class UnlocatedTextError(ContractError):
    """Raised when OCR engine returns text with no corresponding bounding boxes."""

    def __init__(self, txts_count: int, boxes_count: int | None) -> None:
        self.txts_count = txts_count
        self.boxes_count = boxes_count
        super().__init__(
            f"RapidOCR returned {txts_count} text(s) but {boxes_count!r} box(es); "
            f"text requires coordinates; either provide boxes or drop text"
        )


@runtime_checkable
class OcrEngineAdapter(Protocol):
    """Protocol for OCR engine adapters."""

    def process(self, image_bytes: bytes) -> OcrResult:
        """Run OCR on image bytes; returns OcrResult."""
        ...


@dataclass(frozen=True, slots=True)
class OcrRegion:
    """Single detected region from one OCR pass.

    Attributes:
        located: True when polygon contains real engine-reported coordinates;
                 False when text was returned without geometry (polygon is None).
    """

    region_id: str
    source_page: int
    polygon: tuple[tuple[int, int], ...] | None
    text: str
    confidence: float
    located: bool
    transform: str = "none"

    def __post_init__(self) -> None:
        if self.located:
            if self.polygon is None:
                raise ValueError("polygon cannot be None when located=True")
            if len(self.polygon) != 4:
                raise ValueError("polygon must be a 4-point tuple of (x, y) pairs when located")
            for point in self.polygon:
                if len(point) != 2:
                    raise ValueError(f"each polygon point must be (x, y); got {point!r}")
        elif self.polygon is not None:
            raise ValueError("polygon must be None when located=False (unlocated text)")


@dataclass(frozen=True, slots=True)
class OcrResult:
    """Normalized OCR result from an engine adapter.

    All vendor-specific output is converted to this application-owned type.
    RapidOCR native output uses np.ndarray boxes, tuple txts/scores, and
    elapsed time in seconds. This type normalizes those to application types.
    """

    regions: tuple[OcrRegion, ...]
    elapse_ms: int
    engine: str
    engine_version: str
    source_image_hash: str

    @property
    def boxes(self) -> list[list[list[int]] | None]:
        """Bounding boxes as nested lists; None for unlocated regions."""
        return [
            [[int(p[0]), int(p[1])] for p in r.polygon] if r.located else None
            for r in self.regions
        ]

    @property
    def txts(self) -> list[str]:
        """Recognized text strings."""
        return [r.text for r in self.regions]

    @property
    def scores(self) -> list[float]:
        """Confidence scores per region."""
        return [r.confidence for r in self.regions]

    @property
    def is_empty(self) -> bool:
        return len(self.regions) == 0


def _normalize_box(box: Any) -> tuple[tuple[int, int], ...]:
    """Normalize a vendor box (np.ndarray, list, tuple) to a 4-point tuple."""
    if box is None:
        raise ValueError("box cannot be None")

    if hasattr(box, "tolist"):
        box = box.tolist()

    if len(box) == 0:
        raise ValueError("box is empty")

    normalized = []
    for point in box:
        if hasattr(point, "tolist"):
            point = point.tolist()
        if len(point) != 2:
            raise ValueError(f"point {point!r} must have at least x, y")
        normalized.append((int(point[0]), int(point[1])))
    return tuple(normalized)


def _normalize_txts(txts: Any) -> tuple[str, ...]:
    """Normalize txts (tuple, list, None) to tuple of strings."""
    if txts is None:
        return ()
    if hasattr(txts, "tolist"):
        txts = txts.tolist()
    if isinstance(txts, (list, tuple)):
        return tuple(str(t) for t in txts)
    return (str(txts),)


def _normalize_scores(scores: Any) -> tuple[float, ...]:
    """Normalize scores (tuple, list, None) to tuple of floats."""
    if scores is None:
        return ()
    if hasattr(scores, "tolist"):
        scores = scores.tolist()
    if isinstance(scores, (list, tuple)):
        return tuple(float(s) for s in scores)
    return (float(scores),)


def _to_elapse_ms(elapse: Any) -> int:
    """Convert elapsed seconds (or ms) to milliseconds as int.

    RapidOCR 3.9.x reports elapse in seconds (float).
    Treat int/float elapse as seconds and convert to ms.
    """
    if elapse is None:
        return 0
    value = float(elapse)
    if not math.isfinite(value) or value < 0:
        raise ContractError("INVALID_ELAPSED_TIME")
    return round(value * 1000)
