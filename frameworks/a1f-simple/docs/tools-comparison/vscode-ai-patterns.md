# VS Code AI Extension Patterns for Isolated Frameworks

## Source
VS Code AI documentation, GitHub Copilot patterns

## Key Patterns for Isolated Workspaces

### 1. `.vscode/` Workspace Configuration

```jsonc
// .vscode/settings.json
{
  "telemetry.machineId": null,
  "files.exclude": {
    "**/.git": true,
    "**/*.log": true,
    "**/secrets/": true
  },
  "files.watcherExclude": {
    "**/../**": true,
    "**/parent_repo/**": true
  }
}
```

**Best Practice**: Restrict file watching to current directory only

### 2. Workspace Recommendations

```json
// .vscode/extensions.json
{
  "recommendations": [
    "github.copilot",
    "claude.claude-code"
  ],
  "unwantedRecommendations": [
    "parent.repo.extension"
  ]
}
```

### 3. Task Definitions (tasks.json)

```jsonc
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "generate:a1",
      "type": "shell",
      "command": "python scripts/generate_simple.py",
      "args": ["--form", "examples/worker.json", "--output", "out.pdf"],
      "group": "build"
    }
  ]
}
```

### 4. Code Lens and Comments

Use code comments that AI assistants understand:

```python
# ai-context: this file replaces placeholders only, no styling
# ai-rule: DO NOT add watermarks or notices
# ai-rule: Use existing template at templates/a1_template_v1.pdf
```

## Application to a1f-simple

### .vscode Configuration
```
frameworks/a1f-simple/
├── .vscode/
│   ├── settings.json      # Restrict to framework dir
│   ├── extensions.json    # Recommend proper AI tools
│   └── tasks.json         # Build tasks: generate, test, validate
├── AGENTS.md
└── ...
```

### Recommended .vscode/settings.json
```jsonc
{
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  },
  "files.watcherExclude": {
    "**/../**/": true,
    "**/parent_repo/**": true,
    "**/scripts/": true,
    "**/tests_repo/": true
  },
  "search.exclude": {
    "**/venv/**": true,
    "**/.git/**": true
  },
  "python.analysis.excludePaths": [
    "../scripts",
    "../portal"
  ]
}
```

### AI-Specific Settings
```
# Enable reading AGENTS.md
"assistant.readGuidanceFiles": ["AGENTS.md", "README.md"]

# Restrict context to current folder
"assistant.context.limit": "workspace"
```

## VS Code AI Panel Instructions

When opening the AI panel in VS Code:

```
# AI Instructions for this Framework

## Mission
Replace placeholders in A1 template ONLY.

## Rules to Stop
- DO NOT ask about template switching
- DO NOT ask for "improvements"  
- DO NOT modify template except for placeholders

## Entry Points
- Run: Right-click generate_simple.py > Run Task "generate:a1"
- Edit: core/a1_core.py for placeholder logic
```

## Key Takeaways

1. **settings.json isolates** - prevent access to parent directories
2. **tasks.json standardizes** - consistent entry points
3. **extensions.json guides** - users get right tools
4. **AI comments work** - explicit rules in code

## Comparison: VS Code vs CLI AI

| Aspect | VS Code AI | CLI (opencode/claude) |
|--------|------------|----------------------|
| Config file | .vscode/settings.json | .opencode/, CLAUDE.md |
| Entry points | tasks.json | scripts/*.py |
| Rules format | Code comments, settings | AGENTS.md, CLAUDE.md |
| Isolation | File watchers | Directory restrictions |
| Learning | Integrated | CLI output |
