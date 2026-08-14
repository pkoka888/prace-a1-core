# Product Roadmap — Jan Pilot to Recruitment Platform

**Status:** Authoritative
**Date:** 2026-08-12
**Current stage:** M0 repository organization and M1 discovery/architecture proofs

This is the sole authoritative execution roadmap. Dated files under `plans/` define bounded work; older roadmaps remain historical context only.

## Product objective

Design one coherent Czech/German recruitment and workforce platform, including
partner operations, planning, attendance, A1, payroll, and operational finance.
Deliver it incrementally: Jan's document → worker → assignment → A1 workflow is
the first usable increment and must not wait for later module activation.

## Now / Parallel / Gated

| Category | Work |
|---|---|
| **Now** | Stabilize and classify the mixed worktree; finish the Plan L operating-model and minimal Plan M planning checkpoint. |
| **Next on Release 1A** | Complete F/E/H, freeze the Release 1A slices of N/O, then present ADR-001/002 for acceptance. |
| **Parallel** | Plan K infrastructure work; G/J/P research; Plan AC offline Integrity 1.3 repair; Plan AD public/synthetic contract design. |
| **Gated** | N/O implementation waits for the L/M checkpoint; Plan R waits for seven protected CSV columns; AD persistence/adapters, production implementation, and Plan AD acceptance wait for DEC-015; portal scaffolding waits for M1A; GitLab activation, deployment, real data, publication, and destructive history work require their explicit gates. |

## Delivery increments

- **Release 1A — Jan operational core:** shared identity/organization foundation,
  documents/OCR, workers, assignments, A1, audit, and protected access.
- **Release 1B — connected operations:** partner and worker access, jobs,
  applications/reservations, schedules, attendance/time, and communications.
- **Release 1C — certified administration:** independently activated Czech and
  German payroll plus operational finance/accounting integrations.
- **Release 2 — public growth:** public recruitment, feeds, marketing, and broader
  partner self-service after evidence and terms validation.

## M0 — Organize a coherent foundation

- Keep durable project files under the project root and distinguish tracked source
   from gitignored real-data/runtime directories.
- Reconcile `A1_PRIVATE_DIR` with protected inputs and verify canonical commands.
- Keep governance, A1, portal, runtime-data, infrastructure, and history changes
   independently reviewable.
- Execute Plan K's capacity, edge-path, monitoring, and recovery gates. Synthetic
   work continues in parallel; activation requires tested backup and restore.
- Complete Plan L's operating-model and validation checkpoint.
- Execute Plan AE's repository workflow, dual remotes, and CI automation.

**Exit:** the sanitized checkpoint is accepted; private inputs have one truthful
location; ownership and implementation paths are unambiguous. Recovery-ref cleanup
remains separately authorized.

## M1A — Release 1A implementation readiness

- Complete Plan L and the minimal Plan M catalog, validator, and visual shell.
- Complete Plans E, F, and H, including accepted workflows, threat model,
  localization/accessibility contract, and traceability.
- Freeze the Release 1A role/data catalog and database/transaction slices of N/O.
- Prove MFA, organization authorization, jobs, protected downloads, audit events,
  and the A1 package boundary; accept ADR-001 and ADR-002.
- Maintain an illustrated decision brief with researched defaults and meaningful
  variants; ask Jan/operator to approve operational facts research cannot settle.
- Keep `docs/security/real-data-rules.md` as the sole activation gate for new
  real-data portal use; unresolved counsel questions do not block synthetic work.

Research, diagrams, catalogs, wireframes, logical schemas, query design, and
synthetic proofs may proceed concurrently. Dependencies gate acceptance or
implementation where stated; they do not block safe discovery work.

**Exit:** accepted operating model and planning shell; approved Release 1A catalog;
ADR-001/002; synthetic journeys, security/data-flow tests, traceability, and an
implementation-ready backlog.

## M1B — Broader platform design

- Continue broader Plans N/O and complete Plan P/ADR-003 in parallel.
- Continue market research and later-role prototypes without delaying Release 1A.
- Keep payroll inactive until independently specialist-certified.

**Exit:** later roles, modules, interfaces, payroll/finance architecture, and
market evidence are ready for separately gated increments.

## M2 — Build the shared synthetic foundation

- Scaffold the accepted Django architecture, PostgreSQL schema, templates/HTMX UI,
  localization, organization memberships, audit foundation, protected-storage
  interface, and background jobs.
- Deploy development/staging with synthetic fixtures only.

**Exit:** mandatory TOTP, tenant isolation, deployment checks, and core synthetic
workflows pass.

## M3 — Employee, document, OCR, and assignment workflow

- Implement worker records, document quarantine, local OCR proposals, human
  review, workplaces, assignments, current-placement calculation, missing-data
  tasks, and operator oversight.

**Exit:** Jan and operator complete accepted synthetic journeys without scripts or
direct filesystem handling.

## M4 — A1 preparation

- Integrate the existing fail-closed A1 engine as an internal package.
- Create A1 cases from reviewed worker and assignment data; expose validation,
  generation, preview, review, artifacts, and status history.
- Preserve the distinction between prepared applications and official certificates.

**Exit:** accepted synthetic profiles pass deterministic generation and all
failure/approval states.

## M5 — Controlled real-data pilot

- Pass the activation gate, migrate only approved legacy data, and complete
  Jan/operator onboarding, incident procedures, and training.
- Produce an encrypted application-consistent backup, pass integrity checks, and
  complete an isolated application-level restore before any new real-data upload.
- Enable real documents only after explicit operator approval.

**Exit:** explicitly approved real-data workflows are protected and auditable.

## M6 — Later releases and public growth

- Activate partner/worker access, recruitment, planning, attendance/time, and
  communications through separately tested vertical increments.
- Activate Czech and German payroll independently only after specialist-certified
  versioned rules and golden tests; connect the operational subledger to formal
  accounting rather than implementing general accounting.
- Validate business positioning, channels, public UX, integrations, and terms
  before public growth work; select a separate frontend only if evidence warrants it.

**Exit:** every increment has approved requirements, evidence, rollout, and rollback.

## Plan sequence

- **Critical M0/M1A:** worktree stabilization → Plan L/M checkpoint → E/F/H → N-1A/O-1A → ADR-001/002 acceptance.
- **Parallel infrastructure:** Plan K plus GitLab runner preparation.
- **Parallel non-blocking research:** G/J/P and broader N/O.
- **Plan AC integrity lane:** Integrity 1.3 and synthetic replay first; live capture remains blocked.
- **Plan AD lane:** in-memory proof may proceed; persistence, fiscal behavior, Slauf mapping, and acceptance remain DEC-015-gated.
- **Separate A1 lane:** Plan R remains blocked on the seven missing Section 4 columns; preserve the existing provisional package.
- **Quarantined lane:** benchmark ranking, OCR proposal validator, ZIP, and unreviewed operational artifacts.
- **Accepted checkpoint:** Q. Retention, reflog expiry, garbage collection, deletion, and later publication remain separate decisions.
- **Historical input:** D and all 2026-08-11 plans.

Authoritative paths and statuses are maintained in [`plans/INDEX.md`](plans/INDEX.md).
