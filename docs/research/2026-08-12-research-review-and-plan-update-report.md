# Research Review and Final Plan Update Report

> **Status: Accepted historical disposition, not execution authority.** This
> report explains how earlier findings were judged. Later `AGENTS.md`,
> `docs/security/real-data-rules.md`, `roadmap.md`, and active plans prevail where
> decisions changed, including backups/capacity being non-blocking work.

**Date:** 2026-08-12
**Reviewed:** Plan D, its Research A–E findings, the current repository state, and selected primary sources
**Purpose:** Decide which findings may update the authoritative plans and which require correction or follow-up

## Executive decision

The research supports the product direction and a provisional Django architecture, but it is **not complete or ADR-ready as written**. Architecture Research A is a useful shortlist with two material dependency errors. Research B–E are preliminary notes rather than completed market, UX, marketing, or legal studies.

Proceed with Django 5.2 LTS, PostgreSQL, server-rendered templates with targeted HTMX, shared-schema organization scoping, and the existing A1 engine as an internal Python package. Keep package-level choices for authentication, jobs, audit, and document storage provisional until focused proofs of concept pass.

Do not promote the current `django-q`, MinIO, retention, legal-basis, pricing, competitor, channel-ranking, Astro, or “research complete” conclusions into `prd.md`, `roadmap.md`, `AGENTS.md`, `SOUL.md`, or ADR-001.

## Findings disposition

### Accept and carry into the final plans

- Release 1 is the private Jan + operator portal at `portal.prace-v-nemecku.tvoje.info`; the apex domain remains reserved for the later public site.
- Use a Django 5.2 LTS modular monolith with PostgreSQL and Python 3.13 as the provisional implementation baseline.
- Use Django templates and targeted HTMX for Release 1; do not add React, Next.js, Astro, Supabase, or a network A1 microservice to the pilot.
- Model organization membership from day one using a shared database/shared schema. Every business record is organization-owned and every access path is explicitly authorized and tested.
- Model workplaces historically through assignments; derive “currently working at” from active assignment dates and status.
- Treat OCR as an untrusted proposal workflow. Accepted values, the source document, reviewer, decision, and material change history remain traceable.
- Package the current A1 code behind an internal Python service boundary while preserving its fail-closed validation and approval rules.
- Require password + TOTP MFA, synthetic-only development, and a security gate before real scans enter the new application.
- Use systemd, native Nginx, and native PostgreSQL as the preferred server62 deployment baseline, subject to a sysadmin review.
- Treat the measured root filesystem state (92% used, about 7.5 GiB free) as a deployment blocker. Capacity expansion, encrypted data storage, and off-server backups precede production data.
- Use A1 terminology that distinguishes prepared application data, draft package, submission, and an official certificate received from the authority. The product does not issue certificates.

### Keep provisional and prove before ADR-001

- **Authentication:** Compare current `django-allauth[mfa]` with `django-two-factor-auth`. Verify TOTP enrollment, recovery codes, forced MFA, password reset, session invalidation, Czech/German templates, rate limiting, and protected Django Admin. `django-allauth` is current and supports Django 5.2/Python 3.13, but its admin requires explicit secure-login integration.
- **Background jobs:** Replace the abandoned original `django-q` candidate with maintained `django-q2`, plus one PostgreSQL/Redis-backed alternative. Test process isolation, retries, timeouts, duplicate delivery, cancellation, progress, crash recovery, and idempotency for OCR and A1 generation. Select only after the proof of concept.
- **Audit:** `django-auditlog` may supply model diffs, but a purpose-built append-only `AuditEvent` is still required for authentication, authorization failures, document reads/downloads, exports, approvals, and operational actions. Prove actor attribution and tamper/retention controls.
- **Document storage:** Start the comparison with an encrypted filesystem volume plus opaque keys and authorized Nginx `X-Accel-Redirect` delivery. Compare it against one maintained S3-compatible option only if migration or operational requirements justify the extra service. Keep Django's storage abstraction so the backend can change.
- **Deployment:** Validate active services, DNS, certificates, filesystem/mount layout, resource budgets, SMTP, malware scanning, monitoring, backup destination, and restore procedure. Installed packages alone do not establish readiness.
- **Public frontend:** Defer Astro versus Next.js versus Django until the public jobs/applications requirements and content workflow are defined. No public-stack choice belongs in ADR-001 for the Jan portal.

### Reject or correct

- **Original `django-q`: reject.** Version 1.3.9 was released in 2021 and was tested against Python 3.7–3.9 and Django 2.2/3.2, not this stack. Research `django-q2`, not `Koed00/django-q`.
- **MinIO as the high-confidence default: reject.** The community repository was archived in April 2026, distribution is source-only, and licensing is AGPLv3. It adds a service without proven pilot value. Do not prescribe MinIO, S3 SSE-KMS, buckets, or signed URLs in the Release 1 plan.
- **“Weighted” score: reject.** The table has no declared weights, criterion definitions, evidence mapping, blocker thresholds, cost estimates, or sensitivity analysis. Replace it with a reproducible decision matrix after proofs of concept.
- **“Research A–E complete”: reject.** Architecture is partially complete; market, competitor, UX, marketing, and legal work remain discovery inputs.
- **Market classifications: correct.** Kimeta is a general German job-search engine, not a Czech/Polish cross-border worker platform. Remove `MakeIt.ch` unless its identity and relevance are established; do not confuse it with the German government portal “Make it in Germany.” Remove unsupported portal rankings and scale claims.
- **Marketing effectiveness and pricing: remove pending evidence.** “High/medium” channel rankings, search-volume claims, placement percentages, and proposed discounts have no cited dataset or field validation. Treat them as hypotheses for experiments and Jan/operator interviews.
- **Legal bases and retention: remove as conclusions.** Do not encode Article 6/9 bases or a universal seven-year retention period. Determine controller, joint-controller, processor, purpose, necessity, lawful basis, and retention separately for each workflow and data category with Czech/German counsel.
- **Special-category assumptions: correct.** An insurance-card record is not automatically health-status data; an identity-card photo is not automatically biometric special-category data unless processed for unique identification. Conversely, full document copies may still be excessive. Perform necessity and minimization analysis rather than applying blanket Article 9 labels.
- **Partner roles: reopen.** German partners are not “likely processors” by default; they may be independent or joint controllers depending on their purposes and decisions.
- **DPIA/DPO: make conditional.** Require a documented DPIA screening and DPO assessment; do not state that either is automatically mandatory without the factual/legal test.
- **Upload settings: correct.** `FILE_UPLOAD_MAX_MEMORY_SIZE` controls memory-versus-temporary-file handling; it is not an upload-size security limit, and its documented default is about 2.5 MB, not 26 MB. Enforce limits at Nginx and application validation, with MIME/content checks and quarantine.
- **HSTS: stage safely.** Do not enable preload/include-subdomains until every affected hostname is permanently HTTPS-ready.
- **A1 workflow wording: correct.** Replace “A1 issuance portal” and UI actions implying direct OSSZ submission unless a supported submission integration is later proven.

## Missing research deliverables

Create separate, bounded plans instead of marking all tracks complete:

1. **Architecture proof and ADR plan** — authenticate/MFA comparison, job runner comparison, protected-storage comparison, authorization strategy, A1 package boundary, deployment topology, measured resource budget, failure tests, and ADR-001.
2. **Jan workflow discovery plan** — interview Jan and operator; document actual worker types, required documents, assignment lifecycle, current spreadsheet/script handoffs, exception cases, A1 responsibilities, and pilot acceptance scenarios. Do not generalize the current self-employed multi-state A1 cohort to all future workers.
3. **German market and competitor plan** — identify real direct Czech/Slovak-to-Germany competitors, target occupations and regions, service models, pricing evidence, trust claims, German employer workflow, and primary labor-market data. Keep job-feed/posting research separate and deferred to the public-product milestone.
4. **UX/copy research plan** — name and inspect representative global and regional products, record specific patterns with dated sources, test low-fidelity Jan workflows, define accessibility and Czech/German content principles, and avoid copying protected designs or text.
5. **Marketing/business validation plan** — turn channel and revenue claims into hypotheses, define interviews and low-cost experiments, record cost/conversion assumptions, and select positioning only after evidence.
6. **Data-protection/legal plan** — build a data-purpose matrix and questions for counsel covering document necessity, roles, lawful basis, special categories, retention triggers, access, cross-border disclosure, DSRs, incidents, backups, and A1 records.
7. **Sysadmin readiness plan** — give the sysadmin a requirements specification and require an as-built report; do not prescribe exact mount, backup, or service configuration before available storage and host topology are confirmed.

## Required updates to authoritative documents

### `roadmap.md`

- Replace the current audit/research loop with milestone outcomes: M0 repository and server recovery; M1 Jan discovery + architecture proofs; M2 synthetic foundation; M3 employee/document/assignment workflow; M4 A1 preparation; M5 controlled real-data pilot; M6 public recruitment product.
- Mark Research A as “provisional architecture recommendation; dependency corrections pending.” Mark Research B–E as incomplete follow-up work.
- Put decision gates before scaffolding: approved ADR-001, sysadmin as-built readiness, threat model, synthetic acceptance journeys, and legal/privacy questions registered. Legal research may run in parallel and blocks real data, not synthetic implementation.
- Separate project-product progress from historical A1 remediation and from Git-history cleanup.

### `prd.md`

- Make Jan's portal the first product release and define its user-visible success criteria.
- Describe workers, organizations, documents, OCR review, workplaces/assignments, A1 cases, artifacts, review tasks, and audit events at behavior level.
- Explicitly support different employment/activity profiles; do not infer an employee A1 profile from the current self-employed multi-state cohort.
- Keep public jobs, candidate accounts, external feeds, marketing automation, finance, and multiple partner self-onboarding outside Release 1.
- Keep revenue model, reservations, candidate authentication, partner visibility, and public frontend as later open decisions.

### `AGENTS.md`

- Keep it short: authoritative product documents, privacy boundary, synthetic-data rule, tenant authorization rule, A1 safety invariants, test expectations, and links to detailed workflows.
- Do not encode provisional libraries, unverified legal bases, retention periods, marketing claims, or sysadmin commands.
- Reconcile the current `A1_PRIVATE_DIR` policy with the physical data location. Policy was edited to point at repository-root `a1/`, `scans/`, `ocr/`, and `evidence/`, but the existing real inputs remain elsewhere; do not claim migration completion until files, permissions, backup, and commands are verified.

### `SOUL.md`

- Create it from validated product principles, not unsupported competitor claims: calm, practical, trustworthy, human-reviewed, transparent status, no false promises, Czech-first operator clarity, precise German partner communication, and respectful handling of workers and their documents.
- Keep UI component rules and legal text out of `SOUL.md`; place them in design and compliance documentation.

### Planning index and research register

- Replace the obsolete PaddleOCR section in `plans/INDEX.md`; it references removed scripts and plans and currently presents a dead workflow as actionable.
- Index separate active plans with statuses, owners, prerequisites, and exit gates.
- Downgrade the current findings document to **“provisional findings requiring correction”** and link this review beside it.
- Maintain a source register that distinguishes primary, official, vendor, repository, secondary, inaccessible, and inferred claims. A URL and access date alone do not validate a conclusion.

## Repository and rollout controls

- Do not push `/home/pavel/a1-rewrite.git`; its feature-branch tree is not identical to the intended current tree.
- Review all dirty worktree changes together. Current changes include `AGENTS.md`, `.gitignore`, the A1 skill, the planning index, Plan D, and both research documents; the change summary that mentions only two new files plus the index is incomplete.
- Do not combine the history rewrite, operational-data relocation, architecture documentation, and new application scaffold in one commit or rollout.
- Before enabling real data, require TLS, MFA, organization-isolation tests, protected storage, quarantine and malware checks, authorized download logging, encrypted backup, successful restore, incident procedure, and operator approval.

## Evidence used for this review

- Django supported versions and security guidance: https://www.djangoproject.com/download/ and https://docs.djangoproject.com/en/5.2/topics/security/
- Original django-q release/compatibility: https://pypi.org/project/django-q/
- Maintained django-q2 fork: https://pypi.org/project/django-q2/
- Current django-allauth compatibility and MFA/rate-limit documentation: https://pypi.org/project/django-allauth/ and https://docs.allauth.org/
- MinIO archive, distribution, and license status: https://github.com/minio/minio
- Supabase self-hosting responsibilities: https://supabase.com/docs/guides/self-hosting
- German shortage analysis: https://www.arbeitsagentur.de/presse/2025-25-qualifizierte-fachkraefte-weiterhin-gesucht
- BA HR-BA-XML posting interface: https://www.arbeitsagentur.de/unternehmen/arbeitskraefte/hr-ba-xml-schnittstelle
- Kimeta product positioning: https://www.kimeta.de/
- German employee-data rule: https://www.gesetze-im-internet.de/bdsg_2018/__26.html
- Czech DPA guidance on identity-document necessity and minimization: https://uoou.gov.cz/media/clanky/dokumenty/prokazovani-totoznosti-a-zpracovani-osobnich-udaju-1.pdf

## Final recommendation

Approve the **direction**, not the current dependency bundle or claims of completed research. The next authoritative update should lock Django 5.2 + PostgreSQL + Django templates/HTMX + internal A1 package + shared-schema organization model + native server62 deployment as the provisional architecture. It should explicitly leave authentication package, task runner, audit package, document backend, public frontend, legal bases, retention, market positioning, and revenue model subject to the focused plans above.
