# Artifact acceptance and minimum J4

Existing IDs: A1-REPAIR-3/5/6 and ENG-J4-SNAPSHOT/PREVIEW/STATE. This is the next
implementation package now eligible after bounded synthetic stabilization acceptance.
Start each write scope only after the integrator releases its files. Codex has not
opened ENG-001; this engineering handoff does not approve final promotion, deployment
or real-data activation.

Read: canonical A1 scripts/config/template; `portal/release1a/` and its migrations;
`portal/templates/portal/`; `src/document_core/`; `tests/document_web/`, `tests/m2/`,
`tests/test_a1*`; ADR-001/002; PLAN-REAL-DATA engineering tables.

Sequential write scopes:

1. **Receipt and promotion worker:** `scripts/finalize_a1.py`,
   `scripts/a1_quality_gate.py`, `tests/test_a1_employee_delivery.py`,
   `tests/test_a1_quality_gate.py`; report
   `docs/research/opencode-a1-receipts-2026-09-06.md`.
2. After handoff, **J4 worker:** `portal/release1a/models.py`,
   `portal/release1a/services.py`, `portal/release1a/views.py`,
   `portal/release1a/urls.py`, a new `portal/release1a/a1_artifacts.py`,
   `portal/release1a/document_storage.py`, `portal/release1a/migrations/0010_a1_artifacts.py`
   (verify current migration head before selecting number), `portal/templates/portal/a1_case_detail.html`,
   `portal/templates/portal/a1_list.html`, `portal/templates/portal/a1_prepare.html`, `tests/document_web/test_a1_artifacts.py`,
   `scripts/test_document_intake.py` test selection if needed; report
   `docs/research/opencode-j4-2026-09-06.md`.

Do not change both scopes concurrently. If an additional path is needed, record
why and obtain integrator ownership before editing it.

Expected behavior:

- `generate` creates a candidate, not final approval. Keep the existing final-path
  rejection until a separate promotion operation proves all requirements below.
- Immutable snapshot binds accepted identity revision, employment/activity evidence,
  requested assignment period (future periods valid), profile, config, layout,
  template and source/code dependency hashes. Reuse existing A1Case; avoid another
  OCR job abstraction. Store derivatives under opaque protected keys.
- Application readiness differs from certificate readiness. Preserve the canonical
  evidence/YES/validated_by_user rules; OCR proposals alone establish neither.
- Render from snapshot bytes, not mutable latest records. Persist actual PDFs,
  all-page previews, deterministic QA and failure receipts; authenticated download
  verifies stored hashes. No generated URL points to a missing artifact.
- QA must verify fresh preview pixels against current PDF renders, not just matching
  filenames/counts. A current weakness remains: existing quality-gate manifests
  hash preview files without proving those pixels came from the current PDFs.
- Final promotion binds PDF hash + snapshot hash + config/dependency hashes + QA
  receipt hash + explicit authenticated human artifact-approval receipt hash.
  Agent visual PASS is not human publication approval. Do not derive approval from
  elapsed time or existing editable CSV flags alone.
- Read/preview/download actions enforce tenant, record, role and action before
  storage access and write non-content audit events. Real-data activation remains off.
- Changes to accepted identity, assignment, institution, template, layout or config
  mark dependent artifacts stale and prevent approval/download-as-current. Calendar
  certificate expiry is advisory, not a substitute for dependency staleness.
- Idempotent jobs, bounded retries, concurrent claim protection and atomic promotion
  must preserve existing bytes on failure. No in-place final PDF edits.

Mandatory synthetic tests: missing/forged/mismatched receipts; changed source, PDF,
preview, config and profile; identical PDF bytes with valid receipts; unauthorized
actor/tenant before file read; repeat requests; worker acceptance revision change;
future assignment; expired lease and concurrent jobs on PostgreSQL; historical
migration 0009→new head through MigrationExecutor; full HTTP prepare/preview/approve/
stale/retry journey. No persistent migration, deployment or real-data upload.

Exit: behavior demonstrated and evidence mapped to each actual ENG-J4 check.
Do not mark ENG-001 open: integrator must run its full current check set afterward.
