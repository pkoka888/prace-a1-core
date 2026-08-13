# Jan Release 1 — Proposed Solution and Decision Brief

**Status:** Proposed defaults for Pavel/Jan review
**Date:** 2026-08-12
**Project root:** `/var/www/prace-v-nemecku.tvoje.info`

This document prepares the likely best solution before asking Pavel or Jan. Select a recommendation, select a variant, or add a note. Unanswered items use the recommended default for synthetic proofs. New real-data portal uploads remain disabled only until the activation gate in `docs/security/real-data-rules.md` passes.

## 1. Product boundary

**Recommended:** Build a private Jan/operator operations portal first.

- Workers and authoritative identity data
- Protected documents, local OCR proposals, and human review
- Workplaces, current/upcoming/historical assignments
- A1 cases, readiness, prepared packages, previews, and audit history
- Manual recording of external submission and official authority response

Deferred: public recruitment site, candidate accounts, German-partner self-onboarding, job feeds, marketing automation, finance, automatic eligibility, and automatic A1 submission/issuance.

**Decision:** [x] Accept recommended scope  [ ] Change — note: __________

## 2. Architecture and deployment

### Recommended default

```text
Browser
  → HTTPS / Nginx
  → Gunicorn / Django 5.2 modular monolith
      → PostgreSQL
      → background worker
      → protected filesystem
      → internal A1 engine package
```

- Python 3.13, Django 5.2 LTS, PostgreSQL
- Django templates + targeted HTMX
- systemd services and native Nginx/PostgreSQL on server62
- no React, Next.js, Astro, Supabase, MinIO, or network microservice in Release 1
- project-owned append-only `AuditEvent`

Why: it preserves the existing Python A1 capability, minimizes services, gives one authorization model, and can later replace storage/queue/frontend boundaries without changing the Jan workflow.

### Meaningful variants

| Choice | Best when | Cost/risk |
|---|---|---|
| **Django monolith (recommended)** | Small private pilot and strong operational control | Least complexity |
| Django API + Next.js | Public/candidate UX must be built immediately | Two runtimes, API/auth/deployment overhead |
| Supabase + Next.js + Python service | Managed realtime/product primitives dominate requirements | More services and difficult document/A1 boundaries |

**Decision:** [ ] Django monolith  [ ] Django + Next.js  [ ] Supabase hybrid
**Notes:** __________

### Package proofs before ADR-001

- Authentication: compare `django-two-factor-auth` with `django-allauth[mfa]`.
- Jobs: compare `django-q2` ORM broker with Celery/Redis using OCR/A1 failure tests.
- Audit: custom `AuditEvent`; evaluate `django-auditlog` only as a model-diff helper.
- Storage: prove Django filesystem storage + encrypted volume + Nginx internal downloads.

Original `django-q` and MinIO are not candidates.

## 3. Project and folder structure

**Recommended:** Keep the whole deployed product under the existing project root while separating Git-managed source from gitignored protected runtime data.

```text
/var/www/prace-v-nemecku.tvoje.info/
├── portal/
│   ├── manage.py
│   ├── project/                 # settings, URLs, WSGI/ASGI
│   ├── apps/
│   │   ├── accounts/
│   │   ├── organizations/
│   │   ├── workers/
│   │   ├── documents/
│   │   ├── assignments/
│   │   ├── a1_cases/
│   │   ├── work_queue/
│   │   └── audit/
│   ├── templates/
│   ├── static/
│   └── tests/
├── packages/a1_engine/         # Django-independent A1 package
├── config/                     # tracked non-PII product/A1 configuration
├── runtime/portal/             # gitignored, protected
│   ├── quarantine/
│   ├── documents/
│   ├── generated/
│   ├── previews/
│   └── temporary/
├── secrets/                    # gitignored, protected
├── a1/ scans/ ocr/ evidence/   # current protected legacy inputs
├── docs/ plans/ .agents/
└── venv/
```

Nginx must never serve the project root or runtime directories directly. Django authorizes a file request; Nginx serves it only through an `internal` location using `X-Accel-Redirect`.

The native PostgreSQL service may retain its system-managed database directory;
it remains part of the product deployment but should not be forced into the Git
checkout. Encrypted off-server backups are necessarily outside the server/project.

Backups are not required for synthetic implementation, but a tested encrypted
backup and isolated restore are mandatory before pilot activation with real data.
Git protects tracked source history only; it does not protect runtime documents or
PostgreSQL. Ad-hoc PII backup copies remain prohibited.

**Decision:** [ ] Accept structure  [ ] Change — note: __________

## 4. Domain model

### Recommended records

```text
Organization ─ Membership ─ User
      │
      ├─ Worker ─ ActivityProfile
      │      ├─ Document ─ DocumentVersion ─ OCRRun ─ OCRProposal
      │      ├─ Assignment ─ Workplace ─ PartnerCompany
      │      └─ A1Case ─ A1Artifact
      ├─ ReviewTask
      └─ AuditEvent
```

- `Worker` holds stable identity; time-bounded `ActivityProfile` distinguishes employee, self-employed, and later supported profiles.
- `DocumentVersion` is immutable; replacements supersede rather than overwrite it.
- OCR creates proposals only. Human decisions create authoritative revisions and provenance.
- “Currently working at” is derived from assignments, not edited on the worker.
- An A1 case references the relevant worker, activity profile, assignment/activity period, evidence snapshot, and generated artifacts.
- A source change after generation marks the package stale and requires regeneration.

This is necessary because the renderer recognizes employee and self-employed profiles, while current finalization supports only the existing self-employed cohort. Release 1 must not infer one profile from the other.

**Decision:** [x] Stable worker + profiles (recommended)  [ ] Flat worker record
**Notes:** __________

## 5. End-to-end data flow

```text
Login + TOTP
  → organization/record authorization
  → upload one worker document packet
  → quarantine + type/size/hash/malware checks
  → local OCR job
  → field proposals with document/page/region source
  → logged-in uploader corrects or confirms the proposed values
  → confirmed authoritative worker revision attributed to that user
  → authoritative worker revision
  → workplace/assignment update
  → A1 readiness checklist
  → immutable input snapshot
  → A1 generation + deterministic QA + previews
  → authorized approver review
  → external submission recorded manually
  → official authority response uploaded and verified separately
```

Every material step appends an audit event. Ordinary logs must not contain document contents, full identity values, or secrets.

**Decision:** [ ] Accept staged flow  [ ] Change — note: __________

## 6. Roles and permissions

### Confirmed simple workflow

Jan and Pavel are organization administrators. Jan may create additional administrator users who can also review and approve within Jan's organization.

| Capability | Jan/Pavel/admin user | Ordinary future user |
|---|---:|---:|
| View organization workers | Yes | By assigned role |
| Upload OP/ZP and start OCR | Yes | By assigned role |
| Correct or confirm OCR values | Yes | By assigned role |
| Confirm identity/A1-critical data | Yes | No by default |
| Manage workplaces/assignments | Yes | By assigned role |
| Create, generate, and approve A1 package | Yes | No by default |
| Record submission/official response | Yes | No by default |
| Manage organization users/roles | Yes | No |
| View audit history | Yes | Own actions if allowed |

At upload, local OCR displays what it read from OP/ZP. The logged-in uploader corrects or confirms the values. Confirmation makes those values reviewed and records the confirming user, time, document version, and any manual changes. There is no mandatory second-person approval. A1 deterministic validation, package review, and official-evidence distinction remain in force.

All sensitive views/downloads are logged. Access remains organization-scoped and denied by default outside assigned permissions.

**Decision:** [x] Confirmed by Pavel
**Notes:** Jan and Pavel may approve everything; Jan may delegate the same approval rights to an administration employee.

## 7. Assignment behavior

**Recommended:** Preserve planned, active, paused, completed, and cancelled assignments. Allow overlaps with a visible warning; block A1 preparation only when an unresolved overlap makes the relevant activity/period ambiguous.

```text
Current(as_of) = status is active
                 and start_date ≤ as_of
                 and (end_date is empty or as_of ≤ end_date)
```

An assignment ending today is current today. Paused/completed/cancelled status overrides its dates.

**Decision:** [x] Allow overlap with warning  [ ] Hard-block overlap
**Preferred term:** [x] Přiřazení  [ ] Zakázka  [ ] Nasazení  [ ] Other: ______

## 8. UX/UI proposal

### Recommended implementation

- Bootstrap 5.3, self-hosted, with custom Django partials
- HTMX only as progressive enhancement; core workflows work as normal forms/links
- Czech default, German-ready translation strings
- desktop-first for operations, responsive mobile upload and field-by-field review
- WCAG 2.2 AA-oriented labels, keyboard/focus, error summary, 320px reflow, and status not conveyed by color alone

### Navigation

```text
Přehled | Pracovníci | Dokumenty | Přiřazení | A1 případy | Úkoly | Historie | Nastavení
```

Use `Pracovníci` as the generic people label. Display `Zaměstnanec` or `OSVČ` as the actual profile type.

### Dashboard example

```text
Co vyžaduje pozornost
[3] Dokumenty čekají na ověření
[2] Pracovníci mají chybějící údaje
[1] A1 případ čeká na kontrolu
[1] Přiřazení má termínový konflikt

Nedávná aktivita                 Nejbližší termíny
```

The dashboard is a work queue, not a vanity KPI dashboard.

### OCR review example

```text
┌ Document/page preview ──────┬ OCR proposals ───────────────────┐
│ zoom, page, highlighted area│ Name: proposed / current         │
│                             │ [Accept] [Keep] [Edit] [Unclear] │
│                             │ DOB: proposed / current          │
└─────────────────────────────┴──────────────────────────────────┘
```

Mobile shows one field at a time with “Show document crop”; it does not compress the two panes.

### A1 case example

```text
A1 případ — stav: Data neúplná
[Hotovo] Ověřit osobní údaje
[Hotovo] Ověřit typ osoby
[Čeká]  Doplnit místo výkonu
[Čeká]  Zkontrolovat období
[Čeká]  Vygenerovat náhled
[Blokováno] Připravit balíček
```

Do not show “Submit to OSSZ” until a supported integration exists.

**Decision:** [ ] Accept Bootstrap/HTMX and navigation  [ ] Change — note: __________

## 9. Recommended controlled states

- Document: received → validating → review required → verified/rejected → superseded/archived
- Worker: draft → active/missing information → archived
- Assignment: draft → planned → active/paused → completed/cancelled; conflict is a flag
- A1: not started → data needed → ready to generate → generating → prepared package → operator review → submission recorded → response pending → official certificate received/closed

Terminal alternatives: withdrawn, rejected, expired, cancelled. Generated packages are never called official certificates.

**Decision:** [ ] Accept state vocabulary  [ ] Change — note: __________

## 10. Decisions that still need Pavel/Jan confirmation

Research recommends defaults; these are operational facts only Pavel/Jan can settle.

1. Jan relationship: **confirmed organization administrator**; Pavel is also administrator/operator.
2. Identity approval: **confirmed uploader may correct and confirm OCR values**; approval is attributed to the logged-in user.
3. Original scans: **recommended controlled logged viewing/download for assigned workers; bulk export operator-only**.
4. Workplaces/assignments: **recommended Jan edits within his scope**.
5. Overlaps: **recommended allow with warnings**.
6. First worker profile: **recommended implement the currently evidenced self-employed flow first while modeling employee separately**.
7. Submission: **recommended manual external submission recording only**.
8. Primary device: **recommended desktop-first with mobile upload/quick review**.
9. Language: **recommended Czech default, per-user preference, German enabled when partner workflows begin**.

10. Delegation: **confirmed Jan may create an administration employee with approval rights**.

**Approval method:** tick accepted defaults above or annotate only the items that should change.

## 11. Real-data policy

**Approved:** `docs/security/real-data-rules.md` is the sole operational gate for
new real-data portal use.

- Every intake records its purpose, uploader, time, and retention-review date.
- Jan, Pavel, and a Jan-delegated administrator may confirm OCR and approve within
  Jan's organization; every action is attributable.
- Real data remains in protected gitignored project directories and is never
  publicly served, logged, tested, documented, or sent whole to external models.
- The default retention review is 90 days; an administrator deletes, records a
  justified extension, or applies a documented hold.
- Capacity and backup work do not block synthetic implementation. Plan K's
  capacity threshold and backup/restore proof are mandatory activation gates for
  real data.

**Decision:** [x] Confirmed by Pavel

## 12. Acceptance examples before real data

- A renamed executable cannot pass as a PDF/image or enter OCR.
- A clean synthetic scan creates proposals but changes no authoritative value automatically.
- Jan cannot obtain another organization's record by changing a URL/object ID.
- An authorized Jan/Pavel/delegated administrator can approve an A1 package and record verification of an official certificate; the audit identifies the actor and evidence.
- Operator corrections record source, actor, reason, time, and prior value.
- Replacing a document preserves the superseded version and source history.
- Duplicate hashes are detected; OCR failure creates a recoverable review task.
- Assignment boundary, pause, completion, and overlap cases calculate correctly.
- Changing a source value marks a generated A1 package stale.
- Every sensitive view/download is attributable without logging document contents.
- Critical workflows work by keyboard, at 200% zoom, and at a narrow mobile viewport.

## Sources

- Django support/deployment/storage: https://www.djangoproject.com/download/, https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/, https://docs.djangoproject.com/en/5.2/ref/files/storage/
- Authorization and uploads: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html, https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- Nginx protected delivery: https://nginx.org/en/docs/http/ngx_http_core_module.html#internal
- Authentication variants: https://github.com/jazzband/django-two-factor-auth/releases, https://docs.allauth.org/en/latest/mfa/introduction.html
- Jobs: https://django-q2.readthedocs.io/en/master/brokers.html, https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
- Accessibility/forms: https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/, https://www.w3.org/WAI/tutorials/forms/
- UI patterns: https://design-system.service.gov.uk/components/task-list/, https://design-system.service.gov.uk/components/file-upload/
- A1 authority: https://eportal.cssz.cz/web/portal/-/sluzby/zadost-o-urceni-pouzitelnych-pravnich-predpisu-pro-zamestnance-pojistenec
