# JanSA1 Framework v1

**Framework Name:** JanSA1_v1 (Jan's A1 Version 1)
**Purpose:** Czech A1 Certificate PDF Generation with Verification
**Status:** Active

## Quick Start

```bash
# Generate missing PDFs
python frameworks/jansa1_v1/v0.2-incremental/lib/gen_incremental.py

# Verify generation
python frameworks/jansa1_v1/v0.3-verification/lib/chk_schema.py --file output.pdf
python frameworks/jansa1_v1/v0.3-verification/lib/chk_hardcode.py --worker ID --pdf output.pdf
```

## Directory Structure

```
frameworks/jansa1_v1/
├── README.md                    # This file
├── VERSIONS.md                # Version history
├── FRAMEWORK_STRUCTURE.md     # Structure definition
├── RESEARCH.md                # Research notes
│
├── .github/workflows/         # GitHub Actions
│   └── jansa1.yml            # CI/CD pipeline
│
├── .gitlab-ci.yml            # GitLab CI/CD
│
├── .agents/skills/           # Agent skills
│   ├── jansa1-generation/   # Generation skill
│   └── jansa1-verification/ # Verification skill
│
├── i0.1-workflow/           # Historical: Original workflow
├── i0.2-skill/             # Historical: Agent skill
├── i0.3-scripts/           # Historical: Core scripts
├── i0.4-core/              # Historical: Portal core
│
├── v0.1-base/             # Version 0.1: Batch generation
├── v0.2-incremental/        # Version 0.2: Incremental generation
│   └── lib/
│       └── gen_incremental.py
│
├── v0.3-verification/        # Version 0.3: Verification
│   └── lib/
│       ├── chk_schema.py
│       ├── chk_hardcode.py
│       └── chk_dual_framework.py
│
└── v0.4-current/           # Version 0.4: Current (development)
```

## Version History

| Prefix | Version | Description | Date |
|--------|---------|-------------|------|
| i | i0.1 | Historical: Workflow | 2026-08 |
| i | i0.2 | Historical: Agent Skill | 2026-08 |
| i | i0.3 | Historical: Scripts | 2026-08 |
| i | i0.4 | Historical: Portal | 2026-08 |
| v | v0.1 | Base batch generation | 2026-08 |
| v | v0.2 | Incremental generation | 2026-09 |
| v | v0.3 | Verification framework | 2026-09 |
| v | v0.4 | Current development | Current |

## File Naming Convention

| Prefix | Type | Example |
|--------|------|---------|
| `gen_` | Generator | `gen_incremental.py` |
| `chk_` | Checker | `chk_schema.py` |
| `cfg_` | Config | `cfg_generation.yaml` |
| `lib_` | Library | `lib_processing.py` |

## CI/CD Pipelines

### GitHub Actions

```yaml
# .github/workflows/jansa1.yml
name: JanSA1 Framework
on: [push, pull_request]
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate PDFs
        run: python frameworks/jansa1_v1/v0.2-incremental/lib/gen_incremental.py
  verify:
    needs: generate
    steps:
      - name: Verify schema
        run: python frameworks/jansa1_v1/v0.3-verification/lib/chk_schema.py --file output.pdf
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - generate
  - verify
  - test
  - deploy

generate-pdfs:
  stage: generate
  script:
    - python frameworks/jansa1_v1/v0.2-incremental/lib/gen_incremental.py

verify-schema:
  stage: verify
  script:
    - python frameworks/jansa1_v1/v0.3-verification/lib/chk_schema.py --file output.pdf
```

## Agent Skills

### Generation Skill

```markdown
# .agents/skills/jansa1-generation/SKILL.md
---
name: jansa1-generation
description: Generate Czech A1 certificate PDFs
---

Use `gen_incremental.py` to generate PDFs.
Output goes to `output/provisional/`.
```

### Verification Skill

```markdown
# .agents/skills/jansa1-verification/SKILL.md
---
name: jansa1-verification
description: Verify A1 PDFs
---

Run schema and hardcode checks after generation.
```

## Best Practices

1. **Use Incremental Generation** - Only generates missing PDFs
2. **Verify After Generation** - Run all verification checks
3. **Use CI/CD** - Automated pipelines ensure quality
4. **Follow Naming Convention** - Consistent file naming
5. **Document Changes** - Update version history

## When to Use This Structure

### ✓ Optimal For

- Multi-version frameworks with clear evolution
- Projects needing CI/CD integration
- Agent-accessible skills
- Verification-heavy workflows
- Documented historical versions

### ✗ Not Optimal For

- Simple single-file scripts
- One-off experiments
- Very small projects
- Projects without version history

## Integration with Main Project

The framework references main project files:

```python
# References to scripts/
ROOT = Path(__file__).resolve().parents[4]
from scripts.a1_core import build_form_data
from scripts.finalize_a1 import display_row
```

This keeps the framework portable while using shared core logic.

## Git Branch Naming

For framework development:
- `feat/jansa1-v1` - New features
- `fix/jansa1-verification` - Bug fixes
- `docs/jansa1-framework` - Documentation

## Related Documentation

- [Architecture Docs](../../docs/architecture/ARCHITECTURE.md)
- [Verification Framework](../../docs/architecture/verification-framework.md)
- [LangGraph Integration](../../docs/architecture/langgraph-integration.md)

## License

Private - Internal use only
