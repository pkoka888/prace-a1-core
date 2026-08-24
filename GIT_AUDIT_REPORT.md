# Git Repository Audit Report

**Date:** 2026-08-24
**Branch:** `feat/prace-readiness-plan-2026-08-13` (PUSHED)
**Repository:** `https://github.com/pkoka888/prace-v-nemecku.git`

---

## 1. Repository Map

```
pkoka888/prace-v-nemecku
├── branches
│   ├── master (baseline - sanitized checkpoint c01aa2b)
│   ├── feat/prace-readiness-plan-2026-08-13 (active - 17 commits ahead of master)
│   ├── codex/unified-a1-core (historical)
│   ├── pre-rewrite/codex-unified-a1-core-20260812 (historical)
│   └── pre-rewrite/master-20260812 (historical)
├── remotes
│   └── origin → https://github.com/pkoka888/prace-v-nemecku.git
└── tags
    └── wf-a1/v1.0.0 (A1 pipeline stable baseline)
```

---

## 2. Commit History (feat/prace-readiness-plan-2026-08-13)

| Hash | Message | Plan |
|------|---------|------|
| `43eaf31` | feat: add pre-commit hook and AGENTS.md review | AE |
| `0d40d88` | feat: create workflows/ directory structure, archive legacy scripts | R, AE |
| `c413d2e` | test: quarantine stale plan-ac synthetic checkpoint | AC |
| `b2b65b2` | test: add provisional plan-ac research contracts | AC |
| `b84f6b8` | test: add synthetic invoice ingestion contracts | AD |
| `f535e22` | test: reconcile CLI verification tooling | L |
| `c23d8aa` | feat: validate planning catalog and cockpit assets | M, AE |
| `2198eef` | test: add fail-closed change-package validation | AE |
| `23c63d2` | docs: add research-stage repository guide | L |
| `e0a060f` | style: remove audit trailing whitespace | L |
| `8470c99` | docs: reconcile repository governance and planning truth | L |
| `32ac85e` | add reproducible CLI and agent audits | L |
| `4a8c0b1` | feat: Plan Q remediation and policy updates | Q |
| `ba06e05` | docs: classify deferred OCR validator | R |
| `3352dde` | docs: record sanitized sysadmin readiness evidence | K |

**Commits NOT pushed:** 0 (all 17 pushed ✓)

---

## 3. Working Directory Status

### 3.1 Modified Tracked Files (38 files)

| Plan | Files | Action |
|------|-------|--------|
| **Plan R (A1)** | `scripts/a1_core.py`, `scripts/finalize_a1.py`, `plans/2026-08-12-plan-r-a1-production-stabilization.md` | **READY** — commit |
| **Plan L (Agent ops)** | `plans/INDEX.md`, `plans/2026-08-12-plan-l-agent-operating-model.md`, `plans/2026-08-12-plan-f-jan-workflow-discovery.md` | **READY** — commit |
| **Plan M (Cockpit)** | `plans/2026-08-12-plan-m-visual-planning-cockpit.md`, `docs/prototypes/roadmap-portal/*` | **READY** — commit |
| **Plan E (Architecture)** | `plans/2026-08-12-plan-e-architecture-proofs-and-adr.md` | **READY** — commit |
| **Plans H/N/O** | `plans/2026-08-12-plan-h-ux-ui-and-copy-research.md`, `plans/2026-08-12-plan-n-full-platform-role-and-data-discovery.md`, `plans/2026-08-12-plan-o-database-and-transaction-architecture.md` | **READY** — commit |
| **Decisions** | `docs/decisions/ADR-001-jan-portal-architecture.md`, `docs/decisions/decision-register.md` | **READY** — commit |
| **Infrastructure** | `change-packages.yml`, `pytest.ini`, `requirements.txt`, `scripts/validate_planning.py` | **READY** — commit |
| **Plan R (Legacy cleanup)** | `config/a1_checkbox_coords.json`, `config/a1_field_coords.json`, `config/a1_field_map.json`, `plans/2026-11-consolidated-roadmap.md`, `plans/2026-08-11-plan-b-opencode-cleanup-workflows.md`, `plans/2026-08-11-plan-c-opencode-research.md`, `scripts/validate_collector_execution.py`, `scripts/validate_collector_execution_v12.py`, `docs/paddleocr/README.md` | **READY** — commit (deletions) |
| **Governance** | `roadmap.md`, `docs/decisions/2026-08-12-jan-release-1-solution-brief.md`, `config/a1_provisional.json` | **READY** — commit |
| **Tests** | `tests/test_comprehensive.py`, `tests/test_validate_planning.py` | **READY** — commit |
| **Ignored** | `.kilo/kilo.jsonc` | **DISCARD** — not relevant |

### 3.2 Untracked Files (100+ files)

| Category | Files | Action |
|----------|-------|--------|
| **A1 Production Data (PII)** | `a1/cohort.csv`, `a1/review.csv`, `a1/employees_normalized.json`, `a1/*.backup*` | **NEVER COMMIT** — gitignored |
| **Plan AE (GitLab CI)** | `.gitlab-ci.yml` | **READY** — add & commit |
| **Plan AF (Free Model Eval)** | `config/free-model-eval/`, `.opencode/agents/free-eval-*.md` | **READY** — add & commit |
| **Plan M2 (Portal Prototype)** | `portal/`, `manage.py` | **READY** — add & commit |
| **Plan AC (Research)** | `planning/approvals.json`, `planning/approvals.schema.json` | **READY** — add & commit |
| **Architecture Docs** | `docs/architecture/` | **READY** — add & commit |
| **Release 1A Docs** | `docs/release-1a/`, `docs/decisions/ADR-002-*.md` | **READY** — add & commit |
| **Research Docs** | `docs/research/`, `plans/2026-08-15-plan-af*.md`, `plans/2026-08-17-plan-m2*.md` | **READY** — add & commit |
| **Operational Docs** | `docs/operations/`, `docs/prototypes/research-cockpit/` | **READY** — add & commit |
| **CHANGELOG/Audit** | `CHANGELOG.md`, `PROJECT_AUDIT_REPORT.md` | **READY** — add & commit |
| **CLI Docs** | `cli-docs-update/` | **READY** — add & commit |
| **Institution Profiles** | `config/institutions/brno.json`, `decin.json`, `praha.json` | **READY** — add & commit |
| **DB Journal** | `db.sqlite3-journal` | **DISCARD** — runtime artifact |
| **TODO Tracking** | `docs/plans/TODO_TRACKING.md` | **REVIEW** — determine if relevant |

---

## 4. Plan Status vs Working Directory

| Plan | INDEX Status | Working Directory | Action |
|------|-------------|------------------|--------|
| **Plan R** | completed | `scripts/a1_core.py`, `scripts/finalize_a1.py` modified; legacy configs deleted | Commit + close |
| **Plan L** | active | `plans/INDEX.md`, `plans/plan-l-*.md` modified | Commit |
| **Plan M** | active | `plans/plan-m-*.md`, `docs/prototypes/roadmap-portal/*` modified | Commit |
| **Plan E** | completed | `plans/plan-e-*.md` modified | Commit |
| **Plans F/H/N/O** | active | Respective plan files modified | Commit |
| **Plan AE** | active | `.gitlab-ci.yml` untracked; `change-packages.yml` modified | Commit all |
| **Plan AF** | active | `config/free-model-eval/`, `.opencode/agents/free-eval-*.md` untracked | Commit |
| **Plan M2** | active | `portal/`, `manage.py` untracked | Commit |
| **Plan AC** | active | `planning/approvals.*` untracked | Commit |
| **Plan K** | active | `docs/operations/collect-plan-k-evidence.sh` untracked | Commit |

---

## 5. Recommended Git Structure

### 5.1 Branch Model

```
master                    ← Sanitized baseline (c01aa2b) — never force-push
  └─ feat/prace-readiness ← Current work branch (17 commits ahead)
       └─ (future: PR → merge to master when ready)

Tags:
  wf-a1/v1.0.0           ← A1 pipeline stable
  wf-r/v1.0.0             ← (future: Release 1A)
```

**Rule:** Branch from `master`, PR back to `master`. Never push directly to `master`.

### 5.2 Commit Strategy

| Change Type | Commit Message Pattern | Push |
|-------------|----------------------|------|
| A1 production | `a1: <description>` | Manual approval |
| Plan update | `<plan>: <description>` | Auto after checks |
| Infrastructure/CI | `infra: <description>` | Manual approval |
| Governance/Planning | `docs: <description>` | Auto after checks |
| Research (synthetic) | `research: <description>` | Auto after checks |
| Legacy cleanup | `chore: <description>` | Manual approval |
| Hotfix | `fix: <description>` | Manual approval |

### 5.3 Recommended Commit Sequence

```bash
# 1. Commit infrastructure (validated by pre-commit hook)
git add pytest.ini requirements.txt change-packages.yml scripts/validate_planning.py tests/test_validate_planning.py
git commit -m "infra: update test infrastructure and change-packages"

# 2. Commit governance/plans
git add plans/INDEX.md plans/2026-08-12-plan-l-*.md plans/plan-m-*.md plans/plan-e-*.md plans/plan-f-*.md plans/plan-h-*.md plans/plan-n-*.md plans/plan-o-*.md plans/plan-r-*.md roadmap.md docs/decisions/
git commit -m "plans: update plan statuses and governance docs"

# 3. Commit legacy cleanup (deletions)
git add -u config/a1_checkbox_coords.json config/a1_field_coords.json config/a1_field_map.json plans/2026-08-11-consolidated-roadmap.md plans/2026-08-11-plan-b-*.md plans/2026-08-11-plan-c-*.md scripts/validate_collector_execution.py scripts/validate_collector_execution_v12.py docs/paddleocr/
git commit -m "chore: remove legacy A1 configs and superseded plans"

# 4. Commit A1 scripts
git add scripts/a1_core.py scripts/finalize_a1.py config/a1_provisional.json
git commit -m "a1: update A1 production scripts"

# 5. Commit untracked (Plan AE/AF/M2/AC)
git add .gitlab-ci.yml config/free-model-eval/ .opencode/agents/ portal/ manage.py planning/approvals.json planning/approvals.schema.json
git commit -m "infra: add GitLab CI, free-model eval config, portal M2 prototype"

# 6. Commit architecture/release docs
git add docs/architecture/ docs/release-1a/ docs/decisions/ADR-002-*.md
git commit -m "docs: add architecture and Release 1A documentation"

# 7. Commit research and operational docs
git add docs/research/ docs/operations/ docs/prototypes/research-cockpit/ plans/2026-08-15-plan-af*.md plans/2026-08-17-plan-m2*.md
git commit -m "research: add AF/M2 plan docs and operational scripts"

# 8. Discard artifacts
git checkout -- .kilo/ db.sqlite3-journal
```

---

## 6. Recommended Repository Organization

### 6.1 Directory Conventions

```
prace-v-nemecku/
├── workflows/              # Canonical workflow definitions (tracked)
│   ├── a1/               # WF-A1: A1 PDF production
│   ├── ac/               # WF-AC: Market research evidence
│   └── af/               # WF-AF: Free model evaluation
├── scripts/               # Production scripts (tracked)
│   ├── a1_*.py          # A1 pipeline
│   ├── ae_*.py          # Change package validation
│   └── pre-commit        # Pre-commit hook
├── plans/                 # Authoritative plans (tracked)
├── docs/                  # Documentation (tracked)
├── config/                # Configuration (tracked)
├── tests/                 # Tests (tracked)
├── src/                   # Source packages (tracked)
├── research/              # Research outputs (tracked, synthetic)
├── portal/                # Web portal (future, tracked)
├── planning/              # Planning artifacts (tracked)
├── a1/                    # A1 production data (gitignored, PII)
├── scans/                 # Source scans (gitignored, PII)
├── output/                # Generated PDFs (gitignored, PII)
├── evidence/              # Audit evidence (gitignored, PII)
├── runtime/               # Portal runtime (gitignored)
└── secrets/               # Secrets (gitignored)
```

### 6.2 Tagging Convention

| Tag | Meaning | Example |
|-----|---------|---------|
| `wf-a1/v1.0.0` | Workflow stable release | A1 pipeline baseline |
| `r1a/v1.0.0` | Release 1A | Portal + A1 integrated |
| `plan-r/v1.0.0` | Plan R completion | A1 operations stable |
| `checkpoint/c01aa2b` | Sanitized baseline | Historical marker |

---

## 7. Immediate Action Items

| Priority | Action | Command |
|----------|--------|---------|
| **HIGH** | Commit infrastructure updates | `git add pytest.ini requirements.txt change-packages.yml scripts/validate_planning.py tests/test_validate_planning.py && git commit` |
| **HIGH** | Commit plan/governance updates | `git add plans/ docs/decisions/ roadmap.md && git commit` |
| **HIGH** | Commit legacy cleanup | `git add -u config/a1_checkbox_coords.json config/a1_field_coords.json config/a1_field_map.json && git commit` |
| **HIGH** | Commit A1 script updates | `git add scripts/a1_core.py scripts/finalize_a1.py && git commit` |
| **MEDIUM** | Add untracked files (AE/AF/M2) | `git add .gitlab-ci.yml config/free-model-eval/ .opencode/ agents/ portal/ manage.py && git commit` |
| **MEDIUM** | Add architecture docs | `git add docs/architecture/ docs/release-1a/ && git commit` |
| **LOW** | Discard artifacts | `rm db.sqlite3-journal && git checkout -- .kilo/` |
| **LOW** | Review TODO_TRACKING.md | Check if still relevant |

---

## 8. Push Rules (Recommended)

| Change Type | Commit | Push | Reason |
|-------------|--------|------|--------|
| A1 real-data (workflows/a1, a1/, scans/) | Manual | Manual | PII, strict |
| Plans/governance (plans/, docs/decisions/) | Auto after pre-commit | Manual | Non-PII, requires plan owner |
| Infrastructure (scripts/, config/, tests/) | Auto after pre-commit | Manual | Requires validation |
| Portal (portal/, manage.py) | Manual | Manual | Future production |
| Research synthetic (research/, config/free-model-eval/) | Auto after pre-commit | Manual | Synthetic data |
| Legacy cleanup | Manual | Manual | Destructive |

---

## 9. What Was Done Today

| Item | Status |
|------|--------|
| Pushed feat/prace-readiness to origin | ✓ Done |
| wf-a1/v1.0.0 tag created | ✓ Done |
| workflows/ directory created | ✓ Done |
| workflows/a1/, ac/, af/ structure | ✓ Done |
| Legacy scripts archived | ✓ Done |
| Pre-commit hook created + installed | ✓ Done |
| A1 test fixed (36 tests pass) | ✓ Done |
| AGENTS_REVIEW.md created | ✓ Done |
| hucko-martin PDF generated | ✓ Done |
| jaroslav-simek PDF generated | ✓ Done |
| patrik-zivot diacritics fixed (Život) | ✓ Done |
| decin.json institution created | ✓ Done |
| 15-worker cohort complete | ✓ Done |

---

## 10. What's Pending

| Item | Status |
|------|--------|
| Commit modified tracked files (38 files) | **NOT DONE** — needs review |
| Add untracked files (100+ files) | **NOT DONE** — needs classification |
| Plan R closure (mark completed, close R-01/R-02/R-03) | **NOT DONE** |
| Discard .kilo/ artifact | **NOT DONE** |
| Update TODO_TRACKING.md relevance | **NOT DONE** |
| Push remaining commits | **NOT DONE** — needs approval |

---

## 11. GitHub Repository Name

**`pkoka888/prace-v-nemecku`** on GitHub

**URL:** https://github.com/pkoka888/prace-v-nemecku

**Current branch pushed:** `feat/prace-readiness-plan-2026-08-13` — 17 commits ahead of `master`
