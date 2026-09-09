# Plan 2026-09-06-A1-EVIDENCE-STATUS-REPAIR — A1 Evidence Status and Cohort Provenance Repair

**Status**: active
**Milestone**: A1 operations
**Parent**: PLAN-A1

## Stabilization checkpoint — 2026-09-07

Bounded stabilization is synthetic-accepted: **157 passed, 19 subtests** in the
final focused suite; document core **75 passed**. Preserve the initial failed
baseline (**5 failed, 33 passed**) as history. Deployment is not performed or
implied. Final isolated-storage/cache reruns passed **15 PostgreSQL intake tests**
and **33 affected M2 tests**, with no model/migration drift. See the
[stabilization report](../docs/research/2026-09-07-a1-stabilization.md).
The broader A1 repair and engineering gates remain active/pending.
See [roadmap stabilization](../roadmap.md#stabilization-synthetic-acceptance--2026-09-07).
Next bounded J4/promotion engineering may start with sequential file ownership;
this does not approve final promotion or activation. Minimum functioning
J4 remains before ENG-001 → REV-002 → remaining activation gates → REV-003.
No service migration is authorized: identify service settings/database separately;
use fresh PostgreSQL and historical MigrationExecutor states for test evidence.
RapidOCR/ONNX does not require Tesseract. Organization work is read-only inventory,
with unknown artifacts classified before any relocation or deletion.

## Engineering progress — 2026-09-07

[Codex implementation and remaining work](../docs/research/2026-09-06-a1-engineering-delivery.md).
A1-REPAIR-1 has implemented profile guards; A1-REPAIR-2 has canonical employee/casing/
checkbox/input-preservation support and synthetic tests. A1-REPAIR-4 has CSV/cohort
integrity checks but actual protected-source reconciliation remains pending.
A1-REPAIR-5 has dependency/snapshot hashes and changed-input rejection; A1-REPAIR-6
blocks unreceipted final rendering but promotion is not implemented. A1-REPAIR-7 has
sanitized durable readiness receipts; canonical identity comparison is still separate.
A1-REPAIR-3 web readiness and full J4 remain pending.

Do not call the package complete. Follow the [OpenCode work orders](../docs/operations/opencode-work-orders/README.md)
for remaining implementation/tests/audits, and route real-data acceptance to the
primary/operator. Posted employees are 3.1, multi-state employees 3.2, not 3.3;
Section 5 omission is the requested employee-copy presentation, not inapplicability.

## Purpose

Repair A1 evidence status and cohort provenance: reject placeholder institution
profiles, enforce provisional-generation restrictions, distinguish application
readiness from certificate issuance, reconcile cohort/artifact provenance,
and repair snapshot and final-promotion evidence.

Dated findings (2026-09-06 investigation baseline):
- 25/25 rows blocked in `finalize_a1.py readiness`
- 0/25 rows with AUTHORITATIVE source status on activity, certificate, or signatory
- Provisional and final PDF hashes were identical in the earlier baseline (approval was not established)
- Institution profiles use `review_status: VERIFIED` but contain `institution.street: "(doplnit)"` and `institution.code: "TBD"` placeholders

Counts are observations, not a replacement cohort contract. The operator must
populate per-row certificate/signatory/review fields from authoritative sources.

## Session-review additions to existing tasks

See the [current architect review](../docs/research/2026-09-06-a1-session-architect-review.md).
The following session-review additions remain acceptance requirements; the engineering progress above distinguishes implemented guards from outstanding operational evidence.

| Existing task | Additional required result |
|---|---|
| A1-REPAIR-1 | Louny remains unverified until required code/provenance is established; contact identity does not establish certificate signatory. Reject VERIFIED placeholders still present in other profiles. |
| A1-REPAIR-2 | Add canonical per-row employee support across generator, mapper, renderer and PDF verifier. Remove hard-coded self-employed kind and unconditional Section 5 expectations for employee-only profiles. Calibrate missing checkboxes against the actual template. Preserve authoritative prerequisites. |
| A1-REPAIR-3 | Distinguish posting and multi-state employment from confirmed assignments; do not infer either from DE-only display. Missing employer/insurance evidence blocks readiness but not draft intake. |
| A1-REPAIR-4 | Reconcile the skill's historical 11-person contract with authorized cohort scope before generation; observed counts are not authority. Validate CSV row width and uniqueness; reconcile duplicate identity proposals and residual OSVČ employer values in employee rows with protected correction receipts. No OP-first precedence or insurance-number derivation as authority. |
| A1-REPAIR-5 | Scope DE-only policy and casing changes to intended profiles/fields, reconcile tests and skill wording, invalidate dependent artifacts. Do not change unrelated cohorts by global default. |
| A1-REPAIR-6 | Reconcile 26 provisional/25 final files and one-off output with immutable source/config/QA/approval receipts. Preserve evidence; no final promotion by silence. |
| A1-REPAIR-7 | Report missing employer evidence, unsupported profile, unknown institution code and input-integrity errors separately; sanitized errors and protected receipts. |

Acceptance adds synthetic employee/self-employed/mixed cohorts, missing employer
and insurance evidence, Section 5 absence, exact checkbox pixels, consistent casing,
DE-only scope and unchanged template artwork. Resolve current stabilization failures through the intended contract, not by
weakening source or approval checks.

## Dependencies

| Gate | ID | Reason |
|---|---|---|
| evidence-only | PLAN-INFRA | Storage backend required for snapshots and artifact delivery |
| evidence-only | OCR-SHARED-CORE-LOCAL | Document core informs field interpretation for A1 input snapshots |

## Schema conventions (canonical — do not invent alternatives)

| Field/Pattern | Actual convention | Source |
|---|---|---|
| Flag values | `"YES"` / `"NO"` strings | `scripts/finalize_a1.py` |
| `validated_by_user` | `"1"` string when approved | `scripts/finalize_a1.py` |
| Source status | `"AUTHORITATIVE"` (not `"VERIFIED"`) | `scripts/finalize_a1.py` |
| Institution `review_status` | Top-level field in profile JSON, values: `"VERIFIED"` | `config/institutions/*.json` |
| Institution placeholders | Detected by `UNVERIFIED_SOURCE_MARKERS` or missing `institution.code` | `scripts/finalize_a1.py` |
| Review flags | `identity_reviewed`, `certificate_reviewed`, `approved_for_pdf` | `scripts/finalize_a1.py` |

## Tasks

### A1-REPAIR-1: Reject placeholder institution profiles

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- `scripts/finalize_a1.py` (via `load_profile`) and any new validator detect:
  - `review_status != "VERIFIED"` on the institution profile
  - Missing `source_url` or `verified_on` provenance fields
  - Any `UNVERIFIED_SOURCE_MARKERS` (`"assum"`, `"copied"`, `"assigned"`,
    `"example"`, `"placeholder"`, `"template"`) in `institution.name`, `institution.street`,
    `institution.code`
  - Missing required `institution` fields: `name`, `street`, `house_number`,
    `city`, `postal_code`, `country_code`, `code`
  - `institution.code == "TBD"` or `institution.street` containing `"doplnit"`
- Script exits non-zero with explicit error listing blocked profile IDs and specific defects

**Failure cases**:
- Profile with `review_status: VERIFIED` but `institution.street: "(doplnit)"` accepted → FAIL
- Profile with `institution.code: "TBD"` accepted → FAIL
- Blocked profile not logged with specific field defect → FAIL

---

### A1-REPAIR-2: Enforce provisional-generation canonical restrictions

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- Provisional generation only allowed when all canonical requirements are met
  (as defined in `finalize_a1.py`):
  - `certificate_reviewed == "YES"`
  - `approved_for_pdf == "YES"`
  - `activity_name`, `activity_address` are non-empty
  - `document_id` is non-empty and unique per employee
  - `start_date`, `end_date`, `issue_date` present in DD.MM.YYYY format
  - `signed_by` is non-empty
  - `activity_source_status == "AUTHORITATIVE"`
  - `certificate_source_status == "AUTHORITATIVE"`
  - `signatory_source_status == "AUTHORITATIVE"`
  - No `UNVERIFIED_SOURCE_MARKERS` in any `*_source` field
  - `validated_by_user == "1"` — required by canonical readiness
- Missing required field blocks provisional generation with explicit error naming the field
- These are the existing canonical restrictions from `scripts/finalize_a1.py`; this task
  preserves them, not replaces them; the abbreviated checklist does not substitute for
  the actual `finalize_a1.py` validator

**Failure cases**:
- Provisional generated without `signed_by` → FAIL
- Provisional generated with `certificate_source_status: UNVERIFIED` → FAIL
- Provisional generated without `validated_by_user == "1"` → FAIL
- Blocked row report does not name specific missing field → FAIL

---

### A1-REPAIR-3: Distinguish application readiness from certificate issuance

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- `WorkerA1Readiness.application_ready` computed from:
  - Worker has an accepted identity revision (`WorkerIdentityRevision` exists)
  - Worker has at least one confirmed activity/profile entry with an employer
  - Worker has at least one assignment with a requested period (start_date, end_date)
    — the period may be in the future; "active today" is not required for application
  - Employer/organization is confirmed
- `WorkerA1Readiness.certificate_ready` computed from:
  - Authoritative certificate data complete (`document_id`, `start_date`, `end_date`,
    `signed_by` present; source statuses are `AUTHORITATIVE`; institution profile
    is verified with no placeholder fields)
- These are separate fields; `application_ready == True` does NOT imply
  `certificate_ready == True`
- J4 UI shows both states distinctly; certificate readiness shows as "pending"
  when authoritative certificate data is incomplete

**Failure cases**:
- Single boolean used for both concepts → FAIL
- Certificate readiness shown as approved when source statuses are UNVERIFIED → FAIL
- Application readiness requires assignment active today → FAIL (future periods qualify)
- Application readiness shown as approved when no identity revision exists → FAIL

---

### A1-REPAIR-4: Reconcile cohort/artifact provenance

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- `a1/cohort.json` contains only operator-supplied entries referencing real
  authoritative sources (document IDs from actual certificates, institution codes
  from verified profiles)
- Each cohort entry records: source document reference (opaque), intake timestamp,
  authoritative certificate reference (opaque), specific fields that are authoritative
- Cohort provenance logged in `a1/provenance.log` (gitignored):
  - Each entry records: event type, employee hash (SHA-256 of employee_id),
    field name, correction reference (opaque), outcome, timestamp
  - Audit events contain opaque references to protected versioned records;
    no raw field values in the log
  - New values stored in protected versioned records; audit events reference
    those records by hash
- No cohort entry created without corresponding authoritative source document

**Failure cases**:
- Cohort entry references a placeholder institution code → FAIL
- Cohort provenance not logged → FAIL
- Raw field values (as opposed to opaque references) in audit log → FAIL
- Cohort entry created from a field with UNVERIFIED_SOURCE_MARKER in source → FAIL

---

### A1-REPAIR-5: Repair snapshot dependency tracking

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- `A1InputSnapshot` records: snapshot timestamp, input field hash (SHA-256 of
  the CSV row data at snapshot time), cohort reference, source document
  references (by hash), rendering config hash
- Snapshot staleness detected by changed dependencies, not by calendar expiry:
  - Source document modified after snapshot → stale
  - Institution profile modified after snapshot → stale
  - Cohort entry modified after snapshot → stale
  - Rendering config changed after snapshot → stale
- Certificate `end_date` is advisory only (indicates when the certificate expires);
  it does not determine snapshot validity or staleness
- Stale snapshot flagged in `a1_quality_gate.py` output with specific changed dependency

**Failure cases**:
- Snapshot staleness based on calendar date alone → FAIL
- Snapshot created without recording input field hash → FAIL
- Changed institution profile not marking related snapshots stale → FAIL
- Certificate end_date used as staleness signal → FAIL

---

### A1-REPAIR-6: Repair final-promotion evidence

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- Final promotion requires ALL of:
  - `validated_by_user == "1"` (operator approval)
  - All canonical certificate requirements met (per A1-REPAIR-2)
  - Institution profile verified with no placeholder fields (per A1-REPAIR-1)
  - Snapshot exists and is not stale (per A1-REPAIR-5)
  - QA render/validate passed (per `a1_quality_gate.py`)
  - Immutable approval receipt present
- PDF hash computed from actual PDF bytes
- Final artifact manifest binds to: PDF hash + snapshot hash + rendering config hash +
  QA receipt hash + approval receipt hash
- Final artifact is a separate file from provisional; final is never an alias
- Hash comparison between final and provisional is informational; if the authoritative
  fields are identical and QA passes, the hashes may legitimately be equal.
  Hash inequality is not a pass/fail criterion.

**Failure cases**:
- Final artifact created without `validated_by_user == "1"` → FAIL
- Final artifact manifest not bound to QA and approval receipts → FAIL
- Final artifact is an alias of provisional → FAIL
- Final artifact created when institution profile has placeholder fields → FAIL
- Final artifact created without QA pass → FAIL

---

### A1-REPAIR-7: Surface blocked-row root causes specifically

**Owner**: primary A1 production agent; operator approval required for regeneration

**Acceptance evidence**:
- `scripts/finalize_a1.py readiness` output lists each blocked row with:
  - Employee identifier (hashed, not raw name in logs)
  - Specific blocker: `missing <field>`, `source_status is not AUTHORITATIVE`,
    `placeholder detected in <field>`, `review_status is not VERIFIED`
- Blocked-row report written to `a1/blocked-rows-<date>.json` (gitignored)
- Report does not contain employee names, raw personal data, or document content;
  only row indices and field names
- Script exits non-zero when any row is blocked

**Failure cases**:
- Generic "blocked" without field name → FAIL
- Raw PII in blocked-row report → FAIL (PII breach)
- Script exits 0 when any row is blocked → FAIL (must be non-zero)

---

## Completion criteria

| Criterion | Evidence |
|---|---|
| No placeholder institution accepted | `load_profile` rejects `institution.street: "(doplnit)"` and `institution.code: "TBD"` |
| Canonical restrictions preserved | Existing `finalize_a1.py` checks (YES flags, AUTHORITATIVE, etc.) are the baseline |
| Application vs certificate readiness distinct | Two separate fields; UI shows both states; future assignment periods qualify |
| Cohort provenance uses opaque references | Audit log entries reference protected versioned records by hash; no raw values |
| Snapshot staleness by dependency change | Source doc change marks snapshot stale; calendar date alone does not |
| Final artifact dependency-bound manifest | Manifest = SHA(PDF_hash + snapshot_hash + config_hash + QA_hash + approval_hash) |
| Blocked-row report specific | JSON report names specific missing field or placeholder marker |

## Exit evidence

A1 production pipeline correctly distinguishes application readiness from
certificate issuance, rejects placeholder institution profiles, enforces
canonical provisional-generation restrictions (YES flags, AUTHORITATIVE sources),
and surfaces specific root causes for blocked rows. Cohort provenance uses
opaque references. Final promotion produces a dependency-bound artifact
only when all canonical requirements are met and operator-approved.
Certificate end-date is tracked separately as advisory information, not as a
staleness signal.

## Stabilization acceptance additions under existing tasks

- A1-REPAIR-1/2: complete institution verification semantics; required activity fields
  and independent country values agree in readiness and generation.
- A1-REPAIR-5/6: confined paths, exclusive staging, serialized atomic publication,
  no partial packages, recorded-DPI decoded-pixel QA and protected derivatives.
- A1-REPAIR-7: full operation UUID, locked append-only audit, required actor and
  organization, typed non-content metadata, mandatory protected failure receipts.
- A1-REPAIR-3: subsequent [operator workflow](../docs/architecture/operator-a1-workflow.md)
  separates application preparation, submission authorization and issued certificate.

Exit evidence includes sequential/concurrent audit history, audit failure, symlink
and outside-root rejection, concurrent/failing publication, all supported profiles
through subprocess generation/render/QA, unchanged originals, restrictive permissions
and sanitized diagnostics. Unit pass counts alone do not close this package.

Stabilization closure binds QA to the generation manifest, exact PDF hashes, full-UUID
completed operation receipt and terminal completed audit event. Reference stable
receipts/events, not the growing whole audit-log hash. Missing policy shape and
institution-source destination conflicts fail closed with sanitized diagnostics.
See the [2026-09-07 evidence report](../docs/research/2026-09-07-a1-stabilization.md).

Engineering checkpoint 2026-09-07: [runtime/J4 delivery](../docs/research/2026-09-07-runtime-j4-engineering.md) records actual stored canonical PDF/QA/preview evidence, protected delivery and disposable migrations. This does not authorize visual acceptance, final promotion, service deployment or gate opening. Existing task IDs retained.
