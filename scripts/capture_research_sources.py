#!/usr/bin/env python3
"""Capture bounded, public research sources into an immutable run directory.

Fixture mode is deterministic and is the default. Live mode performs explicit
HEAD or bounded GET requests. Exit codes: 0=captured, 1=invalid/unsafe,
2=unproven (missing fixture, network, response, or environment limitation).
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import html.parser
import ipaddress
import json
import os
import shutil
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from urllib.parse import urljoin, urlsplit

from jsonschema import Draft7Validator, FormatChecker

REQUEST_SCHEMAS = {
    "source-capture-1.0": Path("research/query-packs/source-capture-1.0.schema.json"),
    "source-capture-1.1": Path("research/query-packs/source-capture-1.1.schema.json"),
}
RESULT_SCHEMAS = {
    "source-capture-result-1.0": Path("research/query-packs/source-capture-result-1.0.schema.json"),
    "source-capture-result-1.1": Path("research/query-packs/source-capture-result-1.1.schema.json"),
}
QUERY_PACK_REL = Path("research/query-packs/plan-ac-core-1.1.json")
CAPTURE_REL = Path("research/acquisition/source-captures")
DENIED_TOP_LEVEL = {
    "a1", "scans", "evidence", "ocr", "data", "output", "runtime",
    "secrets", ".history-remediation",
}
ALLOWED_TYPES = {
    "text/html", "text/plain", "application/json", "application/xhtml+xml",
}
REDIRECTS = {301, 302, 303, 307, 308}
DENIED_SUFFIXES = (
    ".localhost", ".local", ".internal", ".home.arpa", ".test",
    ".invalid", ".example", ".onion",
)
MAX_BYTES_LIMIT = 2_000_000
DEFAULT_MAX_BYTES = 500_000


class UnsafeCapture(ValueError):
    pass


class UnprovenCapture(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact_hash_without(value: dict, key: str) -> str:
    payload = {name: content for name, content in value.items() if name != key}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode()
    return sha256(encoded)


def _sensitive_relative(relative: Path) -> bool:
    parts = relative.parts
    if not parts:
        return True
    if parts[0] in DENIED_TOP_LEVEL or parts[0] == ".env" or parts[0].startswith(".env."):
        return True
    return len(parts) >= 2 and parts[0] == "employees" and parts[1] == "scans"


def contained(root: Path, value: str, *, output: bool = False,
              relative_only: bool = False) -> Path:
    root = root.resolve()
    path = Path(value)
    if relative_only and path.is_absolute():
        raise UnsafeCapture("input path must be relative to --root")
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if path == root or root not in path.parents:
        raise UnsafeCapture("path must be contained under --root")
    relative = path.relative_to(root)
    if _sensitive_relative(relative):
        raise UnsafeCapture("private or runtime project paths are denied")
    if output:
        base = (root / CAPTURE_REL).resolve()
        if path == base or base not in path.parents:
            raise UnsafeCapture(f"output must be a run directory below {CAPTURE_REL}")
        if (root / "research/processed").resolve() in (path, *path.parents):
            raise UnsafeCapture("canonical processed output is denied")
    return path


def _public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value.split("%", 1)[0])
    return ip.is_global and not ip.is_multicast


def validate_public_https(url: str, resolver=socket.getaddrinfo) -> list[str]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise UnsafeCapture(f"malformed URL: {exc}") from exc
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise UnsafeCapture("only public HTTPS URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeCapture("URL credentials are denied")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(DENIED_SUFFIXES):
        raise UnsafeCapture("local or special-use hostname is denied")
    try:
        literal = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if not _public_ip(str(literal)):
            raise UnsafeCapture("non-public literal address is denied")
        return [str(literal)]
    if "." not in host or not any(c.isalpha() for c in host):
        raise UnsafeCapture("host must be a public DNS name")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeCapture("invalid IDNA hostname") from exc
    if any(not label or len(label) > 63 or label.startswith("-") or
           label.endswith("-") or not all(c.isalnum() or c == "-" for c in label)
           for label in ascii_host.split(".")):
        raise UnsafeCapture("invalid public DNS hostname")
    try:
        answers = resolver(host, port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UnprovenCapture(f"DNS resolution failed: {exc}") from exc
    ips = sorted({answer[4][0].split("%", 1)[0] for answer in answers})
    if not ips:
        raise UnprovenCapture("DNS returned no addresses")
    try:
        unsafe = [ip for ip in ips if not _public_ip(ip)]
    except ValueError as exc:
        raise UnprovenCapture("DNS returned an invalid address") from exc
    if unsafe:
        raise UnsafeCapture(f"DNS returned denied address {unsafe[0]}")
    return ips


class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self.suppressed += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "template"} and self.suppressed:
            self.suppressed -= 1

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(data)


def normalized_text(body: bytes, content_type: str) -> str:
    text = body.decode("utf-8", errors="replace")
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = TextExtractor()
        parser.feed(text)
        text = " ".join(parser.parts)
    elif content_type == "application/json":
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, sort_keys=True)
        except json.JSONDecodeError as exc:
            raise UnprovenCapture(f"invalid JSON response: {exc}") from exc
    return " ".join(text.split())


def targeted_excerpt(text: str, spec: dict) -> tuple[str, list[int], list[str], bool]:
    """Return a bounded window that contains every requested claim term."""
    folded = text.casefold()
    matches = []
    for term in spec["terms"]:
        position = folded.find(term.casefold())
        if position < 0:
            raise UnprovenCapture(f"claim-target term not found: {term}")
        matches.append((position, position + len(term), term))
    target_start = min(item[0] for item in matches)
    target_end = max(item[1] for item in matches)
    if target_end - target_start > spec["max_chars"]:
        raise UnprovenCapture("claim-target terms do not fit bounded excerpt")
    spare = spec["max_chars"] - (target_end - target_start)
    start = max(0, target_start - spare // 2)
    end = min(len(text), start + spec["max_chars"])
    start = max(0, end - spec["max_chars"])
    excerpt = text[start:end]
    return excerpt, [start, end], [item[2] for item in matches], start > 0 or end < len(text)


def _url_belongs_to_root(url: str, root_url: str) -> bool:
    candidate, allowed = urlsplit(url), urlsplit(root_url)
    if (candidate.scheme.lower(), candidate.hostname, candidate.port) != (
            allowed.scheme.lower(), allowed.hostname, allowed.port):
        return False
    allowed_path = allowed.path or "/"
    candidate_path = candidate.path or "/"
    # Refuse path encodings or traversal syntax whose server-side
    # normalization could escape an apparently matching allowlisted prefix.
    if "%" in candidate_path or "\\" in candidate_path or any(
            segment in {"", ".", ".."} for segment in candidate_path.split("/")[1:-1]):
        return False
    if allowed_path.endswith("/"):
        return candidate_path.startswith(allowed_path)
    return candidate_path == allowed_path or candidate_path.startswith(allowed_path + "/")


def query_pack_index(root: Path) -> tuple[dict, dict[str, dict]]:
    try:
        pack = json.loads((root / QUERY_PACK_REL).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnsafeCapture(f"cannot load final query pack: {exc}") from exc
    if pack.get("query_pack_version") != "1.1.0" or compact_hash_without(pack, "query_pack_hash") != pack.get("query_pack_hash"):
        raise UnsafeCapture("final query pack version/hash is invalid")
    index = {}
    for lane in pack.get("lanes", {}).values():
        fields = {field["id"] for field in lane.get("fields", [])}
        for entity in lane.get("entities", []):
            if entity["id"] in index:
                raise UnsafeCapture("duplicate entity in final query pack")
            index[entity["id"]] = {"fields": fields,
                                    "roots": entity["allowed_official_source_roots"]}
    return pack, index


def validate_field_targets(root: Path, item: dict, url: str) -> None:
    if "field_targets" not in item:  # Historical v1.0 check only.
        return
    _, index = query_pack_index(root)
    for target in item["field_targets"]:
        entity = index.get(target["entity_id"])
        if entity is None:
            raise UnsafeCapture(f"unknown target entity: {target['entity_id']}")
        if target["field_id"] not in entity["fields"]:
            raise UnsafeCapture(f"field does not belong to target entity lane: {target['entity_id']}:{target['field_id']}")
        if not any(_url_belongs_to_root(url, allowed) for allowed in entity["roots"]):
            raise UnsafeCapture(f"URL is outside allowed roots for target entity: {target['entity_id']}")


def _response_record(item: dict, *, status: int, final_url: str, chain: list,
                     retrieved_at: str, content_type: str | None, body: bytes,
                     methods: list[str]) -> tuple[dict, bytes | None]:
    record = {
        "id": item["id"], "requested_url": item["url"], "final_url": final_url,
        "redirect_chain": chain, "requested_method": item["method"],
        "performed_methods": methods, "http_status": status,
        "retrieved_at": retrieved_at, "content_type": content_type,
        "response_sha256": sha256(body), "response_bytes": len(body),
        "state": "captured", "reason": None, "excerpt": None,
    }
    if "field_targets" in item:
        record["field_targets"] = item["field_targets"]
    excerpt_bytes = None
    if item["method"] == "GET" and item.get("excerpt"):
        if content_type not in ALLOWED_TYPES:
            raise UnprovenCapture(f"unsupported content type: {content_type}")
        full = normalized_text(body, content_type)
        excerpt, span, matched, truncated = targeted_excerpt(full, item["excerpt"])
        excerpt_bytes = (excerpt + "\n").encode()
        record["excerpt"] = {
            "selector": item["excerpt"]["selector"], "terms": item["excerpt"]["terms"],
            "matched_terms": matched, "span": span,
            "sha256": sha256(excerpt_bytes), "characters": len(excerpt),
            "truncated": truncated,
            "path": f"excerpts/{item['id']}.txt",
        }
        if "field_targets" not in item:
            record["excerpt"]["claim_target"] = item["excerpt"]["claim_target"]
    return record, excerpt_bytes


def resolve_fixture_child(root: Path, fixture_dir: Path, item_id: str) -> Path:
    root, fixture_dir = root.resolve(), fixture_dir.resolve()
    try:
        fixture_relative = fixture_dir.relative_to(root)
    except ValueError as exc:
        raise UnsafeCapture("fixture directory escapes project root") from exc
    if _sensitive_relative(fixture_relative) or not fixture_dir.is_dir():
        raise UnsafeCapture("fixture directory is unavailable or sensitive")
    unresolved = fixture_dir / f"{item_id}.json"
    if unresolved.is_symlink():
        raise UnsafeCapture("fixture child must not be a symbolic link")
    path = unresolved.resolve()
    try:
        path.relative_to(fixture_dir)
        relative = path.relative_to(root)
    except ValueError as exc:
        raise UnsafeCapture("fixture child escapes its contained directory") from exc
    if _sensitive_relative(relative):
        raise UnsafeCapture("fixture child resolves to a sensitive path")
    if not path.is_file() or path.is_symlink():
        raise UnprovenCapture(f"missing regular fixture {path.name}")
    return path


def capture_fixture(item: dict, fixture_dir: Path, max_bytes: int,
                    root: Path | None = None) -> tuple[dict, bytes | None]:
    if root is None:
        raise UnsafeCapture("fixture capture requires an explicit project root")
    path = resolve_fixture_child(root, fixture_dir, item["id"])
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnsafeCapture(f"invalid fixture {path.name}: {exc}") from exc
    required = {"requested_url", "final_url", "redirect_chain", "http_status",
                "retrieved_at", "content_type", "body_text"}
    if set(fixture) != required or fixture["requested_url"] != item["url"]:
        raise UnsafeCapture(f"fixture {path.name} has invalid shape or URL binding")
    chain = fixture["redirect_chain"]
    if not isinstance(chain, list) or len(chain) > 5:
        raise UnsafeCapture("fixture redirect chain is invalid")
    expected = item["url"]
    for hop in chain:
        if set(hop) != {"status", "from", "to"} or hop["status"] not in REDIRECTS or hop["from"] != expected:
            raise UnsafeCapture("fixture redirect chain is discontinuous")
        validate_public_https(hop["from"], _fixture_dns)
        validate_public_https(hop["to"], _fixture_dns)
        if root is not None:
            validate_field_targets(root, item, hop["from"])
            validate_field_targets(root, item, hop["to"])
        expected = hop["to"]
    if expected != fixture["final_url"]:
        raise UnsafeCapture("fixture final URL does not match redirect chain")
    validate_public_https(fixture["final_url"], _fixture_dns)
    if root is not None:
        validate_field_targets(root, item, fixture["final_url"])
    if not isinstance(fixture["http_status"], int) or not 200 <= fixture["http_status"] < 400:
        raise UnprovenCapture("fixture HTTP status is not successful")
    try:
        datetime.fromisoformat(fixture["retrieved_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise UnsafeCapture("fixture retrieval timestamp is invalid") from exc
    ctype = fixture["content_type"].split(";", 1)[0].strip().lower()
    body = fixture["body_text"].encode()
    if len(body) > max_bytes:
        raise UnprovenCapture("fixture response exceeds byte limit")
    return _response_record(item, status=fixture["http_status"],
                            final_url=fixture["final_url"], chain=chain,
                            retrieved_at=fixture["retrieved_at"], content_type=ctype,
                            body=body, methods=[item["method"]] * (len(chain) + 1))


def _fixture_dns(host, port, type=None):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def capture_live(item: dict, timeout: float, max_bytes: int, max_redirects: int,
                 resolver=socket.getaddrinfo, opener=None,
                 root: Path | None = None) -> tuple[dict, bytes | None]:
    network_opener = opener is None
    opener = opener or urllib.request.build_opener(NoRedirect)
    current, chain, methods = item["url"], [], []
    method = item["method"]

    def guarded(*args, **kwargs):
        answers = resolver(*args, **kwargs)
        for answer in answers:
            if not _public_ip(answer[4][0]):
                raise UnsafeCapture("connection-time DNS returned denied address")
        return answers

    for _ in range(max_redirects + 1):
        validate_public_https(current, resolver)
        if root is not None:
            validate_field_targets(root, item, current)
        request = urllib.request.Request(current, method=method,
                                         headers={"User-Agent": "plan-ac-source-capture/1.0"})
        methods.append(method)
        try:
            guard = mock.patch("socket.getaddrinfo", side_effect=guarded) if network_opener else nullcontext()
            with guard:
                response = opener.open(request, timeout=timeout)
            status, headers = response.getcode(), response.headers
        except urllib.error.HTTPError as exc:
            response, status, headers = exc, exc.code, exc.headers
        except UnsafeCapture:
            raise
        except (OSError, urllib.error.URLError) as exc:
            raise UnprovenCapture(f"network request failed: {exc}") from exc
        if status in REDIRECTS:
            location = headers.get("Location")
            response.close()
            if not location:
                raise UnsafeCapture("redirect is missing Location")
            target = urljoin(current, location)
            validate_public_https(target, resolver)
            if root is not None:
                validate_field_targets(root, item, target)
            chain.append({"status": status, "from": current, "to": target})
            if len(chain) > max_redirects:
                raise UnprovenCapture("redirect limit exceeded")
            current = target
            continue
        ctype = (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower() or None
        length = headers.get("Content-Length")
        if length:
            try:
                if int(length) > max_bytes:
                    response.close()
                    raise UnprovenCapture("response exceeds byte limit")
            except ValueError as exc:
                response.close()
                raise UnprovenCapture("invalid Content-Length") from exc
        if method == "GET":
            if ctype not in ALLOWED_TYPES:
                response.close()
                raise UnprovenCapture(f"unsupported content type: {ctype}")
            body = response.read(max_bytes + 1)
            response.close()
            if len(body) > max_bytes:
                raise UnprovenCapture("response exceeds byte limit")
        else:
            body = b""
            response.close()
        if not 200 <= status < 400:
            raise UnprovenCapture(f"HTTP status {status}")
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return _response_record(item, status=status, final_url=current, chain=chain,
                                retrieved_at=timestamp, content_type=ctype, body=body,
                                methods=methods)
    raise UnprovenCapture("redirect limit exceeded")


def load_request(root: Path, input_path: Path, *, allow_historical: bool = False) -> dict:
    try:
        request = json.loads(input_path.read_text(encoding="utf-8"))
        version = request.get("schema_version") if isinstance(request, dict) else None
        schema_path = REQUEST_SCHEMAS.get(version)
        if schema_path is None:
            raise UnsafeCapture("unsupported source capture request version")
        if version == "source-capture-1.0" and not allow_historical:
            raise UnsafeCapture("v1.0 is historical and may only be used with --check")
        schema = json.loads((root / schema_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnsafeCapture(f"cannot load request/schema: {exc}") from exc
    errors = sorted(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(request),
                    key=lambda e: list(e.absolute_path))
    if errors:
        err = errors[0]
        raise UnsafeCapture(f"request schema error at {list(err.absolute_path)}: {err.message}")
    ids = [item["id"] for item in request["requests"]]
    if len(ids) != len(set(ids)):
        raise UnsafeCapture("request IDs must be unique")
    if version == "source-capture-1.1":
        pack, _ = query_pack_index(root)
        if request["query_pack_version"] != pack["query_pack_version"] or request["query_pack_hash"] != pack["query_pack_hash"]:
            raise UnsafeCapture("capture request is not bound to the final query pack")
    for item in request["requests"]:
        validate_public_https(item["url"], _fixture_dns)
        validate_field_targets(root, item, item["url"])
    return request


def validate_result(root: Path, manifest: dict, request: dict | None = None) -> None:
    try:
        schema_path = RESULT_SCHEMAS.get(manifest.get("schema_version"))
        if schema_path is None:
            raise UnsafeCapture("unsupported source capture result version")
        schema = json.loads((root / schema_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnsafeCapture(f"cannot load result schema: {exc}") from exc
    errors = sorted(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(manifest),
                    key=lambda e: list(e.absolute_path))
    if errors:
        err = errors[0]
        raise UnsafeCapture(f"result schema error at {list(err.absolute_path)}: {err.message}")
    counts = {state: sum(row["state"] == state for row in manifest["results"])
              for state in ("captured", "unproven", "invalid")}
    if manifest["summary"] != counts:
        raise UnsafeCapture("result summary does not match results")
    ids = [row["id"] for row in manifest["results"]]
    if len(ids) != len(set(ids)):
        raise UnsafeCapture("result IDs must be unique")
    if manifest["schema_version"] == "source-capture-result-1.1":
        pack, _ = query_pack_index(root)
        if (manifest["query_pack_version"], manifest["query_pack_hash"]) != (
                pack["query_pack_version"], pack["query_pack_hash"]):
            raise UnsafeCapture("capture result is not bound to the final query pack")
    for row in manifest["results"]:
        if "field_targets" in row:
            validate_field_targets(root, row, row["requested_url"])
            if row["state"] == "captured":
                validate_field_targets(root, row, row["final_url"])
        if row["state"] == "captured":
            if row["requested_method"] == "GET" and row["excerpt"] is None:
                raise UnsafeCapture("captured GET result must have a targeted excerpt")
            if row["requested_method"] == "HEAD" and row["excerpt"] is not None:
                raise UnsafeCapture("captured HEAD result must not have an excerpt")
    if request is not None:
        if manifest["request_sha256"] != sha256(canonical_bytes(request)):
            raise UnsafeCapture("capture result request hash differs from canonical request bytes")
        requested = {item["id"]: item for item in request["requests"]}
        if set(requested) != set(ids):
            raise UnsafeCapture("capture result IDs differ from request IDs")
        for row in manifest["results"]:
            item = requested[row["id"]]
            if row["requested_url"] != item["url"] or row.get("field_targets") != item.get("field_targets"):
                raise UnsafeCapture("capture result ownership differs from request")
            if row["state"] != "captured":
                continue
            if row["requested_method"] != item["method"]:
                raise UnsafeCapture("capture result requested method differs from request")
            chain = row["redirect_chain"]
            expected_url = item["url"]
            for hop in chain:
                if (set(hop) != {"status", "from", "to"} or hop["status"] not in REDIRECTS
                        or hop["from"] != expected_url):
                    raise UnsafeCapture("capture redirect chain is malformed or discontinuous")
                validate_public_https(hop["from"], _fixture_dns)
                validate_public_https(hop["to"], _fixture_dns)
                validate_field_targets(root, item, hop["from"])
                validate_field_targets(root, item, hop["to"])
                expected_url = hop["to"]
            if expected_url != row["final_url"]:
                raise UnsafeCapture("capture final URL differs from redirect chain")
            validate_public_https(row["final_url"], _fixture_dns)
            validate_field_targets(root, item, row["final_url"])
            if row["performed_methods"] != [item["method"]] * (len(chain) + 1):
                raise UnsafeCapture("performed method sequence differs from request/redirect semantics")
            if item["method"] == "GET":
                expected_excerpt = item["excerpt"]
                excerpt = row["excerpt"]
                if (excerpt is None or excerpt["selector"] != expected_excerpt["selector"]
                        or excerpt["terms"] != expected_excerpt["terms"]
                        or excerpt["matched_terms"] != expected_excerpt["terms"]
                        or excerpt["characters"] > expected_excerpt["max_chars"]):
                    raise UnsafeCapture("GET excerpt semantics differ from request")


def build_capture(request: dict, *, mode: str, fixture_dir: Path | None,
                  timeout: float, max_bytes: int, max_redirects: int,
                  root: Path | None = None) -> tuple[dict, dict[str, bytes], int]:
    records, excerpts, exit_code = [], {}, 0
    for item in request["requests"]:
        try:
            record, excerpt = (capture_fixture(item, fixture_dir, max_bytes, root) if mode == "fixture"
                               else capture_live(item, timeout, max_bytes, max_redirects, root=root))
            if excerpt is not None:
                excerpts[item["id"]] = excerpt
        except UnsafeCapture as exc:
            record = {"id": item["id"], "requested_url": item["url"],
                      "state": "invalid", "reason": str(exc)}
            exit_code = 1
        except UnprovenCapture as exc:
            record = {"id": item["id"], "requested_url": item["url"],
                      "state": "unproven", "reason": str(exc)}
            if exit_code == 0:
                exit_code = 2
        records.append(record)
        if "field_targets" in item:
            record["field_targets"] = item["field_targets"]
    is_v11 = request["schema_version"] == "source-capture-1.1"
    manifest = {
        "schema_version": "source-capture-result-1.1" if is_v11 else "source-capture-result-1.0",
        "run_id": request["run_id"],
        "mode": mode, "request_sha256": sha256(canonical_bytes(request)),
        "results": records,
        "summary": {state: sum(r["state"] == state for r in records)
                    for state in ("captured", "unproven", "invalid")},
    }
    if is_v11:
        manifest["query_pack_version"] = request["query_pack_version"]
        manifest["query_pack_hash"] = request["query_pack_hash"]
    return manifest, excerpts, exit_code


def expected_files(manifest: dict, excerpts: dict[str, bytes]) -> dict[Path, bytes]:
    files = {Path("manifest.json"): canonical_bytes(manifest)}
    files.update({Path("excerpts") / f"{key}.txt": value for key, value in excerpts.items()})
    return files


def validate_staged_capture(root: Path, staging: Path, expected: dict[Path, bytes],
                            request: dict | None = None) -> None:
    actual = {path.relative_to(staging): path.read_bytes()
              for path in staging.rglob("*") if path.is_file()}
    if actual != expected:
        raise UnsafeCapture("staged capture differs from expected bytes")
    try:
        manifest = json.loads(actual[Path("manifest.json")])
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UnsafeCapture(f"staged manifest is invalid: {exc}") from exc
    validate_result(root, manifest, request)
    referenced = set()
    for row in manifest["results"]:
        excerpt = row.get("excerpt")
        if not excerpt:
            continue
        path = Path(excerpt["path"])
        referenced.add(path)
        content = actual.get(path)
        if content is None or sha256(content) != excerpt["sha256"]:
            raise UnsafeCapture(f"staged excerpt hash mismatch: {path}")
    present = {path for path in actual if path.parts and path.parts[0] == "excerpts"}
    if present != referenced:
        raise UnsafeCapture("staged excerpts contain missing or orphaned files")


def rename_noreplace(source: Path, destination: Path) -> None:
    """Atomically publish a directory while refusing an existing destination."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise UnprovenCapture("atomic exclusive publish is unavailable on this platform")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                          ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise UnsafeCapture("capture output appeared during publication; refusing overwrite")
    if error in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
        raise UnprovenCapture("atomic exclusive publish is unavailable on this filesystem")
    raise OSError(error, os.strerror(error), str(destination))


def publish_atomic(root: Path, output: Path, files: dict[Path, bytes],
                   request: dict | None = None) -> None:
    """Write a complete sibling staging tree and atomically publish it."""
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        for relative, content in files.items():
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        validate_staged_capture(root, staging, files, request)
        rename_noreplace(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Safely capture bounded public research sources")
    parser.add_argument("--root", default=".")
    parser.add_argument("--input", required=True, help="Contained JSON request manifest")
    parser.add_argument("--output", required=True, help="Contained run output directory")
    parser.add_argument("--fixture-dir", help="Contained fixture directory (default mode)")
    parser.add_argument("--live", action="store_true", help="Perform live HTTPS requests")
    parser.add_argument("--check", action="store_true", help="Verify byte parity; fixture mode only")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-redirects", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        input_path = contained(root, args.input, relative_only=True)
        output = contained(root, args.output, output=True)
        fixture_dir = contained(root, args.fixture_dir) if args.fixture_dir else None
        if args.live:
            raise UnprovenCapture(
                "live capture is blocked until Capture/Proposal Integrity 1.3 "
                "and its synthetic replay/review gates pass"
            )
        if args.live and fixture_dir:
            raise UnsafeCapture("choose live or fixture mode, not both")
        if not args.live and fixture_dir is None:
            raise UnsafeCapture("fixture mode requires --fixture-dir")
        if args.check and args.live:
            raise UnprovenCapture("--check is deterministic fixture mode only")
        if not 0 < args.timeout <= 30 or not 1 <= args.max_bytes <= MAX_BYTES_LIMIT or not 0 <= args.max_redirects <= 5:
            raise UnsafeCapture("limits outside allowed bounds")
        request = load_request(root, input_path, allow_historical=args.check)
        if output.name != request["run_id"]:
            raise UnsafeCapture("output directory name must equal run_id")
        if input_path == output or output in input_path.parents:
            raise UnsafeCapture("output must not overlap input")
        manifest, excerpts, exit_code = build_capture(
            request, mode="live" if args.live else "fixture", fixture_dir=fixture_dir,
            timeout=args.timeout, max_bytes=args.max_bytes, max_redirects=args.max_redirects,
            root=root)
        validate_result(root, manifest, request)
        files = expected_files(manifest, excerpts)
        if args.check:
            actual = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()} if output.is_dir() else {}
            if actual != files:
                print("FAIL — capture output is missing, stale, or has extra files", file=sys.stderr)
                return 1
            print(f"PASS — {output} is byte-current")
            return exit_code
        if output.exists():
            raise UnsafeCapture("capture output already exists; immutable runs are never overwritten")
        publish_atomic(root, output, files, request)
        print(f"Capture {request['run_id']}: {manifest['summary']} -> {output}")
        return exit_code
    except UnsafeCapture as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1
    except UnprovenCapture as exc:
        print(f"UNPROVEN — {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"UNPROVEN — filesystem operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
