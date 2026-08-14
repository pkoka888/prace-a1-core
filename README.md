# Práce v Německu

Private research, planning, and tooling repository for a planned Czech/German
recruitment and workforce-operations platform. The first intended product
increment is Jan's protected document → worker → assignment → A1 workflow.

There is **no implemented production portal yet**. `public-site/index.html` is a
placeholder page. Django, PostgreSQL, authentication, background jobs, and the
portal UI remain architecture or implementation plans; do not describe them as
running systems.

## Current capabilities

- Fail-closed local A1 generation and validation tooling. Provisional
  regeneration is currently blocked by seven missing Section 4 columns in the
  protected operator CSV.
- Synthetic/public research tooling for accounting and invoice automation.
  Plan AC live capture and skill activation remain blocked by Integrity 1.3 and
  its replay/review gates.
- Framework-independent in-memory invoice-ingestion contracts tested only with
  synthetic data. Implementation and acceptance require DEC-015 specialist
  approval.
- Planning catalog, decision register, validators, and prototype planning views.

## Setup and tests

Python 3.13 is the documented environment. Dependencies are pinned in
`requirements.txt`.

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m pytest -q
venv/bin/python scripts/validate_planning.py
venv/bin/python scripts/validate_change_packages.py
```

All tests and examples must use synthetic data. Research validators may have
documented non-zero exits for provisional or quarantined evidence; a structural
pass does not convert research into operational authority.

## Protected data

This repository handles real employee identity and A1 material outside tracked
source. Never commit, force-add, copy into tests, or expose content from:

- `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`, `employees/scans/`;
- `output/`, `runtime/portal/`, `private/`, `reports/`, `secrets/`, `.env`;
- `.history-remediation/`.

Set `A1_PRIVATE_DIR` only for explicitly authorized A1 operations:

```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
```

Do not run A1 generation merely to test the repository. See
`readme-employees-to-a1-form.md` and `.agents/skills/a1-pdf-production/` for the
fail-closed production contract.

## Project authority and navigation

When documents conflict, follow the authority order in `AGENTS.md`. Start with:

- `AGENTS.md` — safety, authority, commands, and operational constraints;
- `roadmap.md` — sole authoritative milestone sequence;
- `plans/INDEX.md` — plan statuses, lanes, blockers, and acceptance methods;
- `docs/decisions/decision-register.md` — decision state;
- `plans/audits/2026-08-15-repository-truth-audit.md` — current truth audit;
- `change-packages.yml` — exact worktree package rules and quarantines.

Plans authorize bounded work; skills define reusable procedures; research is
evidence only and never authorizes implementation, real-data use, or publication.

## Git and publication

GitHub `origin` is the current authoritative remote. GitLab backup/CI is a
proposed default under DEC-016, not an activated or implicitly approved workflow.
Never use broad staging (`git add .` or `git add -A`). Review and stage exact paths
only. Committing, pushing, remote configuration, CI activation, history rewriting,
and deletion each require explicit authorization.

The accepted historical checkpoint is `c01aa2b`. Current HEAD contains later
committed work; the change-package validator records that committed delta
separately from the uncommitted worktree.
