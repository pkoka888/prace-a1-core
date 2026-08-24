# Codex Planner Report: Functional Prototype as Priority 1

**Date:** 2026-08-17  
**Author:** primary agent (analysis), Codex planner (action items)  
**Purpose:** Reprioritize plans and roadmap to deliver a functional prototype as the top priority.  
**Scope:** This is a planning recommendation, not an execution directive.

---

## Executive summary

The project has strong governance, decision records, and planning infrastructure but **zero working code** for the portal itself. The critical path to a functional prototype runs through Plan E (synthetic proofs) → M2 (Django scaffold) → M3 (worker/OCR workflow) → M4 (A1 integration). This report recommends concrete plan and roadmap adjustments to make that path explicit and fast.

---

## Current state (what exists)

| Asset | Status | Value |
|---|---|---|
| ADR-001 (architecture direction) | Approved by Pavel | Strong |
| Decision register (DEC-001–016) | Complete and consistent | Strong |
| Planning catalog + validator | Operational | Strong |
| Approval register + validator | Operational, 0/8 checks | Gate |
| Roadmap portal prototype (HTML) | Visual mockup only | Weak — no working backend |
| Synthetic fixtures for Plan E | Created today (`tests/fixtures/release_1a/`) | Ready for Plan E sprint |
| Evidence documents (Plan E) | 6 placeholder comparisons | Weak — not real measurements |
| Plan E proof tests | 0 of 16 files exist | **Critical gap** |
| Plan E prototype (Django) | 0 of 3 directories exist | **Critical gap** |
| M2 Django scaffold | Not started | After Plan E |
| M3 worker/OCR workflow | Not started | After M2 |
| M4 A1 integration | Not started | After M3 |
| J1–J4 journey execution | Not started | After M2 |

---

## What's blocking the prototype

### Blocker 1: Plan E has no code, no tests, no prototype (CRITICAL)

Plan E defines 16 deliverable paths. Zero exist:
- `prototypes/architecture/adr001/project/` — Django settings, URLs, apps (0/3)
- `tests/architecture/` — 8 proof test files (0/8)
- `scripts/run_architecture_proofs.py` — orchestrator (0/1)
- `docs/architecture/` — threat model, dependency review, evidence, report (0/4)

**Impact:** Implementation gate stays blocked. No scaffolding can begin.

**Fix:** Execute Plan E sprint sequence. Synthetic fixtures are now ready. The sprint should produce a minimal disposable Django project that proves MFA, tenant isolation, job recovery, protected storage, audit, A1 boundary, dependencies, and rollback — not a portal.

### Blocker 2: Plan E evidence documents are placeholders

The 6 files under `docs/decisions/evidence/plan-e/` contain comparison text but no measured results, no scores, no sensitivity analysis, and no operational cost data.

**Impact:** Even if Plan E tests pass, the evidence documents don't support the weighted scoring required by Plan E §Decision record.

**Fix:** The proof sprint script (`run_architecture_proofs.py`) must generate the evidence, not hand-write it. Update Plan E to make the script the single source of evidence generation.

### Blocker 3: No Django project exists anywhere

There is no `manage.py`, no `settings.py`, no `urls.py`, no Django app. The roadmap portal is static HTML. The A1 engine is a standalone Python package.

**Impact:** M2 (scaffold the accepted architecture) starts from zero.

**Fix:** Plan E's disposable prototype (`prototypes/architecture/adr001/project/`) should be designed as a seed for M2, not a throwaway. Define the interface boundary clearly so the disposable settings can be replaced with production settings without rewriting apps.

### Blocker 4: J1–J4 journeys have no execution surface

The journeys require a working portal (M2+). But the HTML prototype can serve as a walk-through surface for Jan to validate workflow language and field requirements before M2 exists.

**Fix:** Use the existing HTML prototype for Jan's language/field review (J1–J4 partial). Defer the "actual device/browser" test to after M2.

---

## Recommended plan changes

### 1. Elevate "functional prototype" as explicit M2 exit criterion

**Current M2 exit:** "mandatory TOTP, tenant isolation, deployment checks, and core synthetic workflows pass"

**Proposed M2 exit:** "Jan can log in with TOTP, see his organization's workers, upload a document, see OCR proposals, create an assignment, and trigger A1 preparation — all on synthetic data, all on his actual browser."

**Why:** The current exit is technical. The proposed exit is user-facing and testable by Jan. It makes the prototype tangible.

**Action:** Update `roadmap.md` M2 section and `plans/INDEX.md` M2 row.

### 2. Split Plan E into "proof sprint" and "prototype seed"

**Current Plan E:** One monolithic plan covering proofs, prototype, evidence, and decision.

**Proposed split:**
- **Plan E (proofs only):** MFA, tenant isolation, job recovery, storage, audit, A1 boundary, deps, rollback. Produces test results and evidence. No portal code.
- **Plan M2 (prototype seed):** Takes Plan E's disposable Django settings and apps, adds PostgreSQL, templates/HTMX, and the first working screens. Produces the functional prototype.

**Why:** Plan E is a decision-validation plan. Mixing it with prototype-building delays both. Separate concerns.

**Action:** Create `plans/2026-08-17-plan-m2-prototype-seed.md` as a new active plan under M2.

### 3. Make Plan F/H journey validation parallel with M2

**Current:** J1–J4 require "observed journey" on "actual device/browser" — implicitly after M2.

**Proposed:** 
- Phase 1 (now): Jan reviews J1–J4 field requirements and Czech terminology against the HTML prototype. No code needed.
- Phase 2 (after M2): Jan runs J1–J4 on the actual working prototype. Records blockers.

**Why:** Phase 1 unblocks field/data decisions that M2 needs. Waiting for M2 to start field review creates a circular dependency.

**Action:** Update `docs/release-1a/unblock-review-packet.md` to clarify the two-phase approach.

### 4. Prioritize the Django scaffold (M2) over broader Plan L/M exits

**Current:** Plan L and M have broader exit items that don't block Release 1A synthetic work.

**Proposed:** Explicitly state that M2 implementation begins as soon as Plan E proofs pass, regardless of Plan L/M broader exit status. The operational baseline is already sufficient.

**Why:** The broader Plan L/M exits are governance housekeeping. They shouldn't delay working code.

**Action:** Add explicit note to `roadmap.md` and `plans/INDEX.md` that M2 is unblocked by Plan E alone.

### 5. Create a "prototype sprint" bounded plan

**New plan:** `plans/2026-08-17-plan-m2-prototype-sprint.md`

**Scope:** 
1. Django project setup with production-like settings (but synthetic DB)
2. PostgreSQL schema for organizations, users, workers, documents, assignments, A1 cases, audit events
3. django-allauth[mfa] with mandatory TOTP
4. Organization-scoped middleware and querysets
5. Template-based UI: dashboard, worker list, document upload, assignment form, A1 case view
6. HTMX for document upload progress and assignment overlap warning
7. Protected file storage with Nginx X-Accel-Redirect (mock)
8. Background job queue with django-q2 (mock worker)
9. AuditEvent logging for all writes
10. Jan can complete J1–J4 on synthetic data

**Duration:** 2-week sprint after Plan E proofs pass  
**Exit:** Jan completes J1–J4 without facilitator intervention on his actual device/browser

**Action:** Create this plan and add it to `plans/INDEX.md` as the M2 execution plan.

---

## Roadmap adjustments

### Current roadmap M1A exit (keep as-is)

> "Accepted operating model and planning shell; approved Release 1A catalog; ADR-001/002; synthetic journeys, security/data-flow tests, traceability, and an implementation-ready backlog."

This is correct and should not change. ADR-001 is approved; ADR-002 is still needed.

### Current roadmap M2 (adjust)

**Current:**
> "Scaffold the accepted Django architecture, PostgreSQL schema, templates/HTMX UI, localization, organization memberships, audit foundation, protected-storage interface, and background jobs."
> **Exit:** "mandatory TOTP, tenant isolation, deployment checks, and core synthetic workflows pass."

**Proposed:**
> "Scaffold the accepted Django architecture with PostgreSQL, MFA, organization isolation, protected storage, background jobs, audit events, and the first working screens (dashboard, workers, documents, assignments, A1 cases)."
> **Exit:** "Jan completes J1–J4 on synthetic data in his actual browser. TOTP enforced, tenant isolation verified, audit events recorded for all writes."

### Current roadmap M3/M4 (no change needed)

M3 and M4 depend on M2. No adjustment needed until M2 exits.

### Add "Prototype Sprint" to plan sequence

**Current:**
> "Critical M0/M1A: accepted ADR-001 direction → Plan E validation plus F/H and N-1A/O-1A design in parallel → implementation gate and ADR-002 → exception-only Jan review."

**Proposed:**
> "Critical M0/M1A: accepted ADR-001 direction → Plan E validation plus F/H and N-1A/O-1A design in parallel → implementation gate and ADR-002 → exception-only Jan review → **Plan M2 prototype sprint (2 weeks)** → Jan J1–J4 observation → M2 exit."

---

## Priority-ordered action list for Codex planner

| # | Action | Files to edit | Depends on |
|---|---|---|---|
| 1 | Execute Plan E proof sprint (synthetic fixtures exist) | Create `prototypes/architecture/`, `tests/architecture/`, `scripts/run_architecture_proofs.py` | Nothing (unblocked now) |
| 2 | Update M2 exit criterion to be user-facing | `roadmap.md`, `plans/INDEX.md` | Nothing |
| 3 | Create Plan M2 prototype sprint plan | New file `plans/2026-08-17-plan-m2-prototype-sprint.md` + update `plans/INDEX.md` | Plan E proofs pass |
| 4 | Split Plan E evidence generation into script-driven | `plans/2026-08-12-plan-e-architecture-proofs-and-adr.md` | Nothing |
| 5 | Clarify J1–J4 two-phase approach | `docs/release-1a/unblock-review-packet.md` | Nothing |
| 6 | Add M2 prototype sprint to roadmap plan sequence | `roadmap.md` | Plan M2 created |
| 7 | Explicitly state M2 unblocked by Plan E alone | `roadmap.md`, `plans/INDEX.md` | Nothing |
| 8 | Jan reviews J1–J4 field requirements against HTML prototype | Manual review | Nothing (can start now) |

---

## What NOT to change

- **ADR-001 approval** — already correct. Do not reopen unless a critical Plan E check fails.
- **Decision register** — already consistent. DEC-006–010 are accepted.
- **Approval register** — already validates. 0/8 checks are correctly pending.
- **Plan E scope** — keep it as proof-only. Do not add portal code to Plan E.
- **Real-data gates** — DEC-012, Plan R, Plan K are correctly blocked. Do not weaken them.
- **Plan L/M broader exits** — keep them active but explicitly non-blocking for M2.
- **Historical plans** — do not modify superseded plans B/C/D/I.

---

## Risk: scope creep into "full portal"

The biggest risk to the prototype sprint is scope creep. The prototype must prove:
- Jan can log in (MFA)
- Jan sees only his organization's data (tenant isolation)
- Jan can upload a document and see OCR proposals
- Jan can create an assignment
- Jan can trigger A1 preparation

It must NOT:
- Implement production deployment
- Handle real PII
- Build a public frontend
- Implement payroll/finance
- Replace the existing A1 engine

Keep the prototype sprint bounded. It proves the architecture works for Jan's workflow. Production hardening comes later.

---

## Appendix: fixture inventory created today

```
tests/fixtures/release_1a/
├── manifest.json          # Fiction markers, hashes, independence proof
├── organizations.json     # 3 synthetic orgs (CZ, DE, CZ)
├── users.json             # 5 synthetic users (admin, operator, viewer, 2 cross-org)
├── workers.json           # 4 synthetic workers (2 CZ, 1 DE, 1 inactive)
├── documents.json         # 5 synthetic docs (2 approved, 2 rejected negative, 1 cross-org)
├── assignments.json       # 5 synthetic assignments (2 active, 1 planned, 1 overlapping negative, 1 cross-org)
├── a1_inputs.json         # 2 synthetic A1 cases (1 complete, 1 incomplete)
└── jobs.json              # 5 synthetic jobs (2 completed, 1 failed, 1 queued, 1 cross-org)
```

Full provenance log: `docs/mock-data-provenance.md`
