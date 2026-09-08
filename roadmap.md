# Product Roadmap — Jan Pilot to Recruitment Platform

**Status:** Authoritative
**Original date:** 2026-08-19
**Last status update:** 2026-09-07 (runtime/J4 engineering acceptance recorded)
**Current stage:** M2 synthetic engineering; runtime confinement/readiness and J4 stored artifact implementation delivered; exact synthetic acceptance in the engineering report; remaining ENG-001 checks, visual acceptance and deployment gated.

This is the sole authoritative execution roadmap. Dated files under `plans/` define bounded work; older roadmaps remain historical context only.

## Local automation design — 2026-09-08

Consolidated [local automation contract](plans/2026-09-08-local-a1-automation.md)
and [44-field mapping](docs/architecture/release-1a-field-mapping.md): one editable
source tree; immutable release exports; explicit development/production data roots;
reconciled inputs followed by fresh synthetic DB/seed/reproduction work, then
J2/J4 and DB-MIG-1 through DB-MIG-7. Automatic processing will save proposals and
prepare eligible unverified drafts; BO records actor/time/revision confirmation.
AGENTS.md now uses proportional checks and one delivery record. This is a
documentation checkpoint, not implemented automation, database migration, deployment
or activation; the 34 catalog entries and registered approval states are unchanged.

## Approval validation delivery — 2026-09-08

Shared approval checks preserve catalog consistency and enforce dependency states
from one validated register snapshot. Planning fixtures exclude protected runtime
and secret paths. See the [delivery record](docs/operations/git-delivery.md) for
commit provenance, synthetic acceptance and the concurrent-session limitation.
Plan status, catalog IDs and all human/activation gates remain unchanged.

## Shared intake Git delivery — 2026-09-08

Shared offline processing and synthetic runtime dependencies are committed in
separate scopes. Document replacement now uses the shared intake pipeline with
version preservation, retry reuse and rejection of obsolete OCR acceptance.
The [current delivery record](docs/operations/git-delivery.md) separates exported-snapshot tests,
Git publication and remaining gates. No deployment or real-data activation is
included; all existing plan IDs and approval states remain unchanged.

## Git delivery safeguards — 2026-09-07

Staged-byte validation, fail-closed existing GitHub CI, runtime ignore rules and
repeatable hook installation are implemented. Focused tooling acceptance passes;
this does not establish full-repository CI acceptance. Publish the outstanding
source dependencies in reviewed scopes before merging draft PR #1. Existing
activation gates and 34 catalog IDs are unchanged. See
[delivery contract](docs/operations/git-delivery.md).

## Runtime and J4 engineering — 2026-09-07

Runtime confinement, mandatory live manifest validation, killable supervised
readiness, PostgreSQL cancellation and model verification are implemented.
J4 stores actual canonical PDF bytes, automated QA, immutable snapshots and all-page
previews, with protected audited delivery and source/template/layout/renderer/QA/build staleness.
Preparation alone produces no PDF hash. Migration 0011 is implementation/test evidence,
not a service migration. Exact results and limitations are recorded in the
engineering delivery (unpublished local material: `docs/research/2026-09-07-runtime-j4-engineering.md`).

Visual acceptance, the remaining ENG-001 checks and deployment remain gated.
No automatic ENG-001 opening follows; retain prerequisites including J4 → ENG-001
→ REV-002 → hardening/activation gates → REV-003. Jan confirms facts; routine source
repairs and tests need no per-edit operator approval. Research cleanup remains
retain pending review. Preserve all 34 catalog IDs and existing child task IDs.
Earlier partial-status defect lists below are historical baselines superseded by
this checkpoint only where the delivery report records completed validation.

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
| **Gated** | PLAN-WORKERS (N/O) production impl waits for M1A; **PLAN-A1 (Plan R) active/blocked** — provisional regeneration blocked (25/25 as of 2026-09-06 investigation: 0/25 AUTHORITATIVE source statuses; historical hash equality; current 26 provisional/25 final files need reconciliation; unverified institution evidence); preserve existing provisional package. PLAN-INVOICE (Plan AD) persistence/acceptance waits DEC-015; portal scaffolding proceeds in M2 (synthetic only); GitLab/CI (PLAN-INFRA, formerly Plan AE/DEC-016) requires explicit approval; real data, publication, history rewrite require separate gates. |
| **Cleanup (this cycle)** | Read-only source inventory and dependency analysis only. Unknown research/runtime artifacts require classification; no moves, deletions, backup cleanup or legacy-script execution in stabilization scope. |
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

## M4-A — Worker data unified in the database (DB migration)

The CSV (`a1/review.csv`) + cohort JSON (`a1/cohort.json`) + employees-normalized
JSON trio are file-based, gitignored, and mutated outside the dashboard. The
dashboard already models `portal.Worker`, `portal.A1Case`, `portal.Assignment`,
and `portal.Approval`. The DB migration sub-plan moves the authoritative data
into those models so the dashboard "Generate A1" button is a single-step
routine with full provenance.

- [Plan PLAN-WORKERS-MIGRATE-TO-DB](plans/PLAN-WORKERS-MIGRATE-TO-DB.md)
  (planned) tracks DB-MIG-1 through DB-MIG-7. After DB-MIG-7, A1 generation
  reads exclusively from `portal.release1a` models. The legacy
  `a1/*.json` / `a1/*.csv` files are frozen under `a1/_archive/` and a CI
  gate (`scripts/check_no_csv_reads.py`) blocks any tracked script from
  re-introducing a CSV read.
- The synthetic review environment (`runtime/portal/synthetic-review/`) and
  the Release 1A migration history stay unchanged; this plan only adds a
  one-time legacy-data migration command and the CI gate.
- Until DB-MIG-7 lands, the dashboard continues to read from the file-based
  trio via `portal.release1a.services` adapters. The CLI
  (`scripts/generate_provisional_a1.py`) keeps working because its inputs
  (`--review`, `--cohort`) still exist.

**Exit:** synthetic round-trip via the dashboard produces bytes that match
the legacy CSV-based generation byte-for-byte (sha256). CI gate green.

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

## Immediate delivery priorities — 2026-09-07

Codex implemented canonical employee/casing/checkbox support, template repair,
reviewed-input preservation, profile/CSV guards, snapshot/dependency hashes,
readiness receipts and receipt-scope tests. Rendering cannot enter final destinations.

1. Primary/operator: reconcile authoritative identity/employer/certificate evidence
   and prior artifact status. Directory counts and prior agent claims are not approval.
2. After stabilization acceptance, OpenCode: implement receipt-bound final promotion and remaining minimum J4 with
   actual protected bytes, current all-page QA, immutable snapshots and stale states.
3. OpenCode now: independent regression review, scoped repository organization analysis
   and complete release inventory. Provider implementation remains deferred.

## Stabilization synthetic acceptance — 2026-09-07

The focused pre-repair acceptance run was **5 failed, 33 passed**. Earlier
90/75/15/24 counts did not establish acceptance of the newly added CLI journey.
Bounded stabilization is now **synthetic-accepted**: the final focused suite passed
**157 tests and 19 subtests**; document core passed **75 tests**. Final isolated-storage/cache reruns passed **15 PostgreSQL intake tests** and
**33 affected M2 tests**, with no model/migration drift. Exact commands and scope
are in the stabilization report (unpublished local material: `docs/research/2026-09-07-a1-stabilization.md`).
Implementation, test acceptance and deployment are separate evidence states.
Deployment was not performed. The wider A1 repair plan remains active.

| Initial finding | Implemented and synthetically tested correction |
|---|---|
| Audit writer replaced earlier events | Locked append preserves sequential/concurrent history; missing context/write failure blocks processing |
| Outside-root output accepted | All destinations confined; ancestor symlinks, overlap and reserved final targets rejected |
| Candidate files published individually | Exclusive protected staging and serialized atomic package publication; failure leaves no partial package |
| Fresh QA used `/tmp`, fixed DPI and encoded PNG hashes | Protected temporary storage, recorded DPI, decoded-pixel comparison on every page |
| CLI journey failed | Mandatory receipts, three supported profiles through generation/render/QA, isolated fixtures and sanitized errors |
| Production schema claim lacked an established target | Separate fresh/historical test migrations from identified service deployment evidence |

Bounded repairs are accepted; minimum J4/promotion engineering can now receive
sequential file ownership. This is not final-promotion or activation approval. Retain
activity_name/activity_address requirements, independent activity and employment
countries, complete-verification semantics and source/approval gates. Include audit
and path helpers in approval-review dependency scope. Preserve the repaired template;
file-size growth alone is not a defect.

Acceptance requires the current working-tree command results and exact tested scope;
passing tests never proves a deployment, commit, artifact approval or legal issuance.
Service migrations require target identification and separate deployment authorization.
RapidOCR/ONNX is the existing backend; do not install Tesseract for this pipeline.

Next: functioning engineering prerequisites including
minimum J4 → ENG-001 → REV-002 → remaining hardening/activation gates → REV-003.
The operator workflow contract (unpublished local material: `docs/architecture/operator-a1-workflow.md`) separates
application preparation from issued A1 and limits Jan's choices to facts and a
consolidated confirmation. Its subsequent interface is not part of this repair.

QA now requires the generation manifest, exact PDF hashes, full-UUID completed
receipt and matching terminal completed audit event. Bind stable receipt/event
references, never the hash of the whole growing audit log. Missing or invalid policy
shape fails with sanitized diagnostics and registered staging cleanup; readiness
protects institution-profile sources too.

Work orders (unpublished local material: `docs/operations/opencode-work-orders/README.md`) distinguish current
regression/audit work from gated implementation. Source inventory is read-only;
unknown research/runtime artifacts must be classified before any move or deletion.

## Infrastructure packet review — 2026-09-07

**Implementation:** scoped application repairs integrated in the working tree.
**Acceptance:** see independent review (unpublished local material: `docs/research/2026-09-07-infra-application-review.md`)
for exact synthetic suites, actual Chromium/OCR evidence and limitations.
**Deployment:** BLOCKED; no selected service identity, confined supervised settings,
SOPS/database delivery or recovery proof. Existing review settings share document
storage; the synthetic liveness marker does not establish isolation.

Next: complete the runtime return contract (unpublished local material: `docs/operations/infra-return-work-order-2026-09-07.md`)
and minimum J4. Fixes include anonymous smoke false-pass and OCR review URL mismatch.
Optional Tesseract is a tested local extension, not the default or an accepted field
source. There is no configured ORM broker/queue. Infrastructure's 104 tests/14
validators are attributed evidence from its repository, not application acceptance.
Technical defaults belong to engineering/infrastructure; Jan confirms business facts.
No gate opens: functioning prerequisites including J4 → ENG-001 → REV-002 →
remaining hardening/activation gates → REV-003. Preserve 34 catalog entries.

## Runtime handoff correction — 2026-09-07

The reviewed runtime manifest (unpublished local material: `docs/operations/runtime-manifest.md`) separates source/test evidence from target
activation. `/health/` exists and returns a constant synthetic liveness marker;
`/readiness/` now checks database connectivity and the complete installed-app
migration graph, with sanitized failures and no-cache responses. The isolated
readiness/view/review-fix regression suite passed 41 tests. Storage, model
assets, release identity, timeouts and supervised-runtime evidence remain pending.
Existing PostgreSQL transition
proof does not identify or migrate a service database. Runtime owner selection,
explicit settings/entrypoint, protected paths and actual readiness evidence are
next infrastructure/application tasks alongside minimum J4. No Redis requirement,
production socket, active listener or host-service availability is inferred.
Jan confirms workflow facts; technical runtime choices belong to engineering and
infrastructure. Existing activation and real-data gates remain unchanged.

## Plan sequence

> Mapping note: dated plan letters below correspond to the consolidated plans —
> E/K/L/M/AE→PLAN-INFRA, R/Q→PLAN-A1, F/H/N/O→PLAN-WORKERS, AC/AD/P→PLAN-INVOICE,
> G/J/I→PLAN-LEGAL, AF/AF2→PLAN-FREE-MODEL, B/C/D→PLAN-HISTORY, REAL-DATA→PLAN-REAL-DATA.
> Statuses below are dated records (roadmap dated 2026-08-19); authoritative status lives in `plans/INDEX.md`.

- **Critical Release 1A:** Plan E validation ✅ + Jan phase-1 HTML review ✅ + N-1A/O-1A ✅ → ADR-002 ✅ + automated prototype-start gate ✅ (open 2026-08-17) → M2 synthetic implementation 🟡 (74/74 historical M2 checks; fresh core/approval tests 96 passed and PostgreSQL intake 15 passed; `ENG-001` blocked — Sprint 1–3 implements J2/J4 prerequisites; minimum J4 in Sprint 3 satisfies ENG-J4-SNAPSHOT/PREVIEW/STATE with stored bytes, deterministic generation, all-page QA, and staleness handling; `REV-002` approval follows ENG-001 opening). Gate sequence: Sprint 1–3 → `ENG-001` → `REV-002` → Sprint 4 (A1 hardening, encrypted backup) → `OPS-001`/`LEG-001`/`INF-001` → `REV-003` real-data activation. Sprint 4 follows REV-002; Sprint 3 minimum J4 is an ENG-001 prerequisite. Broader Plan L/M exits do not block this synthetic path.
- **Parallel infrastructure:** Plan K 🟡 (capacity/backup evidence incomplete) + GitLab runner prep (Plan AE/DEC-016 gated).
- **Parallel non-blocking research:** G/J/P 🟡 + broader N/O 🟡.
- **Plan AC integrity lane:** Integrity 1.3 🟡 + synthetic replay 🟡; Pilot 1/2 required before skill activation; live capture blocked.
- **Plan AD lane:** in-memory proof ✅; persistence, fiscal behavior, Slauf mapping, acceptance wait DEC-015.
- **Plan AF/AF2 tooling lane:** AF2 🟡 (separate lane from FREE-VISION-PROVIDER-SAFETY); AF2.1 🟡 evidence-integrity repair; AF2.2 🟡 Luna capsule isolation; no skill activation, protected data, LiteLLM, or publication authority.
- **Plan FREE-VISION-PROVIDER-SAFETY (2026-09-06):** 🟡 planned — remove paid/full-scan paths, metadata-only discovery, synthetic capability tests, exact free-model eligibility, quota accounting, bounded fallback, sanitized audit.
- **Plan OCR-SHARED-CORE-LOCAL (2026-09-06):** 🟡 active — bounded synthetic local/web intake implemented: document segmentation, Czech labelled OP/EHIC/passport field proposals, original/enhanced comparison, typed matching, protected OcrRun results, retries and explicit acceptance. Broader layout calibration, scanner/encryption/retention activation evidence and observed M3 acceptance remain pending; portraits and external providers are deferred. See [implementation and checks](docs/architecture/shared-document-intake.md).
- **Separate A1 lane:** Plan R 🔴 blocked — 25/25 rows blocked (2026-09-06 investigation baseline); 0/25 rows with AUTHORITATIVE source status; historical hash equality is not approval evidence; current package has 26 provisional/25 final files and four ad-hoc employee PDFs; previously VERIFIED placeholder profiles are now NEEDS_VERIFICATION. Counts are observations, not a replacement cohort contract.
- **Plan A1-EVIDENCE-STATUS-REPAIR (2026-09-06):** 🟡 active — engineering guards and employee copies implemented; authoritative reconciliation and receipt-bound promotion remain pending; canonical employee support across mapping/layout/verification and package reconciliation; reject placeholder institution profiles, enforce provisional-generation restrictions, distinguish application readiness from certificate issuance, reconcile cohort/artifact provenance, repair snapshots and final-promotion evidence.
- **Quarantined lane:** benchmark ranking, OCR proposal validator, ZIP, unreviewed operational artifacts; v12 research scripts need classification.
- **Accepted checkpoint:** Q ✅ (sanitized checkpoint `c01aa2b` accepted). Retention, reflog expiry, GC, deletion, publication remain separate decisions.
- **Historical input:** D and all 2026-08-11 plans — mark with headers per Plan L.

Authoritative paths and statuses are maintained in [`plans/INDEX.md`](plans/INDEX.md).

## Session review corrections — 2026-09-07

OpenCode session produced bounded changes against `Priority 1` (confined
supervised settings), `Priority 3` (bounded readiness preflight), `J4`
minimum, synthetic-real-data flag plumbing, and an untracked `research/`
triage report. Independent reviewer enumerated defects that the
implementer's own tests do not cover. Status of every track is **partial**;
deployment is **blocked**; no commit, push, real-data activation or gate
opening follows from these results.

> **Authorization scope (corrected).** Existing authorization covers
> routine source repairs, tests and planning updates; Jan does not
> approve each technical edit. This session is currently in **Plan
> Mode**, so implementation cannot occur here. Production deployment,
> commit/push, and destructive cleanup remain separately controlled.

| Track | Implemented | Outstanding (independent review) | Status |
|---|---|---|---|
| Confined settings (`portal/settings_supervised_synthetic.py`) | Required env contract; 38 dummy-value tests; optional `PRACE_READINESS_BUDGET_MS` | (a) symlink containment not enforced on `PRACE_RUNTIME_ROOT` or any ancestor; (b) fixed-name probe files (`.supervised-write-probe`, `.readiness-write-probe`) can collide with existing files; (c) `PRACE_DB_PASSWORD` is read but never assigned to `DATABASES`; (d) remote TLS verification is optional | partial |
| Bounded readiness (`portal/release1a/views.py:706`, `readiness_checks.py`) | 7 checks with per-check JSON; 2 s default budget; migrations short-circuited when DB unreachable; sanitized detail | (a) wall-clock measurement cannot interrupt a blocked check — a slow final check can still return ready; (b) per-check deadlines not enforced; (c) late results not rejected (a check returning after its budget is silently accepted); (d) connection establishment, filesystem probes and model-asset loads have no individual bounds; (e) PostgreSQL `statement_timeout` not applied; (f) model-asset verification missing | partial |
| Manifest binding | `PRACE_RELEASE_MANIFEST_PATH` parsed at import; owner uid + `S_IWGRP/S_IWOTH` bits checked; `app_build_id`/`git_commit` propagated to `A1Case.receipt_*` | (a) validator accepts owner-writable modes (`0600`, `0640`) because only group/other write bits are rejected; mode `0440` (or stricter) is the only intent; (b) readiness re-hashes manifest bytes but receives no expected hash and reads cached JSON metadata, not the current file; (c) the expected identity must come from a trusted source (e.g. `PRACE_RELEASE_MANIFEST_SHA256` env var or build manifest) and the current JSON must be schema-validated at probe time | partial |
| J4 minimum (`portal/release1a/services.py:108`, models, migration `0010`) | `source_snapshot_json` persisted; `is_stale` synchronized bidirectionally (was latent `AttributeError`); `notes` persisted on approval; idempotent `a1_regenerate()`; receipt bound to `app_build_id`/`git_commit` when manifest is set | **Migration evidence is recorded in three independent states**, all of which must hold: (1) migration file implementation — `0010_a1case_j4_minimum.py` written, `makemigrations --check` clean; (2) disposable transition-test acceptance — `tests.m2.test_readiness.py`, `tests.m2.test_release1a_vertical`, `tests.test_j4_minimum` apply the migration on disposable DBs; (3) deployment on a target database — **not performed.** States (1) and (2) are recorded; state (3) requires separate infrastructure authorization. Outstanding: `prepared_artifact_hash` hashes metadata, not stored PDF bytes; all-page QA, protected previews, dependency staleness all missing. J4 remains **incomplete** | partial — J4 incomplete |
| Flag plumbing (`/health/`, `/readiness/`, `/synthetic/`, `runtime_contract.py`) | Synthetic posture + build identity surfaced; `Cache-Control: no-store`; `/synthetic/` exposes a sanitized contract fixture; 33 tests | (a) tests pass on synthetic fixtures only; (b) contract conformance not established against the infra team's expected fixture; (c) no infra-side correlation yet | partial |
| Research audit (`docs/research/2026-09-07-research-audit.md`) | Disposition matrix per directory | (a) filename/keyword scans cannot establish "no PII" or "public-domain"; (b) different `repeat-2026-08-14/` runs are not proven redundant; lack of script references does not justify deletion; (c) `research/benchmark-experimental/` is directly consumed by `tests/test_benchmark_experimental.py:16` via `shutil.copytree` and cannot be archived; (d) counts conflated files and directories; (e) existing organization work order explicitly excludes these research trees; expanded authorization must be recorded separately; (f) classification needs an **explicitly scoped, authorized local review**; uncertain or sensitive cases require escalation — not universal human inspection of every file | deferred — **all dispositions reclassified as `retain pending review`** |

**Working-tree state** (validated with `git status --porcelain` + `awk`,
not basic `grep`): 0 staged entries (no first-column `A/M/D/R/C/U`); 41
working-tree modifications (` M`); 91 untracked (`??`); 0 deleted. Total
132 porcelain entries. Of those, 4 are planning files (`roadmap.md`,
`plans/PLAN-INFRA.md`, `plans/PLAN-A1.md`, `docs/research/2026-09-07-research-audit.md`)
and the remaining 128 are source/test/config artifacts from prior turns
that were also uncommitted when this session started. No source code
was edited during this session's correction turns. No staging, commits,
pushes, moves or deletions were performed during or after the corrections
review.

**Existing gates preserved:** `ENG-001` remains blocked pending J4
stored-artifact evidence; `REV-002`/`REV-003` remain blocked; Plan R
(A1 production) remains blocked at 25/25 rows per the 2026-09-06 baseline.
Child task IDs and the 34 top-level catalog entries are unchanged.

**Recommended next (technical priorities; no additional operator
decision is needed to choose these):**

1. Repair runtime confinement: enforce ancestor symlink checks for
   `PRACE_RUNTIME_ROOT`; use exclusive, uniquely named probes
   (`uuid4().hex`); reject owner-writable manifest mode (`0600`,
   `0640` must fail closed).
2. Wire PostgreSQL authentication: assign `PRACE_DB_PASSWORD` to
   `DATABASES["default"]["PASSWORD"]`; enforce `verify-full` and require
   `PRACE_DB_SSLROOTCERT` for remote targets.
3. Bind readiness to validated current manifest bytes at probe time
   (re-read `PRACE_RELEASE_MANIFEST_PATH`, compare against a trusted
   expected identity — e.g. `PRACE_RELEASE_MANIFEST_SHA256` env var —
   and schema-validate the current JSON; enforce an overall deadline
   plus per-check deadlines with explicit rejection of late results;
   bound connection establishment, filesystem probes and model-asset
   loads individually; apply `statement_timeout` for PostgreSQL).
4. Complete J4 with stored PDF bytes: hash the actual protected
   artifact, run all-page QA, persist previews, detect dependency
   staleness, before any `ENG-001` opening claim.
5. Research cleanup: deferred. Reclassify all disposition rows as
   `retain pending review` until a scoped local review confirms each
   item's posture; uncertain or sensitive cases escalate per the
   existing operator workflow contract.

## Named PDF variables and Czech personal-name display — 2026-09-07

Implementation: a local named-token helper and shared last-step personal-name casing
are implemented. A protected reference experiment produced 34 variables in 36
positions and compared token replacement with the existing overlay, using synthetic
values. The canonical background/layout migration remains pending.

Acceptance: focused tests pass; the expanded working-tree A1 suite still has an
inherited employment-name reconciliation failure. The failure reproduces with the
new casing function disabled. Deployment, employee regeneration and activation gates
are unchanged. See [current PDF comparison report](docs/research/2026-09-07-pdf-tool-comparison.md)
for methods, measurements, artifact limitations and next integration work.
