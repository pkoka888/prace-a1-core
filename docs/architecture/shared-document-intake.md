# Shared document intake — synthetic implementation

Updated 2026-09-08. This is implementation documentation, not real-data activation
or evidence that all ENG-001 checks have passed.

## Outcome and boundaries

One Python processor serves the CLI and the existing Django intake. It decodes
PNG/JPEG/TIFF/PDF, detects isolated document boundaries, reads original and
contrast-enhanced crops locally, classifies supported Czech document patterns,
and returns field proposals with coordinates, conflicts and missing information.

The first acceptance set covers **labelled Czech OP, EHIC and passport examples**,
plus ICAO TD1/TD3 parsing. It is not a calibrated recognizer for every issued OP
edition. Occluded/overlapping cards, uncertain boundaries, unsupported countries
and unrecognized layouts remain uncertain. Whole-page fallback is explicitly
marked as an unconfirmed boundary; it is not proof that the page contains one card.
No accuracy percentage for real scans is claimed.

Fields are interpreted from Czech/English labels (including separate label/value
boxes), EHIC numbered fields, and checked MRZ positions. Birth, expiry, issue,
document, insurance and personal identifiers have separate meanings. An MRZ
checksum does not authenticate a document. Two-digit years remain unresolved
until corroborated by a full visual date; no current-date century guessing occurs.

Implementation references:

- [ICAO Doc 9303 Part 5 (TD1)](https://www.icao.int/sites/default/files/publications/DocSeries/9303_p5_cons_en.pdf)
- [ICAO Doc 9303 Part 4 (TD3)](https://www.icao.int/sites/default/files/publications/DocSeries/9303_p4_cons_en.pdf)
- [EU Decision S2, EHIC Annex I](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32010D0424(09))
- Prior government-specimen investigation: unpublished local research at
  `docs/research/2026-09-06-ocr-local-web-workflow-report.md`; not release evidence.

## Local interface

```bash
PYTHONPATH=src venv/bin/python -m document_core --help
PYTHONPATH=src venv/bin/python -m document_core --input path/to/synthetic-front.png path/to/synthetic-back.png --output runtime/portal/temporary/synthetic-intake
```

`--worker-id` supplies requested context only; it never confirms an association.
The result directory uses an opaque UUID. Original bytes, original/enhanced PNG
crops and `result.json` stay together. Successful empty OCR has a hash; failed
inputs have a sanitized error tag and no successful OCR-output hash. Partial
multi-file success is preserved and returns a nonzero exit code.

`DocumentProcessor.process(bytes, workers=(), artifact_sink=None)` returns a
versioned semantic dictionary. `process_batch(..., max_concurrency=4)` isolates
failures and caps concurrent documents at four. Each worker thread owns an engine;
ONNX intra/inter-op threads are capped at one. Model assets must already exist
locally; runtime model downloads are not attempted.

`serialization.canonical_json` is the shared UTF-8 serialization/hash contract.
`result_hash` binds the semantic result; OCR hashes bind the explicitly identified
OCR object. UUIDs and timing are evidence from an execution, so separate executions
are compared semantically rather than by requiring identical entire JSON hashes.
Stored results preserve their region IDs. Sources and crops use content hashes.

## Evidence and matching

Every extracted field remains a proposal. Original/enhanced readings are compared
by field; disagreement preserves both readings and blocks automatic matching.
Coordinates refer to the decoded EXIF-oriented source page. Crops retain their
projective mapping and source-page dimensions.

Side matching requires matching typed document number and issuing country,
complementary sides, and no conflicting identity evidence. Exact duplicate crops
are reported separately. Worker candidates require matching typed identifiers;
names alone cannot associate records. Multiple candidates or contradictory
accepted identity values stay unresolved.

Three outcomes remain separate:

- Coverage: observed sides/pages and missing sides.
- Field sufficiency: required fields, missing values and conflicts.
- Workflow readiness: authoritative acceptance and downstream evidence. OCR never
  makes an application or certificate ready by itself.

## Web integration and persistence

`/documents/intake/` accepts unassigned intake; existing worker upload routes use
the same service. Files must pass declared/detected MIME, extension, byte/page/
pixel limits and structural parsing. A configured scanner must pass; the current
synthetic mode explicitly records `synthetic_not_scanned` when none is configured.
Real-data activation remains refused by this adapter.

Django Storage keeps source bytes under `documents/<uuid>.source`. Each `OcrRun`
has a separate `output_key` and `output_sha256`; crops are under a separate
`generated/<attempt>/<hash>.png` namespace. There is no public storage URL.
Original and derivative reads require scoped capabilities and verify hashes.

`execute_run` is a durable, callable job boundary. Synthetic requests currently
execute it inline; no background daemon is deployed. Conditional database claims,
a 15-minute lease, attempt tokens and a maximum of three total attempts support
retry/recovery. A stale attempt cannot publish over a newer one. Completed runs
are reused. Audit references identify the opaque run/attempt, not extracted text.

`IntakeSession.ocr_runs` allows multiple uploads and duplicate reuse without
re-running OCR. The session view recomputes matching from hash-verified immutable
run results; it does not rewrite those receipts. Review displays original and
enhanced crops, grouping fields by detected document region. Explicit
`DocumentRegionAssociation` records bind regions to workers. Field acceptance
creates `FieldDecision` and a `WorkerIdentityRevision`; it never overwrites worker
fields directly from OCR. Worker detail displays accepted source fields and links
to associated documents. Empty confirmation cannot confirm a document.

Migrations 0008–0009 extend the existing schema; they have **not been applied to a
persistent application database**. The historical-state transition test covers
0007 → 0009 on an isolated database. Earlier migration 0006 and the broader
ENG-MIGRATION gate retain their existing independent limitations.

## Verification and remaining rollout gates

```bash
unshare -Urn venv/bin/python -m pytest tests/test_document_core -q
venv/bin/python scripts/test_document_intake.py
DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python manage.py test tests.m2.test_views tests.m2.test_release1a_vertical tests.document_web.test_intake --noinput
venv/bin/python scripts/validate_planning.py
venv/bin/python scripts/generate_planning_asset.py --check
venv/bin/python scripts/generate_approval_asset.py --check
```

The PostgreSQL harness creates a disposable PostgreSQL 18 cluster beneath project
`runtime/`, uses a private Unix socket with no TCP listener, and stops/removes it.
It does not touch host services or existing databases. Fixtures are generated and
fictional; tests never read employee scans or A1 records.

Real-data scanner/encryption/retention operations, comprehensive tenant/database
constraints, full J4 artifact QA, background deployment and Jan's observed review
remain gate work. Free providers, LiteLLM, portraits and broader country/layout
coverage are deferred. Existing A1 canonical approval/evidence restrictions and
ENG-001 → REV-002 → activation gates → REV-003 remain in force.

## Git delivery checkpoint — 2026-09-08

The shared core and runtime dependencies are committed separately. The portal
package integrates uploads and replacement through the same storage, validation
and OCR pipeline. Replacement preserves old source bytes and run receipts,
serializes version allocation, reuses identical retries and rolls back a newly
stored source when the transaction fails. Late OCR completion cannot reset the
latest document state. Obsolete proposals and region associations cannot be
accepted, and session matching uses current versions.

The current [delivery record](../operations/git-delivery.md) identifies exported
Git snapshots, commands and actual acceptance results. Earlier working-tree counts
are historical evidence only. No persistent database migration, deployment or
real-data activation follows from source publication.
