# Historical: Workflow A1 (i0.1)

**Status:** Legacy
**Source:** `workflows/a1/`
**Date:** 2026-08

## Origin
```
workflows/a1/
├── README.md          # Original workflow documentation
└── .archive/         # Superseded scripts
```

## Documentation
```markdown
# A1 PDF Production — Semi-Manual Framework

## Overview

This framework generates provisional A1 certificate PDFs for 
Czech/German cross-border workers from identity card scans.
```

## Key Files

| File | Purpose |
|------|---------|
| `workflows/a1/README.md` | Original workflow documentation |

## Workflow

1. Scan Upload → `scans/`
2. OCR Extraction → `ocr/`
3. Transcription → `a1/review.csv`
4. PDF Generation → `output/provisional/`
5. Visual QA → `output/previews/`

## Migrated To

- v0.2-incremental (generation logic)
- v0.3-verification (QA pipeline)

## Notes

This was the original workflow before the framework was
formalized. Now archived in `.archive/`.
