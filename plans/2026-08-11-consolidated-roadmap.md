# Consolidated Roadmap — A1 Stabilization to Recruitment Platform

> **Status: Superseded on 2026-08-12.** Retained as historical context. The authoritative execution roadmap is [`../roadmap.md`](../roadmap.md); active bounded work is indexed in [`INDEX.md`](INDEX.md).

**Date:** 2026-08-11  
**Inputs:** historical Plans A/B/C, their review reports, current repository
inspection, `research/2026-08-11-ai-infra-library-findings.md`, and `prd.md`

## Finding summary

The repository is between experimental cleanup and a canonical A1 pipeline. Git
reports **296 uncommitted paths**, specifically 239 untracked, 52 deleted and five
modified. This is not “296 uncommitted commits.” The dated archive contains 323
files. Preserve this state until it has an inventory and intentional checkpoint.

The active provisional output currently has 11 PDFs and 33 previews, matching the
cohort count contract. That count does not prove visual or legal approval.

OpenCode completed useful infrastructure research covering OpenRouter,
PyMuPDF/pypdf, RapidOCR, n8n and LiteLLM. It did **not** complete Plan C's required
product research package: only one research file exists, while personas,
competitors, feeds, OSS candidates, GDPR, architecture scoring, estimates, source
register, open questions and `DECISION_INPUTS_FOR_CODEX.md` are absent.

Test status is not green. System Python lacks pytest. The repository venv reaches
collection but fails because archived `test_parsing.py` is collected and requires
`jsonschema`, while active visual tests require missing `pymupdf`. This indicates
missing dependency/pytest-boundary documentation, not necessarily functional
failures in the active code.

Older OCR documentation is stale: it still presents PaddleOCR and
`scripts/employee_scan_processor.py` as current, although current findings select
RapidOCR v3 and that script is removed from the active tree. It must be archived or
rewritten, not blended into the production instructions.

## Workstream 0 — Freeze, inventory, and recoverability

Goal: make the 296-path migration reviewable without losing history.

1. Capture `git status --porcelain=v1 -uall`, branch/HEAD, and hashes for canonical
   inputs, scripts, template, layout, current provisional PDFs and previews.
2. Generate the Plan B machine-readable inventory and `archive/MANIFEST.md`.
3. Separate source/config/docs/tests from private and generated artifacts. Confirm
   `.gitignore` policy before staging anything.
4. Review all 52 deletions against the 323 archived files; prove recoverability and
   flag anything without an archive/source-control copy.
5. Split the work into reviewable checkpoints (policy/docs, canonical code/config,
   tests, archive manifest, deletion cleanup). Do not make one opaque 296-file
   commit.

Exit gate: every path classified, PII excluded from commits, deletion recovery
documented, and an intentional checkpoint sequence approved.

## Workstream 1 — Stabilize the canonical A1 pipeline

Goal: finish Plan A using deterministic QA as authority and free vision only as an
optional advisory check.

1. Lock `generate_provisional_a1.py → finalize_a1.py → a1_core.py`,
   `templates/a1_background.pdf`, and `config/a1_layout.json` as the active graph.
2. Remove special-person logic and undocumented fallbacks from reusable core code;
   every cohort value must come through authoritative/provisional sources with
   provenance.
3. Resolve the canonical background and builder; archive alternate templates only
   after hash/pixel comparison and manifesting.
4. Implement/verify deterministic field bounding-box, baseline, row-line,
   checkbox, forbidden-legacy-text, widget, page-count, hash and freshness gates.
5. Make pytest ignore `archive/`; declare reproducible dependencies and run focused
   then full active-suite tests.
6. If advisory vision is used, rediscover verified-free image models at runtime,
   batch redacted crops per page, stay within approximately 50 requests/day, record
   provider/model/purpose/date, and stop rather than fall back to paid access.
7. Require operator review and authoritative certificate/signatory evidence before
   promotion from provisional to final.

Exit gate: canonical commands work from documented setup; 11 unique three-page
PDFs and 33 fresh hash-bound previews pass deterministic checks; operator approval
state is explicit.

## Workstream 2 — Finish cleanup and operating documentation

Goal: complete Plan B after the A1 contract is stable.

1. Create `readme-scan-to-employees.md` around RapidOCR v3 local-first processing,
   provenance, conflict handling, manual review, and a minimal-redacted free-model
   fallback only.
2. Create `readme-employees-to-a1-form.md` from the verified canonical commands and
   release-state rules.
3. Create the current-state map, dependency graph, privacy classification, rollback
   instructions, Mermaid validation, and `CLEANUP_REPORT.md`.
4. Archive or rewrite stale PaddleOCR/Context7 plans and every unused generator or
   template variant based on reachability evidence.
5. Keep generated previews/PDFs and raw scans out of source control unless an
   explicit, privacy-reviewed distribution policy says otherwise.

Exit gate: both workflows run as documented with synthetic examples; no active
import reaches archive; every retained top-level script has a purpose; archive and
cleanup reports are complete.

## Workstream 3 — Complete missing product discovery

Goal: finish the unfulfilled portion of Plan C before choosing a web stack.

Required searches and deliverables:

1. Personas/workflows: interview assumptions, reservation meaning, operator roles,
   partner permissions, financial workflow, multilingual support and volumes.
2. Competitors: German/Central-European job portals, staffing platforms, ATS/CRM,
   shift/reservation products and cross-border recruiters, using a uniform matrix.
3. Feeds/syndication: verify BA consume versus HR-BA-XML posting, EURES routes,
   direct employer feeds, partner-only portals, terms, quotas and provenance.
4. Reusable software: compare actively maintained job boards, ATS/CRM, portals,
   headless/admin frameworks, booking, secure documents, finance and audit
   components. Verify license, releases, security, tenancy, localization and fit.
5. Privacy/legal: primary EU/Czech/German sources for lawful basis, OP/ZP necessity,
   retention, controller/processor roles, cross-border recruiting and breach/DSR
   operations. Mark questions for counsel.
6. Social: current Meta permissions, app review, professional-account requirements,
   API limits, media lifecycle, n8n implementation and compliant alternatives.
7. Architecture/cost: score at least three approaches with weights fixed before
   scoring; include self-hosted operations, EU residency, recurring non-AI costs,
   migration risk and sensitivity analysis.
8. Produce all Plan C files plus a self-contained
   `research/DECISION_INPUTS_FOR_CODEX.md` and independent evidence audit.

Do not assume current OpenRouter model names, versions, prices, portal interfaces,
laws or Meta permissions remain stable; reverify them at decision/implementation
time from primary sources. Do not send repository PII during research.

Exit gate: source register complete, claims classified by confidence, options
scored consistently, legal questions separated from technical conclusions, and
the product owner answers the decision list.

## Workstream 4 — Architecture and delivery design

Goal: turn `prd.md` and the completed research into an implementable specification.

1. Select architecture with an ADR; define tenancy, RBAC/record scoping, domain
   model, state machines, APIs/events, storage, audit, retention, backups and
   observability.
2. Threat-model identity documents, partner access, staff impersonation, exports,
   signed URLs, automation credentials and A1 artifacts.
3. Define synthetic fixtures, contract tests, permission matrix, E2E journeys,
   accessibility targets, SLOs, RPO/RTO and deployment environments.
4. Prototype the riskiest slices: secure upload/access audit; partner tenancy;
   application/reservation capacity; A1 handoff; one compliant social publish.
5. Re-estimate MVP and decide build/buy per subsystem after prototypes.

Exit gate: approved ADRs, threat model, data-protection design, vertical-slice
results, prioritized backlog and release acceptance plan.

## Workstream 5 — MVP increments

1. Foundation: auth, organizations, roles, audit events, localization, CI/CD,
   environments and observability.
2. Jobs and public site: partner submission, operator review, catalogue, filters,
   detail and SEO.
3. Candidates: contact/application/reservation, profile, availability, timeline and
   secure documents.
4. Operations: assignments, capacity, notes, notifications, search and history.
5. Finance: planned/actual revenue/cost and export at the approved MVP depth.
6. Integrations: selected feeds, Meta publication, n8n workflows and A1 case handoff.
7. Hardening: permission tests, retention/DSR, restore drill, incident response,
   accessibility, load testing and legal/product acceptance.

## Status update — 2026-08-11 stabilization checkpoint

Verified after the checkpoint commits (`8bd2650`, `5e4b7e1`, `568b4b3`, `215d5dc`).

### Confirmed working
- Test env is deterministic: `venv/bin/python -m pytest -q` → 47 passed, 1 skipped
  (visual-regression placeholder), 48 collected, none from `archive/`.
- Refactored `a1_core.build_form_data`/`normalize_date`; regeneration is
  byte-identical for all 11 PDFs (behavior-preserving for the cohort).
- Deterministic gate passes: 11 PDFs / 33 previews, `set_issues=[]`,
  hash-bound QA manifest, ghostscript check active (`gs` installed).
- Release gates block promotion correctly: all 9 CSV rows remain blocked
  (`certificate_reviewed/approved_for_pdf NO`, `validated_by_user 0`).

### Discoveries / gaps found during review
1. **PII in tracked tree (critical).** `config/a1_provisional.json` carried
   unnecessary identity-card numbers/issuer/validity in `comments`; redacted in
   the checkpoint. The wider tracked tree still contains real employee records
   (`data/employees/*.json`, `data/employees_normalized.json`) and the branch
   lives on a GitHub remote. Confirm remote visibility; if public, treat the
   pushed history as an exposure and stop pushing. Remove PII from the
   authoritative data files before any future push.
2. **Cohort split.** `finalize_a1.py` finalizes only the 9 CSV rows
   (`validate_review` checks against `data/employees_normalized.json`), while
   the provisional generator emits 11 (adds pavel-kaspar, rudolf-kotlar from
   `config/a1_provisional.json`). The two additional people have no reviewed
   CSV rows, so they cannot be promoted via the canonical path; they must be
   merged into the review CSV before finalization.
3. **Birth-number check is male-only.** `finalize_a1.validate_review` compares
   `insurance_number[:6]` to `YYMMDD`; Czech female numbers use day+50 and
   would fail. No checksum verification. Fix before any female cohort.
4. **Issue-date policy mismatch.** `a1_core.validate_provisional_issue_date`
   allows 60–184 days; AGENTS.md documents 61–180. Align code and policy.
5. **`employee_multi_state` renders no checkbox.** Layout defines only
   `status_osv_c_multistate` and `employer_type_self_employed`; the override in
   `generate_provisional_a1.py` sets keys not present in the layout
   (`status_multistate_employee`, `employer_type_employee`). Build-form booleans
   for gender/valid_duration/provisional/transitional are computed but never
   drawn. Add the missing layout checkboxes or drop the dead keys.
6. **Deterministic text checks omit address fields.** Gate `validate_pdf` and
   `finalize_a1.verify_pdf` do not verify residence (street/house_number/city/
   postal_code), birth_place, or nationality in extracted text; address
   correctness rests on visual review alone. Extend required-text checks.
7. **Dependencies not declared.** No `requirements.txt`; the venv was assembled
   ad hoc (pytest 9.1.1, pillow, pypdf, reportlab, jsonschema 4.26.0, pymupdf
   1.28.2, numpy). Pin them for reproducibility.
8. **`archive/MANIFEST.md` missing.** Workstream 0's machine-readable archive
   manifest was never produced for the 52 deletions / 323 archived files.
9. **Stale artifacts still referenced.** `tests/test_comprehensive.py` reads the
   legacy `config/a1_field_coords.json` / `a1_checkbox_coords.json`; docs under
   `docs/paddleocr/` and plans referencing PaddleOCR remain unarchived.
10. **“Watermarked drafts” claim vs output.** `generate_provisional_a1.py`
    docstring says watermarked, but the `NÁVRH – ČEKÁ NA POTVRZENÍ OSSZ`
    notice is never rendered and the gate forbids it. Align intent, code, and
    documentation.
11. **Provenance label bug.** `build_form_data` sets
    `meta.institution_source = "config/institution.json"` even when the source is
    `config/institutions/<profile>.json`.
12. **Unreached legacy scripts** in `scripts/` (`a1_form_generator.py`,
    `generate_corrected_a1.py`, `validate_corrected_a1.py`,
    `reconstruct_checkboxes.py`, `detect_row_geometry.py`,
    `create_verification_artifacts.py`, `create_final_archive.py`,
    `build_clean_background.py`, `a1_core.py.backup`) need a reachability audit
    and archive decision. `data/employees/` is an inconsistent legacy snapshot
    (8 files, includes `example-employee.json`, missing two cohort members).

### Updated immediate next actions
1. Decide remote visibility and the PII-in-history remediation for
   `data/employees/` + `data/employees_normalized.json` before any push.
2. Add `requirements.txt` (pinned) and declare the font dependency (bundle a
   Czech-capable TTF; fix `_register_font` fallback).
3. Extend deterministic text checks to residence/birth_place/nationality.
4. Fix birth-number validation for females; align issue-date policy range.
5. Merge the two additional people into the review CSV; then promote with
   `validated_by_user=1` + authoritative signatory evidence only.
6. Produce `archive/MANIFEST.md`; run the script reachability audit.
7. Clean legacy test/config references; refresh stale PaddleOCR docs.

## Immediate next actions

1. Approve this roadmap/PRD direction and answer the highest-impact open questions
   in `prd.md` section 11.
2. Execute Workstream 0 before touching the 296-path state.
3. Finish A1 deterministic QA and dependencies, then finish the two workflow
   READMEs.
4. Resume Plan C only for the missing product work; keep the completed infra report
   as an input rather than repeating it.
5. Do not select or scaffold the frontend/backend until Workstream 3 produces the
   decision package and Workstream 4 records the architecture decision.

## Status update — repository audit and fail-closed hardening

Completed locally after the stabilization checkpoint:

- refreshed and audited local/remote refs; repository is public, `master` matches
  `origin/master`, and `codex/unified-a1-core` is five commits ahead of its remote;
- confirmed public remote history contains employee/normalized data and generated
  A1 artifacts; stopped all push/publication work;
- added pinned dependencies, a PII-safe tracked/nonignored inventory generator,
  `archive/MANIFEST.md`, `CLEANUP_REPORT.md`, and both workflow READMEs;
- added a safe provisional CLI, exact 61–180-day policy, female birth-number
  prefix handling, profile provenance, and broader deterministic text checks;
- tightened Section 4 handling: employment/business values must be separately
  reviewed and cannot be inferred from identity/residence;
- current suite passes (55 passed, one skipped, 20 subtests);
- current provisional regeneration and QA correctly fail closed until the private
  CSV adds seven explicit reviewed `employment_*` columns.

Blocked on new authority or evidence:

1. GitHub visibility/history remediation (private/rewrite/notification response).
2. Operator review of Section 4 values for all 11 people.
3. Authoritative OSSZ activity/certificate/signatory evidence and user approval.
4. Product-owner answers to `prd.md` section 11 and the missing Plan C research.
