# A1 PDF tool comparison — 2026-09-07

Parent: PLAN-A1. Local research and synthetic geometry tests only. No worker records
were read, no generated employee PDF was patched, and no production dependency or
template was changed. Existing test-plan work remains separate.

## Decision

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
separately named employee/reference “A1 2025.pdf” was not supplied as an identified
input and was not inspected. Its coordinates cannot be assumed to fit this template.

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
