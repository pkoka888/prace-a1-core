# A1 Form Generation — Two Frameworks, One Source

This document explains how the Czech A1 (A1) client-confirmation form is
generated end-to-end. It covers the data flow, every script that touches an
A1 artefact, and the two PDF rendering frameworks that are kept side by
side as fallbacks. Operators and engineers who need to add fields, change
the template, or migrate the data source will find a step-by-step trace
here.

## TL;DR

```text
a1/review.csv  ──┐
a1/cohort.json ──┼─►  scripts/finalize_a1.row_to_form ──►  scripts/a1_core.build_form_data  ──►  ┌─► a1_core.generate_a1_pdf     (canonical, today)
a1/employees… ──┘                                                                                │     coordinate overlay on
                                                                                                  │     templates/a1_background.pdf
                                                                                                  │
                                                                                                  └─► pdf_named_fields.replace_placeholders
                                                                                                        (preferred default, vector template
                                                                                                        needed)
```

Both renderers consume the **same** `dict[str, Any]` produced by
`scripts.a1_core.build_form_data`. They are interchangeable as long as the
template is compatible. The coordinate overlay is the active one today
because `templates/a1_background.pdf` is image-backed; the placeholder
search/replace is the preferred default for any future vector-backed
template.

## Files and responsibilities

| File | Role | When it is read | When it is written |
|---|---|---|---|
| `a1/review.csv` | Authoritative row per accepted employee (synthetic for tests, operator-managed in production) | `row_to_form` reads every column; `read_review` reads it as a list of dicts | Operator edits only |
| `a1/cohort.json` | Operator-issued `issue_dates` and `document_ids` per `employee_id` | `generate_provisional_a1.build_provisional_rows` cross-checks cohort against review | Operator edits only |
| `a1/employees_normalized.json` | Accepted identity reference (scans, dob, insurance_number) | Mismatch detection in readiness; not part of the per-employee form | OCR pipeline writes after operator review |
| `config/a1_provisional.json` | Policy defaults: `activity_name=""` (5.1 empty for self-employed), `activity_address="DE, CZ"` (5.2 destination + home), `issue_date_reference="11.08.2026"`, `validity_policy` text | `build_form_data` and `validate_provisional_issue_date` use the reference for the policy window | Operator-edited (rare) |
| `config/a1_layout.json` | Field and checkbox geometry on top of the template. Has two parts: `fields` (text), `checkboxes` (X marks). Each entry has an `area` pointer into `field_areas` for human readability | Every renderer reads this for x, y, size, max_width, source, area | Geometry changes only |
| `config/institutions/<profile>.json` | Per-OSSZ verified profile: name, street, city, postal_code, country_code, code | `build_form_data` reads it via `finalize_a1.load_profile` | Operator-edited; status is `VERIFIED` or `NEEDS_VERIFICATION` |
| `config/address_enrichment.json` | Municipality/district → postal_code, OSSZ, administrative_district rules | `enrich_residence` reads every rule on every form build | Operator-edited |
| `templates/a1_background.pdf` | The official A1 2025 background (image-backed, no AcroForm fields). The empty checkbox squares live in the image. Document ID `N8069S550/2025/DE` in the example | `generate_a1_pdf` and `render_overlay` use it as the page-1, page-2, page-3 source | Never written; treated as read-only source |
| `scripts/a1_core.py` | **Canonical core logic.** `build_form_data`, `render_overlay`, `generate_a1_pdf`, validators, generators for `issue_date` and `document_id`, Czech display casing, residence enrichment, checkbox helpers | Always; imported by `finalize_a1`, `generate_provisional_a1`, dashboard `services.py` | Never written; pure functions |
| `scripts/finalize_a1.py` | Row → form mapper (`row_to_form`, `display_row`), PDF verifier (`verify_pdf`), readiness (`readiness_report`), `load_profile` for institution profiles | CLI uses it via `generate_provisional_a1` and direct test entry points | Audit receipts in `a1/receipts/` |
| `scripts/generate_provisional_a1.py` | Atomic publisher: reads review, cohort, employees; calls `row_to_form` + `build_form_data` + `generate_a1_pdf`; writes one staged package, then publishes to `output/provisional/<UUID>/` | `provisional generation` CLI; can also be called programmatically | `output/provisional/<UUID>/` plus audit JSON |
| `scripts/a1_quality_gate.py` | Deterministic QA. `render` re-renders 300 DPI previews + contact sheets, `validate` re-checks cohort, page count, static-PDF, required text, cross-person identity leakage, hashes. `record-review` binds the human review to the manifest | After generation, before any human approval | `output/provisional-previews/`, `output/provisional-contact-sheets/`, `*-qa-manifest.json` |
| `scripts/pdf_named_fields.py` | **Preferred default framework** (fallback today). `placeholder_template` inserts `{{name}}` tokens into a vector-backed template; `replace_placeholders` swaps them. `display_value` applies personal-name title casing. | Only when the template is vector-backed | Returns bytes of the filled PDF |
| `portal/release1a/services.py:323` | Dashboard click handler. The `Generate A1` button calls `generate_a1_pdf(row_to_form(...), background, layout, output)`. | Operator dashboard only | Stores the artifact under `output/provisional/<UUID>/` |
| `tests/test_a1_core.py`, `tests/test_finalize_a1.py`, `tests/test_a1_quality_gate.py`, `tests/test_pdf_named_fields.py` | Unit + integration + QA tests | `venv/bin/python -m pytest -q` | Updated when the canonical logic changes |

## Two frameworks as fallbacks

Both frameworks share the same data source. They differ in **how** they
draw the rendered text on top of the template.

### Framework A — Coordinate overlay (`scripts/a1_core.py`)

This is the active framework today. The template
`templates/a1_background.pdf` is image-backed: every page is a single
JPEG/bitmap with the form layout baked in, including the empty checkbox
squares. There is no vector text layer to anchor `{{tokens}}` against.

**When to pick this framework:**
- The template is image-backed (current state, and the case for any PDF
  exported from a word processor as a flat scan/print).
- You need Czech diacritics rendered exactly as the canonical pipeline
  produces them.
- The QA gate (`a1_quality_gate.py`) must be able to re-render previews
  and validate text extraction.

**Mechanism:** `render_overlay` produces an overlay PDF (3 pages, same
size as the background) using reportlab. Each field from
`config/a1_layout.json` is drawn with `_draw_field` (wrapping and
auto-shrinking) and each checked checkbox is drawn with `_draw_check_x`
(blue X over the template's empty square). `generate_a1_pdf` then
merges the overlay onto the background using `pypdf.PdfWriter.merge_page`
because earlier experiments with `pymupdf.show_pdf_page` re-encoded the
overlay text into a Form XObject and re-split comma text operands
(e.g. `(DE, CZ) Tj` → `(DE) Tj`). `pypdf` keeps the overlay's text
stream verbatim, including the comma.

### Framework B — Placeholder search/replace (`scripts/pdf_named_fields.py`)

This is the **preferred default** for any vector-backed template. The
template is required to have a vector text layer with `{{name}}` tokens
that `placeholder_template` can find and `replace_placeholders` can swap.

**When to pick this framework:**
- The template is a vector PDF exported from a tool that preserves
  editable text (LibreOffice/InDesign/Figma export, or a hand-authored
  template).
- You want the rendered text to remain searchable in the output PDF.
- You want a single-pass pipeline that does not need a separate overlay
  pass.

**Mechanism:** `placeholder_template(blank_pdf, fields, font)` walks the
blank vector template and inserts each `{{name}}` token at the layout
position. `replace_placeholders(template_pdf, fields, values, font)`
redacts each token, then calls `page.insert_text` with the supplied
value. The text layer is preserved end-to-end so the output is
fully searchable.

The two helpers are kept simple on purpose:
- `display_value` title-cases personal-name fields (`person.surname`,
  `person.given_name`, `person.maiden_name`) so the OCR uppercase
  pass-through does not become a display problem.
- `_check_fields` validates every `name` token and rejects duplicates
  on the same page so the layout cannot double-bind a name.

### Why both are kept

| Concern | Coordinate overlay (today) | Placeholder search/replace (preferred) |
|---|---|---|
| Template must be | Image-backed OK | Vector-backed only |
| Output is searchable | No (overlay text is not part of the background) | Yes |
| Layout is owned by | `config/a1_layout.json` (magic numbers) | The template itself (`{{token}}` placement) |
| Czech diacritics | OK (Liberation Sans fallback to DejaVu Sans) | OK (any TTF) |
| QA previews | `a1_quality_gate.render` re-renders overlay | Template's own text layer is reused |
| Switch cost | Lower for current image template | Lower once the template is reissued vector |

The two renderers are **never invoked from the same call site**. The
dashboard `portal/release1a/services.py:323` uses `generate_a1_pdf`.
Tests for the placeholder framework live in
`tests/test_pdf_named_fields.py`; the canonical pipeline
(`scripts/finalize_a1.py`, `scripts/a1_core.py`,
`scripts/generate_provisional_a1.py`) uses the coordinate overlay.

## End-to-end generation pipeline

The pipeline is invoked by either the CLI or the dashboard. Both paths
share the same core logic.

### Step 1 — Source data lands in `a1/`

For the synthetic test fixtures, the only file the pipeline reads is
`a1/review.csv`. For real production, it also reads
`a1/cohort.json` (operator-issued `document_id` and `issue_date`) and
`a1/employees_normalized.json` (OCR identity reference).

### Step 2 — Row → Form (`scripts/finalize_a1.row_to_form`)

```python
from scripts.finalize_a1 import row_to_form
from scripts.a1_core import load_json

profile = load_json("config/institutions/plzen.json")
with open("a1/review.csv") as f:
    rows = list(csv.DictReader(f))

form = row_to_form(rows[0], profile)
```

Internally `row_to_form` does:

1. `display_row(row)` — applies `czech_display_case` to
   `surname`, `given_name`, `birth_place`, `street`, `city`,
   `district`, `employment_street`, `employment_city` when they are
   uppercase. Other fields (codes, dates) pass through unchanged.
2. Builds the nested `employee` dict (`person`, `residence`,
   `employment`, `a1`, `activity`, `certificate`, `institution`).
3. Builds the `institution_config` from the loaded `profile`
   (institution block + source_url + member_state + issue_date +
   signed_by).
4. Returns `build_form_data(employee, institution_config)`.

### Step 3 — Form → Flat dict (`scripts/a1_core.build_form_data`)

This is the **only** function that knows about the flat shape the
renderer expects. It does:

- Normalizes nationality (`Česká republika` → `CZ`).
- Defensively re-applies `czech_display_case` to all `person`,
  `residence`, `employment` text fields so any caller
  (CSV, JSON fixture, DB row, future dashboard) gets the same casing.
- Resolves the `status_profile` to checkbox booleans
  (`status_posted_employee`, `status_employee_multistate`,
  `status_posted_self_employed`, `status_osv_c_multistate`,
  `employer_type_employee`, `employer_type_self_employed`,
  `gender_male`, `gender_female`, `no_fixed_address`).
- For `self_employed_multi_state`, derives Section 4 from the
  person's own insurance number, surname, given_name, and residence
  (so the worker is their own employer, as in the original form).
- Enriches the residence against
  `config/address_enrichment.json` (adds `postal_code`,
  `administrative_district`, `ossz` if missing and the rule matches).
- Calls `validate_form_data` which fails closed on any missing field
  (insurance_number, surname, address, certificate document_id,
  employer_id, etc.).
- Returns the flat form dict.

**`validate_provisional_issue_date`** enforces the operator policy:
- Day of week must be Monday (0) or Wednesday (2).
- Days-back from the reference must be in `[61, 180]`.
- For synthetic data without operator input, use
  `generate_provisional_issue_date(reference, rng)` which randomly
  picks a Mon/Wed in that window. The reference is
  `config.a1_provisional.issue_date_reference` (currently
  `11.08.2026`).
- For real operator data, the `issue_date` in `a1/review.csv` is
  authoritative and must satisfy `validate_provisional_issue_date`.

**`generate_provisional_document_id`** produces a random
`N{office_code}S{sequence:03d}/{year}/{member_state}` (default
office `65023`, member state `DE`). The year is bound to
`issue_date`; **`document_id_for_issue_year`** enforces the year-token
match for explicit document IDs. The cohort can override with
operator-issued IDs.

### Step 4 — Render the PDF (framework A, the active one)

`scripts/a1_core.generate_a1_pdf(form, background_pdf, layout_json, output_pdf)`:

1. Validates the form one more time.
2. Loads `templates/a1_background.pdf` via pymupdf.
3. Calls `render_overlay(form, layout)` to draw the text and checkboxes:
   - For each `page_number` in 0..2:
     - For each `field` in `layout.fields` on that page: calls
       `_draw_field` with `display_value` (title-cases person names).
     - Saves the canvas state and calls `_draw_form_header` to draw the
       document ID at `(96, 67)`.
     - Restores the canvas state.
     - Calls `_draw_checkboxes_for_page(c, layout, form, page, font)`:
       for each checked checkbox on the page, calls
       `_draw_check_x(c, x, y, size)` with the dark-blue stroke.
4. Saves the merged PDF as a 3-page static document using
   `pypdf.PdfWriter.merge_page` (the merge preserves the overlay text
   layer verbatim, including comma text like `(DE, CZ) Tj`).
5. Re-opens the output with pypdf and asserts three pages and zero
   AcroForm fields (the artefact must be a flat static PDF).

The result is a 3-page static PDF that mirrors the official A1 2025
layout, with the worker data, document ID, certificate dates, and
checked checkboxes filled in.

### Step 5 — Verify (`scripts/finalize_a1.verify_pdf`)

Called by `scripts/a1_quality_gate.py` and by the test suite. Reads the
PDF back, checks:

- Three pages, no AcroForm fields.
- Every required field appears in the extracted text
  (`surname`, `given_name`, `dob`, `birth_place`, `nationality`,
  `insurance_number`, `street`, `house_number`, `city`,
  `postal_code`, `document_id`, `start_date`, `end_date`,
  `issue_date`, `signed_by`, institution `code`, employer block,
  and for self-employed: surname/given + activity name/address).
- No `{{` placeholders left in the text.
- No other cohort member's `insurance_number` is present in the
  text (cross-person identity leakage).
- The `document_id` appears on page 1 (the canonical render puts
  it in the green "A1" header band).

### Step 6 — Deterministic QA (`scripts/a1_quality_gate.py`)

Three subcommands:

- `render --pdf-dir <dir> --preview-dir <dir> --contact-dir <dir> --dpi 300`
  Re-renders every page at 300 DPI PNG previews and builds per-employee
  contact sheets. The previews are hash-bound to the manifest.
- `validate --config … --cohort … --review … --background … --layout …`
  Re-runs the cross-checks above, validates the cohort matches the
  review file, validates the same template bytes are used, and
  computes a SHA-256 manifest.
- `record-review --manifest <qa-manifest> --contact-dir <dir> --output
  <visual-review> --reviewer <OPERATOR_ID> --note …` Binds the
  human visual review to the manifest. Without this, the package
  cannot be promoted to `output/final/`.

### Step 7 — Optional human review + final promotion

`output/final/<UUID>/` is the only sanctioned final destination. It is
written by `scripts/finalize_a1.py` (CLI: `finalize_a1 generate`) and
requires:
- `validated_by_user=1` on the `a1/review.csv` row.
- The `a1_quality_gate.record-review` receipt.
- `a1/employees_normalized.json` matches the row.
- Cohort agrees exactly with the review.
- A valid `a1/receipts/<UUID>.json` audit event.

## Step-by-step example (synthetic)

```bash
cd /var/www/prace-v-nemecku.tvoje.info
export PYTHONPATH=.
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"

# 1. Render a single A1 for milan-orgonik via the canonical pipeline.
venv/bin/python -c '
import csv, json, random
from pathlib import Path
from scripts.a1_core import (
    build_form_data, generate_a1_pdf, load_json,
    generate_provisional_issue_date, generate_provisional_document_id,
)

profile = load_json("config/institutions/plzen.json")
config = load_json("config/a1_provisional.json")
rng = random.Random(42)
with open("a1/review.csv") as f:
    rows = list(csv.DictReader(f))

for row in rows:
    if row["employee_id"] != "milan-orgonik":
        continue
    issue_date = generate_provisional_issue_date("11.08.2026", rng=rng)
    doc_id = generate_provisional_document_id(issue_date, member_state="DE", rng=rng)
    row["issue_date"] = issue_date
    row["document_id"] = doc_id
    row["signed_by"] = row.get("signed_by") or "JUDr. Martina Černušáková"
    row["start_date"] = row.get("start_date") or "01.10.2026"
    row["end_date"] = row.get("end_date") or "31.12.2026"
    if row.get("status_profile") == "self_employed_multi_state":
        row["activity_name"] = ""
    row["activity_address"] = config["activity_address"]

    employee = {
        "id": row["employee_id"],
        "person": {k: row[k] for k in ("surname", "given_name", "dob", "birth_place",
                                       "nationality", "insurance_number", "sex")},
        "residence": {k: row[k] for k in ("street", "house_number", "city",
                                          "postal_code", "country_code")},
        "residence": {**_, "ossz": row.get("resolved_ossz", "")} if False else {k: row[k] for k in ("street", "house_number", "city", "postal_code", "country_code")},
        "employment": {k: row[k] for k in ("employment_id", "employment_name",
                                            "employment_street", "employment_house_number",
                                            "employment_city", "employment_postal_code",
                                            "employment_country_code")},
        "a1": {"status_profile": row["status_profile"],
               "institution_profile": row["institution_profile"]},
        "activity": {"name": row.get("activity_name", ""),
                     "address": row.get("activity_address", "DE, CZ")},
        "certificate": {"document_id": row["document_id"], "member_state": "CZ",
                        "start_date": row["start_date"], "end_date": row["end_date"]},
        "institution": {"issue_date": row["issue_date"],
                        "signed_by": row["signed_by"]},
    }
    institution_config = {"institution": profile["institution"],
                            "source_url": profile.get("source_url", ""),
                            "certificate": {"member_state": "CZ"},
                            "issue_date": row["issue_date"],
                            "signed_by": row["signed_by"]}
    form = build_form_data(employee, institution_config)
    output = "tests/fixtures/release_1a/orgonik_zivot_pdfs/A1_milan-orgonik.pdf"
    generate_a1_pdf(form, Path("templates/a1_background.pdf"),
                    Path("config/a1_layout.json"), Path(output))
    print("Generated:", output)
'

# 2. Run the canonical test suite.
venv/bin/python -m pytest tests/test_a1_core.py tests/test_finalize_a1.py \
    tests/test_a1_quality_gate.py tests/test_pdf_named_fields.py -q

# 3. Compare against the original.
ls -la "output/A1 2025.pdf"
```

The result is a 3-page static PDF in
`tests/fixtures/release_1a/orgonik_zivot_pdfs/A1_milan-orgonik.pdf`,
indistinguishable in shape from `output/A1 2025.pdf` (the original).

## Configuration of `config/a1_layout.json`

The layout is split into two blocks: `fields` (text to write) and
`checkboxes` (X marks to draw). Each entry has an `area` key that
points into `field_areas` for human-readable naming.

```jsonc
{
  "fields": {
    "person.insurance_number": {
      "section": "1.1", "page": 0, "x": 156, "y": 453.5, "size": 9
    },
    "activity.address": {
      "section": "5.2", "page": 2, "x": 84, "y": 605, "max_width": 430
    }
    // ...
  },
  "checkboxes": {
    "status_osv_c_multistate": {
      "section": "3.4", "page": 1, "x": 275, "y": 605, "size": 7.4,
      "area": "section_3_status_checkboxes.boxes.3.4_self_employed_multistate"
    }
    // ...
  },
  "field_areas": {
    "section_3_status_checkboxes": {
      "boxes": {
        "3.1_posted_employee":        { "x":  72.5, "y": 605 },
        "3.2_employee_multistate":    { "x": 275.0, "y": 605 },
        "3.3_posted_self_employed":    { "x":  72.5, "y": 584 },
        "3.4_self_employed_multistate":{ "x": 275.0, "y": 605 }
      }
    }
    // ...
  }
}
```

**Adding a new field** is a two-step process:
1. Add the field source key to `fields` with section, page, x, y, size,
   max_width, and (for multi-line) `line_height` and `max_lines`.
2. Run the test suite. `validate_form_data` will fail until the
   canonical employee schema exposes the new key.

**Adding a new checkbox** is similar:
1. Add the field to `checkboxes` with section, page, x, y, size.
2. Add the boolean derivation in `build_form_data` (e.g. from a new
   source field).
3. Add the named area to `field_areas.<section>_checkboxes.boxes`.

## Validation layers

The pipeline has **four** distinct validation layers, each fail-closed:

| Layer | Tool | What it catches |
|---|---|---|
| 1. Form shape | `a1_core.validate_form_data` | Missing insurance_number, dob, address, certificate document_id, employer_id, etc. |
| 2. Issue-date policy | `a1_core.validate_provisional_issue_date` | Wrong day-of-week, outside the 2-6 month window |
| 3. PDF content | `a1_core.reopen + finalize_a1.verify_pdf` | Wrong page count, AcroForm fields, missing text, `{{` placeholders, cross-person identity leakage, document_id absent from page 1 |
| 4. Deterministic QA | `a1_quality_gate.render` + `a1_quality_gate.validate` | Re-renders previews, hash-binds the manifest, cross-checks the cohort against the review file |

The operator visual review (`a1_quality_gate.record-review`) is the
**fifth** layer: a human confirms the rendered previews against the
source evidence. Only after that can the package be promoted to
`output/final/<UUID>/`.

## Section 5 policy

The current `config/a1_provisional.json` sets:

- `activity_name=""` — Section 5.1 is empty for self-employed
  multi-state workers. Filling it would mean "name the foreign
  employer", which is the worker themselves in section 4.
- `activity_address="DE, CZ"` — Section 5.2 lists the destination
  member state and the home member state as a comma list. The cohort
  may override for AT or other member states.

The QA gate must reject any self-employed multi-state row with a
non-empty 5.1 (this is a deliberate policy violation; the form says
"if you are the employer, leave this blank").

## Common questions

**Why is the document ID drawn both in the header and from the field?**
The `document_id_p1` field was removed in favour of the form-header
helper that paints the ID at the top of every page. Section `1.1`
header `page_header` is `page_header` for the 3-page document. The
field remains in `field_areas` for documentation but the renderer
ignores it.

**Why does the placeholder framework exist if the coordinate overlay
is the only one we use?**
The placeholder framework is the **preferred default** for any
vector-backed template. It produces a fully searchable text layer and
removes the per-field coordinate maintenance burden from
`config/a1_layout.json`. It will become the canonical path as soon
as the A1 2025 background is reissued as a vector PDF.

**Why does the merge use pypdf and not pymupdf?**
`pymupdf.show_pdf_page` re-encodes the overlay text into a Form XObject
and can split comma text operands — `(DE, CZ) Tj` becomes `(DE) Tj` in
the merged file, breaking Section 5.2. `pypdf.PdfWriter.merge_page`
keeps the overlay's text stream verbatim, including the comma. We use
pypdf for the merge step; the layout and rendering are pure reportlab.

**Why is the `generate_provisional_document_id` random?**
In the synthetic test path the cohort `a1/cohort.json` has placeholder
IDs (`PENDING-MILANORGONIK/2026/DE`). The generator produces a
random valid ID in the `N{office}S{seq}/{year}/{state}` format so
synthetic runs can verify the rest of the pipeline without operator
intervention. Real runs use the operator-issued IDs from
`a1/cohort.json`.

## How to extend the pipeline

1. **New employee field** — add the column to `a1/review.csv` header,
   update the `_DISPLAY_CASE_FIELDS` tuple and `_apply_display_casing`
   calls in `build_form_data` if the field needs casing, and add the
   field to `config/a1_layout.json`. Run
   `pytest tests/test_a1_core.py -q`.

2. **New institution profile** — add `config/institutions/<profile>.json`
   with `review_status: VERIFIED`, `source_url`, `verified_on`, and
   the institution block (name, street, house_number, city,
   postal_code, country_code, code). Reference it from
   `a1/review.csv` via `institution_profile` column.

3. **New address enrichment** — add a rule to
   `config/address_enrichment.json` with `city`, optional
   `district`/`street`/`house_number` match, and the
   `postal_code`/`administrative_district`/`ossz` to fill in.

4. **New template** — replace `templates/a1_background.pdf` with a
   vector-backed A1 2025. Switch the dashboard click to call
   `pdf_named_fields.replace_placeholders` instead of
   `a1_core.generate_a1_pdf`. Update `field_areas` to use the
   template's `{{token}}` names instead of raw x/y.

5. **New status profile** — add the profile name to the allowed set
   in `validate_form_data` and to the bool-mapping block in
   `build_form_data`. The QA gate will accept the new combination
   once it is in the cohort and review files.

## File ownership rule

- `scripts/a1_core.py` is the single source of truth for all A1
  rendering, validation, casing, and policy defaults. Do not put any
  PDF rendering code elsewhere.
- `scripts/pdf_named_fields.py` is the only place that uses
  `pymupdf.Page.insert_text` for layout-overlaid insertion. Do not
  add a third renderer.
- `config/a1_layout.json` is the only place that declares per-field
  geometry. Do not scatter magic x/y numbers into scripts.
- `templates/a1_background.pdf` is read-only source data. Do not edit
  it; treat it as the canonical A1 2025 image.
