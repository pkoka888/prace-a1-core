"""One serialization/hash contract for CLI and protected web derivatives."""
import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def content_hash(data):
    return hashlib.sha256(data).hexdigest()


def result_hash(value):
    return content_hash(canonical_json(value).encode("utf-8"))


def ocr_dict(result):
    return {**asdict(result), "region_count": len(result.regions), "is_empty": result.is_empty}


def atomic_bytes(path: Path, data: bytes):
    """Same-directory replacement; complete buffered write, single descriptor owner."""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".result-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def atomic_write(path: Path, text: str):
    atomic_bytes(path, text.encode("utf-8"))
