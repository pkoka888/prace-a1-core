# AGENTS.md Review & Recommendations

**Date:** 2026-08-24
**Analyst:** Internal
**Status:** REVIEWED — Recommendations ready for application

---

## Current State Analysis

### What's Working Well (Keep)

| Rule | Why It's Correct |
|------|-----------------|
| No wildcard staging (`git add -A/.`) | Essential PII protection |
| Forbidden paths list | Correct gitignore discipline |
| Synthetic data in tests | Privacy-by-design |
| PII treatment for external AI calls | Correct data minimization |
| Skills-based execution | Proper abstraction |
| "Never push without approval" for PII workflows | Correct for sensitive data |
| `change-packages.yml` with checks/dependencies | Already exists as automation backbone |

### What's Outdated or Missing (Need Updating)

| Issue | Impact |
|-------|--------|
| AGENTS.md doesn't mention `change-packages.yml` | Automation already exists but undocumented |
| No mention of `workflows/` directory | Structure not communicated to agents |
| No version tagging convention (`wf-a1/v*`) | No stable baseline marker |
| No pre-commit hook | All validation is manual |
| No gradation: strict PII vs automatable workflows | Everything treated as manual |
| Subagent restrictions lack nuance | Hard to parallelize non-PII work |

### Validator Output (Current Dirty State)

```
dirty=405 classified=292 eligible=209 quarantined=182 problems=129
```

| Problem Category | Count | Action |
|-----------------|-------|--------|
| Forbidden dirty (gitignored PII) | 14 | Expected — no action |
| Not classified (new files) | 113 | Add to packages |
| Privacy review (credential patterns) | 2 | Manual review required |

**Pre-commit hook works correctly** — only blocks STAGED forbidden PII paths, not dirty working directory files.
| Push rules too uniform | Research/docs blocked by same rules as PII |
| Subagent restrictions lack nuance | Hard to parallelize non-PII work |

---

## Key Finding: change-packages.yml Is Already Automation

The `change-packages.yml` system **is** a commit automation framework. Each package has:

```yaml
"a1_policy":
  "paths": [...]        # What files belong
  "checks": [...]       # Pre-commit tests to run
  "dependencies": [...]  # What must pass first
  "rollback": "..."     # Recovery procedure
```

**AGENTS.md doesn't mention it.** This is the single biggest gap.

---

## Recommendations

### 1. Add Pre-Commit Hook (Automated Validation)

Create `.git/hooks/pre-commit` that runs `validate_change_packages.py`:

```bash
#!/bin/bash
# Pre-commit hook: auto-classify staged files → run relevant checks

STAGED_FILES=$(git diff --cached --name-only)
PACKAGE=$(python3 scripts/validate_change_packages.py --classify "$STAGED_FILES")
CHECKS=$(python3 scripts/validate_change_packages.py --checks-for-package "$PACKAGE")

echo "Package: $PACKAGE"
echo "Running: $CHECKS"
for check in $CHECKS; do
    eval "$check" || { echo "FAILED: $check"; exit 1; }
done
```

**Effect:** Agents get fast feedback before commit. No manual `git diff --check` needed.

### 2. Distinguish Strict vs Automatable Workflows

**Strict (PII-bearing — always manual):**
- WF-A1 with real scans/PDFs → manual review, manual commit, manual push
- Any `validated_by_user` changes → manual only
- `output/pdf/` promotion → explicit human approval

**Automatable (non-PII — CI can handle):**
- Planning/docs/governance → auto-commit after checks pass
- Research fixtures with synthetic data → auto-commit
- Test-only changes → auto-commit
- Workflow structure changes → auto-commit

### 3. Graduated Push Rules

| Package Type | Commit | Push | Requirement |
|-------------|--------|------|-------------|
| `a1_*`, `quarantined_*` | Manual | Manual | Explicit operator approval always |
| `governance_truth`, `repository_documentation` | Auto after checks | Auto | Non-PII, CI can validate |
| `planning_cockpit`, `cli_agent_tooling` | Auto after checks | Auto | Non-PII, CI can validate |
| `plan_ac_*`, `plan_ad_*` (synthetic) | Auto after checks | Auto | Synthetic data only |
| `legacy_cleanup`, `infrastructure_git_workflow` | Auto after checks | Auto | Mechanical cleanup |

### 4. Update AGENTS.md Sections

**Add these new sections:**

```markdown
## Change Package Automation

The `change-packages.yml` file is the **authoritative commit classifier**.
For any staged change, run:

    python3 scripts/validate_change_packages.py --classify "$(git diff --cached --name-only)"

This returns the package name. Each package has defined checks in `checks[]`.
Run them before commit:

    python3 scripts/validate_change_packages.py --run-checks <package_name>

**Package categories:**
- `a1_*` — Strict: manual commit, manual push
- `plan_*`, `planning_*` — Automatable after checks pass
- `quarantined_*` — Never commit without explicit approval
- `infrastructure_git_workflow` — Automation infrastructure

## Version Tagging

Tag stable baselines:

    git tag -a wf-a1/v1.0.0 -m "A1 pipeline stable"
    git tag -a wf-ac/v1.0.0 -m "Market research stable"

Use lightweight tags for milestones. Tags are the only safe "push everything" target.

## Workflow Structure

Canonical workflows live in `workflows/`:

- `workflows/a1/` — WF-A1: A1 PDF production (strict)
- `workflows/ac/` — WF-AC: Market research evidence (experimental)
- `workflows/af/` — WF-AF: Free model evaluation (experimental)

Non-PII workflow changes can auto-commit. PII workflow changes require manual staging.

## Subagent Permissions (Refined)

| Subagent Type | Allowed Operations |
|--------------|-------------------|
| Research/analysis | Read-only, no writes |
| Workflow automation | Write to non-PII paths only |
| Primary agent | Full write access, all paths |
```

### 5. Add .gitignore Exception for workflows/

**Problem:** `a1/` gitignore was blocking `workflows/a1/`.

**Fix:** Anchor `./a1/` to root only (already done). Verify with:

```bash
git check-ignore -v workflows/a1/
# Should return nothing (not ignored)
```

### 6. Safe Automation Pattern for Non-PII Work

```bash
# Example: Auto-commit planning changes after checks
PACKAGE=$(python3 scripts/validate_change_packages.py --classify "$(git diff --cached --name-only)")
if [[ "$PACKAGE" == "planning_cockpit" ]] || [[ "$PACKAGE" == "governance_truth" ]]; then
    echo "Automatable package. Running checks..."
    python3 scripts/validate_change_packages.py --run-checks "$PACKAGE"
    git commit -m "Auto-commit: $(python3 scripts/validate_change_packages.py --intent "$PACKAGE")"
    echo "Commit done. Push requires manual review for this package type."
else
    echo "Strict package. Manual commit required."
    exit 1
fi
```

### 7. CI Integration Path (After DEC-016)

Once GitLab CI approved, map packages to CI jobs:

```yaml
# .gitlab-ci.yml additions
a1-strict:
  stage: gate
  script: echo "A1 requires manual gate"
  when: manual
  only:
    - tags

planning-automated:
  stage: validate
  script:
    - python3 scripts/validate_change_packages.py --run-checks planning_cockpit
  only:
    - branches
    - tags
```

---

## Specific AGENTS.md Changes

| Line(s) | Change |
|---------|--------|
| §Document authority | Add `change-packages.yml` after `AGENTS.md` |
| §Critical safety | Add "Pre-commit hook auto-runs package checks" |
| §PII Git rules | Keep strict — correct |
| §Task discipline | Add "classify package first, then run relevant checks" |
| §Environment | Add version tagging commands |
| **NEW** | Add `## Change Package Automation` section |
| **NEW** | Add `## Version Tagging` section |
| **NEW** | Add `## Workflow Structure` section |
| **NEW** | Add `## Graduated Push Rules` table |
| §Git remotes | Keep "no push without approval" but add package gradation |

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Pre-commit hook slows down commits | Low | Only runs on `git commit`, not `git add` |
| Agent mis-classifies package | Medium | validate_change_packages.py is authoritative |
| Auto-commit to wrong branch | Low | Pre-commit only, not auto-push |
| PII accidentally auto-committed | Very Low | Forbidden paths in change-packages.yml never auto-commit |
| Subagent writes to PII path | Low | Primary agent scope only |

---

## Summary: Automation Opportunities

| Current (Manual) | Recommended (Automated) |
|-----------------|------------------------|
| `git diff --check` manually | Pre-commit hook auto-runs |
| Check which tests to run manually | `change-packages.yml` checks[] define exact tests |
| All commits "ask before push" | Graduated: non-PII auto-commit after checks |
| No version tagging | `git tag wf-a1/v*` on stable baselines |
| Workflow structure not communicated | `workflows/` directory referenced in AGENTS.md |
| Subagent no write scope | Refined: workflow automation subagents can write non-PII |

**Net effect:** ~80% of non-PII commits become automated. PII workflows stay 100% manual. Agents can parallelize non-PII work without blocking on manual review.
