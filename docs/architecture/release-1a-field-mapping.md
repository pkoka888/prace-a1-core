# Release 1A legacy field mapping

Status: proposed DB-MIG implementation contract, 2026-09-08. This document does
not implement a schema, import records, accept evidence or activate real data.
It refines [DB-MIG-1 through DB-MIG-7](../../plans/PLAN-WORKERS-MIGRATE-TO-DB.md)
under [ADR-002](../decisions/ADR-002-release-1a-data-and-transactions.md), the
[minimum data contract](release-1a-data-contract.md), and the
[local automation proposal](../../plans/2026-09-08-local-a1-automation.md).

## Existing storage and proposed contracts

The inventory is based on [CSV_FIELDS and row_to_form](../../scripts/finalize_a1.py),
[models](../../portal/release1a/models.py),
[current services](../../portal/release1a/services.py), and migrations
[0006](../../portal/release1a/migrations/0006_normalized_intake_ocr_schema.py),
[0010](../../portal/release1a/migrations/0010_a1case_j4_minimum.py),
[0011](../../portal/release1a/migrations/0011_a1case_artifact_evidence.py),
[0012](../../portal/release1a/migrations/0012_a1case_confirmation_evidence.py), and
[0013](../../portal/release1a/migrations/0013_alter_a1case_visual_confirmed_by.py).
No private inputs were inspected to produce this mapping.

`Worker` currently stores names, birth date and a broad `activity_profile`;
`WorkerIdentityRevision.confirmed_fields` already stores additional accepted
identity fields. `Assignment` has dates, labels, state and version. `A1Case`
already has immutable source/artifact snapshots, evidence JSON, external status
and visual-confirmation fields. It has no dedicated `document_id`, `issue_date`,
`signed_by` columns and there is no `Approval` model in this application.
Those facts fit a versioned case snapshot; 44 CSV keys do not imply 44 new columns.

The table uses these explicit destinations:

- **W**: existing `Worker` columns. Accepted names/date are current projections
  of the selected identity revision; future acceptance updates both atomically.
  Existing OCR confirmation currently creates revisions without overwriting W.
- **I**: existing `WorkerIdentityRevision.confirmed_fields`, a flat map using
  canonical field names. Missing JSON keys mean unknown, not empty evidence.
  Pending OCR stays in existing `FieldProposal`/`FieldDecision` records and never
  becomes an I revision solely because machine checks passed.
- **S**: existing `A1Case.source_snapshot_json`. The **planned JSON contract**
  adds `schema_version`, `identity_revision`, `identity`, `assignment_refs`,
  `employment`, `activity`, `certificate`, `institution`, `provenance` and
  `verification`. These keys are not claimed to exist in current snapshots.
  Existing `profile`/`assignments` snapshots need a versioned adapter, not rewriting.
- **E**: existing `A1Case.evidence_notes` and `evidence_documents`. **Planned typed
  entries** distinguish evidence references, source assessments and input decisions
  from free-text notes. Entries carry kind, subject, actor, time, revision/hash,
  result and document/version or import-reference links. Future services enforce
  append-only decisions; the current JSON field alone provides no such guarantee.
- **P**: structured per-field entries in planned `S.provenance.fields`, plus
  `S.provenance.sources`. Each includes source kind, immutable source hash,
  document/version/proposal/decision references where available, import run and
  row reference, original value reference, accepted revision and authority status.
  Protected values stay in their owning records/snapshot, never audit messages.
- **A+**: migration 0015 implements `Assignment.a1_facts_json`, one versioned JSON field for
  structured Section 4 employer/self-employment facts and Section 5 facts which
  the existing display labels cannot represent. It currently holds unconfirmed values; structured source references remain in
  snapshot provenance/owning records. Changes through the service increment `Assignment.version`. S freezes the selected
  values and assignment IDs/versions. It is not an independent worker master.
- **W+**: **planned** nullable `Worker.legacy_employee_id`, with a conditional
  uniqueness constraint on organization plus nonempty key. It is an explicit
  legacy association, not the database primary key or a filename identity guess.
  Compatibility export uses this established key when present; a DB-native worker
  instead uses a stable slug representation of `Worker.pk`, such as `worker-<pk>`.
  Freeze the chosen key in `S.employee_id`, check uniqueness across the selected
  export, and fail on a collision rather than remapping a confirmed association.
  Never derive this key from a name, filename or another personal identifier.

W+ remains a schema gap; A+ has an additive migration and version-checked service. Other listed destinations reuse existing
columns with planned validation/service contracts. DB-MIG must prove historical
migration transitions with `MigrationExecutor`, add constraints only after
reconciliation, and enforce organization ownership on every referenced object.

## Implemented input snapshot and export

`portal/release1a/a1_exports.py` implements synthetic `prepare_input_case`,
`update_assignment_facts` and `export_input_case`. Version `a1-input-1` stores
`row` (all 44 CSV columns), `provenance` keyed directly by CSV field,
`dependencies`, `blockers`, `organization_ref`, `employee_id` and `scope`.
The S/P nested shapes below describe the broader target contract, not this first
version's JSON paths. No existing snapshot is rewritten. Exports return UTF-8
CSV/JSON bytes to an authorized caller; they do not publish files or PDFs.

Dependencies bind worker version/state, selected assignment facts hash/version,
selected claim/run/version/output hash and accepted identity revision. Selected
claims/assignments remain pinned on export; changed evidence fails closed.
Machine claims and worker projections remain unconfirmed. Accepted individual
identity fields override OCR without setting whole-form approval flags. Assignment
inputs are unconfirmed, absent facts remain blank, and source references are opaque.
Migration 0016 and `portal/release1a/a1_drafts.py` now reserve a draft number and
pin the profile/input/dependencies for the canonical unverified PDF publisher.
Migration 0017 retains that stable number while binding each generation to its own
profile/dependencies and immutable package; historical packages remain available.
BO now reads the applicable generation through `portal/release1a/a1_generation_access.py`.
Migration 0018 stores the operator/time and exact source/fingerprint/PDF/receipt
for each visual confirmation. Identity facts and case issuance state remain separate.
BO field confirmation now uses `portal/release1a/field_review.py` and existing
FieldDecision/WorkerIdentityRevision records. Tokens bind proposal/source/association
and the current confirmed revision; replacement of a confirmed value requires reason.
Legacy-key reconciliation, cohort export and identity association/conflict BO integration remain follow-up work.

## Complete CSV mapping

Exactly one row follows for every current CSV field, in source order. “Required”
means the relevant existing canonical validation gate requires a value; it is
not permission to manufacture one. In a proposed unverified draft, absent facts
remain absent and can block that person's rendering. JSON unknowns export as
empty cells. Dates use ISO values internally and `DD.MM.YYYY` in compatibility
CSV; identifiers, house numbers and postcodes remain strings. Accepted source
text is preserved; display casing belongs to the shared renderer.

| CSV field | Destination: existing storage / planned addition | Transformation and export | Provenance | Confirmation and nullability |
|---|---|---|---|---|
| `employee_id` | W+ when established, otherwise existing Worker.pk; frozen `S.employee_id` | Preserve legacy slug or stable opaque worker-<pk> key; export frozen key consistently across CSV/cohort/identity payloads | P: explicit organization/worker association; import-row reference only for imported workers | Required unique export key; legacy key remains nullable for DB-native workers; collision blocks export |
| `source_scans` | Existing Document/DocumentVersion references in `S.provenance.sources` | Parse semicolon list; resolve exact authorized sources; export pinned opaque references in deterministic order | P: document/version hashes; retain original legacy reference privately | May be empty pending evidence; unresolved references are blockers for claimed source acceptance |
| `surname` | Existing W.family_name and I.family_name; freeze S.identity.family_name | Export revision value to surname; renderer applies Czech display casing | P + FieldProposal/FieldDecision or recorded manual/import decision | W non-null; acceptance pins I; no fabricated surname for incomplete intake |
| `given_name` | Existing W.given_name and I.given_name; freeze S.identity.given_name | Preserve spelling; display casing only at rendering | P + identity field decision | W non-null; required accepted identity for canonical approved path |
| `dob` | Existing W.birth_date and I.birth_date; freeze S.identity.birth_date | Validate real date, ISO internally, `DD.MM.YYYY` export | P + identity field decision | W non-null DateField; missing date stays unresolved intake, never a sentinel date |
| `birth_place` | Existing I.birth_place; freeze S.identity.birth_place | Preserve value; shared display casing | P + identity field decision | Missing key allowed in incomplete revision; required by canonical gate |
| `nationality` | Existing I.nationality; freeze S.identity.nationality | Preserve supported source value; never infer from residence | P + identity field decision | Unknown allowed in pending data; required by canonical gate |
| `sex` | Existing I.sex; freeze S.identity.sex | Validate canonical `M`/`F`; no inference from name | P + identity field decision | Unknown stays absent; unsupported values block canonical export validation |
| `insurance_number` | Existing I.insurance_number; freeze S.identity.insurance_number | Preserve string and leading zeroes; shared identity consistency validation | P + identity field decision | Unknown stays absent; required by canonical gate; never populate from another worker |
| `street` | Existing I.street; freeze S.identity.residence.street | Export string; shared display casing | P + residence field decision | Missing allowed pending review; required by canonical gate |
| `house_number` | Existing I.house_number; freeze S.identity.residence.house_number | String, preserve suffixes/separators | P + residence field decision | Missing allowed pending review; required by canonical gate |
| `city` | Existing I.city; freeze S.identity.residence.city | Preserve accepted place; shared display casing | P + residence field decision | Missing allowed pending review; required by canonical gate |
| `district` | Existing I.district; freeze S.identity.residence.district | Preserve district separately from city | P: accepted source or versioned enrichment plus decision | Optional; empty exports empty, never inferred solely for completeness |
| `postal_code` | Existing I.postal_code; freeze S.identity.residence.postal_code | String; preserve accepted formatting/leading zeroes | P: source or versioned enrichment plus decision | Missing allowed pending review; required by canonical gate |
| `country_code` | Existing I.country_code; freeze S.identity.residence.country_code | Validate supported country code; preserve residence distinction | P + residence field decision | Unknown allowed pending review; required by canonical gate |
| `status_profile` | A+.status_profile; freeze S.activity.status_profile; W.activity_profile remains broad projection | Preserve all three canonical values; self_employed_multi_state maps to W self_employed, other two to employee | P + explicit activity decision, never scan/name inference | Unknown blocks profile-specific rendering; broad W profile cannot reconstruct this field |
| `activity_name` | A+.activity.name; freeze S.activity.name | Section 5.1; preserve explicit blank for provisional self-employed multi-state policy | P: activity evidence or versioned policy default | Blank permitted in provisional validation/readiness mode for this profile; authoritative mode still requires a value; neither result establishes artifact acceptance |
| `activity_address` | A+.activity.address; freeze S.activity.address | Section 5.2 territory list, not a street address; default DE, CZ only as labelled policy proposal | P: explicit territory evidence/override or policy version | Required territory; explicit confirmed override wins; generated default remains unverified |
| `employment_id` | A+.employment.employer_id; freeze S.employment.employer_id | CSV employment_id becomes core employer_id; preserve identifier string | P: Section 4 employer/self-employment evidence | Required by current canonical gate; never use tenant Organization.key as employer evidence |
| `employment_name` | A+.employment.employer_name; freeze S.employment.employer_name | CSV employment_name becomes core employer_name; preserve legal name casing | P: Section 4 evidence and decision | Required; employee profiles must not receive self-employed employer data |
| `employment_street` | A+.employment.street; freeze S.employment.street | Core employment.street / employer street display | P: Section 4 evidence and decision | Required by canonical gate; unknown pending data allowed |
| `employment_house_number` | A+.employment.house_number; freeze S.employment.house_number | String, preserve suffixes/separators | P: Section 4 evidence and decision | Required by canonical gate; unknown pending data allowed |
| `employment_city` | A+.employment.city; freeze S.employment.city | Shared display casing; do not substitute worker residence | P: Section 4 evidence and decision | Required by canonical gate; unknown pending data allowed |
| `employment_postal_code` | A+.employment.postal_code; freeze S.employment.postal_code | String, preserve leading zeroes | P: Section 4 evidence and decision | Required by canonical gate; unknown pending data allowed |
| `employment_country_code` | A+.employment.country_code; freeze S.employment.country_code | Validate country code independently of residence and territory | P: Section 4 evidence and decision | Required by canonical gate; unknown pending data allowed |
| `resolved_ossz` | Planned S.institution.resolved_ossz key in existing snapshot | Export institution label; validate agreement with selected institution profile | P: source/enrichment version and review decision | Unknown allowed in draft inputs; canonical gate requires consistent institution |
| `institution_profile` | Planned S.institution.profile_key plus immutable profile values/hash | Export pinned profile key and matching profile payload; no lookup of silently changed live profile | P: reviewed profile source URL/reference, source hash, status and decision | Unknown/unverified profile cannot claim authoritative readiness |
| `document_id` | Planned S.certificate.document_id key | Preserve issued ID exactly; provisional reservation must be stable and explicitly typed provisional | P: certificate evidence or recorded provisional-number policy/reservation | Unknown allowed pending facts; canonical gate requires nonempty unique ID; generated ID never proves issuance |
| `start_date` | Planned S.certificate.start_date key | ISO date / `DD.MM.YYYY`; certificate coverage, not automatically Assignment.start | P: certificate evidence; proposed application period separately labelled | Nullable/absent pending evidence; required on official-evidence path |
| `end_date` | Planned S.certificate.end_date key | ISO date / `DD.MM.YYYY`; validate start <= end; no implicit assignment-date substitution | P: certificate evidence; proposal basis retained | Nullable/absent pending evidence; required on official-evidence path |
| `issue_date` | Planned S.institution.issue_date key | Shared issue-date policy; preserve evidenced date; generated draft date explicitly provisional | P: institution/certificate evidence or versioned provisional policy | Missing allowed pending evidence; current canonical paths require field; draft date is not official issuance |
| `signed_by` | Planned S.institution.signed_by key | Preserve evidenced signatory; never copy template/example signatory | P: signatory evidence and human decision | May be absent in unverified preparation; required authoritative signatory for final path |
| `identity_reviewed` | E input decision kind identity_review; pinned S.verification.identity decision reference | Export YES only for complete accepted identity scope; otherwise NO | Exact I revision, document/version and actor/time; legacy flag retained as import claim | Defaults pending/NO; accepting one field does not approve the whole identity |
| `certificate_reviewed` | E input decision kind certificate_review; pinned S.verification.certificate reference | YES only for explicit review of selected certificate facts/evidence; otherwise NO | Certificate snapshot hash, evidence links and reviewer/time | Pending/NO when unsupported; review alone does not set external_status issued |
| `approved_for_pdf` | E input decision kind pdf_preparation_approval; pinned S.verification.pdf_approval reference | YES only for accepted input scope and intended generation mode; otherwise NO | Case input revision/hash, actor, time and decision | Defaults pending/NO; machine QA must not set it; does not replace artifact visual review |
| `pdf_created` | Existing A1Case.artifact_reference + prepared_artifact_hash | Derived YES only after protected PDF bytes/hash verified for selected case; otherwise empty | Artifact manifest, immutable dependency hashes and storage verification receipt | No human flag import creates bytes; artifact presence is separate from freshness, submission and issuance |
| `validated_by_user` | E input decision kind user_input_acceptance; pinned S.verification.user_acceptance reference | Export 1 only for explicit accepted input revision; otherwise 0 | Authorized user, timestamp, exact source revision and evidence scope | Pending/0 by default; never map to visual_confirmed or synthetic Release1aAcceptance |
| `activity_source` | Planned S.provenance.sources.activity entry, linked E evidence | Export stable protected evidence reference; preserve original source description in import evidence | Structured document/version/hash or policy/manual-source reference | Missing blocks authoritative activity claim; free text alone insufficient |
| `activity_source_status` | Planned S.provenance.sources.activity.authority_status | Export AUTHORITATIVE only from supported accepted source assessment; otherwise UNVERIFIED | E source assessment with actor/time, evidence and revision hash | Defaults UNVERIFIED; policy default/OCR success never promotes authority |
| `certificate_source` | Planned S.provenance.sources.certificate entry, linked E evidence | Export pinned certificate evidence reference, never generated PDF as its own authority | Source document/version/hash and acceptance decision | Missing allowed for application draft; blocks official-evidence path |
| `certificate_source_status` | Planned S.provenance.sources.certificate.authority_status | AUTHORITATIVE only with evidenced assessment; otherwise UNVERIFIED | E source assessment bound to certificate facts and source | Defaults UNVERIFIED; certificate_reviewed YES alone cannot supply missing authority |
| `signatory_source` | Planned S.provenance.sources.signatory entry, linked E evidence | Export pinned signatory evidence reference | Source document/version/hash and acceptance decision | May be absent in draft; required for authoritative signatory |
| `signatory_source_status` | Planned S.provenance.sources.signatory.authority_status | AUTHORITATIVE only with evidenced assessment; otherwise UNVERIFIED | E source assessment bound to signatory and source | Defaults UNVERIFIED; institution profile/name alone is insufficient |
| `comments` | Existing A1Case.notes; freeze initial text in planned S.comments for reproducible export | Preserve protected free text; export pinned snapshot text, not later mutable notes | P: import row/hash or attributed manual note | Optional empty string; no sole ownership of facts, evidence, authority or approval |

## Revision selection, decisions and drafts

Every export selects an explicit case ID and immutable source hash within the
authorized organization. S pins the worker identity revision, each selected
assignment ID/version and period, source versions/hashes, institution payload,
policy version and input decisions. Assignment labels are presentation fields;
they cannot silently become Section 4 employer facts or Section 5 territory.
Ambiguous assignments block the affected preparation. Certificate dates are
independent of assignment dates and proposed application periods.

Changing worker, assignment, institution or certificate facts creates a successor
snapshot and marks dependent artifacts stale. A later confirmation can append
an E decision referring to the displayed snapshot; a new accepted export case
pins that decision, without modifying the old source snapshot or its hash.
Optimistic revision checks reject stale confirmation. Replaying an old export
uses its pinned values, never the latest worker/assignment/profile by accident.
The service must enforce immutability and cross-organization reference checks;
JSON storage alone is insufficient.

Current input flags do not encode the person/time/scope needed to prove acceptance.
Import preserves their literal values as historical claims. Only evidenced
decisions can project YES/1 in accepted exports; missing attribution remains
pending. Exact byte preservation of an import source is evidence retention,
not approval of its assertions. Machine checks and human decisions have separate
states and timestamps. Existing `A1Case.visual_confirmed*` fields refer to the
actual PDF and all-page review receipt, independently of input acceptance.
`external_status=submitted/issued` requires its own evidenced external event.
Neither `pdf_created`, a generated identifier, readiness nor visual PASS supplies it.

Both current `validate_review` modes require `identity_reviewed`,
`certificate_reviewed` and `approved_for_pdf` to equal YES, and
`validated_by_user` to equal 1; provisional mode does not waive these flags.
`readiness_report(provisional=True)` and `readiness --provisional` retain those
flags and share provisional required fields, including the intentional blank 5.1
for self-employed multi-state rows. Default readiness checks authoritative inputs.
Receipts label their mode and review-preflight scope, not artifact acceptance.
`pdf_created` is not an input-approval gate. Nullable/absent facts in the proposed
storage contract therefore do not imply acceptance by either current validator.

Unverified preparation selects explicit pending proposal IDs/versions plus any
already accepted identity revision. S records which values are proposed and
which accepted; missing facts are not invented. Incomplete required W fields
remain in an `IntakeSession`/proposal until a coherent draft worker can exist.
The proposed J4 draft service may prepare eligible visibly unverified artifacts
without waiting for BO; it cannot fake the canonical publisher's approval flags.
Draft IDs/dates are policy-derived, stable per reservation/retry and carry
UNVERIFIED provenance. This document does not implement the draft service,
number reservation or weaken existing canonical readiness/promotion gates.

## Data-first reconciliation before cutover

Use the baseline `a1/review.csv` and an explicitly selected list of scoped run
snapshots as reconciliation inputs, alongside their bound cohort and normalized
identity sources. The protected selection manifest records run IDs, hashes,
organization, worker/case coverage and purpose. Baseline presence, later mtime,
directory order and “newest run” do not establish authority. A scoped run can
contribute only to its declared records; it cannot erase other baseline records.

Compare values and evidence field by field. Identical values retain their source
links; conflicts remain proposals with reason codes until a recorded decision
selects an evidenced value. Preserve confirmed/issued identifiers without
regeneration. Cohort-only records require explicit association and provenance;
row counts never authorize invented workers. A CSV flag or source-status string
does not outrank missing evidence. Never reconstruct source facts by copying
values from generated A1 PDFs. No files are frozen, moved or deleted by this
documentation checkpoint.

The import dry run must report only opaque references, counts and reason codes;
full comparison data remains protected under the
[real-data rules](../security/real-data-rules.md). An accepted migration receipt
binds input hashes, selected decisions, DB revisions and rejected/unresolved rows.
Only DB-MIG acceptance and the applicable activation approval permit cutover.

## Shared export service extension

The input-only `export_input_case` interface above is implemented. Extend that
owner for complete packages/direct-core mapping; do not add a competing exporter.
The following richer interface remains **not implemented**:

```python
portal.release1a.a1_exports.export_a1_snapshot(
    actor, organization, *, case_id, expected_source_hash,
    mode,  # compatibility or direct_core
)
```

This single service selects and authorizes the immutable database snapshot,
validates its version and evidence, audits the export, and returns a protected
manifest/reference. Compatibility mode writes revision-bound review CSV, cohort
JSON, normalized identity JSON and the selected institution profile from that
same snapshot. The manifest hashes all payloads and the source revision; output
is read-only compatibility material, never a parallel editable master. Explicit
legacy scan-name aliases, if required for a historical consumer, stay in protected
metadata and never become storage paths or matching rules.

Direct-core mode adapts the same selected values into the shared
`scripts/a1_core.py` input contract. Web and CLI remain thin callers; rendering,
document-ID/date rules, Czech display casing and validation stay in the existing
shared core. Do not make `finalize_a1.row_to_form` depend on Django or create a
second export service in scripts. Existing legacy callers continue until the
DB-MIG acceptance checkpoint; future commands must not claim to exist already.

## Verification

Documentation acceptance can verify the complete table without loading Django
or any private data. Run this from the repository root:

```bash
PYTHON_BIN="$PWD/venv/bin/python"
"$PYTHON_BIN" - <<'PY'
import ast
import re
from pathlib import Path

tree = ast.parse(Path("scripts/finalize_a1.py").read_text())
fields = next(ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "CSV_FIELDS"
                      for target in node.targets))
document = Path("docs/architecture/release-1a-field-mapping.md").read_text()
rows = re.findall(r"^\| `([a-z_]+)` \|", document, re.MULTILINE)
assert len(fields) == len(rows) == 44
assert tuple(rows) == fields, "Mapping order, duplicates or coverage changed"
print("PASS: all 44 CSV_FIELDS mapped exactly once in source order")
PY
```

Future synthetic implementation acceptance must cover field-level round trips,
unknown/blank distinctions, retained source text, multi-source provenance, stale
confirmation, deterministic assignment selection, cross-organization denial,
unverified drafts, unchanged official IDs and four-way snapshot hash binding.
Compare renderer inputs first; compare PDF bytes only with pinned template,
renderer, dependencies and deterministic metadata. Document-only coverage and
link checks do not establish DB-MIG runtime acceptance or deployment.


## Machine draft provenance — 2026-09-09

`portal/release1a/identity.py` persists `IdentityEvaluation` evidence and
`WorkerIdentityClaim` source links for unconfirmed worker drafts. The claim's
organization/type/issuer/identifier hash is a deduplication key, not a confirmed
identifier. Draft name/date fields originate in the referenced OCR run/region;
activity profile must come explicitly from the batch manifest whose hash and actor
are recorded in the protected receipt. Existing confirmed revisions remain authoritative.
`IdentityResolution` binds explicit human association to evaluated evidence and
expected worker version/revision. It does not confirm individual identity fields.
These records supplement the row mappings above; they do not change the canonical
CSV contract or establish DB cutover. BO form integration remains a follow-up.
