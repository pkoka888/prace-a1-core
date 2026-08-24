# Workflow & Framework Naming, Archival & CI/CD Report

**Date:** 2026-08-24
**Author:** Internal Analysis
**Status:** DRAFT — For Review

---

## 1. Executive Summary

This project contains **4 distinct workflows** that must be clearly separated by naming, versioning, and archival strategy. The A1 PDF production pipeline is the only **production-active** workflow. The others are either **completed**, **experimental**, or **proposed-not-active**.

Key actions needed:
1. Rename `docs/a1-workflow.md` → `workflows/a1/README.md` with `WF-A1` prefix
2. Archive 4 legacy/quarantined scripts
3. Version-tag the A1 pipeline (`v1.0.0`)
4. Leave GitLab CI dormant until DEC-016 approval
5. Create `workflows/` directory structure for separation

---

## 2. Workflow Identification & Naming

### 2.1 Active Workflows

| Workflow ID | Name | Canonical Scripts | Status |
|-------------|------|------------------|--------|
| **WF-A1** | A1 PDF Production Pipeline | `generate_provisional_a1.py`, `a1_core.py`, `finalize_a1.py`, `a1_quality_gate.py` | **Production Active** |
| **WF-AE** | Change Package Validation | `validate_change_packages.py`, `validate_planning.py`, `validate_approvals.py` | **Active (Plan AE)** |
| **WF-M2** | Portal M2 Prototype Sprint | `portal/release1a/`, `check_m2_scaffold_gate.py` | **Active (Plan M2)** |
| **WF-E** | Architecture Proofs | `run_architecture_proofs.py` | **Completed (Plan E)** |

### 2.2 Experimental/Research Workflows

| Workflow ID | Name | Canonical Scripts | Status |
|-------------|------|------------------|--------|
| **WF-AC** | Market Research Evidence | `collect_market_evidence.py`, `normalize_datasets.py`, `score_research_results.py`, `generate_research_cockpit.py` | **Experimental (Plan AC)** |
| **WF-AF** | Free Model Evaluation | `run_free_model_eval.py`, `run_collector_proposals.py`, `run_collector_proposals_v12.py` | **Experimental (Plan AF)** |

### 2.3 Proposed Not-Active

| Workflow ID | Name | Status | Blocker |
|-------------|------|--------|---------|
| **WF-CI** | GitLab CI/CD Pipeline | **Proposed** | DEC-016 not approved |
| **WF-PORTAL** | Jan-First Web Portal | **Proposed** | M2 prototype pending |

---

## 3. Proposed Naming Convention

### 3.1 Directory Structure

```
workflows/                    # All production & experimental workflows
├── a1/                       # WF-A1: A1 PDF Production
│   ├── README.md             # Workflow documentation
│   ├── scripts/              # Symlink or reference to scripts/
│   ├── SKILL.md              # Skill reference
│   └── config/               # Workflow-specific config
├── ac/                       # WF-AC: Market Research Evidence
│   ├── README.md
│   └── ...
└── af/                       # WF-AF: Free Model Evaluation
    └── ...

scripts/                      # Canonical production scripts
├── a1_*.py                   # WF-A1 production (keep existing names)
├── ae_*.py                   # WF-AE validation scripts
├── m2_*.py                   # WF-M2 prototype scripts
research/                     # Research data & outputs (quarantined)
prototypes/                   # Experimental prototypes
portal/                       # Web portal (future)
plans/                        # Plan definitions (authoritative)
docs/
├── workflows/                # NEW: Workflow documentation
│   ├── a1/                   # WF-A1 docs (moved from docs/a1-workflow.md)
│   ├── ac/                   # WF-AC docs
│   └── af/                   # WF-AF docs
```

### 3.2 Script Versioning

| Script | Current | Proposed | Rationale |
|--------|---------|----------|----------|
| `generate_provisional_a1.py` | (none) | `v1.0.0` tag | First stable release |
| `a1_core.py` | (none) | `v1.0.0` tag | Stable rendering engine |
| `a1_quality_gate.py` | (none) | `v1.0.0` tag | QA pipeline stable |
| `finalize_a1.py` | (none) | `v1.0.0` tag | Ready for v1 |

**Version tagging:** `git tag -a wf-a1/v1.0.0 -m "A1 production pipeline v1.0.0"`

### 3.3 Current vs Proposed File Locations

| Current Location | Proposed Location | Action |
|-----------------|-------------------|--------|
| `docs/a1-workflow.md` | `workflows/a1/README.md` | **Move & rename** |
| `scripts/a1_core.py.bak.*` | `workflows/a1/.archive/` | **Archive** |
| `scripts/validate_ocr_proposals.py` | `workflows/a1/.archive/` | **Archive** |
| `scripts/validate_collector_execution*.py` | `workflows/ac/.archive/` | **Archive** |
| `ocr/_ocr_worker.py` | `workflows/a1/ocr_worker.py` | **Move or keep in-place** |
| `docs/paddleocr/` | `workflows/research/.archive/paddleocr/` | **Archive** |

---

## 4. Git Repository Audit

### 4.1 Current Branch State

```
BRANCH: feat/prace-readiness-plan-2026-08-13
├── Status: Working branch (not yet merged)
├── Tracking: origin/feat/prace-readiness-plan-2026-08-13
├── Ahead: ~20 commits uncommitted changes
└── Contains: WF-A1 fixes, M2 prototype, research tooling

REMOTES:
├── origin → https://github.com/pkoka888/prace-v-nemecku.git
│   └── Branches: feat/prace-readiness-plan-2026-08-13, master
└── (no GitLab remote configured — per DEC-016 proposal)
```

### 4.2 Gitignore Status

**Correctly gitignored (must never commit):**
- `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`, `employees/scans/`, `output/`, `runtime/portal/`, `secrets/`, `.env`

**⚠️ Concern:** `scans/processed/` is NOT explicitly gitignored. The `processed/` directory contains identity card scans (PII). This should be added to `.gitignore`:

```
scans/processed/
```

### 4.3 Archive Candidates (Recommended)

| File | Reason to Archive | Risk if Kept |
|------|-------------------|--------------|
| `scripts/a1_core.py.bak.1787572010` | Stale backup | Low (duplicated code) |
| `scripts/a1_core.py.bak.1787572031` | Stale backup | Low (duplicated code) |
| `scripts/validate_collector_execution.py` | v1.1 superseded by v12 | Medium (confusion) |
| `scripts/validate_collector_execution_v12.py` | v12 with integrity issues | Medium (confusion) |
| `scripts/validate_ocr_proposals.py` | Deferred per Plan R | Medium (deprecated workflow) |
| `docs/paddleocr/` | Quarantined per plans INDEX | Low (clearly obsolete) |
| `cli-docs-update/` | CLI doc experiments | Low (historical only) |
| `research/benchmark-experimental/` | Experimental benchmark | Medium (outdated schemas) |
| `plans/2026-08-11-consolidated-roadmap.md` | Superseded by plans/INDEX.md | Low |

---

## 5. GitLab CI/CD Analysis

### 5.1 Current State

| Item | Status | Notes |
|------|--------|-------|
| `.gitlab-ci.yml` | **Exists (proposed)** | NOT committed to Git |
| GitLab remote | **Not configured** | Per DEC-016 proposal |
| GitLab runner | **Not installed** | Requires sysadmin |
| DEC-016 | **Proposed-default** | Not activated |

### 5.2 Recommended Approach

**Keep GitLab CI dormant until:**
1. DEC-016 is formally approved
2. LAN/Tailscale URLs confirmed
3. Runner installed and tested
4. PII-safe artifact handling verified

**Meanwhile:** Use GitHub Actions as lightweight CI (optional).

### 5.3 When Activating GitLab CI

The existing `.gitlab-ci.yml` design is sound:
- `validate` stage → automated checks
- `test` stage → unit tests
- `gate` stage → `when: manual` approval jobs

**Key safety rules:**
```yaml
variables:
  A1_PRIVATE_DIR: ""  # Must not be set in CI — operator only

a1_qa_job:
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"  # Only on schedule
```

---

## 6. Version Strategy

### 6.1 A1 Production Pipeline (WF-A1)

| Component | Version | Schema | Notes |
|-----------|---------|--------|-------|
| `a1_core.py` | 1.0.0 | — | Stable rendering |
| `finalize_a1.py` | 1.0.0 | — | Stable composition |
| `a1_quality_gate.py` | 1.0.0 | — | Stable QA |
| `generate_provisional_a1.py` | 1.0.0 | — | Stable entry point |
| Institution profiles | 1.0 | — | Per-profile versioning |
| `a1_layout.json` | 1.0 | — | Layout schema |

**Tag format:** `wf-a1/v1.0.0-YYYYMMDD`

### 6.2 Research Workflows (WF-AC, WF-AC)

| Component | Version | Schema | Notes |
|-----------|---------|--------|-------|
| Research model | 1.2 | `research-model-1.2.json` | Active |
| Collector protocol | 1.1 | `collector-protocol-1.1.json` | Active |
| Query packs | 1.1 | — | Active |

### 6.3 Portal (WF-PORTAL)

| Component | Version | Notes |
|-----------|---------|-------|
| Django project | 1.0.0 | Release 1A target |
| M2 prototype | 0.1.0 | Pre-alpha |

---

## 7. Recommendations

### 7.1 Immediate Actions (This Session)

| Priority | Action | Rationale |
|----------|--------|-----------|
| **HIGH** | Add `scans/processed/` to `.gitignore` | PII risk — identity scans |
| **HIGH** | Move `docs/a1-workflow.md` → `workflows/a1/README.md` | Name separation |
| **HIGH** | Archive `scripts/a1_core.py.bak.*` | Reduce confusion |
| **MEDIUM** | Create `workflows/` directory structure | Official separation |
| **MEDIUM** | Tag A1 pipeline `wf-a1/v1.0.0` | Version clarity |
| **LOW** | Archive `docs/paddleocr/` | Clearly obsolete |

### 7.2 Short-Term (Before Release 1A)

| Priority | Action | Rationale |
|----------|--------|-----------|
| **HIGH** | Formally approve DEC-016 or close GitLab proposal | Clarity on CI/CD path |
| **HIGH** | Verify GitHub Actions as lightweight CI option | Continuous validation |
| **MEDIUM** | Document `workflows/` structure in `AGENTS.md` | Agent instruction alignment |
| **MEDIUM** | Create `workflows/ac/README.md` | WF-AC documentation |
| **LOW** | Archive `plans/2026-08-11-consolidated-roadroadmap.md` | Superseded |

### 7.3 Long-Term (Release 1A+)

| Priority | Action | Rationale |
|----------|--------|-----------|
| **HIGH** | Activate GitLab CI after DEC-016 approval | Automated validation |
| **HIGH** | Migrate A1 pipeline to versioned package | `pip install prace-a1~=1.0` |
| **MEDIUM** | Create `workflows/af/README.md` | WF-AF documentation |
| **LOW** | Move research scripts to separate `research/` repo | Reduce monorepo size |

---

## 8. Archival Best Practices Applied

### 8.1 What to Archive

Based on analysis:

**Scripts (4 files):**
- `scripts/a1_core.py.bak.1787572010` — stale backup
- `scripts/a1_core.py.bak.1787572031` — stale backup
- `scripts/validate_collector_execution.py` — superseded v1.1
- `scripts/validate_collector_execution_v12.py` — integrity issues

**Documentation (potentially 20+ files):**
- `docs/paddleocr/*` — quarantined per plans INDEX
- `cli-docs-update/*` — experimental CLI docs
- `plans/2026-08-11-consolidated-roadmap.md` — superseded
- `docs/prototypes/2026-08-13-google-ai-studio-frontend-review.md` — quarantined

### 8.2 Archive Location

```
workflows/
├── a1/
│   └── .archive/              # A1 historical scripts
├── ac/
│   └── .archive/              # Research superseded scripts
└── af/
    └── .archive/              # Free model eval superseded

# Or simply:
.archive/
├── a1/                        # A1 superseded
├── ac/                        # Research superseded
└── af/                        # Free model eval superseded
```

### 8.3 Archival Process

```bash
# 1. Copy to archive location
cp scripts/a1_core.py.bak.* workflows/a1/.archive/

# 2. Remove from scripts/
rm scripts/a1_core.py.bak.*

# 3. Commit with tag
git add workflows/a1/.archive/
git commit -m "archive: move A1 stale backups"
git tag -a archive/wf-a1-20260824 -m "Archive stale A1 backups"
```

---

## 9. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `scans/processed/` committed to Git | **HIGH** | Critical (PII) | Add to `.gitignore` immediately |
| Stale backups cause confusion | Medium | Low | Archive or delete |
| Wrong OCR validator used | Medium | High | Archive `validate_ocr_proposals.py` |
| GitLab CI activates before PII controls ready | Low | High | Keep dormant until DEC-016 + sysadmin ready |
| Experimental workflows pollute main branch | Medium | Medium | Use `research/` prefix consistently |

---

## 10. Proposed File Map (Target State)

```
workflows/                    # NEW: Top-level workflow separation
├── a1/                       # WF-A1: A1 PDF Production
│   ├── README.md             # (moved from docs/a1-workflow.md)
│   ├── SKILL.md             # Reference to .agents/skills/a1-pdf-production/
│   └── .archive/            # Archived: stale backups
├── ac/                       # WF-AC: Market Research Evidence
│   ├── README.md
│   └── .archive/            # Archived: superseded collector scripts
└── af/                       # WF-AF: Free Model Evaluation
    └── README.md

scripts/                      # Canonical production scripts
├── a1_generate_provisional_a1.py  # (existing)
├── a1_core.py                    # (existing)
├── a1_finalize.py                # (existing)
├── a1_quality_gate.py            # (existing)
├── ae_validate_change_packages.py # (existing)
├── ae_validate_planning.py        # (existing)
└── m2_check_scaffold_gate.py     # (existing)

research/                     # Research data (quarantined)
├── acquisition/
├── schemas/
│   └── superseded/          # v1.0, v1.1 archived
└── review/

portal/                       # Web portal (future)
release1a/

plans/                       # Authoritative plans (unchanged)
docs/
├── workflows/               # (new — workflow docs)
├── decisions/               # (existing)
└── security/               # (existing)
```

---

## 11. Open Questions

1. **Should `scans/processed/` be gitignored or tracked?** Currently not in `.gitignore` — contains PII scans that need retention for audit. Recommend: **gitignored** (PII should not be in repo).

2. **Should we create a `research/` repo vs monorepo?** Current monorepo is manageable at current size. Recommend: **keep monorepo** until >500 files or CI complexity unmanageable.

3. **GitLab CI timeline?** DEC-016 proposed but not approved. Recommend: **keep GitHub Actions as lightweight CI** option, full GitLab after DEC-016 approval.

4. **Version tagging now or at Release 1A?** A1 pipeline is functionally stable. Recommend: **tag now** as `wf-a1/v1.0.0` to mark stable baseline.

---

## 12. Summary

| Category | Current | Target |
|----------|---------|--------|
| Workflow separation | `scripts/` flat + docs scattered | `workflows/` directory per workflow |
| A1 documentation | `docs/a1-workflow.md` | `workflows/a1/README.md` |
| Stale backups | `scripts/a1_core.py.bak.*` | `workflows/a1/.archive/` |
| OCR worker | `ocr/_ocr_worker.py` | Keep in-place or `workflows/a1/` |
| Version tagging | None | Tag `wf-a1/v1.0.0` |
| GitLab CI | Proposed (dormant) | Keep dormant until DEC-016 |
| PII gitignore | Partial | Add `scans/processed/` |
| Research workflows | `research/` scattered | `workflows/ac/`, `workflows/af/` |

---

## Appendix A: File Classification Summary

| Classification | Files | Action |
|----------------|-------|--------|
| **Production Active** | 15 scripts, 10 institution profiles, 4 core A1 scripts | Keep, version-tag |
| **Experimental** | WF-AC scripts (12+), WF-AF scripts (5+) | Keep in `workflows/` |
| **Completed** | WF-E (architecture proofs) | Archive originals |
| **Legacy/Quarantined** | `a1_core.py.bak.*`, `validate_collector_execution*.py`, `validate_ocr_proposals.py`, `docs/paddleocr/` | Move to `.archive/` |
| **Proposed** | GitLab CI, Web portal | Keep dormant/proposed |
