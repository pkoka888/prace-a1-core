# TODO Tracking — Práce v Německu

**Created:** 2026-08-19 (Audit Session)
**Source:** PROJECT_AUDIT_REPORT.md + docs/research/2026-08-19-open-decisions-research.md
**Operator Approval:** R-01, R-02, R-03 mock data approved for use as templates

---

## Legend
- 🔴 **CRITICAL** — Blocks canonical A1 regeneration (Plan R)
- 🟡 **HIGH** — Required before next milestone
- 🟢 **MEDIUM** — Important but not blocking
- 🔵 **LOW** — Cleanup / technical debt
- ✅ **DONE** — Completed in audit session
- ☐ **PENDING** — Not started
- 🟠 **IN PROGRESS** — Started, awaiting completion

---

## Phase 1: Plan R Unblock (CRITICAL — Operator Action Required) — **COMPLETED 2026-08-20**

### R-01: Add 7 Section 4 Employment Columns to a1/review.csv
| Sub-task | Status | Owner | Notes |
|---|---|---|---|
| Edit `a1/review.csv` — add 7 columns after `status_profile` (pos 17) | ✅ DONE | **Operator** | Template: `docs/research/2026-08-19-mock-review-csv.csv` cols 17-23 |
| `employment_id` — Employer IČO (birth number no slash) | ✅ DONE | Operator | e.g., `0204172144` from `020417/2144` |
| `employment_name` — Employer legal name | ✅ DONE | Operator | e.g., `HLAVAČ RENATO - OSVČ` |
| `employment_street` — Employer street | ✅ DONE | Operator | |
| `employment_house_number` — Employer house number | ✅ DONE | Operator | |
| `employment_city` — Employer city | ✅ DONE | Operator | |
| `employment_postal_code` — Employer postal code | ✅ DONE | Operator | |
| `employment_country_code` — ISO 3166-1 alpha-2 (`CZ`) | ✅ DONE | Operator | |
| **Validation**: `venv/bin/python scripts/finalize_a1.py readiness --review a1/review.csv` | ✅ DONE | Primary Agent | Passed — no "missing employment" errors |

### R-02: Add 2 Missing People to a1/review.csv
| Sub-task | Status | Owner | Notes |
|---|---|---|---|
| Append `pavel-kaspar` row to CSV | ✅ DONE | **Operator** | From `docs/research/2026-08-19-mock-review-csv.csv` row 10 |
| Append `rudolf-kotlar` row to CSV | ✅ DONE | **Operator** | From `docs/research/2026-08-19-mock-review-csv.csv` row 11 |
| **Validation**: CSV has 11 rows × 44 columns | ✅ DONE | Primary Agent | `wc -l a1/review.csv` → 12 (header + 11) |

### R-03: Update a1/cohort.json Document IDs
| Sub-task | Status | Owner | Notes |
|---|---|---|---|
| Change all 11 `document_ids` from `/2025/` to `/2026/` | ✅ DONE | **Operator** | Must match `issue_dates` year (2026) |
| Set `additional_people: []` (both now in CSV) | ✅ DONE | **Operator** | Remove the 2 additional_people entries |
| **Validation**: `generate_provisional_a1.py` no year mismatch | ✅ DONE | Primary Agent | |

---

## Phase 2: Canonical Regeneration (After Phase 1 Complete) — **COMPLETED 2026-08-20**

| Sub-task | Status | Owner | Command |
|---|---|---|---|
| Generate 11 provisional PDFs | ✅ DONE | Primary Agent | `venv/bin/python scripts/generate_provisional_a1.py --review a1/review.csv --profiles config/institutions --config config/a1_provisional.json --cohort a1/cohort.json --output output/provisional/` |
| Verify 11 PDFs in `output/provisional/` | ✅ DONE | Primary Agent | `ls output/provisional/A1_*.pdf | wc -l` → 11 |
| Render 33 previews (11 × 3) + 3 contact sheets | ✅ DONE | Primary Agent | `venv/bin/python scripts/a1_quality_gate.py render --pdf-dir output/provisional --preview-dir output/provisional-previews --contact-dir output/provisional-contact-sheets` → 33 previews, 3 contact sheets |
| Validate quality gate | ✅ DONE | Primary Agent | `venv/bin/python scripts/a1_quality_gate.py validate ...` → `{"passed": true, "actual_pdf_count": 11, "actual_preview_count": 33}` |
| Expect: `{"passed": true, "actual_pdf_count": 11, "actual_preview_count": 33}` | ✅ DONE | Primary Agent | QA gate PASSED |
| Local visual review — all 11 PDFs × 3 pages | 🟡 PENDING | **Operator** | Manual inspection required before promotion |
| Record visual review (hash-bound PASS) | 🟡 PENDING | Primary Agent | `venv/bin/python scripts/a1_quality_gate.py record-review --manifest output/qa_manifest.json --reviewer "<name>" --decision PASS` |

---

## Phase 3: Backup Cleanup (Plan R §8)

| Sub-task | Status | Owner | Notes |
|---|---|---|---|
| Operator explicit approval for deletion recorded | ☐ PENDING | **Operator** | Log in audit trail |
| Delete 15 `output/provisional.backup-*` dirs | ☐ PENDING | Primary Agent | `rm -rf output/provisional.backup-*` |
| Delete `qa_manifest_all5.json`, `qa_report_all5.json` | ☐ PENDING | Primary Agent | `rm -f output/qa_manifest_all5.json output/qa_report_all5.json` |
| Delete legacy preview dirs | ☐ PENDING | Primary Agent | `rm -rf output/provisional-contact-sheets output/provisional-previews output/quarantine-20260811-invalid` |

---

## Phase 4: Plan R Status Update

| Sub-task | Status | Owner | Notes |
|---|---|---|---|
| Plan R status: `blocked` → `active` → `completed` | ☐ PENDING | Primary Agent | Edit `plans/2026-08-12-plan-r-a1-production-stabilization.md` |
| Update `plans/INDEX.md` Plan R blocker → cleared | ☐ PENDING | Primary Agent | |
| Update `roadmap.md` Plan R status → ✅ | ☐ PENDING | Primary Agent | |

---

## Phase 5: M2 Sprint — **VERTICAL SLICE COMPLETED + CODE REVIEWED 2026-08-19**

| Sub-task | Status | Owner | Priority |
|---|---|---|---|
| Implement J1 Worker Create/Read/Update/Delete | ✅ DONE | Primary Agent | 🔴 CRITICAL |
| Implement J2 Document Upload/OCR/Review/Download | ✅ DONE | Primary Agent | 🔴 CRITICAL |
| Implement J3 Assignment Create/Edit with Overlap Warning | ✅ DONE | Primary Agent | 🔴 CRITICAL |
| Implement J4 A1 Readiness/Generation/Approval | ✅ DONE | Primary Agent | 🔴 CRITICAL |
| Mandatory TOTP for privileged roles | ✅ DONE | Primary Agent | 🟡 HIGH |
| Tenant isolation (queryset/view/form/task/Admin/download) | ✅ DONE | Primary Agent | 🟡 HIGH |
| AuditEvent for all material writes/denials/downloads | ✅ DONE | Primary Agent | 🟡 HIGH |
| Czech-first templates + HTMX | ✅ DONE | Primary Agent | 🟡 HIGH |
| 11 M2 view tests in `tests/m2/test_views.py` | ✅ DONE | Primary Agent | 🟡 HIGH |
| **Code review + 10 bug fixes** (HTMX partials, DELETE 405, ProtectedError, overlap DEC-005, optimistic locking, duplicate OCR proposals, HTMX CSRF, size-limit sync, JSON-swap, template quote) | ✅ DONE | Primary Agent | 🔴 CRITICAL |
| 6 regression tests in `tests/m2/test_review_fixes.py` | ✅ DONE | Primary Agent | 🟡 HIGH |
| Accessibility: keyboard, focus, 200% zoom, 320px reflow | 🟡 PENDING | Primary Agent | 🟢 MEDIUM |
| Manual Jan observation of J1–J4 journeys | 🟡 PENDING | **Operator (Jan)** | 🔴 CRITICAL |

---

## Phase 6: Parallel Tracks (Can Proceed Now)

### Plan K — Server62 Readiness (Sysadmin)
| Sub-task | Status | Owner | Priority |
|---|---|---|---|
| Run `docs/operations/collect-plan-k-evidence.sh` | ☐ PENDING | **Sysadmin** | 🟡 HIGH |
| Provide capacity evidence (15 GiB / 15% free) | ☐ PENDING | Sysadmin | 🔴 CRITICAL for real-data |
| Provide backup/restore test evidence | ☐ PENDING | Sysadmin | 🔴 CRITICAL for real-data |
| Provide monitoring/TLS/permissions evidence | ☐ PENDING | Sysadmin | 🟡 HIGH |

### Plan AE — GitLab Remote + CI (DEC-016)
| Sub-task | Status | Owner | Priority |
|---|---|---|---|
| Pavel approves DEC-016 (explicit approval) | ☐ PENDING | **Pavel** | 🟢 MEDIUM |
| Create GitLab project (private) | ☐ PENDING | Primary Agent | 🟢 MEDIUM |
| Add GitLab remote: `git remote add gitlab ...` | ☐ PENDING | Primary Agent | 🟢 MEDIUM |
| Configure GitLab CI/CD variables | ☐ PENDING | Primary Agent | 🟢 MEDIUM |
| Push mirror: `git push gitlab --mirror` | ☐ PENDING | Primary Agent | 🟢 MEDIUM |
| Schedule periodic mirror pull | ☐ PENDING | Primary Agent | 🟢 MEDIUM |

### Plan L — Historical Document Cleanup
| Sub-task | Status | Owner | Priority |
|---|---|---|---|
| ✅ `plans/2026-08-11-consolidated-roadmap.md` header added | ✅ DONE | Primary Agent | — |
| ✅ `plans/2026-08-11-plan-b-opencode-cleanup-workflows.md` header added | ✅ DONE | Primary Agent | — |
| ✅ `plans/2026-08-11-plan-c-opencode-research.md` header added | ✅ DONE | Primary Agent | — |
| ✅ `docs/paddleocr/README.md` header added | ✅ DONE | Primary Agent | — |

### Plan AC — v12 Scripts Classification
| Sub-task | Status | Owner | Priority |
|---|---|---|---|
| ✅ v12 scripts moved to `quarantined_research_artifacts` | ✅ DONE | Primary Agent | — |

---

## Legacy Cleanup (Ready for Staging)

| Sub-task | Status | Owner | Package |
|---|---|---|---|
| Delete `scripts/a1_core.py.backup` | ✅ DONE | Primary Agent | `legacy_cleanup` |
| Delete `portal/settings.py.bak` | ✅ DONE | Primary Agent | `legacy_cleanup` |
| Delete `config/a1_field_coords.json` | ✅ DONE | Primary Agent | `legacy_cleanup` |
| Delete `config/a1_checkbox_coords.json` | ✅ DONE | Primary Agent | `legacy_cleanup` |
| Delete `config/a1_field_map.json` | ✅ DONE | Primary Agent | `legacy_cleanup` |
| `config/a1_provisional.json` restored (policy-only) | ✅ DONE | Primary Agent | `legacy_cleanup` |
| Updated `tests/test_comprehensive.py` to use `a1_layout.json` | ✅ DONE | Primary Agent | — |

---

## Validation Gates (Must Pass Before Commits)

| Gate | Command | Status |
|---|---|---|
| Planning validator | `venv/bin/python scripts/validate_planning.py --json` | ✅ PASS (24/24) |
| Change packages validator | `venv/bin/python scripts/validate_change_packages.py --json` | ✅ PASS |
| M2 scaffold gate | `venv/bin/python scripts/check_m2_scaffold_gate.py --json` | ✅ OPEN |
| Full test suite | `venv/bin/python -m pytest -q` | ✅ 496 passed (479 + 11 M2 views + 6 review-fix) |
| Git diff check | `git diff --check` | ☐ PENDING (before commit) |
| PII/secret check on staged | Manual inspection | ☐ PENDING (before commit) |

---

## Dependencies Graph

```
R-01 → R-02 → R-03 → Phase 2 (Regen) → Phase 3 (Cleanup) → Phase 4 (Plan R done)
                                                      ↓
                                            Phase 5 (M2 Sprint) ← Phase 6 (Parallel)
```

**Critical Path:** R-01 → R-02 → R-03 → Regen → M2 Sprint

---

## Notes for Next Session

1. **Operator must complete R-01/R-02/R-03** before any regeneration can proceed
2. **Mock CSV is validated end-to-end** — generates 11 PDFs, 33 previews, passes quality gate
3. **Document IDs in cohort.json MUST be `/2026/`** — generator validates year matches issue_date
4. **Never commit PII** — `a1/`, `output/`, `secrets/`, `.env` are gitignored
5. **Stage exact paths only** — use `change-packages.yml` package definitions
6. **Run all validation gates** before any commit request

---

*Attach to Plan R, Plan M2, roadmap.md for tracking. Update status checkboxes as work progresses.*