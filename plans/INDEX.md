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
| [Plan E — architecture proofs and ADR-001](2026-08-12-plan-e-architecture-proofs-and-adr.md) | completed | M1A | product engineering | Critical M0/M1A | Synthetic validation complete; production gates remain separate | ADR-001 choices accepted | All 8 checks pass; M2 gate open | Hash-bound eight-check proof and open M2 scaffold gate | `venv/bin/python scripts/run_architecture_proofs.py verify --manifest docs/architecture/adr-001-evidence/manifest.json --json` |
| [Plan F — Jan workflow discovery](2026-08-12-plan-f-jan-workflow-discovery.md) | active | M1A | product owner | Critical M0/M1A | Parallel preparation; Jan review required for exit | Operational Plan L/M baseline (met) | Exception-only Jan/operator validation and synthetic scenario execution remain | Approved Release 1A scenarios and traceability matrix | Manual review of decision brief and scenario pack by Jan/operator |
| [Plan G — German market and competitors](2026-08-12-plan-g-german-market-and-competitors.md) | active | M1B/M6 | product owner | Parallel non-blocking research | Parallel | None | None | Verified market and competitor evidence | Manual primary-source and decision review against Plan G exit gate |
| [Plan H — UX, UI, and copy](2026-08-12-plan-h-ux-ui-and-copy-research.md) | active | M1A–M3 | product owner | Critical M0/M1A | Parallel synthetic design; observed journey test required for exit | Operational Plan L/M baseline (met) | Four critical synthetic journeys are specified but not yet run with Jan/operator | Tested workflow, localization, and accessibility contract | Manual journey observation plus accessibility checks |
| [Plan J — data protection and legal](2026-08-12-plan-j-data-protection-and-legal.md) | active | M1A–M5 | product owner | Parallel non-blocking research | Parallel | None | None | Activation gate and operational procedures | Manual review of legal compliance checklist |
| [Plan L — operating model](2026-08-12-plan-l-agent-operating-model.md) | active | M0–M1A | primary agent with Pavel approval for publication/destructive actions | Critical M0/M1A | Operational baseline available; broader exit continues | None | Does not block Release 1A synthetic work; CLI contradictions, historical-document review, and experimental-skill activation gate remain for Plan L exit | Coherent authority, decisions, status, and documentation checkpoint | `venv/bin/python scripts/validate_planning.py` plus manual checkpoint review |
| [Plan AE — repository workflow, dual remotes, and CI automation](2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md) | active | M0 | primary agent | Critical M0/M1A | Sequential (foundation) | None | Clean reviewed baseline and explicit remote-activation approval not yet available | Local exact-path containment first; dual-remote/CI activation remains gated | `venv/bin/python -m pytest tests/test_validate_change_packages.py -q && venv/bin/python scripts/validate_change_packages.py --json` |
| [Plan AF — bounded Codex-led free-model evaluation](2026-08-15-plan-af-free-model-evaluation.md) | active | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | Parallel | Plan L operating rules | No model promoted; live matrix requires green offline harness and exact zero-cost preflight | Synthetic receipts for trace/review/code-draft suitability; no skill activation | `venv/bin/python -m pytest tests/test_free_model_eval_contracts.py tests/test_free_model_eval_events.py tests/test_free_model_eval_isolation.py tests/test_free_model_eval_preflight.py tests/test_free_model_eval_scoring.py -q` |
| [Plan AF2 — exact-manifest trace repair](2026-08-15-plan-af2-free-model-trace-repair.md) | blocked | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | Sequential within AF2 | Plan AF evidence | Invalid live attempt; AF2.1 evidence-integrity repair required | Historical invalid receipts preserved; no model disposition | `venv/bin/python -m pytest tests/test_free_model_eval_af2_protocol.py -q` |
| [Plan AF2.1 — evidence-integrity repair](2026-08-15-plan-af2.1-evidence-integrity-repair.md) | active | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | Sequential within AF2 | Plan AF2 invalid-run review | Luna control adapter requires AF2.2 capsule isolation before a new immutable run | Valid sanitizer evidence and gated Luna control | `venv/bin/python -m pytest tests/test_free_model_eval_af21_integrity.py -q` |
| [Plan AF2.2 — Luna exact-read adapter and capsule isolation](2026-08-16-plan-af2.2-luna-capsule-isolation.md) | active | M0–M1A | primary agent; Codex integrates and accepts | Parallel tooling evidence | Sequential within AF2 | Plan AF2.1 evidence repair | No live run until adapter, capsule, fixtures, and containment tests are green | Strict `command_execution` read evidence and OS-isolated Luna control | `venv/bin/python -m pytest tests/test_free_model_eval_af21_integrity.py tests/test_free_model_eval_isolation.py -q` |
| [Plan K — server62 readiness](2026-08-12-plan-k-server62-readiness.md) | active | M0–M5 | server sysadmin; product engineering verifies application requirements | Parallel infrastructure | Parallel (infrastructure lane) | None | Operator/sysadmin recovery and capacity evidence incomplete | Capacity, repaired edge path, monitoring, mandatory recovery proof, rollback, permissions, and TLS evidence | Manual sysadmin evidence review against Plan K acceptance gates |
| [Plan P — payroll and finance architecture](2026-08-12-plan-p-payroll-and-finance-architecture.md) | active | M1B | product engineering + Czech/German payroll specialists | Parallel non-blocking research | Parallel | Plans N/O | Specialist certification absent | Parallel non-blocking research/design; authoritative calculations specialist-gated | Manual specialist review against Plan P exit gate; no implementation acceptance yet |
| [Plan M — visual planning cockpit](2026-08-12-plan-m-visual-planning-cockpit.md) | active | M1A/continuous | product design + engineering | Critical M0/M1A | Minimal slice operational; broader work continuous | Plan L governance baseline exists | Does not block Release 1A synthetic work; broader views and repeated-use evidence remain for Plan M exit | Minimal catalog/validator operational; broader views and repeated-use evidence remain | `venv/bin/python scripts/validate_planning.py` |
| [Plan M2 — functional prototype sprint](2026-08-17-plan-m2-functional-prototype-sprint.md) | active | M2 | product engineering + product design | Critical Release 1A | Phase 0 parallel; scaffold gate is sequential | Plan E checks + frozen N-1A + ADR-002/O-1A + Jan phase-1 record | **Gate open (2026-08-17); scaffold location clarified to `portal/release1a/`** | Jan completes J1–J4 on the synthetic vertical slice | Approval/planning validators, Plan E/M2 focused tests, full suite, and manual Jan observation |
| [Plan AC — accounting and invoice automation research](2026-08-13-plan-ac-accounting-automation-research.md) | active | M1B+ | product engineering + Czech/German accounting specialists | Plan AC integrity lane | Parallel (AC integrity lane) | Coordinated with Plans P/N/O/J/H/M | Live capture and skill activation require Integrity 1.3, immutable synthetic replay, and review gates | Evidence basis for invoice processing and accounting workflows | Focused collector/research tests named in Plan AC; live pilot acceptance remains unavailable |
| [Plan AD — invoice ingestion and reviewed export foundation](2026-08-14-plan-ad-invoice-ingestion-foundation.md) | active | M1B | product engineering + Czech/German accounting specialists | Plan AD lane | Parallel non-blocking | Coordinated with Plans M3, N, O, J, H, P, and AC | Persistence/adapters, production implementation, and Plan AD acceptance: DEC-015; public/synthetic in-memory proof is unblocked | Reusable ingestion/review/CSV export boundary; later implementation specialist-gated | `venv/bin/python -m pytest tests/test_invoice_ingestion_contract.py -q` |

## Accepted checkpoint

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan Q — repository history, reference, and privacy remediation](2026-08-12-plan-q-repository-history-reference-privacy.md) | accepted | M0 | Reconciled published checkpoint, remaining inventories, rollback retention, and no implicit remote action |

## Active Release 1A role/data design

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan N — role and data discovery](2026-08-12-plan-n-full-platform-role-and-data-discovery.md) | active | M1A–M1B | Release 1A catalog work proceeds; Jan operational validation remains an acceptance gate |
| [Plan O — database and transactions](2026-08-12-plan-o-database-and-transaction-architecture.md) | active | M1A–M1B | Release 1A logical design proceeds; ADR-002 still requires Plan N/Plan E evidence |

## Blocked operational lane

| Plan | Status | Milestone | Exit result |
|---|---|---|---|
| [Plan R — A1 production stabilization](2026-08-12-plan-r-a1-production-stabilization.md) | **completed** | A1 operations | **R-01/R-02/R-03 done 2026-08-20**: 7 Section 4 cols added, 2 people added, doc_ids → `/2026/`. Canonical: 11 PDFs, 33 previews, QA passed. Visual review & backup cleanup pending.

## Release 1A lanes

| Lane | Plans |
|---|---|
| **Critical path** | E, F/H phase 1, N-1A, O-1A/ADR-002, M2 prototype sprint, Jan J1–J4 |
| **Parallel non-blocking** | G, J, K, P, AC, AD, AF, broader N/O |
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
