# Plan F — Jan Workflow Discovery

**Status:** active
**Milestone:** M1A
**Owner:** product owner

## Objective

Define the real Jan/operator workflow and Release 1 acceptance criteria before modeling or implementing it.

## Discovery

- Before asking Jan or the operator, research applicable domain, workflow, security, accessibility, and A1 practices using bounded lower-cost research agents where available. The primary agent validates evidence and repository fit.
- Prepare one illustrated decision brief containing a recommended default, meaningful variants, trade-offs, data/state flows, permission examples, and synthetic acceptance examples.
- Ask Jan and the operator to approve or annotate the prepared defaults; do not begin with an open-ended requirements interview.
- Inventory current employee sources, scans, manual corrections, spreadsheets/scripts, workplace records, A1 evidence, outputs, approvals, and handoffs without copying PII into research notes.
- Identify worker/activity types, required and optional document types, identity fields, assignment fields, overlapping/ended/future assignments, missing-data handling, corrections, departures, re-hires, and exceptional cases.
- Clarify who uploads, reviews OCR, changes authoritative fields, creates an A1 case, approves a draft, records submission, records an official response, and downloads/exports artifacts.
- Distinguish the current self-employed multi-state cohort from employee or other future profiles; define profile-specific evidence rather than inference.

## Deliverables

- A versioned solution/decision brief that minimizes unanswered questions.
- Current and desired workflow diagrams.
- Role/responsibility matrix for Jan and operator.
- Field/document necessity inventory marked confirmed, optional, unknown, or counsel-dependent.
- State definitions for employee, document/OCR review, assignment, review task, and A1 case.
- Prioritized Release 1 stories and synthetic acceptance scenarios, including failures and corrections.
- Migration inventory describing legacy source-to-record mapping without embedding real values.
- Versioned Release 1A acceptance scenarios covering success, data-quality states, corrections, authorization failures, interruption, recovery, retention/deletion, and stale A1 packages.
- A scenario-to-role/requirement/audit-event/test traceability matrix with an owner and evidence link for every row.

## Exit gate

Jan and operator approve or annotate the prepared workflows, roles, required information, terminology, exception cases, and acceptance scenarios. Unresolved legal questions are linked to Plan J and do not become assumptions in the schema.

## Exclusions

No UI implementation, public jobs/candidates, pricing decision, legal conclusions, real-data migration, or automatic A1 eligibility decision.
