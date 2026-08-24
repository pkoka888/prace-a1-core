# Project Gap Analysis & Best Practices Report

**Date:** 2026-08-24
**Repository:** `https://github.com/pkoka888/prace-v-nemecku.git`
**Branch:** `feat/prace-readiness-plan-2026-08-13` (30 commits ahead of master)
**Status:** Ready for review before merge

---

## Executive Summary

This report analyzes the current project state across 8 dimensions, identifies gaps against best practices, and provides actionable recommendations. The project has a **mature governance structure** with strong PII protection, clear plan lifecycle management, and well-defined agent constraints. Key improvements are in **automation, packaging, health monitoring, and documentation consolidation**.

---

## 1. File & Folder Structure

### Current State

```
prace-v-nemecku/
├── workflows/              # NEW: Workflow separation
│   ├── a1/             # A1 PDF production
│   ├── ac/              # Market research evidence
│   └── af/              # Free model evaluation
├── scripts/              # Production scripts (flat, no packaging)
├── config/              # JSON configurations
├── tests/               # Flat test structure (40+ files)
├── src/                 # Free model eval only
├── portal/              # Django portal (not in src/)
├── plans/               # Markdown plans (authoritative)
├── docs/               # Documentation
├── a1/                 # PII data (gitignored)
├── scans/               # PII scans (gitignored)
└── output/             # Generated PDFs (gitignored)
```

### Best Practice Finding: Python Packaging

| Current | Best Practice | Action |
|--------|--------------|--------|
| No `pyproject.toml` | Add `pyproject.toml` for packaging | **High** |
| Scripts in flat `scripts/` | Move importable code to `src/a1/` | **Medium** |
| Flat `tests/` | Organize into `tests/unit/`, `tests/integration/` | **Medium** |
| `portal/` at root | Move to `src/portal/` (Django project layout) | **Low** |

### Gap: Python Packaging

**Issue:** No `pyproject.toml` means no standard Python package management.

**Recommendation:** Create `pyproject.toml`:
```toml
[project]
name = "prace-v-nemecku"
version = "0.1.0"
requires-python = ">=3.13"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

### Gap: Test Organization

**Issue:** 40+ test files in flat `tests/` structure.

**Recommendation:**
```
tests/
├── unit/
├── integration/
├── architecture/
├── fixtures/         # Synthetic only
└── m2/
```

---

## 2. Automation (Git Hooks, CI/CD)

### Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Pre-commit hook | ✅ Working | Blocks PII, runs package checks |
| change-packages.yml | ✅ Active | 11 packages, quarantine system |
| GitLab CI | ❌ Proposed (DEC-016) | Not activated |
| GitHub Actions | ❌ None | Not configured |
| Pre-commit framework | ❌ Custom script | Could migrate to `.pre-commit-config.yaml` |

### Best Practice Finding: Change Package Validation

The `change-packages.yml` system is **sophisticated and well-designed**:

- ✅ Path classification into packages
- ✅ Per-package checks
- ✅ Quarantine for sensitive files
- ✅ Privacy indicators (credentials, personal paths)
- ✅ Dependency ordering
- ✅ Rollback instructions

**Gap:** No CI integration — only local pre-commit.

### Recommendation: Add GitHub Actions

```yaml
# .github/workflows/validate.yml
name: Validate
on: [pull_request, push]
jobs:
  change-packages:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate change packages
        run: python3 scripts/validate_change_packages.py --json
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash .git/hooks/pre-commit  # Or migrate to pre-commit framework
```

---

## 3. Plans & Roadmap Governance

### Current State: EXCELLENT

| Aspect | Status | Notes |
|--------|--------|-------|
| Status vocabulary | ✅ Controlled | 9 states (planned/active/blocked/etc.) |
| Roadmap | ✅ Authoritative | `roadmap.md` is sole source |
| ADRs | ✅ Active | `docs/decisions/ADR-NNN-*.md` |
| Plan lifecycle | ✅ Defined | Deprecate → historical → archived |
| Validator | ✅ Working | `validate_planning.py` |

### Best Practice Finding: Plan Governance

The plan governance is **mature and well-structured**:
- Nine-state vocabulary covers full lifecycle
- Decision register tracks ADRs
- Plans have explicit exit criteria
- `validate_planning.py` provides deterministic validation

### Gaps

| Gap | Impact | Action |
|-----|--------|--------|
| `superseded_by` not in plan headers | Unclear successor chain | Add `superseded_by` field to plan YAML |
| No archive manifest | Archival not tracked | Create `archive/MANIFEST.md` if archiving starts |
| 30 commits not merged to master | Branch divergence risk | Merge after review |

### Plan R Status (A1 Operations)

| Item | Status |
|------|--------|
| R-01: 7 Section 4 columns | ✅ Done |
| R-02: 2 missing people added | ✅ Done |
| R-03: doc_ids → /2026/ | ✅ Done |
| Canonical 11 PDFs | ✅ Done (now 15 with hucko + jaroslav) |
| Visual review | 🟡 Pending (operator) |
| Backup cleanup | 🟡 Pending (approval needed) |

---

## 4. Skills & Agent Operations

### Current State

| Skill | Status | Authority |
|-------|--------|----------|
| `a1-pdf-production` | ✅ Active | `.agents/skills/a1-pdf-production/SKILL.md` |
| `market-research-evidence` | ⚠️ Experimental | `.opencode/skills/market-research-evidence/SKILL.md` |
| AGENTS.md | ✅ Authoritative | 105 lines, principles-based |

### Best Practice Finding: Skill Structure

The skill structure follows industry best practices:
- Frontmatter metadata
- Authority declaration
- Explicit input/output contracts
- References (one-level deep)
- Activation gates (experimental until pilots pass)

### Gaps

| Gap | Action |
|-----|--------|
| `.opencode/skills/` mostly empty | Follow skill creation pattern when workflows stabilize |
| AGENTS.md doesn't mention `workflows/` | Add reference after creating structure |
| No formal handoff protocol | Use structured `handoff:` block in SKILL.md |

---

## 5. Business Objects (BO) & Services

### Current State: GOOD

```
portal/release1a/
├── models.py      # TenantModel base, org-scoped
├── services.py    # Auth, transactions, domain ops
├── forms.py       # Validation
└── views.py       # Request handling
```

### Best Practice Finding: Django Structure

The portal structure follows best practices:
- ✅ Abstract `TenantModel` for org-scoped ownership
- ✅ Service layer with auth decorators
- ✅ Optimistic locking (`version` field)
- ✅ Append-only `AuditEvent`
- ✅ `@transaction.atomic` boundaries

### Gaps

| Gap | Impact | Action |
|-----|--------|--------|
| No health endpoints | Can't deploy to k8s | Add `/health/live/` and `/health/ready/` |
| No structured logging | Hard to debug | Add request ID tracking |
| SQLite (dev) vs PostgreSQL (prod) | Inconsistency | Document in ADR-001 |

---

## 6. Service Health Monitoring

### Current State: MINIMAL

```python
def health(request):
    return JsonResponse({"status": "synthetic-m2", "real_data": False})
```

### Best Practice Finding: Health Probes

For production deployment, need:

| Probe | Purpose | Auth |
|-------|---------|------|
| `/health/live/` | Is process alive? | Public |
| `/health/ready/` | Can serve traffic? | Public |

### Recommendation

```python
# portal/release1a/health.py
def health_live(request):
    return JsonResponse({"status": "ok"})

def health_ready(request):
    checks = {"db": check_db()}
    overall = all(checks.values())
    return JsonResponse({
        "status": "ok" if overall else "degraded",
        "checks": checks,
    }, status=200 if overall else 503)
```

---

## 7. Repository & Git Workflow

### Current State

| Aspect | Status |
|--------|--------|
| Branches | `master` + `feat/prace-readiness` |
| Remote | GitHub only |
| Tags | `wf-a1/v1.0.0` (1 tag) |
| Pre-commit | ✅ Working |

### Gap: 30 Commits Behind Master

The branch is **30 commits ahead** of `master`. Risk: divergence.

### Recommendation

1. Review all 30 commits
2. Squash or rebase if many small commits
3. PR to `master`
4. Delete branch after merge

### Branch Naming Convention

Current: `feat/prace-readiness-plan-2026-08-13`

Best practice: `type/short-description`
- `docs/plan-r-a1-policy`
- `infra/gitlab-ci`
- `a1/visual-qa-workflow`

---

## 8. Documentation Structure

### Current State: GOOD

```
docs/
├── decisions/          # ADRs
├── architecture/      # ADR evidence
├── operations/        # Ops docs
├── research/          # Research docs
├── prototypes/        # Prototypes
└── security/          # Security policy
```

### Gap: No Central Entry Point

`docs/` needs an `index.md` or `README.md` as entry point.

### Recommendation

Create `docs/README.md`:
```markdown
# Documentation

## Getting Started
- [Setup](../README.md)
- [AGENTS.md](../AGENTS.md)

## Architecture
- [ADR-001](./decisions/ADR-001-jan-portal-architecture.md)
- [Security](./security/real-data-rules.md)

## Operations
- [Git Workflow](./operations/gitlab-integration.md)
```

---

## 9. Pre-commit Hook Analysis

### Current Implementation: GOOD

The custom pre-commit hook works correctly:
- ✅ Blocks PII paths at staging
- ✅ Runs package checks
- ✅ Warns on quarantined packages

### Gap: Pattern Bug (Fixed)

Pattern `ocr/` was matching `paddleocr/`. Fixed by anchoring: `(^|/)ocr/`.

### Future: Migrate to pre-commit Framework

Replace custom script with `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: change-packages
        name: Validate change packages
        entry: python3 scripts/validate_change_packages.py
        language: system
```

---

## 10. Merge Readiness Assessment

### Commits Ahead: 30

| Category | Count |
|----------|-------|
| Infrastructure | 7 |
| Plans/Governance | 5 |
| Research | 4 |
| Docs | 4 |
| A1 Production | 2 |
| Legacy cleanup | 1 |

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Branch divergence | Medium | Merge soon |
| Quarantined files staged | Low | Pre-commit blocks |
| PII committed | Very Low | Forbidden paths enforced |
| Tests broken | Low | 36 tests pass |

### Recommendation

**Ready to merge** after:
1. Review 30 commits (can be automated via PR diff)
2. Run full test suite
3. Verify no quarantined files in diff
4. Squash into logical commits

---

## Priority Matrix

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| **HIGH** | Merge to master | Low | Risk reduction |
| **HIGH** | Add health endpoints | Low | Production readiness |
| **HIGH** | Add GitHub Actions CI | Medium | Automation |
| **MEDIUM** | Create `pyproject.toml` | Medium | Packaging |
| **MEDIUM** | Organize tests | Medium | Maintainability |
| **MEDIUM** | Add docs/index.md | Low | Navigation |
| **LOW** | Migrate to pre-commit framework | Medium | Standardization |
| **LOW** | Move portal to src/ | High | Consistency |

---

## Summary: What's Working Well

1. ✅ **PII protection** — Forbidden paths, synthetic data, pre-commit
2. ✅ **Plan governance** — 9-state lifecycle, ADRs, validators
3. ✅ **Skill structure** — Well-defined contracts, activation gates
4. ✅ **Agent constraints** — Default-deny, explicit scope
5. ✅ **Change packages** — Sophisticated classification and checks
6. ✅ **Portal BO separation** — Service layer, auth, transactions

## Summary: Key Improvements Needed

1. **Merge to master** — 30 commits of divergence is risky
2. **Health endpoints** — Required for production deployment
3. **GitHub Actions CI** — Automation for PR validation
4. **`pyproject.toml`** — Standard Python packaging
5. **`docs/index.md`** — Documentation entry point
6. **Test organization** — Move toward unit/integration split

---

## Appendices

### A. Branch Status

```
feat/prace-readiness-plan-2026-08-13
├── 30 commits ahead of master
├── All committed and pushed
├── Pre-commit hook installed
└── Ready for PR
```

### B. Test Status

```
36 A1 tests: PASSED ✓
QA validation: PASSED ✓
15 PDFs / 45 previews: PASSED ✓
```

### C. Tag Status

```
wf-a1/v1.0.0 — A1 pipeline stable baseline
```

### D. Quarantined Files (NOT Committed)

These remain untracked and should NOT be committed:
- `a1/` (PII data)
- `research/acquisition/atomic-*` (quarantined per change-packages.yml)
- `research/benchmark-*`, `pilot/`, `processed/` (quarantined)
