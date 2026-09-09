# Independent review and regression tests

Read: canonical `scripts/a1_core.py`, `scripts/finalize_a1.py`,
`scripts/generate_provisional_a1.py`, `scripts/a1_quality_gate.py`,
`scripts/a1_audit.py`, `scripts/a1_paths.py`,
`scripts/repair_a1_template_checkboxes.py`, `config/a1_layout.json`,
`config/a1_template_repair_2026-09-06.json`, `config/a1_provisional.json`,
`config/institutions/`, `templates/a1_background.pdf`, `planning/approval_register.py`,
`src/document_core/`, `portal/release1a/`, relevant tests and plans. Static background
is the sanitized blank form; employee outputs and input scans are outside scope.

Write only after integrator releases each file: `tests/test_a1_cli_journey.py`,
`tests/m2/test_review_fixes.py`, `tests/test_a1_employee_delivery.py`,
`tests/test_a1_quality_gate.py`, `tests/test_validate_approvals.py`,
new synthetic cases under `tests/document_web/`, and
`docs/research/opencode-regression-review-2026-09-06.md`. Coordinate test-file locks.
No production edits in this work order; propose a smallest fix with evidence.

Verify:

- Exact per-row profile mapping: posted employee 3.1; multi-state employee 3.2;
  self-employed multi-state 3.4; employee 4.1.1 versus self-employed 4.1.2.
- Section 5 is applicable to employees on the template. Its omission is this user's
  employee-copy presentation request, not a general legal rule. Activity/source
  prerequisites remain enforced. Ensure 5.3 is not baked into the background.
- Gender is data-driven; no validity/no-fixed-address choice is inferred.
- Reviewed IDs/dates/signatories/territories survive config/cohort conflict unchanged;
  conflicts block generation, not silently override data.
- Original CSV/source stays byte-identical; malformed rows and duplicate IDs fail;
  placeholder profiles fail even when labelled VERIFIED; display casing does not
  mutate source evidence or employer legal names.
- Candidate/provisional output cannot target reserved final paths, including symlink
  aliases. Source changes during rendering block publication. Existing destinations are rejected; a failed new publication leaves no partial
  package. Assert exclusive staging, concurrent writer serialization and process-owned
  cleanup; never delete an existing package to make a test pass.
- Receipt scope uses the supplied root, includes untracked runtime dependencies and
  rejects wrong commit/approval hash. Add symlink, missing executable and unusual
  path cases only when they test a concrete failure mode.
- Template repair is hash-guarded and preserves all pixels outside bounded repairs;
  all three pages remain intact after PDF merge. Do not disable pixel checks to pass.

Run:

```bash
venv/bin/python -m pytest -q tests/test_a1_cli_journey.py tests/test_a1_core.py tests/test_finalize_a1.py tests/test_a1_quality_gate.py tests/test_a1_employee_delivery.py tests/test_validate_approvals.py
venv/bin/python -m pytest -q tests/test_document_core
venv/bin/python scripts/test_document_intake.py
venv/bin/python scripts/validate_planning.py
git diff --check
```

The PostgreSQL harness uses a disposable in-project cluster, not the service DB.
Migration tests must use MigrationExecutor historical states. Never turn a test
failure into a claimed old/stale test without checking the intended contract.

Required stabilization scenarios: audit sequential/concurrent history and failures;
missing actor/organization; ancestor symlinks and outside-root paths; partial-write
and publication failures; all supported profiles through actual render and QA;
mandatory receipts; restrictive permissions; decoded-pixel equivalence despite PNG
encoding differences; changed pixels and recorded DPI; original-input preservation.
Use valid programmatically generated PDF fixtures for M2 intake tests and keep a
separate invalid-PDF rejection case. Assert semantic proposal/audit uniqueness,
not an obsolete assumption that every document yields exactly one proposal.
Restore all modified environment settings between tests. Use local RapidOCR/ONNX;
Tesseract is not a dependency of this backend.
