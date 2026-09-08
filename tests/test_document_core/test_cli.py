"""Tests for document_core.cli — offline CLI functionality."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parent.parent.parent / "src"


class TestCLIHelp:
    def test_help_works_without_network(self):
        """--help exits 0 and works without network; no network required."""
        env = {"PYTHONPATH": str(SRC_ROOT)}
        result = subprocess.run(
            [sys.executable, "-m", "document_core", "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert "input" in result.stdout.lower()
        assert "output" in result.stdout.lower()
        assert "worker-id" in result.stdout.lower()


class TestCLIFunctional:
    def _make_synthetic_png(self, lines: list[str]) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            pytest.skip("Pillow not available")

        img = Image.new("RGB", (600, 300), color="white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
            )
        except Exception:
            font = ImageFont.load_default()
        y = 20
        for line in lines:
            draw.text((20, y), line, fill="black", font=font)
            y += 35

        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _run_cli(self, input_path: Path, output_dir: Path, worker_id: str | None = None) -> subprocess.CompletedProcess:
        env = {"PYTHONPATH": str(SRC_ROOT)}
        cmd = [sys.executable, "-m", "document_core", "--input", str(input_path), "--output", str(output_dir)]
        if worker_id is not None:
            cmd.extend(["--worker-id", worker_id])
        return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)

    def _recompute_output_hash(self, ocr_dict: dict) -> str:
        return hashlib.sha256(json.dumps(ocr_dict, sort_keys=True, indent=2).encode()).hexdigest()

    def test_processes_synthetic_image(self):
        """CLI processes a synthetic image and writes structured JSON output."""
        img_bytes = self._make_synthetic_png(["OP/CR/CZ", "Novakova"])

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.png"
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            input_path.write_bytes(img_bytes)

            result = self._run_cli(input_path, output_dir)

            assert result.returncode == 0, f"stderr: {result.stderr}"

            subdirs = list(output_dir.iterdir())
            assert len(subdirs) == 1
            result_file = subdirs[0] / "result.json"
            assert result_file.exists()

            data = json.loads(result_file.read_text())
            assert data["status"] == "completed"
            assert "document_id" in data
            assert "worker_id" in data
            assert data["worker_id"] is None
            assert "ocr" in data
            assert "provenance" in data
            assert "segmentation" in data
            assert "classification" in data
            assert "completeness" in data
            assert data["segmentation"] == "evaluated"
            assert data["classification"] == "evaluated"
            assert "engine_version" in data
            assert "input_hash" in data

    def test_missing_input_file_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            result = self._run_cli(Path(tmpdir) / "nonexistent.png", output_dir)
            assert result.returncode != 0

    def test_worker_id_optional(self):
        """Worker ID is optional; unassigned intake is valid."""
        img_bytes = self._make_synthetic_png(["OP/CR/CZ"])

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.png"
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            input_path.write_bytes(img_bytes)

            result = self._run_cli(input_path, output_dir, worker_id="worker-42")

            assert result.returncode == 0
            subdirs = list(output_dir.iterdir())
            data = json.loads((subdirs[0] / "result.json").read_text())
            assert data["worker_id"] == "worker-42"

    def test_provenance_hash_integrity(self):
        """Provenance output_hash is independently recomputable from OCR JSON."""
        img_bytes = self._make_synthetic_png(["OP/CR/CZ"])

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.png"
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            input_path.write_bytes(img_bytes)

            self._run_cli(input_path, output_dir)

            subdirs = list(output_dir.iterdir())
            data = json.loads((subdirs[0] / "result.json").read_text())

            prov_entries = data["provenance"]
            assert len(prov_entries) >= 1
            for entry in prov_entries:
                assert "input_hash" in entry
                assert "output_hash" in entry
                assert "operation" in entry
                assert len(entry["input_hash"]) == 64

            first_entry = prov_entries[0]
            assert first_entry["operation"] == "crop"
            assert any(e["operation"] == "ocr_original" for e in prov_entries)

            ocr_json = json.dumps(data["ocr"], sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            recomputed = hashlib.sha256(ocr_json.encode()).hexdigest()
            assert data["output_hash"] == recomputed

    def test_unassigned_worker_accepted(self):
        """No worker ID means worker_id is None; unassigned intake is valid."""
        img_bytes = self._make_synthetic_png(["OP/CR/CZ"])

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.png"
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            input_path.write_bytes(img_bytes)

            result = self._run_cli(input_path, output_dir)

            assert result.returncode == 0
            subdirs = list(output_dir.iterdir())
            data = json.loads((subdirs[0] / "result.json").read_text())
            assert data["worker_id"] is None
            assert data["status"] == "completed"

    def test_error_messages_do_not_leak_paths(self):
        """Failed OCR does not expose input paths in stdout/stderr."""
        img_bytes = self._make_synthetic_png(["OP/CR/CZ"])

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.png"
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            input_path.write_bytes(img_bytes)

            result = self._run_cli(input_path, output_dir)

            assert result.returncode == 0
            assert str(input_path) not in result.stderr
            assert str(input_path) not in result.stdout

    def test_failure_result_has_error_tag(self):
        """Failed OCR writes structured failure with error_tag; no raw exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            result = self._run_cli(Path(tmpdir) / "nonexistent.png", output_dir)

            assert result.returncode != 0
            subdirs = list(output_dir.iterdir())
            assert len(subdirs) == 1
            data = json.loads((subdirs[0] / "result.json").read_text())
            assert data["status"] == "failed"
            assert "error_tag" in data
            assert data["error_tag"] == "INPUT_NOT_FOUND"

    def test_output_hash_absent_when_ocr_failed(self):
        """Failed OCR has empty output_hash; failure_tag is recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()
            result = self._run_cli(Path(tmpdir) / "nonexistent.png", output_dir)

            assert result.returncode != 0
            subdirs = list(output_dir.iterdir())
            assert len(subdirs) == 1
            data = json.loads((subdirs[0] / "result.json").read_text())
            assert data["status"] == "failed"
            assert data["output_hash"] == ""
