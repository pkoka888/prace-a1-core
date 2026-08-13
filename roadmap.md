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

- Approve the intended source tree; do not push the incomplete rewrite mirror.
- Keep durable project files under `/var/www/prace-v-nemecku.tvoje.info`; distinguish tracked source from gitignored real-data/runtime directories.
- Reconcile `A1_PRIVATE_DIR` with the actual protected inputs and verify canonical commands.
- Separate source/history cleanup, runtime-data relocation, and product implementation into independent changes.
- Execute Plan K's capacity, shared edge-path, service-account, monitoring, and
  recovery gates. Synthetic design may continue in parallel, but real-data
  activation requires the capacity threshold and tested backup/restore proof.
- Establish Plan L's authority, agent/subagent, skill, validation, historical-doc,
  and Git workflow before new application work.

**Exit:** clean-clone contents are approved; Git history remediation has a separately verified procedure; private inputs have one truthful documented location; active implementation paths and ownership are unambiguous.

## M1A — Release 1A implementation readiness

- Complete Plan L and a minimal Plan M catalog/visual shell.
- Research best-practice defaults first and maintain an illustrated decision brief with a recommended choice and meaningful variants. Ask Jan/operator only to approve or annotate operational facts that research cannot determine.
- Complete Jan/operator workflow confirmation and synthetic acceptance journeys from that prepared brief.
- Complete Plans E, F, and H outputs for Release 1A, including synthetic acceptance
  journeys, the threat model, localization/accessibility contract, and traceability.
- Freeze the Release 1A role, permission, field, report, data-necessity, entity,
  index, transaction, deletion, migration, and reconciliation slices of Plans N/O.
- Prove authentication/MFA, organization authorization, job execution, protected downloads, audit events, and the A1 package boundary.
- Record ADR-001 and ADR-002, the decision register, acceptance traceability, and
  synthetic security/data-flow test evidence.
- Adopt `docs/security/real-data-rules.md` as the sole operational gate for new real-data portal use. Remaining legal questions are recorded for validation and do not block synthetic implementation.

**Exit:** accepted operating model; usable planning shell; approved Release 1A
catalog; ADR-001/002; threat model; synthetic journeys and security/data-flow
tests; acceptance traceability; and an implementation-ready Release 1A backlog.

## M1B — Broader platform design

- Continue the remaining full-platform scope of Plans N and O.
- Complete Plan P and ADR-003 in parallel; neither blocks Release 1A scaffolding.
- Continue market/business research and later-role prototypes for Releases 1B–2.
- Keep Czech/German payroll inactive until separately specialist-certified.

**Exit:** later roles, modules, interfaces, payroll/finance architecture, market
evidence, and public-growth choices are ready for their own gated increments.

## M2 — Build the shared synthetic foundation

- Scaffold the selected Django architecture, PostgreSQL schema, templates/HTMX UI, localization, organization memberships, audit foundation, protected-storage interface, and background jobs.
- Deploy development/staging with synthetic fixtures only.

**Exit:** authentication with mandatory TOTP, tenant-isolation tests, deployment checks, and core synthetic workflows pass.

## M3 — Release 1A employee, document, OCR, and assignment workflow

- Implement employee records, document quarantine, local OCR proposals, human review, workplaces, assignments, current-placement calculation, missing-data tasks, and operator oversight.

**Exit:** Jan and operator complete agreed synthetic employee journeys without spreadsheets or direct filesystem/script handling.

## M4 — Complete Release 1A A1 preparation

- Integrate the existing fail-closed A1 engine as an internal package.
- Create A1 cases from reviewed employee and assignment data; expose validation, generation, preview, review, artifact, and status history.
- Preserve the distinction between a prepared application package and an official certificate.

**Exit:** agreed synthetic profiles generate deterministic packages through the portal and all failure/approval states behave as specified.

## M5 — Controlled real-data pilot

- Pass the activation gate in `docs/security/real-data-rules.md`, migrate approved legacy data, and complete Jan/operator onboarding, incident procedure, and training.
- Produce an encrypted application-consistent backup, pass integrity checks, and
  complete an isolated restore with application-level validation before enabling
  any new real-data portal upload.
- Enable real documents only after explicit operator approval.

**Exit:** Jan manages real employees, placements, and A1 cases in the portal; access and changes are auditable; operational feedback is resolved or prioritized.

## M6 — Releases 1B, 1C, and public growth

- Activate partner/worker access, recruitment, planning, attendance/time, and
  communications in separately tested vertical increments.
- Activate Czech and German payroll independently only after specialist-certified
  versioned rules and golden tests; connect the operational finance subledger to
  formal accounting rather than implementing general accounting.
- Validate business positioning, market channels, public UX, job workflows,
  external integrations, and terms before public growth work.
- Select a separate public frontend only when its proven requirements justify it.

**Exit:** each increment has its own approved requirements, security/legal and
specialist gates, synthetic/real acceptance evidence, rollout, and rollback plan.

## Plan sequence

- **Current execution:** Plans E, F, G, H, J, K, L, and Q.
- **After the operating-model checkpoint:** Plans M, N, O, P, and R.
- **Reviewed/historical input:** Plan D and every 2026-08-11 plan.

The authoritative paths and normalized statuses are maintained in
[`plans/INDEX.md`](plans/INDEX.md). M0 requires a verified history-replacement
procedure from Plan Q, not execution of a force-push; any remote replacement needs
separate approval for exact refs and targets.
