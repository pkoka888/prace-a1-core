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
| [Plan PLAN-INFRA — architecture, operating model and infrastructure](PLAN-INFRA.md) | active | M0–M2 | engineering + primary + sysadmin | Critical Release 1A | Nginx access repaired; desired-state reconciliation, readiness503/build selection and core PG/restart acceptance open; clean bootstrap remains unproven | Truthful evidence, proportional validation, usable testing site | Child reliability plan REL-01–06/JAN-04; targeted checks and one candidate acceptance |
| [Plan PLAN-WORKERS — worker, document/OCR and assignment workflows](PLAN-WORKERS.md) | active | M1A–M3 | product owner + engineering | Critical Release 1A | Core sparse/export/restart coverage still incomplete; intended-route and Jan acceptance open | Jan core workflow; optional A1 excluded from required acceptance | Core browser + role/tenant + missing-data/correction checks; observed acceptance separate |
| [2026-09-06-OCR-SHARED-CORE-LOCAL](2026-09-06-ocr-shared-core-local-web.md) | active | M3 | product engineering | Critical Release 1A (subordinate to PLAN-WORKERS) | Calibration, stage recovery and observed web acceptance remain open; LangGraph comparison optional | Preserve local OCR and human review; measure OCR-CORE-10/11/13/14 follow-up before orchestration adoption | Offline real OCR + document semantics; CLI/web parity; protected OcrRun derivatives; PostgreSQL concurrency and historical migration tests; broader M3 acceptance pending |
| [Plan PLAN-INVOICE — accounting research and invoice ingestion foundation](PLAN-INVOICE.md) | active | M1B+ | product engineering + Czech/German accounting specialists | Parallel non-blocking | DEC-015 specialist sign-off pending; live capture gated by Integrity 1.3 | Provisional evidence corpus; synthetic in-memory ingestion/review/CSV boundary; no accounting behavior | `venv/bin/python -m pytest tests/test_invoice_ingestion_contract.py -q`; DEC-015 before any persistence/adapters |
| [Plan PLAN-LEGAL — data protection, market, and business validation](PLAN-LEGAL.md) | active | M1A–M6 | product owner + legal | Parallel non-blocking | None | Verified market/legal evidence; activation gate and operational procedures | Manual review of legal compliance checklist against real-data-rules |
| [Plan PLAN-A1 — A1 production, repository history, and privacy baseline](PLAN-A1.md) | active | A1 operations | primary A1 production agent | Separate A1 operations | Authoritative-input reconciliation and receipt-bound promotion unresolved; canonical employee support implemented; current scoped input/artifact evidence in PLAN-A1 and the delivery record; historical counts do not define the live cohort | Canonical cohort reproducible from authorized sources; PII never staged | `scripts/a1_quality_gate.py` render+validate; `validated_by_user=1` before final promotion |
| 2026-09-06-A1-EVIDENCE-STATUS-REPAIR (unpublished local material: `plans/2026-09-06-a1-evidence-status-repair.md`) | active | A1 operations | primary A1 production agent | Separate A1 operations (subordinate to PLAN-A1) | Bounded stabilization synthetic-accepted; authoritative reconciliation and promotion pending | A1-REPAIR-1 through A1-REPAIR-7 acceptance criteria met after repair and evidence reconciliation | Placeholder profiles rejected; canonical provisional restrictions enforced including validated_by_user; application vs certificate readiness distinct; cohort provenance uses opaque references; final artifact dependency-bound manifest |
| [Plan PLAN-FREE-MODEL — bounded free-model evaluation, trace repair, and capsule isolation](PLAN-FREE-MODEL.md) | active | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | No live run until offline harness, fixtures, containment, and zero-cost preflight are green | Three repeated synthetic receipts per candidate; no model promoted, no skill activated | `venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py -q` |
| 2026-09-06-FREE-VISION-PROVIDER-SAFETY (unpublished local material: `plans/2026-09-06-free-vision-provider-safety.md`) | planned | M1A–M2 | primary agent; Codex integrates and accepts | Parallel tooling evidence (subordinate to PLAN-FREE-MODEL) | None | FREE-VISION-1 through FREE-VISION-8 acceptance tests pass; zero-cost verified; AF2 lane separate | No paid endpoints; exact endpoint/model required; unknown pricing prohibits dispatch; AF2 and vision share quota where upstream limits shared; independent pool attempts within budget |
| [Plan PLAN-WORKERS-MIGRATE-TO-DB — worker data from JSON/CSV to database](PLAN-WORKERS-MIGRATE-TO-DB.md) | planned | M2–M5 | engineering + primary | Core persistence now; legacy/A1 cutover separate | JAN-04 current PostgreSQL acceptance open; accepted legacy cutover separately gated | Durable core records; DB-MIG IDs retained without making PDF equivalence a core-v1 prerequisite | JAN-04 for core; scoped DB-MIG-1–7 for legacy/A1 cutover |
| [Plan PLAN-REAL-DATA — scoped real-data activation](PLAN-REAL-DATA.md) | active | M5 | engineering + product owner + legal + sysadmin | Restricted pilot | JAN-03 scope reconciliation; OPS-001/LEG-001/INF-001 and REV-003 evidence/decisions remain scoped and unapproved by this checkpoint | Authorized protected core workflow, no official-PDF prerequisite | Existing §14 activation evidence plus scoped core acceptance |
| [PostgreSQL infrastructure request](../docs/operations/servers-infra-core-postgresql-request.md) | request — awaiting infrastructure response | M0–M2 | servers-infra-core | Critical Release 1A | Application team has issued v1.0 request; awaiting infrastructure response with contract values. 2026-09-15: next action is inspection/reconciliation of existing infrastructure, not new provisioning; see the [sysadmin reconciliation report](../docs/operations/sysadmin-postgresql-reconciliation-2026-09-15.md) | Private PostgreSQL target with credentials, backup/restore and documented owner; response alone does not close JAN-04 | Infrastructure response YAML; application validates compatibility, repairs pending defects and runs acceptance |

## Current bounded batch — 2026-09-14

[Delivery reliability and Jan core v1](2026-09-14-delivery-reliability-and-jan-v1.md)
is active under PLAN-INFRA and PLAN-WORKERS. REL-01–06 repair consolidation,
evidence binding, selection/CI ownership and recurring workflow gaps; JAN-01–04
deliver normal login, core worker/document/OCR/assignment use and PostgreSQL
persistence. PILOT-01 is separately gated. Parallel file ownership and acceptance
commands are in the child plan; these are child tasks, not new top-level catalog IDs.

**2026-09-16 follow-up:** `b687abe` integrates the missing shell dependency;
review at `4a38067` identifies partial unstaged PG repairs and a new cleanup-env
regression. The dependency report establishes installed compatibility, not clean
bootstrap. Preserve prior failure receipts and repair PG ownership/forwarding, then
browser readiness/core separation and committed-source acceptance. The
[document orchestration review](../docs/research/2026-09-16-document-orchestration-review.md)
records fresh offline OCR/worker tests and optional LangGraph use cases; bounded
comparison belongs to existing OCR-CORE-10/11/13/14 and is not a v1 dependency.
Infrastructure reconciliation proceeds independently. Details and validation criteria live in
that plan; publication lives in the delivery record. No new catalog ID or approval.

[Local automation](2026-09-08-local-a1-automation.md) remains a retained
implementation/optional-A1 contract. Official A1 generation/issuance is outside v1;
drafts are optional. Weekly budget remains unresolved. Current host acceptance is
unverified at this checkpoint. JAN-03 reconciles machine/UI gate scope; historical
human approvals and the shared §14 activation controls are not rewritten.

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
Session review and ordered next work: 2026-09-06 architect review (unpublished local material: `docs/research/2026-09-06-a1-session-architect-review.md`). Child task IDs and 34 top-level catalog entries are preserved.

2026-09-07: Codex A1 engineering delivery (unpublished local material: `docs/research/2026-09-06-a1-engineering-delivery.md`) and bounded OpenCode work orders (unpublished local material: `docs/operations/opencode-work-orders/README.md`).

## Stabilization acceptance checkpoint — 2026-09-07

Historical checkpoint; current implemented components and next acceptance work
are described above and in the [delivery record](../docs/operations/git-delivery.md).
The current batch's PostgreSQL target acceptance is gated on the infrastructure
response; see the [infrastructure request](../docs/operations/servers-infra-core-postgresql-request.md)
and the active child plan.

PLAN-A1 and PLAN-INFRA remain active. Initial focused acceptance failed (5 failed,
33 passed); bounded repairs now pass 157 tests/19 subtests, document core 75.
Next J4 engineering can begin under sequential file ownership; promotion and
activation remain gated. Implementation evidence, synthetic acceptance and deployment are
recorded separately. See [roadmap](../roadmap.md) and the
operator workflow contract (unpublished local material: `docs/architecture/operator-a1-workflow.md`).

Infrastructure checkpoint 2026-09-07: application review (unpublished local material: `docs/research/2026-09-07-infra-application-review.md`) and return work order (unpublished local material: `docs/operations/infra-return-work-order-2026-09-07.md`); implementation, acceptance and deployment tracked separately under PLAN-INFRA. No new top-level plan or gate approval.

Runtime/J4 checkpoint: engineering delivery (unpublished local material: `docs/research/2026-09-07-runtime-j4-engineering.md`). New migration0011 and artifact tests are not deployment evidence or ENG-001 approval. Existing task IDs remain authoritative.

## Agent/fleet verification checkpoint — 2026-09-16

The [independent review](../docs/operations/2026-09-16-agent-ops-review.md) and
[existing child-plan TODOs](2026-09-14-delivery-reliability-and-jan-v1.md#independent-agentfleet-review-and-todos--2026-09-16)
separate current host/site observations, protected-export repair, offline
Ansible coverage and an optional local LangGraph demonstration. PLAN-INFRA and
REL-02–06 retain ownership; JAN-01–04 and PG5 acceptance remain separate.
No new top-level task, fleet inventory, production authority or v1 prerequisite.
