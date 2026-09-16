# Historical: Agent Skill A1 (i0.2)

**Status:** Legacy  
**Source:** `.agents/skills/a1-pdf-production/`
**Date:** 2026-08

## Origin
```
.agents/skills/a1-pdf-production/
├── SKILL.md          # Agent skill definition
├── agents/         # Agent-specific helpers
└── references/     # Reference materials
```

## Purpose
Agent-facing skill for A1 PDF production:
- Template cleaning
- Field/checkbox placement
- Employee cohort generation
- PDF regression analysis
- Preview rendering
- Manifests

## Key Content

### SKILL.md
```markdown
## Ground the run

1. Read the repository `AGENTS.md` and field-policy.md
2. Inspect `git status`; preserve unrelated work
3. Resolve the current provisional cohort only from 
   `$A1_PRIVATE_DIR/a1/review.csv` plus `$A1_PRIVATE_DIR/a1/cohort.json`
```

## References

| File | Purpose |
|------|---------|
| `references/field-policy.md` | Field policy rules |
| `references/visual-qa.schema.json` | QA schema |
| `references/mcp-contract.md` | MCP contract |

## Migrated To

- v0.3-verification (verification logic)
- Main SKILL.md (agent instructions)

## Notes

This was the agent-facing documentation. Now integrated
into main AGENTS.md and simplified docstrings.
