# General Patterns for Self-Contained AI Frameworks

Research-based patterns for creating maintainable, isolated frameworks that work well with AI coding assistants.

## Source
Kilo docs, OPencode patterns, Claude Code docs, VS Code AI patterns, GitHub Copilot patterns

## Core Principles

### 1. Single Entry Point
```
framework/
├── AGENTS.md       # FIRST READ
├── README.md       # USAGE
└── scripts/main.py # ONLY entry point
```

**Rule**: One way to do things. No alternative paths.

### 2. Explicit Non-Negotiables
List what to STOP working on:

```markdown
## STOP IF ASKED TO DO:
- Add watermarks or notices
- Use other templates  
- Change positioning
- Import from parent
- Refactor for "cleanliness"
```

**Pattern**: Explicit negative examples are more effective than positive lists

### 3. Isolated File Structure
```
framework/
├── core/           # Engine (placeholder replacement)
├── scripts/        # CLI entry points
├── templates/      # SINGLE template only
├── tests/          # Framework tests only
├── examples/       # Example data
├── docs/           # Documentation
├── config/         # Minimal config (checkbox only)
└── AGENTS.md       # Rules
```

**Rule**: No cross-references to parent directories

### 4. Self-Contained Dependencies
```
# requirements.txt should be minimal
pymupdf>=1.23.0
pypdf>=4.0.0
```

**Best Practice**: Only what's needed for the single job

### 5. Test Pattern for Framework
```python
def test_only_replaces_placeholders():
    """Verify no extra text/watermarks added."""
    # 1. Generate from min form
    # 2. Verify all placeholders replaced
    # 3. Verify no notices present
    # 4. Verify template content otherwise unchanged
```

## Tool Compatibility Matrix

| Tool | Primary File | Secondary | Features |
|------|-------------|-----------|----------|
| Kilo | AGENTS.md | README.md | Full control |
| OPencode | AGENTS.md | CLAUDE.md | Memory, Rules |
| Claude Code | CLAUDE.md | AGENTS.md | Automatic read, Sessions |
| VS Code AI | README.md | AGENTS.md | Tasks, Settings |
| Copilot | README.md | .copilot/ | Instructions |

## Framework Template (Copy this pattern)

```markdown
# AGENTS.md

## Mission (One sentence)
Create X by doing Y ONLY.

## Rules (Non-negotiable)
1. Use ONLY [...]
2. Do ONLY [...]
3. Do NOT [...]

## Archictecture
- **Input**: [...]
- **Engine**: [...]
- **Output**: [...]

## Commands
```bash
# Usage
command --args
```

## Testing
- Verify [what matters]
- Verify [what NOT to add]
- Verify [constraints]

## Stop Conditions
If asked to do: [list prohibited actions], STOP.
```

## Common Anti-Patterns (Avoid These)

1. **"Well, I'll just add..."** - Nothing beyond stated purpose
2. **Template switching** - One template, period
3. **Future-proofing** - Handle what exists now
4. **Mock data** - Fix with real data instead
5. **Workaround layers** - Direct solution
6. **Cross-framework deps** - Copy minimal code, don't import

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-10-24 | Single template only | Avoid template drift, simpler maintenance |
| 2024-10-24 | No notices/watermarks | User explicitly requested placeholder-only replacement |
| 2024-10-24 | Copy core logic | Faster than abstract "framework system" |

Track decisions here. Every exception must be documented.
