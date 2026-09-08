"""Local engine boundary; vendor data never escapes the normalized result."""
from hashlib import sha256
from importlib.metadata import version
from uuid import uuid4
from pathlib import Path
import rapidocr
import math
from rapidocr import RapidOCR
from ..ocr_result import (
    ContractError, OcrRegion, OcrResult, UnalignedOutputError, UnlocatedTextError,
    _normalize_box, _normalize_scores, _normalize_txts, _to_elapse_ms,
)


def _engine_version():
    return version("rapidocr")


class RapidOCRAdapter:
    def __init__(self):
        model_dir = Path(rapidocr.__file__).parent / "models"
        models = {"Det": "PP-OCRv6_det_small.onnx", "Rec": "PP-OCRv6_rec_small.onnx", "Cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx"}
        paths = {f"{kind}.model_path": str(model_dir / name) for kind, name in models.items()}
        if not all(Path(path).is_file() for path in paths.values()):
            raise ContractError("LOCAL_OCR_MODEL_MISSING")
        paths.update({"EngineConfig.onnxruntime.intra_op_num_threads": 1, "EngineConfig.onnxruntime.inter_op_num_threads": 1})
        self._engine = RapidOCR(params=paths)
        self._engine_version = _engine_version()

    def process(self, image_bytes):
        return _convert_rapidocr_output(self._engine(image_bytes), image_bytes, self._engine_version)


def _convert_rapidocr_output(raw, image_bytes, engine_version):
    boxes = getattr(raw, "boxes", None)
    txts = _normalize_txts(getattr(raw, "txts", None))
    scores = _normalize_scores(getattr(raw, "scores", None))
    count = len(boxes) if boxes is not None else 0
    if txts and not count:
        raise UnlocatedTextError(len(txts), None if boxes is None else count)
    if count != len(txts) or count != len(scores):
        raise UnalignedOutputError(count, len(txts), len(scores))
    regions = []
    for box, text, score in zip(boxes if count else (), txts, scores, strict=True):
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ContractError("INVALID_CONFIDENCE")
        regions.append(OcrRegion(
            region_id=str(uuid4()), source_page=0, polygon=_normalize_box(box),
            text=text, confidence=score, located=True,
        ))
    return OcrResult(
        regions=tuple(regions), elapse_ms=_to_elapse_ms(getattr(raw, "elapse", None)),
        engine="rapidocr", engine_version=engine_version,
        source_image_hash=sha256(image_bytes).hexdigest(),
    )
