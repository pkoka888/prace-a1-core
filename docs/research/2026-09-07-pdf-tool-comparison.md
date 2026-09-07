# A1 PDF tool comparison — 2026-09-07

Parent: PLAN-A1. Local template investigation and synthetic comparison. The initial
experiment below concerned the canonical raster background. The subsequent
user-authorized reference inspection and named-field experiment are recorded first.
No employee artifact was regenerated or promoted; canonical template migration is pending.

## Named-field comparison after identifying the supplied original

The identified reference PDF has text, vector checkbox borders/marks and image
artwork on all three pages; it has no AcroForm widgets. PyMuPDF, pypdf,
pdfplumber/pdfminer and PDFium independently confirmed the mixed structure.
The earlier image-only finding applies to the canonical raster background only.

A protected experiment prepared a blank vector reference and a searchable template
with **34 named variables in 36 occurrences**. Examples are `{{surname}}`,
`{{given_name}}`, `{{birth_surname}}` and `{{certificate_id}}`; the certificate ID
occurs on every page. The field map records each semantic source, page, baseline,
font size and maximum width. Personal values, institution details and eight existing
cross strokes were removed; checkbox borders and page artwork were preserved.
The original reference was unchanged. No reference content is added to Git.

Both approaches were executed with the same synthetic values and reference geometry:

| Approach | Result | Single-run fill time |
|---|---|---:|
| Located token replacement using PyMuPDF | Complete three-page synthetic PDF, no remaining tokens | 495 ms |
| Existing ReportLab/pypdf overlay on the cleaned reference | Complete three-page synthetic PDF | 89 ms |

These timings exclude template preparation and QA and are not a performance benchmark.
Use named variables as the field contract for either backend. Token replacement is
useful for inspecting and editing a template; the current overlay remains faster in
this trial. Neither requires selecting an OCR engine per worker.

Personal names now share display formatting at the last rendering step:
`NOVÁKOVÁ` becomes `Nováková`, and `ALENA` becomes `Alena`. Diacritics are preserved;
OCR/source values are unchanged. Codes and certificate identifiers are not title-cased.
This corrects the direct-overlay path that could bypass earlier row formatting.

Evidence: all three cleaned pages have zero changed pixels outside allowed field
and mark bounds at 144 DPI. All pages of both filled examples and the token template
were locally inspected. Ghostscript independently rendered all nine pages. Exact
name extraction, repeated IDs, source-value exclusion and absence of leftover tokens
passed. The examples are prominently marked synthetic and remain in protected runtime
storage with hashes, field maps and receipts. This is technical template evidence,
not canonical production QA or confirmation of a worker's facts.

The separately supplied fixed-output claim was checked read-only: its marks use
0.8-point strokes, whereas the reference uses 0.48-point strokes; colors also differ.
Consequently the claim of exactly matching drawing style is false. The experimental
replacement example uses measured reference style; the overlay comparison deliberately
shows the inherited renderer's current border redraw/color behavior.

Acceptance commands:

- `venv/bin/python -m pytest tests/test_pdf_named_fields.py tests/test_a1_core.py -q`:
  28 passed, 3 subtests in the working tree.
- The expanded A1 regression run: 62 passed, 14 subtests, one failure in
  `test_complete_review_publishes_verified_set`. Its expected employment name is
  overwritten by inherited self-employment derivation. This is separate from name
  display formatting: the same test fails with the new formatter disabled in memory.
  Do not describe the complete A1 pipeline as passing.

Next: integrate a hash-bound reference template and matching layout through canonical
validation, resolve source-backed employment mapping, and retain review requirements.
Missing certificate evidence must remain missing. A common template never selects a
worker's legal/employment status merely by copying the reference's selected boxes.

## Initial canonical-background experiment: decision

Keep ReportLab + pypdf for canonical generation, PyMuPDF for geometry inspection,
crops and primary QA rendering, and Ghostscript as the existing independent check.
Use PDFium as an optional second renderer for disputed output. pdfplumber/pdfminer
is useful for future text/vector originals, but adds no checkbox precision to this
image-only template. This experiment does not establish a universal accuracy winner.

## Inputs and installations

The current canonical template is 2,800,789 bytes, SHA256
`0f7d602ecb0f77002feebbb72fb9f716c2f568b72d12587021eb3b5d5fed130a`.
The committed baseline is 1,865,448 bytes. Both have three unrotated pages measuring
595.2 × 841.92 points, one embedded image per page, no text layer and no form widgets.
The current template has three repair drawing paths total; the baseline has none.
These are not separately extractable printed checkbox borders. Each embedded image
is 1985×2807 pixels, approximately 240 DPI: about 0.30 point per source pixel.
Higher rendering DPI does not restore the original vector geometry.

This evaluated the actual canonical background and its committed baseline. The
separately named reference had not yet been inspected during this initial run; the
subsequent reference experiment above supersedes that limitation. Its coordinates
cannot be assumed to fit the canonical raster background.

Existing: PyMuPDF 1.28.2, pypdf 6.15.0, ReportLab 5.0.0 and Ghostscript.
Installed locally: pdfplumber 0.11.10, pdfminer.six 20260107 and pypdfium2 5.13.0,
with dependencies under `runtime/portal/pdf-tool-evaluation/packages`.
No host packages or production requirements were changed. Poppler/qpdf were not
installed: host package changes require separate scope, and existing renderers
already cover this comparison. These tools provide different functions, not
interchangeable precision settings.

## Measured results

All three renderers successfully rendered every canonical page at 144 and 300 DPI.
Times include PNG serialization and are single-run observations, not benchmarks.

| Renderer | Three pages at 144 DPI | Three pages at 300 DPI |
|---|---:|---:|
| PyMuPDF | 0.72 s | 2.05 s |
| PDFium | 1.68 s | 3.07 s |
| Ghostscript | 0.97 s | 2.53 s |

At 144 DPI, MuPDF/PDFium produced 1191×1684 pixels and Ghostscript 1190×1684.
At 300 DPI, MuPDF/Ghostscript produced 2480×3508 and PDFium 2481×3508.
Different page-edge rounding and antialiasing mean cross-engine hashes are not
valid equality gates. Same-canvas mean RGB differences were about 0.26–0.37/255
for PDFium versus MuPDF at 144 DPI, and 0.84–1.49/255 for Ghostscript versus MuPDF
at 300 DPI. No resize/crop was silently applied to unequal canvases.

pypdf, PyMuPDF and pdfplumber extracted no text from either template. pdfplumber
found no printed rectangles/lines. On an independent synthetic vector page,
PyMuPDF and pdfplumber recovered the known 10×10 point rectangle with coordinate
conversion error below 0.001 point. That vector precision does not recover
information lost when the real form was rasterized.

## Coordinate and workflow corrections

For an unrotated page of height H, a top-left rectangle (x, y, width, height) becomes
ReportLab bottom-left (x, H-y-height, width, height). Points use H-y instead.
Normalize page numbering as well. For example H=841.92, y=236.42, height=7.44 gives
bottom-left y=598.06. Do not mix these with unconverted PyMuPDF coordinates.

The supplied option comparison conflates checkbox meaning, geometry and evidence.
Section 3.1 is for posted employees; 3.2 for employment in multiple states; 3.4 for
self-employment in multiple states. A sample's selections do not establish another
worker's status. The proposed counts also conflict: 21+4=25, not 27. No live cohort
or readiness count was established by this experiment.

Choose canonical data-first regeneration after source/readiness validation.
Patching blocked workers' PDFs is not a compliant hybrid: it neither supplies
missing evidence nor satisfies the generation/approval contract. A partial cohort
requires an explicit supported subset contract; ad-hoc CSV filtering breaks exact
cohort matching. Existing output packages must not be overwritten.

## Next automation/test-plan increment

1. Bind a reviewed checkbox map to the exact template SHA, page boxes, rotation,
   coordinate convention and measured border rectangles. Raster detection proposes
   candidates; labels and geometry tests verify the map once per template version.
2. Test every supported profile using synthetic data: correct selected boxes,
   unselected boxes unchanged, and strokes contained inside the existing borders.
3. Render all pages at the recorded DPI and compare original/template pixels outside
   allowed field regions. Use independent rendering for anomalies, with explicit
   canvas normalization and tolerances rather than hash equality across engines.
4. Preserve the original, publish only complete canonical packages, and bind QA and
   visual-review receipts to the actual bytes and dependencies. No gate weakening.

## Reproduction and evidence

Run `venv/bin/python scripts/evaluate_a1_pdf_tools.py` after installing the pinned
optional tools with the venv pip `--target runtime/portal/pdf-tool-evaluation/packages`.
The harness writes results.json, synthetic.pdf and all-page renderer PNGs in that
protected evaluation directory. It asserts synthetic coordinate recovery and that
the canonical template hash remains unchanged. It makes no external model calls.
A known limitation is that the baseline is taken from HEAD at execution time;
results record its byte hash so later runs must compare input hashes first.

Sources: [PyMuPDF coordinate conventions](https://pymupdf.readthedocs.io/en/latest/app3.html),
[pypdf image/text limitations](https://github.com/py-pdf/pypdf/blob/main/docs/user/extract-text.md),
[pdfplumber scope](https://github.com/jsvine/pdfplumber),
[PDFium renderer](https://pypdfium2-team.github.io/pypdfium2/),
[European Labour Authority A1 field descriptions](https://www.ela.europa.eu/sites/default/files/2021-02/SSC-and-Highly-mobile-workers.pdf).

Implementation commit: `094f956`. Its exported Git snapshot passes 44 focused
PDF/core/Git-scope tests (3 subtests); three pre-existing pypdf warnings concern the
committed baseline merge implementation. Git publication is checked separately.
