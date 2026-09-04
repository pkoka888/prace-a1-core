# Plan PLAN-INFRA — Architecture, Agent Operating Model, Planning Cockpit, Release 1A Prototype, and Infrastructure

**Status**: active
**Milestone**: M0–M2

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
| M2-B | Jan functional review ready | ⏳ Pending | `REV-1A-FRONTEND` pending Jan acceptance via `/review/`; J1–J4 observation/acceptance not yet completed |
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