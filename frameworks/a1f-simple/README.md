# a1f-simple

Standalone framework for generating A1 provisional forms by replacing placeholders in `templates/a1_template_v1.pdf` with worker values.

## For AI Agents: How to Load and Work with This Framework

### 1. READ THESE FILES FIRST (in order)
1. **README.md** - This file (entry point)
2. **AGENTS.md** - Full mission, rules, constraints
3. **CLAUDE.md** - Claude Code compatibility (copy of AGENTS.md)
4. **.opencode/rules/framework-rules.md** - OPencode-specific rules

### 2. UNDERSTAND THE CORE RULES
- Use ONLY `templates/a1_template_v1.pdf` - no template switching
- Replace `{{placeholder}}` tokens with worker values ONLY
- Checkboxes are the ONLY exception - toggle checked/unchecked only, no repositioning
- NO notices, watermarks, styling, or "improvements"
- Self-contained: no parent imports, all paths relative to this framework

### 3. USE THE CLI TOOL
```bash
# Generate PDF from worker JSON
python scripts/generate_simple.py --form worker.json --output a1.pdf

# Advanced: with empty placeholder erase
python scripts/generate_simple.py --form worker.json --output a1.pdf --erase-empty
```

## Tools Compatibility

| Tool | How It Works | Path to Rules |
|------|--------------|---------------|
| Kilo | Reads AGENTS.md in `frameworks/a1f-simple/` | `frameworks/a1f-simple/AGENTS.md` |
| OPencode | Reads `.opencode/rules/` | `.opencode/rules/framework-rules.md` |
| Claude Code | Reads `CLAUDE.md` | `CLAUDE.md` (copy of AGENTS.md) |
| VS Code AI | Reads README.md first | `README.md` (rules at top) |
| Generic CLI | Uses scripts/ directly | N/A |

## Architecture

```
frameworks/a1f-simple/
├── AGENTS.md              # Primary rules (read first)
├── CLAUDE.md              # Claude Code compatibility  
├── README.md              # This file (entry point)
├── .opencode/             # OPencode rules
│   └── rules/
│       └── framework-rules.md
├── core/
│   ├── a1_core.py         # Main engine (placeholder replacement ONLY)
│   ├── generate.py        # Clean API wrapper
│   └── pdf_named_fields.py (reference only)
├── scripts/
│   └── generate_simple.py # CLI entry point
├── templates/
│   └── a1_template_v1.pdf # ONLY template
├── config/
│   └── a1_layout.json     # For checkbox positions only
├── tests/
│   └── test_placeholder_replacement.py
├── docs/
│   ├── GAP_ANALYSIS.md
│   ├── EXAMPLES.md
│   ├── RESEARCH_SOLUTIONS.md
│   └── tools-comparison/  # Tool patterns documentation
└── REPORT_TODOS.md        # Status and tasks
```

## CRITICAL RULES (Violations Must Stop Work)

❌ DO NOT:
- Add watermarks/notices/provisional stamps
- Use other templates or background files
- Add styling, font changes, or positioning
- Import from parent repository (`../scripts/`, etc.)
- Refactor for "improvements" not requested
- Create mock data as workaround

✅ DO:
- Replace `{{placeholder}}` with worker data
- Toggle checkbox states if specified in layout
- Fix issues directly without workarounds
