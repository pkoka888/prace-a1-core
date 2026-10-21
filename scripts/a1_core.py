#!/usr/bin/env python3
"""A1 PDF rendering core. Output goes to output/provisional/."""

from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, NullObject, StreamObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

try:
    from .pdf_named_fields import display_value
except ImportError:
    from pdf_named_fields import display_value


PAGE_SIZE = (595.2, 841.92)

# The supported A1 status profiles, in one place. Every site that offers,
# accepts or derives a status reads this, so that adding a profile cannot
# leave one site behind. Before this, the set was written out in six places
# and the activation path had to name all of them. Decisions D1a and D1b
# (2026-10-20).
A1_STATUS_PROFILES = (
    "posted_employee",
    "employee_multi_state",
    "self_employed_multi_state",
)
# The application variant each profile belongs to. The variant says which
# application form applies; the profile says which situation was declared.
A1_STATUS_VARIANTS = {
    "posted_employee": "employee",
    "employee_multi_state": "employee",
    "self_employed_multi_state": "self_employed",
}
# The profiles that assert a posting, and so carry the Article 12 conditions
# of Regulation 883/2004. "posted_self_employed" is not yet a supported
# profile, but it is listed here so that the conditions are already written
# for the day it is.
A1_POSTING_STATUS_PROFILES = ("posted_employee", "posted_self_employed")
# The profiles whose activity is the employer's own, so Section 5 does not
# apply. The self-employed ones carry the host-State territory instead.
A1_SELF_EMPLOYED_STATUS_PROFILES = ("self_employed_multi_state",)
# The Czech labels the portal offers, in the same order as the profiles.
A1_STATUS_LABELS = {
    "posted_employee": "Vyslaný zaměstnanec",
    "employee_multi_state": "Zaměstnanec ve více státech",
    "self_employed_multi_state": "OSVČ ve více státech",
}
APPLICATION_DRAFT_NOTICE = "UNVERIFIED DRAFT – NEOVĚŘENÝ NÁVRH, NENÍ VYDANÉ A1"
PROVISIONAL_NOTICE = "NÁVRH – ČEKÁ NA POTVRZENÍ OSSZ"
ROOT = Path(__file__).resolve().parents[1]
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ROOT / "assets/fonts/DejaVuSans.ttf",
    Path(
        "C:/Users/pavel/.cache/codex-runtimes/codex-primary-runtime/"
        "dependencies/native/poppler/Library/share/fonts/DejaVuSans.ttf"
    ),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)
# Liberation Sans is the metric-compatible free replacement for Arial/Helvetica
# and ships Czech diacritics. The A1 2025 form template embeds Helvetica; this
# font matches the visual proportions and supports all required accented glyphs.
HELVETICA_FALLBACK = (
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
)


class A1ValidationError(ValueError):
    """Raised when unreviewed or incomplete data would enter a final A1."""


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_date(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().replace("/", ".").replace("-", ".")
    match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value)
    if not match:
        raise A1ValidationError(f"Unsupported date format: {value!r}")
    day, month, year = (int(part) for part in match.groups())
    try:
        datetime(year, month, day)
    except ValueError:
        raise A1ValidationError(f"Invalid date: {value!r}") from None
    return f"{day:02d}.{month:02d}.{year:04d}"


def validate_provisional_issue_date(value: str, reference: str) -> str:
    """Require client-review issue dates 2–6 months back and on Mon/Wed.

    This is only a placeholder scheduling policy; OSSZ must supply the official
    issue date. Different employees may use different qualifying dates.
    """
    normalized = normalize_date(value)
    issued = datetime.strptime(normalized, "%d.%m.%Y")
    reference_day = datetime.strptime(normalize_date(reference), "%d.%m.%Y")
    age_days = (reference_day - issued).days
    if issued.weekday() not in {0, 2}:
        raise A1ValidationError("Provisional issue date must be Monday or Wednesday")
    if not 61 <= age_days <= 180:
        raise A1ValidationError(
            "Provisional issue date must be 61–180 days before reference"
        )
    return normalized


# Czech OSSZ policy window: client-confirmation issue dates are scheduled on
# Monday (0) or Wednesday (2), 2-6 months back from the review reference date.
ISSUE_DATE_WEEKDAYS = (0, 2)
ISSUE_DATE_MIN_AGE_DAYS = 61
ISSUE_DATE_MAX_AGE_DAYS = 180


def generate_provisional_issue_date(
    reference: str | None = None, rng: random.Random | None = None
) -> str:
    """Generate a provisional issue date in DD.MM.YYYY form.

    The date is a Monday or Wednesday within the 2-6 month window ending on the
    reference day (default: today). Used to populate new cohort entries when the
    operator has not yet supplied an authoritative OSSZ-issued date.
    """
    rng = rng or random.Random()
    reference_day = (
        datetime.strptime(normalize_date(reference), "%d.%m.%Y")
        if reference
        else datetime.now()
    )
    # Enumerate every Mon and Wed in the policy window, then pick one randomly.
    candidates: list[datetime] = []
    day = reference_day - timedelta(days=ISSUE_DATE_MIN_AGE_DAYS)
    end_day = reference_day - timedelta(days=ISSUE_DATE_MAX_AGE_DAYS)
    while day >= end_day:
        if day.weekday() in ISSUE_DATE_WEEKDAYS:
            candidates.append(day)
        day -= timedelta(days=1)
    if not candidates:
        raise A1ValidationError("Cannot place an issue date within the policy window")
    return rng.choice(candidates).strftime("%d.%m.%Y")


# Czech OSSZ certificate number format: N{office}{sequence}S{sequence}/{year}/{member_state}
# Example: N65023S444/2026/DE. Year MUST match the 6.10 issue_date year.
DOCUMENT_ID_PATTERN = re.compile(r"^N\d{5}S\d{3}/(\d{4})/([A-Z]{2})$")


def generate_provisional_document_id(
    issue_date: str,
    member_state: str = "DE",
    rng: random.Random | None = None,
    office_code: int = 65023,
) -> str:
    """Generate a provisional Czech OSSZ certificate number for an issue date.

    Format: N{office_code}S{sequence}/{year}/{member_state}, e.g.
    N65023S444/2026/DE. The embedded ``/YYYY/`` year is bound to the supplied
    ``issue_date`` year. The 3-digit sequence is randomly drawn from
    1-999 so each generated ID has low collision risk across a half-year cohort.
    """
    rng = rng or random.Random()
    year = int(issue_date[-4:])
    sequence = rng.randint(1, 999)
    return f"N{office_code:05d}S{sequence:03d}/{year:04d}/{member_state.upper()}"


def document_id_for_issue_year(document_id: str, issue_date: str) -> str:
    """Bind a certificate number to its 6.10 issue-date year.

    The certificate number stays constant across all three pages of a person's
    PDF and unique per person.  Its embedded ``/YYYY/`` year must reflect the
    year shown in section 6.10: a ``{year}`` token is substituted with the issue
    year, otherwise an explicit ``/YYYY/`` is validated and left untouched so
    the same number is reused verbatim on every page.
    """
    issue_year = int(issue_date[-4:])
    if "{year}" in document_id:
        return document_id.replace("{year}", f"{issue_year:04d}")
    match = re.search(r"/(\d{4})/", document_id)
    if match and int(match.group(1)) != issue_year:
        raise A1ValidationError(
            f"document_id {document_id} year does not reflect 6.10 issue year {issue_year}"
        )
    return document_id


def provisional_one_year_period(start_value: str) -> tuple[str, str]:
    """Return A1 fields 2.2/2.3 for a one-year inclusive provisional period."""
    start_text = normalize_date(start_value)
    start = datetime.strptime(start_text, "%d.%m.%Y")
    try:
        anniversary = start.replace(year=start.year + 1)
    except ValueError:  # 29 February -> 28 February in the following year.
        anniversary = start.replace(year=start.year + 1, day=28)
    end = anniversary - timedelta(days=1)
    return start_text, end.strftime("%d.%m.%Y")


def _key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return (
        "".join(char for char in text if not unicodedata.combining(char))
        .casefold()
        .strip()
    )


def czech_display_case(value: str | None) -> str:
    """Convert scan-style uppercase names/places/streets to Czech display casing."""
    if not value:
        return ""
    keep_upper = {"CZ", "DE", "EU", "OSSZ", "ÚSSZ", "SRN"}
    lower_inside = {
        "a",
        "i",
        "k",
        "ke",
        "na",
        "nad",
        "od",
        "pod",
        "pro",
        "u",
        "v",
        "ve",
        "z",
        "ze",
    }
    words = []
    for index, word in enumerate(value.strip().split()):
        if word.upper() in keep_upper:
            words.append(word.upper())
            continue
        parts = word.lower().split("-")
        rendered = []
        for part_index, part in enumerate(parts):
            if index > 0 and part_index == 0 and part in lower_inside:
                rendered.append(part)
            else:
                rendered.append(part[:1].upper() + part[1:])
        words.append("-".join(rendered))
    return " ".join(words)


def enrich_residence(
    residence: dict[str, Any], rules_config: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply only exact, evidence-backed municipality/address enrichment rules."""
    result = deepcopy(residence)
    evidence: list[dict[str, Any]] = []
    for rule in rules_config.get("rules", []):
        if _key(rule.get("city")) != _key(result.get("city")):
            continue
        if rule.get("district") and _key(rule["district"]) != _key(
            result.get("district")
        ):
            continue
        if rule.get("street") and _key(rule["street"]) != _key(result.get("street")):
            continue
        if rule.get("house_number") and _key(rule["house_number"]) != _key(
            result.get("house_number")
        ):
            continue
        for field in ("postal_code", "administrative_district", "ossz"):
            if rule.get(field) and not result.get(field):
                result[field] = rule[field]
        evidence.append(
            {
                "source": rule.get("source", ""),
                "verified_on": rule.get("verified_on", ""),
                "fields": [
                    field
                    for field in ("postal_code", "administrative_district", "ossz")
                    if rule.get(field)
                ],
            }
        )
        break
    return result, evidence


def _full_address(data: dict[str, Any]) -> str:
    return " ".join(
        part for part in (data.get("street", ""), data.get("house_number", "")) if part
    )


# Fields whose display values come from OCR scans and need display casing.
# Codes (CZ, DE, OSSZ) are preserved as-is by `czech_display_case`.
# Callers pass the field names that exist on their section dict:
# - person: surname, given_name, maiden_name, birth_place
# - residence / employment: street, city, district, employer_name
_DISPLAY_CASE_FIELDS = (
    "surname",
    "given_name",
    "maiden_name",
    "birth_place",
    "street",
    "city",
    "district",
    "employer_name",
)


def _apply_display_casing(
    section: dict[str, Any], fields: tuple[str, ...] = _DISPLAY_CASE_FIELDS
) -> None:
    """Apply Czech display casing to text fields in-place.

    Defensive guard so any caller of ``build_form_data`` gets the same display
    casing the canonical ``row_to_form`` pipeline produces. Pure codes such as
    ``CZ`` and ``OSSZ`` are preserved by ``czech_display_case``.
    """
    for field in fields:
        value = section.get(field, "")
        if isinstance(value, str) and value and value.isupper():
            section[field] = czech_display_case(value)


def build_form_data(
    employee: dict[str, Any],
    institution_config: dict[str, Any],
    *,
    application_draft: bool = False,
    completion_preview: bool = False,
) -> dict[str, Any]:
    """Create the only flat data model accepted by the renderer."""
    if completion_preview and not application_draft:
        raise A1ValidationError(
            "Completion previews require an unverified draft notice"
        )
    person = deepcopy(employee.get("person", {}))
    source_nationality = person.get("nationality", "")
    if _key(source_nationality) in {"ceska republika", "czech republic", "cz", "cze"}:
        person["nationality"] = "CZ"
    _apply_display_casing(
        person, ("surname", "given_name", "maiden_name", "birth_place")
    )
    residence = deepcopy(employee.get("residence", {}))
    employment = deepcopy(employee.get("employment", {}))
    _apply_display_casing(residence, ("street", "city", "district"))
    _apply_display_casing(employment, ("employer_name", "street", "city"))
    certificate = deepcopy(institution_config.get("certificate", {}))
    certificate.update(employee.get("certificate", {}))
    institution = deepcopy(institution_config.get("institution", {}))

    # Situation is source-backed only: the reviewed status profile selects the
    # checkboxes. It is never guessed from other employee fields.
    a1 = employee.get("a1") or {}
    status_profile = str(a1.get("status_profile", "")).strip()
    if status_profile not in A1_STATUS_PROFILES:
        if completion_preview and not status_profile:
            # Undecided completion worksheet: no status checkbox is selected and
            # no situation is claimed; the choice is reported as a missing field.
            pass
        else:
            raise A1ValidationError(
                f"Missing or unsupported a1.status_profile: {status_profile!r}; expected one of "
                ", ".join(A1_STATUS_PROFILES) + " "
                "(a coarse activity_profile such as 'employee' is not an A1 status profile)"
            )
    # Enrich residence with address rules
    address_rules = load_json(ROOT / "config" / "address_enrichment.json")
    enriched_residence, _ = enrich_residence(residence, address_rules)
    _apply_display_casing(enriched_residence)
    residence = enriched_residence

    # For the provisional self-employed multi-state profile, the employer is the
    # person themselves. Derive the Section 4 employer block deterministically from
    # reviewed source data only (identity number -> employer_id, the person's own
    # surname/given -> employer_name without OSVČ suffix, residence -> employer
    # address). This is source-derived, not invented, and matches the reference
    # form structure where 4.3 shows the person's name only.
    if status_profile == "self_employed_multi_state":
        if not employment.get("employer_id"):
            employment["employer_id"] = person.get("insurance_number", "")
        employer_name = (
            f"{person.get('surname', '')} {person.get('given_name', '')}".strip()
        )
        if employer_name:
            employment["employer_name"] = czech_display_case(employer_name)
        for field in ("street", "house_number", "city", "postal_code", "country_code"):
            if not employment.get(field):
                employment[field] = residence.get(field, "")
        # Re-apply display casing to the employment block after the residence copy,
        # because the copy may have re-introduced uppercase values.
        _apply_display_casing(employment, ("employer_name", "street", "city"))
        employment.setdefault("kind", "self_employed")

    employment["kind"] = (
        "self_employed" if status_profile == "self_employed_multi_state" else "employee"
    )
    document_id = certificate.get("document_id") or certificate.get(
        "document_id_prefix", ""
    )
    institution_profile = str(a1.get("institution_profile", "")).strip()
    form = {
        "meta": {
            "employee_id": employee.get("id", ""),
            "application_draft": application_draft,
            "completion_preview": completion_preview,
            "status_profile": status_profile,
            "resolved_ossz": residence.get("ossz", ""),
            "institution_source": (
                f"config/institutions/{institution_profile}.json"
                if institution_profile
                else ""
            ),
            "source_nationality": source_nationality,
        },
        "person": {
            **person,
            "dob": normalize_date(person.get("dob")) if person.get("dob") else "",
        },
        "residence": residence,
        "employment": employment,
        "certificate": {
            **certificate,
            "start_date": normalize_date(certificate.get("start_date"))
            if certificate.get("start_date")
            else "",
            "end_date": normalize_date(certificate.get("end_date"))
            if certificate.get("end_date")
            else "",
            "document_id": document_id,
            "member_state": certificate.get("member_state", ""),
        },
        "institution": {
            **institution,
            "issue_date": normalize_date(
                employee.get("institution", {}).get("issue_date")
                or institution_config.get("issue_date", "")
            )
            if (
                employee.get("institution", {}).get("issue_date")
                or institution_config.get("issue_date")
            )
            else "",
            "signed_by": employee.get("institution", {}).get("signed_by")
            or institution_config.get("signed_by", ""),
            "contact_person_1": employee.get("institution", {}).get("contact_person_1")
            or institution_config.get("contact_person_1", ""),
            "contact_title_1": employee.get("institution", {}).get("contact_title_1")
            or institution_config.get("contact_title_1", ""),
        },
        "activity": deepcopy(employee.get("activity", {}))
        if (
            status_profile
            in {"self_employed_multi_state", "employee_multi_state", "posted_employee"}
            or completion_preview
        )
        else {},
        # Checkboxes: derived from the reviewed status profile.
        "status_posted_employee": status_profile == "posted_employee",
        "status_employee_multistate": status_profile == "employee_multi_state",
        "status_posted_self_employed": False,  # Not derivable from current profiles.
        "status_osv_c_multistate": status_profile == "self_employed_multi_state",
        "employer_type_employee": status_profile
        in {"employee_multi_state", "posted_employee"},
        "employer_type_self_employed": status_profile == "self_employed_multi_state",
        # Gender: from person
        "gender_male": person.get("sex") == "M",
        "gender_female": person.get("sex") == "F",
        # Valid duration: checked when certificate has a specific validity period.
        "valid_duration": bool(
            certificate.get("start_date") and certificate.get("end_date")
        ),
        "provisional": False,
        "transitional_rules": False,
        # No reviewed source field exists for this checkbox yet.
        "no_fixed_address": False,
    }
    validate_form_data(form)
    return form


def mark_provisional(
    form: dict[str, Any], reason: str, visible_notice: bool = False
) -> dict[str, Any]:
    """Mark a form as non-final when certificate facts are temporary placeholders.

    Jurisdiction may be resolved from exact address evidence by ``enrich_residence``.
    The current director/contact from an official OSSZ page is only an office contact;
    it is not proof that this person issued or signed the future certificate.
    """
    result = deepcopy(form)
    result.setdefault("meta", {})["provisional"] = True
    result["meta"]["provisional_reason"] = reason
    result["meta"]["provisional_notice_visible"] = visible_notice
    # Client-copy presentation only: retain reviewed activity in the source and
    # in application drafts, but leave Section 5.1 blank on provisional copies.
    if (
        result["meta"].get("status_profile") == "self_employed_multi_state"
        and result["meta"].get("application_draft") is not True
    ):
        result.setdefault("activity", {})["name"] = ""
    return result


def validate_form_data(form: dict[str, Any]) -> None:
    required = {
        "person": (
            "insurance_number",
            "surname",
            "given_name",
            "dob",
            "birth_place",
            "nationality",
            "sex",
        ),
        "residence": ("street", "house_number", "city", "postal_code", "country_code"),
        "certificate": ("member_state", "start_date", "end_date", "document_id"),
    }
    if form.get("meta", {}).get("application_draft") is True:
        required["certificate"] = ("member_state", "document_id")
    missing = [
        f"{section}.{field}"
        for section, fields in required.items()
        for field in fields
        if not form.get(section, {}).get(field)
    ]
    employment = form.get("employment", {})
    for field in (
        "employer_id",
        "employer_name",
        "street",
        "house_number",
        "city",
        "postal_code",
        "country_code",
    ):
        if not employment.get(field):
            missing.append(f"employment.{field}")
    if form.get("meta", {}).get("completion_preview") is True:
        if form["meta"].get("application_draft") is not True:
            raise A1ValidationError(
                "Completion previews require an unverified draft notice"
            )
        form["meta"]["missing_fields"] = sorted(missing)
        missing = [field for field in missing if field.startswith("person.")]
    if missing:
        raise A1ValidationError(
            "Missing required A1 fields: " + ", ".join(sorted(missing))
        )
    if form.get("person", {}).get("sex") not in {"M", "F"}:
        raise A1ValidationError("person.sex must be M or F")
    status_profile = form.get("meta", {}).get("status_profile")
    if status_profile not in {
        "self_employed_multi_state",
        "employee_multi_state",
        "posted_employee",
    } and not (
        form.get("meta", {}).get("completion_preview") is True and status_profile == ""
    ):
        raise A1ValidationError("Unsupported status_profile for this visual template")


def _get_path(data: dict[str, Any], path: str) -> str:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return ""
        current = current.get(part, "")
    return str(current or "")


_A1_FONT_SIGNATURE = None


def _register_font(*, require_current: bool = False) -> str:
    """Pin cached reportlab font bytes for reproducible application drafts."""
    global _A1_FONT_SIGNATURE
    candidate = next((path for path in FONT_CANDIDATES if path.exists()), None)
    signature = (
        (str(candidate), hashlib.sha256(candidate.read_bytes()).hexdigest())
        if candidate is not None
        else None
    )
    if "A1Sans" in pdfmetrics.getRegisteredFontNames():
        if require_current and (signature is None or signature != _A1_FONT_SIGNATURE):
            raise A1ValidationError("APPLICATION_DRAFT_FONT_CACHE_CHANGED")
        return "A1Sans"
    if candidate is not None:
        pdfmetrics.registerFont(TTFont("A1Sans", str(candidate)))
        _A1_FONT_SIGNATURE = signature
        if (
            require_current
            and hashlib.sha256(candidate.read_bytes()).hexdigest() != signature[1]
        ):
            raise A1ValidationError("APPLICATION_DRAFT_FONT_CHANGED")
        return "A1Sans"
    if require_current:
        raise A1ValidationError("APPLICATION_DRAFT_FONT_UNAVAILABLE")
    return "Helvetica"


def _fit_font(text: str, font: str, size: float, max_width: float) -> float:
    while size > 6 and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.25
    return size


# X mark stroke color and width for all checkboxes. Matches the official
# A1 2025 form's dark blue X over the gray checkbox squares.
CHECKBOX_X_COLOR = (0.05, 0.35, 0.48)
CHECKBOX_X_LINE_WIDTH = 0.8
# Keep the full stroke inside the original template's checkbox border.
CHECKBOX_X_INSET = 1.0


def _draw_check_x(c: canvas.Canvas, x: float, y: float, size: float) -> None:
    """Draw a manual X mark inside the empty checkbox at (x, y, size).

    The template background provides the empty checkbox square; this function
    only paints the cross. Coordinates are the bottom-left corner of the box.
    """
    inset = CHECKBOX_X_INSET
    c.setStrokeColorRGB(*CHECKBOX_X_COLOR)
    c.setLineWidth(CHECKBOX_X_LINE_WIDTH)
    c.line(x + inset, y + inset, x + size - inset, y + size - inset)
    c.line(x + size - inset, y + inset, x + inset, y + size - inset)


def _draw_checkboxes_for_page(
    c: canvas.Canvas,
    layout: dict[str, Any],
    form: dict[str, Any],
    page_number: int,
    font: str,
) -> None:
    """Draw the X marks for every checked checkbox on ``page_number``.

    Each checkbox layout entry may declare an ``area`` key (a JSON-pointer-like
    reference to ``field_areas``) so the script can stay decoupled from raw
    magic numbers. Coordinates still live in the layout for round-trip ease.
    """
    for field, cfg in layout.get("checkboxes", {}).items():
        if int(cfg.get("page", -1)) != page_number:
            continue
        if not form.get(field):
            continue
        x = float(cfg["x"])
        y = float(cfg["y"])
        size = float(cfg.get("size", 7.4))
        _draw_check_x(c, x, y, size)


def _draw_field(c: canvas.Canvas, value: str, cfg: dict[str, Any], font: str) -> None:
    if not value:
        return
    size = float(cfg.get("size", 9))
    max_width = float(cfg.get("max_width", 400))
    max_lines = int(cfg.get("max_lines", 1))
    line_height = float(cfg.get("line_height", size + 2))
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and pdfmetrics.stringWidth(candidate, font, size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = [value]
        max_lines = 1
        size = _fit_font(value, font, size, max_width)
    for index, line in enumerate(lines[:max_lines]):
        line_size = _fit_font(line, font, size, max_width)
        c.setFont(font, line_size)
        c.drawString(float(cfg["x"]), float(cfg["y"]) - index * line_height, line)


def _draw_form_header(
    c: canvas.Canvas, page_number: int, doc_id: str, font: str
) -> None:
    """Draw only dynamic form data not present in the static background template.

    The A1 2025 background template already includes the title, subtitle,
    section labels, page numbers, and form headers. This function adds the
    document ID at the top-left of every page (template has no doc id anywhere).
    All other overlay text would duplicate template content.
    """
    if doc_id:
        c.setFillColorRGB(0.07, 0.07, 0.07)
        c.setFont(font, 9)
        # Keep the number in the white margin above the static A1/EU banner.
        c.drawString(72, PAGE_SIZE[1] - 42, doc_id)


def render_overlay(form: dict[str, Any], layout: dict[str, Any]) -> BytesIO:
    font = _register_font(
        require_current=form.get("meta", {}).get("application_draft") is True
    )
    buffer = BytesIO()
    c = canvas.Canvas(
        buffer,
        pagesize=PAGE_SIZE,
        invariant=form.get("meta", {}).get("application_draft") is True,
    )
    fields_by_page: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    for field_name, cfg in layout["fields"].items():
        fields_by_page.setdefault(int(cfg["page"]), []).append((field_name, cfg))

    computed = {
        "residence.address": _full_address(form["residence"]),
        "employment.address": _full_address(form["employment"]),
        "institution.address": _full_address(form["institution"]),
    }
    page_count = int(layout.get("page_count", 3))
    doc_id = form.get("certificate", {}).get("document_id", "")
    for page_number in range(page_count):
        for field_name, cfg in fields_by_page.get(page_number, []):
            value = computed.get(
                field_name, _get_path(form, cfg.get("source", field_name))
            )
            _draw_field(
                c, display_value(cfg.get("source", field_name), value), cfg, font
            )
        c.saveState()
        _draw_form_header(c, page_number, doc_id, font)
        _draw_checkboxes_for_page(c, layout, form, page_number, font)
        c.restoreState()
        if form.get("meta", {}).get("application_draft") is True or form.get(
            "meta", {}
        ).get("provisional_notice_visible"):
            c.saveState()
            c.setFillColorRGB(0.78, 0.12, 0.12)
            c.setFillAlpha(0.75)
            c.setFont(font, 7)
            c.drawRightString(
                PAGE_SIZE[0] - 35,
                18,
                APPLICATION_DRAFT_NOTICE
                if form.get("meta", {}).get("application_draft") is True
                else PROVISIONAL_NOTICE,
            )
            c.restoreState()
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_a1_pdf(
    form: dict[str, Any],
    background_pdf: str | Path,
    layout_json: str | Path,
    output_pdf: str | Path,
) -> Path:
    """Render the A1 form data onto the official A1 2025 background.

    Two PDF frameworks are available for this task:

    - ``scripts.pdf_named_fields`` (preferred default): placeholder
      search-and-replace against a vector-backed template.
    - The coordinate overlay in this file (fallback): rendered text
      drawn at fixed coordinates on top of the image-backed A1 2025
      background.

    The current A1 2025 background is image-backed, so we use the
    coordinate overlay. The page merge re-uses the canonical
    overlay buffer so values flow through a single source of truth
    (``build_form_data``).
    """
    validate_form_data(form)
    layout = load_json(layout_json)
    background = PdfReader(str(background_pdf))
    if len(background.pages) != layout.get("page_count", 3):
        raise A1ValidationError("A1 background and layout page counts differ")
    overlay_buffer = render_overlay(form, layout)
    output = Path(output_pdf)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Merge the overlay onto the background using pypdf's merge_page.
    # Earlier experiments with pymupdf's show_pdf_page showed that
    # pymupdf re-encodes the overlay's text into a Form XObject and
    # can split comma-separated text operands. The overlay buffer
    # is a known good PDF; the merge step below preserves its text.
    # Build a fresh page tree, as in the original generator. Attach pages
    # before merging so pypdf owns their content streams.
    writer = PdfWriter()
    overlay = PdfReader(overlay_buffer)
    for index, source_page in enumerate(background.pages):
        page = writer.add_page(source_page)
        page.merge_page(overlay.pages[index])
    # The original image-backed PDF used ASCII85 around its image data.
    # Apply the same lossless transport encoding to images so compressed
    # bytes cannot look like Unicode line/paragraph separators to consumers.
    for obj in writer._objects:
        if not isinstance(obj, StreamObject) or obj.get("/Subtype") != "/Image":
            continue
        filters = obj.get("/Filter")
        filters = (
            list(filters)
            if isinstance(filters, ArrayObject)
            else ([filters] if filters else [])
        )
        params = obj.get("/DecodeParms")
        if params is not None:
            params = list(params) if isinstance(params, ArrayObject) else [params]
            obj[NameObject("/DecodeParms")] = ArrayObject([NullObject(), *params])
        obj._data = base64.a85encode(obj._data, adobe=True)[2:]
        obj[NameObject("/Filter")] = ArrayObject(
            [NameObject("/ASCII85Decode"), *filters]
        )
    with output.open("wb") as stream:
        writer.write(stream)
    reopened = PdfReader(str(output))
    if len(reopened.pages) != 3 or reopened.get_fields():
        raise A1ValidationError(
            "Generated A1 failed static-PDF structural verification"
        )
    return output
