# Planning Index

The sole authoritative milestone sequence is [`../roadmap.md`](../roadmap.md).
Agent operation is governed first by [`../AGENTS.md`](../AGENTS.md), with the
documentation checkpoint owned by [Plan L](2026-08-12-plan-l-agent-operating-model.md).
Decisions are indexed in the
[decision register](../docs/decisions/decision-register.md); ADRs live only in
`docs/decisions/` and use `ADR-NNN-short-title.md` names.

## Controlled status vocabulary

Plan headers and this index use exactly: `planned`, `active`, `blocked`,
`awaiting-review`, `accepted`, `completed`, `superseded`, `historical`, or
`archived`. Qualifiers belong in prose, not in the status field.

## Current execution

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan E — architecture proofs and ADR-001](2026-08-12-plan-e-architecture-proofs-and-adr.md) | active | M1A | Approved ADR-001, threat model, dependency and rollback evidence |
| [Plan F — Jan workflow discovery](2026-08-12-plan-f-jan-workflow-discovery.md) | active | M1A | Approved Release 1A scenarios and traceability matrix |
| [Plan G — German market and competitors](2026-08-12-plan-g-german-market-and-competitors.md) | active | M1B/M6 | Verified market and competitor evidence |
| [Plan H — UX, UI, and copy](2026-08-12-plan-h-ux-ui-and-copy-research.md) | active | M1A–M3 | Tested workflow, localization, and accessibility contract |
| [Plan J — data protection and legal](2026-08-12-plan-j-data-protection-and-legal.md) | active | M1A–M5 | Activation gate and operational procedures |
| [Plan L — operating model](2026-08-12-plan-l-agent-operating-model.md) | active | M0–M1A | Coherent authority, decisions, status, and documentation checkpoint |
| [Plan K — server62 readiness](2026-08-12-plan-k-server62-readiness.md) | active | M0–M5 | Capacity, repaired edge path, monitoring, mandatory recovery proof, rollback, permissions, and TLS evidence |
| [Plan Q — repository history, reference, and privacy remediation](2026-08-12-plan-q-repository-history-reference-privacy.md) | active | M0 | Reconciled published checkpoint, remaining inventories, rollback retention, and no implicit remote action |

## Planned after the operating-model checkpoint

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan M — visual planning cockpit](2026-08-12-plan-m-visual-planning-cockpit.md) | planned | M1A/continuous | Derived catalog/views and deterministic validators |
| [Plan N — role and data discovery](2026-08-12-plan-n-full-platform-role-and-data-discovery.md) | planned | M1A–M1B | Release 1A catalog first; broader discovery afterward |
| [Plan O — database and transactions](2026-08-12-plan-o-database-and-transaction-architecture.md) | planned | M1A–M1B | Release 1A data architecture and ADR-002 first |
| [Plan P — payroll and finance architecture](2026-08-12-plan-p-payroll-and-finance-architecture.md) | planned | M1B | Parallel later design and ADR-003; not a 1A gate |
| [Plan R — A1 production stabilization](2026-08-12-plan-r-a1-production-stabilization.md) | planned | A1 operations | Reproducible canonical 11/33 package contract |

## Reviewed handoff

- [Jan Release 1 solution brief](../docs/decisions/2026-08-12-jan-release-1-solution-brief.md): reviewed decision input; the register records decision state.
- [Real-data rules](../docs/security/real-data-rules.md): authoritative policy and sole activation gate.
- [Plan D](2026-08-12-plan-d-product-research-and-deployment.md): superseded and decomposed; retained as reviewed handoff.
- [Plan I](2026-08-12-plan-i-marketing-and-business-validation.md): superseded as a standalone M1 gate; useful later-growth questions remain inputs to M1B/M6.
- [Research review](../docs/research/2026-08-12-research-review-and-plan-update-report.md): accepted disposition, not execution authority.

## Historical context

- [2026-08-11 consolidated roadmap](2026-08-11-consolidated-roadmap.md): historical.
- [Plan B](2026-08-11-plan-b-opencode-cleanup-workflows.md): historical.
- [Plan C](2026-08-11-plan-c-opencode-research.md): historical.
- `docs/paddleocr/`, root research reports, and `CLEANUP_REPORT.md`: historical,
  non-executable sources retained in place pending Plan Q.

Historical records are excluded from active queues and dependency paths. Plan Q
must complete its reference/privacy audit before any move or deletion; PII-bearing
outputs are never moved into a tracked archive.
