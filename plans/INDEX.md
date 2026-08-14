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

| Plan | Status | Milestone | Owner | Lane | Concurrency | Prerequisite | Current Blocker | Expected Result | Acceptance Command |
|---|---|---|---|---|---|---|---|---|---|
| [Plan E — architecture proofs and ADR-001](2026-08-12-plan-e-architecture-proofs-and-adr.md) | active | M1A | product engineering | Critical M0/M1A | Sequential (blocks Release 1A) | Plan L/M checkpoint | L/M checkpoint not accepted | Approved ADR-001, threat model, dependency and rollback evidence | Manual evidence review against Plan E exit gate; automated proof tests must be named when implemented |
| [Plan F — Jan workflow discovery](2026-08-12-plan-f-jan-workflow-discovery.md) | active | M1A | product owner | Critical M0/M1A | Sequential (blocks Release 1A) | Plan L/M checkpoint | None | Approved Release 1A scenarios and traceability matrix | Manual review of decision brief by Jan/operator |
| [Plan G — German market and competitors](2026-08-12-plan-g-german-market-and-competitors.md) | active | M1B/M6 | product owner | Parallel non-blocking research | Parallel | None | None | Verified market and competitor evidence | Manual primary-source and decision review against Plan G exit gate |
| [Plan H — UX, UI, and copy](2026-08-12-plan-h-ux-ui-and-copy-research.md) | active | M1A–M3 | product owner | Critical M0/M1A | Sequential (blocks Release 1A) | Plan L/M checkpoint | None | Tested workflow, localization, and accessibility contract | Manual review of research outputs |
| [Plan J — data protection and legal](2026-08-12-plan-j-data-protection-and-legal.md) | active | M1A–M5 | product owner | Parallel non-blocking research | Parallel | None | None | Activation gate and operational procedures | Manual review of legal compliance checklist |
| [Plan L — operating model](2026-08-12-plan-l-agent-operating-model.md) | active | M0–M1A | primary agent with Pavel approval for publication/destructive actions | Critical M0/M1A | Sequential (foundation) | None | README/documentation checkpoint, CLI contradictions, and experimental-skill activation gate unresolved | Coherent authority, decisions, status, and documentation checkpoint | `venv/bin/python scripts/validate_planning.py` plus manual checkpoint review |
| [Plan AE — repository workflow, dual remotes, and CI automation](2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md) | active | M0 | primary agent | Critical M0/M1A | Sequential (foundation) | None | Clean reviewed baseline and explicit remote-activation approval not yet available | Local exact-path containment first; dual-remote/CI activation remains gated | `venv/bin/python -m pytest tests/test_validate_change_packages.py -q && venv/bin/python scripts/validate_change_packages.py --json` |
| [Plan K — server62 readiness](2026-08-12-plan-k-server62-readiness.md) | active | M0–M5 | server sysadmin; product engineering verifies application requirements | Parallel infrastructure | Parallel (infrastructure lane) | None | Operator/sysadmin recovery and capacity evidence incomplete | Capacity, repaired edge path, monitoring, mandatory recovery proof, rollback, permissions, and TLS evidence | Manual sysadmin evidence review against Plan K acceptance gates |
| [Plan P — payroll and finance architecture](2026-08-12-plan-p-payroll-and-finance-architecture.md) | active | M1B | product engineering + Czech/German payroll specialists | Parallel non-blocking research | Parallel | Plans N/O | Specialist certification absent | Parallel non-blocking research/design; authoritative calculations specialist-gated | Manual specialist review against Plan P exit gate; no implementation acceptance yet |
| [Plan M — visual planning cockpit](2026-08-12-plan-m-visual-planning-cockpit.md) | active | M1A/continuous | product design + engineering | Critical M0/M1A | Sequential (blocks Release 1A) | Plan L governance baseline exists | None | Minimal catalog/validator operational; broader views and repeated-use evidence remain | `venv/bin/python scripts/validate_planning.py` |
| [Plan AC — accounting and invoice automation research](2026-08-13-plan-ac-accounting-automation-research.md) | active | M1B+ | product engineering + Czech/German accounting specialists | Plan AC integrity lane | Parallel (AC integrity lane) | Coordinated with Plans P/N/O/J/H/M | Live capture and skill activation require Integrity 1.3, immutable synthetic replay, and review gates | Evidence basis for invoice processing and accounting workflows | Focused collector/research tests named in Plan AC; live pilot acceptance remains unavailable |
| [Plan AD — invoice ingestion and reviewed export foundation](2026-08-14-plan-ad-invoice-ingestion-foundation.md) | active | M1B | product engineering + Czech/German accounting specialists | Plan AD lane | Parallel non-blocking | Coordinated with Plans M3, N, O, J, H, P, and AC | Persistence/adapters, production implementation, and Plan AD acceptance: DEC-015; public/synthetic in-memory proof is unblocked | Reusable ingestion/review/CSV export boundary; later implementation specialist-gated | `venv/bin/python -m pytest tests/test_invoice_ingestion_contract.py -q` |

## Accepted checkpoint

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan Q — repository history, reference, and privacy remediation](2026-08-12-plan-q-repository-history-reference-privacy.md) | accepted | M0 | Reconciled published checkpoint, remaining inventories, rollback retention, and no implicit remote action |

## Planned after the operating-model checkpoint

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan N — role and data discovery](2026-08-12-plan-n-full-platform-role-and-data-discovery.md) | planned | M1A–M1B | Release 1A catalog first; broader discovery afterward |
| [Plan O — database and transactions](2026-08-12-plan-o-database-and-transaction-architecture.md) | planned | M1A–M1B | Release 1A data architecture and ADR-002 first |

## Blocked operational lane

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan R — A1 production stabilization](2026-08-12-plan-r-a1-production-stabilization.md) | blocked | A1 operations | Operator must add 7 Section 4 columns to the protected CSV; preserve the existing 5/15 package |

## Release 1A lanes

| Lane | Plans |
|---|---|
| **Critical path** | L, M, F, E, N-1A, O-1A, H |
| **Parallel non-blocking** | G, J, K, P, AC, AD, broader N/O |
| **Separate A1 operations** | R |
| **Closed checkpoint** | Q |

## Reviewed handoff

- [Jan Release 1 solution brief](../docs/decisions/2026-08-12-jan-release-1-solution-brief.md): reviewed decision input; the register records decision state.
- [Real-data rules](../docs/security/real-data-rules.md): authoritative policy and sole activation gate.
- [DEC-014](../docs/decisions/decision-register.md): confirmed sanitized checkpoint `c01aa2b` as approved repository baseline, accepted 2026-08-13; acceptance does not authorize GC, ref deletion, or another push.
- [Plan D](2026-08-12-plan-d-product-research-and-deployment.md): superseded and decomposed; retained as reviewed handoff.
- [Plan I](2026-08-12-plan-i-marketing-and-business-validation.md): superseded as a standalone M1 gate; useful later-growth questions remain inputs to M1B/M6.
- [Research review](../docs/research/2026-08-12-research-review-and-plan-update-report.md): accepted disposition, not execution authority.

## Historical context

- [2026-08-11 consolidated roadmap](2026-08-11-consolidated-roadmap.md): historical.
- [Plan B](2026-08-11-plan-b-opencode-cleanup-workflows.md): historical.
- [Plan C](2026-08-11-plan-c-opencode-research.md): historical.
- `docs/paddleocr/`, root research reports, and `CLEANUP_REPORT.md`: historical,
  non-executable sources retained in place pending Plan Q.

Historical records are excluded from active queues and dependency paths.
Acceptance of the sanitized publication checkpoint closes the repository baseline;
archive, delete, rollback-ref, reflog expiry, and garbage collection disposition
remain separately authorized follow-up decisions. PII-bearing outputs are never
moved into a tracked archive.
