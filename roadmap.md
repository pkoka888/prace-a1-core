# Product Roadmap — Jan Pilot to Recruitment Platform

**Status:** Authoritative
**Date:** 2026-08-19
**Current stage:** M0 repository organization, M1 discovery/architecture proofs, M2 scaffold gate open

This is the sole authoritative execution roadmap. Dated files under `plans/` define bounded work; older roadmaps remain historical context only.

## Product objective

Design one coherent Czech/German recruitment and workforce platform, including
partner operations, planning, attendance, A1, payroll, and operational finance.
Deliver it incrementally: Jan's document → worker → assignment → A1 workflow is
the first usable increment and must not wait for later module activation.

## Now / Parallel / Gated

| Category | Work |
|---|---|
| **Now** | M2 review environment **implemented** (2026-09-02): synthetic DB under `runtime/portal/synthetic-review/`, real django-allauth TOTP (DEC-007), CSRF enforcement, `Kontrola Release 1A` four-section review surface at `/review/`, hash-bound build receipts, automated readiness script `scripts/verify_synthetic_review_readiness.sh`. Jan observes J1–J4 via `/review/`; approval records are immutable. |
| **Next on Release 1A** | Complete runnable Czech-first J1–J4 screens; observe Jan/operator journeys; collect operational exceptions. |
| **Parallel** | PLAN-INFRA infrastructure (capacity, backup/restore evidence); PLAN-LEGAL (G/J) + PLAN-INVOICE (P) research; Plan AC integrity lane (PLAN-INVOICE): Integrity 1.3 repair + Pilot 1/2; PLAN-INVOICE (Plan AD) synthetic contract; PLAN-FREE-MODEL bounded free-model eval (AF2.1/2.2 repair). |
| **Gated** | PLAN-WORKERS (N/O) production impl waits for M1A; **PLAN-A1 (Plan R) completed** (2026-08-20) — 11 PDFs/33 previews generated, QA passed; visual review & backup cleanup pending. PLAN-INVOICE (Plan AD) persistence/acceptance waits DEC-015; portal scaffolding proceeds in M2 (synthetic only); GitLab/CI (PLAN-INFRA, formerly Plan AE/DEC-016) requires explicit approval; real data, publication, history rewrite require separate gates. |
| **Cleanup (this cycle)** | Delete `scripts/a1_core.py.backup`, `portal/settings.py.bak`; remove 3 legacy config files (`a1_field_coords.json`, `a1_checkbox_coords.json`, `a1_field_map.json`); keep `config/a1_provisional.json` as active provisional-policy config (per AGENTS.md, not legacy); resolve v12 research script duplicates; inventory 15 `output/provisional.backup-*` dirs per PLAN-A1; mark historical plans with headers. |
| **Immediate TODOs (R-01/R-02/R-03)** | ✅ **COMPLETED 2026-08-20**: R-01 (7 cols added), R-02 (2 people added), R-03 (doc_ids→/2026/). Canonical: 11 PDFs, 33 previews, QA passed. Visual review & backup cleanup pending. |

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
- Execute PLAN-INFRA's capacity, edge-path, monitoring, and recovery gates. Synthetic
   work continues in parallel; activation requires tested backup and restore.
- Complete PLAN-INFRA's operating-model and validation checkpoint.
- Execute PLAN-INFRA's repository workflow, dual remotes, and CI automation (formerly Plan AE).

**Exit:** the sanitized checkpoint is accepted; private inputs have one truthful
location; ownership and implementation paths are unambiguous. Recovery-ref cleanup
remains separately authorized.

## M1A — Release 1A implementation readiness

- Complete PLAN-INFRA, including the minimal plan catalog, validator, and visual shell (formerly Plans L/M).
- Complete the PLAN-INFRA (E), PLAN-LEGAL (F), and PLAN-WORKERS (H) Release 1A outputs,
  including accepted workflows, threat model,
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

- Continue broader PLAN-WORKERS (N/O) design and complete PLAN-INVOICE (P)/ADR-003 in parallel.
- Continue market research and later-role prototypes without delaying Release 1A.
- Keep payroll inactive until independently specialist-certified.

**Exit:** later roles, modules, interfaces, payroll/finance architecture, and
market evidence are ready for separately gated increments.

## M2 — Build the shared synthetic foundation

- Execute the bounded [Release 1A foundation and functional prototype preparation](plans/PLAN-INFRA.md)
  after its machine-readable start gate opens. The gate opened on 2026-08-17 and
  the initial synthetic scaffold/vertical domain path is present under `portal/`.
- Build mandatory TOTP, organization-scoped workers, synthetic document/OCR
  review, assignment overlap behavior, A1 readiness trigger, protected delivery,
  background recovery, and non-content audit as one thin vertical slice.
- Use production-shaped synthetic fixtures only; real backend values arrive later
  through configuration, migrations, or authorized intake—not fixture replacement.

**Status (2026-09-02):** review environment implemented: synthetic DB at `runtime/portal/synthetic-review/db.sqlite3` (gitignored), real django-allauth TOTP enrollment and challenge (DEC-007), CSRF enforced, `Kontrola Release 1A` at `/review/` with four sections (Pracovník, Dokument a kontrola OCR, Přiřazení, Příprava a kontrola A1), one `Schválit Release 1A` button enabled only when all sections DONE and automated readiness passes. Immutable `Release1aAcceptance` receipt stamped with git commit hash + clean/dirty + build ID. Jan acceptance is one screen; automated readiness gates are machine-verified and stored in `readiness.json`. See `docs/operations/release-1a-review-environment.md`.

## M3 — Employee, document, OCR, and assignment completeness

- Expand the M2 slice across document/profile variants, correction and recovery
  paths, queues, current-placement calculation, missing-data tasks, exceptions,
  retention/deletion behavior, and operator oversight.

**Exit:** Jan and operator complete accepted synthetic journeys without scripts or
direct filesystem handling.

## M4 — Deterministic A1 completion and hardening

- Complete the existing fail-closed A1 engine integration with validation,
  generation, previews, immutable snapshots/artifacts, approval, staleness,
  recovery, failure reporting, and status history.
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

> Mapping note: dated plan letters below correspond to the consolidated plans —
> E/K/L/M/AE→PLAN-INFRA, R/Q→PLAN-A1, F/H/N/O→PLAN-WORKERS, AC/AD/P→PLAN-INVOICE,
> G/J/I→PLAN-LEGAL, AF/AF2→PLAN-FREE-MODEL, B/C/D→PLAN-HISTORY, REAL-DATA→PLAN-REAL-DATA.
> Statuses below are dated records (roadmap dated 2026-08-19); authoritative status lives in `plans/INDEX.md`.

- **Critical Release 1A:** Plan E validation ✅ + Jan phase-1 HTML review ✅ + N-1A/O-1A ✅ → ADR-002 ✅ + automated prototype-start gate ✅ (open 2026-08-17) → M2 functional prototype sprint 🟡 (synthetic implementation green 74/74 tests; `REV-1A-FRONTEND` pending Jan J1–J4 acceptance via `/review/`; PLAN-REAL-DATA gates Sprint 1–4 before any real-data activation). Broader Plan L/M exits do not block this synthetic path.
- **Parallel infrastructure:** Plan K 🟡 (capacity/backup evidence incomplete) + GitLab runner prep (Plan AE/DEC-016 gated).
- **Parallel non-blocking research:** G/J/P 🟡 + broader N/O 🟡.
- **Plan AC integrity lane:** Integrity 1.3 🟡 + synthetic replay 🟡; Pilot 1/2 required before skill activation; live capture blocked.
- **Plan AD lane:** in-memory proof ✅; persistence, fiscal behavior, Slauf mapping, acceptance wait DEC-015.
- **Plan AF/AF2 tooling lane:** AF2 🔴 blocked by invalid harness; AF2.1 🟡 evidence-integrity repair; AF2.2 🟡 Luna capsule isolation; no skill activation, protected data, LiteLLM, or publication authority.
- **Separate A1 lane:** Plan R 🔴 blocked — CSV needs 7 Section 4 columns + 2 missing people; preserve existing provisional package.
- **Quarantined lane:** benchmark ranking, OCR proposal validator, ZIP, unreviewed operational artifacts; v12 research scripts need classification.
- **Accepted checkpoint:** Q ✅ (sanitized checkpoint `c01aa2b` accepted). Retention, reflog expiry, GC, deletion, publication remain separate decisions.
- **Historical input:** D and all 2026-08-11 plans — mark with headers per Plan L.

Authoritative paths and statuses are maintained in [`plans/INDEX.md`](plans/INDEX.md).
