# Mock-Data Provenance Log

**Purpose:** Maintain the reviewed synthetic-data contract for named Release 1A,
prototype, and research fixture families. This is not an automated inventory of
every synthetic literal in the repository.

**Maintainer:** primary agent  
**Created:** 2026-08-17  
**Governs:** `tests/fixtures/release_1a/`, inline test fixtures, prototype mock data

---

## How to read this log

| Column | Meaning |
|---|---|
| **Fixture** | Where the synthetic data lives |
| **Synthetic value** | What the mock data contains |
| **Production intake/migration** | How separately authorized application data later enters; tracked fixtures are never replaced |
| **Gate** | Which approval/decision gates the swap |
| **Status** | `ready` (synthetic complete), `gap` (production data not yet available), `blocked` (waiting on human decision) |

---

## 1. Release 1A Architecture Proof Fixtures

Source: `tests/fixtures/release_1a/`

### 1.1 Organizations

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `org-synthetic-alpha` | "TESTOVACÍ s.r.o.", CZ-00000001, Praha | Real Jan's company from solution brief | DEC-012 real-data activation | ready (synthetic) |
| `org-synthetic-beta` | "FIKTIVNÍ Bau GmbH", DE-00000001, München | Real German partner company | DEC-012 | ready (synthetic) |
| `org-synthetic-gamma` | "UKÁZKOVÁ Agentura a.s.", CZ-00000002, Brno | Third org for tenant-isolation edge cases | DEC-012 | ready (synthetic) |

**Production note:** Jan must provide the actual company name, registration number, and address. The `country` field determines regulatory scope (CZ vs DE vs AT). Do not invent these.

### 1.2 Users

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `user-synthetic-01` | admin@example.invalid | Jan's admin account | DEC-012 | ready (synthetic) |
| `user-synthetic-02` | jan@example.invalid | Jan's operator account | DEC-012 | ready (synthetic) |
| `user-synthetic-03` | viewer@example.invalid | Operator/viewer account | DEC-012 | ready (synthetic) |
| `user-synthetic-04` | admin-beta@example.invalid | German partner admin | DEC-012 | ready (synthetic) |
| `user-synthetic-05` | operator-gamma@example.invalid | Third-org operator | DEC-012 | ready (synthetic) |

**Production note:** Real email addresses. MFA method and role assignments come from Jan's delegation decisions (PLAN-LEGAL, formerly Plan F/J). No real credentials in fixtures.

### 1.3 Workers

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `worker-synthetic-01` | TESTOVACÍ Novotný, OSVČ, CZ | Authorized portal intake/migration after activation | DEC-012 | ready (synthetic) |
| `worker-synthetic-02` | FIKTIVNÍ Králová, zaměstnanec, CZ | Authorized portal intake/migration after activation | DEC-012 | ready (synthetic) |
| `worker-synthetic-03` | UKÁZKOVÝ Müller, zaměstnanec, DE | Authorized portal intake/migration after activation | DEC-012 | ready (synthetic) |
| `worker-synthetic-04` | TESTOVACÍ Dvořák, inactive, CZ | Authorized portal intake/migration after activation | DEC-012 | ready (synthetic) |

Successful Czech identifier cases use deterministic checksum-valid synthetic
values; rejection cases are explicitly labeled invalid. Real identifiers arrive
only through authorized application intake after DEC-012. Separately, PLAN-A1 is
blocked on seven Section 4 columns in the existing protected A1 CSV.

### 1.4 Documents

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `doc-synthetic-01` | SYNTHETIC-op-novotny-1.pdf, approved | Real OP scan | DEC-012 | ready (synthetic) |
| `doc-synthetic-02` | SYNTHETIC-zp-kralova-1.pdf, approved | Real ZP scan | DEC-012 | ready (synthetic) |
| `doc-synthetic-03` | virus-test.exe, rejected | N/A (negative test only) | N/A | ready (negative) |
| `doc-synthetic-04` | SYNTHETIC-oversize.pdf, rejected | N/A (negative test only) | N/A | ready (negative) |
| `doc-synthetic-05` | SYNTHETIC-pa-mueller-1.pdf, different org | Real DE document | DEC-012 | ready (synthetic) |

**Production note:** `storage_key` values are SHA-256 hashes of encrypted content. Real keys replace synthetic hashes. `ocr_proposals` are outputs of the OCR pipeline; real values come from actual document processing.

### 1.5 Assignments

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `asgn-synthetic-01` | München, Elektrikář, Aug–Sep 2026 | Real assignment | Jan confirms | ready (synthetic) |
| `asgn-synthetic-02` | Augsburg, Instalatér, Sep–Oct 2026 | Future assignment | Jan confirms | ready (synthetic) |
| `asgn-synthetic-03` | Dresden, Svářeč, Aug–Nov 2026 | Real assignment | Jan confirms | ready (synthetic) |
| `asgn-synthetic-04` | Overlapping assignment (negative test) | N/A (negative test only) | N/A | ready (negative) |
| `asgn-synthetic-05` | Berlin, different org | Real DE assignment | Jan confirms | ready (synthetic) |

**Production note:** `partner_name`, `workplace`, `role`, and dates come from Jan's actual assignment data. The `a1_period_ambiguous` flag triggers when overlapping assignments create unclear A1 periods.

### 1.6 A1 Inputs

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `A1-SYNTH-001` | Complete case, prepared, with hash | Real A1 case from `a1/review.csv` | PLAN-A1 + DEC-012 | ready (synthetic) |
| `A1-SYNTH-002` | Incomplete case, no preparation | In-progress real case | PLAN-A1 + DEC-012 | ready (synthetic) |

**Critical gap:** `section4_employment` fields (activity_type, employer_country, worker_state, legislation_applied, partial_exemption, multiple_states, posted_worker) are the 7 columns missing from the protected CSV. These are the PLAN-A1 blocker. Real values must come from authoritative employer/employee sources.

### 1.7 Jobs

| Fixture | Synthetic value | Production replacement | Gate | Status |
|---|---|---|---|---|
| `job-synthetic-01` | Completed OCR job | Real OCR job | DEC-012 | ready (synthetic) |
| `job-synthetic-02` | Completed A1 generation job | Real A1 job | DEC-012 | ready (synthetic) |
| `job-synthetic-03` | Failed/timeout OCR job | N/A (negative test only) | N/A | ready (negative) |
| `job-synthetic-04` | Queued A1 job | Real queued job | DEC-012 | ready (synthetic) |
| `job-synthetic-05` | Completed export job, different org | Real export job | DEC-012 | ready (synthetic) |

---

## 2. Existing Inline Test Fixtures (already in repo)

| File | What it contains | Production replacement | Status |
|---|---|---|---|
| `tests/test_a1_core.py` | `complete_employee()` and `synthetic_institution()` — synthetic A1 data | Same pattern, real values from `a1/review.csv` | ready (synthetic) |
| `tests/test_comprehensive.py` | Section 4 employment data, incomplete employee | Same pattern, real values | ready (synthetic) |
| `tests/test_invoice_ingestion_contract.py` | Synthetic invoice/extract/review records | Real invoice data (Plan AD, DEC-015 gated) | ready (synthetic) |
| `config/institutions/*.json` | 7 institution config files | Real institution configs | ready (config) |

---

## 3. Existing Research Synthetic Data

| Dataset | What it contains | Production replacement | Status |
|---|---|---|---|
| `research/synthetic/` | 24 synthetic invoice PDFs + ground truth | Real invoice ground truth (Plan AC, DEC-15 gated) | ready (synthetic) |
| `research/acquisition/synthetic-mini-pilot/` | 20-tool fixture set + execution traces | Real tool profiles from live capture | ready (synthetic) |
| `research/acquisition/source-captures/synthetic-mini-*/` | Source capture excerpts | Real source captures | ready (synthetic) |

---

## 4. Prototype Mock Data

| Prototype | What it contains | Production replacement | Status |
|---|---|---|---|
| `docs/prototypes/roadmap-portal/index.html` | Hardcoded portal mock data (Adam Novotný, Eva Králová, Tomáš Malý) | Django template rendering from real DB | ready (mock) |
| `docs/prototypes/roadmap-portal/planning-data.js` | Generated planning/catalog data | Same script, real `catalog.json` | ready (generated) |
| `docs/prototypes/roadmap-portal/approval-data.js` | Generated approval data | Same script, real `approvals.json` | ready (generated) |

---

## 5. Summary: What Blocks Production Data

| Blocker | Who provides | When | Gate |
|---|---|---|---|
| 7 missing Section 4 employment columns in protected CSV | Jan/Pavel via operator | Before PLAN-A1 unblocks | PLAN-A1 |
| Real worker names, IDs, addresses | Jan (cohort list) | Before M5 real-data pilot | DEC-012 |
| Real company details (name, reg. number, address) | Jan | Before M5 | DEC-012 |
| Real assignment data (workplace, role, dates, partner) | Jan | Before M5 | DEC-012 |
| Real document scans | Jan (upload) | During M5 pilot | DEC-012 |
| Real user accounts and email addresses | Jan | Before M5 | DEC-012 |
| Real A1 case data (from `a1/review.csv`) | Existing production data | Before M5 | DEC-012 + PLAN-A1 |
| Institution configs (real employer data) | Jan | Before M5 | DEC-012 |

---

## 6. Rules for Synthetic Data Maintenance

1. **Every fixture file must contain a `_fiction` field** explaining it is synthetic.
2. **Fixture hashes in `manifest.json` must be updated** whenever any fixture file changes.
3. **Real data must never be copied into fixture files** — not even "lightly altered" values.
4. **Negative test fixtures** (disguised executable, oversize, overlapping assignment) are intentionally synthetic and have no production replacement.
5. **Never create `tests/fixtures/production/` or place real data anywhere under
   `tests/fixtures/`.** Authorized real data remains only in protected A1 or
   `runtime/portal/` paths and enters through application intake/migration.
6. **The fiction manifest is checked by `run_architecture_proofs.py preflight`**;
   hashes, schema, markers, references, declared paths, counts, and negative-case
   contracts fail closed. Later proof phases must additionally demonstrate that
   protected paths and real-data environment values are never read.
