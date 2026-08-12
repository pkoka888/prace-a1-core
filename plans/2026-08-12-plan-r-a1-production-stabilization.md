# Plan R — A1 Production Stabilization and Reproducibility

**Status:** planned
**Milestone:** A1 operations; separate from portal scaffolding and Git history
**Owner:** primary A1 production agent using `a1-pdf-production`

## Objective

Restore a reproducible canonical provisional package and close deterministic A1
validation gaps without copying issuance data, weakening approval gates, or mixing
the work with portal scaffolding or repository-history remediation.

## Work

1. Reconcile the observed 5-PDF/15-preview output with the canonical 11 unique
   three-page PDFs and 33 hash-bound fresh previews contract.
2. Regenerate or recover only through `.agents/skills/a1-pdf-production/`, canonical
   inputs under `A1_PRIVATE_DIR`, institution profiles, background, and layout.
3. Add the source commit and SHA-256 hashes of generator/core scripts, template,
   layout, profiles/config inputs, and bundled font to generation/QA manifests.
4. Bundle a Czech-capable font in an appropriate tracked asset location, record its
   license/provenance, and fail closed when its runtime hash changes.
5. Add Czech birth-number checksum validation with synthetic unit/boundary cases;
   do not place real identifiers in tests or documentation.
6. Keep `employee_multi_state` disabled until its complete geometry and checkbox
   behavior pass deterministic and all-page visual verification.
7. Classify `scripts/validate_ocr_proposals.py` as deferred/non-executable by
   default. Do not use its mutating `--fix` behavior until schema, atomicity,
   provenance, privacy, tests, and explicit operator-review semantics are redesigned.
8. Inventory stale output backups by path, timestamp, counts, hashes, and canonical
   relevance without opening PII in prompts or deleting anything. Propose deletion
   only after canonical reconciliation and obtain explicit approval.

## Verification

- Pre-generation schema/completeness and template/layout integrity checks pass.
- Exactly 11 unique PDFs, three pages each, and 33 matching fresh previews exist.
- Manifest hashes bind source commit, scripts, inputs, template, layout, and font.
- Geometry/pixel, parser, cross-person leakage, clipping/overlap, checkbox, and
  Czech-text checks pass; every page receives local authorized visual review.
- `validated_by_user=1` plus authoritative evidence remains mandatory for promotion.
- Relevant unit/integration/regression tests and `git diff --check` pass.

## Deferred OCR validator classification

Review on 2026-08-12 confirmed that the untracked
`scripts/validate_ocr_proposals.py` is **non-executable project input** and must
not be staged, committed, or run against operational data in its current form.
It is not part of the canonical A1 pipeline.

The redesign gate remains open because the draft:

- offers an in-place mutating `--fix` mode without atomic publication,
  provenance, or operator confirmation;
- prints employee identifiers and field values to standard output;
- accepts a literal missing-data placeholder instead of failing closed;
- derives birth-date/sex data without the required complete Czech birth-number
  date and checksum contract;
- has no approved proposal schema, privacy/logging contract, or synthetic tests.

Any successor must be implemented from a reviewed specification with synthetic
fixtures, non-mutating validation by default, redacted diagnostics, and an
explicit human-confirmation boundary. The existing untracked draft is preserved
only pending a separate disposition decision; this plan does not authorize its
deletion or replacement.

## Exit gate

The canonical cohort is reproducible from authorized sources, all manifests and
previews are hash-bound, the font and birth-number validation are deterministic,
disabled/deferred paths cannot run accidentally, and backup disposition awaits a
separate explicit decision.

## Exclusions

No portal scaffolding, history work, remote publication, real-data copy, ad-hoc
backup, output deletion, or promotion of provisional artifacts.
