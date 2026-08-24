# A1 PDF Production — Semi-Manual Framework

## Overview

This framework generates provisional A1 certificate PDFs for Czech/German cross-border workers from identity card scans. It is a **semi-manual** pipeline: scans are uploaded, identity data is extracted via OCR (human-verified), and PDFs are generated through a deterministic pipeline with automated quality gates.

**PII handling:** All scans, extracted identity data, and generated PDFs are PII. They reside only in gitignored private directories (`a1/`, `scans/`, `output/`). See [`AGENTS.md`](../../AGENTS.md) and [`docs/security/real-data-rules.md`](../../docs/security/real-data-rules.md) before any operation.

---

## File Map

### Core Scripts

| File | Purpose |
|------|---------|
| `scripts/generate_provisional_a1.py` | **Canonical entry point.** Reads `a1/review.csv` + `a1/cohort.json`, composes form data, renders PDFs to `output/provisional/`. |
| `scripts/finalize_a1.py` | Composes per-employee form data from CSV rows + institution profiles. Called by `generate_provisional_a1.py`. |
| `scripts/a1_core.py` | Static overlay renderer + form validation. Handles font registration, field placement, PDF stamping. |
| `scripts/a1_quality_gate.py` | QA pipeline: `render` (300 DPI previews), `validate` (structural checks), `record-review` (hash-bound operator sign-off). |
| `scripts/a1_private.py` | Per-employee private manifest builder. |

### OCR Pipeline

| File | Purpose |
|------|---------|
| `ocr/_ocr_worker.py` | **Active OCR script.** Sends scans to `minimax/minimax-01` via OpenRouter, extracts JSON identity fields. Moves processed scans to `scans/processed/` after success. |
| `ocr/validate_ocr_proposals.py` | Validates OCR JSON proposals against expected schema. |
| `ocr/run_ocr_benchmark.py` | Benchmark harness for OCR model evaluation. |

### Data Directories

| Directory | Content |
|-----------|---------|
| `a1/review.csv` | **Authoritative identity source.** One row per employee. All Section 1–4 fields after human transcription. |
| `a1/cohort.json` | **Cohort metadata.** Issue dates, document IDs, and `additional_people` entries (people in CSV but not yet promoted). |
| `a1/employees_normalized.json` | Normalized employee records for internal use. |
| `scans/` | **Source scans.** Named `{employee_id}-op{N}.jpeg` (OP = občanský průkaz), `{employee_id}-zp{N}.jpeg` (ZP = health insurance card). |
| `scans/processed/` | Scans that have been successfully OCR'd and moved. Original filenames preserved. |
| `ocr/new_scans_ocr2.json` | Latest OCR results from `_ocr_worker.py`. Not authoritative — human review required. |
| `ocr/new_scans_ocr.json` | Legacy OCR results. Superseded by `new_scans_ocr2.json`. |
| `ocr/new_scans_merged.json` | Merged OCR outputs. |
| `ocr/new_people_review.csv` | OCR-extracted entries pending human review. |

### Output Directories

| Directory | Content |
|-----------|---------|
| `output/provisional/` | **Staging area.** 3-page PDFs named `A1_{employee_id}.pdf`. Not for client delivery. |
| `output/previews/` | 300 DPI PNG renders of every PDF page. Used for visual QA. |
| `output/contactsheets/` | 3-page contact sheets (3-column grid of all workers per page). |
| `output/pdf/` | **Final approved PDFs.** Only promoted here after `validated_by_user=1` + operator sign-off. |
| `output/quarantine-*/` | PDFs that failed QA — quarantined with hashes for audit. |

### Configuration

| File | Purpose |
|------|---------|
| `config/a1_layout.json` | Field positions (x, y, page, source mapping) for PDF overlay. |
| `config/a1_provisional.json` | Non-personal provisional policy and placeholder text. **Never an identity source.** |
| `config/institutions/{name}.json` | OSSZ office data (name, address, signatory). **Must be VERIFIED before use.** |
| `config/address_enrichment.json` | Residence address normalization rules. |
| `templates/a1_background.pdf` | Static 3-page A1 form template. |

---

## Workflow

### Phase 0 — Setup (One Time)

```bash
# Set environment
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
cd $A1_PRIVATE_DIR

# Python environment
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

---

### Phase 1 — Scan Upload (Operator)

1. **Upload scans** to `scans/` with naming convention:
   - OP (identity card): `{employee_id}-op{N}.jpeg`
   - ZP (health card): `{employee_id}-zp{N}.jpeg`
   - Example: `hucko-martin-op1.jpeg`, `hucko-martin-op2.jpeg`, `hucko-martin-zp1.jpeg`

2. Scans stay in `scans/` until OCR completes, then `_ocr_worker.py` moves them to `scans/processed/`.

---

### Phase 2 — OCR Extraction (Internal + MiniMax API)

```bash
cd $A1_PRIVATE_DIR
python3 ocr/_ocr_worker.py
```

**What happens:**
- Lists all unscanned images in `scans/` (excludes `processed/`)
- Sends each to `minimax/minimax-01` via OpenRouter
- Extracts JSON fields: surname, given_name, dob, birth_place, nationality, sex, rodne_cislo, insurance_number, address fields, insurer, etc.
- Results saved to `ocr/new_scans_ocr2.json`
- **Processed scans auto-move to `scans/processed/`**

**What it produces:**
```json
{
  "hucko-martin-op1.jpeg": {
    "model": "minimax/minimax-01",
    "cost": 0.0,
    "fields": {
      "surname": "HUČKO",
      "given_name": "MARTIN",
      "dob": "12.08.1981",
      ...
    },
    "raw": "..."
  }
}
```

**⚠️ OCR output is a proposal only.** It must be human-verified before entry into `a1/review.csv`.

---

### Phase 3 — Transcription to review.csv (Operator)

1. **Read OCR output** from `ocr/new_scans_ocr2.json`
2. **Verify against scans** — check every field against the original images
3. **Correct diacritics** — OCR may output uppercase; convert to proper Czech casing (e.g., `HUČKO` → `Hučko`, `ŽIVOT` → `Život`)
4. **Add row to `a1/review.csv`** with all required columns:

Required columns in `a1/review.csv`:
```
employee_id, source_scans, surname, given_name, dob, birth_place, nationality, sex,
insurance_number, street, house_number, city, district, postal_code, country_code,
status_profile, activity_name, activity_address,
employment_id, employment_name, employment_street, employment_house_number,
employment_city, employment_postal_code, employment_country_code,
resolved_ossz, institution_profile, document_id, start_date, end_date, issue_date,
signed_by, identity_reviewed, certificate_reviewed, approved_for_pdf, pdf_created,
validated_by_user, activity_source, activity_source_status, certificate_source,
certificate_source_status, signatory_source, signatory_source_status, comments
```

5. **Add entry to `a1/cohort.json`**:
   - `issue_dates.{employee_id}`: Issue date (must be Monday or Thursday, 61–180 days before reference)
   - `document_ids.{employee_id}`: Certificate number (format: `N650{Sequence}S558/2026/DE`)
   - If `additional_people` entry exists, promote to main CSV and remove from `additional_people`

---

### Phase 4 — PDF Generation (Internal)

```bash
cd $A1_PRIVATE_DIR
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"

# Generate all PDFs
python3 scripts/generate_provisional_a1.py \
  --review a1/review.csv \
  --cohort a1/cohort.json \
  --output output/provisional

# Render previews
python3 scripts/a1_quality_gate.py render \
  --pdf-dir output/provisional \
  --preview-dir output/previews \
  --contact-dir output/contactsheets

# Validate
python3 scripts/a1_quality_gate.py validate \
  --pdf-dir output/provisional \
  --preview-dir output/previews \
  --report output/provisional/qa_report.json \
  --manifest output/provisional/qa_manifest.json
```

**What the generation pipeline does:**
1. Reads each CSV row → composes form data structure
2. Looks up institution profile from `config/institutions/{profile}.json`
3. Applies `czech_display_case()` to name/place fields (e.g., `HUČKO` → `Hučko`)
4. Validates all required fields present
5. Renders overlay text via `a1_core.py` onto `templates/a1_background.pdf`
6. Stamps PROVISIONAL watermark on each page
7. Writes `A1_{employee_id}.pdf` to `output/provisional/`

**Quality gate (`validate`)** checks:
- Page count = 3 per PDF
- All required text fields present
- No legacy/cross-person data contamination
- Background template integrity (0 erased pixels per page)
- Ghostscript structural validity
- AcroForm fields = 0 (flat static PDF)

---

### Phase 5 — Visual QA (Operator)

1. **Review previews** in `output/previews/` — 3 pages per worker
2. **Contact sheets** in `output/contactsheets/` — all workers gridded
3. **Check every page** for:
   - Correct diacritics (Č, Ď, Ě, Ř, Š, Ť, ů, Ž)
   - Correct name casing (not ALL CAPS for display fields)
   - Correct address, dates, document ID
   - No clipping, overlapping, or hidden text
   - Correct checkbox states
   - Correct institution name and address

4. **For each worker**, run:
```bash
python3 scripts/a1_quality_gate.py record-review \
  --employee-id {employee_id} \
  --pdf output/provisional/A1_{employee_id}.pdf \
  --review-dir output/previews \
  --outcome pass  # or fail
```

---

### Phase 6 — Final Promotion (Operator)

Only after `validated_by_user=1` in CSV AND operator visual sign-off:

```bash
# Move PDF to final output
cp output/provisional/A1_{employee_id}.pdf output/pdf/

# Mark as approved in CSV
# (set validated_by_user=1 for the row)
```

**⚠️ Provisional PDFs are NEVER the same as issued A1 certificates.**

---

## OCR Worker Reference

**Location:** `ocr/_ocr_worker.py`

**Run:** `python3 ocr/_ocr_worker.py` from repo root

**Requirements:**
- `OPENROUTER_API_KEY` in `.env` (currently set to free-tier `minimax/minimax-01`)
- All target scans present in `scans/` (not in `processed/`)
- Output written to `ocr/new_scans_ocr2.json`

**Post-processing:** On success, each scan is moved from `scans/` → `scans/processed/`

**Prompt fields extracted:**
```
surname, given_name, dob, birth_place, nationality, sex,
rodne_cislo, insurance_number, insurer,
op_valid_from, op_valid_to,
street, house_number, city, district, postal_code,
country_code, issuing_authority
```

---

## Institution Profile Reference

Each `config/institutions/{name}.json` must have:
```json
{
  "version": "1.0.0",
  "review_status": "VERIFIED",
  "source_url": "https://www.cssz.cz/...",
  "verified_on": "DD.MM.YYYY",
  "expected_ossz": "OSSZ {City}",
  "institution": {
    "name": "OSSZ {City}",
    "street": "...",
    "house_number": "...",
    "city": "...",
    "postal_code": "...",
    "country_code": "CZ",
    "code": "NNN"
  },
  "current_office_contact": {
    "name": "...",
    "role": "...",
    "status": "CONTACT_NOT_CONFIRMED_SIGNATORY"
  }
}
```

**Verified institutions currently available:** `brno`, `decin`, `frydek-mistek`, `kladno`, `most`, `novy-jicin`, `plzen`, `praha`, `teplice`, `usti-nad-labem`

---

## Validation Rules

| Rule | Constraint |
|------|------------|
| Issue date | Must be Monday or Thursday, 61–180 days before today |
| Institution profile | Must exist in `config/institutions/` and be `review_status: VERIFIED` with `source_url` + `verified_on` |
| Document ID | Format `N650{Sequence}S558/2026/DE`, unique per employee |
| Name casing | Display fields use `czech_display_case()` — not ALL CAPS |
| PDF pages | Exactly 3 pages, zero AcroForm fields |
| Cohort consistency | `issue_dates`, `document_ids`, and CSV rows must name the same set of employees |

---

## Current Cohort (15 workers)

| employee_id | institution | document_id | issue_date |
|-------------|-------------|-------------|------------|
| hlavac-renato | plzen | N65023S444/2026/DE | 12.02.2026 |
| jiri-stembera | teplice | N65022S558/2026/DE | 23.02.2026 |
| jozef-hada | most | N65024S557/2026/DE | 12.03.2026 |
| jozef-kotlar | frydek-mistek | N65025S886/2026/DE | 30.03.2026 |
| karel-kotlar | novy-jicin | N65026S888/2026/DE | 09.04.2026 |
| petr-gizman | most | N65027S557/2026/DE | 27.04.2026 |
| petr-kalcik | teplice | N65021S558/2026/DE | 14.05.2026 |
| petr-nastin | teplice | N65028S558/2026/DE | 01.06.2026 |
| robert-danko | frydek-mistek | N65029S886/2026/DE | 11.06.2026 |
| pavel-kaspar | teplice | N65030S558/2026/DE | 08.06.2026 |
| rudolf-kotlar | novy-jicin | N65031S888/2026/DE | 25.05.2026 |
| patrik-zivot | praha | N65032S558/2026/DE | 28.05.2026 |
| zimnuchov-igor-alexandrovic | brno | N65033S888/2026/DE | 18.05.2026 |
| jaroslav-simek | most | N65034S558/2026/DE | 16.04.2026 |
| hucko-martin | decin | N65035S558/2026/DE | 16.04.2026 |

---

## Quick Reference

```bash
# Full pipeline (after scans uploaded and transcribed)
cd /var/www/prace-v-nemecku.tvoje.info
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"

python3 scripts/generate_provisional_a1.py --review a1/review.csv --cohort a1/cohort.json --output output/provisional
python3 scripts/a1_quality_gate.py render --pdf-dir output/provisional --preview-dir output/previews --contact-dir output/contactsheets
python3 scripts/a1_quality_gate.py validate --pdf-dir output/provisional --preview-dir output/previews --report output/provisional/qa_report.json --manifest output/provisional/qa_manifest.json

# OCR new scans
python3 ocr/_ocr_worker.py
```
