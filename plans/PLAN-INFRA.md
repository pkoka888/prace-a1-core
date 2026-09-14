# Plan PLAN-INFRA — Architecture, Agent Operating Model, Planning Cockpit, Release 1A Prototype, and Infrastructure

**Status**: active
**Milestone**: M0–M2

## Current execution — 2026-09-14

Own REL-01–REL-06 and JAN-04 in [delivery reliability and Jan core v1](2026-09-14-delivery-reliability-and-jan-v1.md). Priorities are truthful
completion evidence, proportional validation and usable private-site acceptance.
Keep the existing custom hook/runner, Django/HTMX architecture and private receipts.
Reconcile conflicting hook/CI entrypoints; no new MCP, queue, container platform or
second settings module is a prerequisite. Host state must be rechecked before
repeating historical “not deployed” or “cluster down” claims.

The implementation backlog and parallel ownership live in the child plan. Core
v1 excludes official A1 generation/issuance; drafts are optional. JAN-03 owns
scope reconciliation in review UI/machine checks, with shared controls preserved.
No registered approval is changed by this planning checkpoint.

## Retained contracts and dated evidence

The following older sections retain provenance and architecture/operational
contracts. Their dated next-step/absence statements are historical, not the
current queue; current scope and next actions are the section above and roadmap.


## Practical consolidation and delivery — 2026-09-08

Follow the [local automation plan](2026-09-08-local-a1-automation.md): one editable
source tree, immutable `runtime/s-<full-commit-sha>/` exports and fresh
`runtime/portal/supervised-development/` under `portal.settings_supervised_synthetic`.
Preserve historical databases; rebuild development from the on-disk migration graph.
Future `runtime/portal/production/` and `portal.settings_production` require separate
provisioning. Engineering owns settings/manifests; sysadmin owns credentials/host state.
Seed `--verify` and `scripts/release_reproducer.sh <sha>` are implemented with
exact settings selection, role/duplicate reconciliation and verified committed
source. Supervised inbox defaults select existing operator/organization IDs only.
The delivery record separates synthetic tests, committed-source reproduction,
fresh development bootstrap, publication and activation. No service is deployed.
Use AGENTS.md's proportional checks and one delivery record; historical duplicate
export-test requirements do not add a new gate. Existing hooks/activation checks
remain effective. Optional skills/MCPs/client hooks do not block this work.

## Approval validation delivery — 2026-09-08

Shared approval checks preserve catalog consistency and enforce dependency states
from one validated register snapshot. Planning fixtures exclude protected runtime
and secret paths. See the [delivery record](../docs/operations/git-delivery.md) for
commit provenance, synthetic acceptance and the concurrent-session limitation.
Plan status, catalog IDs and all human/activation gates remain unchanged.

## Git delivery safeguards — 2026-09-07

Existing GitHub CI now propagates test, dependency and lint failures. The local
hook checks staged blobs/catalog and rejects missing or invalid validation.
Synthetic tooling tests pass from an exported commit snapshot. Full-suite
collection dependencies and lint backlog remain separate acceptance blockers.
Next: coherent source publication, clean CI, then review draft PR #1; no new
runner, remote, deployment or activation authorization. See
[delivery contract](../docs/operations/git-delivery.md).

## Runtime and J4 engineering — 2026-09-07

Runtime confinement, mandatory live manifest validation, killable supervised
readiness, PostgreSQL cancellation and model verification are implemented.
J4 stores actual canonical PDF bytes, automated QA, immutable snapshots and all-page
previews, with protected audited delivery and source/template/layout staleness.
Preparation alone produces no PDF hash. Migration0011 is implementation/test evidence,
not a service migration. Exact results and limitations are recorded in the
[engineering delivery](../docs/research/2026-09-07-runtime-j4-engineering.md).

Visual acceptance, the remaining ENG-001 checks and deployment remain gated.
No automatic ENG-001 opening follows; retain prerequisites including J4 → ENG-001
→ REV-002 → hardening/activation gates → REV-003. Jan confirms facts; routine source
repairs and tests need no per-edit operator approval. Research cleanup remains
retain pending review. Preserve all34 catalog IDs and existing child task IDs.
Earlier partial-status defect lists below are historical baselines superseded by
this checkpoint only where the delivery report records completed validation.

## Stabilization checkpoint — 2026-09-07

Bounded stabilization is synthetic-accepted: **157 passed, 19 subtests** in the
final focused suite; document core **75 passed**. Preserve the initial failed
baseline (**5 failed, 33 passed**) as history. Deployment is not performed or
implied. Final isolated-storage/cache reruns passed **15 PostgreSQL intake tests**
and **33 affected M2 tests**, with no model/migration drift. See the
[stabilization report](../docs/research/2026-09-07-a1-stabilization.md).
The broader A1 repair and engineering gates remain active/pending.
See [roadmap stabilization](../roadmap.md#stabilization-synthetic-acceptance--2026-09-07).
Next bounded J4/promotion engineering may start with sequential file ownership;
this does not approve final promotion or activation. Minimum functioning
J4 remains before ENG-001 → REV-002 → remaining activation gates → REV-003.
No service migration is authorized: identify service settings/database separately;
use fresh PostgreSQL and historical MigrationExecutor states for test evidence.
RapidOCR/ONNX does not require Tesseract. Organization work is read-only inventory,
with unknown artifacts classified before any relocation or deletion.

## Infrastructure packet review — 2026-09-07

**Implementation:** scoped application repairs integrated in the working tree.
**Acceptance:** see [independent review](../docs/research/2026-09-07-infra-application-review.md)
for exact synthetic suites, actual Chromium/OCR evidence and limitations.
**Deployment:** BLOCKED; no selected service identity, confined supervised settings,
SOPS/database delivery or recovery proof. Existing review settings share document
storage; the synthetic liveness marker does not establish isolation.

Next: complete the [runtime return contract](../docs/operations/infra-return-work-order-2026-09-07.md)
and minimum J4. Fixes include anonymous smoke false-pass and OCR review URL mismatch.
Optional Tesseract is a tested local extension, not the default or an accepted field
source. There is no configured ORM broker/queue. Infrastructure's 104 tests/14
validators are attributed evidence from its repository, not application acceptance.
Technical defaults belong to engineering/infrastructure; Jan confirms business facts.
No gate opens: functioning prerequisites including J4 → ENG-001 → REV-002 →
remaining hardening/activation gates → REV-003. Preserve 34 catalog entries.

## Runtime handoff correction — 2026-09-07

The reviewed [runtime manifest](../docs/operations/runtime-manifest.md) separates source/test evidence from target
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

## Bounded settings and readiness — partial status — 2026-09-07

The OpenCode session produced a `portal/settings_supervised_synthetic.py`
contract and bounded `/readiness/` checks (38 + 28 = 66 tests passing in
isolation). Independent reviewer enumeration found each track
**implemented partially / acceptance incomplete / deployment blocked**:

- Symlink containment is not enforced on `PRACE_RUNTIME_ROOT` or any
  ancestor path; the contract only checks `Path.is_dir()`.
- The fixed-name probe files (`.supervised-write-probe`,
  `.readiness-write-probe`) can collide with existing files in the
  permitted root. Unique probe names (e.g. `uuid4().hex`) are required.
- `PRACE_DB_PASSWORD` is read but never assigned to
  `DATABASES["default"]["PASSWORD"]`; the contract reads the variable
  but the database configuration never wires it through.
- Remote TLS verification (`verify-full` + `sslrootcert`) is optional in
  the contract; the return work order makes it mandatory for remote
  targets.
- The manifest validator accepts any mode where the group/other write
  bits are clear, which includes owner-writable modes (`0600`, `0640`).
  Mode `0440` (or stricter) is the only intent: owner read + group read,
  no writes anywhere. The current validator does not reject the
  owner-writable alternatives, so an operator-introduced `0600`
  manifest passes the contract. The contract must enforce a true
  read-only posture (mode bits other than `S_IRUSR` / `S_IRGRP`
  unset, no owner write) or record explicit operator authorization for
  an owner-writable exception.
- Readiness re-hashes manifest bytes at probe time but receives no
  expected hash and validates cached JSON metadata; binding to a
  `PRACE_RELEASE_MANIFEST_SHA256` env var, re-reading the file at
  every probe, comparing bytes against the trusted expected identity,
  and validating the current JSON against schema is required.
- Readiness measures elapsed time after synchronous checks; a blocked
  final check can still return ready. Required: enforced overall
  deadline, bounded individual operations (per-check deadline), and
  rejection of late results (any check that returns after its own
  budget or the overall deadline is treated as failure, not silently
  accepted). `statement_timeout` for PostgreSQL alone is insufficient
  — connection establishment, filesystem probes, model-asset loads
  and OCR/model invocations need their own bounds; nothing in the
  current implementation interrupts a hung cursor or file handle.
- Model-asset verification is missing from the bounded checks.

`ENG-001` remains blocked. No commit, push, real-data activation or
gate opening follows from these results. Repairs are next
infrastructure/application tasks; child task IDs and the 34 top-level
catalog entries are unchanged.

## Purpose

Single governing plan for the foundation and infrastructure of Release 1A:
architecture proofs and ADR-001, the agent/skill/workflow/Git operating model,
the generated visual planning cockpit, the bounded functional prototype sprint
(M2), server62 production readiness, and repository workflow/dual-remote/CI
automation.

Replaces and consolidates the dated plans:

- `plans/2026-08-12-plan-e-architecture-proofs-and-adr.md`
- `plans/2026-08-12-plan-l-agent-operating-model.md`
- `plans/2026-08-12-plan-m-visual-planning-cockpit.md`
- `plans/2026-08-17-plan-m2-functional-prototype-sprint.md`
- `plans/2026-08-12-plan-k-server62-readiness.md`
- `plans/2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md`
- `plans/2026-08-25-plan-e01-environment-ci-stabilization.md`

The archive of the individual dated plans lives under `.archive/plans/`; the
tracked source of truth is this file plus [`plans/INDEX.md`](INDEX.md).

## Status and governance

- Status: `active` (foundation is in progress; M0/M1A-facing work continues).
- Decision state: `prototype-required` — ADR-001 choices are validated, but
  production/activation gates remain machine-readable and separate.
- Evidence: `synthetic-tested` — eight hash-bound architecture checks plus
  catalog/validator tooling are green; operator/sysadmin evidence for server62
  and GitLab/CI activation is still required.

Dependencies (all recorded in `planning/catalog.json`):

- `DEC-016` with gate `activation-gate` — GitLab/CI activation requires explicit
  Pavel approval before any remote, credential, runner, or CI mutation.
- `PLAN-WORKERS` with gate `may-be-implemented` — Release 1A role/data/ADR-002
  slice acceptance must precede scaffolding of the functional prototype.

## Codex/OpenCode handoff — 2026-09-07

Receipt-scope root binding and transitive core/A1/template scope tests are implemented.
[OpenCode work orders](../docs/operations/opencode-work-orders/README.md) assign
remaining J4/receipt implementation, regression tests, safe organization inventory,
release packaging audit and offline provider safety. No gate/approval changes.
[Implementation evidence](../docs/research/2026-09-06-a1-engineering-delivery.md).

## Next integration closure from the 2026-09-06 review

Keep the existing shared document core; no replacement framework or duplicate
parser. Extend review-scope enforcement to `src/document_core/`, the intake test
harness and all transitive runtime/config dependencies. Add focused receipt-binding
and clean/dirty/untracked scope tests (including expected commit and approval hash).
Prepare an explicit complete source/template/migration/test path inventory before
any separately requested publication; verify the exported Git object afterward.
Untracked work is not a deployed outage, but partial publication is unsafe.

Sprint 1–4 are ordered delivery batches governed by existing PLAN-REAL-DATA task
tables, not new calendar commitments. Synthetic prerequisite implementation is
allowed before ENG-001. Minimum J4 stored snapshots, all-page previews/QA and
staleness handling remain Sprint 3 prerequisites. See the
[architect review](../docs/research/2026-09-06-a1-session-architect-review.md).

## Contents and exit evidence

- **Architecture proofs:** all ADR-001 validation checks pass with hash-bound
  run/verify evidence; production gates remain separate. See
  [`ADR-001`](../docs/decisions/ADR-001-jan-portal-architecture.md) and
  `planning/approvals.json`.
- **Operating model:** authority hierarchy and task startup/Git/subagent rules
  exist ([`AGENTS.md`](../AGENTS.md)); deterministic model-free CLI verification
  is required before any checkpoint is called green.
- **Planning cockpit:** `planning/catalog.json` + schema, the deterministic
  renderer/loader, and `scripts/validate_planning.py` are the single validation
  entry point.
- **Functional prototype sprint:** Jan completes J1–J4 on a tenant-isolated
  synthetic review environment. Access: `ssh -L 8000:127.0.0.1:8000 s62` then open
  `http://127.0.0.1:8000/` in the browser on s62; or via a separately-approved stable
  HTTPS review URL (Tailscale-internal, not public). Review surface at `/review/`
  (Kontrola Release 1A) — four sections, one acceptance button. Automated readiness:
  `scripts/verify_synthetic_review_readiness.sh` writes `runtime/portal/synthetic-review/readiness.json`.
  Seed: `DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review scripts/seed_release1a_dev.py --apply`.
  Activate reviewer: `python manage.py activate_reviewer --email pavel-reviewer@example.invalid`.
  Allauth TOTP enrollment enforced (DEC-007); `Membership.mfa_verified` deprecated.
  Accessibility: axe-core checks via `scripts/axe_check.sh` (engineering QA gate, not Jan's approval precondition).
  synthetic vertical slice; the scaffold gate is machine-readable and bound to
  ADR-001, Release 1A slice acceptance, and Jan phase-1 defaults/exceptions.
- **server62 readiness:** capacity, repaired edge path, monitoring, mandatory
  recovery proof, rollback, permissions, and TLS evidence. The authoritative
  operational requirements live in
  [`docs/operations/sysadmin-readiness-2026-08-12.md`](../docs/operations/sysadmin-readiness-2026-08-12.md).
- **Repository workflow / dual remotes / CI:** local exact-path containment and
  synthetic tests pass; dual-remote and CI activation remain gated by
  [`DEC-016`](../docs/decisions/decision-register.md) in
  [`docs/operations/gitlab-integration.md`](../docs/operations/gitlab-integration.md).

## Acceptance

`venv/bin/python scripts/validate_planning.py` passes (24/24), the planning
asset is current, referenced files/commands resolve, and every external mutation
(remote, CI, credential, runner, server62 activation) carries its own explicit
approval record.

## M2 Sprint Status (2026-09-03)

### Outcomes

| # | Outcome | Status | Evidence |
|---|---|---|---|
| M2-A | Committed build coherent | ✅ Passed | Exported HEAD validation: 74/74 M2 tests pass, `manage.py check` clean, `makemigrations --check` clean |
| M2-B | Jan functional review ready | ⏳ Pending | `REV-002` blocked: J2/J4 require real storage/OCR/download implementation before sections can be marked DONE |
| M2-C | Production infrastructure ready | ⏳ Pending | server62 recovery evidence + separately approved CI; does not block M2-B |

### Key Findings

- **allauth `authenticator_added` not connected**: allauth defines the signal but
  has no internal handler that updates `account_authentication_methods` in the session.
  Our `on_authenticator_added` handler fills this gap.
- **Django test client `logout()` uses GET**: `client.get('/accounts/logout/')` follows
  the 302 redirect, creating a new session in the test client. Use POST for tests
  that need to verify subsequent auth state.
- **`is_mfa_enabled()` reads DB not session**: allauth's stage controller uses the DB
  authenticator table to decide whether to show MFA challenge, but uses session's
  `account_authentication_methods` to decide which stages to activate on a given login
  attempt. Both must be satisfied.
- **Accessibility removed from approval gate**: `_axe_receipt_valid()` call removed from
  `review_approve()`. Accessibility remains an engineering QA item required before M5
  real-data activation or production release.

### Accessibility (Engineering Gate)

Accessibility is NOT part of Jan's approval preconditions. It is tracked separately as an engineering gate:
- Required before M5 real-data activation or production release
- Run with proper local axe-core dependency and authenticated Playwright fixture
- Not presented as Jan's responsibility

### Implementation Commits

The following commits constitute the Phase 1 remediation implementation:
- `dee29c6` — Phase 1 remediation: normalize intake/OCR schema, fix P0 bugs, add capabilities
- `e38c930` — Fix worker_a1_readiness: map OCR field names to canonical names
- `5e0e89e` — Add M2 release templates and static assets

### Migration 0006 Note

Migration `0006` is synthetic-only and destructive. It is not production migration evidence. Do not cite it as proof of production schema readiness.

### Status Reports

- Superseded: `plans/RELEASE-1A-REVIEW-STATUS-2026-09-02.md`, `plans/RELEASE-1A-REVIEW-STATUS-2026-09-03.md`

## Execution sequence and ENG-001 prerequisite mapping

The authoritative execution sequence is:

```
Sprint 1–3 tasks (including minimum J4 implementation)
  → ENG-001 (implementation_gate: open)
  → REV-002 (human_decision: approved) — Jan/operator J1–J4 observed
  → Sprint 4 tasks (A1 hardening, encrypted backup)
  → operational/legal/infrastructure gates (OPS-001, LEG-001, INF-001)
  → REV-003 (human_decision: approved)
  → real-data activation
```

Every ENG-001 prerequisite must pass before that gate opens. Minimum J4
implementation is part of Sprint 3 and must satisfy the actual ENG-J4 checks
(stored snapshot/artifact bytes, deterministic generation, fresh all-page QA,
required visual validation, and working state/staleness handling). Being "defined"
or "documented" is insufficient.

| Prerequisite | Maps to | Evidence |
|---|---|---|
| Sprint 1: Protected storage (encryption-at-rest) | `tests/architecture/test_protected_storage.py` | Django Storage backend; OcrRun reads from storage |
| Sprint 1: Scanner adapter fail-closed | Size limit, SHA-256, extension allowlist, MIME detection | Structural parser check; scanner failure is hard reject |
| Sprint 1: FieldProposal/FieldDecision immutability | No mutation path after creation | DB uniqueness for one final decision per proposal |
| Sprint 2: Forward-only migrations from 0005 | `MigrationExecutor` transition tests pass | PostgreSQL; not SQLite |
| Sprint 2: Composite tenant FKs on PostgreSQL | RLS as optional defense | Non-owner application role |
| Sprint 3: IntakeItem, partial-failure recovery | Multi-file intake partial success | Staged state and reconciliation |
| Sprint 3: Purpose, legal-basis, retention fields | All document models | `retention_review_at`, `legal_hold_at`, `deleted_at` |
| Sprint 3: Minimum J4 snapshot model | ENG-J4-SNAPSHOT | `A1InputSnapshot` schema migrated; bytes stored in protected storage |
| Sprint 3: Minimum J4 preview/artifact | ENG-J4-PREVIEW | `A1Artifact` created; all-page QA passed; visual validation recorded |
| Sprint 3: Minimum J4 state machine | ENG-J4-STATE | Deterministic generation; staleness triggered by dependency change; fail-closed pipeline |
| Sprint 4: A1 hardening after REV-002 | Follows REV-002 | Full artifact production, encrypted backup |
| Sprint 4: Encrypted backup | INF-001 | Separate operator/sysadmin gate |

Later sprints extend and verify these capabilities rather than introduce prerequisites after approval.
