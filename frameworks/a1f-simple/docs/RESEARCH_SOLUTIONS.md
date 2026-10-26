# Research: Alternatives & Prevention

## Common pitfalls
- **Over-engineering**: Adding notices, styling "improvements" when only replacement requested
- **Template drift**: Using different templates/backgrounds causing confusion
- **Scope creep**: Agents adding features not requested
- **Coordinate dependency**: Relying on layout files makes things fragile

## Prevention strategies
1. **Hard constraints in AGENTS.md** - Make rules non-negotiable and explicit
2. **Single source of truth** - Only one template file, hardcoded
3. **Minimal API** - Function should take (worker_data, template_path) and only do replacement
4. **Code review checklist** - Reject any changes that add drawing/styling/positioning
5. **Tests** - Verify no extra objects drawn, only placeholders replaced

## External patterns to consider
- Simple PDF form filling: use PyPDF (form fields) vs direct text replacement
- For AcroForm fields: fill fields; for placeholder text: replace text spans
- The template `a1_template_v1.pdf` uses placeholder text tokens like `{{person.surname}}` - text replacement is appropriate
- Checkboxes: may be form fields or drawn objects - need to inspect and toggle state only

## Governance recommendations
- Keep framework self-contained with its own AGENTS.md
- No imports from parent - copy minimal needed code
- CI/checks specific to this framework enforce the rules
- Documentation must be explicit about what NOT to do
