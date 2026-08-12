# Deferred read-only PDF MCP contract

Do not deploy an MCP server while the A1 CLI and schemas are still changing. Reconsider only after at least three successful production batches use the same command and manifest contracts.

The future server must be local-only, read-only, network-disabled, restricted to workspace paths, and must not log extracted employee text. It may expose only:

- `inspect_pdf(path)`: structure, page boxes, fonts, images, drawings, widgets, hashes;
- `render_page(path, page, dpi)`: a local image resource;
- `render_section(path, page, rect, dpi)`: a minimal crop;
- `compare_template(pdf, template, allowed_regions)`: deterministic pixel differences;
- `validate_overlay(pdf, layout)`: field containment and checkbox results;
- `create_review_sheet(paths, dpi)`: a local contact sheet.

Reuse the canonical functions in `scripts/a1_quality_gate.py`; never fork validation logic into the MCP layer. Require explicit user authorization before returning a PII-bearing image or extracted text.
