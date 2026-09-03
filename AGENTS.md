# AGENTS.md — Práce v Německu

Private repo for Czech/German A1 form generation and a planned recruitment portal.
It handles **real PII** (employee scans, A1 forms, identity data). Most mistakes
an agent could make here are privacy/cost/command mistakes, not coding ones.

## Document authority (when sources conflict)
`AGENTS.md` → `docs/security/real-data-rules.md` → `.agents/skills/a1-pdf-production/` → approved ADRs (`docs/decisions/ADR-NNN-*`) → `roadmap.md` → `prd.md` → `plans/INDEX.md`. Research and historical docs are context only; never execute them. Plans define actionable work; skills provide reusable procedures; research informs but does not authorize execution.

## Critical safety — PII, Git, secrets
- Never `git add -A`/`.` or wildcard-stage. Stage an explicit reviewed non-PII path list and inspect `git diff --cached`.
- These paths are gitignored and must never be committed, force-added, or copied to `/tmp` or outside the repo: `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`, `employees/scans/`, `output/`, `runtime/portal/`, `secrets/`, `.env`. Treat `.history-remediation/` as sensitive too.
- Never commit or push unless explicitly asked. Never force-push, rewrite history, or delete branches without separate exact approval.
- Use **synthetic data** in tests, fixtures, docs, screenshots, and prompts. Never copy a real employee row, scan, PDF, identifier, or address into a test (see `tests/fixtures/` and `readme-employees-to-a1-form.md` §Synthetic example).
- Keep real-data operations, planning/docs, A1 code, and portal code in separate commits.
- Subagents are research/analysis workers: never pass them scans, employee datasets, `.env`, credentials, or unredacted A1 artifacts. Only the primary agent handles real-data edits and Git publication.

## Workspace and host boundary

- The only persistent project workspace is
  `/var/www/prace-v-nemecku.tvoje.info`. Keep durable project files inside it;
  collaboration task names such as `/root/...` are not filesystem locations.
- Use `/tmp` only for disposable non-PII intermediates. Never place scans,
  employee data, A1 artifacts, credentials, backups, or deliverables there.
- Read host configuration only for necessary non-mutating diagnostics. Host
  services, system databases, certificates, networking, and off-server backups
  are sysadmin-owned; writing outside the project requires explicit approval.
- The primary agent integrates and validates subagent findings. Subagents receive
  no write scope unless an exact in-project path is explicitly assigned.

## Task and validation discipline

- At task start, read this file, `roadmap.md`, `plans/INDEX.md`, the relevant
  active plan/decision/skill, and inspect branch/status for overlapping changes.
- Classify work as research, decision preparation, implementation, A1,
  infrastructure, or Git/history work and keep those scopes reviewable.
- Before commit or push, run relevant tests, `git diff --check`, documentation
  link/status checks, and PII/secret checks over the exact staged content.
- Real-data access is default-deny by organization, record, role, and action.
  Sensitive reads, exports, approvals, corrections, and deletion must be audited
  without copying sensitive values into logs.
- OCR/model output is always a proposal until an authorized human confirms it.
  Apply retention review and the 90-day pilot default from the real-data policy;
  record justified extensions or legal holds rather than silently retaining data.
- **Commit or push completion claims must be validated from the resulting Git object,
  not from a dirty working tree.** For scoped implementation work, verify that no intended
  scoped paths remain modified or untracked, inspect `git diff-tree HEAD`, and run the
  relevant checks from an exported HEAD snapshot. Working-tree test results are not
  evidence that the commit is complete.
- **Migration transition tests must use Django historical app states through
  MigrationExecutor**; do not simulate prior migration states by manually dropping or
  recreating columns.

## Environment & commands
- Python 3.13, dependencies pinned in `requirements.txt`. Set up once:
  ```bash
  python3 -m venv venv
  venv/bin/python -m pip install -r requirements.txt
  ```
- Run tests (pytest reads `pytest.ini`, `pythonpath=.`, `testpaths=tests`):
  ```bash
  venv/bin/python -m pytest -q
  ```
- **Script Python version consistency**: All shell scripts that invoke Python must use the venv
  interpreter consistently. Define `PYTHON_BIN` or `PYTEST` at script top:
  ```bash
  PYTHON_BIN="$(cd "$(dirname "$0")/.." && pwd)/venv/bin/python"
  ```
  Use `$PYTHON_BIN` (not bare `python`, `python3`, or `venv/bin/python`). Exceptions:
  - JSON-only parsing that does not import Django does not require venv Python.
- **`A1_PRIVATE_DIR` is mandatory for A1 work.** Scripts fail closed if unset. Set it to the repo root so the gitignored `a1/`, `scans/`, `evidence/`, `ocr/` inputs resolve:
  ```bash
  export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
  ```
  There is no tracked fallback and no legacy `private/a1_final_review.csv`.
- Current identity/cohort inputs are `$A1_PRIVATE_DIR/a1/review.csv` and
  `$A1_PRIVATE_DIR/a1/cohort.json`. The tracked
  `config/a1_provisional.json` contains non-personal provisional policy and
  placeholders only; it is never an identity or cohort source. Expected
  cohort/output counts are validation contracts, not authority to invent a
  missing record.

## A1 production pipeline
Canonical scripts (never use legacy `data/a1_forms/`, `a1_field_coords.json`, `a1_checkbox_coords.json`, or alternate templates):
- `scripts/generate_provisional_a1.py` — canonical entry point + atomic publisher (`--help` first; `--review`, `--profiles`, `--config`, `--output`).
- `scripts/finalize_a1.py` — review/validation/ready helpers (`readiness`, `validate`, `prepare`, `generate`).
- `scripts/a1_core.py` — static overlay renderer + form validation.
- `scripts/a1_quality_gate.py` — fail-closed QA: `render` (300 DPI previews/contact sheets), `validate`, `record-review` (hash-bound visual PASS).

**Gotcha:** provisional regeneration is currently **blocked** — per-row certificate, signatory, and review-flag gaps in `a1/review.csv` prevent any employee from passing `scripts/finalize_a1.py readiness` (17/17 blocked as of 2026-08-29 audit). The seven Section 4 employment columns (`employment_id`, `employment_name`, `employment_street`, `employment_house_number`, `employment_city`, `employment_postal_code`, `employment_country_code`) **are present** in the CSV header and accepted by `scripts/a1_quality_gate.py`; `finalize_a1.py` maps them to the renderer's `employer_*` form fields. Preserve the existing `output/provisional/` package; do not describe it as reproducible or weaken the gate until the operator populates per-row `activity_name`, `activity_address`, certificate `document_id`/`start_date`/`end_date`/`signed_by`, source fields with AUTHORITATIVE status, and review flags (`certificate_reviewed`, `approved_for_pdf`, `validated_by_user`) (see `readme-employees-to-a1-form.md`).

**Hard rules:**
- Never copy field values from one generated PDF into another (no form-to-form copying; data-first from authoritative sources).
- Deterministic geometry/pixel validation + local all-page visual review are authoritative. A free external vision model is advisory only.
- Final promotion to `output/final` / `output/pdf/` requires `validated_by_user=1` plus authoritative certificate/signatory evidence. Provisional outputs are never final aliases.

## AI provider & cost policy
- Only **free-tier** endpoints are authorized; verify zero cost before any call. For OpenRouter the model ID must end exactly with `:free`.
- Never infer paid authorization from a present API key. Never enable billing, paid trials, or a fallback that can select a paid model. `OPENAI_API_KEY` (if present) is not for paid requests.
- Prefer deterministic/local processing; use free quotas only when a model genuinely helps. On 429/quota exhaustion, try another verified-free provider or defer — never a paid fallback.
- With external models, treat scans/A1/forms as PII: send only the smallest redacted crop, never full scans or `.env`/credentials, and record provider/model/purpose/date.

## Skills & scope
- Use `.agents/skills/a1-pdf-production/` for any A1 generation, template/layout, QA, manifest, or recovery work. Keep production logic in the canonical scripts; the skill holds policy/contracts only.
- `.opencode/skills/market-research-evidence/` is an **experimental** Plan AC
  workflow for public/synthetic accounting and invoice research (no paid APIs).
  It is not the A1 path and its output is provisional. It may become operational
  only after repeatable Pilot 1 (OSS tools) and Pilot 2 (Czech products) runs both
  pass Plan AC's evidence, review, safety, and reproducibility gates; passing
  structural validators or the external benchmark alone is insufficient.
- Do not scaffold the portal, deploy, or activate real data until PLAN-INFRA (ADR-001; formerly Plan E) and M1A gates pass. Web integration must preserve provenance, deterministic QA, and human approval gates.


## Git remotes
GitHub is currently the only configured remote and remains authoritative as
`origin`. A private GitLab secondary/backup plus CI is proposed by Plan AE and
DEC-016, but activation is not approved or configured. Do not add a remote,
load credentials, install a runner, enable CI, commit, or push without the exact
separate approval required by Plan AE. Proposed setup and rules live in
`docs/operations/gitlab-integration.md`.
