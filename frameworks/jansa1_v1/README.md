# JanSA1 Framework v1

**Framework Name:** JanSA1_v1 (Jan's A1 Version 1)
**Purpose:** Czech A1 Certificate PDF Generation with Verification
**Status:** Active

## Overview

```
frameworks/jansa1_v1/
├── README.md                    # This file
├── FRAMEWORK_STRUCTURE.md       # Architecture definition
├── VERSIONS.md                 # Version history
│
├── v0.1-base/                 # Base generation (original)
│   ├── gen_provisional.py     # Original batch generator
│   ├── fin_a1.py              # Finalization logic
│   └── a1_core.py             # Core rendering
│
├── v0.2-incremental/          # Incremental generation
│   ├── gen_incremental.py     # Incremental generator
│   └── a1_generation.yaml     # YAML config
│
├── v0.3-verification/         # Verification framework
│   ├── dual_framework.py      # Hash comparison
│   ├── hardcode_check.py      # No hardcodes check
│   ├── schema_valid.py        # Schema validation
│   └── web_search.py         # External verification
│
└── current/                   # Symlink to latest stable
    └── -> ../v0.3-verification
```

## File Naming Convention

All files use prefixes to prevent duplicates:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `gen_` | Generator scripts | `gen_provisional.py`, `gen_incremental.py` |
| `chk_` | Checker/validator | `chk_hardcode.py`, `chk_schema.py` |
| `val_` | Validator scripts | `val_dual_framework.py` |
| `cfg_` | Configuration | `cfg_generation.yaml`, `cfg_provisional.json` |
| `doc_` | Documentation | `doc_architecture.md` |

## Version History

| Version | Description | Date |
|---------|-------------|------|
| v0.1 | Base generation - original batch processing | 2026-08 |
| v0.2 | Incremental generation - only missing PDFs | 2026-09 |
| v0.3 | Verification framework - dual checks | 2026-09 |

## Usage

```bash
# Generate all missing PDFs
python frameworks/jansa1_v1/current/gen_incremental.py

# Verify last generation
python frameworks/jansa1_v1/current/chk_schema.py --file output.pdf
python frameworks/jansa1_v1/current/chk_hardcode.py --worker id --pdf output.pdf
```

## Research Sources

This framework is based on:
- CSSZ (Czech Social Security Administration) official guidelines
- EU A1 certificate regulations
- Czech form standards

See `docs/architecture/ARCHITECTURE.md` for full architecture.
