# OPencode Rules: a1f-simple Framework

**Source URL**: https://opencode.com/docs

## Framework Rules

These rules are loaded automatically when working in this directory.

### Core Mission
Create A1 provisional forms by replacing placeholders in a single template ONLY.

### Non-Negotiable Constraints
1. **SINGLE TEMPLATE**: Only `templates/a1_template_v1.pdf`
2. **PLACEHOLDER REPLACEMENT ONLY**: Replace `{{token}}` with worker values
3. **NO STYLING/POSITIONING**: Never draw, style, reposition, or enhance
4. **CHECKBOX EXCEPTION**: Toggle checked/unchecked only - no moving
5. **NO NOTICES**: Never add watermarks or provisional stamps
6. **ISOLATED**: No imports from parent repository

### Allowed Actions
- Read worker JSON from --form parameter
- Replace `{{placeholder}}` tokens with values
- Toggle checkbox states if specified
- Create output PDF with only replacements

### Prohibited Actions
- Adding watermarks/notices
- Using template switching
- Adding styling/positioning changes
- Importing from `../scripts/` or parent
- Refactoring for aesthetics
- Mock data creation
- Workarounds

### Entry Point
```bash
python scripts/generate_simple.py --form input.json --output output.pdf
```

### Memory Tags
Use these tags for persistent notes:
- `#decision` - Permanent decision
- `#blocker` - Issue blocking progress  
- `#todo` - Action required
- `#skip` - Explicitly skip this

### Stop Conditions
If user asks for any prohibited action above, STOP and explain why it violates rules.
