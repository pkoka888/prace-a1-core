# Codex Planner Handoff — Release 1A and AF2 Parallel Lane

**Status:** Superseded snapshot — do not execute
**Date:** 2026-08-17
**Purpose:** decision-ready input for the next planning session
**Successor:** [Release 1A unblock and review packet](../release-1a/unblock-review-packet.md),
the authoritative [roadmap](../../roadmap.md), and [planning index](../../plans/INDEX.md)

This file preserves the input that led to the current planning update. Status
claims below are historical and must not override its successors.

## Current truth

At the time of this snapshot, the product critical path was the Jan/operator
private Release 1A portal. The current authority now records Plan L and Plan M as
`active` with an operational baseline sufficient for synthetic work, Plan F as
`active`, and Plans N/O as `active`. The four journeys are specified but have not
been observed with Jan/operator. ADR-001 and ADR-002 remain unaccepted, so portal
scaffolding remains blocked.

AF2.2a is useful parallel tooling and follows its main-path isolation goal, but
it is not ready for another live run. Offline evidence is green; no model is
promoted and no skill is activated.

## Planner decisions already settled

- Continue synthetic Release 1A proofs using Pavel's documented defaults.
- Require Jan/operator validation before real-data activation, not before
  synthetic architecture and UX proofs.
- Keep AF2/OpenCode work parallel and non-blocking.
- Keep the public recruitment site after the accepted synthetic portal
  foundation, with separate routes, data, deployment, forms, and authority.
- Do not scaffold Django until measured ADR-001/002 gates pass.

## Next product plan

Prepare a decision-complete Plan E proof sprint driven by the four frozen
journeys. It must produce reproducible synthetic evidence for MFA, organization
isolation, background jobs, protected delivery, append-only audit, the
Django-independent A1 boundary, dependency/version/license review, observability,
failure recovery, deployment rollback, and a Release 1A threat model. In
parallel, turn the N-1A/O-1A contracts into the detailed ERD, dictionary,
permission/transaction matrices, deletion graph, query/index catalog, and
synthetic concurrency proofs required for ADR-002. Plan H should convert the UX
contract into reviewable low-fidelity desktop/mobile journey artifacts and
accessibility test cases.

The plan must define exact files, fixtures, commands, measurement environment,
acceptance thresholds, rollback, and the evidence required before ADR-001 or
ADR-002 may change from proposed to accepted. It must exclude real data,
deployment, commit/push, and public-site implementation.

## AF2 backlog for OpenCode

Before a live AF2 run: reject symlink escape from the dedicated credential path;
require a regular owner-only `0600` source with non-empty token structure;
disable or capsule-route the legacy generic Codex branch; derive home paths in
tests; and capture one separately authorized, redacted pinned-0.147.0 JSONL
compatibility stream. Do not merge this work into the product plan.

## Human queue

Pavel must later approve ADR-001 and ADR-002 from measured evidence, decide
DEC-012 real-data activation only after all gates pass, coordinate Plan K
capacity/backup/restore evidence, and authorize any Git publication or DEC-016
GitLab activation separately. For AF2 only, Pavel/operator must provision and
rotate a dedicated revocable Codex credential before an authorized compatibility
probe or evaluation run.

Jan/operator must validate the required field set and terminology, original-scan
view/download and bulk-export policy, workplace/assignment editing boundary,
first supported activity profile, manual submission/response workflow, primary
device assumptions, language behavior, delegation details, and completion of
the four synthetic journeys before a real-data pilot.

Plan R separately waits for the operator to add the seven required Section 4
columns to the protected CSV. Plan AD waits for accounting-specialist DEC-015;
those are not Release 1A architecture decisions.
