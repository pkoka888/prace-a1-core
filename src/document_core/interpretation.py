"""Conservative CZ label and ICAO MRZ interpretation; outputs are proposals.

References: ICAO Doc 9303 parts 4/5; EU Decision S2, Annex I (EHIC fields 3–9).
Unsupported layouts remain uncertain, rather than using a universal coordinate map.
"""
import re
import unicodedata
from datetime import datetime


def normalized(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text)
                             if not unicodedata.combining(c)).upper().split())


def check_digit(text):
    values = {c: i for i, c in enumerate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
    values["<"] = 0
    return str(sum(values[c] * (7, 3, 1)[i % 3] for i, c in enumerate(text)) % 10)


def parse_mrz(regions):
    candidates = [(re.sub(r"\s", "", normalized(r.text)), r) for r in regions]
    candidates = [(s, r) for s, r in candidates if len(s) in (30, 44) and re.fullmatch(r"[A-Z0-9<]+", s)]
    for i, (first, _) in enumerate(candidates):
        td1 = len(first) == 30 and first.startswith(("I", "A", "C"))
        td3 = len(first) == 44 and first.startswith("P")
        n = 3 if td1 else 2
        group = candidates[i:i+n]
        if not (td1 or td3) or len(group) != n or any(len(s) != len(first) for s, _ in group):
            continue
        a, b = group[0][0], group[1][0]
        if td1:
            names = group[2][0]
            number, birth, expiry = a[5:14], b[:6], b[8:14]
            checks = [(number, a[14]), (birth, b[6]), (expiry, b[14]),
                      (a[5:30]+b[:7]+b[8:15]+b[18:29], b[29])]
            nationality, sex = b[15:18], b[7]
        else:
            names = a[5:]
            number, birth, expiry = b[:9], b[13:19], b[21:27]
            checks = [(number, b[9]), (birth, b[19]), (expiry, b[27]),
                      (b[:10]+b[13:20]+b[21:43], b[43])]
            if b[28:42].strip("<"):
                checks.append((b[28:42], b[42]))
            nationality, sex = b[10:13], b[20]
        valid = all(check_digit(value) == digit for value, digit in checks)
        # Validate day/month without silently deciding the century.
        for date in (birth, expiry):
            try:
                datetime.strptime("20" + date, "%Y%m%d")
            except ValueError:
                valid = False
        parts = names.split("<<", 1)
        return {"format": "td1" if td1 else "td3", "issuer": a[2:5], "valid": valid,
                "document_number": number.rstrip("<"), "birth_yymmdd": birth,
                "expiry_yymmdd": expiry, "family_name": parts[0].replace("<", " ").strip(),
                "given_name": parts[1].replace("<", " ").strip() if len(parts) > 1 else "",
                "nationality": nationality, "sex": sex,
                "region_ids": [r.region_id for _, r in group]}
    return None


class Classifier:
    def classify(self, regions):
        text = normalized(" ".join(r.text for r in regions))
        mrz = parse_mrz(regions)
        cz = "CESKA REPUBLIKA" in text or bool(re.search(r"\b(CZE|CZ)\b", text))
        if mrz:
            cz = mrz["issuer"] == "CZE"
        op = "OBCANSKY PRUKAZ" in text or bool(mrz and mrz["format"] == "td1")
        passport = "CESTOVNI PAS" in text or bool(mrz and mrz["format"] == "td3")
        zp = any(t in text for t in ("EUROPEAN HEALTH INSURANCE CARD", "EVROPSKY PRUKAZ ZDRAVOTNIHO POJISTENI", "EHIC"))
        kinds = [kind for kind, present in (("op", op), ("passport", passport), ("zp", zp)) if present]
        if len(kinds) != 1 or not cz:
            return {"type": None, "country": "cz" if cz else None, "version": None,
                    "side": None, "confidence": .3, "uncertainty_reason": "mixed_or_unsupported_layout",
                    "mrz": mrz, "evidence": [r.region_id for r in regions]}
        kind = kinds[0]
        side = None
        if kind == "op":
            side = "back" if (mrz or "TRVALY POBYT" in text or "MISTO TRVALEHO POBYTU" in text) else "front"
        return {"type": kind, "country": "cz", "side": side,
                "version": mrz["format"] if mrz else ("ehic_s2" if kind == "zp" else None),
                "confidence": .9 if mrz and mrz["valid"] else .8,
                "uncertainty_reason": None if mrz or kind == "zp" else "visual_edition_unresolved",
                "mrz": mrz, "evidence": [r.region_id for r in regions]}


# Longest label first; dates never match an unlabelled generic date regex.
LABELS = {
    "family_name": ("PRIJMENI", "SURNAME", "LAST NAME"),
    "given_name": ("JMENA", "JMENO", "GIVEN NAMES", "GIVEN NAME", "FORENAMES"),
    "birth_date": ("DATUM NAROZENI", "DATE OF BIRTH"),
    "expiry_date": ("PLATNOST DO", "DATUM SKONCENI PLATNOSTI", "DATUM KONCE PLATNOSTI", "DATE OF EXPIRY", "EXPIRY DATE", "PLATNOST"),
    "issue_date": ("DATUM VYDANI", "DATE OF ISSUE"),
    "document_number": ("CISLO DOKLADU", "CISLO OBCANSKEHO PRUKAZU", "CISLO PASU", "DOCUMENT NO", "PASSPORT NO"),
    "personal_identifier": ("RODNE CISLO",),
    "insurance_number": ("CISLO POJISTENCE", "PERSONAL IDENTIFICATION NUMBER", "IDENTIFIKACNI CISLO OSOBY"),
    "card_number": ("CISLO PRUKAZU", "CISLO KARTY", "IDENTIFICATION NUMBER OF THE CARD", "IDENTIFIKACNI CISLO PRUKAZU"),
    "insurer": ("KOD POJISTOVNY", "IDENTIFICATION NUMBER OF THE INSTITUTION", "IDENTIFIKACNI CISLO INSTITUCE"),
    "residence_address": ("MISTO TRVALEHO POBYTU", "TRVALY POBYT", "ADRESA POBYTU"),
    "birth_place": ("MISTO NAROZENI", "PLACE OF BIRTH"),
    "nationality": ("STATNI OBCANSTVI", "NATIONALITY"),
    "sex": ("POHLAVI", "SEX"),
    "issuing_authority": ("VYDAL", "ISSUING AUTHORITY"),
}
EHIC_NUMBERS = {"3": "family_name", "4": "given_name", "5": "birth_date", "6": "insurance_number",
                "7": "insurer", "8": "card_number", "9": "expiry_date"}
IDENTIFIERS = {"document_number", "insurance_number", "personal_identifier", "card_number"}


def label_value(text, ehic=False):
    clean = normalized(text)
    prefix = re.match(r"^(\d)[. )]+", clean)
    if prefix:
        start = prefix.end()
        clean = clean[start:]
    else:
        start = 0
    for field, labels in LABELS.items():
        for label in sorted(labels, key=len, reverse=True):
            if clean == label or clean.startswith(label + ":") or clean.startswith(label + " ") or clean.startswith(label + "/"):
                offset = start + len(label)
                value = text[offset:].lstrip(" :./")
                # A bilingual label can occupy one OCR box; never treat its translation as the value.
                for alias in sorted(labels, key=len, reverse=True):
                    remaining = normalized(value)
                    if remaining == alias or remaining.startswith(alias + ":") or remaining.startswith(alias + " "):
                        value = value[len(alias):].lstrip(" :./")
                        break
                return field, value
    if ehic and prefix and prefix[1] in EHIC_NUMBERS:
        return EHIC_NUMBERS[prefix[1]], text[start:].strip()
    return None


def valid_value(field, value):
    value = " ".join(value.split())
    if field.endswith("_date"):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date().isoformat(), []
            except ValueError:
                return value, ["invalid_date"]
        match = re.fullmatch(r"(\d{1,2})[. /-](\d{1,2})[. /-](\d{4})", value)
        if not match:
            return value, ["invalid_date"]
        try:
            return datetime(int(match[3]), int(match[2]), int(match[1])).date().isoformat(), []
        except ValueError:
            return value, ["invalid_date"]
    if field == "sex":
        value = {"Z": "F", "ZENA": "F", "MUZ": "M"}.get(normalized(value), normalized(value))
    if field == "nationality" and normalized(value) in ("CZ", "CZE", "CESKA REPUBLIKA"):
        value = "CZE"
    if field in IDENTIFIERS:
        value = re.sub(r"\s", "", value).upper()
        if not re.fullmatch(r"[A-Z0-9/]{3,30}", value):
            return value, ["invalid_identifier"]
    return value, []


class FieldInterpreter:
    def interpret(self, regions, classification):
        if not classification["type"]:
            return [], ["classification_unresolved"]
        fields = []
        ehic = classification["type"] == "zp"
        for region in regions:
            labelled = label_value(region.text, ehic)
            if not labelled:
                continue
            field, raw_value = labelled
            evidence = [region.region_id]
            if not raw_value and region.polygon:
                x, y = min(p[0] for p in region.polygon), max(p[1] for p in region.polygon)
                height = max(1, y - min(p[1] for p in region.polygon))
                candidates = [r for r in regions if r is not region and r.polygon and
                              not label_value(r.text, ehic) and
                              ((0 <= min(p[1] for p in r.polygon)-y <= height*2 and
                                abs(min(p[0] for p in r.polygon)-x) <= height*3) or
                               (abs(min(p[1] for p in r.polygon)-(y-height)) <= height*.5 and
                                0 <= min(p[0] for p in r.polygon)-max(p[0] for p in region.polygon) <= height*4))]
                candidates.sort(key=lambda r: min(p[1] for p in r.polygon))
                if len(candidates) == 1:
                    raw_value = candidates[0].text
                    evidence.append(candidates[0].region_id)
            if not raw_value:
                continue
            value, findings = valid_value(field, raw_value)
            fields.append({"field": field, "value": value, "raw_text": raw_value,
                           "confidence": region.confidence, "evidence": evidence,
                           "findings": findings, "source": "visual", "accepted": False})
        mrz = classification.get("mrz")
        findings = []
        if mrz and not mrz["valid"]:
            findings.append("mrz_checksum_or_date_invalid")
        if mrz and mrz["valid"]:
            for key in ("document_number", "family_name", "given_name", "nationality", "sex"):
                if mrz[key]:
                    fields.append({"field": key, "value": mrz[key], "raw_text": mrz[key],
                                   "confidence": min(r.confidence for r in regions if r.region_id in mrz["region_ids"]),
                                   "evidence": mrz["region_ids"], "findings": [], "source": "mrz", "accepted": False})
            for field, key in (("birth_date", "birth_yymmdd"), ("expiry_date", "expiry_yymmdd")):
                visual = [f for f in fields if f["field"] == field and not f["findings"]]
                if not visual:
                    findings.append(field + "_century_unresolved")
                elif any(f["value"].replace("-", "")[2:] != mrz[key] for f in visual):
                    findings.append(field + "_mrz_disagreement")
        values = {}
        for f in fields:
            values.setdefault(f["field"], set()).add(normalized(f["value"]))
        for f in fields:
            if len(values[f["field"]]) > 1:
                f["findings"].append("conflicting_values")
        return fields, findings
