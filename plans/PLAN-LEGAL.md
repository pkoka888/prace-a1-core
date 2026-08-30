# Plan PLAN-LEGAL — Data Protection, Legal, Market, and Business Validation

**Status**: active
**Milestone**: M1A–M6

## Purpose

Single governing plan for the legal, data-protection, market, and business
validation context that bounds the portal and its real-data activation: German
market and competitor research, data protection and legal requirements, and
later marketing/business validation.

Replaces and consolidates the dated plans:

- `plans/2026-08-12-plan-g-german-market-and-competitors.md`
- `plans/2026-08-12-plan-j-data-protection-and-legal.md`
- `plans/2026-08-12-plan-i-marketing-and-business-validation.md`

The archive of the individual dated plans lives under `.archive/plans/`; the
tracked source of truth is this file plus [`plans/INDEX.md`](INDEX.md).

## Status and governance

- Status: `active` — legal/market research proceeds in parallel and does not
  block Release 1A synthetic work.
- Decision state: `prototype-required`.
- Evidence: `primary-source-verified` (market/competitor and legal research come
  from reviewed primary sources).

## Dependencies (catalog-recorded)

- `PLAN-INFRA` with gate `evidence-only` — the operating model and architecture
  baseline bounds legal/data-protection design.
- `PLAN-WORKERS` with gate `evidence-only` — role/data discovery and UX research
  inform the legal user-facing text and processing boundaries.

## Contents and exit evidence

- **Market and competitors:** verified market and competitor evidence; inputs to
  later growth (M1B/M6), never implementation authority.
- **Data protection and legal:** activation gate and operational procedures per
  [`docs/security/real-data-rules.md`](../docs/security/real-data-rules.md) and
  the [decision register](../docs/decisions/decision-register.md).
- **Business validation:** later-growth questions documented as inputs to M1B/M6.

Exit evidence: verified market evidence, legal compliance checklist, and an
activation gate with operational procedures; real-data activation remains
gated by DEC-011/DEC-012/real-data-rules before the M5 pilot.