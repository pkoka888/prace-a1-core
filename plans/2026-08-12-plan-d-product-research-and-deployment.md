# Plan D — Product Research, Architecture Decision, and Deployment Readiness

> **Status: Superseded planning input.** Active execution is governed by
> `roadmap.md` and Plans E–K. References below to disk capacity or backups as
> blockers are historical and must not block synthetic implementation or the
> current real-data policy in `docs/security/real-data-rules.md`.

**Date:** 2026-08-12
**Status:** superseded
**Owner:** operator/product owner
**Scope:** Research and architecture decision for the Jan private-portal pilot deployment.

## 0. Infrastructure assessment

**Host:** server62 — Debian 13, 4 CPU cores, 15 GiB RAM, 8 GiB swap, root at 92% (~7.5 GiB free).
**Blocker:** 7.5 GiB free is insufficient for Docker images, PostgreSQL growth, OCR temp, scans, generated PDFs, and local backups. The sysadmin proposal must require storage expansion or a dedicated encrypted data volume (target ≥50 GiB free) before deployment.

## 1. Architecture recommendation (provisional)

- **Django 5.2 LTS modular monolith** as the target for the Jan pilot.
- **Server-rendered Django + targeted HTMX** for the private portal; no React/Next/Astro in Release 1.
- **A1 implementation as an internal Python package** with a clean service interface, not a microservice.
- **PostgreSQL + background worker**; maintained job-runner candidates must pass Plan E proofs.
- **One named product deployment root** with separate protected subtrees.
- Research Next.js/Astro/Supabase for the later public site as alternatives, not as equal defaults.

## 2. Architecture: Django over Supabase self-hosting

Self-hosted Supabase adds API gateway, Auth, PostgREST, Realtime, Storage, metadata, functions, and operational duties; its docs say backups, HA, monitoring, security, and maintenance remain the operator's responsibility. Disproportionate for the first private workflow. Django's security guidance supports strict upload limits, HTTPS, protected upload handling, isolated database/cache access, and keeping code outside a web-served root.

References:
- Supabase self-hosting: https://supabase.com/docs/guides/self-hosting
- Django security: https://docs.djangoproject.com/en/5.2/topics/security/
- Django supported releases: https://www.djangoproject.com/download/

## 3. Lockable deployment/product choices

1. Private portal: `portal.prace-v-nemecku.tvoje.info`
2. Future public site: `prace-v-nemecku.tvoje.info`
3. Real scans enabled only after the security deployment gate
4. Password plus mandatory TOTP MFA
5. Jan + operator initially, with multi-client boundaries built in

## 4. Review of the Perplexity proposal

Directionally strong. Agree on: narrow Release 1 to Jan's workflow; Django monolith; PostgreSQL; server-rendered portal; existing A1 code as internal package; historical assignments; OCR as proposals requiring human acceptance; organization boundaries; private document delivery; deferring marketplace, Next.js, Supabase, feeds, marketing.

Four changes:
1. Architecture is recommended, not irrevocably selected — run a short time-boxed comparison.
2. Keep the product rooted at `/var/www/prace-v-nemecku.tvoje.info`, with Git-managed source separated from gitignored protected runtime subdirectories for documents, generated artifacts, quarantine, temporary files, secrets, and logs.
3. Do not overbuild provenance into every column — use authoritative employee record, immutable OCR proposals, review decisions, source doc reference, append-only audit events, material field-change history.
4. Compliance research must not block synthetic implementation.

## 5. Provisional architecture

```
Browser → Nginx + TLS + upload limits → Django 5.2 LTS modular monolith:
  Organizations/memberships, Employees, Documents+OCR review, Workplaces+assignments,
  A1 cases, Audit+review tasks, Django Admin.
  Backing: PostgreSQL, background-job worker, protected document storage, A1 engine.
```

UI: Django templates + HTMX; small CSS design system; Czech UI first, German l10n infrastructure; no React/Next.js in Release 1.

## 6. First product: Jan portal — Release 1 capabilities

1. Auth and organization access 2. Employee database 3. Document upload 4. Local OCR 5. OCR review 6. Workplaces and assignments 7. Assignment history 8. Missing-data dashboard 9. Audit history 10. A1 case creation 11. A1 engine integration 12. Preview, review, download.

## 7. Principal records

Organization, User, Membership, Employee, Document, OCRRun, OCRProposal, Workplace, Assignment, A1Case, A1Artifact, ReviewTask, AuditEvent. Current workplace = calculated from active assignments.

## 8. A1 terminology

A1 case, Prepared A1 data, Draft application package, Ready for submission, Submitted, Official certificate received, Rejected, Expired. The generator does not claim to issue official certificates.

## 9. Research disposition

Research A produced a useful provisional Django direction, but its original `django-q`, MinIO, scoring, and package-level conclusions are not accepted. Research B–E are discovery notes, not completed research.

The authoritative review is `docs/research/2026-08-12-research-review-and-plan-update-report.md`. Follow-up work is split into Plans E–J; server work is Plan K. ADR-001 is created only after Plan E proofs pass.

## 10. Repository reorganization plan

Do not push incomplete rewrite. Before implementation: declare current branch as source tree, rebuild sanitized history, preserve A1 engine/template/layouts/tests/fixtures, place A1 code under internal package boundary, remove files only after reachability check, move planning reports to dated archive, replace sprawling roadmap, correct private-input policies, verify clean clone/tests before force-push.

## 11. Documentation authority

SOUL.md, prd.md, roadmap.md, AGENTS.md, docs/decisions/, docs/research/, and
future operations runbooks when an active plan creates them.

## 12. Sysadmin proposal for server62

Blocked by disk (~7.5 GiB free at 92%). Require sysadmin: increase storage or attach encrypted capacity for protected runtime subdirectories under `/var/www/prace-v-nemecku.tvoje.info`; use dedicated non-login service accounts; confirm native PostgreSQL/Nginx/systemd; bind internal services locally; configure Nginx+TLS; enforce upload limits; provide encrypted off-server backups and restore testing; SMTP, monitoring, malware scanning, secrets separation, and patching. Do not expose the project root, database, storage, Admin, or monitoring directly.

## 13. Delivery roadmap

The authoritative milestone definitions are in `roadmap.md`: M0 recover control → M1 Jan discovery and architecture proofs → M2 synthetic foundation → M3 employee/document/OCR/assignment workflow → M4 A1 preparation → M5 controlled real-data pilot → M6 public recruitment product.

## 14. Research findings

Treat `docs/research/2026-08-12-research-findings.md` as provisional and read it together with `docs/research/2026-08-12-research-review-and-plan-update-report.md`.
