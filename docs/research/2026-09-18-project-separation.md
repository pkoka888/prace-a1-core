# Project separation: options and recommendation

Date: 2026-09-18. Status: researched recommendation; no extraction or backup executed.
Scope: keep sites, front office (FO), back office (BO), OCR and A1 forms, including
their operational, security, testing and documentation dependencies.
Execution: [backup-first separation plan](../../plans/2026-09-18-backup-and-project-separation.md).

Follow-up: [authoritative Git extraction research, local experiment and actual-plan comparison](2026-09-18-git-extraction-evidence.md).
This expands the initially incomplete extraction-tool comparison with filter-repo,
subtree, concrete dependency findings and executed synthetic evidence.

## Decision

Choose **a focused application repository plus an independent tooling/research
repository**, preserving the application's existing Django modular monolith.
Use **Restic plus a PostgreSQL-consistent dump and coordinated file capture** for
the prerequisite backup, unless infrastructure already has an approved, verified
equivalent. Do not introduce a second backup system merely for this cleanup.

This is an engineering recommendation, not approval of new remotes, host changes,
service interruption or real-data activation. FO/BO meanings are an explicit working
assumption. No frontend rewrite, service split or A1-engine replacement is needed.

## Local evidence and limits

Inspection baseline: `ea81d9b76e2188a93ec2815f7f6ea37b081567ff` on
`feat/prace-readiness-plan-2026-08-13`. Locally recorded upstream was one commit
ahead, `ecc813a`; the remote was not refreshed. Nine tracked files were modified,
the index was empty, and many untracked scripts, skills and research files existed.
Those working-tree inputs must be preserved independently of HEAD.

Tracked-path and bounded source inspection found:

- `public-site/index.html`, `portal/`, shared `src/document_core/`, and canonical
  A1 scripts are the product foundation. `frameworks/jansa1_v1/` is A1-related,
  so its generic directory name does not justify extraction.
- `cli-docs-update/` contains general CLI investigations. Market-evidence collectors,
  `src/free_model_eval/` and `workflows/ac/` / `workflows/af/` are candidate tooling
  units. Move their tests, schemas, configurations and docs together if confirmed.
- `change-packages.yml` explicitly selects research, collector, evaluation and
  agent-operation checks. `scripts/validate_planning.py` carries historical research
  references. Deleting those directories without updating consumers breaks tooling.
- `src/invoice_ingestion/`, prototypes, general skills and recruitment market
  research need individual scope decisions. Recruitment research may support the
  site even when its general-purpose collector belongs elsewhere.
- Current filesystem availability was about 85 GiB. This is not a backup-size
  estimate or evidence that an archive and full restore fit.
- Restic, Borg, age and pg_dump executables exist. Their presence does not prove a
  configured destination, key custody, successful job or usable restore.
- The existing sysadmin readiness record warns that historical Git objects may
  contain PII. A Git bundle or history-preserving split is not a safe default.

Private file contents, credentials and runtime configuration were not inspected.
No claim of exhaustive file classification or runtime dependency closure is made.

## Separation alternatives

The tradeoff assessments below are project-specific engineering judgments.
Documentation establishes tool behavior; it does not establish this application's
acceptance. No application migration rehearsal or performance benchmark has been
performed; the linked follow-up records a bounded synthetic extraction experiment.

| Solution | Advantages | Disadvantages | Disposition |
|---|---|---|---|
| **Focused application + independent Git repository** | Separate dependencies, tests, ownership and release cadence; unrelated files absent from application checkout/build; retains existing product architecture | Requires precise dependency closure and two maintenance roots; new remote/location needs its own authorization | **Selected target**; transfer reviewed current files without importing historical Git objects |
| **Single repository with product/tooling directories** | Atomic cross-cutting changes; simple source navigation and rollback; no second remote | Unrelated material remains in project; access and history remain shared; packaging boundaries need enforcement | Useful transition, insufficient final separation for this request |
| **Git submodules** | Independently versioned repository pinned to a commit | Clone/update/authentication complexity; keeps a tooling relationship in the parent; developers must manage two states | Use only if the application truly needs a separately maintained dependency |
| **Git sparse-checkout** | Smaller working-tree view; convenient developer focus | Does not remove material from repository/history or establish an access boundary; omitted files can still be dependencies | Optional convenience, not the separation solution |

Names and primary references:

- **Git**: [project](https://git-scm.com/), [independent repository initialization](https://git-scm.com/docs/git-init).
- **Git submodules**: [documentation](https://git-scm.com/docs/git-submodule).
- **Git sparse-checkout**: [documentation](https://git-scm.com/docs/git-sparse-checkout).
- **Import Linter**: [project/documentation](https://import-linter.readthedocs.io/en/stable/),
  [forbidden and layer contracts](https://import-linter.readthedocs.io/en/stable/contract_types/).
  Optional future enforcement of Python boundaries; it does not inspect shell,
  templates, data files or dynamic path lookups. Existing focused checks should be
  extended first; no new dependency is required to prepare this separation.

Do not split FO, BO, OCR and A1 into microservices for this task. They remain in
scope and share authentication, provenance and transactions under ADR-001/002.
Repository separation of unrelated tools does not require network service boundaries.

## Backup alternatives

| Solution | Advantages | Disadvantages | Disposition |
|---|---|---|---|
| **Restic** | Encrypted repository, deduplication, multiple storage backends, integrity and restore commands | Needs separately recoverable key, destination and retention ownership; filesystem capture alone cannot make DB/files consistent | **Preferred if no approved solution already exists** |
| **BorgBackup** | Deduplication, compression, authenticated encryption when configured, local/SSH workflow | Repository/key configuration and remote operation need ownership; still needs database/file coordination | Strong alternative for an existing Borg-operated estate |
| **Git alone** | Preserves committed source history and makes source rollback convenient | Omits ignored/private files and unsaved work; not a live database backup; historical objects may be sensitive | Source versioning only; reject as whole-project backup |

Primary product and documentation links:

- **Restic**: [project](https://restic.net/), [repository and key setup](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html),
  [backup](https://restic.readthedocs.io/en/stable/040_backup.html),
  [integrity checks](https://restic.readthedocs.io/en/stable/045_working_with_repos.html),
  [restore](https://restic.readthedocs.io/en/stable/050_restore.html).
- **BorgBackup**: [project](https://www.borgbackup.org/),
  [documentation](https://borgbackup.readthedocs.io/en/stable/).
- **PostgreSQL pg_dump / pg_restore**: [project](https://www.postgresql.org/),
  [SQL dump and restore documentation](https://www.postgresql.org/docs/current/backup-dump.html).
  A database dump has database consistency semantics; it does not synchronize
  external uploaded files. Roles and other cluster-wide prerequisites need explicit
  recovery coverage as well.

All recommendations use existing/self-managed capacity; no paid provider or new
subscription is selected. Operating effort and storage capacity are still costs.

## What “complete separation” means

The application can be installed, tested, built and demonstrated with the extracted
tooling directory absent. Its dependency files and mandatory checks do not require
unrelated tools. Extracted tools have their own reproducible setup, tests and owner.
Protected data remains in its authorized locations; it is not moved with source.
Original paths and history remain traceable in a sanitized transfer manifest.

A normal source removal leaves older Git commits intact. This plan separates the
current tree and delivery inputs, not history. History erasure requires a separate,
exactly authorized operation and is deliberately not part of the recommendation.

## Limitations and next owner

Research and planning are complete for the compared options. Backup execution is
pending identification of the approved destination/key custodian and infrastructure
coordination. Exact file manifest, transfer, installation and runtime acceptance
remain implementation work. Infrastructure owns recovery; engineering owns source
classification and extraction; Jan owns confirmation of ambiguous business scope
and observed product acceptance.
