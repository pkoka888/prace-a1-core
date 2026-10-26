# Tool Comparison Matrix: AI Framework Patterns

Comparison of patterns across popular AI coding assistants for creating isolated/self-contained frameworks.

## Comparison Table

| Concern | OPencode | Claude Code | VS Code AI | Kilo | Recommendation |
|---------|----------|-------------|------------|------|----------------|
| Primary rules file | `.opencode/rules/` | `CLAUDE.md` | README.md (with comments) | `AGENTS.md` | AGENTS.md primary, CLAUDE.md fallback |
| Entry points | CLI scripts | CLI scripts | tasks.json + scripts | scripts/*.py | scripts/ prefix standard |
| File isolation | allowed_paths | worktree/permission | .vscode/watcherExclude | kilo.json | Explicit "only this dir" |
| Rule enforcement | Rules system | "STOP" patterns | Comments | AGENTS.md | Use "STOP IF" list |
| Memory | `.opencode/memory/` | Session-based | Integrated | None | Document in AGENTS.md |
| Dependency control | requirements.txt | requirements.txt | venv + extensions.json | venv | Minimal venv |

## Detailed Recommendations

### Rules Files
1. **AGENTS.md** - Primary source, read by all compatible tools
2. **CLAUDE.md** - Backup for Claude Code users (same content, rename)
3. **README.md** - Entry point, contains critical rules upfront

### Directory Isolation
```
# .opencode/rules/isolation.md
Only work in this framework directory
Do not import from parent repository
One template only: templates/a1_template_v1.pdf
```

### Entry Points Naming
| Tool Expected | Our Framework |
|--------------|---------------|
| scripts/main.py | scripts/generate_simple.py |
| cli/entry.py | cli/entry.py (optional) |
| run.sh | scripts/run.sh |

**Recommendation**: Use `scripts/generate_simple.py` - clear and follows Python conventions

### Permission Patterns

#### OPencode Permissions
```json
// .opencode/permissions.json
{
  "allowed_paths": [
    "./"  // current framework only
  ],
  "deny_patterns": [
    "*/../",
    "*/parent_repo/*"
  ]
}
```

#### VS Code File Watching
```jsonc
// .vscode/settings.json
{
  "files.watcherExclude": {
    "**/../**": true,
    "**/scripts/": true,
    "**/tests_repo/": true
  }
}
```

### Memory & State Tracking
Each tool has different approaches:

| Tool | Mechanism | Scope |
|------|-----------|-------|
| OPencode | `.opencode/memory/` | Persistent |
| Claude | In-chat context | Session |
| VS Code | `settings.json` | Workspace |
| Kilo | Agent manager | Session |

**Recommendation**: Document persistent state in AGENTS.md

## Universal Best Practices

### 1. Rule Documentation Pattern
```markdown
## STOP IF ASKED TO DO (Never do these):

1. Add watermarks or notices
2. Use other templates
3. Change element positions
4. Import from parent directory
5. Refactor without explicit request
```

### 2. File Structure Pattern
```
framework/
├── AGENTS.md     │ Primary rules
├── CLAUDE.md     │ Claude Code compatibility (copy ADN)
├── README.md     │ Entry point
├── scripts/      │ CLI entry points
├── core/         │ Engine (standalone)
├── tests/        │ Framework tests
├── templates/    │ Single template only
├── config/       │ Minimal config
├── examples/     │ Example data
├── .vscode/      │ Optional editor config
└── docs/
    └── tools-comparison/ │ This directory
```

### 3. Entry Point Pattern
```python
#!/usr/bin/env python3
"""
Framework entry point - replaces placeholders only.
Usage:
    python scripts/generate_simple.py --form worker.json --output out.pdf
"""
```

### 4. Test Pattern
```python
def test_no_extra_content_added():
    """Verify framework respects 'no improvements' rule."""
    generate(form_with_minimal_data)
    pdf = read_output()
    assert_not watermark_present(pdf)
    assert_not notice_present(pdf)  
    assert_only placeholders_replaced(pdf)
```

## Tool-Specific Additions

### For OPencode Users
Create `.opencode/rules/framework-rules.md`:
```
Rules for a1f-simple framework:
- SINGLE TEMPLATE: templates/a1_template_v1.pdf
- ONLY PLACEHOLDERS: Replace {{...}} only
- NO IMPROVEMENTS: No styling, positioning changes
- CHECKBOX EXCEPTION: Only toggle state, don't move
```

### For Claude Code Users
`CLAUDE.md` is auto-read. Copy AGENTS.md content there.

### For VS Code Users
Add to `.vscode/settings.json`:
```json
{
  "assistant.readGuidanceFiles": ["AGENTS.md", "README.md"]
}
```

## Key Takeaway

Different tools expect different conventions. Support ALL through:
1. **AGENTS.md** - Kilo/primary
2. **CLAUDE.md** - Claude Code compatibility
3. **README.md upfront rules** - VS Code/Copilot
4. **scripts/*.py** - Universal entry point
