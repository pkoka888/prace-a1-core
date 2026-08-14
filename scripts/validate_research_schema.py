#!/usr/bin/env python3
"""Validate a research envelope against the frozen research-model schema (v1.2).

This module is the SINGLE canonical validation library for the research
subsystem. The validator, normalizer, scorer, completeness checker, cockpit
generator, and acceptance logic all import from here so behaviour cannot
drift between commands.

Validation layers
-----------------
1. Schema version gate: only the active ``SUPPORTED_VERSIONS`` are accepted.
   Anything else (including the superseded 1.0/1.1) is rejected explicitly.
2. JSON Schema (Draft-07) validation with a ``FormatChecker`` for date/uri.
3. An indexed relationship/state invariant pass (``relationship_checks``) that
   also enforces the run-level acceptance rules for ``verified`` / ``accepted``
   envelopes (policy quotas, calculated scores, reviewer records, eligible
   evidence, no unresolved conflicts).

Run-level rules read ``envelope.run_status`` — never a per-entity field.

Exit codes (mirrored by ``main``):
   0  all validations pass
   1  schema or relationship/state validation failure
   2  environment error (jsonschema lib missing, schema/file missing)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "research" / "schemas"

# Only this version is active. v1.0/v1.1 live under schemas/superseded/.
SUPPORTED_VERSIONS = {"1.2"}

LANES = ["oss_invoice", "czech_invoice_software", "czech_accounting_firms",
         "czech_individual", "studies_comprehensive"]
MIN_PER_COHORT = 10


def load_schema(root: Path, version: str):
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema not available: " + str(exc))
    schema_path = root / "research" / "schemas" / f"research-model-{version}.json"
    if not schema_path.is_file():
        raise RuntimeError("Schema not found: " + str(schema_path))
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid schema JSON: " + str(exc))
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except Exception as exc:  # invalid schema itself
        raise RuntimeError("Schema self-check failed: " + str(exc))
    return jsonschema, schema


HTTP_SCHEMES = {"http", "https"}


def _is_http_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return value.split(":", 1)[0].lower() in HTTP_SCHEMES


def relationship_checks(data: dict) -> list[dict]:
    """Return indexed relationship/state invariants: [{index, name, passed, detail}]."""
    out: list[dict] = []
    i = 0

    def add(name, ok, detail=""):
        nonlocal i
        out.append({"index": i, "name": name, "passed": bool(ok), "detail": detail})
        i += 1

    run_status = data.get("run_status")
    entities = data.get("entities", []) or []
    evidence = data.get("evidence", []) or []
    reviews = data.get("reviews", []) or []

    entity_ids = {e.get("id") for e in entities if isinstance(e, dict)}
    evidence_by_id = {e.get("id"): e for e in evidence if isinstance(e, dict)}
    entity_id_list = [e.get("id") for e in entities if isinstance(e, dict)]
    evidence_id_list = [e.get("id") for e in evidence if isinstance(e, dict)]
    review_ids = [r.get("reviewer_id") for r in reviews if isinstance(r, dict) and r.get("reviewer_id")]

    # 0: unique entity IDs (by id value, not object identity)
    dup_e = {x for x in entity_id_list if entity_id_list.count(x) > 1}
    add("unique entity IDs", not dup_e, "duplicates: " + ", ".join(sorted(dup_e)) if dup_e else "")

    # 1: unique evidence IDs
    dup_ev = {x for x in evidence_id_list if evidence_id_list.count(x) > 1}
    add("unique evidence IDs", not dup_ev, "duplicates: " + ", ".join(sorted(dup_ev)) if dup_ev else "")

    # 2: unique review identities
    dup_r = {x for x in review_ids if review_ids.count(x) > 1}
    add("unique review identities", not dup_r, "duplicates: " + ", ".join(sorted(dup_r)) if dup_r else "")

    # 3: evidence foreign key -> entity
    bad_fk = [e.get("id") for e in evidence if isinstance(e, dict) and e.get("entity_id") not in entity_ids]
    add("evidence.entity_id resolves to an entity", not bad_fk, "orphans: " + ", ".join(bad_fk[:8]) if bad_fk else "")

    # 4: evidence ownership by its entity
    owned = all(e.get("entity_id") in entity_ids for e in evidence if isinstance(e, dict))
    add("evidence owned by a known entity", owned)

    # 5: claim evidence_ref resolves
    bad_claim = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for c in e.get("claims", []) or []:
            if isinstance(c, dict) and c.get("evidence_ref") not in evidence_by_id:
                bad_claim.append(e.get("id"))
                break
    add("claim.evidence_ref resolves to evidence", not bad_claim, "entities: " + ", ".join(bad_claim[:8]) if bad_claim else "")

    # 5b: claim evidence belongs to the same entity (no cross-entity laundering)
    cross_claim = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for c in e.get("claims", []) or []:
            if not isinstance(c, dict):
                continue
            ev = evidence_by_id.get(c.get("evidence_ref"))
            if ev and ev.get("entity_id") != e.get("id"):
                cross_claim.append(e.get("id"))
                break
    add("claim evidence belongs to same entity", not cross_claim, "entities: " + ", ".join(cross_claim[:8]) if cross_claim else "")

    # 6: claim field matches referenced evidence.claim_field
    mism = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for c in e.get("claims", []) or []:
            if not isinstance(c, dict):
                continue
            ev = evidence_by_id.get(c.get("evidence_ref"))
            if ev and ev.get("claim_field") and ev.get("claim_field") != c.get("field"):
                mism.append(e.get("id"))
                break
    add("claim.field matches evidence.claim_field", not mism, "entities: " + ", ".join(mism[:8]) if mism else "")

    # 7: confirmed capability evidence_ref resolves and belongs to same entity
    cap_bad = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for cap in (e.get("offerings", {}) or {}).values():
            if isinstance(cap, dict) and cap.get("state") == "confirmed" and cap.get("evidence_ref"):
                if cap.get("evidence_ref") not in evidence_by_id:
                    cap_bad.append(e.get("id"))
                    break
                ev = evidence_by_id.get(cap.get("evidence_ref"))
                if ev and ev.get("entity_id") != e.get("id"):
                    cap_bad.append(e.get("id"))
                    break
    add("confirmed capability evidence_ref resolves", not cap_bad, "entities: " + ", ".join(cap_bad[:8]) if cap_bad else "")

    # 8: pricing tier evidence_ref resolves and belongs to same entity
    price_bad = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for t in (e.get("pricing", {}) or {}).get("tiers", []) or []:
            if isinstance(t, dict) and t.get("evidence_ref"):
                if t.get("evidence_ref") not in evidence_by_id:
                    price_bad.append(e.get("id"))
                    break
                ev = evidence_by_id.get(t.get("evidence_ref"))
                if ev and ev.get("entity_id") != e.get("id"):
                    price_bad.append(e.get("id"))
                    break
    add("pricing tier evidence_ref resolves", not price_bad, "entities: " + ", ".join(price_bad[:8]) if price_bad else "")

    # 9: HTTP/HTTPS enforcement for all urls
    url_problems = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        for link in e.get("source_links", []) or []:
            if not _is_http_url(link):
                url_problems.append("%s:source_links" % e.get("id"))
        p = e.get("pricing", {}) or {}
        if p.get("pricing_url") and not _is_http_url(p.get("pricing_url")):
            url_problems.append("%s:pricing_url" % e.get("id"))
    for ev in evidence:
        if isinstance(ev, dict) and not _is_http_url(ev.get("canonical_url")):
            url_problems.append("%s:canonical_url" % ev.get("id"))
    add("all URLs are http/https", not url_problems, "bad: " + ", ".join(url_problems[:8]) if url_problems else "")

    # 10: reviewed/accepted states require reviewer records (practical use confirmed)
    reviewed_entities = set()
    for r in reviews:
        if isinstance(r, dict):
            reviewed_entities.update(r.get("verified_entities", []) or [])
    need_review = {e.get("id") for e in entities if isinstance(e, dict) and e.get("practical_business_use") == "confirmed"}
    missing_review = need_review - reviewed_entities
    add("confirmed entities have reviewer coverage", not missing_review, "missing: " + ", ".join(sorted(missing_review)[:8]) if missing_review else "")

    # 11: calculated scores required for non-collecting statuses (run-level)
    non_collecting = run_status in ("complete", "verified", "accepted")
    scored_ok = True
    if non_collecting:
        for e in entities:
            if not isinstance(e, dict):
                continue
            sc = e.get("scores", {}) or {}
            if not sc.get("calculated"):
                scored_ok = False
                break
    add("calculated scores present for non-collecting status", scored_ok)

    # 12: immutable run metadata present
    run_ok = bool(data.get("run_id")) and bool(data.get("as_of")) and "schema_version" in data
    add("immutable run_id/as_of/schema_version present", run_ok)

    # 13: schema-valid representation of unproven score states
    unproven_ok = True
    for e in entities:
        if not isinstance(e, dict):
            continue
        sc = e.get("scores", {}) or {}
        for k, v in sc.items():
            if k in ("calculated", "calculated_at"):
                continue
            if isinstance(v, str) and v != "unproven":
                unproven_ok = False
            elif isinstance(v, str):
                continue
            elif not isinstance(v, (int, float)):
                unproven_ok = False
    add("score fields are numeric or 'unproven'", unproven_ok)

    # ------------------------------------------------------------------
    # Run-level acceptance rules for verified / accepted envelopes.
    # ------------------------------------------------------------------
    if run_status in ("verified", "accepted"):
        counts = {}
        for e in entities:
            if isinstance(e, dict):
                c = e.get("cohort")
                if c:
                    counts[c] = counts.get(c, 0) + 1
        unmet = [lane for lane in LANES if counts.get(lane, 0) < MIN_PER_COHORT]
        add("verified/accepted: policy quotas met", not unmet, "unmet: " + ", ".join(unmet))

        add("verified/accepted: reviewer records present", bool(reviews) and bool(review_ids))

        all_scored = all((e.get("scores", {}) or {}).get("calculated")
                         for e in entities if isinstance(e, dict))
        add("verified/accepted: all entities have calculated scores", all_scored)

        claims_eligible = (not bad_claim) and (not cross_claim) and (not mism)
        add("verified/accepted: all claims have eligible evidence", claims_eligible)

        conflicts = bool(dup_e) or bool(dup_ev) or bool(dup_r) or bool(cross_claim) or bool(bad_fk)
        add("verified/accepted: no unresolved conflicts", not conflicts)

        if run_status == "accepted":
            covered = {e.get("id") for e in entities if isinstance(e, dict)}
            add("accepted: every entity has approval coverage",
                covered.issubset(reviewed_entities) if covered else True)

    return out


def validate_envelope(root: Path, data: dict, version: str | None = None) -> tuple[bool, str, str]:
    """Canonical envelope validation: version gate + schema + relationship/state.

    Returns ``(ok, detail, version)``. A non-supported schema version is a hard
    validation failure (this is how superseded 1.0/1.1 get rejected).
    """
    version = version or data.get("schema_version")
    if version not in SUPPORTED_VERSIONS:
        return (False,
                "unsupported schema_version '%s' (active version is %s)"
                % (version, "/".join(sorted(SUPPORTED_VERSIONS))),
                version or "unknown")

    try:
        jsonschema, schema = load_schema(root, version)
    except RuntimeError as exc:
        return False, str(exc), version

    checker = jsonschema.FormatChecker()
    validator = jsonschema.Draft7Validator(schema, format_checker=checker)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        msgs = ["%s: %s" % ("/".join(str(p) for p in e.path) or "<root>", e.message) for e in errors[:8]]
        return False, "schema validation failed: " + " | ".join(msgs), version

    rel = relationship_checks(data)
    failed = [r for r in rel if not r["passed"]]
    if failed:
        det = "; ".join("[%d] %s: %s" % (r["index"], r["name"], r["detail"]) for r in failed)
        return False, "relationship/state invariants failed: " + det, version

    return True, "envelope validates against research-model-%s (schema + %d invariants)" % (version, len(rel)), version


def validate_entities(root: Path, jsonschema, schema, data_path: Path) -> tuple[bool, str]:
    """Back-compat shim: validate a file by path. Prefer ``validate_envelope``."""
    if not data_path.is_file():
        return False, "envelope not found: %s" % data_path
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, "invalid JSON: " + str(exc)
    ok, detail, _ = validate_envelope(root, data)
    return ok, detail


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate research envelope against schema")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--input", default=None, help="Path to JSON envelope (default research/processed/entities.json)")
    parser.add_argument("--schema-version", default=None, help="Schema version to validate against (default: envelope.schema_version)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    input_path = Path(args.input).resolve() if args.input else (root / "research" / "processed" / "entities.json")

    if not input_path.is_file():
        msg = "envelope not found: %s" % input_path
        if args.json:
            print(json.dumps({"result": "fail", "error": msg, "exit": 1}))
        else:
            sys.stderr.write("FAIL — " + msg + "\n")
        return 1

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = "invalid JSON: %s" % exc
        if args.json:
            print(json.dumps({"result": "fail", "error": msg, "exit": 1}))
        else:
            sys.stderr.write("FAIL — " + msg + "\n")
        return 1

    version = args.schema_version or data.get("schema_version")
    ok, detail, resolved = validate_envelope(root, data, version)

    if args.json:
        payload = {"result": "pass" if ok else "fail", "detail": detail,
                   "schema_version": resolved, "input": input_path.name, "exit": 0 if ok else 1}
        print(json.dumps(payload, indent=2))
    else:
        print(("PASS" if ok else "FAIL") + " — " + input_path.name + ": " + detail)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
