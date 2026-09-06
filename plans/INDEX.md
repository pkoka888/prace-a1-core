# Planning Index

The sole authoritative milestone sequence is [`../roadmap.md`](../roadmap.md).
Agent operation is governed first by [`../AGENTS.md`](../AGENTS.md), with the
documentation checkpoint carried by [Plan PLAN-INFRA](PLAN-INFRA.md).
Decisions are indexed in the
[decision register](../docs/decisions/decision-register.md); ADRs live only in
`docs/decisions/` and use `ADR-NNN-short-title.md` names.

## Controlled status vocabulary

Plan headers and this index use exactly: `planned`, `active`, `blocked`,
`awaiting-review`, `accepted`, `completed`, `superseded`, `historical`, or
`archived`. Qualifiers belong in prose, not in the status field.

## Current execution

| Plan | Status | Milestone | Owner | Lane | Current Blocker | Expected Result | Acceptance Command |
|---|---|---|---|---|---|---|---|
| [Plan PLAN-INFRA — architecture, operating model, cockpit, prototype, and infrastructure](PLAN-INFRA.md) | active | M0–M2 | product engineering + primary agent + server sysadmin | Critical Release 1A | ADR-001 validated; server62/GitLab-CI activation evidence incomplete and separately gated | Coherent foundation: validated ADR-001, operating model, planning cockpit, functional prototype, and infrastructure evidence | `venv/bin/python scripts/validate_planning.py`; ADR-001 hash-bound checks; separate approvals for infra/CI mutations |
| [Plan PLAN-WORKERS — worker role, data, UX, and OCR workflows](PLAN-WORKERS.md) | active | M1A–M3 | product owner + product design + product engineering | Critical Release 1A | `ENG-001` blocked: J2/J4 require real storage/OCR/concurrency/artifacts; Jan open questions unresolved | Moves to `awaiting-review` when ENG-001 opens and Jan's open questions are resolved | `ENG-001` implementation_gate: open; `REV-002` human_decision: approved; all checks passed |
| [Plan PLAN-INVOICE — accounting research and invoice ingestion foundation](PLAN-INVOICE.md) | active | M1B+ | product engineering + Czech/German accounting specialists | Parallel non-blocking | DEC-015 specialist sign-off pending; live capture gated by Integrity 1.3 | Provisional evidence corpus; synthetic in-memory ingestion/review/CSV boundary; no accounting behavior | `venv/bin/python -m pytest tests/test_invoice_ingestion_contract.py -q`; DEC-015 before any persistence/adapters |
| [Plan PLAN-LEGAL — data protection, market, and business validation](PLAN-LEGAL.md) | active | M1A–M6 | product owner + legal | Parallel non-blocking | None | Verified market/legal evidence; activation gate and operational procedures | Manual review of legal compliance checklist against real-data-rules |
| [Plan PLAN-A1 — A1 production, repository history, and privacy baseline](PLAN-A1.md) | active | A1 operations | primary A1 production agent | Separate A1 operations | Provisional regeneration blocked (17/17) until operator populates per-row certificate/signatory/review fields | Canonical cohort reproducible from authorized sources; PII never staged | `scripts/a1_quality_gate.py` render+validate; `validated_by_user=1` before final promotion |
| [Plan PLAN-FREE-MODEL — bounded free-model evaluation, trace repair, and capsule isolation](PLAN-FREE-MODEL.md) | active | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | No live run until offline harness, fixtures, containment, and zero-cost preflight are green | Three repeated synthetic receipts per candidate; no model promoted, no skill activated | `venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py -q` |
| [Plan PLAN-REAL-DATA — real-data activation after Sprint 4 gates](PLAN-REAL-DATA.md) | active | M5 | product engineering + product owner + legal + sysadmin | Critical Release 1A | `ENG-001` → `REV-002` → `OPS-001` + `LEG-001` + `INF-001` → Sprint 1–4 → `REV-003` approval; sequential gates required | Prerequisites and evidence defined; explicit operator/legal/sysadmin activation decision deferred | All Sprint 1–4 acceptance criteria green; `REV-003` approved in `planning/approvals.json` |

## Historical

| Plan | Status | Milestone | Successor |
|---|---|---|---|
| [Plan PLAN-HISTORY — archived superseded and historical plans](PLAN-HISTORY.md) | historical | historical | PLAN-INFRA |

## Release 1A lanes

| Lane | Plans |
|---|---|
| **Critical path** | PLAN-INFRA, PLAN-WORKERS, PLAN-REAL-DATA |
| **Parallel non-blocking** | PLAN-LEGAL, PLAN-INVOICE, PLAN-FREE-MODEL |
| **Separate A1 operations** | PLAN-A1 |
| **Historical reference** | PLAN-HISTORY |

## Reviewed handoff

- [Jan Release 1 solution brief](../docs/decisions/2026-08-12-jan-release-1-solution-brief.md): reviewed decision input; the register records decision state.
- [Real-data rules](../docs/security/real-data-rules.md): authoritative policy and sole activation gate.
- [DEC-014](../docs/decisions/decision-register.md): confirmed sanitized checkpoint `c01aa2b` as approved repository baseline, accepted 2026-08-13; acceptance does not authorize GC, ref deletion, or another push.
- [PLAN-HISTORY](PLAN-HISTORY.md): superseded/historical dated plans are archived under `.archive/plans/` and retained as reviewed context; never execution authority.
- [Research review](../docs/research/2026-08-12-research-review-and-plan-update-report.md): accepted disposition, not execution authority.

Historical records are excluded from active queues and dependency paths.
Acceptance of the sanitized publication checkpoint closes the repository baseline;
archive, delete, rollback-ref, reflog expiry, and garbage collection disposition
remain separately authorized follow-up decisions. PII-bearing outputs are never
moved into a tracked archive.