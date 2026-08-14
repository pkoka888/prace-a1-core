# Plan P — Czech/German Payroll and Operational Finance Architecture

**Status:** active
**Prerequisite:** Coordinated with Plans N/O. Research and synthetic design proceed
now; ADR-003 acceptance requires the relevant N/O catalog.
**Milestone:** M1B design; later certified implementation
**Owner:** product engineering + Czech/German payroll specialists
**Lane:** Parallel non-blocking M1B research/design; payroll implementation and
authoritative calculations specialist-gated

## Objective

Design Czech and German payroll engines and the operational commercial subledger
in parallel with Release 1A. This plan and ADR-003 do not gate Release 1A
scaffolding, and neither jurisdiction activates without specialist certification
and official test evidence.

## Work

- Separate jurisdiction-neutral payroll orchestration from effective-dated Czech
  and German rule packs, filings, identifiers, authority responses, and corrections.
- Model payroll period, approved input snapshot, rule-set version/source, component
  calculation, run/result, payslip, correction/recalculation, approval/finalization,
  filing payload, acknowledgement, and reconciliation.
- Design attendance/time, contract, compensation, absence, expense, and assignment
  inputs with explicit approval and source provenance.
- Model planned/actual rates, revenue, costs, invoice references/status, payment
  events, currencies, tax metadata, and exports as an operational subledger—not
  general double-entry accounting.
- Research current official Czech/German rules and electronic interfaces; obtain
  specialist-owned golden cases and sign-off for each activated rule version.
- Specify immutable results, retroactive changes, parallel/correction runs,
  rounding, period locks, audit, access segregation, integration failure, and
  jurisdiction-specific rollout/rollback in ADR-003.

## Exit

The full data/interface/test design is approved before scaffold. Each jurisdiction
has versioned source evidence and specialist-certified golden cases before its
engine becomes authoritative. Jan Release 1A can deploy while payroll remains
designed but inactive.
