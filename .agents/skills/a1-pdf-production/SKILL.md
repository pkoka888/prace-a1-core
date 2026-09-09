---
name: a1-pdf-production
description: Generate, recover, inspect, and visually validate Czech A1 provisional PDF packages in this repository. Use for A1 template cleaning, field or checkbox placement, employee cohort generation, PDF regression analysis, preview rendering, manifests, client-confirmation packages, or diagnosing damaged rules, clipping, stale data, and mismatched outputs.
---

# A1 PDF production

## Ground the run

1. Read the repository `AGENTS.md` and [field-policy.md](references/field-policy.md).
2. Inspect `git status`; preserve unrelated and historical work.
3. Resolve the current provisional cohort only from `$A1_PRIVATE_DIR/a1/review.csv` plus `$A1_PRIVATE_DIR/a1/cohort.json`. Require exact unique cohort agreement between the reviewed CSV, normalized identity source, and cohort maps. The former 11-person count is historical; observed directory counts never authorize cohort additions. `config/a1_provisional.json` contains non-personal provisional policy/placeholders only and is never an identity source. Operational inputs resolve only through `A1_PRIVATE_DIR`; set it to the repository root so the in-repo gitignored `a1/`, `scans/`, `evidence/`, and `ocr/` directories serve as inputs (see `AGENTS.md`). There is no tracked fallback, and canonical commands fail closed when `A1_PRIVATE_DIR` is unset.
4. Use `config/institutions/` for office profiles. Never derive issuance fields by copying another person's completed form.
5. Treat scans, CSV rows, PDFs, previews, and extracted text as PII. Keep them local unless the repository policy explicitly permits a minimal redacted external-model crop.

## Generate safely

1. Validate inputs and cohort uniqueness before rendering.
2. Use `scripts/generate_provisional_a1.py`; it composes review data through `scripts/finalize_a1.py` and renders with `scripts/a1_core.py`.
3. Use `templates/a1_background.pdf` and `config/a1_layout.json` unless a tested migration changes both canonical references.
4. Place text with per-field coordinates and measured font metrics. Do not apply a global baseline correction or opaque background rectangle.
5. Draw checkbox state from form data on the declared page. Never reconstruct template line art during employee generation.
6. Generate into staging and publish atomically only after all gates pass. Keep provisional output in `output/provisional/`; generation cannot enter reserved `output/final/` or `output/pdf/`; a separately implemented receipt-bound promotion must enforce QA and explicit artifact approval.

## Validate every package

1. Run the repository unit and integration tests relevant to A1 generation.
2. Require one three-page PDF and three previews per member of the authorized input cohort; do not use a historical fixed count.
3. Verify PDF readability, page count, expected per-person values, unique certificate IDs, absence of legacy/cross-person values, and hashes tying inputs, template, layout, PDFs, and previews together.
4. Render fresh fixed-DPI previews from the just-generated PDFs. Never approve old previews by filename alone.
5. Apply [visual-qa.schema.json](references/visual-qa.schema.json) to every page and field. Fail closed on clipping, overlap, hidden colored rules, incorrect checkboxes, unknown hashes, or pending review.
6. Use deterministic geometry and pixel checks first. Use local visual inspection for the whole package. External free vision models are advisory only and may receive only minimal redacted crops under `AGENTS.md`.
7. Use the repository CLI directly. Do not add a PDF MCP until the stability conditions in [mcp-contract.md](references/mcp-contract.md) are met.

## Recover regressions

1. Quarantine broken outputs with hashes; do not delete evidence.
2. Compare the damaged PDF, canonical background, layout, manifest, and a known-good archived source.
3. Determine whether the defect belongs to source data, background, field coordinates, font metrics, checkbox state, or stale packaging before editing.
4. Correct the smallest responsible layer. Regenerate every affected PDF and its previews; then rerun all gates.
5. Do not accept text-presence validation as proof of visual correctness.

## Hand off

Report the exact cohort size, tests run, PDF/preview counts, manifest location, remaining provisional fields, and whether operator approval is still required. Never call a client-confirmation copy an issued A1 certificate.
