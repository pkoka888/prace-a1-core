# Python Environment & CI/CD Research Report

**Date:** 2026-08-25
**Repository:** `pkoka888/prace-v-nemecku`
**Branch:** `feat/prace-readiness-plan-2026-08-13`

---

## 1. Current State Analysis

### 1.1 Python Dependencies

**Current `requirements.txt`:**
```
jsonschema==4.26.0
numpy==2.5.2
pillow==12.3.0
pymupdf==1.28.2
pypdf==6.15.0
pytest==9.1.1
reportlab==5.0.0

Django==5.2.17
django-allauth[mfa]==65.19.1
django-q2==1.11.0
psycopg[binary]==3.3.4
cryptography==50.0.0

rapidocr==3.9.2
```

### 1.2 Installed venv Packages (Actual)

| Package | In requirements.txt? | Installed? |
|---------|---------------------|------------|
| Django | ✅ | ✅ |
| django-allauth | ✅ | ✅ |
| django-q2 | ✅ | ✅ |
| psycopg | ✅ | ✅ |
| cryptography | ✅ | ✅ |
| jsonschema | ✅ | ✅ |
| numpy | ✅ | ✅ |
| pillow | ✅ | ✅ |
| pymupdf | ✅ | ✅ |
| pypdf | ✅ | ✅ |
| pytest | ✅ | ✅ |
| reportlab | ✅ | ✅ |
| **rapidocr** | ✅ | ❌ **MISSING** |

### 1.3 Missing Dependencies Found

| Package | Status | Impact |
|---------|--------|--------|
| `rapidocr` | In requirements.txt but NOT installed | OCR workflow broken |
| `onnxruntime` | Required by rapidocr but NOT installed | rapidocr fails without it |
| `pytesseract` | Not in requirements.txt | Tesseract OCR unavailable |

### 1.4 OCR Stack Analysis

**Local OCR attempt results:**

| Tool | Attempted | Result | Error |
|------|-----------|--------|-------|
| `tesseract` CLI | Yes | Failed | Not installed on system |
| `pytesseract` | Yes | Failed | Not in venv |
| `rapidocr` | Yes | **Failed** | Not installed |
| `rapidocr` (after install) | Yes | **Failed** | Missing `onnxruntime` |
| `rapidocr` (after onnxruntime) | Yes | **Worked** | Returned OCR results |

**API Changes Found:**
- rapidocr 3.9.2 returns `RapidOCROutput` object (not tuple)
- Import is `from rapidocr import RapidOCR` (not `rapidocr_onnxruntime`)

---

## 2. Best Practices Research

### 2.1 Python venv Management

| Tool | When to Use | Recommendation |
|------|-------------|-----------------|
| **`venv`** | Simple projects, Python 3.3+ | **Use for lightweight isolation** |
| `virtualenv` | Legacy Python 2/3 | Avoid unless legacy |
| `conda`/`mamba` | Data science with CUDA/MKL | Overkill for pure Python |
| **`poetry`** | Modern apps/services | **Strong choice for new projects** |
| `pdm` | Performance-critical, pip-compatible | Good alternative to Poetry |

**Recommendation:** Keep using `venv` (current approach) but add lock files via `pip-compile` or migrate to Poetry.

### 2.2 Dependency Management

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| `requirements.txt` (flat) | Simple | No lock, no optional deps | Current (incomplete) |
| `pyproject.toml` + `requirements.txt` | Centralized | Two sources of truth | **Recommended** |
| `poetry.lock` | Full lock, hashes | Poetry-specific | Future migration |
| `pip-compile` | pip-compatible lock | Extra tool | Future migration |

### 2.3 CI/CD Best Practices (GitHub Actions)

```yaml
# Recommended: Two-stage testing
jobs:
  fast-tests:      # Every PR
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest --ignore=tests/slow/ -q

  slow-tests:      # Scheduled + main push
    if: github.event_name == 'schedule' || github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pytest tests/slow/ -q
```

**Key insights:**
- Cache pip packages (90%+ hit rate with stable requirements.txt)
- Separate fast/slow tests (OCR/PDF generation are slow)
- Use `actions/setup-python@v5` for proper caching integration
- Never log PII or artifact sensitive data

### 2.4 Python Packaging

**`src/` layout vs flat:**

| Layout | Best For | This Project |
|--------|----------|--------------|
| `src/` | Installable packages | `src/free_model_eval/`, `src/invoice_ingestion/` already use it |
| Flat `scripts/` | Standalone executables | A1 scripts should stay flat (PII isolation) |

**Recommended pyproject.toml structure:**
```toml
[project]
name = "prace-v-nemecku"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "Django>=5.2",
    "psycopg[binary]>=3.3",
    # ... all current deps
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
ocr = ["rapidocr>=3.9"]
a1 = ["pypdf", "pymupdf", "reportlab"]
portal = ["Django", "django-allauth"]
```

---

## 3. OpenRouter API Analysis

### 3.1 Free Tier Models Tested

| Model | Status | Error |
|-------|--------|-------|
| `minimax/minimax-01:free` | ❌ | 404 Not Found |
| `google/gemma-4-26b-a4b-it:free` | ❌ | 429 Rate Limited |
| `google/gemma-4-31b-it:free` | ❌ | 429 Rate Limited |
| `nvidia/nemotron-nano-12b-v2-vl:free` | ❌ | 404 Not Found |
| `google/gemini-2.0-flash-thinking:free` | ❌ | 400 Bad Request |
| `anthropic/claude-3.5-haiku:free` | ❌ | 404 Not Found |
| `mistralai/devstral-small:free` | ❌ | 404 Not Found |
| **`minimax/minimax-m3:free`** | ✅ | **Worked** |

### 3.2 Free Vision Models Available

Total free models on OpenRouter: **18**

None are vision-capable except potentially `minimax/minimax-m3:free` (worked for OCR).

---

## 4. Issues Found

### 4.1 Dependency Installation Gap

**Problem:** `requirements.txt` contains `rapidocr==3.9.2` but it was not installed in the venv.

**Root cause:** Unknown - possibly:
- `venv/bin/pip install -r requirements.txt` was never run
- Installation failed silently
- venv was created but deps installed differently

**Verification:**
```bash
venv/bin/pip list | grep rapidocr  # Empty - not installed
pip list | grep rapidocr            # Shows as installed (system pip?)
```

### 4.2 OCR Import Path Changed

**Problem:** `workflows/a1/README.md` references `from rapidocr_onnxruntime import RapidOCR` but actual import is `from rapidocr import RapidOCR`.

**Also:** Return type changed from tuple `(result, elapse)` to `RapidOCROutput` object.

### 4.3 Missing onnxruntime

**Problem:** rapidocr requires `onnxruntime` but it wasn't in requirements.txt or installed.

**Fix applied:** `pip install onnxruntime` → rapidocr now works.

---

## 5. Recommendations

### 5.1 Immediate Actions (High Priority)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | **Fix requirements.txt** - add `onnxruntime` | Low | Enables local OCR |
| 2 | **Verify venv installation** - ensure all deps from requirements.txt are installed | Low | Reproducibility |
| 3 | **Update OCR import paths** in `workflows/a1/README.md` and `ocr/_ocr_worker.py` | Low | Documentation accuracy |
| 4 | **Create lock file** (`pip freeze > requirements-lock.txt`) | Low | Reproducibility |

### 5.2 Medium-Term Actions

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 5 | **Create `pyproject.toml`** with optional dependency groups | Medium | Modern packaging |
| 6 | **Add GitHub Actions CI** (fast tests on PR, slow tests scheduled) | Medium | Automation |
| 7 | **Create `.pre-commit-config.yaml`** | Medium | Code quality |
| 8 | **Add pip caching** to CI | Low | Faster builds |

### 5.3 Future Actions (Lower Priority)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 9 | Migrate to Poetry with lock file | High | Full reproducibility |
| 10 | Create `src/` package for reusable code | Medium | Better testing |
| 11 | Add dependency vulnerability scanning (pip-audit) | Low | Security |

---

## 6. Proposed Plan

### Plan: Environment & CI Stabilization

**Objective:** Ensure reproducible Python environment and basic CI automation.

**Pre-requisites:** None (can start immediately)

**Exit criteria:**
- [ ] All packages in requirements.txt install correctly
- [ ] Lock file generated and committed
- [ ] GitHub Actions CI runs fast tests on PR
- [ ] pre-commit hooks functional

### Tasks:

**E-01: Fix requirements.txt**
- Add `onnxruntime>=1.29` (required by rapidocr)
- Consider adding `pytesseract` if tesseract is installed system-wide
- Add version bounds where missing

**E-02: Verify full installation**
```bash
venv/bin/pip install -r requirements.txt
# Should complete without errors
```

**E-03: Generate lock file**
```bash
venv/bin/pip freeze > requirements-lock.txt
git add requirements-lock.txt
git commit -m "chore: add locked dependency versions"
```

**E-04: Update OCR documentation**
- Fix import path: `from rapidocr import RapidOCR`
- Update return value handling for new API
- Document that `minimax/minimax-m3:free` works for OCR

**E-05: Create GitHub Actions workflow** (`.github/workflows/ci.yml`)
- Run fast tests on every PR
- Run slow tests (OCR/PDF) on schedule + main push
- Cache pip packages
- No PII in logs/artifacts

**E-06: Create pre-commit config** (`.pre-commit-config.yaml`)
- trailing-whitespace, end-of-file-fixer, check-yaml
- ruff for Python linting
- gitleaks for secret detection
- Skip PII directories automatically

---

## 7. Cost & Risk Analysis

### 7.1 Free Tier Constraints

| Resource | Free Limit | Current Usage | Risk |
|----------|------------|---------------|------|
| OpenRouter API | Rate limited | OCR via minimax-m3 | Low (works) |
| GitHub Actions | 2000 min/month | None yet | Low |
| GitLab CI | Proposed (DEC-016) | Inactive | N/A |

### 7.2 Security Considerations

| Concern | Mitigation |
|---------|------------|
| PII in CI logs | Never log employee data, use hash comparisons only |
| Secrets in CI | GitHub secrets only, never hardcode |
| Dependency vulnerabilities | pip-audit in scheduled CI run |
| Pre-commit secrets scan | gitleaks hook |

---

## 8. Alternatives Considered

### 8.1 Poetry vs pip + lock

| Aspect | pip + lock | Poetry |
|--------|------------|--------|
| Compatibility | 100% (pip-compatible) | New syntax |
| Lock file | `pip freeze` | `poetry.lock` |
| Learning curve | None | Medium |
| CI integration | Native | `snok/install-poetry` |

**Decision:** Use pip + lock for now (simpler), migrate to Poetry later.

### 8.2 Docker vs Native venv in CI

| Aspect | Native venv | Docker |
|--------|-------------|--------|
| Speed | Faster (no container) | Slower build |
| Cache | Good (pip cache) | Good (layer cache) |
| Complexity | Low | Medium |

**Decision:** Native venv (simpler, sufficient for this project).

---

## 9. Files to Create/Modify

### Create:
```
.github/
  workflows/
    ci.yml              # Main CI pipeline
.pre-commit-config.yaml # pre-commit hooks
requirements-lock.txt   # Locked versions
```

### Modify:
```
requirements.txt        # Add onnxruntime
workflows/a1/README.md  # Fix OCR import docs
```

### No Change Needed:
```
venv/                   # Already exists
scripts/                # Work as-is
portal/                 # Works as-is
```

---

## 10. Summary

| Category | Current | Target |
|----------|---------|--------|
| **Dependencies** | Incomplete (rapidocr missing) | All installed + locked |
| **venv** | Works | Works |
| **Local OCR** | Broken (now fixed) | Working |
| **CI/CD** | None | Basic GitHub Actions |
| **Pre-commit** | Custom script | Standard pre-commit |
| **Packaging** | requirements.txt only | pyproject.toml + lock |

**Estimated effort:** 2-4 hours for immediate actions, 1-2 days for full CI setup.
