# A1 engineering delivery and OpenCode handoff

**Subsequent stabilization:** current audit/path/publication/QA behavior and acceptance
are recorded in [2026-09-07 stabilization](2026-09-07-a1-stabilization.md). Counts and
remaining-work statements below describe the earlier engineering slice.

Started 2026-09-06; continued/completed 2026-09-07. Working-tree implementation on
`feat/prace-readiness-plan-2026-08-13`, starting HEAD `32daa23`. No commit, push,
production deployment, persistent migration, employee correction, real A1
regeneration or approval was performed. Earlier reports remain dated observations.

## Implemented by Codex

| Area | Actual result | Plan mapping |
|---|---|---|
| Institution validation | VERIFIED no longer admits TBD/doplnit/source-placeholder institution fields. Two falsely verified profiles are NEEDS_VERIFICATION; Louny mapping exists and its unresolved code remains blocked. | A1-REPAIR-1 |
| Reviewed inputs | CSV rejects wrong row width, duplicate headers/people and empty input. Provisional generation calls canonical validation against normalized sources, requires exact cohort agreement, and never substitutes dates/IDs/activity/contact names from config/cohort placeholders. | A1-REPAIR-2/4 |
| Employee profiles | Posted employee maps to 3.1/4.1.1; multi-state employee to 3.2/4.1.1; self-employed multi-state to 3.4/4.1.2. Mapper sets employee kind correctly, uses explicit employer fields and rejects residual OSVČ employer markers on employee rows. | A1-REPAIR-2/3 |
| Presentation | Employee copies omit Section 5 values; underlying activity/source requirements remain. Section 5 is applicable to employees in the actual template, so omission is a user-requested presentation contract. Casing affects uppercase personal/place fields, preserves employer legal names/prose and does not modify source rows. DE-only defaults never override reviewed activity territory. | A1-REPAIR-2/5 |
| Template | Three baked selections (male, 2.4 validity, 5.3 no-fixed-address) removed from the blank canonical background. Hash-guarded repair retained every pixel outside checkbox interiors at 144 and 300 DPI. Gender is now data-driven; unsupported validity/address selections remain false. | A1-REPAIR-2 |
| PDF merge | Attach background pages to PdfWriter before overlay merge. The repaired multi-image background exposed a detached-page resource corruption; all-page integrity tests caught it and pass after the fix. | A1-REPAIR-2 |
| Generation provenance | Candidate/provisional manifests include reviewed snapshot hash and source, normalized input, profiles, layout, background, code/config hashes. Dependency changes during generation reject publication; replace failure restores previous package; generated artifacts use 0600. | A1-REPAIR-5, partial |
| Publication boundary | Rendering rejects reserved output/final and output/pdf destinations, including resolved aliases. finalize generate defaults to output/candidate and reports QA/approval pending. No final-promotion mechanism is claimed complete. | A1-REPAIR-6, containment only |
| Missing evidence | Readiness reports fields, invalid dates, duplicates, profile problems and review/source flags with row indices, not names. CLI persists a 0600 JSON receipt; invalid input replaces a stale successful receipt with sanitized failure. | A1-REPAIR-7, partial |
| Review receipts | Supplied repository root now controls Git checks. Review scope includes shared core, template/config and A1 runtime dependencies. Real disposable-Git tests cover clean, tracked dirty, untracked, wrong commit/hash and missing repository. | PLAN-INFRA / ENG evidence |

The blank template was inspected directly. Earlier reports incorrectly called 3.3
posted employment and treated Section 5 as self-employment-only. The corrected
mapping comes from the actual canonical template, not an inference from filenames.
Repair provenance is in `config/a1_template_repair_2026-09-06.json`; replay tool is
`scripts/repair_a1_template_checkboxes.py`. It rejects any source hash other than
the specified pre-repair shell. `.gitattributes` treats template PDFs as binary.

## Remaining work and boundaries

- **Authoritative data, primary/operator only:** resolve actual identity/employer
  evidence, institute codes, certificate/signatory sources, cohort inconsistencies,
  correction provenance and prior package status. No automatic YES flag updates.
- **Final acceptance/promotion:** immutable human artifact approval and QA receipts,
  current-preview pixel proof, complete promotion validation and crash/concurrent
  publisher handling remain required. Generating hashes alone does not complete
  A1-REPAIR-5/6. Current directory-rename recovery covers caught replacement errors;
  it is not a proof of concurrent-writer or process-crash recovery.
- **J4:** persisted snapshots/artifacts, authenticated previews/downloads, tenant
  authorization, staleness transitions, idempotent durable jobs and HTTP acceptance
  remain a bounded OpenCode work package. Existing A1Case/shared OCR core must be reused.
- **Readiness limits:** row diagnostics do not replace normalized-source comparison
  or full canonical validation. Existing birth-number-style insurance prefix checks
  are preserved; broader insurer identifier schemes need a separate typed contract.
- **QA limits:** production preview freshness currently hashes existing files without
  proving their pixels came from current PDFs. This is explicitly assigned for repair;
  it cannot support final promotion until fixed.
- **Privacy incident:** the previously reported person-linked script in /tmp remains
  a primary/operator containment item. Remote agents must not read/copy it. No host
  changes or deletion were performed during this engineering work.
- Free-provider/LiteLLM extensions remain separate. The user's permission to use
  direct MiniMax m3/m2.7 for OpenCode does not change application OCR free eligibility.

## Reproducible validation

```bash
venv/bin/python -m pytest -q tests/test_a1_core.py tests/test_finalize_a1.py tests/test_a1_quality_gate.py tests/test_a1_employee_delivery.py tests/test_validate_approvals.py tests/test_a1_private.py
venv/bin/python -m pytest -q tests/test_document_core
venv/bin/python -m pytest -q tests/test_a1_private.py tests/architecture/test_a1_boundary.py tests/test_release_verifier.py
venv/bin/python scripts/test_document_intake.py
venv/bin/python scripts/validate_planning.py
git diff --check
```

Final focused A1/approval/private run: **90 passed, 3 subtests passed**.
Document core: **75 passed**. Planning: **24/24 passed**, generated asset current,
34 catalog entries retained. Independent checks: PostgreSQL intake 15 passed;
private/boundary/release-verifier tests 15 passed (verifier unit tests are not an
ENG-001 acceptance run). Template repair checks: six page/DPI comparisons, zero
changed pixels outside declared checkbox interiors. No full-repository green claim.

Synthetic rendering demonstration uses three profiles, three PDFs/nine pages, under
`runtime/portal/temporary/`; these are fictional test records, not production forms.
All-page visual inspection is engineering evidence only, not human artifact approval.

## Ready-to-use OpenCode packet

[Start here](../operations/opencode-work-orders/README.md). Work orders give exact
read/write scope, sequencing, tests, provider constraints and reporting contracts:
independent regression review; artifact receipts/J4 implementation; read-only folder
organization audit; release packaging audit; offline provider safety work. Only the
primary integrates changes and updates authoritative acceptance/gate decisions.

Keep 34 top-level catalog entries and existing child task IDs. Synthetic prerequisite
implementation precedes ENG-001; then REV-002, remaining hardening and OPS/LEG/INF,
then REV-003. No gate was opened by this patch.

Final source diff and relative-link checks passed. Refreshed three-profile synthetic
contact sheets were inspected on all nine pages after the template/merge repairs.
No obvious clipping or lost artwork was observed; this is not approval of real forms.
