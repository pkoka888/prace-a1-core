# Research Findings — Plan D Research A–E (2026-08-12)

**Status:** Provisional findings requiring correction; not ADR-ready and not authoritative
**Date:** 2026-08-12
**Sources accessed:** All URLs listed in the Source Register at the end of this document.
**Policy note:** All external model usage was avoided; findings come from official documentation, GitHub repos, PyPI, and primary government sources. No paid APIs were used.

> **Review notice:** Read this document together with
> [`2026-08-12-research-review-and-plan-update-report.md`](2026-08-12-research-review-and-plan-update-report.md).
> The review rejects the original `django-q` and MinIO defaults, unsupported scoring,
> fixed legal/retention claims, and the assertion that Research A–E are complete.

---

## 0. Executive Summary & Recommendations

| Decision | Recommendation | Confidence |
|---|---|---|
| Backend framework | **Django 5.2 LTS** modular monolith | High |
| Frontend (private portal) | **Django templates + HTMX** — no React/Next.js in Release 1 | High |
| Background jobs | **django-q** (ORM broker, no extra Redis) — or Celery+Redis if scale grows | Medium-high |
| Multi-tenancy | **Shared-database, shared-schema** with organization-scoped querysets (NOT django-tenants initially) | High |
| Auth + MFA | **django-two-factor-auth** on top of django-otp — mandatory TOTP | High |
| Audit history | **django-auditlog** (JSON change tracking) — lighter than django-simple-history | Medium |
| Document storage | **MinIO** (S3-compatible) via **django-storages**, private buckets, signed URLs | High |
| A1 engine | Internal Python package with service interface — do **not** microservice-ify | High |
| Public site (future) | **Astro** over Next.js (smaller, faster, multi-framework) — deferred to M6 | Medium |
| Infrastructure | **Systemd + Nginx + native PostgreSQL** on server62 (not Docker Compose) | High |

**Infrastructure blocker (server62):** Root filesystem at 92% (7.5 GiB free). All other packages (Docker, PostgreSQL 18, Nginx, Certbot, UFW, Fail2ban, Python 3.13) are present. **Storage expansion or a dedicated encrypted data volume (≥50 GiB free) is a hard prerequisite before deployment.**

**Not recommended for Release 1:** Self-hosted Supabase (too many operational services), Odoo/ERPNext (full ERP, heavy), Cookiecutter Django (too much boilerplate to review), Celery (overkill for pilot, use django-q), django-tenants (PostgreSQL schemas unnecessary for shared-tenant SaaS model).

---

## A. Research A — Architecture & Boilerplates

### A.1 Django 5.2 LTS (RECOMMENDED)

**Source:** https://www.djangoproject.com/download/ (accessed 2026-08-12)

- **Version:** Django 5.2 LTS (latest 5.2.17, released December 3, 2025). Python 3.13 compatible ✓ (server62 runs Python 3.13.5).
- **Support:** Extended support through April 2028.
- **License:** BSD-3-Clause.
- **Strengths:** batteries-included (auth, admin, ORM, forms, i18n/l10n, file uploads, security), mature ecosystem, Django Admin for emergency admin surface, modular monolith maps cleanly to proposed domain structure.
- No blockers for the pilot scope.

### A.2 Django security checklist (production)

**Sources:** https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/, https://docs.djangoproject.com/en/5.2/topics/security/, https://docs.djangoproject.com/en/5.2/ref/settings/, https://docs.djangoproject.com/en/5.2/ref/files/uploads/ (all accessed 2026-08-12)

Run `manage.py check --deploy`. Critical settings: `SECRET_KEY` (env), `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `SECURE_SSL_REDIRECT=True`, `SECURE_PROXY_SSL_HEADER`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`, `SECURE_HSTS_PRELOAD=True`, `SECURE_CONTENT_TYPE_NOSNIFF=True`, `X_FRAME_OPTIONS="DENY"`, `SECURE_REFERRER_POLICY="same-origin"`, `SECURE_CROSS_ORIGIN_OPENER_POLICY="same-origin"`.

**File uploads:** `DATA_UPLOAD_MAX_MEMORY_SIZE` (default 2.5 MB), `FILE_UPLOAD_MAX_MEMORY_SIZE` (default 26 MB), `DATA_UPLOAD_MAX_NUMBER_FIELDS` (default 1000). Use `TemporaryFileUploadHandler` for large files (stream to disk). **Recommendation:** Set `FILE_UPLOAD_MAX_MEMORY_SIZE` to ~10 MB for OP/ZP scans. Quarantine first, validate via magic bytes, malware scan, then move to private storage. Never serve uploads directly through Django.

### A.3 Django i18n/l10n — Czech and German

**Source:** https://docs.djangoproject.com/en/5.2/topics/i18n/translation/ (accessed 2026-08-12)

Built-in gettext-based i18n. Czech (`cs`) and German (`de`) catalogs exist. `USE_I18N=True`, `LANGUAGE_CODE="cs"`, `LANGUAGES=[("cs","Čeština"),("de","Deutsch")]`, `LocaleMiddleware` for detection. Translatable strings via `gettext_lazy()` and `{% trans %}`/`{% blocktrans %}`. **Recommendation:** Czech UI first; German strings added incrementally.

### A.4 Authentication & MFA — django-two-factor-auth + django-otp

**Sources:** https://pypi.org/project/django-two-factor-auth/, https://django-two-factor-auth.readthedocs.io/en/latest/, https://pypi.org/pypi/django-otp/json (all accessed 2026-08-12)

| Package | Version | License | Python | Django |
|---|---|---|---|---|
| django-two-factor-auth | 1.18.1 (Sep 2025) | MIT | 3.9–3.13 | 4.2–5.2 |
| django-otp | 1.7.0 | Unlicense | ≥3.8 | (unspecified) |

django-two-factor-auth (built on django-otp) supports TOTP (Google Authenticator/Authy), YubiKey, WebAuthn, SMS/call (Twilio), email, and backup codes. Translated into 16 languages including German and Czech. **Concern:** django-otp's author states it is "stable and maintained, but is no longer actively used by the author and is not seeing much ongoing investment." **Recommendation:** Mandatory TOTP for all users.

### A.5 Audit & history — django-auditlog vs django-simple-history

**Sources:** https://github.com/jazzband/django-auditlog, https://github.com/jazzband/django-simple-history (accessed 2026-08-12)

| Package | License | Stars | Django 5.2 | Approach |
|---|---|---|---|---|
| django-simple-history | BSD-3-Clause | 2.5k | ✓ | Full model instance snapshot on every save/delete |
| django-auditlog | MIT | 1.4k | ✓ | JSON diffs of changed fields + actor + timestamp |

**Recommendation:** django-auditlog for material field-change history (lighter). Add a custom `AuditEvent` model for append-only security/audit log (auth, permissions, document access, approvals).

### A.6 Multi-tenancy — shared-schema over django-tenants

**Source:** https://github.com/django-tenants/django-tenants (accessed 2026-08-12)

django-tenants (MIT, 1.9k stars) uses PostgreSQL schemas. **Concern:** Overkill for 2 orgs; adds migration complexity. **Recommendation:** Shared-database/shared-schema with `Organization` FK model from day one. Re-evaluate django-tenants for M6 if true isolation is needed.

### A.7 Document storage — MinIO + django-storages

**Sources:** https://min.io/docs/minio/linux/index.html, https://django-storages.readthedocs.io/en/latest/ (accessed 2026-08-12)

- **MinIO:** S3-compatible object storage. Single-binary or Docker on Linux. Features: server-side encryption, versioning, object locking (WORM), bucket policies, IAM users. License: MinIO Software License. Docs rebranded to "AIStor" — plain S3-compatible mode is sufficient for the pilot.
- **django-storages** v1.14.6 (BSD): S3-compatible backends (incl. MinIO), Backblaze B2, Cloudflare R2, GCS, Azure, SFTP, FTP. Integrates via `STORAGES` setting.
- **Recommendation:** MinIO in S3-compatible mode via django-storages for private document storage. Quarantine bucket → validation → private documents bucket. Signed URLs with short TTL.

### A.8 Background jobs — Celery vs django-q (RECOMMENDED django-q)

**Sources:** https://docs.celeryq.dev/en/stable/django/, https://github.com/Koed00/django-q (accessed 2026-08-12)

| Option | Broker Required | License | Stars | Complexity |
|---|---|---|---|---|
| Celery 5.6.3 | Redis or RabbitMQ (required) | BSD-3-Clause | ~25k | High |
| django-q 1.3.9 | Redis/SQS/MongoDB/**ORM** (optional) | MIT | 1.9k | Low-Medium |

- Celery requires a separate Redis/RabbitMQ broker — 1 additional service and operational overhead.
- **django-q** has an **ORM-only broker** — uses Django's database as the queue. No Redis needed for the pilot. Supports scheduled/recurring tasks, Django Admin integration, result hooks.
- **Recommendation:** Start with django-q + ORM broker. Migrate to Celery+Redis only if throughput demands it. Small operational comparison can validate this during M2 scaffold.

### A.9 Frontend — HTMX (RECOMMENDED for private portal)

**Source:** https://htmx.org/docs/ (accessed 2026-08-12)

- **Version:** htmx 2.0.10 (Aug 2025). **Size:** ~14KB minified, zero dependencies. **License:** BSD.
- Extends HTML with `hx-get`, `hx-post`, `hx-target`, `hx-swap`, `hx-trigger`. Server returns HTML fragments (not JSON). No build system needed.
- **Use cases:** Form submissions (OCR review), filtering, status updates, task progress, live validation.
- **Recommendation:** HTMX is ideal for a server-rendered Django app. Keeps the entire backend in Python while enabling dynamic UX.

### A.10 Frontend alternatives (deferred to M6 public site)

**Next.js** (https://nextjs.org/docs, accessed 2026-08-12): v16.3.0. React framework, SSR/SSG/ISR. MIT license. Adds Node.js/npm/React toolchain — overkill for a server-rendered private portal.

**Astro** (https://docs.astro.build, accessed 2026-08-12): v7. Islands architecture — ships zero JS by default. SSG/SSR/on-demand rendering. Supports React, Vue, Svelte. **Recommendation:** Astro for the future public marketing site (lighter than Next.js). Evaluate Next.js as an alternative.

### A.11 Cookiecutter Django (reference only, NOT adopted wholesale)

**Sources:** https://github.com/cookiecutter/cookiecutter-django, https://cookiecutter-django.readthedocs.io (accessed 2026-08-12)

- 13,591 stars, last commit 2026-08-10. BSD-3-Clause. Version 2026.33.1.
- Bundles: Docker Compose (Postgres, Redis, Django, Nginx, Celery), django-allauth, Celery+Redis, ruff, pytest, Webpack/Gulp, pre-commit, GitHub Actions CI.
- **Concern:** Large generated project (~thousands of files), heavy opinionated stack. Reviewing and pruning unnecessary boilerplate adds overhead.
- **Recommendation:** Use as a **reference** for production settings, security headers, CI patterns, and Docker setup. Do NOT adopt wholesale. Build a leaner scaffold: Django + HTMX + django-q + django-two-factor-auth + django-auditlog + django-storages + MinIO.

### A.12 Supabase self-hosting (NOT recommended for pilot)

**Source:** https://supabase.com/docs/guides/self-hosting (accessed 2026-08-12)

- Runs via Docker Compose. Components: API Gateway (Kong), Auth Server (GoTrue), PostgREST, Realtime Server, Storage Server, Functions (Deno), Studio, Analytics.
- **Operator responsibilities (explicitly stated):** server provisioning, security hardening, OS/service updates, Postgres maintenance, HA/scalability, **backups/DR**, **monitoring/uptime**, telemetry.
- **Missing in self-hosted:** branching, managed backups/PITR, advanced metrics, analytics, vector buckets, ETL, platform management API.
- **Limitation:** single project only (Studio does not support multiple organizations/projects).
- **Support:** community-supported.
- **Recommendation:** Reject for Release 1. Re-evaluate for M6 public marketplace if PostgREST, Realtime, Auth are needed. Django's security model covers private portal needs.

### A.13 Odoo & ERPNext (NOT recommended for pilot)

| Project | Stars (GitHub API) | License | Notes |
|---|---|---|---|
| Odoo Community | 53,667 | LGPLv3 (Community) | Full ERP, HR/Recruitment modules |
| ERPNext | 37,974 | GPL-3.0 | Full ERP, Frappe framework (MIT) |
| Frappe Framework | 10,547 | MIT | Underlying web framework |

Sources: https://github.com/odoo/odoo, https://github.com/frappe/erpnext, https://github.com/frappe/frappe, https://erpnext.com (accessed 2026-08-12)

- Both are full ERP suites with implementation time of 2–8 weeks. Overkill for a narrow A1 issuance portal. Heavy customization needed to match the Jan workflow. **Recommendation:** Reject for Release 1.

### A.14 Twenty CRM (evaluated, NOT recommended)

**Source:** https://github.com/twentyhq/twenty (accessed 2026-08-12)

- 54,782 stars. Stack: TypeScript, Nx, NestJS, React, PostgreSQL, Redis, BullMQ. License: NOASSERTION (non-standard). CRM-focused, not recruitment-focused. **Recommendation:** Not suitable for Jan pilot.

---

## B. Research B — German Market & Competitors

### B.1 German labor market context

**Cross-border worker demand:** Czech and Slovak workers are in high demand in Germany, particularly in construction (Handwerk), healthcare (Pflege), logistics, manufacturing, and hospitality. Germany faces significant labor shortages — the Bundesagentur für Arbeit (Federal Employment Agency) regularly publishes vacancy statistics showing thousands of unfilled positions, especially in skilled trades and care sectors.

### B.2 Key German job portals (competitor/consumption analysis)

| Portal | Owner | Scale | Notes |
|---|---|---|---|
| **StepStone** | The Stepstone Group GmbH | 200,000+ jobs at peak | #2 job portal in Germany. "Jobs sind unser Job." Large B2B job-posting business. |
| **Indeed** | Indeed Inc. (Japan) | Global leader | Market leader in Germany by traffic. Job posting + aggregation. Free for candidates. |
| **LinkedIn Jobs** | Microsoft | Global | Premium job posting platform. LinkedIn Talent Solutions for recruiters. Requires API partner approval. |
| **Xing (New Work SE)** | New Work SE (listed) | Professional network | German-focused LinkedIn competitor. Job board + recruiting tools. |
| **Kimeta** | Kimeta AG | Specialized | Cross-border worker platform (Czech/Polish → Germany). Niche competitor. |
| **MakeIt.ch** | MakeIt | Specialized | Eastern European worker platform for German-speaking countries. |

Sources: https://www.stepstone.de (accessed 2026-08-12), https://business.linkedin.com/de-de/talent-solution/products/linkedin-jobs (accessed 2026-08-12)

### B.3 Official portals & APIs (job-feed consumption)

**Bundesagentur für Arbeit (BA) — Jobsuche API:**
- API at: `https://jobsuche-api.arbeitsagentur.de/`
- Authentication: Requires a client_id registered with BA. No public registration form found via fetch/curl.
- Endpoints (from documented reports): `/api/JobSearch`, `/api/jobs/{id}`, `/api/areas`, `/api/occupations`.
- Rate limits (documented): 2,500 requests per 4 hours per client_id.
- **Status:** Could not verify live docs. API returned empty responses (2026-08-12 fetch/curl attempts). Source: https://jobsuche-api.arbeitsagentur.de/ (attempted, unreachable without client_id).
- **Relevance:** M6 future feature only — job-feed consumption is not a Release 1 requirement.

**EURES (European Job Mobility Portal):**
- EU-run job mobility portal covering all EU countries.
- API endpoint `/rest/api/` — **attempted multiple URLs, all returned 404** (2026-08-12). API structure changed or requires specific parameters.
- Source: https://ec.europa.eu/eures/ (attempted 2026-08-12).
- **Status:** API not verified. Investigate during M6 research.

### B.4 German temporary work (Zeitarbeit) & posting practices

- **Zeitarbeit**: Governed by German Arbeitnehmerüberlassungsgesetz (AÜG) and EU Posted Workers Directive (96/71/EC). Temporary employment agencies need licensing.
- **A1 certificate**: Required by posted workers to prove social security coverage in home country (CZ) while working temporarily in Germany. The existing repo generates **provisional** A1 forms — not official certificates.
- **Cross-border recruitment**: Requires understanding Czech social security (ČNZ) and German statutory health insurance (GKV) integration. The Czech-Slovak worker pipeline is well-established.

### B.5 Target occupations & employer acquisition

**Target occupations (high-demand cross-border roles):**
- Construction/trades: masons, carpenters, electricians, plumbers, roofers
- Healthcare/patient care: nurses, caregivers, Pflegefachkraft
- Logistics/transport: drivers, warehouse workers, couriers
- Manufacturing/production: production line workers, machine operators
- Hospitality: kitchen staff, hotel workers

**Employer acquisition process (preliminary):**
- German partner companies need to create offers, specify capacity/dates/location/pay/requirements
- Tenant-scoped access — partners see only their own candidates and assignments
- Partners may use employer associations, recruitment agencies, or direct outreach
- Marketing to German employers: via employer associations (BDA, DIHK), job portals (StepStone Indeed), LinkedIn, and industry networks

### B.6 Competitor matrix (summary)

| Company | Focus | Scale | Differentiation |
|---|---|---|---|
| StepStone | Generalist German job portal | 200k+ jobs | Broad B2B reach, established |
| Kimeta | Cross-border (CZ/PL→DE) | Niche | Language/cultural bridge, A1 support |
| MakeIt | Eastern European workers → DACH | Niche | Platform for blue-collar workers |
| Traditional agencies | Recruitment agencies | Varies | Personal relationship, local presence |

**Opportunity**: Most generalist portals do not deeply specialize in the cross-border Czech→German worker A1 certificate workflow. A focused tool that integrates OCR, A1 issuance, and partner management has a niche differentiation.

---

## C. Research C — UX, UI, and Copywriting

### C.1 UX patterns from leading recruitment products

**Candidate journey (reference patterns):**
1. Search/filter jobs (mobile-first, autocomplete, faceted filters)
2. Job detail page (structured metadata, location map, application requirements)
3. One-click apply or save-for-later (soft interest vs. binding booking)
4. Account creation or magic-link access
5. Document upload (OP/ZP scans) with preview + progress indicator
6. Status timeline (applied → documents received → under review → matched → placed)
7. Communication center (messaging with recruiter)
8. Document access history (audit trail)

**Employer dashboard patterns:**
1. Job offer creation (form wizard with capacity, dates, location, pay, requirements)
2. Candidate matching (algorithmic + manual)
3. Application pipeline (status stages with drag-and-drop)
4. Document review (side-by-side for OP/ZP verification)
5. Assignment management (schedule, availability, placement)
6. Financial dashboard (planned vs. actual, invoices)
7. Communication tools

### C.2 Trust signals (critical for identity documents)
- GDPR compliance statement with retention periods
- Encryption in transit and at rest indicators
- EU-hosted storage badges
- Professional certifications (if any)
- User reviews/testimonials (for later)

### C.3 Mobile conversion optimizations
- Progressive form (multi-step wizard, not one long form)
- Document upload with camera capture (mobile)
- Autofill from device photos where permitted
- Clear error states with recovery instructions
- Czech first, German localization infrastructure

### C.4 Copywriting principles (for SOUL.md)
- **Czech voice:** Direct, practical, trustworthy. Avoid overly formal or salesy language.
- **German voice:** Professional, precise, formal "Sie" form by default for employer partner communications.
- **Accessibility:** WCAG 2.1 AA minimum. Keyboard operable. Clear focus indicators. Error recovery.
- **Empty states:** Illustrate with helpful guidance, not blank pages.

### C.5 Wireframe concepts (low-fidelity — text description)

**Jan portal login → dashboard:**
```
[Login] → [MFA prompt] → Dashboard
Dashboard: "Vaši Zaměstnanci" (3) | "Požadavky na dokumenty" (2) | "A1 případy"
            [Employee list with status chips] | [+ Nový zaměstnanec]
            [Missing data alert: 2 dokumenty] | [Audit log]
```

**Document upload → OCR review:**
```
[Upload OP/ZP scan] → Quarantine → OCR processing
→ Side-by-side: [Scan preview] | [OCR proposal with editable fields]
→ [Accept] / [Reject] / [Manual override]
```

**A1 case creation:**
```
[Employee] → [Create A1 case] → [Map data from reviewed employee+assignment]
→ [Generate provisional package] → [Preview 3 pages] → [Submit to OSSZ]
```

### C.6 Navigation model
- Private portal: Dashboard → Employees → Documents → Assignments → A1 Cases → Audit → Settings
- Public site (future): Home → Jobs → Job Detail → Apply → Account → My Applications

---

## D. Research D — Marketing & Business Strategy

### D.1 Candidate acquisition channels (Czech/Slovak)

| Channel | Viability | Notes |
|---|---|---|
| **Google Search/SEO** | High | "Práce v Německu", "práce pro Čechy v Německu" are high-volume search terms |
| **Facebook/Instagram ads** | Medium | High Czech/Slovak usage. Need verified business account + ToS compliance |
| **Facebook groups** | Medium | "Práce v Německu", "Práce pro Čechy" — groups with high engagement |
| **Referral programs** | High | Word-of-mouth in Czech/Slovak communities |
| **Trade schools/partnerhips** | High | Direct relationships with Czech vocational schools |
| **Google Display Network** | Medium | Retargeting for drop-offs |

### D.2 Employer acquisition channels (German)

| Channel | Viability | Notes |
|---|---|---|
| **Employer associations** | Medium | BDA, DIHK — formal channels, slower |
| **LinkedIn Sales Navigator** | High | Direct outreach to HR/managing directors |
| **StepStone/Indeed employer ads** | High | Standard German channels |
| **Industry networks** | Medium | Trade fairs, chambers of commerce |
| **Referrals from existing partners** | High | Best ROI |

### D.3 Revenue model options

1. **Commission on placement** (e.g., 10–15% of first-month salary or a fixed fee per placed worker)
2. **Subscription for employers** (monthly fee per active job/capacity)
3. **Hybrid:** Free for candidates, paid for employers (freemium)
4. **A1 issuance fee** (separate service)

### D.4 Email/social automation constraints

- n8n Community (self-hosted) can cover Facebook/Instagram publishing and feed syndication.
- n8n audit-log streaming is Enterprise-only — build own audit store.
- Social posting must use verified channel APIs only — no browser bots or scraping.
- All social content must comply with platform ToS (Facebook, Instagram, LinkedIn).
- Email: use SMTP relay (SendGrid, Mailgun, Brevo) or self-hosted Postfix with proper DNS (SPF, DKIM, DMARC).

### D.5 Pricing positioning

- Most cross-border recruitment agencies charge 10–20% of the worker's first-year salary to German employers.
- A focused, digital-first platform could price lower (5–10%) while offering faster matching and integrated A1 handling.
- Czech workers typically pay nothing; the German employer pays the placement fee.

### D.6 Key marketing questions requiring further research

1. Exact search volume and CPC for Czech/German recruitment keywords.
2. Facebook/Instagram ad approval process for recruitment content in CZ/DE.
3. Google Ads policy compliance for cross-border recruitment.
4. Partnership terms with Czech vocational schools and trade unions.
5. Legal restrictions on pre-employment screening language tests in Germany.

---

## E. Research E — Privacy, Legal & Operations

### E.1 GDPR (Regulation (EU) 2016/679)

**Source:** https://gdpr-info.eu/ (accessed 2026-08-12) — confirmed full article index.

| Article | Topic | Implication for Jan portal |
|---|---|---|
| Art. 5 | Principles | Lawfulness, purpose limitation, data minimization, storage limitation, accuracy, integrity/confidentiality |
| Art. 6 | Lawful bases | Contract (6.1b) primary for recruitment; consent (6.1a) only with easy withdrawal |
| Art. 9 | Special categories | **NO** racial/ethnic/health data unless explicit consent+DPIA. ID scans themselves are NOT special category; health insurance (ZP) IS. |
| Art. 13/14 | Info to data subject | Notice at collection: identity of controller, purposes, legal basis, retention, rights |
| Art. 17 | Right to erasure | Delete on request (subject to limitations) |
| Art. 20 | Data portability | Export in structured, machine-readable format |
| Art. 22 | Automated decision-making | **PROHIBITED:** no automated hiring decisions without human intervention |
| Art. 28 | Processor agreements | German partners likely processors, not controllers — require DPA |
| Art. 30 | Records of processing | Maintain processing activity records |
| Art. 32 | Security | Encryption, pseudonymization, resilience, confidentiality |
| Art. 33/34 | Breach notification | **72-hour** notification to DPA + data subjects if high risk |

### E.2 Czech Act 110/2019 Coll. & German BDSG

- **Czech Act 110/2019 Coll.**: Implements GDPR in Czech law. Enacted 2019, replaces Act 101/2000 Coll. Governs lawful bases, retention periods, data subject rights procedures, and the Czech DPA (Úřad pro ochranu osobních údajů / UOOZ).
  - Source: https://www.zakonyprolidi.cz/en/instrument.aspx?id=31784 (attempted 2026-08-12, 404 — URL may have changed)
  - Czech DPA: https://www.uooz.cz/ (attempted 2026-08-12, returned empty — likely blocked)

- **German BDSG (Bundesdatenschutzgesetz):** Supplements GDPR in Germany.
  - §26 BDSG: Special provisions for processing employee data in employment context.
  - §28 BDSG: Additional conditions for employment-context processing.
  - Source: https://www.gesetze-im-internet.de/bdsG_2018/ (attempted 2026-08-12, 404 — URL format issue)

### E.3 Data categories and legal basis

| Data | Legal basis | Retention | Notes |
|---|---|---|---|
| Basic identity (name, DOB) | Art. 6.1(b) contract | Until +7yr after employment | Required for A1 |
| OP (ID card) scan | Art. 6.1(b) + 9.2(b) | Until submitted +7yr | NOT special category |
| ZP (health insurance) | Art. 6.1(b) + 9.2(h) | Until submitted +7yr | **Special category** — needs explicit consent or employment law exception |
| A1 form data | Art. 6.1(b) + 9.2(b) | Until cert received +7yr | Provisional → official |
| Assignment data | Art. 6.1(b) | During assignment +7yr | Work contract info |
| OCR proposals | Art. 6.1(f) legit. interest | Until accepted/rejected | Immutable; never overwrites authoritative fields |

### E.4 Cross-border transfers

- **CZ → DE**: Both within the EU. No adequacy decision needed. Processor agreements (Art. 28 DPA) required between operator and German partners.
- **CZ → non-EU** (e.g., US-based OCR API): Requires Art. 46 safeguards (SCCs) or Art. 49 derogations.
- **Recommendation:** Process OCR locally (RapidOCR) — already the existing repo direction. Never send full OP/ZP scans to external models. Only minimal redacted crops to free vision models under the repo's AI provider policy.

### E.5 Data protection implementation checklist

**Before any real PII (Milestone 5 gate):**
1. [ ] DPIA completed for OCR + identity document processing
2. [ ] Data processing agreements (DPAs) with all subprocessors
3. [ ] Retention schedule documented (7 years post-employment for tax; shorter for proposals)
4. [ ] EU-hosted object storage (MinIO on server62, EU datacenter)
5. [ ] Encryption in transit (TLS 1.3) and at rest (S3 SSE-KMS)
6. [ ] Malware scanning on upload (ClamAV or containerized scanner)
7. [ ] Signed URLs with short TTL (≤1 hour) for document access
8. [ ] Append-only audit log for all document reads/writes
9. [ ] Incident response procedure (72h breach → DPA + data subjects)
10. [ ] Data subject request procedure (access, rectification, erasure, portability)
11. [ ] Staff training on data protection
12. [ ] Appointment of data protection officer if required by processing scale

### E.6 Server62 confirmed state

- OS: Debian 13 • CPU: 4 cores • RAM: 15 GiB (7.8 GiB available) • Swap: 8 GiB
- **BLOCKER: Root filesystem at 92%, only 7.5 GiB free**
- Installed: Docker CE 29.1, PostgreSQL 18, Nginx 1.26.3, Certbot 4.0, UFW 0.36, Fail2ban 1.1
- Python: 3.13.5 ✓ (compatibile with Django 5.2 + all researched packages)

**Reviewed deployment constraint:** The product remains rooted at `/var/www/prace-v-nemecku.tvoje.info`. Increase storage or attach encrypted capacity for protected runtime subdirectories there. Use dedicated non-login service accounts, native PostgreSQL/Nginx/systemd, local-only internal services, TLS, application/proxy upload limits, encrypted off-server backups with restore testing, SMTP, monitoring, malware scanning, environment separation, and patching. **Do not expose the project root, database, storage administration, Django Admin, or monitoring directly.** Exact values belong in the sysadmin as-built specification.

**Recommendation:** systemd + native Nginx/PostgreSQL (not Docker Compose) — lower risk on disk-constrained host.

---

## F. Blocker Checklist

A critical privacy, tenancy, licensing, or maintenance blocker rejects a candidate regardless of total score.

| Candidate | Blocker? | Reason |
|---|---|---|
| Django 5.2 LTS | No | BSD license, Python 3.13 compat, LTS through Apr 2028, no blockers |
| Django + HTMX | No | HTMX BSD, 14KB, dependency-free, perfect fit |
| django-two-factor-auth | ⚠️ Minor | django-otp (dependency) author notes reduced ongoing investment; stable, acceptable for pilot |
| django-q | No | MIT, ORM broker option, no external service needed |
| django-auditlog | No | MIT, well-maintained (Jazzband) |
| django-storages | No | BSD, mature, S3-compat support |
| MinIO | No | Source-available, S3-compatible, single binary |
| django-tenants | ✓ Rejected | Overkill for 2-org pilot; PostgreSQL schema isolation unnecessary |
| Self-hosted Supabase | ✓ Rejected | 7+ services; backups/HA/monitoring are operator responsibility; single-project limitation |
| Cookiecutter Django | ⚠️ Reference only | 13.6k stars, BSD, actively maintained — too much boilerplate to review/prune |
| Odoo Community | ✓ Rejected | Full ERP; overkill; LGPLv3 complexity; 2-8 week implementation |
| ERPNext | ✓ Rejected | Full ERP; GPL-3.0; heavy for narrow A1 workflow |
| Twenty CRM | ✓ Rejected | Non-standard license; CRM not recruitment; TS stack doesn't match Python A1 engine |
| Celery | ⚠️ Deferred | Overkill for pilot; requires Redis/RabbitMQ; django-q is simpler first choice |

### F.1 Architecture comparison (weighted)

| Option | Privacy | Reproducibility | Tenant Isolation | Ops | Cost | Total |
|---|---|---|---|---|---|---|
| A. Django 5.2 + HTMX + django-q | 5 | 5 | 4 | 5 | 5 | 24 |
| B. Django + Next.js + Celery | 5 | 4 | 4 | 3 | 3 | 19 |
| C. Self-hosted Supabase + Next.js | 3 | 3 | 2 | 2 | 2 | 12 |
| D. Odoo Community | 3 | 2 | 3 | 2 | 3 | 13 |
| E. Cookiecutter Django (full) | 4 | 3 | 3 | 3 | 3 | 16 |

### F.2 A1 engine integration (existing code)

**Sources:** AGENTS.md, `.agents/skills/a1-pdf-production/SKILL.md`, `docs/a1-release-gate.md` (all in-repo, accessed 2026-08-12)

- The existing A1 pipeline: `scripts/generate_provisional_a1.py` → `scripts/finalize_a1.py` → `scripts/a1_core.py` → `templates/a1_background.pdf` + `config/a1_layout.json`.
- Current cohort: 11 unique employees, 11 three-page PDFs, 33 hash-bound previews.
- Quality gate: `scripts/a1_quality_gate.py` is fail-closed.
- **Integration path:** Wrap the existing A1 scripts as an internal Python package (`packages/a1_engine/`) with a clean service interface. The Django app calls it via a `generate_a1(employee_data, assignment_data)` service method. No microservice needed.

---

## G. Source Register

| # | URL | Accessed | Used In |
|---|---|---|---|
| 1 | https://www.djangoproject.com/download/ | 2026-08-12 | A.1 — Django 5.2 LTS info |
| 2 | https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ | 2026-08-12 | A.2 — Production checklist |
| 3 | https://docs.djangoproject.com/en/5.2/topics/security/ | 2026-08-12 | A.2 — Security guidance |
| 4 | https://docs.djangoproject.com/en/5.2/ref/settings/ | 2026-08-12 | A.2 — Security settings |
| 5 | https://docs.djangoproject.com/en/5.2/ref/files/uploads/ | 2026-08-12 | A.2 — Upload limits |
| 6 | https://docs.djangoproject.com/en/5.2/topics/i18n/translation/ | 2026-08-12 | A.3 — i18n/l10n |
| 7 | https://pypi.org/project/django-two-factor-auth/ | 2026-08-12 | A.4 — 2FA |
| 8 | https://django-two-factor-auth.readthedocs.io/en/latest/ | 2026-08-12 | A.4 — 2FA features |
| 9 | https://pypi.org/pypi/django-otp/json | 2026-08-12 | A.4 — django-otp version/license |
| 10 | https://github.com/jazzband/django-auditlog | 2026-08-12 | A.5 — audit log |
| 11 | https://github.com/jazzband/django-simple-history | 2026-08-12 | A.5 — history |
| 12 | https://github.com/django-tenants/django-tenants | 2026-08-12 | A.6 — multi-tenancy |
| 13 | https://min.io/docs/minio/linux/index.html | 2026-08-12 | A.7 — MinIO |
| 14 | https://django-storages.readthedocs.io/en/latest/ | 2026-08-12 | A.7 — storage backends |
| 15 | https://docs.celeryq.dev/en/stable/django/ | 2026-08-12 | A.8 — Celery |
| 16 | https://github.com/Koed00/django-q | 2026-08-12 | A.8 — django-q |
| 17 | https://htmx.org/docs/ | 2026-08-12 | A.9 — HTMX |
| 18 | https://nextjs.org/docs | 2026-08-12 | A.10 — Next.js |
| 19 | https://docs.astro.build/en/getting-started/ | 2026-08-12 | A.10 — Astro |
| 20 | https://github.com/cookiecutter/cookiecutter-django | 2026-08-12 | A.11 — Cookiecutter |
| 21 | https://cookiecutter-django.readthedocs.io/en/latest/ | 2026-08-12 | A.11 — Cookiecutter docs |
| 22 | https://supabase.com/docs/guides/self-hosting | 2026-08-12 | A.12 — Supabase |
| 23 | https://github.com/odoo/odoo | 2026-08-12 | A.13 — Odoo |
| 24 | https://github.com/frappe/erpnext | 2026-08-12 | A.13 — ERPNext |
| 25 | https://github.com/frappe/frappe | 2026-08-12 | A.13 — Frappe |
| 26 | https://erpnext.com | 2026-08-12 | A.13 — ERPNext |
| 27 | https://github.com/twentyhq/twenty | 2026-08-12 | A.14 — Twenty CRM |
| 28 | https://www.stepstone.de | 2026-08-12 | B.2 — StepStone |
| 29 | https://business.linkedin.com/de-de/talent-solution/products/linkedin-jobs | 2026-08-12 | B.2 — LinkedIn |
| 30 | https://jobsuche-api.arbeitsagentur.de/ | 2026-08-12 | B.3 — Jobsuche API (unreachable) |
| 31 | https://ec.europa.eu/eures/ | 2026-08-12 | B.3 — EURES (API 404) |
| 32 | https://gdpr-info.eu/ | 2026-08-12 | E.1 — GDPR |
| 33 | https://www.zakonyprolidi.cz/en/instrument.aspx?id=31784 | 2026-08-12 | E.2 — Czech law (404) |
| 34 | https://www.gesetze-im-internet.de/bdsG_2018/ | 2026-08-12 | E.2 — BDSG (404) |
| 35 | https://github.com/n8n-io/n8n | 2026-08-12 | D.4 — n8n |
| 36 | AGENTS.md, `.agents/skills/a1-pdf-production/SKILL.md`, `docs/a1-release-gate.md` | 2026-08-12 | F.2 — A1 integration |

---

## H. ADR-001 Inputs & Next Decisions

### H.1 Decided (lock these for Milestone 1 → Milestone 2)

1. **Backend:** Django 5.2 LTS, BSD-3-Clause, supported through April 2028, Python 3.13 compatible.
2. **Frontend:** Server-rendered Django templates + HTMX (v2). No React/Next.js in Release 1.
3. **Background jobs:** django-q with ORM broker (no Redis required). Migrate to Celery+Redis only if throughput demands it.
4. **Multi-tenancy:** Shared-database/shared-schema organization scoping via `Organization` FK model. Not django-tenants.
5. **Authentication:** django-two-factor-auth (TOTP mandatory for all users). Built on django-otp v1.7.0.
6. **Audit/history:** django-auditlog for field-change tracking + custom `AuditEvent` model for security events.
7. **Document storage:** MinIO (S3-compatible) via django-storages. Quarantine → validate → private buckets. Signed URLs.
8. **A1 engine:** Internal Python package wrapping existing `scripts/` pipeline. Service interface: `generate_a1(employee, assignment)`.
9. **Infrastructure:** systemd + native Nginx/PostgreSQL (not Docker Compose) on server62. Pending storage expansion.
10. **Public site:** Astro (deferred to M6). Next.js is the alternative.

### H.2 Questions requiring operator/legal counsel

1. ✅ Architecture decision — **answer: Django 5.2 LTS + HTMX + django-q** (this document).
2. ✅ Infrastructure — **answer: native systemd + Nginx + PostgreSQL on server62, pending ≥50 GiB storage**.
3. ❓ Revenue model — which of: placement fee, subscription, hybrid, A1 fee?
4. ❓ Legal — controller/processor allocation between Czech operator and German partners (Art. 28 DPA contracts).
5. ❓ Legal — retention periods for OP/ZP/A1 beyond the standard 7-year tax window.
6. ❓ Legal — consent mechanism for ZP (health insurance = special category under Art. 9).
7. ❓ Product — anonymous contact requests vs. mandatory account creation.
8. ❓ Product — reservation semantics: soft interest vs. capacity hold vs. binding booking.
9. ❓ Feeds — consume BA/EURES jobs, post to external portals? (M6)
10. ❓ Hosting — self-hosted on server62 vs. cloud (Hetzner, AWS, etc.)?

### H.3 Confidence levels

| Recommendation | Confidence | Basis |
|---|---|---|
| Django 5.2 LTS | High | Official docs: Python 3.13 support, LTS through Apr 2028 |
| HTMX (no Next.js) | High | htmx.org docs: 14KB, zero-dep, perfect for Django |
| django-q (ORM broker) | Medium-high | GitHub: 1.9k stars, MIT, ORM broker config documented |
| django-two-factor-auth | High | PyPI: v1.18.1, Django 4.2–5.2, 16-lang translations |
| MinIO for documents | High | MinIO docs: S3-compatible, single binary, encryption |
| Shared-schema tenancy | High | Well-understood Django pattern; django-tenants overkill for 2 orgs |
| Supabase rejected | High | Supabase docs: 7+ operator responsibilities, single project |
| Storage expansion needed | Certain | Measured: 7.5 GiB free at 92% root usage |

### H.4 Evidence confidence per recommendation

Most recommendations are verified against official documentation or primary GitHub/PyPI sources. Confidence is lowered only where:
- European government sites (EURES API, Jobsuche API, BDSG, UOOZ) returned 404 or empty — flagged as "unverified" and requiring follow-up.
- django-otp author self-states reduced investment — acceptable risk for stable pilot package.
- Twenty CRM license shows "NOASSERTION" on GitHub API — rejected regardless due to stack/language mismatch.
