# A1 Generation Frameworks

## Two frameworks, one canonical path

This repository holds two PDF generation frameworks for the Czech A1 form.
Both are **fallbacks** for each other; one is preferred. Pick the right one
based on the template you are rendering against.

| Framework | Module | Preferred for | Status |
|---|---|---|---|
| **Placeholder search/replace** | `scripts/pdf_named_fields.py` `placeholder_template()` + `replace_placeholders()` | Vector-backed templates with `{{variable}}` tokens. Cleaner code; the value flows through a single substitution step. | **Preferred default** (when template is vector-backed) |
| **Coordinate overlay** | `scripts/a1_core.py` `generate_a1_pdf()` | Image-backed templates (the current A1 2025 background has no vector text layer). Required when the template cannot accept text-insertion without an opaque redraw. | **Fallback** (forced by image-backed A1 2025 template) |

## Why coordinate overlay is currently canonical

`templates/a1_background.pdf` is the official A1 2025 form. It is delivered
as a single image per page with no vector text layer. The placeholder
framework requires a vector text layer to anchor `{{tokens}}` for
search-and-replace. Until the A1 background template is replaced with a
vector-backed one, the coordinate overlay (`a1_core.generate_a1_pdf()`)
is the only framework that produces a release artifact.

When the A1 2025 template is reissued as vector-backed text, the placeholder
framework becomes the preferred default. The coordinate overlay stays as the
fallback for any image-backed template the operator may need to render
against.

## Canonical framework today: coordinate overlay

Files involved:

- `scripts/a1_core.py` — static overlay renderer + form validation. **All
  core logic lives here** (validators, builders, generators).
- `scripts/generate_provisional_a1.py` — atomic publisher; wraps
  `a1_core.generate_a1_pdf()` with audit, staging, output validation.
- `scripts/finalize_a1.py` — readiness checks, `row_to_form()` mapper.
- `scripts/a1_quality_gate.py` — fail-closed QA gate that re-renders and
  validates the published PDFs.
- `portal/release1a/services.py:323` — dashboard click → calls
  `a1_core.generate_a1_pdf()` after readiness and approval gates pass.

Entry points (CLI):

```bash
# 1. Atomic provisional publication
venv/bin/python scripts/generate_provisional_a1.py \
  --review $A1_PRIVATE_DIR/a1/review.csv \
  --cohort  $A1_PRIVATE_DIR/a1/cohort.json \
  --profiles config/institutions \
  --config  config/a1_provisional.json \
  --output  $A1_PACKAGE

# 2. Deterministic QA gate
venv/bin/python scripts/a1_quality_gate.py render \
  --pdf-dir "$A1_PACKAGE" --preview-dir ... --contact-dir ... --dpi 300
venv/bin/python scripts/a1_quality_gate.py validate ...
```

Entry point (dashboard):

```python
# portal/release1a/services.py:323
generate_a1_pdf(row_to_form(row, profile), background, layout, output)
```

## Preferred default: placeholder search/replace

Files involved:

- `scripts/pdf_named_fields.py` — placeholder insertion + redaction/replace.
- `tests/test_pdf_named_fields.py` — sole consumer today. Synthetic PDF only.

The placeholder framework is the **preferred default** because:

1. The data flow is simpler: `{{name}}` tokens in the template, search-and-
   replace with a flat `dict[str, str]`.
2. It does not need the coordinate layout JSON — the template itself is the
   layout contract.
3. It produces searchable text in the rendered PDF (useful for visual review).

It is **not yet** the canonical release path because the current A1 2025
background is image-backed. When the template becomes vector-backed, swap
the call site in `portal/release1a/services.py:323` to:

```python
from scripts.pdf_named_fields import placeholder_template, replace_placeholders
template = placeholder_template(blank_background, fields, font)
filled = replace_placeholders(template, fields, values, font)
```

## Core logic — single source of truth

All shared logic lives in `scripts/a1_core.py`. If you find yourself writing
the same helper in another script, **stop and add it to `a1_core.py`**.

| Concern | Where |
|---|---|
| Date parsing / normalization | `a1_core.normalize_date()` |
| Provisional issue-date policy (Mon/Wed, 61–180 days) | `a1_core.validate_provisional_issue_date()`, `a1_core.generate_provisional_issue_date()`, constants `ISSUE_DATE_WEEKDAYS`, `ISSUE_DATE_MIN_AGE_DAYS`, `ISSUE_DATE_MAX_AGE_DAYS` |
| Certificate number binding to issue year | `a1_core.document_id_for_issue_year()` |
| Random certificate number generation | `a1_core.generate_provisional_document_id()` |
| One-year provisional period | `a1_core.provisional_one_year_period()` |
| Czech display casing | `a1_core.czech_display_case()` and `pdf_named_fields.display_value()` (same logic; display_value is the test seam) |
| Address enrichment | `a1_core.enrich_residence()` |
| Form validation | `a1_core.validate_form_data()` |
| Form data flattening (with defensive casing) | `a1_core.build_form_data()` |
| PDF rendering (coordinate overlay, fallback) | `a1_core.generate_a1_pdf()` and `a1_core.render_overlay()` |
| PDF rendering (placeholder search/replace, preferred) | `pdf_named_fields.placeholder_template()` and `pdf_named_fields.replace_placeholders()` |

## Section 5 policy (current)

The original A1 2025 form has two sections for the activity details:

- **Section 5.1** — "Jméno (jména) nebo obchodní název (názvy) … kde budete
  zaměstnán / zaměstnána". For a self-employed worker this is empty (the
  worker is the employer declared in section 4). The provisional
  configuration must therefore leave `activity_name` empty:
  `config/a1_provisional.json::activity_name = ""`.
- **Section 5.2** — "Adresa (adresy) … kde budete zaměstnán / zaměstnána".
  The default is the destination country and home country as a comma list:
  `config/a1_provisional.json::activity_address = "DE, CZ"`. The cohort may
  override for AT or other member states.

If section 5.1 is filled for a self-employed multi-state profile, that is a
**policy violation**; the QA gate must reject it.

## Naming conventions

Scripts use a **domain-prefixed** style. New scripts should follow the same
pattern so the catalog stays predictable:

| Prefix | Purpose |
|---|---|
| `a1_*` | A1 form generation, validation, quality gate, audit |
| `portal/release1a/*` | Django app for the A1 release 1A dashboard |
| `document_core` | Cross-document OCR + extraction library (`src/document_core/`) |
| `research_*` | Market research and benchmark tooling |
| `validate_*` | Validation harnesses for plans, approvals, schemas |
| `run_*` | Executable benchmarks / proofs of concept |
| `seed_*` | Local DB seeding and dev fixtures |
| `release_verifier.py` | End-to-end release smoke checks |
| `release1a_*` | (legacy) early release1a scripts; superseded by the `portal/release1a/` Django app |
| `migrate_*` | One-time data migration commands (see PLAN-WORKERS-MIGRATE-TO-DB) |

If a new script does not match a known prefix, prefer the **most specific**
prefix and add a short docstring at the top declaring its scope.

## File-system conventions

A1 artifacts should follow a stable, predictable layout. The repo accumulates
many "backup" and "preview" trees if generated carelessly.

### Output package layout (canonical)

```
output/provisional/<UUID>/                # atomic publisher destination
├── A1_<employee_id>.pdf                   # one per accepted row
├── verification_table.csv                 # per-row gate status
├── CLIENT_CONFIRMATION_CHECKLIST.md       # manual review reminder
└── generation_manifest.json               # inputs/snapshot/receipt hashes
```

No timestamped backups, no per-page preview copies, no contact-sheets baked
into the same directory. Previews and contact sheets go into adjacent
`-previews/` and `-contact-sheets/` directories produced by the QA gate, not
into the provisional package.

### Test fixture layout

`tests/fixtures/release_1a/orgonik_zivot_pdfs/`:

```
A1_<cohort_employee_id>.pdf       # canonical name; one per worker
MANIFEST.json                     # synthetic notice + provenance
templates/a1_template_marked.pdf  # red {{placeholder}} overlay for review
```

Naming must match the cohort employee IDs (`a1/cohort.json`). One naming
convention per artifact — no `-contact.pdf` / `-preview.pdf` duplicates in
the same directory.

## What the dashboard calls

The dashboard (Django `portal/release1a`) does **not** call any A1 helper
directly. The path is:

1. Operator uploads scans via the intake view.
2. OCR pipeline extracts fields; review UI presents them.
3. Operator finalizes the review → `portal.Worker` row (today: `a1/review.csv`,
   after PLAN-WORKERS-MIGRATE-TO-DB: direct DB write).
4. Click **Generate A1** → `portal/release1a/services.py:323`
   `generate_a1_pdf(row_to_form(row, profile), background, layout, output)`
5. Deterministic QA gate (`a1_quality_gate.py`) validates the artifact.
6. Visual review + explicit human approval → `output/final/<UUID>/`.

If you are tempted to add a "Generate A1" button that skips readiness or QA,
**do not**. The gate is fail-closed for a reason.

## Why both frameworks stay

The coordinate overlay is required for the current image-backed A1 2025
template; the placeholder search/replace is the preferred default for any
vector-backed template. They are not duplicated logic — they share
`display_value`, `czech_display_case`, and the data flow from `build_form_data`.
They are two renderers consuming the same canonical form data.
