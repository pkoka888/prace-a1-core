#!/usr/bin/env python3
"""Import an employer from the Czech business register, after review.

Two steps, on purpose. The first retrieves the registry record and writes it
with its source and the hash of the response, for a human to look at. The
second stores a reviewed record as a ``LegalEntity``. Nothing reaches the
database without the review in between.

    # 1. retrieve for review
    venv/bin/python scripts/import_ares_legal_entity.py \\
        --registration-id 17511267 --out runtime/portal/temporary/ares-review.json

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
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import django  # noqa: E402


def _store(review_path: Path) -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
    django.setup()
    from portal.release1a.models import LegalEntity, Organization

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
    print(f"{'created' if created else 'updated'} LegalEntity {entity.pk} "
          f"for {entity.registration_id}")
    return 0


def _retrieve(registration_id: str, out: Path) -> int:
    from portal.release1a.ares import (
        AresUnavailable,
        fetch_legal_entity,
        write_review_record,
    )

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration-id")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--confirm", type=Path)
    args = parser.parse_args(argv)
    if args.confirm:
        return _store(args.confirm)
    if not args.registration_id or not args.out:
        parser.error("--registration-id and --out are required to retrieve")
    return _retrieve(args.registration_id, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
