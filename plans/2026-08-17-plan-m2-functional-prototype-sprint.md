# Plan M2 — Functional Release 1A Prototype Sprint

**Status:** active (vertical slice implemented + code reviewed; awaiting Jan observation)
**Milestone:** M2
**Owner:** product engineering + product design
**Duration target:** two bounded weeks after the prototype-start gate opens
**Vertical slice implemented:** 2026-08-19
**Code review & bug fixes:** 2026-08-19

## Objective

Deliver a production-shaped, synthetic-only Django vertical slice in which Jan
can complete J1–J4. Real values remain replaceable through configuration,
versioned migrations, and authorized application intake; tracked fixtures are
never replaced with real data.

## Prototype-start gate

**Gate result (2026-08-17): open.** `scripts/check_m2_scaffold_gate.py --json`
passes after independently validating the eight ADR-001 checks, frozen catalog,
ADR-002, Jan phase-1 defaults, planning/approval registers, proof evidence, and
generated assets. The initial production-shaped synthetic Django scaffold is in
`portal/`; it does not import proof settings.

Phase 0 preparation is active now. Creating the M2 Django scaffold begins
automatically, without another approval meeting, only when all are true:

1. all eight ADR-001 checks in `planning/approvals.json` pass;
2. Plan N freezes the Release 1A roles, fields, permissions, sources, and states
   using approved defaults plus recorded Jan exceptions;
3. ADR-002 accepts the minimum tenancy, schema, transaction, audit, deletion,
   query/index, concurrency, and migration contract from Plan O;
4. Jan phase-1 HTML review is recorded as accepted defaults or explicit exceptions;
5. `validate_approvals.py`, `validate_planning.py`, and Plan E preflight pass.

Plan L/M broader exits, Plan R, Plan K production evidence, and DEC-012 do not
block this synthetic gate. They retain their separate governance, A1-production,
infrastructure, and real-data scopes.

## Scaffold Location Clarification (2026-08-19)

The M2 prototype-start gate is **open** (all 8 ADR-001 checks pass, catalog frozen,
ADR-002 approved, REV-001 approved). Two scaffold locations exist:

| Location | Status | Purpose |
|---|---|---|
| `prototypes/architecture/adr001/apps/` | **Empty** (only `__init__.py`) | Plan E proof modules (disposable, not promoted to production) |
| `portal/release1a/` | **Minimal scaffold** | Production-shaped M2 vertical slice (models, views, services, migrations) |

**Decision:** The M2 functional prototype sprint implements the vertical slice in
`portal/release1a/` as the production-shaped scaffold. The
`prototypes/architecture/adr001/apps/` directory remains for disposable Plan E
architecture proof modules only and is not the M2 implementation target.

## Vertical slice

- Mandatory TOTP login for privileged roles and default-deny organization scope.
- Worker list/create/detail using the frozen synthetic field contract.
- Synthetic PDF/image upload, quarantine, OCR proposals, human confirmation,
  protected delivery boundary, and retry/recovery states.
- Effective-dated assignment create/edit with overlap warning and ambiguous A1
  period block.
- A1 readiness and preparation trigger through the Django-independent engine
  boundary; prepared output never appears as an official certificate.
- Project-owned non-content `AuditEvent` for every material write, sensitive
  read/download, denial, review, approval, and status transition.
- Czech-first templates with targeted HTMX enhancement; ordinary form/link
  behavior remains functional without JavaScript.

Plan E proof settings and shortcuts are not promoted. M2 may reuse validated
contracts, fixtures, interfaces, and domain behavior only.

## Journey and failure acceptance

- J1 worker creation: success, duplicate, invalid, forbidden organization, and
  interrupted save.
- J2 document/OCR: valid upload, mismatch/executable/oversize rejection,
  duplicate, retry, correction/provenance, and unauthorized zero-byte delivery.
- J3 assignment: current/future/paused/completed boundaries, overlap warning,
  stale concurrent edit, and A1 ambiguity block.
- J4 A1: readiness, snapshot, generation trigger, job retry, source-change
  staleness, approval denial, and manual external status distinction.
- Cross-cutting: keyboard completion, visible focus, 200% zoom, 320 px reflow,
  attributable non-content audit, no cross-organization leakage, and deterministic
  synthetic reset.

## Exit

Jan completes J1–J4 with synthetic data in the supported browser without
facilitator intervention. Mandatory TOTP, tenant isolation, audit coverage,
retry/idempotency, protected download, accessibility checks, and the full
repository suite pass. Exit does not authorize deployment or real-data use.

## Exclusions

No production deployment, real PII, public frontend, payroll/finance, automatic
A1 submission/eligibility, replacement of the canonical A1 engine, or weakening
of Plan K/R/DEC-012 gates.

## M2 Implementation Status (2026-08-19)

### J1 — Worker CRUD ✅
- [x] **Models**: `Worker` (TenantModel, Organization, given_name, family_name, birth_date, activity_profile, state, version)
- [x] **Views**: `worker_list`, `worker_create`, `worker_detail`, `worker_edit`, `worker_delete`
- [x] **Forms**: `WorkerForm` (Czech-first labels, birth_date validation 15-100, HTMX-enhanced)
- [x] **Templates**: `worker_list.html`, `worker_detail.html`, `worker_form.html`, partial `worker_row.html`, partial `worker_form.html`
- [x] **URLs**: `/workers/`, `/workers/new/`, `/workers/<pk>/`, `/workers/<pk>/edit/`, `/workers/<pk>/delete/`
- [x] **Tenant isolation**: All views filter by `request.organization` from Membership
- [x] **Audit**: `worker.created`, `worker.updated`, `worker.deleted` events
- [x] **Tests**: 4 tests in `tests/m2/test_views.py`

### J2 — Document/OCR ✅
- [x] **Models**: `Document` (TenantModel, opaque_key, sha256, content_type, state), `OcrProposal` (field_name, proposed_value, confidence, confirmed)
- [x] **Views**: `document_upload`, `document_detail`, `document_download`
- [x] **Forms**: `DocumentUploadForm` (PDF/PNG/JPG, 10 MB limit, path traversal protection), `OcrConfirmationForm` (HTMX per-field)
- [x] **Templates**: `document_upload.html`, `document_detail.html`, partial `document_row.html`
- [x] **URLs**: `/workers/<pk>/documents/upload/`, `/documents/<pk>/`, `/documents/<pk>/download/`
- [x] **Protected delivery**: Document state guard + audit (synthetic X-Accel-Redirect simulation)
- [x] **Audit**: `document.uploaded`, `ocr.confirmed`, `document.downloaded`, `document.download_denied` events
- [x] **Tests**: 1 test for login requirement

### J3 — Assignment ✅
- [x] **Models**: `Assignment` (TenantModel, workplace_label, activity_label, start, end, state, version)
- [x] **Views**: `assignment_create`, `assignment_edit`
- [x] **Forms**: `AssignmentForm` (overlap warning, version optimistic locking, Czech-first)
- [x] **Templates**: `assignment_form.html`, partial `assignment_form.html`, partial `assignment_row.html`
- [x] **URLs**: `/workers/<pk>/assignments/new/`, `/workers/<pk>/assignments/<pk>/edit/`
- [x] **Optimistic locking**: Version field prevents stale concurrent edits
- [x] **Audit**: `assignment.created`, `assignment.created_overlap`, `assignment.updated` events
- [x] **Tests**: 1 test for form rendering

### J4 — A1 Preparation & Approval ✅
- [x] **Models**: `A1Case` (TenantModel, source_hash, readiness, prepared_artifact_hash, external_status)
- [x] **Views**: `a1_prepare`, `a1_case_detail`, `a1_regenerate`
- [x] **Forms**: `A1PrepareForm` (readiness confirmation), `A1ApprovalForm` (approve/deny + external status)
- [x] **Templates**: `a1_prepare.html`, `a1_case_detail.html`, partial `a1_prepare_form.html`, partial `a1_case_row.html`
- [x] **URLs**: `/workers/<pk>/a1/prepare/`, `/a1/<pk>/`, `/a1/<pk>/regenerate/`
- [x] **A1 boundary**: Prepared ≠ issued distinction enforced
- [x] **Audit**: `a1.prepared`, `a1.blocked`, `a1.approved`, `a1.denied`, `a1.regenerated` events
- [x] **Tests**: 1 test for form rendering

### Cross-cutting ✅
- [x] **Tenant isolation**: All views use `request.organization` filter
- [x] **Audit (non-content)**: No sensitive data in `AuditEvent.object_ref`
- [x] **HTMX**: Per-field validation, partial updates, modal-style forms
- [x] **Czech-first**: All templates in Czech, CSRF token integrated
- [x] **Login required**: `require_org_membership` decorator enforces auth + TOTP
- [x] **Anonymous safety**: Unauthenticated users see "Nepřihlášen" panel

### Files Created/Updated
| Path | Purpose |
|---|---|
| `portal/release1a/forms.py` | 5 forms (Worker, Document, OCR, Assignment, A1Prepare/Approval) |
| `portal/release1a/views.py` | 14 views (J1-J4) + decorators |
| `portal/release1a/urls.py` | 12 URL patterns |
| `portal/urls.py` | Login/logout URLs |
| `portal/templates/portal/base.html` | Updated with HTMX, Czech nav |
| `portal/templates/portal/login.html` | New login page |
| `portal/templates/portal/dashboard.html` | Updated dashboard |
| `portal/templates/portal/worker_*.html` | 4 worker templates |
| `portal/templates/portal/document_*.html` | 2 document templates |
| `portal/templates/portal/assignment_*.html` | 1 assignment template |
| `portal/templates/portal/a1_*.html` | 2 A1 templates |
| `portal/templates/portal/partials/*.html` | 6 partial templates |
| `tests/m2/test_views.py` | 11 new M2 view tests |

## Code Review & Fixes (2026-08-19)

A review of the vertical-slice implementation found and fixed 11 issues (10 review bugs
plus the duplicate-audit-event regression). All fixes are covered by regression tests
in `tests/m2/test_review_fixes.py` (6 tests).

### Fixed bugs
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | `'blocked"` mismatched quotes in `a1_case_detail.html` | Page 500s (`KeyError`) | Fixed to `'blocked'` |
| 2 | 7 HTMX partial templates missing | `TemplateDoesNotExist` on HTMX requests | Created all 7 partials |
| 3 | `worker_delete` allowed POST only; template used `hx-delete` (DELETE) | 405 Method Not Allowed | Allow `POST, DELETE`; empty response for clean swap |
| 4 | `worker_delete` raised `ProtectedError` on workers with related records | 500 | Graceful denied page + `worker.delete_denied` audit event |
| 5 | Optimistic locking dead code (`version` not a form field) | Stale-write check never fired | Added hidden `version` field; view rejects stale edits |
| 6 | Overlap blocked save — contradicted DEC-005 | Overlapping assignments could not be created | Overlap now warns + saves; A1 prep still blocks ambiguous periods |
| 7 | Duplicate OCR proposals (service + view) | 4 proposals incl. duplicate `family_name` | Service is the single proposal source (1 proposal) |
| 7b | Duplicate audit events (`document.uploaded`, `a1.prepared`) created by both service and view | 2 events per action | Removed view duplicates; services layer is authoritative (verified: 1 event per action) |
| 8 | No HTMX CSRF integration | `hx-delete`/`hx-post` outside forms → 403 | CSRF meta tag + `htmx:configRequest` header in `base.html` |
| 9 | Size limit mismatch (form 10MB vs service 4KB) | Confusing rejection between 4KB–10MB | Single `MAX_UPLOAD_BYTES` constant shared by form + service |
| 10 | `worker_delete` returned JSON for `outerHTML` swap | Row replaced with JSON text | Return empty `HttpResponse` |

### Code quality
- Removed 13 unused imports from `views.py`/`forms.py`
- Removed dead `DocumentUploadForm.save()` override (service is the authority)
- Moved `import os` to module level; removed unused `_login_redirect` helper

### Post-review validation
- Full test suite: **496 passed** (479 + 11 M2 view tests + 6 regression tests)
- M2 tests: **19 passed**
- `validate_planning.py`: 24/24 checks pass
- M2 scaffold gate: **open**
- `git diff --check`: clean

### Pending (Per Plan M2 Exit)
- [ ] **Jan observation**: Manual review of J1–J4 journeys
- [ ] **Accessibility audit**: Keyboard nav, 200% zoom, 320px reflow verification
- [ ] **A1 integration test**: End-to-end prepare → regenerate → approval flow
- [ ] **Visual review**: Dashboard + form rendering across browsers
