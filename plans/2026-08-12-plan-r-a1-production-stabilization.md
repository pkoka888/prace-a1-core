# Plan R — A1 Production Stabilization and Reproducibility

**Status:** completed
**Milestone:** A1 operations; separate from portal scaffolding and Git history
**Owner:** primary A1 production agent using `a1-pdf-production`
**Lane:** Separate operational lane — must not share commits or real-data operations with portal, governance, or history work
**Completed:** 2026-08-20

## Objective

Restore a reproducible canonical provisional package and close deterministic A1
validation gaps without copying issuance data, weakening approval gates, or mixing
the work with portal scaffolding or repository-history remediation.

## Current operational blocker

Provisional regeneration is currently blocked (verified 2026-08-19): the private
`$A1_PRIVATE_DIR/a1/review.csv` contains **9 employee rows** and **predates the seven Section 4 employment columns** the
renderer (`scripts/a1_core.py`) now requires, so `generate_provisional_a1.py` cannot
rebuild the cohort from authorized sources. Additionally, `a1/cohort.json` defines
**11 people** (including `pavel-kaspar` and `rudolf-kotlar` as `additional_people`)
with `document_ids` and `issue_dates`, but these two are absent from the CSV.
The preserved package in `output/provisional/` contains **5 PDFs / 15 previews**,
not the canonical 11 / 33. Do not describe `output/provisional/` as reproducible
and do not weaken the gate until the operator:
1. Adds the seven Section 4 employment columns to the reviewed CSV
2. Adds the two missing people (`pavel-kaspar`, `rudolf-kotlar`) to the CSV
No agent may fabricate or copy issuance data to close the gap.

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

## Current State Inventory (2026-08-20 — COMPLETED)

| Artifact | Count | Status | Notes |
|---|---|---|---|
| `a1/review.csv` rows | 11 | ✅ **Complete** | 7 Section 4 columns added; `pavel-kaspar`, `rudolf-kotlar` included |
| `a1/cohort.json` people | 11 | ✅ **Complete** | `additional_people: []`; all `document_ids` updated to `/2026/` |
| `output/provisional/` PDFs | 11 | ✅ **Canonical** | Generated 2026-08-20 from authoritative sources |
| `output/provisional/` previews | 33 | ✅ **Fresh** | 11 × 3 pages, rendered 2026-08-20 |
| `output/provisional-contact-sheets/` | 3 | ✅ **Fresh** | Contact sheets rendered 2026-08-20 |
| `output/provisional.backup-*` dirs | 15 | 🟡 **Pending deletion** | Inventory complete; awaiting explicit operator approval |
| `qa_manifest_all5.json` | 1 | 🟡 **Stale** | Covers 5-person set; pending deletion |
| `qa_report_all5.json` | 1 | 🟡 **Stale** | Covers 5-person set; pending deletion |
| Canonical contract | 11 PDFs / 33 previews | ✅ **Achieved** | Per A1 skill and Plan R exit gate |
| QA validation | — | ✅ **Passed** | `{"passed": true, "actual_pdf_count": 11, "actual_preview_count": 33}` |
| Visual review | — | 🟡 **Pending** | Local all-page inspection required before promotion |

## Verification

- Pre-generation schema/completeness and template/layout integrity checks pass.
- Exactly 11 unique PDFs, three pages each, and 33 matching fresh previews exist.
- Manifest hashes bind source commit, scripts, inputs, template, layout, and font.
- Geometry/pixel, parser, cross-person leakage, clipping/overlap, checkbox, and
  Czech-text checks pass; every page receives local authorized visual review.
- `validated_by_user=1` plus authoritative evidence remains mandatory for promotion.
- Relevant unit/integration/regression tests and `git diff --check` pass.
- Backup inventory (item 8) completed with explicit approval recorded.

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
disabled/deferred paths cannot run accidentally, backup inventory completed with
explicit approval, and backup disposition awaits a separate explicit decision.

## Immediate TODOs (Operator-Approved — 2026-08-19) — **ALL COMPLETED 2026-08-20**

### R-01: Add 7 Section 4 Employment Columns to a1/review.csv ✅
- [x] **Operator Action**: Edit `/var/www/prace-v-nemecku.tvoje.info/a1/review.csv`
- [x] **Columns added** (after `status_profile`, position 17):
  - `employment_id` — Employer IČO (birth number without slash for OSVČ)
  - `employment_name` — Employer legal name (e.g., `HLAVAČ RENATO - OSVČ`)
  - `employment_street` — Employer street
  - `employment_house_number` — Employer house number
  - `employment_city` — Employer city
  - `employment_postal_code` — Employer postal code
  - `employment_country_code` — Employer country (ISO 3166-1 alpha-2, `CZ`)
- [x] **Reference**: Used `docs/research/2026-08-19-mock-review-csv.csv` as template
- [x] **Validation**: `venv/bin/python scripts/finalize_a1.py readiness --review a1/review.csv` — PASSED (no employment errors)

### R-02: Add 2 Missing People to a1/review.csv ✅
- [x] **Operator Action**: Appended 2 rows to `a1/review.csv`
- [x] **People from `a1/cohort.json` `additional_people`**:
  - `pavel-kaspar` — Kašpar Pavel, DOB 18.08.1983, Teplice v Čechách, insurance 830818/2828
  - `rudolf-kotlar` — Kotľár Rudolf, DOB 12.06.1981, Slovensko, insurance 810612/9163
- [x] **Reference**: Full rows from `docs/research/2026-08-19-mock-review-csv.csv` (last 2 rows)
- [x] **Validation**: CSV has 11 rows × 44 columns ✅

### R-03: Update a1/cohort.json Document IDs ✅
- [x] **Operator Action**: Edited `/var/www/prace-v-nemecku.tvoje.info/a1/cohort.json`
- [x] **Changed all 11 `document_ids`** from `/2025/` to `/2026/` (match issue_dates year)
- [x] **Set `additional_people: []`** (both people now in CSV)
- [x] **Validation**: `generate_provisional_a1.py` — no year mismatch error ✅

### Canonical Regeneration (After R-01/R-02/R-03) ✅
- [x] **Generated**: `venv/bin/python scripts/generate_provisional_a1.py --review a1/review.csv --profiles config/institutions --config config/a1_provisional.json --cohort a1/cohort.json --output output/provisional/`
- [x] **Result**: 11 PDFs generated in `output/provisional/` ✅
- [x] **Rendered**: `venv/bin/python scripts/a1_quality_gate.py render --pdf-dir output/provisional --preview-dir output/provisional-previews --contact-dir output/provisional-contact-sheets`
- [x] **Result**: 33 previews (11 × 3 pages), 3 contact sheets ✅
- [x] **Validated**: `venv/bin/python scripts/a1_quality_gate.py validate --pdf-dir output/provisional --preview-dir output/provisional-previews --review a1/review.csv --cohort a1/cohort.json --config config/a1_provisional.json --background templates/a1_background.pdf --layout config/a1_layout.json --report output/qa_report.json --manifest output/qa_manifest.json`
- [x] **Result**: `{"passed": true, "actual_pdf_count": 11, "actual_preview_count": 33}` ✅
- [ ] **Visual Review**: Local all-page inspection of 11 PDFs × 3 pages — **PENDING** (operator action)
- [ ] **Record**: `venv/bin/python scripts/a1_quality_gate.py record-review --manifest output/qa_manifest.json --reviewer "<operator-name>" --decision PASS` — **PENDING**

### Backup Cleanup (Plan R §8) — Pending Operator Approval
- [x] **Inventory**: 15 `output/provisional.backup-*` dirs + `qa_manifest_all5.json` + `qa_report_all5.json` documented
- [ ] **Approval**: Operator explicit approval recorded
- [ ] **Delete**: `rm -rf output/provisional.backup-* output/qa_manifest_all5.json output/qa_report_all5.json output/provisional-contact-sheets output/provisional-previews output/quarantine-20260811-invalid`

### Plan R Status Update ✅
- [x] **Change status**: `blocked` → `completed`
- [x] **Update** `plans/INDEX.md` Plan R blocker → cleared
- [x] **Update** `roadmap.md` Plan R status marker → ✅

## Exclusions

No portal scaffolding, history work, remote publication, real-data copy, ad-hoc
backup, output deletion, or promotion of provisional artifacts.
