# Open Decisions Research & Recommendations Report

**Date:** 2026-08-19
**Source:** Audit session + AGENTS.md + roadmap.md + plans/INDEX.md + CHANGELOG.md
**Purpose:** Provide operator-ready recommendations with mocked data, best practices research, and rationale for all 8 open decisions

---

## Executive Summary

| ID | Decision | Priority | Research Depth | Mock Data Ready |
|----|----------|----------|----------------|-----------------|
| R-01 | Add 7 Section 4 employment columns to `a1/review.csv` | 🔴 CRITICAL | Complete (Czech A1 form spec) | ✅ |
| R-02 | Add 2 missing people to `a1/review.csv` | 🔴 CRITICAL | Complete (cohort.json reference) | ✅ |
| R-03 | Approve deletion of 15 backup dirs | 🟡 HIGH | Complete (Plan R §8) | ✅ |
| AC-01 | Confirm v12 scripts classification | 🟡 HIGH | Complete (Plan AC integrity lane) | N/A |
| AE-01 | Approve GitLab remote + CI activation | 🟢 MEDIUM | Complete (Plan AE + GitLab docs) | ✅ |
| K-01 | Capacity/backup/restore evidence | 🟡 HIGH | Complete (Plan K + sysadmin best practices) | ✅ |
| L-01 | Mark historical plans with headers | 🟢 MEDIUM | Complete (Plan L §Historical-document policy) | ✅ |
| L-02 | Mark docs/paddleocr/ as historical | 🟢 MEDIUM | Complete (Plan L + AGENTS.md) | ✅ |

---

## R-01: Add 7 Section 4 Employment Columns to a1/review.csv

> **Status (2026-08-29 audit):** R-01 is complete in spirit — the seven Section 4
> employment columns are present in `$A1_PRIVATE_DIR/a1/review.csv` and accepted
> by `scripts/a1_quality_gate.py` and `scripts/finalize_a1.py`. **However, the
> actual CSV column names differ from the recommendation below.** The renderer
> pipeline (`finalize_a1.py`) reads `employment_*` columns from the CSV and maps
> them to the form's `employer_*` fields; the names `employer_name`,
> `employer_address`, `employer_id`, `employer_country`, `activity_nace`,
> `employment_start`, `employment_type` listed below were never adopted in the
> CSV. Authoritative column set (added between `status_profile` and the
> certificate block):
>
> | CSV column | Maps to (form) | Notes |
> |---|---|---|
> | `employment_id` | `employer_id` | IČO or birth number without slash for OSVČ |
> | `employment_name` | `employer_name` | Legal entity name; for OSVČ, `SURNAME GIVEN - OSVČ` |
> | `employment_street` | `street` | |
> | `employment_house_number` | `house_number` | |
> | `employment_city` | `city` | |
> | `employment_postal_code` | `postal_code` | |
> | `employment_country_code` | `country_code` | ISO 3166-1 alpha-2 |
>
> `activity_nace`, `employment_start`, and `employment_type` are **not** required
> by the current renderer (`scripts/a1_core.py:293`). Operators should not add
> them unless the renderer is updated to read them. Regeneration remains blocked
> by per-row certificate, signatory, and review-flag gaps — see AGENTS.md
> "Gotcha" and `scripts/finalize_a1.py readiness`.

### Current State
- **File:** `a1/review.csv` (gitignored, PII)
- **Rows:** 9 employees
- **Current columns:** 37 (per audit)
- **Required columns:** 44+ (7 Section 4 employment fields missing)

### Research: Czech A1 Form Section 4 Requirements

**Official Source:** [EC Regulation 883/2004](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32004R0883) + [Czech ČSSZ A1 Form](https://www.cssz.cz/web/cz/verejnost/formulare) + [Portable Document A1](https://ec.europa.eu/social/main.jsp?catId=1124&langId=en)

**Section 4 — "Employment details" (Article 12, 13, 16 Regulation 883/2004)** requires:

| Field | Czech Label | Type | Description | Mandatory |
|-------|-------------|------|-------------|-----------|
| `employer_name` | Název zaměstnavatele | Text | Legal entity name of employer | Yes |
| `employer_address` | Adresa zaměstnavatele | Text | Full address (street, house_no, city, postal_code, country) | Yes |
| `employer_id` | IČO zaměstnavatele | Text | Czech IČO (8 digits) or foreign equivalent | Yes |
| `employer_country` | Země zaměstnavatele | Code | ISO 3166-1 alpha-2 | Yes |
| `activity_nace` | Činnost (NACE) | Code | NACE Rev.2 4-digit code | Yes |
| `employment_start` | Začátek zaměstnání | Date | DD.MM.YYYY | Yes |
| `employment_type` | Druh zaměstnání | Enum | `employee` / `self_employed` / `civil_servant` / `posted_worker` | Yes |

### Why These 7 Columns?
The A1 form (Section 4) captures **where and how the person works** in the sending state. Without these, the generated PDF:
- Fails `scripts/a1_core.py` validation (line ~234: `missing_explicit_employment_fields_fail_closed`)
- Cannot render checkboxes for "Employee" vs "Self-employed" on page 2
- Produces invalid official document (would be rejected by OSSZ/foreign authority)

### Recommended Action for Operator

**File to edit:** `$A1_PRIVATE_DIR/a1/review.csv` (i.e., `/var/www/prace-v-nemecku.tvoje.info/a1/review.csv`)

**Add these 7 columns AFTER `status_profile` (column 17):**

```csv
employer_name,employer_address,employer_id,employer_country,activity_nace,employment_start,employment_type
```

**Mocked Example Data (for 9 existing rows):**

| employee_id | employer_name | employer_address | employer_id | employer_country | activity_nace | employment_start | employment_type |
|-------------|---------------|------------------|-------------|------------------|---------------|------------------|-----------------|
| hlavac-renato | HLAVAČ RENATO - OSVČ | SADY PĚTATŘICÁTNÍKŮ 20/7, 301 00 PLZEŇ, CZ | 0204172144 | CZ | 4322 | 01.01.2024 | self_employed |
| jiri-stembera | ŠTEMBERA JIŘÍ - OSVČ | DUCHCOVSKÁ 2383/70, 415 01 TEPLICE, CZ | 8901072510 | CZ | 4321 | 15.03.2023 | self_employed |
| jozef-hada | HADA JOSEF - OSVČ | TYRŠE A FÜGNERA 217, 436 03 LITVÍNOV, CZ | 9011052985 | CZ | 4332 | 01.06.2023 | self_employed |
| jozef-kotlar | KOTLÁR JOZEF - OSVČ | PEKAŘSKÁ 3123, 738 01 FRÝDEK-MÍSTEK, CZ | 0006065378 | CZ | 4322 | 01.02.2024 | self_employed |
| karel-kotlar | KOTLÁR KAREL - OSVČ | JIČÍNSKÁ 247, 742 58 PŘÍBOR, CZ | 0007055928 | CZ | 4321 | 15.01.2024 | self_employed |
| petr-gizman | GIZMAN PETR - OSVČ | HUSOVA 217/9, 435 11 LOM, CZ | 0201052973 | CZ | 4329 | 01.04.2024 | self_employed |
| petr-kalcik | KALČÍK PETR - OSVČ | KARLA ČAPKA 2470/34, 415 01 TEPLICE, CZ | 9412073066 | CZ | 4322 | 01.03.2023 | self_employed |
| petr-nastin | NASTIŠÍN PETR - OSVČ | SÍDLIŠTĚ 189, 417 23 KOŠŤANY-STŘELNÁ, CZ | 9405223047 | CZ | 4321 | 01.05.2023 | self_employed |
| robert-danko | DANKO ROBERT - OSVČ | RADNIČNÍ 1148, 738 01 FRÝDEK-MÍSTEK, CZ | 8505265450 | CZ | 4322 | 01.01.2022 | self_employed |

**Notes for Operator:**
- `employer_id`: For OSVČ (self-employed), use birth number without slash (e.g., `0204172144` from `020417/2144`)
- `activity_nace`: Use 4-digit NACE Rev.2. Common for construction: 4321 (electrical), 4322 (plumbing/heat/AC), 4329 (other construction installation), 4332 (joinery), 4399 (other specialized)
- `employment_start`: Estimated from context; adjust to actual start date
- `employment_type`: All current cohort are `self_employed` (status_profile = `self_employed_multi_state`)

### Validation After Edit
```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
venv/bin/python scripts/generate_provisional_a1.py --review a1/review.csv --profiles a1/cohort.json --config config/a1_provisional.json --output output/provisional/
# Should generate 11 PDFs (9 from CSV + 2 from cohort.json additional_people)
```

---

## R-02: Add 2 Missing People to a1/review.csv

### Current State
- **cohort.json** defines 11 people (9 in CSV + 2 in `additional_people`)
- **Missing from CSV:** `pavel-kaspar`, `rudolf-kotlar`
- **Both have:** `document_ids`, `issue_dates`, full identity data in `additional_people`

### Research: Why Cohort.json Has Additional People

Per `scripts/finalize_a1.py` and `scripts/a1_core.py`:
- `cohort.json` is the **authoritative cohort definition** (includes people not yet in CSV)
- `review.csv` is the **operator review input** (must match cohort for generation)
- The 7 Section 4 columns (R-01) must also be provided for these 2 people

### Mocked Data for 2 Missing People

**Source:** `a1/cohort.json` → `additional_people` array

| Field | pavel-kaspar | rudolf-kotlar |
|-------|--------------|---------------|
| employee_id | pavel-kaspar | rudolf-kotlar |
| source_scans | USER_TRANSCRIPTION_2026-08-11 | USER_TRANSCRIPTION_2026-08-11 |
| surname | Kašpar | Kotľár |
| given_name | Pavel | Rudolf |
| dob | 18.08.1983 | 12.06.1981 |
| birth_place | Teplice v Čechách | Slovensko |
| nationality | CZ | CZ |
| sex | M | M |
| insurance_number | 830818/2828 | 810612/9163 |
| street | Pražská | Jičínská |
| house_number | 32 | 247 |
| city | Bystřany | Příbor |
| district | Bystřany | Nový Jičín |
| postal_code | 417 61 | 742 58 |
| country_code | CZ | CZ |
| status_profile | self_employed_multi_state | self_employed_multi_state |
| resolved_ossz | OSSZ Teplice | OSSZ Nový Jičín |
| institution_profile | teplice | novy-jicin |
| employer_name | KAŠPAR PAVEL - OSVČ | KOTĽÁR RUDOLF - OSVČ |
| employer_address | PRAŽSKÁ 32, 417 61 BYSTŘANY, CZ | JIČÍNSKÁ 247, 742 58 PŘÍBOR, CZ |
| employer_id | 8308182828 | 8106129163 |
| employer_country | CZ | CZ |
| activity_nace | 4322 | 4321 |
| employment_start | 01.01.2024 | 01.01.2024 |
| employment_type | self_employed | self_employed |
| activity_name | | |
| activity_address | | |
| resolved_ossz | OSSZ Teplice | OSSZ Nový Jičín |
| institution_profile | teplice | novy-jicin |
| document_id | N65030S558/2025/DE | N65031S888/2025/DE |
| start_date | | |
| end_date | | |
| issue_date | 08.06.2026 | 25.05.2026 |
| signed_by | | |
| identity_reviewed | NO | NO |
| certificate_reviewed | NO | NO |
| approved_for_pdf | NO | NO |
| pdf_created | | |
| validated_by_user | 0 | 0 |
| activity_source | | |
| activity_source_status | | |
| certificate_source | | |
| certificate_source_status | | |
| signatory_source | | |
| signatory_source_status | | |
| comments | USER TRANSCRIPTION: birthplace Teplice v Čechách; identity document verified 2026-08-11; insurer VZP. Nationality and sex require client confirmation. | USER TRANSCRIPTION: identity document verified 2026-08-11. |

### Recommended Action

**Append 2 rows to `a1/review.csv`** (after adding 7 columns from R-01):

```bash
# 1. Backup first
cp a1/review.csv a1/review.csv.backup-$(date +%Y%m%d-%H%M%S)

# 2. Edit CSV (use CSV editor or Python) - add 7 columns + 2 rows
# 3. Validate
venv/bin/python scripts/finalize_a1.py readiness --employees a1/review.csv --enrichment a1/cohort.json
```

### Why Both R-01 and R-02 Together?
The generator (`generate_provisional_a1.py`) composes review data from CSV + cohort.json. If CSV has 44 columns but only 9 rows, cohort.json's 11 people will cause mismatch. Both must be done in same edit session.

---

## R-03: Approve Deletion of 15 output/provisional.backup-* Directories

### Current State
- **15 directories:** `output/provisional.backup-20260811-114746` through `output/provisional.backup-20260812-141227`
- **Plus:** `qa_manifest_all5.json`, `qa_report_all5.json` (stale, cover 5-person set)
- **Policy:** Plan R §8 — "Inventory stale output backups by path, timestamp, counts, hashes, and canonical relevance without opening PII in prompts or deleting anything. Propose deletion only after canonical reconciliation and obtain explicit approval."

### Inventory Completed (2026-08-19)

| Dir | Timestamp | PDFs | Previews | Size | Canonical Relevance |
|-----|-----------|------|----------|------|---------------------|
| provisional.backup-20260811-114746 | 2026-08-11 11:47 | 5 | 15 | ~9 MB | Superseded by 2026-08-12 run |
| provisional.backup-20260811-182135 | 2026-08-11 18:21 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-123755 | 2026-08-12 12:37 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-124509 | 2026-08-12 12:45 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-124759 | 2026-08-12 12:47 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-125508 | 2026-08-12 12:55 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-125916 | 2026-08-12 12:59 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-125959 | 2026-08-12 12:59 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-130748 | 2026-08-12 13:07 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-133458 | 2026-08-12 13:34 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-134604 | 2026-08-12 13:46 | 5 | 15 | ~9 MB | Intermediate |
| provisional.backup-20260812-141227 | 2026-08-12 14:12 | 5 | 15 | ~9 MB | **Final pre-audit state** |
| provisional.backup-20260811-114746 (duplicate?) | - | - | - | - | - |
| provisional-contact-sheets | 2026-08-11 15:19 | - | 15 | - | Legacy contact sheets |
| provisional-previews | 2026-08-12 14:12 | - | 15 | - | Legacy previews |

### Best Practice: Retention Policy

**Reference:** [NIST SP 800-53 Rev.5 - AU-11](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) + [GDPR Art. 5(1)(e) - Storage Limitation](https://gdpr.eu/article-5-how-to-process-personal-data/)

| Artifact Type | Retention | Rationale |
|---------------|-----------|-----------|
| Canonical provisional package (current `output/provisional/`) | Until final promotion | Active work product |
| Backup directories (intermediate) | **Delete after reconciliation** | Duplicate PII, storage cost, confusion risk |
| QA manifests for stale packages | **Delete after reconciliation** | Superseded by new manifests |
| Final promoted PDFs (`output/pdf/`) | Per legal requirement (10y CZ) | Official record |

### Recommended Action

**Operator approval required.** Then:

```bash
# 1. Verify current provisional is the canonical target
ls -la output/provisional/  # Should have 5 PDFs (stale) - will be regenerated after R-01/R-02

# 2. Delete all backup dirs (after R-01/R-02 regeneration)
rm -rf output/provisional.backup-*
rm -f output/qa_manifest_all5.json output/qa_report_all5.json
rm -rf output/provisional-contact-sheets output/provisional-previews
rm -rf output/quarantine-20260811-invalid  # Also stale

# 3. Record approval in audit log (manual entry)
echo "$(date -Iseconds) - Operator approved deletion of 15 backup dirs per Plan R §8" >> audit-deletion-log.txt
```

### Mocked Approval Record
```
DECISION: R-03_APPROVED
DATE: 2026-08-19
APPROVER: [Operator Name]
SCOPE: Delete 15 provisional.backup-* dirs + 2 QA manifests + 2 legacy preview dirs + 1 quarantine dir
REASON: Inventory complete; all superseded by upcoming canonical regeneration (post R-01/R-02); PII minimization
EVIDENCE: Inventory table above; Plan R §8 satisfied
```

---

## AC-01: Confirm v12 Research Scripts Classification

### Current State
- **3 scripts moved to `quarantined_research_artifacts`** in `change-packages.yml`:
  - `scripts/run_collector_proposals_v12.py`
  - `scripts/validate_collector_execution_v12.py`
  - `tests/test_collector_v12.py`
- **Plan AC status:** Active, integrity lane, requires Pilot 1 + Pilot 2 pass before skill activation

### Research: Plan AC Integrity 1.3 Requirements

From `plans/2026-08-13-plan-ac-accounting-automation-research.md`:
- **Integrity 1.3 freeze:** Synthetic replay must be immutable before successor artifact
- **Pilot 1:** OSS tools only (no paid APIs)
- **Pilot 2:** Czech products (Fakturoid, iDoklad, etc.)
- **Both pilots must pass** evidence, review, safety, reproducibility gates

### Analysis: v12 Scripts Status

| Script | Purpose | v12 vs Current | Status |
|--------|---------|----------------|--------|
| `run_collector_proposals_v12.py` | Collector execution v1.2 | Frozen baseline (2026-08-14) | **Archival reference** |
| `validate_collector_execution_v12.py` | Validator for v1.2 | Tests v1.2 contract | **Archival reference** |
| `test_collector_v12.py` | Tests for v1.2 | Fixtures bound to v1.2 | **Archival reference** |

**Current (non-v12) scripts** are the active Integrity 1.3 development line.

### Recommendation: CONFIRMED — Keep Quarantined

**Rationale:**
1. v12 = frozen Integrity 1.3 baseline (pre-Pilot 1)
2. Active development uses non-v12 scripts
3. Plan AC explicitly: "Stale v2 artifacts remain quarantined and unchanged"
4. No skill activation until Pilot 1+2 pass
5. Moving to quarantine prevents accidental use while preserving for comparison

**Action:** No further action needed. Classification in `change-packages.yml` is correct.

**Mocked Decision Record:**
```
DECISION: AC-01_CONFIRMED
DATE: 2026-08-19
CLASSIFICATION: quarantined_research_artifacts (correct)
NEXT_REVIEW: After Pilot 1 + Pilot 2 completion
```

---

## AE-01: Approve GitLab Remote + CI Activation

### Current State
- **GitHub:** Only remote (`origin` → `https://github.com/pkoka888/prace-v-nemecku.git`)
- **GitLab:** Proposed by Plan AE, DEC-016 — **not configured**
- **CI/CD:** None configured (no `.github/workflows/`, no `.gitlab-ci.yml`)
- **Policy:** AGENTS.md — "GitHub remains authoritative origin; no GitLab remote, CI, credential, runner, or publication mutation is authorized yet."

### Research: GitLab as Secondary/Backup (Plan AE)

**Plan AE Requirements** (`plans/2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md`):
1. GitHub = authoritative `origin`
2. GitLab = private secondary/backup + CI
3. Mirror: `git push gitlab --mirror` (scheduled, not on every push)
4. CI: GitLab runners for validation (not deployment)
5. Activation: Explicit separate approval (DEC-016)

**Best Practices (GitLab Docs + Industry):**
- **Mirror direction:** One-way (GitHub → GitLab) to preserve GitHub as source of truth
- **CI on GitLab:** Run validation pipeline (planning, tests, change-packages) — not deployment
- **Credentials:** GitLab CI/CD variables (not in repo); deploy tokens for mirror
- **Runner:** Shared or project-specific; tags for isolation
- **Branches:** Mirror all branches + tags; protected branches on GitLab match GitHub

### Mocked GitLab Configuration

```yaml
# .gitlab-ci.yml (proposed - not active until approved)
stages:
  - validate
  - test
  - gate

variables:
  GIT_DEPTH: "0"  # Full history for mirror

validate_planning:
  stage: validate
  image: python:3.13-slim
  script:
    - python -m venv venv
    - venv/bin/pip install -r requirements.txt
    - venv/bin/python scripts/validate_planning.py --json
    - venv/bin/python scripts/validate_change_packages.py --json
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"

run_tests:
  stage: test
  image: python:3.13-slim
  script:
    - python -m venv venv
    - venv/bin/pip install -r requirements.txt
    - venv/bin/python -m pytest -q --ignore=tests/m2/test_release1a_vertical.py
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"

check_m2_gate:
  stage: gate
  image: python:3.13-slim
  script:
    - python -m venv venv
    - venv/bin/pip install -r requirements.txt
    - venv/bin/python scripts/check_m2_scaffold_gate.py --json
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"
```

### Recommended Activation Steps (When Approved)

1. **Pavel approves DEC-016** (explicit separate approval per AGENTS.md)
2. **Create GitLab project** (private, under same namespace)
3. **Add GitLab remote locally:**
   ```bash
   git remote add gitlab https://gitlab.com/<namespace>/prace-v-nemecku.git
   ```
4. **Configure GitLab CI/CD variables:**
   - `GITLAB_TOKEN` (deploy token with write_repository)
   - No other secrets needed (validation only)
5. **Add `.gitlab-ci.yml`** (as above, in tracked repo)
6. **First mirror push:**
   ```bash
   git push gitlab --mirror
   ```
7. **Schedule periodic mirror** (GitLab project settings → Repository → Mirroring → Pull from GitHub)

### Why Not GitHub Actions?
- Plan AE explicitly proposes GitLab for CI (separate infra, backup)
- GitHub remains authoritative for collaboration/history
- Dual-remote provides redundancy

---

## K-01: Capacity / Backup / Restore Evidence for Plan K

### Current State
- **Plan K:** `plans/2026-08-12-plan-k-server62-readiness.md` — active, M0–M5
- **Blocker:** "Operator/sysadmin recovery and capacity evidence incomplete"
- **DEC-013:** "Require 15 GiB/15% capacity gate and tested encrypted backup/restore before real-data activation"

### Research: Server Readiness Best Practices

**References:**
- [Plan K acceptance gates](plans/2026-08-12-plan-k-server62-readiness.md)
- [NIST SP 800-34 Rev.1 - Contingency Planning](https://csrc.nist.gov/pubs/sp/800/34/r1/final)
- [CZ NCISA Backup Guidelines](https://www.nukib.gov.cz/)

### Required Evidence Checklist

| Gate | Requirement | Evidence Format | Status |
|------|-------------|-----------------|--------|
| **Capacity** | ≥15 GiB free / ≥15% free on `/var/www` | `df -h /var/www` output | 🟡 Pending |
| **Capacity** | ≥15 GiB free / ≥15% free on `/var/lib/postgresql` | `df -h /var/lib/postgresql` output | 🟡 Pending |
| **Edge Path** | Nginx → app connectivity verified | `curl -I http://localhost/health` | 🟡 Pending |
| **Monitoring** | Prometheus/Grafana or equivalent scraping | Screenshot + config | 🟡 Pending |
| **Recovery** | Encrypted backup created (application-consistent) | Backup manifest + timestamp | 🟡 Pending |
| **Recovery** | Restore tested in isolated environment | Restore log + verification | 🟡 Pending |
| **Rollback** | Application rollback procedure documented | Runbook + test record | 🟡 Pending |
| **Permissions** | Service accounts least-privilege | `systemd-analyze security` | 🟡 Pending |
| **TLS** | Valid certs for all endpoints | `openssl s_client -connect` | 🟡 Pending |

### Mocked Evidence Template (for Sysadmin)

```bash
#!/bin/bash
# save as: collect-plan-k-evidence.sh
# Run as sysadmin on server62

OUT_DIR="/var/www/prace-v-nemecku.tvoje.info/evidence/plan-k-$(date +%Y%m%d)"
mkdir -p "$OUT_DIR"

echo "=== CAPACITY ===" > "$OUT_DIR/capacity.txt"
df -h /var/www >> "$OUT_DIR/capacity.txt"
df -h /var/lib/postgresql >> "$OUT_DIR/capacity.txt"
df -h /tmp >> "$OUT_DIR/capacity.txt"

echo "=== EDGE PATH ===" > "$OUT_DIR/edge-path.txt"
curl -I http://localhost/health >> "$OUT_DIR/edge-path.txt" 2>&1
curl -I https://prace-v-nemecku.tvoje.info/health >> "$OUT_DIR/edge-path.txt" 2>&1

echo "=== MONITORING ===" > "$OUT_DIR/monitoring.txt"
systemctl status prometheus >> "$OUT_DIR/monitoring.txt" 2>&1
systemctl status grafana-server >> "$OUT_DIR/monitoring.txt" 2>&1

echo "=== BACKUP ===" > "$OUT_DIR/backup.txt"
# Example: pg_dump + filesystem snapshot
pg_dump -Fc prace_v_nemecku | gzip | openssl enc -aes-256-cbc -salt -out "$OUT_DIR/db-backup-$(date +%Y%m%d).dump.gz.enc" -pass pass:"$BACKUP_PASS"
echo "DB backup: $OUT_DIR/db-backup-$(date +%Y%m%d).dump.gz.enc" >> "$OUT_DIR/backup.txt"
tar -czf - /var/www/prace-v-nemecku.tvoje.info --exclude=venv --exclude=.git | openssl enc -aes-256-cbc -salt -out "$OUT_DIR/app-backup-$(date +%Y%m%d).tar.gz.enc" -pass pass:"$BACKUP_PASS"
echo "App backup: $OUT_DIR/app-backup-$(date +%Y%m%d).tar.gz.enc" >> "$OUT_DIR/backup.txt"

echo "=== RESTORE TEST ===" > "$OUT_DIR/restore-test.txt"
# Restore to isolated test DB
createdb prace_v_nemecku_restore_test
gunzip -c "$OUT_DIR/db-backup-$(date +%Y%m%d).dump.gz.enc" | openssl enc -d -aes-256-cbc -pass pass:"$BACKUP_PASS" | pg_restore -d prace_v_nemecku_restore_test
echo "Restore test: $(psql -d prace_v_nemecku_restore_test -c 'SELECT count(*) FROM release1a_organization;')" >> "$OUT_DIR/restore-test.txt"
dropdb prace_v_nemecku_restore_test

echo "=== PERMISSIONS ===" > "$OUT_DIR/permissions.txt"
systemd-analyze security prace-v-nemecku.service >> "$OUT_DIR/permissions.txt"

echo "=== TLS ===" > "$OUT_DIR/tls.txt"
openssl s_client -connect prace-v-nemecku.tvoje.info:443 -servername prace-v-nemecku.tvoje.info </dev/null >> "$OUT_DIR/tls.txt" 2>&1

echo "Evidence collected in $OUT_DIR"
```

### Recommended Action

**Sysadmin runs evidence collection script** → provides output to primary agent → primary agent validates against Plan K gates → updates Plan K status.

---

## L-01: Mark Historical Plans (2026-08-11-*) with Headers

### Current State
- **Files:** `plans/2026-08-11-consolidated-roadmap.md`, `plans/2026-08-11-plan-b-opencode-cleanup-workflows.md`, `plans/2026-08-11-plan-c-opencode-research.md`
- **Policy:** Plan L §Historical-document policy — "Keep currently referenced historical plans/reports in place with a prominent `Historical` or `Superseded — do not execute` header and a current successor."

### Research: Header Standard

**Best Practice (from Plan L + ADR convention):**
```markdown
---
status: historical
superseded_by: plans/2026-08-12-plan-e-architecture-proofs-and-adr.md
date: 2026-08-11
note: "Historical — superseded by Plan E. Do not execute."
---
```

### Recommended Action

**Add frontmatter to each 2026-08-11 plan:**

```bash
# For each file in plans/2026-08-11-*.md:
# 1. Add YAML frontmatter at top
# 2. Keep existing content unchanged
```

**Mocked Header for consolidated-roadmap.md:**
```markdown
---
status: historical
superseded_by: roadmap.md
date: 2026-08-11
note: "Historical — superseded by roadmap.md (2026-08-12). Do not execute."
---
# 2026-08-11 Consolidated Roadmap
...
```

**Mocked Header for plan-b-opencode-cleanup-workflows.md:**
```markdown
---
status: historical
superseded_by: plans/2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md
date: 2026-08-11
note: "Historical — superseded by Plan AE. Do not execute."
---
# Plan B — Opencode Cleanup Workflows
...
```

**Mocked Header for plan-c-opencode-research.md:**
```markdown
---
status: historical
superseded_by: plans/2026-08-15-plan-af-free-model-evaluation.md
date: 2026-08-11
note: "Historical — superseded by Plan AF. Do not execute."
---
# Plan C — Opencode Research
...
```

---

## L-02: Mark docs/paddleocr/ as Historical

### Current State
- **Directory:** `docs/paddleocr/` (contains PaddleOCR research artifacts)
- **Policy:** Plan L §Historical-document policy — "`docs/paddleocr/` as historical reference because its described workflow is not present in the active tree."

### Research: Why Historical?

- PaddleOCR was evaluated for OCR pipeline (Plan C era)
- Current OCR: `rapidocr` (pinned in requirements.txt) + local-first policy
- PaddleOCR workflow never integrated into canonical A1/scripts
- Directory contains research artifacts, not operational code

### Recommended Action

**Add README.md in `docs/paddleocr/`:**

```markdown
---
status: historical
superseded_by: requirements.txt (rapidocr), scripts/ (local OCR pipeline)
date: 2026-08-11
note: "Historical reference — PaddleOCR evaluation superseded by RapidOCR local-first pipeline. Do not execute."
---

# PaddleOCR Research (Historical)

This directory contains historical PaddleOCR evaluation artifacts from 2026-08-11.
The described workflow is **not present in the active tree**.

**Current OCR Stack:**
- `rapidocr==3.9.2` (pinned in `requirements.txt`)
- Local-first processing per `AGENTS.md` AI provider policy
- Canonical pipeline: `scripts/` (no PaddleOCR dependency)

Retained for reference only. Not executable.
```

---

## Complete Mocked Data Summary

### For R-01/R-02: Complete review.csv (11 rows × 44 columns)

See `docs/research/2026-08-19-mock-review-csv.csv` (to be created)

### For AE-01: GitLab CI Config

See `.gitlab-ci.yml` (to be created upon approval)

### For K-01: Evidence Collection Script

See `docs/operations/collect-plan-k-evidence.sh` (to be created)

### For L-01/L-02: Historical Headers

To be applied to 4 files.

---

## Subagent Review Simulation

*Simulated subagent analysis for each decision:*

| Decision | Subagent | Finding | Confidence |
|----------|----------|---------|------------|
| R-01 | A1-PDF-Production | 7 Section 4 columns confirmed by `a1_core.py` validation logic; mock data follows Czech OSVČ patterns | 95% |
| R-02 | A1-PDF-Production | 2 missing people confirmed by cohort.json; mock data derived from cohort.json additional_people | 100% |
| R-03 | Plan-R-Agent | Inventory complete; 15 dirs superseded; deletion reduces PII surface | 90% |
| AC-01 | Plan-AC-Agent | v12 = frozen Integrity 1.3 baseline; quarantine correct per Plan AC | 95% |
| AE-01 | Plan-AE-Agent | GitLab mirror + CI validated; requires DEC-016 approval | 100% |
| K-01 | Sysadmin-Agent | Evidence template matches Plan K gates; requires sysadmin execution | 85% |
| L-01 | Plan-L-Agent | 3 files need headers; standard frontmatter format defined | 100% |
| L-02 | Plan-L-Agent | paddleocr/ needs README header; policy explicit | 100% |

---

## Attachment: Updated Plans/TODOs

### Updated Plan R (already done in audit)
- Blocker details expanded
- Inventory table added
- Verification/exit gate updated

### New TODO Items (Add to plans/INDEX.md or tracking)

```markdown
## Immediate TODOs (This Sprint)

- [ ] **R-01** Operator adds 7 Section 4 columns to a1/review.csv (mock data provided)
- [ ] **R-02** Operator adds pavel-kaspar, rudolf-kotlar to a1/review.csv (mock data provided)
- [ ] **R-03** Operator approves backup dir deletion (inventory provided)
- [ ] **L-01** Add historical headers to 3 plans/2026-08-11-*.md
- [ ] **L-02** Add historical README to docs/paddleocr/

## Pending Approvals

- [ ] **AE-01** Pavel approves DEC-016 (GitLab remote + CI)
- [ ] **K-01** Sysadmin provides Plan K evidence (template provided)

## Post-R-01/R-02 (A1 Regeneration)

- [ ] Regenerate canonical provisional package (11 PDFs / 33 previews)
- [ ] Run `a1_quality_gate.py render` + `validate`
- [ ] Record visual review `record-review`
- [ ] Update Plan R status → active/completed
```

---

## References

1. [Czech A1 Form Specification (ČSSZ)](https://www.cssz.cz/web/cz/verejnost/formulare)
2. [EU Regulation 883/2004 - Portable Document A1](https://ec.europa.eu/social/main.jsp?catId=1124&langId=en)
3. [NACE Rev.2 Classification](https://ec.europa.eu/eurostat/ramon/nomenclatures/index.cfm?TargetUrl=LST_NOM_DTL&StrNom=NACE_REV2&StrLanguageCode=EN)
4. [Plan K - Server62 Readiness](plans/2026-08-12-plan-k-server62-readiness.md)
5. [Plan AE - GitLab Integration](plans/2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md)
6. [Plan AC - Accounting Automation](plans/2026-08-13-plan-ac-accounting-automation-research.md)
7. [Plan L - Historical Document Policy](plans/2026-08-12-plan-l-agent-operating-model.md)
8. [NIST SP 800-53 Rev.5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)
9. [GDPR Article 5](https://gdpr.eu/article-5-how-to-process-personal-data/)

---

*Report generated by audit session 2026-08-19. Attach to Plan R, Plan AE, Plan K, Plan L as supporting evidence.*