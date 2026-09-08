# A1 generation frameworks

## One policy core, two rendering frameworks

| Framework | Owner | Current use |
|---|---|---|
| Coordinate overlay | `scripts/a1_core.py::generate_a1_pdf` | Canonical path for the current image-backed template |
| Placeholder search/replace | `scripts/pdf_named_fields.py` | Synthetic-tested alternative for a suitable vector/token template |

Keep both frameworks. A vector-backed template makes placeholder rendering the
preferred candidate, not an automatic production switch. Integrate it through the
shared policy and validate equivalent output before changing the canonical path.
Do not swap only the dashboard call site and leave CLI/QA using another contract.

All shared date, provisional-number, Czech display casing, flattening and validation
policy belongs in [a1_core.py](../../scripts/a1_core.py). Renderer-specific helpers
must delegate shared policy there; duplication is a refactoring defect, not another
source of authority. Integration must make both engines consume the same normalized form values.
The experimental named-field helper still has its own display seam; reconcile it
with the core before promoting that engine.

## Current canonical path

- [generate_provisional_a1.py](../../scripts/generate_provisional_a1.py) composes
  reviewed inputs, stages output and publishes a protected provisional package.
- [finalize_a1.py](../../scripts/finalize_a1.py) owns CSV/readiness and `row_to_form()`.
- [a1_core.py](../../scripts/a1_core.py) owns `build_form_data()`, `render_overlay()`
  and `generate_a1_pdf()` using `templates/a1_background.pdf` and `config/a1_layout.json`.
- [a1_quality_gate.py](../../scripts/a1_quality_gate.py) owns package validation,
  rendered previews and hash-bound visual review.
- [portal services](../../portal/release1a/services.py) prepare versioned case inputs
  and call the same renderer; [j4_artifacts.py](../../portal/release1a/j4_artifacts.py)
  publishes actual PDF bytes, snapshots, page previews and receipts.

As of 2026-09-08, the core reads the background with `PdfReader`, creates a fresh
`PdfWriter`, adds each background page, then calls `page.merge_page()` with the
ReportLab overlay. Image streams receive lossless ASCII85 transport encoding.
The output is reopened to check three pages and no interactive form fields.
This describes current source, not a general claim about another library's behavior.
A PDF text dump in an editor is not a rendered-page inspection.

Operational entry points (inspect `--help` and use authorized protected inputs):

```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
venv/bin/python scripts/generate_provisional_a1.py --help
venv/bin/python scripts/finalize_a1.py --help
venv/bin/python scripts/a1_quality_gate.py --help
```

Use the [pipeline guide](readme-a1-forms.md) and
[A1 skill](../../.agents/skills/a1-pdf-production/SKILL.md) for procedures.
Never copy another person's generated values or substitute a legacy template.

## Section 5 policy

For the current self-employed multi-state provisional presentation,
`config/a1_provisional.json` defaults `activity_name` (5.1) to blank and
`activity_address` (5.2) to `DE, CZ`. Preserve explicitly reviewed row-specific
territory overrides and distinguish employee from self-employed profiles.
Provisional validation and QA support blank 5.1; the generic readiness report
still lists activity_name as required. Record that discrepancy as a focused
follow-up, not proof that provisional generation is universally blocked. Do not
introduce an additional documentation-only rejection rule or interpret this display default
as a legal determination. Explicit values must follow the implemented field policy.

## Data and storage ownership

The [field mapping](release-1a-field-mapping.md) defines the proposed database
transition. Until accepted cutover, reconcile the baseline review/cohort files
with explicitly selected scoped snapshots; neither newest mtime nor an existing
PDF supplies authoritative input. After cutover the database owns facts and
CSV/JSON are revision-bound compatibility exports.

The CLI and portal intentionally have different protected package contracts:

| Owner | Storage contract |
|---|---|
| Canonical CLI publisher | `output/provisional/<run_uuid>/A1_<opaque_worker_id>.pdf` plus publisher manifests/checklists; QA previews/contact sheets use protected companion directories |
| `ProtectedDocumentStorage` | Relative keys matched by `(?:documents\|generated)/[a-f0-9]{32}(?:/[a-f0-9]{64})?\.(?:source\|json\|png)` beneath `DOCUMENT_STORAGE_ROOT`; no public URL |
| J4 artifact publisher | `<configured-artifact-root>/<artifact_uuid_hex>/artifact.pdf`, `snapshot.json`, `page-1.png` etc. and `receipt.json`; staged, hashed and atomically published |

The regex is enforced by
[document_storage.py](../../portal/release1a/document_storage.py), not a suggestion
for naming PDF packages. J4 has its own publisher and receipt validation.
Private directories/files default to `0700`/`0600` (documented dedicated-group
exception only). Keep original display filenames in protected metadata when needed.

Fixtures must be wholly synthetic and independent of operational cohorts. Never
name a fixture directory after actual employees or populate it from their PDFs.
Generation/visual review does not mean external submission, official issuance or
final promotion. Reserved final destinations still need the separately implemented
receipt-bound promotion contract and authoritative evidence.

## Directory and release consolidation

Follow the [local automation plan](../../plans/2026-09-08-local-a1-automation.md):
one editable source tree; immutable exports at `runtime/s-<full-commit-sha>/`;
a fresh `runtime/portal/supervised-development/` environment; historical packages
preserved until individually classified. No parallel editable production code tree.
Shared OCR stays in `src/document_core/`; thin Django adapters stay in
`portal/release1a/`. Match existing domain prefixes for new scripts.
