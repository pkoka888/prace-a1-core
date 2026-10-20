# Git extraction research and comparison with the actual plan

Date accessed and tested: 2026-09-18.
Scope: authoritative web research, bounded source inspection, and a generated
synthetic Git experiment. No project history or private files were copied.
Companion: [initial comparison](2026-09-18-project-separation.md).
Plan assessed: [backup-first separation](../../plans/2026-09-18-backup-and-project-separation.md).

## Correction to the first research pass

The initial pass did consult official websites, but compared repository layouts
more thoroughly than extraction mechanisms. It omitted `git-filter-repo` and
`git subtree split`, had no executable comparison, and could not justify treating
the current validation-package boundaries as extraction boundaries. This follow-up
addresses those gaps. It does not certify an application migration or whole backup.

## Authoritative source register

These are vendor/project documentation and upstream source, not search snippets or
third-party tutorials. Claims are paraphrased. Upstream main/master pages can change;
the local experiment separately records the installed tool identities.

| ID | Authority and direct URL | Finding relevant to this task | Limitation/application |
|---|---|---|---|
| S1 | GitHub: [Splitting a subfolder into a new repository](https://docs.github.com/en/get-started/using-git/splitting-a-subfolder-out-into-a-new-repository) | Documents extraction in a fresh clone using `git-filter-repo`; the recipe does not preserve all original branches/tags | A Git history workflow, not a backup of dirty/untracked/private application state |
| S2 | git-filter-repo upstream: [project](https://github.com/newren/git-filter-repo), [manual source](https://github.com/newren/git-filter-repo/blob/main/Documentation/git-filter-repo.txt) | Supports multiple selected paths, path remapping and fresh-clone safety; renamed paths need explicit coverage | Best flexible history-preserving candidate; path selection alone is not content sanitization |
| S3 | Git upstream: [git-subtree manual](https://github.com/git/git/blob/master/contrib/subtree/git-subtree.adoc) | `split` produces synthetic history for one prefix with that directory at the new root | Fits a self-contained directory; distributed config/tests require more work |
| S4 | Git: [filter-branch warning](https://git-scm.com/docs/git-filter-branch) | Warns about safety/performance problems and recommends an alternative such as filter-repo | Do not choose legacy filter-branch for a new extraction |
| S5 | GitHub: [Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) | Rewriting can affect hashes/signatures and requires coordination with other copies | Extraction is not proof that sensitive history has been purged everywhere |
| S6 | Git: [submodules](https://git-scm.com/docs/git-submodule) | Records another repository as a pinned dependency with separate initialization/update behavior | Appropriate for a retained dependency, not unrelated tools that should disappear from app delivery |
| S7 | Git: [sparse-checkout](https://git-scm.com/docs/git-sparse-checkout), [worktree](https://git-scm.com/docs/git-worktree) | Sparse checkout controls visible working files; worktrees share repository data with separate checkout state | Neither creates an independent ownership/history boundary |
| S8 | Git: [bundle](https://git-scm.com/docs/git-bundle), [archive](https://git-scm.com/docs/git-archive) | Bundle transports Git objects/refs; archive exports a selected tree (with explicit options for extra files) | Neither automatically backs up dirty work, database, protected files and configuration as a consistent whole |
| S9 | Git: [init](https://git-scm.com/docs/git-init) | Creates a new repository | Foundation for a reviewed current-file transfer; preserving history is deliberately traded away |
| S10 | BFG author: [BFG Repo-Cleaner project and usage](https://rtyley.github.io/bfg-repo-cleaner/) | Targets removal of unwanted large files and sensitive content from history | Cleanup tool, not our selected multi-path application/tooling separation mechanism |

S1 currently says Git 2.22 or later; S2's current project prerequisites say Git
2.36 or later. Use the selected tool release's own requirements rather than blindly
copying the tutorial minimum. Installed Git here is 2.47.3 and filter-repo reports
`31ebad4c8fb3`; this is an observed identifier, not a guessed release number.

## Purpose-specific solution comparison

Costs and fit below are engineering judgments based on the inspected repository.
They are not vendor benchmarks or measured large-repository performance results.

| Mechanism | Advantages | Disadvantages | Fit here / selection |
|---|---|---|---|
| **Reviewed current-file transfer + fresh Git repository** (S9) | Can transfer selected current dirty/untracked bytes after review; no inherited Git objects; accommodates scattered files | Loses native old blame/history in destination; needs manifest, attribution/licenses and explicit byte/mode checks; current content still requires review | **Selected now**, because preserved local historical refs may contain PII and source is dirty |
| **git-filter-repo** (S1/S2) | Purpose-built repository extraction; multiple paths and remapping; retains relevant rewritten history | Changes commit IDs; historical paths/messages/authors/content need review; does not include uncommitted work automatically | **Preferred conditional alternative if retaining history becomes a requirement**, using a separately authorized sanitized source and fresh protected clone |
| **git subtree split** (S3) | Direct split of a self-contained directory with relevant history; supports future synchronization workflows | Single-prefix boundary; output history is still history, including old contents; scattered helpers/config/tests are omitted unless prepared | Not selected: our tooling units span several directories |
| **Submodule** (S6) | Pin independent component revisions explicitly | Adds checkout/update/authentication burden and continuing dependency relationship | Not needed for unrelated tooling; reconsider only for a real shared component |
| **Sparse-checkout / worktree** (S7) | Convenient focused checkout or parallel source work | Does not remove unrelated repository history or provide independent access control | Implementation conveniences only, not final separation |
| **filter-branch / BFG** (S4/S10) | Existing history rewriting/cleanup capabilities | filter-branch has upstream warnings; BFG's documented focus is cleanup rather than this extraction shape | Neither selected |

The destination repository strategy and extraction tool are separate decisions.
GitHub's filter-repo recommendation does not oblige us to transfer history when
our task is current-tree separation and historical data requires special handling.
The tradeoff is explicit: a clean new history with a provenance manifest instead
of old destination blame. Original governed history stays where it is.

## Actual repository findings

Baseline remains `ea81d9b76e2188a93ec2815f7f6ea37b081567ff` plus inherited dirty
work and this task's documentation. Locally recorded upstream is one commit ahead;
no fetch or reconciliation has been performed in this research.

| Inspected evidence | What it shows | Change required in the plan |
|---|---|---|
| `change-packages.yml`, `cli_agent_tooling`, around lines 350–380 | General CLI verifier shares a package with `release_verifier.py`, `playwright_smoke.py`, readiness tests and `repair_a1_template_checkboxes.py` | Split selection at file level; retain site/release/A1 helpers and their checks |
| `scripts/verify_cli_claims.py:25–28`, `tests/test_verify_cli_claims.py:99–110` | Verifier reads both `config/cli_verification_claims.json` and its schema, writes under `cli-docs-update/` | Transfer runner, both configuration files, tests and relevant docs together; directory-only extraction is incomplete |
| `change-packages.yml:354–359` versus the verifier | Package path list includes the schema but omits the default registry JSON | Package declarations are useful discovery seeds, not an exhaustive dependency manifest |
| `scripts/run_free_model_eval.py:15–16`, `src/free_model_eval/core.py:651`, `engine.py:28`, package around line 606 | Evaluation spans source, runner, policy/config, fixtures, tests and docs; runtime reads fixture paths | Multi-path transfer required; splitting only `src/free_model_eval/` fails to deliver a usable unit |
| `agent_operations_experiment` package around line 312 | Bounded synthetic graph has separate config/dependencies/script/test/docs | Candidate coherent extraction unit, subject to file review; not a reason to remove product OCR orchestration |
| `src/invoice_ingestion/contracts.py` and `plan_ad_invoice_contracts` | Synthetic in-memory contracts with no database/web/OCR dependency declared | Keep under business-scope review; insufficient evidence to call it unrelated to BO |
| `docs/operations/sysadmin-readiness-2026-08-12.md:56–61` | Recorded local pre-rewrite refs/history may be sensitive | Avoid copying `.git` into the extracted source; do not run real-history experiments |

These observations establish concrete dependencies and risks, not a complete
classification of all repository files. In particular, package names, filenames
and an absence of literal imports cannot prove runtime independence.

## Executed synthetic comparison

A generated repository contained `app/site.txt`, `tools/tool.txt` and
`config/tool.json`. The first tool revision held a clearly fictional historical
marker, then a second commit removed it. Later working edits and an untracked
file modeled the current dirty-checkout problem. No real file/history was used.

Successful run: `runtime/portal/temporary/separation-research-79fqh0w9/`.
It contains `experiment.py`, `receipt.json`, exact Git argument arrays and generated
fixtures. Reproduce by copying the script into a new empty protected in-project
directory and invoking the repository venv interpreter; do not rerun over its
existing fixture directories.

| Experiment | Executed result | Consequence |
|---|---|---|
| `filter-repo --path tools/ --path config/tool.json` on a fresh fixture clone | Selected both paths; historical fictional marker remained in old commits | Good multi-path extraction; selecting clean current paths does not sanitize their history |
| `subtree split --prefix=tools HEAD` | Produced root `tool.txt`; separate config omitted; old marker retained | Single-folder convenience does not solve scattered dependency closure |
| Bundle HEAD and clone it | Committed tool version restored; later dirty edit and untracked file absent | Bundle alone is not the requested current whole-project backup |
| Copy three explicit reviewed working files into a fresh repository | Current working bytes matched; one new commit; old marker absent from history | Supports the selected extraction mechanism for these controlled inputs |
| Check original fixture HEAD | Unchanged | Experiment did not rewrite its source HEAD |

Eight assertions passed. The initial experiment failed because the harness tried
to check out `FETCH_HEAD` after a bundle clone. The corrected run selects the known
synthetic commit ID. Original script and failure note remain at
`runtime/portal/temporary/separation-research-9fcyrrm8/`; this was a harness defect,
not an extraction-tool defect. No application tests, remote publication, backup
restore or large-history benchmark is claimed by these checks.

## Comparison with the existing plan and resulting decision

| Existing plan element | Assessment after research | Disposition |
|---|---|---|
| Backup before relocation | Correct; Git extraction omits important state | Retain, with actual encrypted restore still pending |
| Keep application modular monolith; extract unrelated tools | Fits current multi-directory product and supporting services | Retain |
| Fresh history for extracted tooling | Justified by dirty source and sensitive-history record; previously underexplained | Retain with explicit loss-of-blame tradeoff and filter-repo alternative |
| Start with CLI investigations | Reasonable only at exact-file granularity | Amend: never move the whole `cli_agent_tooling` package |
| Use package definitions to scope tests/files | Definitions demonstrably mix scopes and omit a consumed config | Amend: inspect runtime reads, tests and scripts; manifests must be independently complete |
| Independent destination | Still only a proposed logical name; no exact authorized final location/remote | Keep as unresolved completion criterion; nested workspace is only staging |
| “Complete separation” | Current-tree/build separation does not erase original history | Make this limitation visible; history purge is a distinct task |

Final recommendation remains **reviewed multi-path current-file extraction into
an independent repository**, after verified backup. If history preservation is
required, choose **git-filter-repo**, not subtree, after a separately authorized
history review. The stronger research changes the migration safeguards and file
classification, not the retained application architecture.
