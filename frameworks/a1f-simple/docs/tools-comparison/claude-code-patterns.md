# Claude Code Patterns for Isolated Frameworks

## Source
Documentation: https://docs.anthropic.com/en/docs/claude-code

## Key Patterns for Isolated Workspaces

### 1. `CLAUDE.md` as Primary Instructions
Claude Code reads `CLAUDE.md` in project root before starting work.

**Pattern**: Create `CLAUDE.md` alongside `AGENTS.md` for compatibility across tools.

```markdown
# CLAUDE.md

## Project Rules (ALWAYS FOLLOW THESE)
1. ONLY use templates/a1_template_v1.pdf
2. ONLY replace placeholders - no styling/improvements
3. NEVER use parent repository code
4. NO notices/watermarks

## Work Done So Far
- Template created at templates/a1_template_v1.pdf
- Core engine at core/a1_core.py
```

### 2. Workspace Context Files
Claude Code respects these files automatically:
- `CLAUDE.md` - Primary instructions
- `.claude/agents/` - Custom agent definitions  
- `.claude/rules/` - Rule files (with Claude Enterprise)
- `README.md` - Project overview

### 3. Agent Handoff Protocol
When delegating work:

```bash
# Tell Claude what to do
echo "Analyze placeholders in template" | claude-code --execute
```

**Best Practice**: Provide exact task descriptions rather than vague requests

### 4. File System Isolation
Claude Code can be restricted to specific directories via:
- `claude.conf` configuration
- Permission prompts per-directory
- `allowed_directories` in settings

**Rule**: Explicitly declare allowed directories in instructions

### 5. Memory & Learning
- `scripts/` prefix for runnable code
- `.claude.md.memory` for persistent workspace memory
- Session memory resets each conversation

**Use Case**: Mark decisions as "permanent" or "temporary" to avoid re-asking

## Application to a1f-simple

### File Structure
```
frameworks/a1f-simple/
├── CLAUDE.md           # Claude Code compatibility  
├── AGENTS.md           # Kilo/standalone rules
├── README.md           # Entry point
└── .claude/
    └── rules/
        └── framework-only.md  # Prohibited actions
```

### CLAUDE.md Content
```markdown
# A1F-SIMPLE Framework - CLAUDE.md

## RULES (FOLLOW THESE OR STOP WORK)

⚠️ CRITICAL: This is an ISOLATED FRAMEWORK
- Use ONLY templates/a1_template_v1.pdf
- Replace placeholders ONLY
- NO styling, NO watermarks, NO notices
- NEVER import from parent repository

## STOP IF ASKED TO DO:
- Add watermarks/notices
- Use other templates  
- Change styling/positions
- Import from scripts/

## HOW TO WORK
1. Read AGENTS.md first
2. Use scripts/generate_simple.py
3. Test with example data
```

## Key Takeaways

1. **CLAUDE.md is read automatically** - create it for Claude Code users
2. **Explicit "STOP IF" rules** - clear termination conditions
3. **File structure matters** - Claude respects standard layouts
4. **Memory is session-scoped** - document decisions that must persist

## Comparison: AGENTS.md vs CLAUDE.md

| Feature | AGENTS.md | CLAUDE.md |
|---------|-----------|-----------|
| Read by | Kilo, OPencode | Claude Code |
| Location | Project root OR subdirectory | Project root preferred |
| Precedence | Framework-specific | Project-specific fallback |
| Rule format | Markdown sections | Markdown at top priority |

**Recommendation**: Create both for maximum compatibility
