"""Offline document intake. Only synthetic inputs until real-data gates pass."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .ocr_result import ContractError, UnalignedOutputError, UnlocatedTextError
from .serialization import atomic_write, canonical_json, content_hash, result_hash
from .pipeline import DocumentProcessor

# Kept as an importable boundary for focused failure-injection tests.
_atomic_write = atomic_write


def error_tag(exc):
    if isinstance(exc, UnalignedOutputError):
        return "OCR_OUTPUT_MISALIGNED"
    if isinstance(exc, UnlocatedTextError):
        return "OCR_UNLOCATED_TEXT"
    if isinstance(exc, FileNotFoundError):
        return "INPUT_NOT_FOUND"
    if isinstance(exc, PermissionError):
        return "ACCESS_DENIED"
    if isinstance(exc, ContractError):
        tag = str(exc)
        return tag if tag.isupper() and tag.replace("_", "").isalnum() else "INVALID_OCR_OUTPUT"
    return "DOCUMENT_PROCESSING_FAILED"


def process_files(input_paths, output_dir, worker_id=None, processor=None):
    document_id = str(uuid4())
    directory = Path(output_dir) / document_id
    try:
        directory.mkdir(parents=True, mode=0o700)
    except OSError:
        print("OUTPUT_NOT_WRITABLE", file=sys.stderr)
        return 1
    processor = processor or DocumentProcessor()
    documents, sources, failures = [], [], []
    def store_artifact(digest, data):
        target = directory / (digest + ".png")
        # Binary PNGs use the same atomic publication discipline as JSON.
        from .serialization import atomic_bytes
        atomic_bytes(target, data)
    for index, input_path in enumerate(input_paths):
        digest = ""
        try:
            data = Path(input_path).read_bytes()
            digest = content_hash(data)
            from .serialization import atomic_bytes
            atomic_bytes(directory / (digest + ".source"), data)
            result = processor.process(data, artifact_sink=store_artifact)
            documents.extend(result["documents"])
            sources.append({"input_index": index, "input_hash": digest, "status": "completed"})
        except Exception as exc:
            tag = error_tag(exc)
            failures.append({"input_index": index, "input_hash": digest, "error_tag": tag, "status": "failed", "output_hash": ""})
    semantic = processor.combine(documents)
    payload = {"document_id": document_id, "worker_id": worker_id,
               "association_status": "requested_unverified" if worker_id else "unassigned",
               "status": "failed" if failures and not documents else "partial" if failures else "completed",
               "error_tag": failures[0]["error_tag"] if failures else None,
               "sources": sources, "failures": failures, "timestamp": datetime.now(timezone.utc).isoformat(),
               **semantic, "result_hash": result_hash(semantic),
               "input_hash": sources[0]["input_hash"] if sources else (failures[0]["input_hash"] if failures else ""),
               "output_hash": "", "segmentation": "evaluated" if documents else "not_evaluated",
               "classification": "evaluated" if documents else "not_evaluated",
               "completeness": "evaluated" if documents else "not_evaluated", "provenance": []}
    if documents:
        # Compatibility summary for the single-image CLI; full evidence is per-document.
        first = documents[0]
        payload.update(ocr=first["ocr"], output_hash=result_hash(first["ocr"]),
                       engine_version=first["ocr"]["engine_version"], provenance=first["provenance"])
    try:
        _atomic_write(directory / "result.json", canonical_json(payload))
    except OSError:
        print("RESULT_WRITE_FAILED", file=sys.stderr)
        return 1
    if failures:
        print(failures[0]["error_tag"], file=sys.stderr)
    return 1 if failures else 0


def process_document(input_path, output_dir, worker_id=None):
    return process_files([input_path], output_dir, worker_id)


def main():
    parser = argparse.ArgumentParser(description="Offline document intake: images, multi-page TIFF and PDF.")
    parser.add_argument("--input", required=True, type=Path, nargs="+")
    parser.add_argument("--worker-id", default=None, help="Requested worker context; never confirms an association")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return process_files(args.input, args.output, args.worker_id)


if __name__ == "__main__":
    raise SystemExit(main())
