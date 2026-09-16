# LangGraph Integration Guide

## Principle: Core stays clean, LangGraph is optional orchestration layer

```
┌─────────────────────────────────────────────────────────┐
│  Core Logic (deterministic, tested)                      │
│  - a1_core.py, finalize_a1.py                           │
│  - Pure functions, no external state                     │
│  - Unit tested, reproducible                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (optional)
┌─────────────────────────────────────────────────────────┐
│  LangGraph Orchestration (research/exploration)          │
│  - Research workflows                                   │
│  - OSSZ verification                                    │
│  - OCR provider fallback                                │
│  - Human-in-the-loop review flows                       │
└─────────────────────────────────────────────────────────┘
```

## Good LangGraph use cases

| Use Case | Why LangGraph | Example |
|----------|---------------|---------|
| **OSSZ research** | Multi-source verification, URL checking | Check CSSZ, extract contact, validate |
| **Institution updates** | Step-by-step verification, fallbacks | Try URL A → URL B → manual |
| **OCR orchestration** | Provider fallback, retry logic | MiniMax → fallback → queue |
| **Research workflows** | State management, branching | Gather → analyze → summarize |

## NOT for LangGraph

| Use Case | Why NOT | Solution |
|----------|---------|----------|
| **A1 PDF generation** | Deterministic, no state | Use core directly |
| **Data validation** | Pure functions | Unit tests |
| **Database operations** | Django ORM handles this | Services layer |

## Integration pattern

```python
# scripts/research/ossz_verification.py
from langgraph.graph import StateGraph
from typing import TypedDict

class OSSZState(TypedDict):
    institution_id: str
    sources_checked: list[str]
    verified_data: dict | None
    errors: list[str]

def verify_ossz(institution_id: str) -> dict:
    """LangGraph workflow for OSSZ verification."""
    # Uses core logic for validation, LangGraph for orchestration
    graph = StateGraph(OSSZState)
    # ... workflow definition
    return result
```

## File structure

```
research/
├── langgraph/                    # LangGraph workflows (optional)
│   ├── __init__.py
│   ├── ossz_verification.py     # OSSZ research workflow
│   ├── institution_updates.py   # Institution data updates
│   └── ocr_orchestration.py    # OCR provider fallback
├── acquisition/                  # Research data (existing)
│   └── ...
scripts/
├── core/                         # Core deterministic logic (existing)
│   ├── a1_core.py
│   └── finalize_a1.py
```

## Key rules

1. **Core is always the source of truth** - LangGraph calls core, not the other way
2. **Core has no LangGraph imports** - keeps it testable without LangGraph
3. **LangGraph workflows are optional** - deployment doesn't require them
4. **Research outputs go to research/** - not to production data

## Example: OSSZ verification flow

```python
# research/langgraph/ossz_verification.py
"""
OSSZ institution verification workflow.

Uses LangGraph to orchestrate:
1. Check institutional website (CSSZ)
2. Extract signatory data
3. Validate against existing profile
4. Generate update proposal
"""
```

This keeps the deterministic core clean while enabling sophisticated research workflows.
