# A1 session and document-intake architect review — 2026-09-06

Review of the two supplied session/gap reports against the working tree at
`32daa23` (HEAD). This is a working-tree review, not release approval. Reports are
claims; current code, aggregate protected-data checks and fresh tests take
precedence. No employee values or scan extracts are reproduced here.

## Outcome

Keep the shared document core and existing web adapter. Repair employee A1 support
inside the canonical generator, mapper, renderer and verifier. Do not adopt the
one-off script as another production path. The urgent PDFs demonstrate rendering,
but do not establish correct employment evidence, reproducibility or issuance.
Technical classification and missing-evidence routing remain automatic; acceptance
of authoritative values and certificate publication retain existing gates.

## Verified current state

- CSV: 25 rows, no row-width mismatch, four `employee_multi_state` rows; all 25
  blocked by canonical `readiness_report`, zero with all three AUTHORITATIVE source
  statuses. A structurally valid row does not prove its values are correct.
- Four corresponding provisional PDFs exist, each three pages; all contain `TBD`.
  None equals its corresponding final-directory file (including absent counterparts).
  Overall: 26 provisional PDFs and 25 final PDFs. Earlier whole-package hash equality
  is a dated baseline, not the current state or a criterion for approval.
- All four employee rows still have an OSVČ marker in employer names; two employer
  IDs equal the insurance number. These are unresolved input-evidence defects.
  Exact uppercase OSVČ was not found in the four extracted PDF texts; the report's
  claim about identical displayed employer placeholders is not independently proven.
- Relevant Louny office-label/profile-slug mappings agree now. Louny profile exists
  but is untracked, `NEEDS_VERIFICATION`, with code/date `TBD`. Kladno and Ústí profiles
  still say VERIFIED with placeholders. The gap report's claimed revert is absent.
- Canonical A1 scripts and layout have no changes against HEAD. The tracked A1 policy
  change is global `activity_address: DE`; `employment_mode` remains self-employed.
- `/tmp/regenerate_4.py` still exists, contains person-linked literals and a direct
  renderer call; no canonical readiness or quality-gate call was found. This is a
  confirmed storage-boundary violation, reported to the user. Preserve minimal
  protected evidence and arrange authorized containment; do not publish/copy this
  script into tracked source. This review did not delete or relocate it.

Protected reads were audited locally with opaque review events under `evidence/`.
No scan identity was re-adjudicated, no record corrected, and no visual QA approval
was issued. The skill still specifies an 11-person/33-preview cohort contract, while current
counts differ; reconcile the authorized cohort contract before generation rather
than adopting observed file counts. Historical CSV corruption, who edited each field, actual transmission
to a recipient, and the complete provenance of the one-off run remain unverified.

## Code findings and corrections to the reports

| Finding | Assessment and consequence |
|---|---|
| Employee generation unsupported | Confirmed: `generate_provisional_a1.generate` checks global config mode and rejects any mode except self-employed. It does not correctly dispatch by row profile. |
| More than missing checkbox coordinates | `finalize_a1.row_to_form` hard-codes `employment.kind=self_employed` and always fills activity; `verify_pdf` expects activity text. `a1_core.build_form_data` maps employee_multi_state to status_posted_employee. Repair these together before adding calibrated employee checkbox coordinates. |
| Missing employer evidence | An expected independent input requirement, not permission to derive employer identity/address from a worker's residence or OP. Keep intake drafts valid while export readiness names missing evidence. |
| Insurance number | Required by current form validator. Do not waive it or silently substitute a birth number/insurer code. Document type/side alone does not establish an insurance field's authority. |
| Identity/date claims | The report calls a non-leap-year February 29 valid; it is invalid. OP1 priority, shared first name, filename or model transcription cannot resolve conflicting identity evidence. Retain the competing proposals and source regions; accepted corrections need provenance. |
| Slug rejection | Correct boundary behavior. Fix office mapping upstream; do not relax `_slug` to accept arbitrary display names/paths. |
| Casing | Provisional path calls `czech_display_case`; final mapper does not. The helper preserves diacritics and is intended for names/places. Do not title-case activity prose or legal employer names indiscriminately. |
| Zero web tests / two OCR failures | Outdated: fresh 75 core tests and 15 PostgreSQL intake tests pass, including historical migrations and HTTP intake. |
| Legacy parser still in services | Outdated: legacy classification/proposal functions are gone; `process_intake_document` delegates to shared intake. No parallel parser should be introduced. |
| Untracked runtime imports | Confirmed packaging risk. Current checkout works, but a partial future commit/deployment can omit modules, templates, migrations or tests. Untracked work is expected before authorized publication; it is not evidence of a deployed outage. |
| Receipt gate coverage | Confirmed gap: one wrong-approval-hash test exists; no focused clean-scope/expected-commit success-and-failure coverage. `src/document_core/` and the dedicated intake harness are missing from review scope. |
| Circular dependency | Child plan already permits synthetic implementation. Clarify parent acceptance wording: ENG-001 consumes prerequisite implementation evidence; it does not prohibit building that evidence. |
| Sprint files | No separate sprint file is necessary. Treat existing sprint task tables as ordered delivery batches and track evidence there. |
| Slow verifier / conflicting_instructions | Secondary review items; reported timing is not freshly benchmarked. Do not replace PostgreSQL concurrency/migration proof with SQLite to gain speed. Inspect whether the conflict marker represents unresolved policy before changing enforcement. |

## Authoritative clarification

Posted work and activity in multiple states are distinct situations in
[ČSSZ posted-worker guidance](https://www.cssz.gov.cz/vyslani-pracovnici) and
[ČSSZ multi-state guidance](https://www.cssz.gov.cz/soubezny-vykon-cinnosti).
The implementation must distinguish the profile and checkbox mapping from confirmed
assignment/employment evidence; a DE-only display preference cannot decide legal
classification. The actual A1 template must be inspected before assigning positions.

The [official Louny contact page](https://www.cssz.gov.cz/web/cz/kontakty/region/ossz/ustecky-kraj/louny)
confirms the configured office address and named director as of this review. It
supplies neither an A1 issuance decision nor proof that this contact signed an
individual certificate. Its data-box ID is not a substitute for the A1 institution code.

## Simplified next delivery batches

1. **A1 evidence and package reconciliation (A1-REPAIR-1/4/5/6/7).** Reject placeholder
   profiles; reconcile selected rows, artifacts and current source hashes; preserve
   previous artifacts with truthful provisional/stale status. Resolve duplicate
   identity proposals and contaminated employer inputs in protected versioned records.
   Missing source evidence routes to the responsible operator; no automated approval.
2. **Canonical employee support (A1-REPAIR-2/3).** One profile contract drives mapping,
   required fields, Section 4 employer data, Section 5 omission, checkbox selection,
   field-specific casing and PDF expectations. Scope DE-only placement to confirmed
   assignment/policy instead of silently altering unrelated cohorts. Preserve canonical
   authoritative restrictions; update the stale DE/CZ test and skill wording only
   alongside the implemented intended contract. Synthetic tests must cover employee,
   self-employed and mixed cohorts, missing employer/insurance evidence, unsupported
   profile, no activity text, checkbox pixels, and unchanged template artwork.
3. **Integration closure (existing OCR-CORE and ENG checks).** Keep the shared core;
   extend receipt-scope checks to all transitive runtime dependencies and test clean,
   dirty, untracked, wrong commit and wrong approval-hash cases. Prepare a complete
   explicit publication path list including migration dependencies. Commit/push only
   when requested; validate an exported committed snapshot before release claims.
   Complete minimum J4 stored snapshots, previews/all-page QA and stale-state handling
   before ENG-001, then REV-002 and remaining activation gates.

Free-provider/LiteLLM connections, portraits and broad document coverage remain
extensions. None resolves the present employer/certificate evidence gaps.

## Fresh checks

| Command | Result |
|---|---|
| `venv/bin/python -m pytest -q tests/test_document_core tests/test_validate_approvals.py` | 96 passed: 75 core + 21 approval tests |
| `venv/bin/python scripts/test_document_intake.py` | 15 passed on disposable PostgreSQL; no persistent DB migration |
| `venv/bin/python -m pytest -q tests/test_a1_core.py tests/test_finalize_a1.py tests/test_a1_quality_gate.py` | 34 passed, 2 failed; 3 subtests passed |

A1 failures: the tracked policy test expects DE, CZ while config says DE; verified
profile test detects placeholder code. These failures remain visible; this review
updates planning rather than hiding failures or modifying production data. Structural
planning checks do not establish A1 readiness or production acceptance.

Planning validation after updates: 24/24 passed; generated planning asset current,
approval asset unchanged/current, 34 catalog items preserved, relative links and
`git diff --check` clean. No production code/config, employee inputs or A1 PDFs
were changed by this review; no commit, push, deployment or approval was performed.
