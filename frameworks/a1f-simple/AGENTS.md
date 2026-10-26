# AGENTS.md — A1F-SIMPLE (a1f-simple)

**This is a standalone framework. Do NOT depend on parent repository AGENTS.md. Treat this directory as its own workspace.**

## Mission (Single Goal)
Create A1 provisional forms by copying `templates/a1_template_v1.pdf` and replacing placeholders with worker values ONLY. Nothing more. Get straight to producing correct A1 forms for Jan with minimal complexity.

## Non-negotiable rules
1. **Single template only**: Use ONLY `templates/a1_template_v1.pdf`. No other templates/backgrounds. Copy as-is, use as-is.
2. **Placeholder replacement only**: Replace placeholders with worker values ONLY. No styling, repositioning, font changes, text insertion beyond placeholder replacement, layout modifications, or drawing of non-worker content.
3. **Checkboxes only exception**: The ONLY deviation is toggling checkbox checked/unchecked state as they exist in the PDF based on worker data. Do NOT reposition, resize, or redraw checkboxes. Do NOT change template structure.
4. **No scope creep**: No notices, watermarks, "improvements", refactoring for aesthetics, or additions beyond placeholder replacement.
5. **Self-contained**: All paths relative to framework dir. No imports from parent `scripts/`, no reliance on parent config except what is copied here. Framework must run standalone.
6. **Own governance**: This framework has its own AGENTS.md. Agents working here MUST follow ONLY these rules. Parent rules do not apply.

## Architecture (Keep it simple)
- **Input**: Worker data (JSON) with values for placeholders
- **Template**: `templates/a1_template_v1.pdf` (single source of truth)
- **Engine**: `core/a1_core.py` + `core/pdf_named_fields.py` (placeholder replacement). `core/generate.py` provides clean API.
- **Output**: New PDF with placeholders replaced by worker values
- **Checkbox handling**: Only if present in worker data - toggle existing checkbox states via layout/structure inspection, no coordinate-based repositioning

## Dependencies
- Keep minimal: `pymupdf` (fitz), `pypdf`, `reportlab` only if absolutely necessary for the minimal case. Prefer what's already working.
- All deps must be importable in isolated environment or documented. No hidden parent deps.

## Input/Output Contract
- Input JSON structure must map to placeholder names used in template (see `templates/a1_placeholders.json` if present, or inspect template)
- Output is a new file copied-from-template with placeholders replaced
- No modifications to template file

## Development Standards
- **Simplicity first**: If it adds complexity not needed for placeholder replacement, don't do it.
- **No mocks/workarounds**: Fix issues directly; don't create mock data or workarounds that hide problems.
- **Explicit over implicit**: Hardcode the single template path. No configuration that allows switching templates.
- **Test what matters**: Tests must verify placeholders replaced correctly, no extra text/stamps added, checkboxes toggled only if specified.
- **No dead code**: Remove unused imports/functions.

## Commands
```bash
# Generate from form JSON
python scripts/generate_simple.py --form form.json --output out.pdf
```

## Testing & Validation
- Verify: placeholders replaced with correct values
- Verify: no notices/watermarks/stamps added
- Verify: only checkboxes changed if requested (no repositioning)
- Verify: template structure unchanged except placeholder text replacement and checkbox states

## Git Workflow (framework-specific)
- Work in this directory only when operating on framework
- Commit with clear messages focused on framework goal
- Keep commits small and focused
- No force-push
- Follow parent's git delivery rules only if they don't conflict with these standalone rules (they must not conflict)

## .agents/ & Skills
- Consider adding `.agents/` if needed for framework-specific skills/workflows
- Skills should be minimal and support only placeholder replacement + checkbox toggling
- Don't pull parent skills unless necessary and compatible with standalone nature

## Gap Analysis & Continuous Improvement
- Review `docs/GAP_ANALYSIS.md` regularly
- Update `docs/RESEARCH_SOLUTIONS.md` with findings
- Document any issues found and solutions without adding scope creep

## Anti-patterns (FORBIDDEN)
- Adding notices/provisional stamps
- Using layout coordinates to reposition elements
- Template switching logic
- Style/formatting changes
- Background/template overlay
- Font changes outside minimal necessity
- "Improvements" not requested
