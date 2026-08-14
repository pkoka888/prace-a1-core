"""Network-free tests for the bounded Plan AC source capture boundary."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from email.message import Message
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/capture_research_sources.py"
SCHEMA = REPO / "research/query-packs/source-capture-1.0.schema.json"
RESULT_SCHEMA = REPO / "research/query-packs/source-capture-result-1.0.schema.json"
SCHEMA_V11 = REPO / "research/query-packs/source-capture-1.1.schema.json"
RESULT_SCHEMA_V11 = REPO / "research/query-packs/source-capture-result-1.1.schema.json"
PACK = REPO / "research/query-packs/plan-ac-core-1.1.json"
PACK_HASH = "69ea1e988271dafaaea0ea84cc75e6eac8ad7c884ec4f66212ce57a3a68a3819"
SOURCE_URL = "https://github.com/docling-project/docling"
FINAL_URL = "https://github.com/docling-project/docling/blob/main/README.md"
TARGET = {"entity_id": "oss-docling", "field_id": "local_execution"}


def setup_root(tmp_path: Path, requests: list[dict] | None = None):
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    (root / "research/query-packs").mkdir(parents=True)
    (root / "research/acquisition/requests").mkdir(parents=True)
    (root / "tests/fixtures/capture").mkdir(parents=True)
    (root / "scripts/capture_research_sources.py").write_bytes(SCRIPT.read_bytes())
    (root / "research/query-packs/source-capture-1.0.schema.json").write_bytes(SCHEMA.read_bytes())
    (root / "research/query-packs/source-capture-result-1.0.schema.json").write_bytes(RESULT_SCHEMA.read_bytes())
    (root / "research/query-packs/source-capture-1.1.schema.json").write_bytes(SCHEMA_V11.read_bytes())
    (root / "research/query-packs/source-capture-result-1.1.schema.json").write_bytes(RESULT_SCHEMA_V11.read_bytes())
    (root / "research/query-packs/plan-ac-core-1.1.json").write_bytes(PACK.read_bytes())
    payload = {"schema_version": "source-capture-1.1", "run_id": "run-1",
               "query_pack_version": "1.1.0", "query_pack_hash": PACK_HASH,
               "requests": requests or [{"id": "page", "url": SOURCE_URL,
                                           "field_targets": [TARGET],
                                           "method": "GET", "excerpt": {
                                               "selector": "term-window", "terms": ["public"],
                                               "max_chars": 20}}]}
    request = root / "research/acquisition/requests/run-1.json"
    request.write_text(json.dumps(payload), encoding="utf-8")
    return root, request, root / "tests/fixtures/capture", root / "research/acquisition/source-captures/run-1"


def fixture(directory: Path, *, final=FINAL_URL, chain=None, body="Hello   public world"):
    chain = chain if chain is not None else [{"status": 302, "from": SOURCE_URL, "to": final}]
    value = {"requested_url": SOURCE_URL, "final_url": final,
             "redirect_chain": chain, "http_status": 200,
             "retrieved_at": "2026-08-14T10:00:00Z", "content_type": "text/html; charset=utf-8",
             "body_text": f"<html><script>secret()</script><body>{body}</body></html>"}
    (directory / "page.json").write_text(json.dumps(value), encoding="utf-8")


def run(root, request, fixtures, output, *extra):
    input_arg = (str(request.relative_to(root)) if request.is_absolute() and root in request.parents
                 else str(request))
    return subprocess.run([sys.executable, str(root / "scripts/capture_research_sources.py"),
                           "--root", str(root), "--input", input_arg, "--output", str(output),
                           "--fixture-dir", str(fixtures), *extra], text=True, capture_output=True)


def module():
    spec = importlib.util.spec_from_file_location("capture", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_capture_is_bounded_bound_and_byte_current(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    result = run(root, request, fixtures, output)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((output / "manifest.json").read_text())
    row = manifest["results"][0]
    assert row["requested_url"] == SOURCE_URL
    assert row["final_url"] == FINAL_URL
    assert row["field_targets"] == [TARGET]
    assert row["http_status"] == 200 and row["content_type"] == "text/html"
    assert len(row["response_sha256"]) == len(row["excerpt"]["sha256"]) == 64
    assert row["excerpt"]["span"] == [0, 18]
    assert row["excerpt"]["terms"] == row["excerpt"]["matched_terms"] == ["public"]
    assert (output / row["excerpt"]["path"]).read_text() == "Hello public world\n"
    assert run(root, request, fixtures, output, "--check").returncode == 0
    (output / "excerpts/page.txt").write_text("tampered\n")
    assert run(root, request, fixtures, output, "--check").returncode == 1


def test_cli_live_capture_is_fail_closed_before_network(tmp_path):
    root, request, _fixtures, output = setup_root(tmp_path)
    result = subprocess.run(
        [sys.executable, str(root / "scripts/capture_research_sources.py"),
         "--root", str(root), "--input", str(request.relative_to(root)),
         "--output", str(output), "--live"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2
    assert "Integrity 1.3" in result.stderr
    assert not output.exists()


def test_existing_output_and_canonical_processed_are_never_overwritten(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    output.mkdir(parents=True)
    sentinel = output / "keep"
    sentinel.write_text("x")
    assert run(root, request, fixtures, output).returncode == 1
    assert sentinel.read_text() == "x"
    forbidden = root / "research/processed/run-1"
    result = run(root, request, fixtures, forbidden)
    assert result.returncode == 1 and not forbidden.exists()


def test_missing_fixture_is_unproven_and_manifest_is_written(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    result = run(root, request, fixtures, output)
    assert result.returncode == 2
    assert json.loads((output / "manifest.json").read_text())["summary"]["unproven"] == 1


def test_fixture_body_obeys_same_size_limit(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures, body="too long")
    result = run(root, request, fixtures, output, "--max-bytes", "3")
    assert result.returncode == 2
    assert not (output / "excerpts/page.txt").exists()


def test_fixture_child_symlink_is_denied_without_following(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    target = root / "tests/fixtures/real-page.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    fixture(fixtures)
    (fixtures / "page.json").replace(target)
    (fixtures / "page.json").symlink_to(target)
    result = run(root, request, fixtures, output)
    assert result.returncode == 1
    assert json.loads((output / "manifest.json").read_text())["results"][0]["state"] == "invalid"


def test_request_rejects_credentials_private_urls_duplicate_ids_and_head_excerpt(tmp_path):
    bad_sets = [
        [{"id": "x", "url": "https://u:p@example.org", "method": "GET", "field_targets": [TARGET]}],
        [{"id": "x", "url": "https://127.0.0.1", "method": "GET", "field_targets": [TARGET]}],
        [{"id": "x", "url": SOURCE_URL, "method": "GET", "field_targets": [TARGET]},
         {"id": "x", "url": SOURCE_URL + "/x", "method": "GET", "field_targets": [TARGET]}],
        [{"id": "x", "url": SOURCE_URL, "method": "HEAD", "field_targets": [TARGET],
          "excerpt": {"selector": "term-window", "terms": ["term"], "max_chars": 20}}],
    ]
    for index, requests in enumerate(bad_sets):
        root, request, fixtures, output = setup_root(tmp_path / str(index), requests)
        assert run(root, request, fixtures, output).returncode == 1
        assert not output.exists()


def test_non_global_shared_address_is_denied():
    mod = module()
    try:
        mod.validate_public_https("https://100.64.0.1/x", public_dns)
    except mod.UnsafeCapture:
        pass
    else:
        raise AssertionError("non-global shared address was accepted")


def test_fixture_redirect_to_private_target_is_invalid(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures, final="https://127.0.0.1/x")
    result = run(root, request, fixtures, output)
    assert result.returncode == 1
    assert json.loads((output / "manifest.json").read_text())["results"][0]["state"] == "invalid"


def test_paths_must_be_contained_and_private_roots_denied(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    outside = tmp_path / "outside.json"
    outside.write_text(request.read_text())
    assert run(root, outside, fixtures, output).returncode == 1
    absolute_inside = subprocess.run(
        [sys.executable, str(root / "scripts/capture_research_sources.py"), "--root", str(root),
         "--input", str(request), "--output", str(output), "--fixture-dir", str(fixtures)],
        text=True, capture_output=True)
    assert absolute_inside.returncode == 1
    private = root / "a1/request.json"
    private.parent.mkdir()
    private.write_text(request.read_text())
    assert run(root, private, fixtures, output).returncode == 1
    for relative in (Path(".env"), Path("employees/scans/request.json"),
                     Path("runtime/portal/request.json")):
        sensitive = root / relative
        sensitive.parent.mkdir(parents=True, exist_ok=True)
        sensitive.write_text(request.read_text())
        assert run(root, sensitive, fixtures, output).returncode == 1


class Response:
    def __init__(self, status=200, body=b"hello", content_type="text/plain", location=None):
        self._status, self._body = status, body
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if location:
            self.headers["Location"] = location
    def getcode(self): return self._status
    def read(self, amount): return self._body[:amount]
    def close(self): pass


class Opener:
    def __init__(self, values): self.values, self.requests = iter(values), []
    def open(self, request, timeout):
        self.requests.append((request.full_url, request.method))
        return next(self.values)


def public_dns(host, port, type=None):
    return [(2, 1, 6, "", ("93.184.216.34", port))]


def test_live_get_bounded_and_redirect_target_checked_without_network():
    mod = module()
    opener = Opener([Response(302, location="https://example.org/b"), Response(body=b"hello")])
    item = {"id": "x", "url": "https://example.org/a", "method": "GET",
            "excerpt": {"claim_target": "greeting", "selector": "term-window",
                        "terms": ["hello"], "max_chars": 20}}
    row, excerpt = mod.capture_live(item, 1, 5, 2, resolver=public_dns, opener=opener)
    assert row["final_url"] == "https://example.org/b" and excerpt == b"hello\n"
    assert opener.requests == [("https://example.org/a", "GET"), ("https://example.org/b", "GET")]
    bad = Opener([Response(302, location="https://169.254.169.254/latest")])
    try:
        mod.capture_live(item, 1, 5, 2, resolver=public_dns, opener=bad)
    except mod.UnsafeCapture:
        pass
    else:
        raise AssertionError("private redirect target was accepted")


def test_live_size_and_type_limits_are_unproven_without_network():
    mod = module()
    item = {"id": "x", "url": "https://example.org/a", "method": "GET"}
    for response in (Response(body=b"123456"), Response(body=b"x", content_type="application/pdf")):
        try:
            mod.capture_live(item, 1, 5, 0, resolver=public_dns, opener=Opener([response]))
        except mod.UnprovenCapture:
            pass
        else:
            raise AssertionError("bounded response violation was accepted")


def test_missing_claim_term_is_unproven_and_no_excerpt_is_published(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures, body="unrelated words only")
    result = run(root, request, fixtures, output)
    assert result.returncode == 2
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["results"][0]["state"] == "unproven"
    assert not (output / "excerpts/page.txt").exists()


def test_generated_manifest_validates_against_result_schema(tmp_path):
    from jsonschema import Draft7Validator, FormatChecker
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    assert run(root, request, fixtures, output).returncode == 0
    schema = json.loads(RESULT_SCHEMA_V11.read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    assert list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(manifest)) == []


def test_exact_field_ownership_blocks_same_entity_cross_field_laundering(tmp_path):
    invalid_target = {"entity_id": "oss-docling", "field_id": "received_invoice_extraction"}
    request_item = {"id": "page", "url": SOURCE_URL, "method": "GET",
                    "field_targets": [invalid_target],
                    "excerpt": {"selector": "term-window", "terms": ["public"], "max_chars": 20}}
    root, request, fixtures, output = setup_root(tmp_path, [request_item])
    fixture(fixtures)
    result = run(root, request, fixtures, output)
    assert result.returncode == 1 and not output.exists()


def test_result_preserves_only_explicit_targets_and_supports_multiple_fields(tmp_path):
    targets = [TARGET, {"entity_id": "oss-docling", "field_id": "license_spdx"}]
    request_item = {"id": "page", "url": SOURCE_URL, "method": "GET",
                    "field_targets": targets,
                    "excerpt": {"selector": "term-window", "terms": ["public"], "max_chars": 20}}
    root, request, fixtures, output = setup_root(tmp_path, [request_item])
    fixture(fixtures)
    assert run(root, request, fixtures, output).returncode == 0
    row = json.loads((output / "manifest.json").read_text())["results"][0]
    assert row["field_targets"] == targets
    assert {tuple(target.values()) for target in row["field_targets"]} == {
        ("oss-docling", "local_execution"), ("oss-docling", "license_spdx")}


def test_source_root_must_belong_to_every_target_entity(tmp_path):
    targets = [TARGET, {"entity_id": "vendor-idoklad", "field_id": "public_api"}]
    request_item = {"id": "page", "url": SOURCE_URL, "method": "GET",
                    "field_targets": targets,
                    "excerpt": {"selector": "term-window", "terms": ["public"], "max_chars": 20}}
    root, request, fixtures, output = setup_root(tmp_path, [request_item])
    fixture(fixtures)
    assert run(root, request, fixtures, output).returncode == 1
    assert not output.exists()


def test_allowed_root_rejects_prefix_confusion_and_path_traversal():
    mod = module()
    root = "https://github.com/docling-project/docling"
    assert mod._url_belongs_to_root(root + "/blob/main/README.md", root)
    assert not mod._url_belongs_to_root(root + "-evil/readme", root)
    assert not mod._url_belongs_to_root(root + "/../other/repo", root)
    assert not mod._url_belongs_to_root(root + "/%2e%2e/other", root)


def test_historical_v10_can_be_checked_but_not_newly_published(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    historical = {
        "schema_version": "source-capture-1.0", "run_id": "run-1",
        "requests": [{"id": "page", "url": SOURCE_URL, "method": "GET",
                      "excerpt": {"claim_target": "historical proof",
                                  "selector": "term-window", "terms": ["public"],
                                  "max_chars": 20}}],
    }
    request.write_text(json.dumps(historical), encoding="utf-8")
    fixture(fixtures)
    assert run(root, request, fixtures, output).returncode == 1
    mod = module()
    loaded = mod.load_request(root, request, allow_historical=True)
    manifest, excerpts, _ = mod.build_capture(loaded, mode="fixture", fixture_dir=fixtures,
                                               timeout=1, max_bytes=1000, max_redirects=2, root=root)
    mod.validate_result(root, manifest, loaded)
    mod.publish_atomic(root, output, mod.expected_files(manifest, excerpts), loaded)
    assert run(root, request, fixtures, output, "--check").returncode == 0


def test_result_validator_rejects_mutated_field_ownership(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    assert run(root, request, fixtures, output).returncode == 0
    mod = module()
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["results"][0]["field_targets"][0]["field_id"] = "license_spdx"
    loaded = mod.load_request(root, request)
    try:
        mod.validate_result(root, manifest, loaded)
    except mod.UnsafeCapture:
        pass
    else:
        raise AssertionError("mutated field ownership was accepted")


def test_result_request_binding_and_capture_semantics_reject_mutations(tmp_path):
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    assert run(root, request, fixtures, output).returncode == 0
    mod = module()
    original = json.loads((output / "manifest.json").read_text())
    loaded = mod.load_request(root, request)
    mutations = []
    for mutate in (
        lambda value: value.__setitem__("request_sha256", "0" * 64),
        lambda value: value["results"][0].__setitem__("requested_method", "HEAD"),
        lambda value: value["results"][0].__setitem__("performed_methods", ["GET"]),
        lambda value: value["results"][0]["excerpt"].__setitem__("selector", "wrong"),
        lambda value: value["results"][0]["excerpt"].__setitem__("terms", ["other"]),
        lambda value: value["results"][0]["redirect_chain"][0].__setitem__("from", FINAL_URL),
        lambda value: value["results"][0].__setitem__("final_url", SOURCE_URL),
    ):
        candidate = json.loads(json.dumps(original))
        mutate(candidate)
        mutations.append(candidate)
    for candidate in mutations:
        try:
            mod.validate_result(root, candidate, loaded)
        except mod.UnsafeCapture:
            pass
        else:
            raise AssertionError("mutated result semantics were accepted")


def test_atomic_publish_cleans_staging_if_rename_is_interrupted(tmp_path, monkeypatch):
    mod = module()
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    request_data = mod.load_request(root, request)
    manifest, excerpts, _ = mod.build_capture(request_data, mode="fixture", fixture_dir=fixtures,
                                               timeout=1, max_bytes=1000, max_redirects=2, root=root)
    files = mod.expected_files(manifest, excerpts)
    def fail_rename(source, destination):
        raise OSError("simulated interruption")
    monkeypatch.setattr(mod, "rename_noreplace", fail_rename)
    try:
        mod.publish_atomic(root, output, files, request_data)
    except OSError:
        pass
    else:
        raise AssertionError("simulated interruption did not propagate")
    assert not output.exists()
    assert list(output.parent.glob(".run-1.staging-*")) == []


def test_atomic_publish_race_refuses_without_overwrite(tmp_path, monkeypatch):
    mod = module()
    root, request, fixtures, output = setup_root(tmp_path)
    fixture(fixtures)
    request_data = mod.load_request(root, request)
    manifest, excerpts, _ = mod.build_capture(request_data, mode="fixture", fixture_dir=fixtures,
                                               timeout=1, max_bytes=1000, max_redirects=2, root=root)
    files = mod.expected_files(manifest, excerpts)
    def raced(source, destination):
        destination.mkdir()
        (destination / "sentinel").write_text("other publisher")
        raise mod.UnsafeCapture("capture output appeared during publication; refusing overwrite")
    monkeypatch.setattr(mod, "rename_noreplace", raced)
    try:
        mod.publish_atomic(root, output, files, request_data)
    except mod.UnsafeCapture:
        pass
    else:
        raise AssertionError("destination race was not refused")
    assert (output / "sentinel").read_text() == "other publisher"
    assert list(output.parent.glob(".run-1.staging-*")) == []
