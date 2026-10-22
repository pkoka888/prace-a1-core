#!/usr/bin/env python3
"""Import an employer from the Czech business register, after review.

Two steps, on purpose. The first retrieves the registry record and writes it
with its source and the hash of the response, for a human to look at. The
second stores a reviewed record as a ``LegalEntity``. Nothing reaches the
database without the review in between.

    # 1. retrieve for review
    venv/bin/python scripts/import_ares_legal_entity.py \\
        --registration-id <registration number> --out <review file>

    # 2. store the reviewed record
    venv/bin/python scripts/import_ares_legal_entity.py \\
        --confirm runtime/portal/temporary/ares-review.json

Decision D11a (2026-10-20). The registry is public and free, so no provider
authorisation is needed for the retrieval; the record it produces is a
natural person's registration data when the employer is a sole trader, so it
is stored with its provenance and never published in a committed document.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import deque
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import django  # noqa: E402


class TokenBucketRateLimiter:
    """Token bucket rate limiter for ARES API (500 requests/minute)."""

    def __init__(self, rate: int = 500, per: int = 60):
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.last = time.monotonic()
        self.lock = Lock()

    def acquire(self):
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate / self.per)
            if self.tokens >= 1:
                self.tokens -= 1
                self.last = now
                return
            wait = (1 - self.tokens) * self.per / self.rate
            time.sleep(wait)
            self.tokens = 0
            self.last = time.monotonic()


ARES_RATE_LIMITER = TokenBucketRateLimiter(500, 60)


def _store(review_path: Path) -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
    django.setup()
    from portal.release1a.models import LegalEntity, Organization, Assignment

    record = json.loads(review_path.read_text(encoding="utf-8"))
    organization = Organization.objects.filter(key="default").first()
    if organization is None:
        print("no default organization; nothing stored", file=sys.stderr)
        return 2
    entity, created = LegalEntity.objects.update_or_create(
        organization=organization,
        registration_id=record["registration_id"],
        defaults={
            "legal_name": record.get("legal_name", ""),
            "legal_form": record.get("legal_form", "company"),
            "country_code": record.get("country_code", "CZ"),
            "registered_address": record.get("registered_address", {}),
            "nace_codes": record.get("nace_codes", []),
            "source": record.get("source", ""),
            "verified_on": record.get("verified_on") or None,
            "content_sha256": record.get("content_sha256", ""),
        },
    )
    # Link LegalEntity to Assignments that reference this registration_id
    reg_id = record["registration_id"]
    assignments = Assignment.objects.filter(
        organization=organization,
        a1_facts_json__employment_id=reg_id,
    )
    count = assignments.update(legal_entity=entity)
    if count:
        print(f"linked LegalEntity {entity.pk} to {count} Assignment(s)")
    print(
        f"{'created' if created else 'updated'} LegalEntity {entity.pk} "
        f"for {entity.registration_id}"
    )
    return 0


def _discover(review_path: Path) -> list[str]:
    """The registration numbers the agency's own review rows name.

    The import does not guess which employer to look up: it reads the
    registration numbers the reviewed data already carries, and skips the
    ones that are still pending.
    """
    if not review_path.is_file():
        return []
    with review_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    found: list[str] = []
    for row in rows:
        value = (row.get("employment_id") or "").strip()
        if not value.isdigit() or value in found:
            continue
        found.append(value)
    return found


def _retrieve_one(registration_id: str, out: Path) -> bool:
    """Retrieve one registration. Returns whether it succeeded."""
    from portal.release1a.ares import (
        AresUnavailable,
        fetch_legal_entity,
        write_review_record,
    )

    ARES_RATE_LIMITER.acquire()
    try:
        record = fetch_legal_entity(registration_id)
    except AresUnavailable as exc:
        print(f"{registration_id}: not retrieved ({exc})", file=sys.stderr)
        return False
    record["content_sha256"] = hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    destination = out / f"{registration_id}.json"
    write_review_record(record, destination)
    print(f"{registration_id}: wrote {destination}")
    return True


def _retrieve(registration_id: str, out: Path) -> int:
    from portal.release1a.ares import (
        AresUnavailable,
        fetch_legal_entity,
        write_review_record,
    )

    ARES_RATE_LIMITER.acquire()
    try:
        record = fetch_legal_entity(registration_id)
    except AresUnavailable as exc:
        print(f"the register is not available: {exc}", file=sys.stderr)
        print(
            "Nothing was stored. An offline deployment can record the "
            "employer by hand with the same fields and its source.",
            file=sys.stderr,
        )
        return 2
    record["content_sha256"] = hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    write_review_record(record, out)
    print(f"wrote the record for review to {out}")
    print("review it, then store it with --confirm")
    return 0


def _annotate(review_path: Path) -> int:
    """Mark each review row with how it compares to the register.

    The file path reads a review CSV, and the generator must not reach the
    network or the database, so this is how a hand-written row learns that its
    employer disagrees with the register. The comparison itself is the
    review contract's, so the export and this path agree. Gate D15.
    """
    from scripts.finalize_a1 import employment_divergence

    from portal.release1a.ares import AresUnavailable, fetch_legal_entity

    if not review_path.is_file():
        print(f"no review file at {review_path}", file=sys.stderr)
        return 2
    with review_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "employment_source_status" not in fieldnames:
        fieldnames.append("employment_source_status")
    registry: dict[str, dict] = {}
    for row in rows:
        registration_id = (row.get("employment_id") or "").strip()
        if not registration_id.isdigit() or registration_id in registry:
            continue
        ARES_RATE_LIMITER.acquire()
        try:
            registry[registration_id] = fetch_legal_entity(registration_id)
        except AresUnavailable as exc:
            print(f"{registration_id}: not retrieved ({exc})", file=sys.stderr)
    diverging = 0
    for row in rows:
        registration_id = (row.get("employment_id") or "").strip()
        record = registry.get(registration_id)
        if record is None:
            row["employment_source_status"] = ""
            continue
        differences = employment_divergence(row, record)
        if differences:
            row["employment_source_status"] = "DIVERGES_FROM_REGISTER"
            diverging += 1
            print(
                f"{row.get('employee_id', registration_id)}: " + "; ".join(differences)
            )
        else:
            row["employment_source_status"] = "REGISTRY_VERIFIED"
    with review_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"annotated {len(rows)} row(s); {diverging} diverge from the register")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration-id")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--confirm", type=Path)
    parser.add_argument(
        "--review",
        type=Path,
        help="the review CSV to read the registration numbers from; "
        "without --registration-id every number in it is retrieved",
    )
    parser.add_argument(
        "--all-reviewed",
        action="store_true",
        help="retrieve every registration number the review rows carry",
    )
    parser.add_argument(
        "--annotate",
        type=Path,
        help="mark each row of a review CSV with how its employer compares to "
        "the register, so the file path learns the divergence too",
    )
    args = parser.parse_args(argv)
    if args.annotate:
        return _annotate(args.annotate)
    if args.confirm:
        return _store(args.confirm)
    if args.registration_id:
        if not args.out:
            parser.error("--out is required with --registration-id")
        return _retrieve(args.registration_id, args.out)

    review = args.review or (ROOT / "a1" / "review.csv")
    out = args.out or (ROOT / "runtime" / "portal" / "temporary" / "ares-review")
    if not args.all_reviewed and not review.is_file():
        parser.error(
            f"no review file at {review}; pass --registration-id, or "
            "--all-reviewed with a review file"
        )
    registrations = _discover(review)
    if not registrations:
        print("no registration numbers in the review data", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    print(f"retrieving {len(registrations)} registration(s) for review")
    retrieved = sum(1 for r in registrations if _retrieve_one(r, out))
    print(
        f"{retrieved} of {len(registrations)} retrieved; review them, then "
        "store each with --confirm"
    )
    return 0 if retrieved else 2


if __name__ == "__main__":
    raise SystemExit(main())
