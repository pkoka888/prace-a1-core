# Workflows Directory

This directory contains all production and experimental workflows, separated by function.

## Active Workflows

| Workflow | Location | Status | Description |
|----------|----------|--------|-------------|
| **WF-A1** | `a1/` | Production Active | A1 PDF production pipeline for Czech/German cross-border workers |
| **WF-AE** | (in `scripts/`) | Active | Change package validation and planning approval |
| **WF-M2** | `portal/release1a/` | Active (Plan M2) | Portal Release 1A prototype |

## Experimental Workflows

| Workflow | Location | Status | Description |
|----------|----------|--------|-------------|
| **WF-AC** | `ac/` | Experimental (Plan AC) | Market research evidence collection and scoring |
| **WF-AF** | `af/` | Experimental (Plan AF) | Free model evaluation with bounded synthetic testing |

## Proposed (Not Active)

| Workflow | Location | Status | Description |
|----------|----------|--------|-------------|
| **WF-CI** | `.gitlab-ci.yml` | Proposed (DEC-016) | GitLab CI/CD pipeline — dormant until approved |
| **WF-PORTAL** | `portal/` | Proposed | Jan-first web portal — after M2 |

## Directory Structure

```
workflows/
├── README.md              # This file
├── a1/                    # WF-A1: A1 PDF Production
│   ├── README.md          # Full workflow documentation
│   ├── SKILL.md          # Reference to canonical skill
│   └── .archive/         # Archived superseded scripts
├── ac/                    # WF-AC: Market Research Evidence
│   ├── README.md          # (to be created)
│   └── .archive/          # Archived superseded collector scripts
└── af/                    # WF-AF: Free Model Evaluation
    ├── README.md          # (to be created)
    └── .archive/          # Archived superseded scripts
```

## Versioning

- **WF-A1**: Version-tagged — see `git tag wf-a1/v*`
- **WF-AC/WF-AF**: Unversioned (experimental)
- **Scripts**: Use SemVer when stable

## See Also

- [`plans/INDEX.md`](../plans/INDEX.md) — All plans and their status
- [`docs/decisions/decision-register.md`](../docs/decisions/decision-register.md) — All decisions
- [`AGENTS.md`](../AGENTS.md) — Agent instructions and authority hierarchy
