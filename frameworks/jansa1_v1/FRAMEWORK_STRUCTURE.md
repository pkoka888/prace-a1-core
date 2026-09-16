# JanSA1 Framework - Structure Definition

## Framework Identity

| Property | Value |
|----------|-------|
| **Name** | JanSA1_v1 |
| **Full Name** | Jan's A1 Version 1 |
| **Purpose** | Czech A1 Certificate PDF Generation |
| **Language** | Python 3.13 |
| **License** | Private |

## Directory Structure

```
frameworks/
└── jansa1_v1/                    # Main framework folder
    ├── README.md                 # Framework overview
    ├── VERSIONS.md              # Version history
    ├── FRAMEWORK_STRUCTURE.md   # This file
    │
    ├── v0.1-base/              # Version 0.1 - Original
    │   ├── gen_provisional.py  # Batch generator (PREFIX: gen_)
    │   ├── fin_a1.py           # Finalization (DEPRECATED)
    │   ├── a1_core.py          # Core rendering
    │   └── doc_base.md         # Documentation
    │
    ├── v0.2-incremental/       # Version 0.2 - Incremental
    │   ├── gen_incremental.py  # Incremental generator
    │   ├── cfg_generation.yaml # YAML config (PREFIX: cfg_)
    │   └── doc_incremental.md  # Documentation
    │
    ├── v0.3-verification/       # Version 0.3 - Verification
    │   ├── chk_dual.py         # Dual framework check (PREFIX: chk_)
    │   ├── chk_hardcode.py     # Hardcode check
    │   ├── chk_schema.py       # Schema validation
    │   ├── chk_web.py          # Web search
    │   └── doc_verification.md  # Documentation
    │
    └── current/                 # Symlink to latest stable
        └── -> ../v0.3-verification
```

## File Naming Convention

### Prefix System

To prevent duplicates and clarify purpose:

| Prefix | Type | Description | Example |
|--------|------|-------------|---------|
| `gen_` | Generator | Creates output | `gen_incremental.py` |
| `chk_` | Checker | Verifies output | `chk_hardcode.py` |
| `val_` | Validator | Validates data | `val_schema.py` |
| `cfg_` | Config | Configuration | `cfg_generation.yaml` |
| `doc_` | Docs | Documentation | `doc_architecture.md` |
| `tst_` | Test | Unit tests | `tst_core_logic.py` |
| `lib_` | Library | Shared code | `lib_processing.py` |

### File Extension Standards

| Extension | Type | Usage |
|-----------|------|-------|
| `.py` | Python | Scripts and modules |
| `.yaml` | YAML | Configuration |
| `.json` | JSON | Data files |
| `.md` | Markdown | Documentation |
| `.sh` | Shell | Shell scripts |

## Data Flow

```mermaid
flowchart TD
    subgraph INPUT["Input Layer"]
        CSV[a1/review.csv]
        COHORT[a1/cohort.json]
        EMPLOYEES[a1/employees.json]
        PROFILES[config/institutions/]
    end

    subgraph PROCESS["Processing (v0.2)"]
        READ[lib_read_csv]
        DISPLAY[lib_display_case]
        TRANSFORM[lib_transform]
        BUILD[lib_build_form]
    end

    subgraph GENERATE["Generation"]
        OVERLAY[gen_overlay]
        STAMP[gen_stamp]
        RENDER[gen_render]
    end

    subgraph VERIFY["Verification (v0.3)"]
        CHK_HASH[chk_dual]
        CHK_HARDC[chk_hardcode]
        CHK_SCHEMA[chk_schema]
        CHK_WEB[chk_web]
    end

    subgraph OUTPUT["Output"]
        PDF[A1_{worker}.pdf]
        MANIFEST[manifest.json]
    end

    INPUT --> PROCESS
    PROCESS --> GENERATE
    GENERATE --> OUTPUT
    OUTPUT --> VERIFY
```

## Core Libraries (lib_)

```
lib_processing.py       # Core data transformations
├── display_row()       # ALL-CAPS → Czech casing
├── transform_form()     # CSV → nested dict
└── build_data()        # Enrich and validate

lib_rendering.py       # PDF generation
├── render_overlay()    # Text overlay
├── stamp_document()    # Add markers
└── generate_pdf()     # Final PDF

lib_verification.py    # Shared verification
├── compare_hashes()    # Hash comparison
├── check_patterns()    # Pattern matching
└── validate_schema()   # Schema validation
```

## Version Contract

Each version must define:

1. **Input Contract** - What data is required
2. **Output Contract** - What is produced
3. **Verification Contract** - How to verify
4. **Migration Path** - How to upgrade

### v0.1 Contract (Base)
```yaml
input:
  - review.csv
  - cohort.json
  - employees.json
output:
  - A1_{worker}.pdf (batch)
verification:
  - Manual visual check
```

### v0.2 Contract (Incremental)
```yaml
input:
  - review.csv
  - cohort.json
  - employees.json (optional)
output:
  - A1_{worker}.pdf (missing only)
verification:
  - Hash comparison
  - Hardcode check
```

### v0.3 Contract (Verification)
```yaml
input:
  - Any PDF output
  - Source data
output:
  - Verification report
verification:
  - Dual framework
  - Schema validation
  - Web search
  - Hardcode check
```

## Integration Points

### Dashboard Integration
```python
# Called by dashboard
from frameworks.jansa1_v1.v0.2_incremental.gen_incremental import main
main(workers=["id1", "id2"])

# Verification after
from frameworks.jansa1_v1.v0.3_verification.chk_schema import main
main(file="output.pdf")
```

### CI/CD Integration
```yaml
# .github/workflows/a1.yml
- name: Generate A1
  run: python frameworks/jansa1_v1/current/gen_incremental.py

- name: Verify A1
  run: python frameworks/jansa1_v1/current/chk_schema.py --file output.pdf
```

## Best Practices

1. **Never modify historical versions** - Create new version instead
2. **Use prefixes consistently** - Prevents naming conflicts
3. **Document contracts** - Each version has clear I/O
4. **Test in isolation** - Version-specific tests
5. **Symlink current/** - Always points to latest stable

## Anti-Patterns

❌ Don't modify v0.1 files after v0.2 exists
❌ Don't use generic names like `test.py`
❌ Don't skip verification
❌ Don't hardcode values
❌ Don't create duplicate functionality

## Migration Checklist

When creating new version:

- [ ] Copy previous version as base
- [ ] Rename files with new prefix
- [ ] Update version in README
- [ ] Add migration notes
- [ ] Update symlink
- [ ] Test compatibility
- [ ] Document breaking changes
