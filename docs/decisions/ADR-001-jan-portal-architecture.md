# ADR-001 — Jan Portal Architecture

**Status:** proposed (evidence structure in place; proofs awaiting validation)
**Owner:** product engineering
**Approver:** Pavel
**Milestone:** M1A
**Date:** 2026-08-13 (synthetic evidence placeholder)

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

- [MFA comparison](evidence/plan-e/01-mfa-comparison.md)
- [Queue comparison](evidence/plan-e/02-queue-comparison.md)
- [Storage comparison](evidence/plan-e/03-storage-comparison.md)
- [Audit comparison](evidence/plan-e/04-audit-comparison.md)
- [Threat model](evidence/plan-e/05-threat-model.md)
- [Deployment/rollback](evidence/plan-e/06-deployment-rollback.md)
- [Cockpit asset](../../docs/prototypes/roadmap-portal/planning-data.js)

## Required evidence before acceptance

- Synthetic proof results validated (above documents are placeholders)
- Threat model reviewed by security team
- Deployment/rollback tested on staging
- Dependency versions locked in requirements.txt
- Upgrade path documented

## Consequences

- Single-database background processing (no Redis)
- Filesystem-based document delivery (no S3)
- Custom audit model (not django-auditlog)
- Monolithic but organized by Django apps

## Exit gate

Plan E must attach reproducible synthetic proof results, threat model, selected
versions/licenses, weighted comparison and sensitivity results, application
observability, deployment rollback proof, dependency review, and unresolved risks.

**Approval:** Pending — synthetic evidence placeholders exist; real measurements await.