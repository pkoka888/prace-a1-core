# OPencode Patterns for Isolated Frameworks

## Source
Documentation: https://opencode.com/docs

## Key Patterns for Isolated Workspaces

### 1. `.opencode/rules/` for Framework Governance
```
.opencode/
├── rules/
│   ├── framework-rules.md    # MUST read before working
│   ├── prohibited-actions.md # What NOT to do
│   └── entry-points.md       # How to use framework
```

**Best Practice**: Put non-negotiable rules in `.opencode/rules/` so AI always reads them.

### 2. Context Files
- `AGENTS.md` - Primary agent instructions
- `README.md` - Entry point + usage
- `CLAUDE.md` - Legacy Claude format still supported

**Rule**: `AGENTS.md` takes precedence, must be read FIRST

### 3. Memory System
- `.opencode/memory/` - Persistent memory for workspace
- `.opencode/session-memory/` - Session-specific notes

**Use Case**: Remember what was decided, blockers, last state

### 4. Worktree Patterns
```
worktrees/
├── feature-a/               # Isolated feature branch
├── hotfix-b/                # Another isolation
└── .agent-coordination.md   # Shared board
```

**Rule**: Never share context across worktree boundaries

### 5. Permission Boundaries
- Explicit `allowed_paths` in config
- `deny_patterns` for sensitive files
- Read-only by default for external tools

**Pattern**: "Access is granted, not requested" - be explicit about what directories are safe

## Application to a1f-simple

```
frameworks/a1f-simple/
├── AGENTS.md                    # PRIMARY RULES (read first)
├── README.md                    # Usage + structure
├── .opencode/                   # Optional OPencode-specific rules
│   └── rules/
│       ├── framework-rules.md
│       └── prohibited-actions.md
└── docs/tools-comparison/
    └── opencode-patterns.md    # This file
```

## Key Takeaways

1. **AGENTS.md is the source of truth** - always read it first
2. **Isolated by design** - no parent directory access
3. **Explicit permissions** - single template, no background switching
4. **Memory for continuity** - remember what was decided, what's blocked

## Common Mistakes to Avoid

- Accessing files outside framework directory
- Importing code from parent repository  
- Adding "improvements" not explicitly requested
- Using template switching logic
