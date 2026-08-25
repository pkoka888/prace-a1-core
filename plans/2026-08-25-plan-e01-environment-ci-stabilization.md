# Plan E-01: Environment & CI Stabilization

**Status:** `planned`
**Author:** Primary Agent
**Created:** 2026-08-25
**Modified:** 2026-08-25
**Exit criteria:** All dependencies install correctly; basic CI runs; pre-commit functional

---

## Context

The project has an incomplete Python environment:
- `requirements.txt` contains `rapidocr==3.9.2` but it was not installed
- `onnxruntime` (required by rapidocr) was missing
- No lock file for reproducibility
- No GitHub Actions CI
- No standard pre-commit configuration

This blocks local OCR workflows and CI automation.

## Actions

### E-01.1: Fix requirements.txt
- [x] Add `onnxruntime>=1.29` (required by rapidocr)
- [x] Verify all packages install correctly

### E-01.2: Generate lock file
- [x] Run `pip freeze > requirements-lock.txt`
- [ ] Commit lock file

### E-01.3: Update OCR documentation
- [ ] Fix import path in `workflows/a1/README.md`: `from rapidocr import RapidOCR`
- [ ] Update return value handling for `RapidOCROutput` object
- [ ] Document `minimax/minimax-m3:free` works for OCR

### E-01.4: Create GitHub Actions CI
- [ ] Create `.github/workflows/ci.yml`
  - Fast tests on every PR
  - Slow tests (OCR/PDF) on schedule + main push
  - pip caching
- [ ] Verify CI runs successfully

### E-01.5: Create pre-commit config
- [ ] Create `.pre-commit-config.yaml`
  - trailing-whitespace, end-of-file-fixer, check-yaml
  - ruff for Python linting
  - gitleaks for secret detection
- [ ] Test pre-commit hooks

### E-01.6: Update validate_change_packages for CI
- [ ] Ensure pre-commit hook works with change-package validation
- [ ] Document CI-only validation path

## Verification

```bash
# Verify all deps install
venv/bin/pip install -r requirements.txt

# Verify lock file matches
venv/bin/pip freeze | diff - requirements-lock.txt

# Verify pre-commit
pre-commit run --all-files

# Verify CI (after GitHub Actions setup)
# Check PR status at https://github.com/pkoka888/prace-v-nemecku/actions
```

## Files

| File | Action |
|------|--------|
| `requirements.txt` | Modified - added onnxruntime |
| `requirements-lock.txt` | Created |
| `.github/workflows/ci.yml` | Create |
| `.pre-commit-config.yaml` | Create |
| `workflows/a1/README.md` | Update OCR docs |

## Risks

| Risk | Mitigation |
|------|------------|
| Lock file drifts from requirements | Run `pip freeze` on each dependency change |
| CI secrets exposure | Use GitHub secrets, never log PII |
| Pre-commit slows commits | Use `pre-commit run --files` for targeted runs |

## Dependencies

- None (can start immediately)

## Notes

- Per AGENTS.md: GitLab CI activation requires DEC-016 approval
- This plan covers GitHub Actions only (existing GitLab CI remains inactive)
- PII paths (`a1/`, `scans/`, etc.) remain gitignored per policy
