"""Optional offline Tesseract adapter. Never selected implicitly by intake."""
import csv
from hashlib import sha256
from io import StringIO
import math
import shutil
import subprocess
import time
from uuid import uuid4

from ..ocr_result import ContractError, OcrRegion, OcrResult


class TesseractAdapter:
    def __init__(self, *, timeout_seconds=30):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120:
            raise ValueError("INVALID_TIMEOUT")
        self.timeout_seconds = timeout_seconds
        self.binary = shutil.which("tesseract")
        if not self.binary:
            raise ContractError("TESSERACT_UNAVAILABLE")
        self.engine_version = self._call(["--version"]).decode().splitlines()[0]
        languages = self._call(["--list-langs"]).decode().splitlines()
        if not {"ces", "deu", "eng"}.issubset(languages):
            raise ContractError("TESSERACT_LANGUAGES_MISSING")

    def _call(self, arguments, content=None):
        # No paths, credentials or inherited provider configuration passed to engine.
        environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "OMP_THREAD_LIMIT": "1"}
        try:
            result = subprocess.run([self.binary, *arguments], input=content,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=self.timeout_seconds, check=True, env=environment)
        except subprocess.TimeoutExpired:
            raise ContractError("TESSERACT_TIMEOUT") from None
        except (OSError, subprocess.CalledProcessError):
            raise ContractError("TESSERACT_FAILED") from None
        return result.stdout

    def process(self, image_bytes):
        started = time.monotonic()
        raw = self._call(["stdin", "stdout", "-l", "ces+deu+eng", "--psm", "6", "tsv"], image_bytes)
        regions = []
        try:
            reader = csv.DictReader(StringIO(raw.decode("utf-8")), delimiter="\t")
            if not {"text", "left", "top", "width", "height", "conf"}.issubset(reader.fieldnames or ()):
                raise ValueError()
            for row in reader:
                text = row["text"].strip()
                if not text:
                    continue
                x, y, w, h = (int(row[key]) for key in ("left", "top", "width", "height"))
                score = float(row["conf"]) / 100
                if min(x, y) < 0 or min(w, h) <= 0 or not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError()
                regions.append(OcrRegion(str(uuid4()), 0, ((x,y), (x+w,y), (x+w,y+h), (x,y+h)), text, score, True))
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise ContractError("TESSERACT_OUTPUT_INVALID") from None
        return OcrResult(tuple(regions), round((time.monotonic()-started)*1000), "tesseract",
                         self.engine_version, sha256(image_bytes).hexdigest())
