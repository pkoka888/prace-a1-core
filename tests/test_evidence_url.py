"""Adversarial, network-free tests for the Plan AC URL verifier."""
from __future__ import annotations

import importlib.util
import json
import urllib.error
from email.message import Message

from _research_tmp import REPO, build_tmp_root, load, processed, run_script, write_input


def _module():
    spec = importlib.util.spec_from_file_location("urlcheck", REPO / "scripts/check_evidence_url.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _public_dns(host, port, type=None):
    return [(2, 1, 6, "", ("93.184.216.34", port))]


class Response:
    def __init__(self, status, location=None):
        self.status = status
        self.headers = Message()
        if location:
            self.headers["Location"] = location

    def getcode(self):
        return self.status

    def close(self):
        pass


class Opener:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request.full_url, request.get_method(), timeout))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_inventory_deduplicates_and_retains_references():
    mod = _module()
    env = load(REPO / "tests/fixtures/research/envelope_partial.json")
    rows = mod.inventory_urls(env)
    pricing = next(row for row in rows if row["url"] == "https://fakturoid.cz/cenik")
    assert {r["field"] for r in pricing["references"]} == {"pricing_url", "canonical_url"}
    assert len([r for r in rows if r["url"] == pricing["url"]]) == 1


def test_literal_private_and_credentials_are_denied():
    mod = _module()
    for url in ("http://127.0.0.1/x", "http://169.254.169.254/", "http://[::1]/",
                "https://user:secret@example.com/"):
        try:
            mod.validate_target(url, _public_dns)
        except mod.UnsafeURL:
            pass
        else:
            raise AssertionError(f"unsafe URL accepted: {url}")


def test_any_private_dns_answer_denies_host():
    mod = _module()

    def mixed(host, port, type=None):
        return [(2, 1, 6, "", ("93.184.216.34", port)),
                (2, 1, 6, "", ("10.0.0.7", port))]

    result = mod.check_live("https://example.com", 1, resolver=mixed,
                            opener=Opener([Response(200)]))
    assert result["verdict"] == "invalid"


def test_redirect_target_is_validated_before_request():
    mod = _module()
    opener = Opener([Response(302, "http://127.0.0.1/admin")])
    result = mod.check_live("https://example.com", 1, resolver=_public_dns, opener=opener)
    assert result["verdict"] == "invalid"
    assert [r[0] for r in opener.requests] == ["https://example.com"]


def test_head_falls_back_to_get_without_reading_body():
    mod = _module()
    headers = Message()
    err = urllib.error.HTTPError("https://example.com", 405, "no head", headers, None)
    opener = Opener([err, Response(204)])
    result = mod.check_live("https://example.com", 1, resolver=_public_dns, opener=opener)
    assert result["verdict"] == "verified"
    assert [r[1] for r in opener.requests] == ["HEAD", "GET"]


def test_invalid_envelope_fails_before_output(tmp_path):
    root = build_tmp_root(tmp_path)
    env = load(REPO / "tests/fixtures/research/envelope_partial.json")
    env["entities"][0]["source_links"] = ["file:///etc/passwd"]
    write_input(root, env)
    output = processed(root) / "checks.json"
    result = run_script(root, "check_evidence_url.py", "--output", str(output))
    assert result.returncode == 1
    assert not output.exists()


def test_output_must_be_explicit_and_contained(tmp_path):
    root = build_tmp_root(tmp_path)
    write_input(root, load(REPO / "tests/fixtures/research/envelope_empty.json"))
    assert run_script(root, "check_evidence_url.py").returncode != 0
    outside = __import__("pathlib").Path("/var/tmp/plan-ac-forbidden-output.json")
    result = run_script(root, "check_evidence_url.py", "--output", str(outside))
    assert result.returncode == 1
    assert not outside.exists()


def test_empty_valid_envelope_is_vacuously_verified(tmp_path):
    root = build_tmp_root(tmp_path)
    write_input(root, load(REPO / "tests/fixtures/research/envelope_empty.json"))
    output = processed(root) / "checks.json"
    result = run_script(root, "check_evidence_url.py", "--output", str(output))
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())["summary"] == {
        "verified": 0, "unproven": 0, "invalid": 0,
    }
