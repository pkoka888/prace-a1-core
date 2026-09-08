"""Bounded decoding and document-boundary detection, before OCR fields."""
from dataclasses import dataclass
from io import BytesIO
import warnings
import numpy as np
import cv2
from PIL import Image, ImageOps, ImageEnhance
from .ocr_result import ContractError

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 20
MAX_PIXELS = 20_000_000
MAX_TOTAL_PIXELS = 60_000_000


@dataclass
class Page:
    index: int
    image: Image.Image


@dataclass
class Crop:
    page: int
    image: Image.Image
    polygon: list
    to_page: np.ndarray
    confidence: float
    reason: str


def png_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def decode_pages(content):
    if not content or len(content) > MAX_BYTES:
        raise ContractError("INPUT_SIZE_INVALID")
    pages = []
    total = 0
    try:
        if content.startswith(b"%PDF-"):
            import pymupdf as fitz
            with fitz.open(stream=content, filetype="pdf") as pdf:
                if pdf.needs_pass:
                    raise ContractError("PDF_ENCRYPTED")
                if not 0 < len(pdf) <= MAX_PAGES:
                    raise ContractError("PAGE_LIMIT")
                for i, page in enumerate(pdf):
                    width, height = page.rect.width * 2, page.rect.height * 2
                    total += int(width * height)
                    if width * height > MAX_PIXELS or total > MAX_TOTAL_PIXELS:
                        raise ContractError("PIXEL_LIMIT")
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False, colorspace=fitz.csRGB)
                    pages.append(Page(i, Image.frombytes("RGB", (pix.width, pix.height), pix.samples)))
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as source:
                    if source.format not in {"PNG", "JPEG", "TIFF"}:
                        raise ContractError("UNSUPPORTED_IMAGE")
                    if source.n_frames > MAX_PAGES:
                        raise ContractError("PAGE_LIMIT")
                    for i in range(source.n_frames):
                        source.seek(i)
                        pixels = source.width * source.height
                        total += pixels
                        if pixels > MAX_PIXELS or total > MAX_TOTAL_PIXELS:
                            raise ContractError("PIXEL_LIMIT")
                        pages.append(Page(i, ImageOps.exif_transpose(source).convert("RGB")))
    except ContractError:
        raise
    except Exception:
        raise ContractError("INPUT_DECODE_FAILED") from None
    return pages


class Segmenter:
    """Detect isolated quadrilateral documents; ambiguous pages stay whole.

    No text/filename heuristics. Overlapping/occluded cards require a clearer input.
    """
    def segment(self, page):
        image = np.asarray(page.image)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 40, 120)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = page.image.width * page.image.height
        polygons = []
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, .025 * perimeter, True)
            a = abs(cv2.contourArea(approx))
            if len(approx) == 4 and cv2.isContourConvex(approx) and .06 * area <= a <= .98 * area:
                polygons.append(approx.reshape(4, 2).astype(np.float32))
        if not polygons:
            w, h = page.image.size
            return [Crop(page.index, page.image, [[0, 0], [w, 0], [w, h], [0, h]],
                         np.eye(3), .4, "whole_page_boundary_unconfirmed")]
        crops = []
        for points in sorted(polygons, key=lambda p: (float(p[:, 1].min()), float(p[:, 0].min()))):
            # TL, TR, BR, BL; preserve projective mapping for field evidence.
            sums, diffs = points.sum(axis=1), np.diff(points, axis=1).ravel()
            ordered = np.array([points[sums.argmin()], points[diffs.argmin()],
                                points[sums.argmax()], points[diffs.argmax()]], dtype=np.float32)
            if len(np.unique(ordered, axis=0)) != 4:
                continue
            tl, tr, br, bl = ordered
            w = max(2, round(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl))))
            h = max(2, round(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr))))
            target = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
            mapping = cv2.getPerspectiveTransform(ordered, target)
            crop = cv2.warpPerspective(image, mapping, (w, h))
            crops.append(Crop(page.index, Image.fromarray(crop), ordered.tolist(),
                              np.linalg.inv(mapping), .85, "quadrilateral_boundary"))
        if not crops:
            w, h = page.image.size
            return [Crop(page.index, page.image, [[0,0],[w,0],[w,h],[0,h]], np.eye(3), .4,
                         "whole_page_boundary_unconfirmed")]
        return crops


def enhanced(image):
    # Same pixel dimensions: deterministic contrast; geometry already normalized.
    return ImageEnhance.Contrast(ImageOps.autocontrast(image.convert("RGB"))).enhance(1.25)


def page_polygon(polygon, transform):
    points = cv2.perspectiveTransform(np.array([polygon], dtype=np.float32), transform)[0]
    return [[round(float(x), 2), round(float(y), 2)] for x, y in points]
