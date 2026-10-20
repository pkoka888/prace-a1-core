# A1 data architecture — file inventory, variants, and gap analysis

**Status:** analysis and recommendation. No cutover, migration or activation is
claimed or performed by this document.

**Scope:** why worker/A1 data currently lives in several files, what each file is
authoritative for, which consolidation variants are viable, and which gaps the
current workflow actually exhibits. Read with
[PLAN-WORKERS-MIGRATE-TO-DB](../../plans/PLAN-WORKERS-MIGRATE-TO-DB.md) (DB-MIG-1
through DB-MIG-7) and
[release-1a-data-contract](release-1a-data-contract.md).

**Terminology — do not confuse with the generator variants.** The letters
**A/B/C** below are *data-model* variants (where worker data lives). They are
unrelated to the **V1–V8** *generator* variants catalogued in
[A1_FRAMEWORKS.md](A1_FRAMEWORKS.md) (which renderer produces the PDF). A
document-model choice and a renderer choice are independent axes. For
document-parsing/OCR technology choices, see
[2026-10-20 document-automation SOTA review](../research/2026-10-20-document-automation-sota-review.md).

---

## 1. Diagnosis: three data classes share one directory name

`a1/` is not one dataset. It holds three classes with **different authority**,
and the confusion is structural, not cosmetic.

| Class | Files | Authority | Mutability |
|---|---|---|---|
| **1. Sources / facts** | `a1/employees_normalized.json`, `a1/review.csv` | Identity, residence, employment, activity, certificate *candidates* | Edited during review |
| **2. Issuance authority** | `a1/cohort.json` | Which employees the issuer will cover, and the issued `issue_dates` / `document_ids` | Set by the issuing decision, not by OCR |
| **3. Derived views** | `a1/review.csv` (as produced by `prepare_review`), `config/institutions/*.json` join | Flattened/compat projection for the legacy generator | Regenerable from (1) + policy |

The real coupling is narrow and specific:

```
finalize_a1.prepare_review(employees_normalized, address_enrichment, institution)
    -> a1/review.csv                      (44 canonical columns, CSV_FIELDS)
generate_provisional_a1.build_provisional_rows(review, institutions, policy, cohort)
    -> requires set(cohort.issue_dates) == set(review.employee_id)
    -> requires cohort.document_ids[id] == review.document_id   (per row)
    -> rows -> row_to_form(row, profile) -> a1_core.build_form_data -> PDF
```

So `cohort.json` is **not** a second employee list. It is the issuer's
commitment record: which of the reviewed employees get a certificate number and
an issue date. `generate_provisional_a1.py:148-154` enforces set equality
*and* per-row value equality — that is the "whole-set" gate.

---

## 2. Where each piece of employee data actually lives today

| Question | Authoritative location today | Notes |
|---|---|---|
| Name, DOB, birth place, nationality, sex | `a1/employees_normalized.json` → `person.*` | Mirrored into `review.csv` |
| Insurance number | `employees_normalized.json` → `person.insurance_number` | Semantics differ per source (OP `rodné číslo` vs ZP `číslo pojištěnce`) — see §5 |
| Residence | `employees_normalized.json` → `residence.*` | `config/address_enrichment.json` supplies `ossz` + admin district by exact street match |
| Which OSSZ office | `review.csv` → `resolved_ossz`; keyed to a profile via `finalize_a1.PROFILE_BY_OSSZ` | `address_enrichment.json` policy: OSSZ is a *review suggestion*, never silently replaces the issuing institution |
| Institution (name/address/code) | `config/institutions/<profile>.json` | 11 office profiles; `code` is `TBD` in some (e.g. `usti-nad-labem.json`) |
| Employer | `employees_normalized.json` → `employment.*`; ARES enrichment for the agency employer | |
| Certificate dates / document id | `a1/cohort.json` **and** `review.csv` (must agree) | Two copies, one authority — this is the duplication to remove |
| Activity (workplace) | `employees_normalized.json` → `activity.*` | Default `"DE, CZ"` for self-employed multi-state |
| Provenance (scans, ARES URL, hashes) | `employees_normalized.json` → `provenance.*` | |
| Auth/review flags | `review.csv` only | `identity_reviewed`, `certificate_reviewed`, `approved_for_pdf`, `validated_by_user`, `*_source_status` |
| Live DB records | `portal/release1a/models.py::Worker` (+ `Document`, `Assignment`, `A1Case`) | 5 workers created 2026-10-20 from OCR; **not yet** the generation source |

---

## 3. The variants

### Variant A — current: flat files, several masters

`employees_normalized.json` + `review.csv` + `cohort.json` + `config/institutions/*.json`
edited by hand; `cohort.json` and `review.csv` both hold certificate dates.

- **Pros:** zero migration; every artefact is human-readable and diff-able; the
  44-column CSV is the exact contract the legacy renderer consumes; low blast radius.
- **Cons:** two copies of certificate dates with a set-equality gate between
  them; the flat CSV cannot express per-field provenance; `review.csv` mixes
  *facts* with *authority flags*; a hand edit can break a 44-column row silently
  in a spreadsheet; the DB is a parallel universe that the generator does not read.

### Variant B — one merged JSON: `a1/employees.json`

Single file per employee with `person / residence / employment / certificate /
activity / institution / ossz / provenance / authority_flags`, plus a top-level
`policy` block and per-field `source` + `expected_empty` + `default_value`
annotations.

- **Pros:** one place to look; per-field semantics become explicit and
  machine-checkable; satisfies the user's stated wish directly ("in each provide
  source, logic, script to run which gathers those data (if empty) or if are
  expected empty and which are default values").
- **Cons:** a single file is a single write hotspot and a single merge-conflict
  surface; large cohorts (24 today, likely hundreds) make merge painful; it
  duplicates the DB and the DB still does not become the source; it does not
  fix the *authority* duplication, only relocates it.

### Variant C — one model + generated, self-describing views *(recommended)*

Keep **one** authoritative employee model. Every other file becomes a
**declared, regenerable view** with a contract:

| View | Source of truth | Regenerated by | Declares |
|---|---|---|---|
| `a1/employees.json` (or DB tables) | — authoritative | human/OCR intake | per-field `source`, `expected_empty`, `default_value` |
| `a1/review.csv` | derived from employees + policy | `finalize_a1.prepare_review` | 44-col compat projection for the legacy renderer |
| `a1/cohort.json` | derived from employees + issuer decision | new `export_cohort` | ids + issue_dates + document_ids for the covered set |
| `config/institutions/*.json` | manual, verified | research task | office profile, verification date, unresolved fields |
| `portal/release1a/models.py` | authoritative (post-cutover) | Django services | worker/assignment/case revisions |

- **Pros:** no second copy of certificate dates — `cohort.json` becomes a
  *projection* of the issuer decision plus employee ids, so the set-equality
  gate becomes an assertion about the model, not a hand-kept duplicate;
  per-field `expected_empty` / `default_value` make "is this missing or is this
  legitimately blank?" answerable by a validator; `review.csv` stays a
  compatibility export (exactly what DB-MIG-3/DB-MIG-6 already mandate);
  the DB and the files stop being parallel universes.
- **Cons:** needs a real migration (the DB-MIG work already planned); one
  authority decision must be made about *where* the model lives (file vs DB);
  derived views must be regenerated in CI or they go stale.

---

## 4. Comparison

| Criterion | A (current) | B (one merged JSON) | C (model + generated views) |
|---|---|---|---|
| Single source of truth | ✗ (cert dates twice) | ✓ within files | ✓ across files *and* DB |
| Per-field source / expected-empty / default | ✗ | ✓ | ✓ |
| Machine-checkable completeness | ✗ (44 flat cols) | ✓ | ✓ |
| Handles the 24→N cohort growth | ✓ | ✗ merge hotspot | ✓ |
| DB becomes the system of record | ✗ | ✗ | ✓ (already planned) |
| Legacy renderer compatibility | ✓ | ✓ | ✓ (view, not master) |
| Migration cost | none | medium (rewrite all writers) | medium-high (DB-MIG-1..7) |
| Risk of silent data corruption | high (hand-edited 44-col CSV) | medium | low (derived + validated) |
| Fits existing plans | — | partial | ✓ (DB-MIG-1..7, ADR-001/002) |
| Makes the "why is data everywhere" question go away | no | partially | yes |

**Recommendation: Variant C.** It is the only option that removes the *class* of
problem (parallel masters) rather than relocating it, and it is already the
planned target in `PLAN-WORKERS-MIGRATE-TO-DB.md` (DB-MIG-1…7) with the
supporting export adapter `portal/release1a/a1_exports.py` in place. Variant B
is a reasonable intermediate step *if* it is explicitly framed as the
pre-cutover single model, and it becomes a view under C afterwards.

A pragmatic sequence that delivers value without waiting for the full cutover:

1. **Add per-field metadata to the model** — `source`, `expected_empty`,
   `default_value` — and a validator that reports *which* field is missing and
   *why* it is legitimately empty. (Small, independent, immediately useful.)
2. **Add a `cohort` export** that derives `a1/cohort.json` from the employee
   model + an explicit issuer decision, replacing the hand-maintained duplicate.
   This alone removes the `set(cohort) == set(review)` trap.
3. **Add a batch selector** to `scripts/a1_completion_preview.py`
   (`--all-undecided`, `--latest N`) so one documented command produces every
   worksheet — the callability gap, independent of the data-model choice.
4. **Close the arity/validation gap** (see §5) and land a regression test.
5. **Then** execute DB-MIG-1..7 to make the DB the system of record with
   `review.csv`/`cohort.json` as generated compatibility exports.

---

## 5. Gaps found in the current workflow (empirical, 2026-10-20)

Each was reproduced in this repository, not inferred.

### 5.1 A hand-edited 44-column CSV fails closed, but only at row granularity

A hand-written `review.csv` with 45–46 fields against the 44-column header is
**rejected** by `finalize_a1.read_review` with
`review CSV row 2: field count differs from header`. The guard is real and
works. Two residual gaps:

- The message names a **row number, not the `employee_id`**, so an operator
  cannot tell *which* worker is broken without counting lines.
- Nothing validates the **header itself** against `CSV_FIELDS` when the file is
  *written* — only on read. A writer that emits a 44-column row into a
  46-column header is caught, but the failure surfaces at read time, far from
  the edit.

`finalize_a1.write_review` already uses `csv.DictWriter(fieldnames=CSV_FIELDS)`,
which is arity-safe by construction. **Any new writer must do the same**; the
failure mode is hand-assembled comma strings.

### 5.2 The cohort/review mismatch is masked by an earlier validation error

With `a1/cohort.json` holding 24 ids and `a1/review.csv` holding 5, the
whole-set path fails with:

```
FinalizationError: every employee needs a non-empty, unique document_id
```

The real cause is two errors at once: the id-set mismatch *and* missing
`document_id` values. The reported error is the second, so an operator fixing
`document_id` will hit the same wall again. **Diagnosis order should be
reported explicitly** (id-set first, then per-row authority), or the two checks
should be reported together.

### 5.3 `scripts/a1_generate.py` bypasses the audited publisher

`scripts/a1_generate.py` writes `A1_<worker>.pdf` straight into an output
directory. It produces **no manifest, no receipt, no audit event, and no draft
notice** (the notice is only applied when `form["meta"]["application_draft"] is
True`, `scripts/a1_core.py:624`).

This is the confirmed origin of the two orphan files in `output/provisional/`:

| File | Pages | Draft notice | Manifest entry | Receipt |
|---|---|---|---|---|
| `A1_martin-sveda.pdf` | 3 | **no** | none | none |
| `A1_tomas-nistor.pdf` | 3 | **no** | none | none |

Neither sha256 appears in any manifest or receipt under `output/provisional/`
or `a1/receipts/`. They are therefore **not** acceptance evidence, not
issuance evidence, and not comparable to the 24 packages listed in
`output/provisional/generation_manifest.json` (all of which come from the
audited `generate_provisional_a1.py` path). They should be treated as
unverified scratch output and excluded from any acceptance comparison.

Note the catalog status: [A1_FRAMEWORKS.md](A1_FRAMEWORKS.md) lists V6
(`scripts/a1_generate.py`) as **active**, "hardened by AFG-04…AFG-07", while
V1 (`generate_provisional_a1.py` + `finalize_a1.py` + `a1_core.py` +
`a1_quality_gate.py`) is the **canonical** path with production authority. The
two differ in a way the catalog does not currently spell out: V6 emits a PDF
with **no manifest, no receipt, no audit event and no draft notice**, whereas
every V1 package carries all four. A PDF produced by V6 is therefore not
comparable to a V1 package and must not be counted as one. The residual task
is to state that distinction in the catalog and decide whether V6's output
should carry the same evidence envelope as V1.

Note the asymmetry: `output/provisional/tomas-nistor/A1_tomas-nistor.pdf` is a
*different* file with a different sha256 from the orphan
`output/provisional/A1_tomas-nistor.pdf`. The `a1/tomas-nistor/review.csv`
comment claims data was "copied unchanged from existing
`output/provisional/tomas-nistor/A1_tomas-nistor.pdf`" — that is the
subdirectory copy, not the orphan. The comment's provenance claim should be
checked against the file it names before the data is trusted as reviewed.

### 5.4 The completion-preview path deliberately blanks certificate data

`scripts/a1_completion_preview.py:75` sets `employee["certificate"] = {}` — a
completion worksheet, not an issued form. Consequently `certificate.member_state`
is reported missing even though `employees_normalized.json` carries
`member_state: "CZ"`. The missing-field list therefore mixes
*genuinely absent* facts with *deliberately withheld* ones. `--use-osvc-shared-defaults`
populates the institution/certificate baseline from `config/institution.json` and
is the correct way to produce a fuller worksheet.

### 5.5 The DB is a parallel universe for the generation path

The 5 `Worker` records created 2026-10-20 hold identity only. The A1 generator
reads `a1/employees_normalized.json` and never touches `portal/release1a/models.py`.
Nothing reconciles the two, so a worker edited in the DB cannot reach a PDF, and
a worker edited in the JSON cannot reach the portal. This is the concrete form
of the "data is everywhere" complaint, and it is exactly what DB-MIG-1..7
resolve.

### 5.6 Observed quality gap in the OCR intake itself

The intake path produced a **page swap** between `gregor-marian-op2.jpeg` and
`petr-badi-op2.jpeg` (the MRZ in each file carries the other person's name).
It was detected by cross-reading the MRZ, **not by any code**:
`src/document_core/interpretation.py` parses the MRZ and validates check
digits, but nothing compares the MRZ name against the OP1 name of the same
person, and nothing ties a filename to its content. A `rodcne cislo` check-digit
validator and a cross-document name/identifier consistency check would make
this an automatic, machine-detectable finding rather than an operator discovery.

The OCR engine choice itself is a separate axis and is already researched in
[2026-10-20 document-automation SOTA review](../research/2026-10-20-document-automation-sota-review.md);
that review covers parser/model options, and it does not address the
**cross-document consistency** gap described here, which lives in the
interpretation layer rather than in the OCR engine.

---

## 6. Scope of this document

This document is analysis and recommendation. It does not perform, approve or
schedule the migration described in Variant C, does not change any generation
output, and does not alter the accepted state of `a1/`, the portal models, or
the delivery record. The empirically reproduced gaps in §5 are findings for the
next bounded task; each needs its own scoped change, focused check and
known-limitations note under [AGENTS.md](../../AGENTS.md).
