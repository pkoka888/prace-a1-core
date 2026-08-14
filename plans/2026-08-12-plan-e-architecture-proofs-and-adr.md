# Plan E — Architecture Proofs and ADR-001

**Status:** active
**Milestone:** M1A
**Owner:** product engineering

## Objective

Convert the provisional Django direction into a measured, reproducible architecture decision for Jan's private portal.

## Fixed baseline

- Django 5.2 LTS, Python 3.13, PostgreSQL, Django templates with targeted HTMX.
- Shared database/schema with mandatory `Organization` ownership and membership-based authorization.
- Existing A1 engine behind an internal Python service interface, not a network service.
- Preferred server62 topology: systemd, native Nginx and native PostgreSQL.

## Proofs

1. Compare `django-allauth[mfa]` and `django-two-factor-auth` for forced TOTP, recovery, password reset, session invalidation, rate limiting, Czech/German templates, and protected Admin access.
2. Compare `django-q2` using its ORM broker with Celery/Redis for OCR and A1 jobs. Exercise retries, timeouts, duplicate delivery, cancellation, progress, worker crash/restart, and idempotency.
3. Prove encrypted-filesystem document storage using opaque object keys, quarantine, content/MIME/size checks, malware scanning, authorized Nginx `X-Accel-Redirect` delivery, and audited access. Compare one maintained S3-compatible backend only if a documented migration or operations need justifies it.
4. Prove organization isolation at queryset, view, form, task, Admin, and download layers.
5. Compare `django-auditlog` model diffs with required custom append-only `AuditEvent` behavior for authentication, authorization, document access, exports, reviews, and approvals.
6. Wrap one synthetic employee/assignment through A1 validation, generation, preview, failure reporting, and artifact hashing without importing Django into the A1 engine.
7. Measure installation size, steady/peak memory, CPU, disk/temp use, job duration, recovery behavior, and service count on server62-compatible staging.
8. Produce a Release 1A threat model with assets, actors, trust boundaries, abuse cases, mitigations, residual risks, and owners; exercise synthetic authorization, upload, download, task, audit, and data-flow abuse cases.
9. Review dependency versions, maintenance, licenses, security support, and upgrade constraints; define application observability without PII.
10. Prove deployment and application rollback, including migration limits, worker/version skew, artifact compatibility, and safe resume criteria.

## Decision record

ADR-001 must state selected packages and versions, deployment topology, storage/backend choice, trust boundaries, data flow, alternatives rejected, evidence, operational costs, upgrade policy, rollback path, and unresolved risks. Use declared scoring weights: workflow fit 20%, security/privacy 20%, maintainability 15%, delivery speed 15%, operations 10%, integration 10%, cost 5%, migration/exit 5%. A critical authorization, maintenance, licensing, recovery, or privacy failure rejects a candidate regardless of score; run speed- and cost-doubled sensitivity checks.

The [Google AI Studio frontend review](../docs/prototypes/2026-08-13-google-ai-studio-frontend-review.md)
is provisional comparison evidence only. Its export was rejected for direct import;
ADR-001 must still decide between Django templates/HTMX and a Next.js frontend
with an explicit Django API and operational boundary.

## Exit gate

- Proof results are reproducible from synthetic fixtures.
- Dependency compatibility is confirmed against Python 3.13/Django 5.2.
- Failure and tenant-isolation tests pass.
- Threat model, dependency/license/version review, observability contract, deployment rollback proof, and synthetic abuse/security cases are accepted.
- Sysadmin topology constraints are incorporated.
- ADR-001 is approved before application scaffolding begins.

## Exclusions

No real PII, MinIO default, original `django-q`, Supabase deployment, public frontend selection, or production rollout.
