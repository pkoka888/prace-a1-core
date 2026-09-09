# OpenCode work orders — 2026-09-06/07

This packet is the user's requested handoff after Codex's A1 engineering patch.
Use the existing repository and task IDs. Do not restart document intake, introduce
another parser/generator, or treat a research report as execution authority.

## Start each run

Read `AGENTS.md`, `docs/security/real-data-rules.md`, `roadmap.md`, `plans/INDEX.md`,
the assigned parent/child plan, and the relevant skill. Inspect scoped working-tree
changes before editing. Read the [Codex delivery report](../../research/2026-09-06-a1-engineering-delivery.md).
There are substantial uncommitted/untracked changes from multiple sessions. Preserve
them. No task authorizes staging, commit, push, deployment, activating real data,
editing approval decisions, changing host services, or deleting/moving private files.

Select one work order below. Read scope is limited to the listed source/test/docs
paths plus imports needed from the same approved source namespaces. Never read or
search `.env`, `secrets/`, `a1/`, `scans/`, `ocr/`, `evidence/`, `data/`, `employees/`,
`output/`, `runtime/`, `.history-remediation/`, `research/acquisition/`,
`research/pilot/`, `research/processed/`, `research/benchmark-experimental/`,
attachments or `/tmp` incident
scripts. These restrictions include grep, recursive inventory, tool output, browser
uploads and automatic context collection. Use generated fictional fixtures only.
This is an operating contract, not an OS sandbox; an orchestrator must enforce tool
permissions/capsules before delegating to remotely hosted models.

## Provider selection

- Default to an existing verified-free exact endpoint/model pair. OpenRouter IDs
  must end exactly in `:free`; provider-level free tiers do not admit paid models.
- Fresh zero-price metadata and quota reservation are required before free dispatch;
  unknown/stale pricing blocks dispatch. On quota exhaustion, at most two independent
  eligible pools may be attempted; otherwise defer. No paid fallback.
- The user explicitly permits direct MiniMax **m3 / m2.7** for these OpenCode tasks.
  Use only the user's existing configured endpoint/model IDs and entitlement. This
  exception is specific to these named models; it does not authorize enabling billing,
  purchasing credits, choosing other paid models, or bypassing a configured spend cap.
  Do not guess API identifiers or claim these models are free. If entitlement/cost
  controls cannot be established, use the verified-free/local path and report the gap.
- Use a capable model (including the permitted MiniMax option) for J4/receipt code;
  bounded free-model runs suit tests, documentation and read-only inventory. Confirm
  actual capability with synthetic fixtures, not brand/model-name assumptions.
- No provider call was performed by Codex for this handoff. Do not read keys into
  prompts/logs; let the already-configured provider integration handle credentials.
  Never send real identity data, full documents or generated employee PDFs to models.

## Scheduling and write ownership

Only one writer owns a file at a time. Run inventory and independent review in
parallel with implementation; run J4 and A1 receipt writers sequentially where they
share models/services/views or canonical A1 code. Every task starts with a scoped
diff and ends with a changed-path list. Before a new worker starts, the integrator
checks that the preceding worker has released those paths.

| Order | Work order | Parent/task mapping | Role |
|---|---|---|---|
| 1 | [Independent regression review](review-and-tests.md) | A1-REPAIR-1/2/5/7; OCR-CORE-13/14; ENG-MIGRATION | Review first, tests only unless integrator assigns a fix |
| after stabilization acceptance | [Artifact acceptance and J4](artifact-and-j4.md) | A1-REPAIR-3/5/6; ENG-J4-SNAPSHOT/PREVIEW/STATE | Bounded implementation, sequential ownership |
| parallel | [Repository organization audit](organization-audit.md) | PLAN-INFRA / PLAN-HISTORY | Read-only analysis; no moves/deletions |
| after stabilization fixes | [Release integration audit](release-audit.md) | ENG-001 prerequisites / PLAN-INFRA | Test, audit, exact publication inventory |
| deferred extension | [Free-provider safety](provider-safety.md) | FREE-VISION-1 through 8 | Offline policy/adapter implementation first |

Human evidence reconciliation is **primary/operator-only**: employer evidence,
identity conflict acceptance, institution codes, certificate/signatory sources,
cohort reconciliation, and containment of the previously reported `/tmp` incident.
Give the primary agent missing field names and opaque task references; never request
private files in a remote model session. These items cannot be completed by changing
YES flags, waiting one day, choosing OP1 by default, or copying another PDF.

## Required report from every agent

Write a sanitized report in `docs/research/opencode-<work-order>-2026-09-06.md`:

1. Parent task/check IDs; objective and exact write scope.
2. Starting HEAD and dirty/untracked scope (source paths only).
3. Verified before/after behavior, citing source functions and lines.
4. Exact tests run, exit codes, passed/failed/skipped counts, environment and limits.
5. Negative tests and failure/recovery behavior; mocks versus real engine/DB evidence.
6. Changed paths, migration dependencies, rollback approach, unresolved risks.
7. Proposed plan-status changes, with evidence; no self-awarded human approval.
8. Provider/model, purpose, date, free eligibility or MiniMax entitlement reference;
   cost as actually observed or unknown, never fabricated zero.

A successful structural validator is not functional acceptance. A working-tree test
is not proof of a complete commit. Report blocked work specifically and continue
independent authorized tasks; do not repeatedly request approval for ordinary edits.

## Current stabilization priority — 2026-09-07

Initial focused acceptance failed: 5 failed, 33 passed. Codex integrated runtime
repairs in canonical A1, audit/path and QA helpers. OpenCode test writers receive explicit
file ownership from the integrator; read-only reviewers may run in parallel.
Bounded stabilization is now synthetic-accepted (157 focused tests/19 subtests;
75 document-core tests). J4/promotion engineering can begin with integrator-assigned
sequential ownership; actual promotion, service changes and activation remain gated.
Provider implementation remains deferred.
The numbered scopes in later work orders are bounded assignments, not concurrent
write authorization. Existing migration files must be delivered together with
models and dependent code when publication is separately authorized; no service
migration is authorized by their presence or by a test database result.

Report three independent states: implementation, synthetic acceptance, deployment.
Record exact commands, counts, tested paths and limitations. Do not repeat historical
counts as current acceptance. Preserve the 34 top-level catalog IDs and child tasks.
Jan's later interface follows the [operator contract](../../architecture/operator-a1-workflow.md):
automatic technical routing, missing/conflicting facts and one consolidated
confirmation; application preparation and official issuance remain distinct.

Current acceptance evidence: [stabilization report](../../research/2026-09-07-a1-stabilization.md).
The release-verifier unit tests now mock live harness boundaries and exercise actual
main exit-code logic, avoiding recursive PostgreSQL resets; isolated integration
harness results are separate evidence. Never turn unit tests into service diagnostics.

Final isolated-storage/cache verification: PostgreSQL intake 15 passed; affected M2
33 passed; no model/migration drift. This proves synthetic test state only.

## Infrastructure follow-up — 2026-09-07

Read the [application review](../../research/2026-09-07-infra-application-review.md)
and [return contract](../infra-return-work-order-2026-09-07.md). Next bounded source
work is confined supervised settings with dummy-value configuration tests, followed
by storage/model/release timeout preflight and minimum J4. Assign exact file ownership
before implementation. Current optional engine experiments do not authorize changing
intake defaults. Do not invoke live release_verifier against its persistent database;
use isolated test harnesses. Host provisioning, service identity, SOPS consumption,
proxy/logging and coherent restore remain infrastructure-owned, separately authorized.

## Runtime/J4 implementation checkpoint — 2026-09-07

[Engineering delivery](../../research/2026-09-07-runtime-j4-engineering.md) supersedes
the prior next-source-repair list. Next independent review: confined settings and
subprocess cleanup, canonical artifact attachment, source dependency checks,
protected delivery and historical0010→0011 migration evidence. Reconcile every
ENG-001 check separately; do not infer gate opening from J4 or test counts.
Remaining product work is the evidence/visual-review interface. Host deployment
remains separately authorized. No organization audit moves or private research
inspection are added to agent scope.
