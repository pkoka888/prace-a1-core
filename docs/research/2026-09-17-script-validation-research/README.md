# Script validation research, trial and agent-output review

**The supplied completion claim is not accepted.** Its 15 tests pass, but eight
safe synthetic probes reproduce important discovery defects. The working
application/generator/PDF and existing Git hook were not changed.

| Deliverable | Open |
|---|---|
| Agent research/report template and ranking rubric | [Research contract](RESEARCH-CONTRACT.md) |
| Ten ranked current solutions, coverage, versions and trial comparison | [Comparison](COMPARISON.md) |
| Popularity, release/activity dates, licenses, requirements and official URLs | [Verified sources](source-verification.md), [metadata JSON](tool-metadata.json) |
| Good/bad examples and exit/result expectations for all ten | [Solution examples](SOLUTION-EXAMPLES.md) |
| Actual free-model CLI runs, failures and proposal corrections | [CLI research](CLI-RESEARCH.md), [receipt](cli-research-receipt.json) |
| Top two installation/review/trial contracts | [Nox YAML](nox-installation.yaml), [pre-commit YAML](pre-commit-installation.yaml) |
| Executed positive/negative trial, source hashes and timings | [Trial results](pilot-results.json), [runner](examples/research_run_pilot.py) |
| Review of the supplied agent output and prioritized findings | [Review](AGENT-OUTPUT-REVIEW.md), [probe results](review-probe-results.json) |
| Validation/automation definitions, paths, dates, triggers and coverage | [Definition inventory](validation-definitions.md), [JSON](validation-definitions.json) |
| Latest retained results, observed counts, errors and unknowns | [Health table](validation-health.md), [JSON](validation-health.json) |

## What the results mean

Nox and pre-commit both passed the good synthetic fixture and rejected the bad
fixture with the expected detailed results. They use the same five check groups;
this is a workflow demonstration, not an accuracy benchmark or acceptance of the
discovery script. The dedicated research environment contains pinned dependencies;
the application venv is unchanged. No Git hooks or CI were installed.

The project uses **GitHub as origin**. GitLab configuration exists as an inactive
proposal; neither its file presence nor a proposed server URL proves active CI
or a particular server edition. GitHub API reads returned 401, so remote workflow
activation/run history remains unknown. No credential changes were attempted.

The local health view covers 125 definitions and 83 retained receipts containing 320
check records (307 PASS, 10 FAIL, 1 ERROR, 2 INTERRUPTED). Only 29 definition rows
match this evidence; unmatched rows are unknown, not proven unused. Counts cover
September 11–17 retained parent-run starts, not lifetime usage. File creation/update
dates are Git history for containing files, not individual validation birth dates.

The latest retained runtime-dependency package result is FAIL with a
`ModuleNotFoundError` in a named regression test. Historical passes elsewhere do
not establish today’s source/dependency/settings identity. Read the health table
before deciding which checks are missing or redundant.

## Scope and limitations

- New work is local and uncommitted. No source publication, deployment or activation.
- CLI research used public documents/synthetic context on explicit free models.
  Two broad Kilo runs retrieved sources but exceeded their fetch budgets; their
  incomplete summaries are not claimed as completed research reports. Both smaller
  finalist installation-research tasks returned proposals, which were reviewed.
- Public research scratch is in `/tmp/script-validation-research-20260917/`.
  Durable primary-reviewed reports are here. Detailed trial receipts are protected
  under `runtime/portal/temporary/validation-research-20260917/` (90-day review).
- Host cron/systemd timer inventories, arbitrary agent session histories and
  deleted/unretained CI logs are outside this scoped snapshot. No full lifetime
  automation inventory is claimed. The missing prior-session file-operation
  ledger remains a finding against the supplied completion report.
- The existing change-package receipts provide the best starting point for a
  health view. Allure/ReportPortal can add test history after integration; they
  cannot recover executions that were never recorded. Monitoring research and
  official API links are in the definition/health reports.

Next: repair discovery confinement/redaction first, verify coverage and session
provenance, then add meaningful checks through the existing catalog. Avoid a new
orchestrator dependency until its incremental benefit is demonstrated.
