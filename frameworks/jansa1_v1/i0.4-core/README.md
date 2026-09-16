# Historical: Portal Core (i0.4)

**Status:** Legacy
**Source:** `portal/release1a/`
**Date:** 2026-08 to 2026-09

## Origin
```
portal/release1a/
├── a1_drafts.py              # Draft generation
├── a1_exports.py            # Export helpers
├── a1_generation_access.py  # Access control
├── a1_generation_confirmation.py  # Confirmation
├── management/commands/
│   └── a1_prepare_draft.py  # CLI draft command
└── services.py              # Service layer
```

## Key Files

| File | Purpose |
|------|---------|
| `a1_drafts.py` | Portal draft generation |
| `a1_exports.py` | Export to CSV/JSON |
| `a1_generation_access.py` | Authorization |
| `a1_prepare_draft.py` | CLI command |
| `services.py` | Service layer |

## Portal Workflow

1. Worker created in portal
2. Document uploaded
3. OCR proposals
4. A1 draft preparation
5. Visual confirmation
6. Download

## Integration Points

```python
# From portal
from portal.release1a.a1_drafts import prepare_application_draft

draft = prepare_application_draft(user, organization, case_id)
```

## Migrated To

- Current portal/release1a/ (still active)
- v0.3-verification (output validation)

## Notes

Portal integration evolved independently from CLI scripts.
Both now use shared core logic from scripts/a1_core.py.
