# Master Plan — Automation, Testing, Deployment & Agent Workflows
**Date:** 2026-09-17  
**Scope:** Complete the s62 delivery readiness work with sustainable automation, proper testing, and deployment infrastructure  
**Status:** Research complete — awaiting implementation approval

---

## 1. Current State Summary

### What We Have

| Layer | What Exists | State | Gaps |
|---|---|---|---|
| **Change-package governance** | `change-packages.yml` with 19 packages, path-level checks, secret scanning | Working | No Ansible paths registered; no deployment playbook paths |
| **Delivery lifecycle** | `rehearse_synthetic_site.sh` (7-phase lifecycle), `rehearse_verify_persistence.py`, `disposable_pg_guard.py` | Working | No parallel execution; no tiered CI routing |
| **Readiness probes** | `smoke_probe.py`, `validate_delivery_readiness.py`, `check_readiness.sh`, `fix_nginx_static_alias.sh` | Working | No structured logging; no correlation IDs; no test for `fix_nginx_static_alias.sh` |
| **Regression guards** | `test_no_networkidle_regression.py`, `test_release_export_sensitive_paths.py` | Working | No guards for systemd/nginx contract; no deployment contract tests |
| **CI/CD** | `.github/workflows/ci.yml` (fast + slow tests), `.gitlab-ci.yml` (inactive) | Partial | No PG service job; no browser tests in PR CI; no xdist; no coverage |
| **Agent skills** | 3 skills in `.agents/skills/` (a1-pdf-production, postgres-ops, synthetic-portal-delivery) | Working | No skill for deployment/readiness; no skill for release reproducer |
| **Documentation** | 30+ ops docs, triage reports, verification reports, git-delivery.md | Current | No consolidated deployment runbook; no Ansible playbook docs |
| **Tests** | 74 test files, ~1200+ test functions | Working | No parallel execution; no shared fixtures; no tier markers; no PG in CI |

### What We Don't Have

| Missing | Impact | Priority |
|---|---|---|
| Ansible playbooks/roles | Operator must manually run shell commands for deployment | **High** |
| Parallel test execution | CI wall-clock 5-10 min; blocks fast feedback | **High** |
| Test tier markers | Slow integration tests block PR feedback | **High** |
| GitHub Actions PG service job | PG integration paths only tested manually | **High** |
| Shared pytest fixtures | 200+ lines of duplicated setup across 20+ files | **High** |
| Task runner (`justfile`/`tox`) | Developers must remember correct `DJANGO_SETTINGS_MODULE` per test type | **High** |
| Deployment contract tests | Systemd/nginx/static collection regressions caught only in slow lifecycle test | **Medium** |
| Structured logging | Scripts use `print()` to stderr; no JSON, no correlation IDs | **Medium** |
| Browser tests in PR CI | Browser regressions caught only on schedule | **Medium** |
| Skill for deployment/readiness | No authoritative agent guidance for G-1..G-4 fixes | **Medium** |

---

## 2. Solution Comparison Matrix

### 2.1 Deployment Automation: Ansible vs Alternatives

| Criterion | Ansible | Docker Compose | SaltStack | Manual Scripts |
|---|---|---|---|---|
| **Fit for Django+PG+nginx+systemd** | ✅ Excellent | ⚠️ Overkill | ⚠️ Overkill | ✅ Current state |
| **Idempotent by design** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Learning curve** | Low-medium | Low | High | Low |
| **Secrets management** | ✅ Ansible Vault | ⚠️ .env files | ✅ Pillar | ❌ Ad-hoc |
| **Multi-host support** | ✅ Native | ⚠️ Single host | ✅ Native | ❌ Manual |
| **Testing infrastructure** | ✅ Molecule, ansible-lint | ⚠️ Docker test | ⚠️ Salt test | ❌ None |
| **Community examples for Django** | ✅ Many | ⚠️ Few | ❌ Few | ✅ Our scripts |
| **Agent/CI integration** | ✅ Good | ✅ Good | ⚠️ Complex | ⚠️ Ad-hoc |
| **Single-host overhead** | ✅ Minimal | ⚠️ Docker daemon | ❌ Heavy | ✅ None |
| **Current repo investment** | ❌ None | ❌ None | ❌ None | ✅ ~80 scripts |

**Recommendation:** **Ansible** for this project. Rationale:
- The stack is single-host Django + PostgreSQL + nginx + systemd — Ansible's sweet spot
- Existing scripts (`rehearse_synthetic_site.sh`, `fix_nginx_static_alias.sh`) already encode the operational knowledge; Ansible roles would formalize and idempotize them
- Ansible Vault solves the secrets management gap
- Molecule + ansible-lint provide testing infrastructure
- No Docker daemon required on the target host
- Agent skills can invoke `ansible-playbook` with the same privilege model as current `sudo` scripts

### 2.2 Test Parallelization: pytest-xdist vs Alternatives

| Criterion | pytest-xdist | pytest-parallel | unittest-parallel | Sequential |
|---|---|---|---|---|
| **Django compatibility** | ✅ Good (`--dist=loadfile`) | ⚠️ Limited | ❌ Poor | ✅ Perfect |
| **Playwright compatibility** | ❌ Not thread-safe | ❌ Not thread-safe | ❌ Not thread-safe | ✅ Safe |
| **Setup complexity** | Low | Medium | High | None |
| **CI integration** | ✅ Easy | ⚠️ Complex | ⚠️ Complex | ✅ Current |
| **DB test isolation** | ✅ `--dist=loadscope` | ❌ Risk | ❌ Risk | ✅ Safe |
| **Speed improvement** | 60-80% | 60-80% | 60-80% | 0% |

**Recommendation:** **pytest-xdist** with `--dist=loadfile` for unit tests, dedicated jobs for browser/lifecycle tests.

### 2.3 Task Runner: just vs tox vs Make

| Criterion | just | tox | Make |
|---|---|---|---|
| **Syntax** | ✅ Modern, simple | ⚠️ INI-based | ⚠️ Shell-based |
| **Cross-platform** | ✅ Good | ✅ Good | ✅ Good |
| **Python env management** | ⚠️ Manual | ✅ Built-in | ⚠️ Manual |
| **Visibility** | ✅ `just --list` | ⚠️ `tox -l` | ✅ `make help` |
| **Current repo precedent** | ❌ None | ❌ None | ❌ None |

**Recommendation:** **`just`** — modern, readable, no magic. Install via `pip install just` or binary.

### 2.4 Structured Logging: Python logging vs print vs JSON

| Criterion | `logging` module | `print()` | JSON structured |
|---|---|---|---|
| **Machine-readable** | ⚠️ With formatter | ❌ No | ✅ Yes |
| **Log levels** | ✅ Yes | ❌ No | ⚠️ Manual |
| **CI integration** | ⚠️ Needs parsing | ✅ Direct | ✅ Direct |
| **Correlation IDs** | ✅ With filters | ❌ No | ✅ Native |
| **Migration effort** | Low | None | Medium |

**Recommendation:** **Python `logging` with a JSON formatter** (stdlib + `python-json-logger` or custom). Migration from `print()` is mechanical: replace `print(..., file=sys.stderr)` with `logger.error(...)`.

---

## 3. File-to-Functionality Mapping

### 3.1 Current Mapping (what maps to what)

```
FUNCTIONALITY                    PRIMARY FILE(S)                    FALLBACK/DUP
─────────────────────────────────────────────────────────────────────────────────
A1 PDF generation                generate_provisional_a1.py         generate_a1_form.py
A1 core rendering                a1_core.py                         a1_core.py.backup
A1 QA gate                       a1_quality_gate.py                 (none)
A1 audit trail                   a1_audit.py                        (none)
A1 path safety                   a1_paths.py                        (none)

Readiness probes                 validate_delivery_readiness.py     check_readiness.sh (wrapper)
Smoke probe                      smoke_probe.py                     (none)
Nginx static fix                 fix_nginx_static_alias.sh          (none)
Unit status check                validate_delivery_readiness.py     (none)
Browser wait guard               test_no_networkidle_regression.py  (none)

Delivery lifecycle               rehearse_synthetic_site.sh         rehearse_dev_local.sh (wrapper)
Release reproducer               run_release_reproducer.py          release_reproducer.sh (wrapper)
Persistence verification         rehearse_verify_persistence.py    (none)

Change-package gate              validate_change_packages.py        select_*_checks.py (selectors)
Planning validation              validate_planning.py               validate_approvals.py
Release export boundary          test_release_export_sensitive_paths.py (none)

OCR worker lifecycle             run_ocr_worker_lifecycle.py       process_ocr.py (management)
Document intake                  document_intake.py                 (none)
Inbox processing                 inbox.py                           a1_process_inbox.py (CLI)

Runtime safety                   runtime_safety.py                  (none)
Settings (supervised)            settings_supervised_synthetic.py  settings_browser_tests.py
Settings (browser)               settings_browser_tests.py         (none)
Settings (document tests)        settings_document_tests.py        (none)

PG test guard                    test_pg_contract.py               disposable_pg_guard.py
PG ops skill                     .agents/skills/postgres-ops/SKILL.md (none)

A1 production skill              .agents/skills/a1-pdf-production/  (none)
Delivery skill                   .agents/skills/synthetic-portal-delivery/ (none)

Git delivery record              docs/operations/git-delivery.md    (none)
Triage/playbook                  docs/operations/s62-*-2026-09-16   (none)
Operator triage                  docs/operations/s62-operator-...   (none)
```

### 3.2 Duplication Analysis

| Duplicate | Primary | Duplicate | Action |
|---|---|---|---|
| `a1_core.py` vs `a1_core.py.backup` | `a1_core.py` | `a1_core.py.backup` | **Remove** `.backup` (in `legacy_cleanup` package) |
| `rehearse_dev_local.sh` vs `rehearse_synthetic_site.sh` | `rehearse_synthetic_site.sh` | `rehearse_dev_local.sh` | **Keep both** — wrapper is intentional |
| `release_reproducer.sh` vs `run_release_reproducer.py` | `run_release_reproducer.py` | `release_reproducer.sh` | **Keep both** — wrapper is intentional |
| `check_readiness.sh` vs `validate_delivery_readiness.py` | `validate_delivery_readiness.py` | `check_readiness.sh` | **Keep both** — wrapper is intentional |
| `generate_a1_placeholder.py` vs `generate_a1_incremental.py` | Both are independent | Both serve different use cases | **Keep both** |
| `axe_check.sh` vs `smoke_synthetic_review_ui.mjs` | Both are independent | Different tech stacks | **Keep both** |
| `cli-docs-update/` historical artifacts | Historical | Quarantined | **Archive or remove** per `legacy_cleanup` |
| `tests/test_a1_core.py` vs `tests/test_comprehensive.py` | `test_a1_core.py` | `test_comprehensive.py` | **Keep both** — different scopes |

### 3.3 What to Archive vs Remove

| Item | Action | Reason |
|---|---|---|
| `scripts/a1_core.py.backup` | **Remove** | Listed in `legacy_cleanup` package; backup of active file |
| `portal/settings.py.bak` | **Remove** | Listed in `legacy_cleanup` package |
| `config/a1_field_coords.json` | **Remove** | Legacy coordinate system; replaced by `config/a1_layout.json` |
| `config/a1_checkbox_coords.json` | **Remove** | Legacy coordinate system |
| `config/a1_field_map.json` | **Remove** | Legacy field map |
| `cli-docs-update/2026-08-14-*` | **Archive** | Historical investigation artifacts; in `quarantined_unrelated` |
| `.archive/plans/2026-08-12-plan-k-server62-readiness.md` | **Keep** | Historical archive; `.archive/` is for non-sensitive history |
| `tests/m2/test_release1a_vertical.py` | **Quarantine** | Known flaky; excluded from CI; add `@pytest.mark.flaky` and track |

---

## 4. Recommended Implementation Plan

### Phase 1: Foundation (Week 1) — "Make it work reliably"

| Task | Effort | Impact | Owner |
|---|---|---|---|
| Add `pytest-xdist` + `--dist=loadfile` to `pytest.ini` | 1h | 60-80% CI time reduction | Engineering |
| Add `@pytest.mark.unit/smoke/integration/serial` to all tests | 3h | Enables tiered CI routing | Engineering |
| Add `tests/fixtures/conftest.py` with shared synthetic fixtures | 2h | Removes 200+ lines duplication | Engineering |
| Add `justfile` with canonical test commands | 2h | Eliminates env confusion | Engineering |
| Fix `tests/m2/test_release1a_vertical.py` flaky or quarantine | 2h | CI stability | Engineering |

**Verification:** CI wall-clock drops from ~10 min to ~3 min; PR feedback < 5 min.

### Phase 2: Testing Gaps (Week 2) — "Make it testable"

| Task | Effort | Impact | Owner |
|---|---|---|---|
| Create `tests/test_deployment_contract.py` (systemd/nginx/static) | 2h | Catches infra contract breaks | Engineering |
| Create `tests/test_static_collection.py` (fast collectstatic test) | 1h | Fast regression signal | Engineering |
| Add GitHub Actions PostgreSQL service job | 2h | PG integration on every PR | Engineering |
| Add Playwright tests to PR CI with sharding | 3h | Browser regressions caught early | Engineering |
| Add coverage reporting + thresholds to CI | 1h | Prevents coverage regression | Engineering |

**Verification:** All gaps from §6.2 of testing research are closed.

### Phase 3: Deployment Automation (Week 3-4) — "Make it repeatable"

| Task | Effort | Impact | Owner |
|---|---|---|---|
| Create `ansible/` directory structure | 1h | Foundation for deployment automation | Engineering |
| Write `roles/python_venv` (idempotent venv + requirements) | 2h | Reproducible Python env | Engineering |
| Write `roles/postgresql` (DB + user + extensions) | 3h | PG managed by code, not manual | Engineering |
| Write `roles/django_app` (collectstatic, migrate) | 2h | Django commands idempotent | Engineering |
| Write `roles/gunicorn` (systemd unit + env file) | 2h | G-2/G-4 fixes codified | Engineering |
| Write `roles/nginx` (site config + static alias) | 2h | G-3 fix codified | Engineering |
| Write `playbooks/site.yml` (orchestration) | 1h | Single-command deploy | Engineering |
| Add `group_vars/` with vars+vault pattern | 2h | Secrets management | Engineering |
| Add Molecule tests for each role | 4h | Deployment tested in isolation | Engineering |
| Write `docs/operations/ansible-deployment-runbook.md` | 2h | Operator guide | Engineering |

**Verification:** `ansible-playbook playbooks/site.yml --check` passes; Molecule tests green; dry-run produces no changes on already-configured host.

### Phase 4: Agent Skills & Observability (Week 5) — "Make it observable"

| Task | Effort | Impact | Owner |
|---|---|---|---|
| Create `.agents/skills/deployment/SKILL.md` | 2h | Agent guidance for deployment | Engineering |
| Create `.agents/skills/readiness/SKILL.md` | 2h | Agent guidance for G-1..G-4 | Engineering |
| Add structured logging to `validate_delivery_readiness.py` | 2h | Machine-readable output | Engineering |
| Add correlation ID propagation to scripts | 2h | Log correlation across services | Engineering |
| Add `test_fixture_schema_validation.py` | 2h | Catches corrupt fixtures | Engineering |

**Verification:** Agent can read skill docs and execute deployment/readiness workflows correctly; logs are parseable by `jq`.

---

## 5. Testing Strategy

### 5.1 Test Tiers

| Tier | Definition | Examples | When to Run | CI Job |
|---|---|---|---|---|
| **Unit** | Isolated, no server, no subprocess, <5s each | `test_a1_core.py`, `test_readiness_checks.py`, `test_disposable_pg_guard.py`, architecture proofs | Every commit | `unit-tests` (xdist) |
| **Smoke** | Live server, HTTP requests, <30s each | `test_wsgi_asgi.py`, `test_playwright_smoke.py`, `test_check_readiness.py` | Every commit | `smoke-tests` |
| **Integration** | Real services (gunicorn, PG, browser), ~60s each | `test_rehearse_synthetic_site_lifecycle.py`, `test_browser_journey.py`, `test_rehearse_workflow.py` | Every PR + schedule | `integration-tests` |
| **A1 Quality Gate** | Full render/validate cycle, ~30 min | `test_a1_quality_gate.py`, `scripts/a1_quality_gate.py` | Schedule + main only | `a1-quality-gate` (nightly) |

### 5.2 CI Job Matrix

```yaml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - run: just test-unit  # xdist, --dist=loadfile

  smoke-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - run: just test-smoke

  integration-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, smoke-tests]
    steps:
      - run: just test-integration

  browser-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - run: just test-browser

  pg-tests:
    runs-on: ubuntu-latest
    services:
      - image: postgres:18-alpine
        options: --health-cmd pg_isready
    needs: unit-tests
    steps:
      - run: just test-pg

  a1-quality-gate:
    runs-on: ubuntu-latest
    needs: integration-tests
    schedule:
      - cron: '0 2 * * *'  # nightly
    steps:
      - run: just test-a1-gate
```

### 5.3 Parallel Execution Plan

| Test Group | Parallelization | Expected Speedup |
|---|---|---|
| Unit tests (60+ files) | `pytest-xdist -n auto --dist=loadfile` | 5-10x |
| Smoke tests (10 files) | `pytest-xdist -n 4` | 2-3x |
| Browser tests (1 file) | Playwright sharding `--shard=1/2` | 1.5-2x |
| Lifecycle tests (1 file) | **Serial only** (spawns real gunicorn) | 1x |
| A1 quality gate (1 file) | **Serial only** (render/validate) | 1x |

---

## 6. Logging and Observability Plan

### 6.1 Current State

All scripts use `print(..., file=sys.stderr)` for errors and `print(...)` for status. No structured logging, no log levels, no correlation IDs.

### 6.2 Target State

```python
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler(sys.stderr)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)

# Usage:
logger = logging.getLogger("delivery.readiness")
logger.info("check_started", extra={"check": "g3_static_files"})
logger.error("check_failed", extra={"check": "g3_static_files", "error": "permission_denied"})
```

Output:
```json
{"asctime":"2026-09-17T10:00:00Z","levelname":"ERROR","name":"delivery.readiness","check":"g3_static_files","error":"permission_denied","correlation_id":"abc123"}
```

### 6.3 Migration Path

1. Add `python-json-logger` to `requirements.txt` (or implement minimal JSON formatter)
2. Create `src/logging_config.py` with `setup_logging()` helper
3. Migrate one script at a time (start with `validate_delivery_readiness.py`)
4. Add `correlation_id` propagation via environment variable

---

## 7. Agent Skills Roadmap

### 7.1 Current Skills

| Skill | Purpose | Status |
|---|---|---|
| `a1-pdf-production` | A1 generation, recovery, visual QA | Active |
| `postgres-ops` | PG connection, disposable target, migrations | Active |
| `synthetic-portal-delivery` | Delivery-1 rehearsal, provisioning, OCR | Active |

### 7.2 Proposed New Skills

| Skill | Purpose | Content |
|---|---|---|
| `deployment` | Ansible-based deployment, systemd, nginx, gunicorn | Playbook invocation, vault handling, rollback |
| `readiness` | G-1..G-4 diagnostics, fix execution | `check_readiness.sh`, `fix_nginx_static_alias.sh`, `check_git_content.py` |
| `release-management` | Release reproducer, persistence verification, export boundary | `run_release_reproducer.py`, `rehearse_verify_persistence.py`, `test_release_export_sensitive_paths.py` |

### 7.3 Skill Structure (canonical)

```
.agents/skills/<skill-name>/
  SKILL.md              # Authoritative instructions, references, constraints
  references/           # Supporting docs, schemas, contracts
    <topic>.md
    <topic>.schema.json
  scripts/              # Optional: skill-specific helpers
    <helper>.py
```

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Ansible adds operational complexity | Medium | Medium | Start with one role (gunicorn), prove value, expand |
| pytest-xdist introduces flaky tests | Medium | High | Use `--dist=loadfile`; mark serial tests; run subset first |
| Parallel tests interfere via DB | Medium | High | Use `--dist=loadscope` per Django `TestCase` class |
| Agent skills become stale | High | Medium | Tie skill validation to CI (validate skill references still exist) |
| Deployment automation duplicates scripts | Medium | Medium | Map every script to a role task; deprecate script after role proves equivalent |
| Structured logging migration incomplete | Low | Low | Incremental: one script per session |

---

## 9. Next Actions (Ordered)

1. **Approve this plan** — confirm priorities and resource allocation
2. **Phase 1 kickoff** — add xdist, justfile, test markers, shared fixtures
3. **Run baseline CI** — capture current wall-clock, failure rate, flaky tests
4. **Phase 2 kickoff** — deployment contract tests, PG CI job, browser CI
5. **Phase 3 kickoff** — Ansible roles (start with `gunicorn` + `nginx`)
6. **Phase 4 kickoff** — agent skills + structured logging
7. **Archive/remove legacy files** per §3.3

---

## 10. Authoritative Sources

| Topic | Source | URL |
|---|---|---|
| Ansible layout | Ansible docs | docs.ansible.com/projects/ansible/latest/tips_tricks/sample_setup.html |
| Ansible best practices | Ansible user guide | docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html |
| Ansible Vault | Ansible vault guide | docs.ansible.com/projects/ansible/latest/vault_guide/ |
| Molecule testing | Molecule GitHub | github.com/ansible/molecule |
| pytest-xdist | pytest-xdist docs | pytest-xdist.readthedocs.io |
| Django test isolation | Django docs | docs.djangoproject.com/en/stable/topics/testing/overview.html |
| Playwright sharding | Playwright docs | playwright.dev/docs/test-parallel |
| Linux path resolution | `path_resolution(7)` | man7.org/linux/man-pages/man7/path_resolution.7.html |
| systemd.exec | systemd docs | man7.org/linux/man-pages/man5/systemd.exec.5.html |
| nginx user/alias | nginx docs | nginx.org/en/docs/ngx_core_module.html#user |
| AGENTS.md | Project policy | AGENTS.md — "Private storage defaults" section |
