import time
import pytest
from src.document_core.adapters.fallback import LocalFallbackAdapter
from src.document_core.ocr_result import OcrResult, OcrRegion, ContractError


class Good:
    def process(self, content):
        return OcrResult((OcrRegion("synthetic", 0, ((0,0),(1,0),(1,1),(0,1)), "TEST", .95, True),), 1, "fake", "1", "hash")


class Bad:
    def __init__(self):
        raise RuntimeError("private path must not be logged")


class Slow:
    def process(self, content):
        time.sleep(10)


class Low:
    def process(self, content):
        return OcrResult((), 1, "fake", "1", "hash")


def test_unavailable_primary_uses_fallback_as_proposal():
    result = LocalFallbackAdapter(("primary", Bad), ("secondary", Good)).process_with_evidence(b"synthetic")
    assert [a.reason for a in result.attempts] == ["engine_failed", "proposal"]
    assert result.review_required and result.status == "proposal"


def test_fallback_failure_is_bounded_and_sanitized():
    adapter = LocalFallbackAdapter(("primary", Bad), ("secondary", Bad))
    result = adapter.process_with_evidence(b"synthetic")
    assert result.result is None and result.status == "failed" and len(result.attempts) == 2
    with pytest.raises(ContractError, match="ATTEMPTS_EXHAUSTED"):
        adapter.process(b"synthetic")


def test_timeout_kills_primary_then_attempts_secondary():
    started = time.monotonic()
    result = LocalFallbackAdapter(("primary", Slow), ("secondary", Good), timeout_seconds=.1).process_with_evidence(b"synthetic")
    assert time.monotonic()-started < 3
    assert result.attempts[0].reason == "timeout" and result.attempts[1].reason == "proposal"


def test_low_quality_remains_review_required():
    result = LocalFallbackAdapter(("primary", Low), ("secondary", Low)).process_with_evidence(b"synthetic")
    assert result.status == "review_required" and result.review_required
    assert [a.reason for a in result.attempts] == ["low_quality", "low_quality"]


def test_good_primary_does_not_call_secondary():
    result = LocalFallbackAdapter(("primary", Good), ("secondary", Bad)).process_with_evidence(b"synthetic")
    assert len(result.attempts) == 1 and result.review_required


def test_partial_ipc_write_cannot_bypass_deadline(monkeypatch):
    import os
    import src.document_core.adapters.fallback as module
    def stalled(read_fd, write_fd, factory, content):
        os.close(read_fd)
        os.setsid()
        os.write(write_fd, b"partial result")
        time.sleep(10)
    monkeypatch.setattr(module, "_execute", stalled)
    started = time.monotonic()
    result = LocalFallbackAdapter(("primary", Good), ("secondary", Good), timeout_seconds=.1).process_with_evidence(b"synthetic")
    assert time.monotonic()-started < 3
    assert [a.reason for a in result.attempts] == ["timeout", "timeout"]


def test_threaded_caller_is_rejected():
    from concurrent.futures import ThreadPoolExecutor
    adapter = LocalFallbackAdapter(("primary", Good), ("secondary", Good))
    with ThreadPoolExecutor(1) as pool:
        with pytest.raises(ContractError, match="CLI_ONLY"):
            pool.submit(adapter.process_with_evidence, b"synthetic").result()
