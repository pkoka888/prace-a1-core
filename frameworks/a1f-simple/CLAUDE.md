# A1F-SIMPLE Framework - CLAUDE.md

## RULES (FOLLOW THESE OR STOP WORK)

⚠️ **CRITICAL**: This is an ISOLATED FRAMEWORK
- Use ONLY templates/a1_template_v1.pdf
- Replace placeholders ONLY with worker values
- NO styling, NO watermarks, NO notices, NO "improvements"
- NEVER import from parent repository
- NEVER use template switching or background overlays

## STOP IF ASKED TO DO:
1. Add watermarks or notices
2. Use other templates or backgrounds  
3. Change element positions or styling
4. Import from ../scripts/ or ../portal/
5. Refactor for "cleanliness" without request
6. Add mock data or workarounds

## HOW TO WORK
1. Read AGENTS.md first (this file contains same content for Claude Code compatibility)
2. Use scripts/generate_simple.py for generation
3. Test with example data
4. Document decisions in AGENTS.md

## Missions
- Replace placeholders in A1 template ONLY
- Toggle checkboxes ONLY if specified in worker data
- Produce valid A1 provisional forms for Jan

## File Structure
```
frameworks/a1f-simple/
├── AGENTS.md / CLAUDE.md    # Rules (same content)
├── README.md                  # Entry point
├── scripts/                   # CLI: generate_simple.py
├── core/                      # Engine: a1_core.py, pdf_named_fields.py
├── templates/                 # SINGLE template: a1_template_v1.pdf
├── config/                    # Layout (checkbox only)
├── tests/                     # Framework tests
└── docs/                      # Documentation
```

## Commands
```bash
# Generate from worker JSON
python scripts/generate_simple.py --form worker.json --output out.pdf

# With error placeholder erase
python scripts/generate_simple.py --form worker.json --output out.pdf --erase-empty
```

## Success Criteria
- Placeholders replaced with correct worker values
- No extra text/watermarks/stamps added
- Template structure unchanged except replacements
- Checkboxes toggled only if specified (no repositioning)
