#!/usr/bin/env python3
"""Validate and verify every outbound URL in a Plan AC research envelope.

Fixture-only operation is deterministic and is the default. ``--live`` uses
bounded HEAD requests (GET only when HEAD is unsupported), validates every DNS
answer and redirect target before connecting, and never downloads a body.

Exit codes: 0 all URLs verified; 1 invalid/unsafe input; 2 unproven environment.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
import urllib.error
import urllib.request
from contextlib import nullcontext
from pathlib import Path
from unittest import mock
from urllib.parse import urljoin, urlsplit

ALLOWED_SCHEMES = {"http", "https"}
REDIRECT_CODES = {301, 302, 303, 307, 308}
OFFLINE_DENIED_SUFFIXES = (
    ".localhost", ".local", ".internal", ".home.arpa", ".test",
    ".invalid", ".example", ".onion",
)


class UnsafeURL(ValueError):
    """A deterministic URL/network-policy violation."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _safe_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value.split("%", 1)[0])
    return not any((ip.is_private, ip.is_loopback, ip.is_link_local,
                    ip.is_multicast, ip.is_reserved, ip.is_unspecified))


def validate_public_https_url(url: str) -> str:
    """Apply deterministic public-HTTPS policy without performing DNS.

    This is suitable for validating stored evidence references. A live client
    must additionally validate every DNS answer and redirect target with
    :func:`validate_target` immediately before connecting.
    """
    try:
        parsed = urlsplit(url)
        parsed.port  # Force malformed-port validation.
    except (TypeError, ValueError) as exc:
        raise UnsafeURL(f"malformed URL: {exc}") from exc
    if parsed.scheme.lower() != "https":
        raise UnsafeURL("public evidence URLs must use HTTPS")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("URL must have a host and must not contain credentials")
    host = parsed.hostname.rstrip(".").lower()
    if not host or host == "localhost" or host.endswith(OFFLINE_DENIED_SUFFIXES):
        raise UnsafeURL("non-public or local hostname is denied")
    try:
        literal = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if not _safe_ip(str(literal)):
            raise UnsafeURL("non-public literal IP is denied")
        return url
    # Reject single-label and alternate numeric IPv4 spellings that URL stacks
    # may resolve as loopback/private addresses (for example 2130706433).
    if "." not in host or not any(char.isalpha() for char in host):
        raise UnsafeURL("hostname is not a public DNS name")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeURL("hostname is not valid IDNA") from exc
    labels = ascii_host.split(".")
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
           or not all(char.isalnum() or char == "-" for char in label)
           for label in labels):
        raise UnsafeURL("hostname is not a valid public DNS name")
    return url


def validate_target(url: str, resolver=socket.getaddrinfo) -> list[str]:
    """Validate scheme/host and every resolved address; return normalized IPs."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise UnsafeURL(f"malformed URL: {exc}") from exc
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURL("disallowed scheme (only http/https)")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("URL must have a host and must not contain credentials")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeURL("localhost is denied")
    try:
        literal = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if not _safe_ip(str(literal)):
            raise UnsafeURL("non-public literal IP is denied")
        return [str(literal)]
    try:
        answers = resolver(host, port or (443 if parsed.scheme == "https" else 80),
                           type=socket.SOCK_STREAM)
    except (OSError, socket.gaierror) as exc:
        raise RuntimeError(f"DNS resolution failed: {exc}") from exc
    ips = sorted({item[4][0].split("%", 1)[0] for item in answers})
    if not ips:
        raise RuntimeError("DNS resolution returned no addresses")
    for ip in ips:
        try:
            safe = _safe_ip(ip)
        except ValueError as exc:
            raise RuntimeError(f"DNS returned an invalid address: {ip}") from exc
        if not safe:
            raise UnsafeURL(f"DNS resolved to denied address {ip}")
    return ips


def inventory_urls(envelope: dict) -> list[dict]:
    """Deduplicate URLs while retaining all entity/field/evidence references."""
    found: dict[str, dict] = {}

    def add(url, entity_id, field, evidence_id=None):
        if not isinstance(url, str):
            # Schema validation normally catches this; retain defense in depth.
            raise UnsafeURL(f"{entity_id}:{field} is not a URL string")
        row = found.setdefault(url, {"url": url, "references": []})
        ref = {"entity_id": entity_id, "field": field}
        if evidence_id:
            ref["evidence_id"] = evidence_id
        if ref not in row["references"]:
            row["references"].append(ref)

    for entity in envelope.get("entities", []):
        entity_id = entity.get("id")
        for url in entity.get("source_links", []) or []:
            add(url, entity_id, "source_links")
        pricing_url = (entity.get("pricing") or {}).get("pricing_url")
        if pricing_url:
            add(pricing_url, entity_id, "pricing_url")
    for evidence in envelope.get("evidence", []):
        add(evidence.get("canonical_url"), evidence.get("entity_id"),
            "canonical_url", evidence.get("id"))
    return list(found.values())


def _fixture_path(root: Path, url: str) -> Path:
    name = url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]
    return root / "tests" / "fixtures" / f"url_fixture_{name}.json"


def check_fixture(root: Path, url: str, resolver=socket.getaddrinfo) -> dict:
    try:
        # Fixture-only results must not vary with ambient DNS. Literal IP and
        # syntax policy still run; hostname resolution is represented by a
        # fixed public documentation address solely for validation.
        validate_target(url, lambda host, port, type=None:
                        [(socket.AF_INET, socket.SOCK_STREAM, 6, "",
                          ("93.184.216.34", port))])
    except UnsafeURL as exc:
        return {"verdict": "invalid", "reason": str(exc), "mode": "fixture-only"}
    path = _fixture_path(root, url)
    if not path.is_file():
        return {"verdict": "unproven", "reason": "no deterministic fixture",
                "mode": "fixture-only"}
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"verdict": "invalid", "reason": f"invalid fixture: {exc}",
                "mode": "fixture-only"}
    verdict = fixture.get("verdict")
    if verdict not in {"verified", "unproven", "invalid"}:
        return {"verdict": "invalid", "reason": "fixture has invalid verdict",
                "mode": "fixture-only"}
    return {"verdict": verdict, "status": fixture.get("status"),
            "final_url": fixture.get("final_url", url), "redirect_chain": [],
            "reason": fixture.get("reason") or fixture.get("detail"),
            "mode": "fixture-only"}


def check_live(url: str, timeout: float, max_redirects: int = 5,
               resolver=socket.getaddrinfo, opener=None) -> dict:
    uses_network_opener = opener is None
    opener = opener or urllib.request.build_opener(NoRedirect)
    current, chain, method = url, [], "HEAD"

    def guarded_resolution(*args, **kwargs):
        answers = resolver(*args, **kwargs)
        for answer in answers:
            ip = answer[4][0].split("%", 1)[0]
            if not _safe_ip(ip):
                raise UnsafeURL(f"connection DNS resolved to denied address {ip}")
        return answers

    try:
        for _ in range(max_redirects + 1):
            validate_target(current, resolver)
            req = urllib.request.Request(current, method=method,
                                         headers={"User-Agent": "plan-ac-url-check/2.0"})
            try:
                # urllib resolves independently from our preflight. Guard that
                # second resolution as well so DNS rebinding cannot turn a
                # public preflight answer into a private connection target.
                guard = (mock.patch("socket.getaddrinfo", side_effect=guarded_resolution)
                         if uses_network_opener else nullcontext())
                with guard:
                    response = opener.open(req, timeout=timeout)
                status = response.getcode()
                headers = response.headers
                response.close()
            except urllib.error.HTTPError as exc:
                status, headers = exc.code, exc.headers
                exc.close()
            if status in REDIRECT_CODES:
                location = headers.get("Location")
                if not location:
                    return {"verdict": "invalid", "status": status,
                            "final_url": current, "redirect_chain": chain,
                            "reason": "redirect missing Location", "mode": "live"}
                target = urljoin(current, location)
                validate_target(target, resolver)  # validate before next request
                chain.append({"status": status, "from": current, "to": target})
                if len(chain) > max_redirects:
                    return {"verdict": "unproven", "status": status,
                            "final_url": current, "redirect_chain": chain,
                            "reason": "redirect limit exceeded", "mode": "live"}
                current = target
                method = "HEAD"
                continue
            if status in {405, 501} and method == "HEAD":
                method = "GET"
                continue
            if 200 <= status < 400:
                return {"verdict": "verified", "status": status,
                        "final_url": current, "redirect_chain": chain,
                        "reason": None, "mode": "live"}
            return {"verdict": "unproven", "status": status,
                    "final_url": current, "redirect_chain": chain,
                    "reason": f"HTTP status {status}", "mode": "live"}
    except UnsafeURL as exc:
        return {"verdict": "invalid", "status": None, "final_url": current,
                "redirect_chain": chain, "reason": str(exc), "mode": "live"}
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        return {"verdict": "unproven", "status": None, "final_url": current,
                "redirect_chain": chain, "reason": str(exc)[:300], "mode": "live"}


def _contained_output(root: Path, value: str) -> Path:
    path = Path(value).resolve()
    tmp = Path("/tmp").resolve()
    if path != root and root not in path.parents and path != tmp and tmp not in path.parents:
        raise ValueError("--output must be contained under project root or /tmp")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify all Plan AC evidence URLs")
    parser.add_argument("--root", default=".")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", required=True,
                        help="Explicit report path under project root or /tmp")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-redirects", type=int, default=5)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    input_path = Path(args.input).resolve() if args.input else root / "research/processed/entities.json"
    try:
        output_path = _contained_output(root, args.output)
        if args.timeout <= 0 or args.max_redirects < 0:
            raise ValueError("timeout must be positive and max-redirects non-negative")
        envelope = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1

    try:
        from validate_research_schema import validate_envelope
        valid, detail, _ = validate_envelope(root, envelope)
    except Exception as exc:
        print(f"UNPROVEN — validator unavailable: {exc}", file=sys.stderr)
        return 2
    if not valid:
        print(f"FAIL — invalid envelope: {detail}", file=sys.stderr)
        return 1

    try:
        inventory = inventory_urls(envelope)
    except UnsafeURL as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1
    results = []
    for item in inventory:
        result = (check_live(item["url"], args.timeout, args.max_redirects)
                  if args.live else check_fixture(root, item["url"]))
        results.append({**item, **result})
    report = {"mode": "live" if args.live else "fixture-only",
              "input": str(input_path), "results": results,
              "summary": {v: sum(r["verdict"] == v for r in results)
                          for v in ("verified", "unproven", "invalid")}}
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    except OSError as exc:
        print(f"UNPROVEN — cannot write report: {exc}", file=sys.stderr)
        return 2
    print(f"URL check: {len(results)} unique; {report['summary']}; output: {output_path}")
    if report["summary"]["invalid"]:
        return 1
    if report["summary"]["unproven"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
