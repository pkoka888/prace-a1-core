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
| [Plan PLAN-WORKERS — worker role, data, UX, and OCR workflows](PLAN-WORKERS.md) | active | M1A–M3 | product owner + product design + product engineering | Critical Release 1A | `ENG-001` blocked: J2/J4 require real storage/OCR/concurrency/artifacts; Jan open questions unresolved; shared local/web document intake implemented for synthetic acceptance; remaining ENG/M3 gates pending | Moves to `awaiting-review` when ENG-001 opens and Jan's open questions are resolved | `ENG-001` implementation_gate: open; `REV-002` human_decision: approved; all checks passed |
| [2026-09-06-OCR-SHARED-CORE-LOCAL](2026-09-06-ocr-shared-core-local-web.md) | active | M3 | product engineering | Critical Release 1A (subordinate to PLAN-WORKERS) | None | Task OCR-CORE-1 through OCR-CORE-14 acceptance tests pass | Offline real OCR + document semantics; CLI/web parity; protected OcrRun derivatives; PostgreSQL concurrency and historical migration tests; broader M3 acceptance pending |
| [Plan PLAN-INVOICE — accounting research and invoice ingestion foundation](PLAN-INVOICE.md) | active | M1B+ | product engineering + Czech/German accounting specialists | Parallel non-blocking | DEC-015 specialist sign-off pending; live capture gated by Integrity 1.3 | Provisional evidence corpus; synthetic in-memory ingestion/review/CSV boundary; no accounting behavior | `venv/bin/python -m pytest tests/test_invoice_ingestion_contract.py -q`; DEC-015 before any persistence/adapters |
| [Plan PLAN-LEGAL — data protection, market, and business validation](PLAN-LEGAL.md) | active | M1A–M6 | product owner + legal | Parallel non-blocking | None | Verified market/legal evidence; activation gate and operational procedures | Manual review of legal compliance checklist against real-data-rules |
| [Plan PLAN-A1 — A1 production, repository history, and privacy baseline](PLAN-A1.md) | active | A1 operations | primary A1 production agent | Separate A1 operations | Provisional regeneration blocked (25/25) — 2026-09-06 investigation: 0/25 AUTHORITATIVE source statuses; historical hash equality; current 26 provisional/25 final files; employee support implemented; authoritative evidence and receipt-bound promotion unresolved | Canonical cohort reproducible from authorized sources; PII never staged | `scripts/a1_quality_gate.py` render+validate; `validated_by_user=1` before final promotion |
| [2026-09-06-A1-EVIDENCE-STATUS-REPAIR](2026-09-06-a1-evidence-status-repair.md) | active | A1 operations | primary A1 production agent | Separate A1 operations (subordinate to PLAN-A1) | Bounded stabilization synthetic-accepted; authoritative reconciliation and promotion pending | A1-REPAIR-1 through A1-REPAIR-7 acceptance criteria met after repair and evidence reconciliation | Placeholder profiles rejected; canonical provisional restrictions enforced including validated_by_user; application vs certificate readiness distinct; cohort provenance uses opaque references; final artifact dependency-bound manifest |
| [Plan PLAN-FREE-MODEL — bounded free-model evaluation, trace repair, and capsule isolation](PLAN-FREE-MODEL.md) | active | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | No live run until offline harness, fixtures, containment, and zero-cost preflight are green | Three repeated synthetic receipts per candidate; no model promoted, no skill activated | `venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py -q` |
| [2026-09-06-FREE-VISION-PROVIDER-SAFETY](2026-09-06-free-vision-provider-safety.md) | planned | M1A–M2 | primary agent; Codex integrates and accepts | Parallel tooling evidence (subordinate to PLAN-FREE-MODEL) | None | FREE-VISION-1 through FREE-VISION-8 acceptance tests pass; zero-cost verified; AF2 lane separate | No paid endpoints; exact endpoint/model required; unknown pricing prohibits dispatch; AF2 and vision share quota where upstream limits shared; independent pool attempts within budget |
| [Plan PLAN-WORKERS-MIGRATE-TO-DB — worker data from JSON/CSV to database](PLAN-WORKERS-MIGRATE-TO-DB.md) | planned | M2–M5 | product engineering + primary agent | Critical Release 1A (subordinate to PLAN-WORKERS) | ENG-001 opens, observed Release 1A acceptance, JSON/CSV freeze plan approved | Single dashboard write path; CSV/JSON frozen for archive; CI gate blocks scripts reading legacy files | DB-MIG-1 through DB-MIG-7 acceptance commands; DB-MIG-7 byte-equality round-trip on synthetic data |
| [Plan PLAN-REAL-DATA — real-data activation after Sprint 4 gates](PLAN-REAL-DATA.md) | active | M5 | product engineering + product owner + legal + sysadmin | Critical Release 1A | Sprint 1–3 → `ENG-001` → `REV-002` → Sprint 4 → `OPS-001`/`LEG-001`/`INF-001` → `REV-003`; Sprint 4 follows REV-002, not ENG-001 | Prerequisites and evidence defined; explicit operator/legal/sysadmin activation decision deferred | All Sprint 1–4 acceptance criteria green; `REV-003` approved in `planning/approvals.json` |

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
Session review and ordered next work: [2026-09-06 architect review](../docs/research/2026-09-06-a1-session-architect-review.md). Child task IDs and 34 top-level catalog entries are preserved.

2026-09-07: [Codex A1 engineering delivery](../docs/research/2026-09-06-a1-engineering-delivery.md) and [bounded OpenCode work orders](../docs/operations/opencode-work-orders/README.md).

## Stabilization acceptance checkpoint — 2026-09-07

PLAN-A1 and PLAN-INFRA remain active. Initial focused acceptance failed (5 failed,
33 passed); bounded repairs now pass 157 tests/19 subtests, document core 75.
Next J4 engineering can begin under sequential file ownership; promotion and
activation remain gated. Implementation evidence, synthetic acceptance and deployment are
recorded separately. See [roadmap](../roadmap.md) and the
[operator workflow contract](../docs/architecture/operator-a1-workflow.md).

Infrastructure checkpoint 2026-09-07: [application review](../docs/research/2026-09-07-infra-application-review.md) and [return work order](../docs/operations/infra-return-work-order-2026-09-07.md); implementation, acceptance and deployment tracked separately under PLAN-INFRA. No new top-level plan or gate approval.

Runtime/J4 checkpoint: [engineering delivery](../docs/research/2026-09-07-runtime-j4-engineering.md). New migration0011 and artifact tests are not deployment evidence or ENG-001 approval. Existing task IDs remain authoritative.
