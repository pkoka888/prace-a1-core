# ADR-001 — Jan Portal Architecture

**Status:** accepted architecture direction; synthetic technical validation passed
**Owner:** product engineering
**Approver:** Pavel
**Milestone:** M1A
**Decision date:** 2026-08-17
**Machine-readable approval:** [`planning/approvals.json`](../../planning/approvals.json)

## Context

Release 1A needs one measured architecture for protected worker documents, OCR
proposals, assignments, A1 cases, audit, and organization-scoped authorization.

## Decision

Django 5.2 LTS on Python 3.13 as a modular monolith with PostgreSQL, Django
templates plus targeted HTMX, a background worker, protected filesystem storage,
and the existing A1 engine behind a Django-independent Python interface.

### Selected packages (synthetic comparison)

| Component | Selection | Rationale |
|-----------|-----------|-----------|
| Authentication + MFA | django-allauth[mfa] | TOTP support, Django 5.2 compatible, active maintenance |
| Background queue | django-q2 (ORM broker) | No external Redis; integrated with Django; meets fail-closed A1 requirements |
| Protected storage | Encrypted filesystem + Nginx X-Accel-Redirect | Zero external dependencies; audit trail via Nginx logs |
| Audit logging | Custom append-only AuditEvent model | Organization-scoped, covers auth/authz/document access/export/approvals |

## Evidence links

Publication note (2026-09-07): the six comparison/evidence files below are
local, unpublished references. A clean clone does not contain them; this note
does not revalidate or alter the historical architecture decision.

- MFA comparison — local reference `evidence/plan-e/01-mfa-comparison.md` (unpublished)
- Queue comparison — local reference `evidence/plan-e/02-queue-comparison.md` (unpublished)
- Storage comparison — local reference `evidence/plan-e/03-storage-comparison.md` (unpublished)
- Audit comparison — local reference `evidence/plan-e/04-audit-comparison.md` (unpublished)
- Threat model — local reference `evidence/plan-e/05-threat-model.md` (unpublished)
- Deployment/rollback — local reference `evidence/plan-e/06-deployment-rollback.md` (unpublished)
- [Cockpit asset](../../docs/prototypes/roadmap-portal/planning-data.js)

## Validation result

The eight machine-readable checks pass in the hash-bound architecture manifest;
the implementation gate is open for the synthetic M2 scaffold. This does not
claim production staging, host capacity, malware operations, encrypted backup or
restore evidence. Those remain separate Plan K/activation requirements.

## Consequences

- Single-database background processing (no Redis)
- Filesystem-based document delivery (no S3)
- Custom audit model (not django-auditlog)
- Monolithic but organized by Django apps

## Implementation gate

Plan E must attach reproducible synthetic proof results, threat model, selected
versions/licenses, weighted comparison and sensitivity results, application
observability, deployment rollback proof, dependency review, and unresolved risks.

**Human approval:** Accepted by Pavel on 2026-08-17 for Django and every selected
component above. This approves the architecture direction. It does not assert that
the checks passed and does not authorize deployment or real-data activation.

**Technical validation:** Passed for the bounded synthetic proof. The approval
validator and automated M2 scaffold gate report open; deployment and real-data
activation remain blocked.
