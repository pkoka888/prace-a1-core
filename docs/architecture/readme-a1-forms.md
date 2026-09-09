# A1 pipeline: inputs, rendering and verification

Current implementation reference, updated 2026-09-08. For authority and operational
boundaries use [AGENTS.md](../../AGENTS.md), the
[A1 production skill](../../.agents/skills/a1-pdf-production/SKILL.md) and
[real-data rules](../security/real-data-rules.md). The
[framework guide](A1_FRAMEWORKS.md) owns the engine comparison and storage contracts;
the [local automation plan](../../plans/2026-09-08-local-a1-automation.md) owns future work.

## Ownership and present data flow

```text
Selected protected review/cohort/identity/profile inputs
  → generate_provisional_a1: reconciliation, policy composition, staging
  → finalize_a1: validation and row_to_form
  → a1_core: build_form_data → render_overlay → generate_a1_pdf
  → protected provisional package and dependency manifest
  → quality_gate: previews, deterministic validation, hash-bound visual review
```

The portal has a separate adapter and publisher, while using the same renderer:
`services.prepare_a1()` captures case inputs; `services.attach_a1_artifact()`
authorizes the expected source revision, builds the form and calls the core;
`j4_artifacts.publish_artifact()` stores PDF bytes, snapshot, previews and receipt.
Preparation alone does not create a PDF or its hash. Existing J4 storage does not
prove unattended fresh-OCR draft preparation or a complete DB migration.

| Owner | Responsibility |
|---|---|
| `scripts/generate_provisional_a1.py` | Reviewed input composition, staging and atomic CLI publication |
| `scripts/finalize_a1.py` | Canonical CSV_FIELDS, readiness/validation, row_to_form and PDF verification |
| `scripts/a1_core.py` | Shared field policy, dates/numbers, casing, flattening, validation and renderer |
| `scripts/a1_quality_gate.py` | Package checks, preview rendering and visual-review receipts |
| `src/document_core/` | Shared local OCR/processing; results remain proposals |
| `portal/release1a/services.py` | Authorized worker/case/revision and artifact adapters |
| `portal/release1a/document_storage.py` | Protected source/derivative keys; no public URL |
| `portal/release1a/j4_artifacts.py` | Separate immutable PDF-package publication and verification |

## 1. Resolve the authorized input snapshot

Operational inputs require `A1_PRIVATE_DIR` pointing at the repository root:

```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
venv/bin/python scripts/generate_provisional_a1.py --help
venv/bin/python scripts/finalize_a1.py --help
venv/bin/python scripts/a1_quality_gate.py --help
```

The baseline is `a1/review.csv`, `a1/cohort.json` and the associated normalized
identity source. Select scoped run snapshots explicitly, reconcile their record
coverage and evidence, and bind their hashes. Do not mix a CSV from one run with
another run's IDs, profiles or identity data. Never use latest mtime, output counts
or another employee's generated PDF as authority.

`config/a1_provisional.json` contains non-personal policy defaults, not employee
identities or a cohort. `config/institutions/` contains office profiles whose status
and evidence must be checked. Keep real inputs, differences and receipts protected;
audit with opaque references and reason codes, not source values in console logs.

## 2. Validate the intended generation mode

The canonical publisher calls finalization validation before rendering. Identity,
certificate and PDF-approval flags are not populated by machine OCR or visual QA.
An existing flag without attributed evidence is an import claim, not proof of a
new human decision. Missing facts are routed to the affected record's review.

For the current self-employed multi-state provisional presentation, Section 5.1
may be blank; Section 5.2 defaults to `DE, CZ`. Preserve explicitly reviewed
territory overrides and keep employee/self-employed profiles distinct.
`readiness --provisional` now uses the same required-field contract as provisional
validation; default readiness still checks authoritative review requirements.
Both retain all human input flags. Provisional preflight does not demand evidence
of issuance; it never upgrades unverified facts or authorizes final promotion.

```bash
venv/bin/python scripts/finalize_a1.py readiness --provisional
```

This uses the selected protected inputs and writes an audited private readiness
receipt. The JSON receipt and sanitized console summary identify `mode` and
`scope=review_preflight`. A ready result is not full normalized-source reconciliation,
PDF generation or artifact QA. The canonical publisher still performs those checks.
Use `readiness` without the flag for the authoritative-evidence preflight.

The proposed unattended draft service must prepare visibly unverified artifacts
without pretending canonical approval flags were confirmed. That new contract
remains implementation work under J4. Final certificate evidence is separate from
application preparation and generated provisional dates/numbers.

## 3. Compose and render through the core

`finalize_a1.row_to_form()` maps the review row and institution profile into the
shared form contract, including Section 4 employment fields. `build_form_data()`
flattens that contract and applies defensive Czech display casing. Preserve accepted
source spelling and provenance separately from the rendered presentation.

Date normalization, issue-date policy, provisional document-ID generation and
period policy live in `a1_core.py`; adapters must not duplicate them. Preserve
evidenced issued values. Proposed coordinator number reservation must reuse the
same provisional number on retries; generating a number never establishes issuance.

The active renderer:

1. Validates form data and loads `templates/a1_background.pdf` with `pypdf.PdfReader`
   and geometry from `config/a1_layout.json`.
2. Draws a ReportLab overlay using measured text and configured checkbox geometry.
3. Adds background pages to a fresh `PdfWriter`, then calls `page.merge_page()`
   with each overlay page. Image streams receive lossless ASCII85 transport encoding.
4. Writes the PDF and reopens it to require three pages and no interactive form fields.

This describes the current implementation, not a general defect claim about another
PDF library. Seeing PDF syntax in a text editor does not inspect rendered output.
Use page previews to assess alignment, duplicated text, clipping and checkbox strokes.
The background and layout form one geometry contract; employee generation must not
reconstruct blank template lines or place opaque masks over unrelated content.

Placeholder search/replace remains a synthetic-tested alternative for a suitable
vector/token template. Before promoting it, reconcile its display helper with the
shared core and prove equivalent input/output behavior across CLI, portal and QA.
A different template alone does not authorize swapping one dashboard call site.

## 4. Publish and verify the actual artifact

The CLI atomically publishes protected `output/provisional/<run_uuid>/` packages.
The portal publisher instead stores `<artifact-root>/<artifact_uuid_hex>/` with
`artifact.pdf`, `snapshot.json`, `page-1.png` etc. and `receipt.json`. Its receipt
covers byte/preview integrity; visual acceptance is separate. Neither path goes
through the other publisher's filename format. See the [storage contract](A1_FRAMEWORKS.md).

Require one static three-page PDF per authorized cohort member, expected values,
unique IDs, no cross-person leakage, and matching input/template/layout/renderer
hashes. Generate previews from those exact PDF bytes. Deterministic geometry/pixel
checks and local visual review cover every page; external free vision is advisory.
Do not reuse an old preview or receipt merely because filenames match.

Package-specific validation remains necessary after regeneration. Unchanged source
code does not make a different employee artifact visually accepted. Conversely,
unrelated documentation edits do not require regenerating PDFs or rerunning all
application tests. Apply the proportional policy in AGENTS.md.

## 5. Confirm, retain and hand off

Keep these states separate: input facts confirmed, artifact generated, artifact
visually accepted, application submitted and certificate issued. Each confirmation
references its actor, time and exact revision or artifact. Changed inputs mark
artifacts stale; previous versions and decisions remain traceable.

Reserved `output/final/` and `output/pdf/` destinations require the separate
receipt-bound promotion contract, authoritative certificate/signatory evidence,
`validated_by_user=1` and explicit artifact approval. Visual PASS alone does not
implement promotion. Working provisional packages remain in place until individually
classified; follow the existing retention/recovery policy rather than ad-hoc backups.

Report protected artifact/manifest locations and relevant acceptance evidence in
[one delivery record](../operations/git-delivery.md). Do not describe a prepared
package as an issued certificate or a source commit as a deployed service.

## Synthetic development and planned database cutover

Use wholly synthetic tests already scoped to the relevant change, for example:

```bash
venv/bin/python -m pytest tests/test_a1_core.py tests/test_finalize_a1.py -q
```

Never build fixtures from operational CSVs, scans or PDFs, or fill unknown
signatories/dates from an example. Existing tests own synthetic setup; operational
artifacts stay in protected storage, never under `tests/fixtures/`.

The [44-field mapping](release-1a-field-mapping.md) defines database ownership,
structured evidence and the single future compatibility-export service. Reconcile
legacy sources first; after accepted cutover, render a selected database snapshot
and treat CSV/JSON as derived exports. The coordinator, fresh development database,
seed reconciliation and release reproducer remain follow-up tasks in the local plan.
