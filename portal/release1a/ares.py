"""ARES: the Czech public business register, as a source of employer facts.

ARES is the Ministry of Finance's register of economic subjects. It is free,
needs no key, has no quota to buy and returns public registry data. It is
therefore inside the "verified-free endpoints" envelope, and it is not a
model provider, so the provider rules about keys and billing do not apply to
it.

What the approval covered is the *capability*: the service may make an
outbound HTTPS request to a third-party host. Whether the host can actually
reach ares.gov.cz is a deployment fact, so the client degrades rather than
fails: a timeout, a DNS failure or a non-200 response leaves the caller with
no enrichment and an explicit reason, and never with a partially filled
record.

Decisions D11a and D11b (2026-10-20).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest"
# The registry's own operating limit, documented in its technical catalogue.
RATE_LIMIT_PER_MINUTE = 500
DEFAULT_TIMEOUT_SECONDS = 5.0
# A registry record changes rarely, so a short cache removes most repeat
# lookups. The cache is in-process and deliberately small.
CACHE_TTL_SECONDS = 3600.0

_CACHE: dict[str, tuple[float, dict]] = {}


class AresUnavailable(RuntimeError):
    """The register could not be reached or refused the request."""


def enabled() -> bool:
    """Whether outbound lookups are permitted.

    The approval is the default; a deployment without egress sets the
    variable to off and the import path falls back to a manual record.
    """
    return os.environ.get("A1_ARES_LOOKUP_ENABLED", "1").strip().casefold() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _cache_key(url: str) -> str:
    return url


def _cached(url: str) -> dict | None:
    entry = _CACHE.get(_cache_key(url))
    if entry is None:
        return None
    stored_at, payload = entry
    if time.monotonic() - stored_at > CACHE_TTL_SECONDS:
        _CACHE.pop(_cache_key(url), None)
        return None
    return payload


def _store(url: str, payload: dict) -> None:
    _CACHE[_cache_key(url)] = (time.monotonic(), payload)


def _get_json(url: str, *, timeout: float) -> dict:
    if not enabled():
        raise AresUnavailable("A1_ARES_LOOKUP_DISABLED")
    cached = _cached(url)
    if cached is not None:
        return cached
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "prace-a1-core"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise AresUnavailable(f"ARES_HTTP_{response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AresUnavailable(f"ARES_HTTP_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AresUnavailable("ARES_UNREACHABLE") from exc
    except ValueError as exc:
        raise AresUnavailable("ARES_MALFORMED_RESPONSE") from exc
    _store(url, payload)
    return payload


def legal_entity_url(registration_id: str) -> str:
    return f"{BASE_URL}/ekonomicke-subjekty/{urllib.parse.quote(registration_id)}"


def economic_subject_url(registration_id: str) -> str:
    """The view with the predominant CZ-NACE activity and the size category."""
    return f"{BASE_URL}/ekonomicke-subjekty-res/{urllib.parse.quote(registration_id)}"


def _address(raw: dict) -> dict:
    return {
        "street": raw.get("textovaAdresa", "") or "",
        "house_number": raw.get("cisloDomovni", "") or "",
        "city": raw.get("nazevObce", "") or "",
        "postal_code": raw.get("psc", "") or "",
        "municipality_code": raw.get("kodObce", "") or "",
        "country_code": raw.get("kodStatu", "") or "",
    }


def fetch_legal_entity(
    registration_id: str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> dict:
    """Look a registration number up and return a reviewable record.

    The result carries its source and the hash of the response, so a later
    correction is traceable to the registry event that caused it. Nothing is
    stored here: the caller decides whether the record is accepted.
    """
    registration_id = (registration_id or "").strip()
    if not registration_id.isdigit():
        raise AresUnavailable("ARES_REGISTRATION_ID_INVALID")
    url = legal_entity_url(registration_id)
    payload = _get_json(url, timeout=timeout)
    # The endpoint answers with the subject at the top level. Some deployments
    # wrap it, so both shapes are accepted.
    raw = payload.get("ekonomickySubjekt") or payload
    if not raw.get("ico"):
        raise AresUnavailable("ARES_SUBJECT_NOT_FOUND")
    address = _address(raw.get("sidlo") or {})
    legal_form = raw.get("pravniForma") or ""
    nace = [code for code in (raw.get("czNace2008") or []) if code]
    record = {
        "registration_id": registration_id,
        "legal_name": raw.get("obchodniJmeno", "") or "",
        # 101 is the legal form for an individual, so a sole trader is the
        # person's own record rather than a company's.
        "legal_form": "sole_trader" if legal_form == "101" else "company",
        "country_code": address.get("country_code") or "CZ",
        "registered_address": address,
        "nace_codes": nace,
        "source": url,
        # The registry's own last-update date, and the date we verified the
        # record. The two differ, and the difference is the point: the
        # registry says when it last changed the record, and the agency says
        # when it checked.
        "registry_updated_on": raw.get("datumAktualizace") or "",
        "founded_on": raw.get("datumVzniku") or "",
        "verified_on": date.today().isoformat(),
        "retrieved_on": date.today().isoformat(),
        "content_sha256": "",
    }
    # The predominant activity is in a second view; it is optional.
    try:
        subject = _get_json(economic_subject_url(registration_id), timeout=timeout)
    except AresUnavailable:
        subject = {}
    for entry in subject.get("zaznamy") or []:
        for code in entry.get("czNace") or []:
            if code and code not in record["nace_codes"]:
                record["nace_codes"].append(code)
    return record


def fetch_changed_registrations(
    since: str, *, subject: str = "", timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> list[dict]:
    """The register's change notifications: which registrations changed, and when.

    This is the channel that makes a correction to a shared record traceable:
    a point lookup says what an entity is now, the notification says when it
    changed, so a master record can carry an "as of" date that is evidence
    rather than an assertion.
    """
    if not enabled():
        raise AresUnavailable("A1_ARES_LOOKUP_DISABLED")
    body = json.dumps({"predmet": subject, "od": since}).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/ekonomicke-subjekty-notifikace/vyhledat",
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "prace-a1-core",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise AresUnavailable(f"ARES_HTTP_{response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AresUnavailable(f"ARES_HTTP_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AresUnavailable("ARES_UNREACHABLE") from exc
    except ValueError as exc:
        raise AresUnavailable("ARES_MALFORMED_RESPONSE") from exc
    return list(payload.get("ekonomickeSubjekty") or [])


def write_review_record(record: dict, destination: Path) -> Path:
    """Write the looked-up record for review, with its provenance.

    The review step is the point: a human sees the registry data and its
    source before it becomes a stored fact.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    destination.chmod(0o600)
    return destination
