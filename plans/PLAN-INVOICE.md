# Plan PLAN-INVOICE — Accounting Automation Research and Invoice Ingestion Foundation

**Status**: active
**Milestone**: M1B+

## Purpose

Single governing plan for the provisional Czech/German market and accounting
research and the public/synthetic invoice ingestion/review/export foundation:
invoice automation research, invoice ingestion foundation, and payroll/finance
architecture.

Replaces and consolidates the dated plans:

- `plans/2026-08-13-plan-ac-accounting-automation-research.md`
- `plans/2026-08-14-plan-ad-invoice-ingestion-foundation.md`
- `plans/2026-08-12-plan-p-payroll-and-finance-architecture.md`

The archive of the individual dated plans lives under `.archive/plans/`; the
tracked source of truth is this file plus [`plans/INDEX.md`](INDEX.md).

## Status and governance

- Status: `active` — research and public/synthetic in-memory proof may proceed;
  no accounting behavior is authorized.
- Decision state: `prototype-required` (also by
  [`DEC-015`](../docs/decisions/decision-register.md)).
- Evidence: `provisional` — research corpora and benchmark remain draft until
  the evidence, review, leakage, safety, and reproducibility gates pass.

## Dependencies (catalog-recorded)

- `PLAN-LEGAL`, `PLAN-INFRA`, `PLAN-WORKERS`, and milestone `M3` with gate
  `evidence-only` — legal constraints, operating baseline, role/data discovery,
  and the M3 document workflow inform ingestion scope.
- `DEC-015` with gate `specialist-gate` — persistence/adapters, production
  implementation, and Plan acceptance require accounting-specialist sign-off.

## Contents and exit evidence

- **Research (provisional):** experimental skill
  [`.opencode/skills/market-research-evidence/SKILL.md`](../.opencode/skills/market-research-evidence/SKILL.md)
  and collector/review tooling (see `research/query-packs/`,
  `research/benchmark-experimental/STATUS.json`,
  `research/processed/reproducibility-report.json`). Integrity 1.3 must reject
  rebound sources, modified excerpts, out-of-window timestamps, and incomplete
  pricing before any new live collector run. It may become operational only
  after Pilot 1 and Pilot 2 each pass twice; structural validators and the
  external benchmark alone are insufficient.
- **Ingestion foundation:** domain contracts and adapters unit-tested with
  synthetic data
  ([`src/invoice_ingestion/contracts.py`](../src/invoice_ingestion/contracts.py),
  [`tests/test_invoice_ingestion_contract.py`](../tests/test_invoice_ingestion_contract.py)).
- **Payroll/finance architecture:** parallel non-blocking design; authoritative
  calculations are specialist-gated.

No real invoices, PII, tax calculation, or production activation is permitted
under this plan.

Exit evidence: evidence corpus and capability matrix complete; domain interfaces
and adapters specified and synthetically unit-tested; synthetic review/CSV
prototype demonstrated; no production activation.