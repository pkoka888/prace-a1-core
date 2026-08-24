# Market Research Evidence Workflow (WF-AC)

## Overview

WF-AC collects and validates market, workflow, and architecture evidence for Czech/German invoice processing and accounting automation. It is **research-only**: definitive bookkeeping, tax calculations, and real invoice ingestion are NOT authorized here. All evidence is provisional until passing human review and reproducibility gates.

**Status:** experimental — blocked until Capture/Proposal Integrity 1.3 and both pilots pass their evidence/review/safety/reproducibility gates.

---

## File Map

### Core Scripts

| File | Purpose |
|------|---------|
| `scripts/collect_market_evidence.py` | Raw lane writer. Produces `research/acquisition/raw/<lane>.json` (never canonical entities). |
| `scripts/normalize_datasets.py` | Merges raw lanes into schema-valid candidate envelope. Fail-closed on schema violations. |
| `scripts/score_research_results.py` | Calculates deterministic scores (authority, recency, corroboration, completeness, accounting_fit). |
| `scripts/generate_research_cockpit.py` | Renders static HTML cockpit from validated envelope. Strict CSP and XSS protections. |
| `scripts/capture_research_sources.py` | Bounded public-source capture into immutable run directories. Fixture/live modes. |
| `scripts/compare_research_runs.py` | Validates and compares two collection runs for reproducibility. |
| `scripts/check_research_completeness.py` | Validates cohort quotas (10+ per lane) against schema-valid entities. |
| `scripts/validate_research_schema.py` | **Canonical validation library.** Single source of truth for schema v1.2. |
| `scripts/generate_research_review_queue.py` | Generates deterministic, hash-bound operator review queue. Non-authoritative. |
| `scripts/validate_research_review_response.py` | Validates completed operator responses against immutable queue. |
| `scripts/create_synthetic_benchmark.py` | Renders synthetic Czech invoice PDFs from ground truth. No network, no real data. |
| `scripts/run_ocr_benchmark.py` | Synthetic OCR benchmark probe. Marks engines `unproven` (lightweight honest pass). |

### Data Directories

| Directory | Content |
|-----------|---------|
| `research/acquisition/raw/` | Lane-specific raw evidence files (5 lanes). |
| `research/acquisition/atomic-*.json` | Frozen atomic collection runs. |
| `research/processed/entities.json` | Canonical processed entity envelope. |
| `research/query-packs/` | Frozen query packs and collector protocols. |
| `research/review/` | Hash-bound operator review queues. |
| `research/synthetic/` | Ground truth and synthetic artifacts for benchmark. |
| `research/benchmark-experimental/` | Quarantined experimental benchmark (invalid-for-scoring). |
| `docs/prototypes/research-cockpit/` | Generated HTML cockpits. |

---

## Key Constraints

- **No real data** — synthetic fixtures only; never employee, A1, invoice, or credential content
- **No production invoice ingestion** — portal scaffold does not depend on this workflow
- **No tax calculation or bookkeeping** — awaits specialist certification
- **No payment processing integration**
- **Evidence states:** `provisional` → `primary-source-verified` → `operator-verified` → `specialist-verified`
- Exit requires: complete evidence corpus, both pilots on two repeatable runs, repaired benchmark passing all gates

---

## Quick Reference

```bash
# Validate envelope + check completeness
python3 scripts/validate_research_schema.py --input research/processed/entities.json
python3 scripts/check_research_completeness.py

# Generate review queue (non-authoritative)
python3 scripts/generate_research_review_queue.py --pack research/query-packs/plan-ac-core-1.1.json --output research/review/queue-v1.1.json

# Generate cockpit
python3 scripts/generate_research_cockpit.py --input research/processed/entities.json --output docs/prototypes/research-cockpit/pilot.html
```
