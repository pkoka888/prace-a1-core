# Plan 2026-09-06-OCR-SHARED-CORE-LOCAL — Shared Document Intake

**Status**: active
**Milestone**: M3
**Parent**: PLAN-WORKERS

## Goal

Upload scans/photos → identify document regions and sides → extract and compare
field proposals → associate evidence with worker drafts → show coverage,
missing information and readiness. One Python core serves local and web intake.

## Current implementation

The bounded synthetic local/web path is implemented; Git snapshot acceptance
and publication are recorded in the [delivery record](../docs/operations/git-delivery.md).
[Implementation contracts and reproducible checks](../docs/architecture/shared-document-intake.md)
describe actual interfaces, storage, supported patterns and limits. This is not a
release acceptance or real-data activation claim. Task IDs are preserved below;
completed synthetic acceptance does not imply all document editions are calibrated.

## Infrastructure review checkpoint — 2026-09-07

The unpublished local application review (`docs/research/2026-09-07-infra-application-review.md`)
adds actual offline Chromium and two-engine synthetic evidence. RapidOCR stays the
intake default; optional Tesseract/fallback is not wired into production processing.
Both engines make field errors. This is not document-edition calibration or authority
for automatic acceptance. Existing task IDs and active status remain unchanged.
The OCR review route now matches the view/template document_pk contract.

## Dependencies and defaults

- PLAN-INFRA: engineering/storage/deployment evidence; synthetic implementation may proceed.
- PLAN-A1: existing canonical evidence and approval restrictions remain unchanged.
- Local RapidOCR first; model assets preinstalled, no runtime network required.
- External providers, LiteLLM, portraits and broader country coverage remain deferred.
- Technical processing and routing are automatic; authoritative acceptance is explicit.
- Preserve original bytes, provenance and existing OcrRun lifecycle conventions.

## Tasks and acceptance evidence

### OCR-CORE-1: Shared core

Implemented: framework-independent types, decoding, segmentation, classifier,
field interpreter, matcher and processor. Engine imports are confined to the
adapter and lazy default-engine construction. Synthetic package tests required.

### OCR-CORE-2: Document segmentation

Implemented: bounded image/PDF decoding, page indices, isolated quadrilateral
boundaries and crop-to-page mappings. Mixed-image and PDF tests required.
Uncertain boundaries remain an explicit whole-page fallback; no claim of robust
segmentation for overlapping or occluded cards.

### OCR-CORE-3: Classification

Implemented: supported Czech labelled OP/EHIC/passport and TD1/TD3 patterns.
Unknown country/layout returns null type with uncertainty; unmatched sides remain
independent of pairing. Visual document edition remains null unless established.

### OCR-CORE-4: Field interpretation

Implemented: labelled dates, typed identifiers, names, residence text, EHIC numbered
fields and checked MRZ positions. Exact field tests cover invalid dates, separate
labels/values, bilingual labels, birth versus expiry and identifier distinctions.
Unresolved MRZ centuries do not become invented full dates.

### OCR-CORE-5: Side matching

Implemented: complementary sides, same typed document number/issuer, conflict and
ambiguity detection. Matching is an evidence proposal; filename and upload order
never determine a match. Session matching spans independent file uploads.

### OCR-CORE-6: Worker association

Implemented: unassigned intake and candidate proposals from accepted typed
identifiers; names alone are insufficient. Explicit per-region human associations
and accepted field decisions create worker identity revisions. Mixed uploads do
not implicitly belong to the worker named in upload context.

### OCR-CORE-7: RapidOCR adapter

Implemented and repaired: UUID4 regions, aligned vendor arrays/tuples, typed
malformed-output errors, actual package version and elapsed milliseconds including
empty results. Public results contain immutable normalized data, not mutable raw
vendor objects. Tests cover every prior regression.

### OCR-CORE-8: Completeness

Implemented: side coverage, field sufficiency and workflow readiness separately.
A valid front-only crop may provide identity fields while missing back-side
coverage. OCR cannot claim authoritative application/certificate readiness.

### OCR-CORE-9: Original/enhanced verification

Implemented: both crops retained and read; field-level differences, classification
disagreements and source coordinates retained. No pixel threshold certifies OCR
accuracy. Conflicts are preserved instead of silently choosing one reading.

### OCR-CORE-10: Bounded processing

Implemented: local batch limit four with thread-owned engines and isolated
failures; one ONNX intra/inter-op thread per engine. The current synthetic HTTP
path queues durable OcrRun work; scoped `process_ocr` consumes it sequentially.
The shared callable also supports synchronous use. The rehearsal lifecycle owns
its worker process; intended-host deployment is not established by source inspection.

### OCR-CORE-11: Provenance

Implemented: original bytes, crop/operation hashes, actual engine version,
source geometry, canonical output hashes and immutable persisted run receipts.
Session-level matching is a derived view over those receipts. Non-content audits
use opaque references. Retention/deletion operations remain rollout prerequisites.

### OCR-CORE-12: Local CLI

Implemented: `PYTHONPATH=src venv/bin/python -m document_core` accepts one or more
`--input` paths, optional requested `--worker-id`, and `--output`. Results and
originals/crops use opaque or content-addressed filenames. Atomic publication,
mandatory writable-storage failure receipts, sanitized errors and partial-success
handling are covered by tests. Successful empty OCR still receives an output hash.

### OCR-CORE-13: OcrRun integration

Implemented with migrations 0008–0009: protected original/version bytes; separate
run output keys/hashes; session reuse; per-region proposals/associations. Existing
pending/running/completed/failed states, timestamps and failure_reason remain.
Conditional claims, bounded attempts, leases and fencing prevent duplicate or
stale publication. Tenant denial, hash corruption, retries, CLI/web semantic
parity, PostgreSQL concurrency and MigrationExecutor transitions are tested.
No persistent application migration or real-data activation is included.

### OCR-CORE-14: Real offline OCR proof

Implemented: real RapidOCR processes generated synthetic images with exact text
and date assertions, plus full OP/EHIC/passport labelled examples. Execute the
suite with networking disabled at OS level. Deterministic MRZ/matching edge cases
also use scripted engine outputs; those are not advertised as real-scan accuracy.

## Recovery, quality and LangGraph follow-up — 2026-09-16

The [dependency/orchestration review](../docs/research/2026-09-16-document-orchestration-review.md)
is research, not architecture approval. Current baseline `4a38067` plus identified
unstaged PG/dependency changes passed three real generated-document OCR cases under
OS network isolation and 18 isolated SQLite worker tests. Neither result establishes
real-scan accuracy, PostgreSQL concurrency, cold bootstrap or intended-host acceptance.
Keep the existing RapidOCR processor, OcrRun jobs and revision-bound Django review.

| Existing task / priority | Bounded TODO and owned paths | Acceptance / expected result | Owner |
|---|---|---|---|
| OCR-CORE-14 / next | Extend existing synthetic helpers/tests and benchmark contract after reviewing inherited benchmark changes; label document family, field and degradation | Exact critical-field errors, unresolved/false-confident proposals, original/enhanced disagreement, correction count; clean/rotated/blurred/missing-side/unsupported/invalid-MRZ cases. No auto-confirmation or invented dates. Real representative calibration is separately scoped | OCR engineering |
| OCR-CORE-10/11 / next | Measure queue/stage/retry cost in existing processor/worker; preserve opaque diagnostics. Own `src/document_core/`, `portal/release1a/document_intake.py` and focused tests | Cold/warm latency, peak memory, attempt categories and repeated work identified by source/model/config; no text or image content in logs. Derive a timeout/resource budget from measurements, not package presence | OCR engineering |
| OCR-CORE-10/13 / after measurement | Fix measured native-call deadline/recovery gaps using existing owned process patterns; review applicability of CLI-only fallback before portal integration | Hung engine bounded and reaped; expired/duplicate/stale attempts cannot publish or confirm; one explicit job owner; current worker retry and source-replacement tests remain green | runtime + OCR engineering |
| OCR-CORE-10/11/13 / optional experiment | At most two engineering days comparing existing whole-run recovery, minimal Django stage receipts and a thin local LangGraph adapter. Synthetic-only isolated environment; no source/runtime adoption implied | Same engine/model/corpus; fault injection around domain publication and checkpoint commit; duplicate/cross-tenant/stale/revoked resume refused; restart resumes completed stages without repeating OCR; report latency/storage/maintenance tradeoff. No canonical venv change or paid/cloud dependency | OCR engineering; primary reviews result |
| OCR-CORE-13 / adoption decision | Record adopt/defer against existing ADR-001/002 and the simpler Django alternative; preserve current domain authority | Demonstrated recovery or workflow-maintenance gain justifies dependencies/checkpoint operations. Keep tenant authorization, FieldDecision/AuditEvent, retention, graph-version compatibility and rollback. If benefit is absent, retain current worker and stage receipts | primary + architecture owner |

LangGraph may coordinate stage recovery, bounded local fallback and waiting for a
human/missing side. It does not improve recognition by itself or replace human
confirmation. Do not hold the OcrRun lease across human waiting, store scans in
checkpoint state, or introduce a second scheduler. Resume authorization and source
revision are rechecked through existing domain services. Proposed graph APIs and
versions must be validated in the isolated experiment before documentation calls
them supported. No new top-level catalog ID or Release 1A gate is introduced.

The dependency/bootstrap TODO belongs to REL-03/05 in the delivery plan; the newly
reproduced PostgreSQL cleanup-env regression belongs to JAN-04. These repairs and
JAN core acceptance take priority over optional orchestration experimentation.

## Exit evidence and next gates

Run the commands in the implementation document. Record actual results in the
handoff; do not substitute a test count or planning validator for behavioral
proof. Keep this plan active until the broader M3 coverage and observed web
workflow acceptance are satisfied.

Maintain the 34 top-level catalog IDs and this child link. Minimum functioning J4
remains before ENG-001; then REV-002, remaining hardening/operational/legal/
infrastructure evidence, REV-003 and real-data activation. None of those approval
records is changed by this implementation.

Engineering checkpoint 2026-09-07: unpublished local runtime/J4 delivery (`docs/research/2026-09-07-runtime-j4-engineering.md`) records actual stored canonical PDF/QA/preview evidence, protected delivery and disposable migrations. This does not authorize visual acceptance, final promotion, service deployment or gate opening. Existing task IDs retained.


## Version replacement checkpoint — 2026-09-08

OCR-CORE-13 now routes supersession through shared intake, preserves original
versions and immutable run receipts, and rejects obsolete proposals/associations.
PostgreSQL tests exercise duplicate replacement concurrency and late OCR completion.
See the current delivery record for commit-bound results. OCR-CORE-1 through
OCR-CORE-14 and this plan remain active; observed acceptance and activation gates
are unchanged.
