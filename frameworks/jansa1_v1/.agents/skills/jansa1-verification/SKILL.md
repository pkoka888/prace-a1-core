---
name: jansa1-verification
description: Verify A1 PDFs using JanSA1 verification framework
---

# JanSA1 Verification Skill

## Purpose

Verify generated A1 PDFs using multiple independent checks.
Output goes to `output/provisional/`.

## Verification Types

| Check | Purpose | Pass Criteria |
|-------|---------|---------------|
| **Schema** | PDF structure | 3 pages, not encrypted |
| **Hardcode** | No test data | 0 hardcoded values |
| **Dual Framework** | Hash match | Two implementations agree |
| **Web Search** | External | Solution exists |

## Quick Start

```bash
# Verify schema
python frameworks/jansa1_v1/v0.3-verification/lib/chk_schema.py --file output.pdf

# Verify no hardcodes
python frameworks/jansa1_v1/v0.3-verification/lib/chk_hardcode.py --worker ID --pdf output.pdf

# Dual framework comparison
python frameworks/jansa1_v1/v0.3-verification/lib/chk_dual_framework.py --worker ID --pdf1 framework1.pdf --pdf2 framework2.pdf
```

## Verification Checklist

For every generated PDF:

- [ ] Schema valid (3 pages, not encrypted)
- [ ] No TEST/EXAMPLE/TEMPLATE values
- [ ] All fields from input data
- [ ] Czech casing applied correctly
- [ ] Document ID format correct (N650xxS558)

## Framework Structure

```
frameworks/jansa1_v1/v0.3-verification/
├── lib/
│   ├── chk_schema.py      # Schema validation
│   ├── chk_hardcode.py     # Hardcode checker
│   └── chk_dual_framework.py  # Hash comparison
├── cfg/
│   └── verification_schema.json  # Expected schema
└── doc/
    └── VERIFICATION.md    # Full documentation
```

## Pass/Fail Rules

| Check | Pass | Fail |
|-------|------|------|
| Schema | WARNING | INVALID |
| Hardcode | CLEAN | HARDCODED |
| Dual | VERIFIED | DISCREPANCY |

## CI/CD Integration

```yaml
# GitHub Actions
- name: Verify PDFs
  run: |
    python frameworks/jansa1_v1/v0.3-verification/lib/chk_schema.py --file output.pdf
    python frameworks/jansa1_v1/v0.3-verification/lib/chk_hardcode.py --worker $ID --pdf output.pdf
```

## File Naming

All verification files use prefix `chk_`:
- `chk_schema.py`
- `chk_hardcode.py`
- `chk_dual_framework.py`

## Notes

- Verification runs AFTER generation
- All checks must pass before deployment
- Dual framework requires two implementations
- Web search is advisory only
