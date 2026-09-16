---
name: jansa1-generation
description: Generate Czech A1 certificate PDFs using JanSA1 framework
---

# JanSA1 Generation Skill

## Purpose

Generate Czech A1 provisional PDFs using the JanSA1 framework.
Output goes to `output/provisional/`.

## Quick Start

```bash
# Generate all missing PDFs
python frameworks/jansa1_v1/v0.2-incremental/lib/gen_incremental.py

# Generate specific worker
python frameworks/jansa1_v1/v0.2-incremental/lib/gen_incremental.py --worker jiri-stembera

# Dry run
python frameworks/jansa1_v1/v0.2-incremental/lib/gen_incremental.py --dry-run
```

## Framework Versions

| Version | Purpose | Use |
|---------|---------|-----|
| v0.1 | Base generation | Legacy |
| v0.2 | Incremental | Current |
| v0.3 | Verification | After generation |

## Data Flow

```
review.csv → display_row() → row_to_form() → build_form_data() → PDF
```

## Configuration

```yaml
# config/a1_generation.yaml
source:
  review_csv: a1/review.csv
  cohort_json: a1/cohort.json
output:
  provisional_dir: output/provisional
```

## Rules

1. **Never generate official A1** - Only provisional drafts
2. **Use core logic** - Don't modify a1_core.py
3. **Verify after generation** - Run verification checks
4. **No hardcoded values** - All data from inputs

## Verification

After generation, run:

```bash
# Schema check
python frameworks/jansa1_v1/v0.3-verification/lib/chk_schema.py --file output.pdf

# Hardcode check
python frameworks/jansa1_v1/v0.3-verification/lib/chk_hardcode.py --worker ID --pdf output.pdf
```

## File Locations

| File | Purpose |
|------|---------|
| `scripts/a1_core.py` | Core PDF rendering |
| `scripts/finalize_a1.py` | CSV processing |
| `scripts/generate_incremental.py` | Incremental generator |
| `verification/*.py` | Verification checks |
