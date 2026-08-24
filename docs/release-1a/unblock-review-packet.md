# Release 1A Unblock and Review Packet

**State:** synthetic work unblocked; named human/evidence gates remain
**Date:** 2026-08-17
**Owner:** product owner
**Prototype defaults reviewed by:** Codex, under Jan's delegated trust conveyed by
the project user
**Prototype approval date:** 2026-08-17
**Approval scope:** recommended defaults for synthetic prototype design and proof
work only; not personal Jan attestation, observed usability evidence, pilot
acceptance, real-data authority, or publication/deployment authority
**Scope:** decision preparation only; no portal scaffolding, deployment, real data,
infrastructure mutation, credential handling, commit, or push authority

## Decision rule

Use the recommended defaults in the Jan Release 1 solution brief for reversible,
synthetic design and proofs. Do not wait for preference approval. Stop only where
the next step would assert a real operational fact, accept measured evidence,
use protected data, mutate infrastructure, publish Git state, or activate the
portal.

The operational Plan L governance baseline and minimal Plan M catalog are already
sufficient for Plans E, F, H, N-1A, and O-1A synthetic work. Their broader exit
items remain active; this is not a claim that Plans L or M are accepted.

## Unblocked now

| Work | Adopted working default | Remaining acceptance gate |
|---|---|---|
| Architecture proofs | ADR-001 choices accepted: Django modular monolith, PostgreSQL, templates/targeted HTMX, protected filesystem, django-q2, allauth MFA, and project-owned audit | Reproducible Plan E checks open the implementation gate; critical failure reopens only the affected choice |
| Workflow and data design | Recommended Section 10 behaviors; unknown required fields remain explicitly classified | Jan/operator confirms actual fields, terms, exceptions, and first pilot profile |
| Original scans | Logged in-browser view; explicit-purpose individual download; no Release 1A bulk document export | Jan identifies a workflow that cannot operate under this safer default, if any |
| Assignment editing | Scoped editor role, effective-dated history, optimistic concurrency, staleness propagation | Jan validates who performs the edits and exceptional corrections |
| A1 external handling | Manual submission/response events with separate evidence and status | Jan validates the real handoff steps and terminology |
| Device/language | Czech-first desktop review; responsive mobile intake/quick review; German later with named reviewer | Observed journey test on Jan's actual supported device/browser |
| Delegation | Named, least-privilege, revocable, effective-dated grants with MFA and audit | Jan names delegates and chooses roles; Pavel remains incident contact |
| N-1A/O-1A | Catalog, logical schema, transaction/query/deletion design with synthetic fixtures | ADR-002 acceptance after evidence; no production implementation yet |
| Plan K preparation | Read-only evidence collection and documented runbooks may proceed | Sysadmin performs/attests host work; capacity, TLS, backup, and isolated restore evidence required |

## Two-phase Jan validation and four synthetic journeys

**Phase 1 — now:** Jan reviews fields, Czech terminology, roles, states,
scan/download defaults, assignment boundaries, and manual submission behavior in
the HTML prototype. Approved defaults apply unless Jan records an exception. This
record freezes the minimum Plan N input for ADR-002 and the M2 start gate.

**Phase 2 — M2 exit:** Jan executes J1–J4 in the functional Django prototype on
the supported browser and records only blockers, missing steps, or exceptions.

These scripts define completion; they do not claim that a runnable portal exists
yet. Use fictional fixtures only. Jan/operator must later complete each journey without
facilitator intervention before Plan H exits or a real-data pilot begins.

| ID | Journey | Required success path | Mandatory failure/recovery observations | Evidence owner |
|---|---|---|---|---|
| J1 | Create worker | Create a scoped worker and the selected activity profile; show missing required information without inventing it | Duplicate candidate, forbidden organization, invalid field, interrupted save | Jan/operator observation; product design records sanitized result |
| J2 | Review document/OCR | Upload a valid synthetic document, quarantine/validate it, review proposals, correct one value, and confirm provenance | Disguised executable, duplicate hash, OCR failure/retry, unauthorized view/download | Product engineering tests; Jan/operator validates workflow language |
| J3 | Update assignment | Create workplace and effective-dated assignment; derive current placement; warn on overlap | Stale concurrent edit, pause/completion boundary, ambiguous period blocks A1 preparation | Product engineering tests; Jan/operator validates edit boundaries |
| J4 | Prepare A1 | Resolve readiness, snapshot inputs, generate/validate preview, approve prepared package, record manual submission and separate official response | Missing profile field, worker/job restart, source change marks package stale, forbidden approval | A1 deterministic tests plus Jan/operator observation |

Every journey must show actor, organization scope, result, and non-content audit
events. Keyboard completion, visible focus, 200% zoom, 320 px reflow, clear Czech
status language, and interruption recovery are cross-journey acceptance checks.

## What Jan must review

The recommended prototype defaults are approved by delegation. Jan's remaining
review is limited to facts the repository cannot discover or observe:

1. Mark each proposed required field and Czech term as correct, optional, missing,
   or wrong for the first supported profile.
2. Confirm the first real pilot profile/cohort; do not provide real person values
   in the review document.
3. Identify any need for original-file download or multi-record export that the
   safe default does not cover, including recipient, purpose, and frequency.
4. Confirm who may edit workplaces/assignments and which historical corrections
   occur in practice.
5. Walk through the manual submission and official-response handoff and correct
   the state names.
6. Run J1–J4 on the actual supported device/browser and record only blockers,
   ambiguous wording, and missing steps.
7. Name delegated roles and their scope; never share credentials in the review.

## What Pavel must review or authorize

Pavel should not be asked to approve package preferences before evidence exists.
His remaining decisions are:

1. ADR-001/DEC-006–010 are approved. Review a reopened choice only if a critical
   Plan E check fails; approval does not replace tenant-isolation, MFA,
   queue-recovery, storage/download, audit, dependency, and rollback evidence.
2. Activate real-data portal use (DEC-012) only after every authoritative
   real-data gate is checked with synthetic evidence and Plan K recovery evidence.
3. Authorize GitLab remote/CI activation (DEC-016) only as a separate change with
   reviewed credential, runner isolation, rollback, and publication scope.
4. Separately authorize any commit/push, deployment, destructive history action,
   host mutation, or protected-data operation requested at that time.
5. Arrange the Plan R operator update of the seven protected Section 4 columns
   from authoritative sources. Agents must not infer or copy these values.

## Evidence-owned blockers that no recommendation can waive

- Plan E implementation gate: the approved ADR-001 choices still require measured
  synthetic checks before scaffolding.
- Release 1A usability readiness: observed J1–J4 completion first.
- Plan K capacity, alert receipt, TLS, encrypted backup, integrity, and isolated
  restore: sysadmin/operator evidence first.
- AF2 credential provisioning/rotation: a human-controlled, dedicated, revocable,
  single-provider credential is required only when the offline harness and exact
  zero-cost gates authorize a live run. Its value must never enter the repository
  or evidence logs.
- Plan R Section 4 data: authorized operator source update first.
- Real-data activation, publication, deployment, and destructive work: explicit
  authority at the time of action.

## Review response format

Jan may respond with `no operational exceptions` or a short list keyed to J1–J4
and Section 10 item numbers. Pavel may respond only to a completed evidence packet
or an exact authorization request. The delegated approval keeps the synthetic
defaults in force but never counts as Jan's personal factual attestation or
approval of a gated action.
