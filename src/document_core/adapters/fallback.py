"""Explicit opt-in, two-attempt local comparison/fallback; never confirms fields.

Factories initialize engines inside disposable Linux processes. This runner is
CLI-only (single Python thread), not wired into portal intake; callers must persist its review-required outcome.
"""
from dataclasses import dataclass
import math
import multiprocessing
import os
import signal
import selectors
import pickle
import threading
import time

from ..ocr_result import ContractError, OcrResult


@dataclass(frozen=True)
class Attempt:
    engine: str
    reason: str
    elapsed_ms: int


@dataclass(frozen=True)
class FallbackOutcome:
    result: OcrResult | None
    attempts: tuple[Attempt, ...]
    review_required: bool = True
    status: str = "proposal"


MAX_RESULT_BYTES = 8 * 1024 * 1024


def _execute(read_fd, write_fd, factory, content):
    os.close(read_fd)
    os.setsid()  # Timeout cleanup includes native-engine descendants.
    try:
        data = pickle.dumps(factory().process(content))
        if len(data) > MAX_RESULT_BYTES:
            return
        while data:
            count = os.write(write_fd, data)
            data = data[count:]
    except Exception:
        pass  # Never transport engine exceptions or document text in errors.
    finally:
        os.close(write_fd)


class LocalFallbackAdapter:
    def __init__(self, primary, secondary, *, timeout_seconds=30, confidence_floor=.7):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120:
            raise ValueError("INVALID_TIMEOUT")
        if not 0 <= confidence_floor <= 1:
            raise ValueError("INVALID_CONFIDENCE")
        self.factories = (primary, secondary)
        self.timeout_seconds = timeout_seconds
        self.confidence_floor = confidence_floor

    def process_with_evidence(self, image_bytes):
        if threading.current_thread() is not threading.main_thread() or threading.active_count() != 1:
            raise ContractError("LOCAL_FALLBACK_CLI_ONLY")
        attempts, last = [], None
        for name, factory in self.factories:
            started = time.monotonic()
            deadline = started + self.timeout_seconds
            context = multiprocessing.get_context("fork")
            read_fd, write_fd = os.pipe()
            os.set_blocking(read_fd, False)
            process = context.Process(target=_execute, args=(read_fd, write_fd, factory, image_bytes))
            process.start()
            os.close(write_fd)
            result, reason, payload = None, "engine_failed", bytearray()
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(read_fd, selectors.EVENT_READ)
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0 or not selector.select(remaining):
                            reason = "timeout"
                            break
                        chunk = os.read(read_fd, 65536)
                        if not chunk:
                            if payload:
                                try:
                                    result = pickle.loads(payload)  # Trusted local child only.
                                except Exception:
                                    pass
                            break
                        payload.extend(chunk)
                        if len(payload) > MAX_RESULT_BYTES:
                            reason = "result_limit"
                            break
            finally:
                os.close(read_fd)
                # Kill remaining native descendants even if the Python child exited.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    if process.is_alive():
                        process.kill()
                process.join()
                process.close()
            if isinstance(result, OcrResult):
                last = result
                reason = "proposal" if result.regions and min(result.scores) >= self.confidence_floor else "low_quality"
            attempts.append(Attempt(name, reason, round((time.monotonic()-started)*1000)))
            if reason == "proposal":
                return FallbackOutcome(result, tuple(attempts))
        return FallbackOutcome(last, tuple(attempts), status="review_required" if last else "failed")

    def process(self, image_bytes):
        outcome = self.process_with_evidence(image_bytes)
        if outcome.result is None:
            raise ContractError("LOCAL_OCR_ATTEMPTS_EXHAUSTED")
        return outcome.result
