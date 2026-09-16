# Cline claims review — 2026-09-16

Status: research, bounded source repair and executed synthetic diagnostics; not release, deployment,
real-data activation or operator acceptance. Owner: primary engineering agent,
under existing REL-02/REL-05 and OCR-CORE-10/11/13/14 tasks.

Inspected checkout: `995c945` on `feat/prace-readiness-plan-2026-08-13`, including
inherited working-tree edits. The index was empty at review start. Existing edits
were preserved. After the reproduced export finding, the primary assigned a
bounded repair in `scripts/run_release_reproducer.py` and the new
`tests/test_release_export_sensitive_paths.py`. The inherited
`tests/test_release_reproducer.py` remains untouched.
The attached Cline report is a set of claims, not an execution receipt.

## Findings

| Severity | Finding and executed evidence | Required next action |
|---|---|---|
| High | The proposed three-script baseline can report success for unusable artifacts. Empty JSON is `VALID/0`; a blank three-page PDF is `WARNING/0`; absent review input or missing expected worker values is `CLEAN/0`. | Do not use these tools as acceptance gates. Retain canonical artifact-specific QA and human review. Repair or explicitly mark these helpers as diagnostic, with negative controls and an unproven outcome. |
| High; repaired in working source | The original `run_release_reproducer.tree()` rejects `.env` but accepts a committed `.runtime-config/gunicorn.env` and `.env.synthetic`. A disposable Git repository containing fictional canary text reproduced both omissions. | REL-02: the bounded repair now rejects protected configuration paths before reading any tree blobs. The new focused regression passes; publication and committed-source evidence remain with the primary. |
| Medium | `dual_framework.py` reports `PARTIAL/0` without a second PDF and `VERIFIED/0` for the same blank PDF supplied twice. It never generates the second framework output despite its function docstring. A metadata-only difference produces `DISCREPANCY/1`. | Require two independently produced, provenance-bound artifacts for framework comparison. Compare intended field semantics and layout using the canonical renderer contract; a byte hash proves identity, not equivalence or correctness. |
| Medium | `hardcode_checker.py` defaults to `a1/review.csv`, returns no failure when input/worker/expected values are absent, and its JSON output includes up to 50 characters of each matched source value. | Never run its suggested default as a synthetic probe. Use an explicitly generated synthetic CSV. Remove value-bearing diagnostics before considering real-data use; replace keyword absence with explicit expected-field validation. |
| Medium | “Proven stability” of the current orchestration is unsupported. Inspected code has useful durable leases, attempts, tenant scope and audit integration; the current research explicitly leaves production supervision, PostgreSQL concurrency and full browser acceptance open. | State implementation and test coverage separately. Measure an isolated synthetic worker and queue before comparing orchestration frameworks. |
| Medium | The older LangGraph guide is a sketch with inconsistent/nonexistent paths and incomplete Python. The newer review prioritizes measured stage recovery; the Cline recommendation makes the OSSZ sketch look like an approved next implementation. | Treat the guide as conceptual. Scope any graph experiment in the active child plan with measurable comparison/stop criteria; preserve JAN-01–04 priority. |
| Low | `web_search.py` is correctly identified as a stub, but it still returns `PARTIAL/0` with zero results and no sources. Adding a key would not implement its missing search code. | Exclude it from research-verification claims. Real research must have retrieved primary sources, retrieval dates and explicit supported claims. |

Severity describes the impact if these scripts are used as proposed gates. The
export probe demonstrates a missing defense; it does not establish that protected
configuration is present in the actual Git history or that any secret was exposed.

## What the existing commands actually establish

| Tool | Verified behavior | Evidence boundary |
|---|---|---|
| `verification/schema_validator.py` | Its documented `--file`, optional `--type`, and `--json` arguments exist. PDF checks count pages and reject encryption; JSON checks selected keys only if present. The `schema` function argument is unused. | It does not enforce a receipt schema, require JSON top-level fields, verify field values, or prove visual PDF correctness. The nominal PDF “required markers” are not required for success. |
| `verification/dual_framework.py` | The stated CLI exists. It hashes and counts supplied PDFs; `--worker` labels the output. Without `--pdf1`, it searches provisional subdirectories and takes the first matching filename. | No framework is executed and no worker/input binding is checked. Never choose artifact authority by this implicit directory search. |
| `verification/hardcode_checker.py` | The stated CLI exists. It scans six English placeholder words and lists source values that happen to be found. | It does not establish that all expected fields are present or that absent keywords imply correct data. Valid synthetic markers can also trigger its heuristic. |
| `scripts/validate_planning.py` | Checks catalog schema and enumerated planning/governance invariants; CLI distinguishes pass `0`, failure `1` and environmental/unproven `2`. | Structural planning validation is not application, host, legal or operator acceptance. No live planning-validation run was performed in this delegated review. |
| `scripts/validate_change_packages.py` | Classifies paths and inspects eligible content. Executing selected checks requires `--staged --run-checks`; command results and timing are recorded separately. | Classification without executed checks is not runtime validation. Staged selection can execute working-tree commands; it is not committed-source testing. |
| `scripts/run_release_reproducer.py` | Exports and verifies a requested committed tree, records runner/dependencies/environment and command exits. Default commands are a selected mix of planning, pytest and Django tests. | Its default selection is not an all-services or intended-host browser acceptance run, and includes optional A1 checks. Current interpreter/dependencies and selected DB context remain part of evidence. See the export-path finding above. |
| `scripts/rehearse_synthetic_site.sh` | Exposes explicit prepare/start/stop/restart/smoke/provision/workflow commands. `workflow --profile core\|optional-a1` exists. | Preparation/migration, process management and workflow execution have side effects. Merely naming the script is not evidence of a completed rehearsal. No lifecycle command was executed here. |

All four `verification/` commands' `--help` invocations completed with exit `0`.
No actual `process_ocr` worker, database, rehearsal server, external model or
network search was started by this review.

## Executed synthetic checks

The fixtures were newly created blank PDFs, an empty JSON object and a CSV with
the conspicuous identity `SYNTHETIC_ONLY`. They were created in disposable non-PII
temporary directories and removed afterwards. No existing PDFs, worker records,
runtime receipts, credentials or protected configuration were inspected.

For the command table, `$fixture` denotes that newly generated temporary directory;
`blank3.pdf` has three blank A4 pages, `blank1.pdf` one, and
`blank3-metadata.pdf` the same page structure with an added synthetic title.
`review.csv` contains `employee_id,given_name` and
`SYNTHETIC_ONLY,EXPECTED_SYNTHETIC_VALUE`; `missing.csv` does not exist.
All commands used the canonical `venv/bin/python` interpreter.

| Command after `venv/bin/python` | Native exit | Observed outcome |
|---|---:|---|
| `verification/schema_validator.py --file "$fixture/empty.json" --json` | 0 | `VALID`, `schema_valid=true` for `{}` |
| `verification/schema_validator.py --file "$fixture/blank3.pdf" --json` | 0 | `WARNING`, `schema_valid=true` |
| `verification/schema_validator.py --file "$fixture/blank1.pdf" --json` | 1 | `INVALID`, confirming the page-count negative control |
| `verification/dual_framework.py --worker SYNTHETIC_ONLY --pdf1 "$fixture/blank3.pdf" --json` | 0 | `PARTIAL` |
| `verification/dual_framework.py --worker SYNTHETIC_ONLY --pdf1 "$fixture/blank3.pdf" --pdf2 "$fixture/blank3.pdf" --json` | 0 | `VERIFIED` |
| `verification/dual_framework.py --worker SYNTHETIC_ONLY --pdf1 "$fixture/blank3.pdf" --pdf2 "$fixture/blank3-metadata.pdf" --json` | 1 | `DISCREPANCY` |
| `verification/hardcode_checker.py --worker SYNTHETIC_ONLY --pdf "$fixture/blank3.pdf" --review-csv "$fixture/missing.csv" --json` | 0 | `CLEAN`, zero verified input values |
| `verification/hardcode_checker.py --worker SYNTHETIC_ONLY --pdf "$fixture/blank3.pdf" --review-csv "$fixture/review.csv" --json` | 0 | `CLEAN`, zero verified input values |
| `verification/web_search.py --type pdf-overlay --json` | 0 | `PARTIAL`, zero results |

Focused existing regression command:

```bash
venv/bin/python -m pytest -c /dev/null -p no:cacheprovider \
  tests/test_validate_change_packages.py tests/test_release_reproducer.py -q
```

Native exit `0`: **64 passed in 13.36 seconds**. These tests use disposable
synthetic repositories. They establish those runner/selection contracts, including
failure and cancellation handling; they do not close the independently reproduced
export exclusion defect or run application acceptance. The full planning test
module was not run because its fixture enumerates a broader committed source tree
than this delegated review needed.

Observed environment: Python `3.13.5`, pypdf `6.15.0`, pytest `9.1.1`.
This is an installed-environment observation, not clean-install reproducibility.
The 64-test run occurred before the export repair; it must not be represented as
a regression run of the repaired source.

The additional export probe created a separate disposable Git repository per case,
committed only `SYNTHETIC_CANARY=fictional-only`, then called
`scripts.run_release_reproducer.tree(repository, "HEAD")`: `.env` raised
`ValueError`; `.runtime-config/gunicorn.env` and `.env.synthetic` returned one
exportable entry each. No `reproduce()` invocation against the actual repository
was made during that original probe.

## Bounded export repair

The repaired tree reader validates all Git entry metadata before reading any
blob. It retains existing protected root rules and `employees/scans`, excludes
`.runtime-config`, `.history-remediation` and `secrets` components at any depth,
and excludes `.env`, `.env.*` and `*.env` payload paths. A final `.env.example`
filename, or a `*.env.example` source template, remains eligible outside protected
directories. Publication privacy/content checks still apply to examples: a name
is not proof that a file is nonsecret. Ordinary source filenames containing
`a1`, `ocr` or `secret` are allowed, as is existing non-sensitive
`docs/decisions/evidence/` documentation.

The new test module commits only fictional canaries to disposable repositories,
asserts protected trees are rejected before the first `cat-file blob` call,
checks non-sensitive examples, and exercises `reproduce()` rejection before any
runtime/export is created. It never opens the actual protected locations.

```bash
venv/bin/python -m pytest -c /dev/null -p no:cacheprovider \
  tests/test_release_export_sensitive_paths.py -q
```

Native exit `0`: **23 passed in 1.91 seconds**. The scoped whitespace check also
returned `0`. The inherited 64-test suite was not repeated ahead of the delivery
hook. Final source SHA-256 identities for this focused run:

| File | SHA-256 |
|---|---|
| `scripts/run_release_reproducer.py` | `23450bedfa8c80e56fdfb98853d70bb7570dbad27a8bac2d760eb19aaa1efb99` |
| `tests/test_release_export_sensitive_paths.py` | `c9fcaa3c7447955fdf286cfd4bd1ef850e88ebdc37c39a31481f4398d61ad422` |

This repair closes the reproduced path-exclusion defect in working source. It
does not claim all possible secret-bearing filenames can be recognized by path,
repair the legacy verification tools, or provide full release acceptance.

## Orchestration claims and next decision

The reviewed worker reloads actor/organization authorization for each batch;
`document_intake.py` uses conditional claims, 15-minute leases, attempt fencing,
up to three attempts and existing audit records. Failed work requires an explicit
retry; expired running work can be reclaimed. The processor runs synchronously
inside its claimed attempt and is rerun on recovery. A lease is not a process
deadline, cancellation mechanism or durable checkpoint for each OCR stage.

No LangGraph imports occur in the inspected worker/intake/verification/runner
source paths. This scoped inspection does **not** independently establish the
report's repository-wide count of 45 references, zero imports everywhere, absent
CI integration, or stable host operations.

The older [integration guide](../architecture/langgraph-integration.md) names
`scripts/research/ossz_verification.py`, `research/langgraph/ossz_verification.py`
and `scripts/core/a1_core.py`; none exists in this checkout. The canonical
`scripts/a1_core.py` exists. Its example returns an undefined `result` after a
comment standing in for workflow construction; it is not an executable starter.

Use the newer [orchestration review](2026-09-16-document-orchestration-review.md)
for the comparison specification: current worker versus minimal Django stage
receipts versus an optional thin LangGraph adapter, with identical synthetic
inputs, engines and configuration. Measure repeated work after faults, queue/stage
latency, recovery complexity and review effort before adoption. Keep human review,
tenant authorization, source revisions and business audit in the existing domain
services. An agent message, graph checkpoint or successful CLI exit cannot grant
approval or replace any of those controls.

Recommended bounded queue for the primary:

1. REL-02: integrate the bounded committed-export exclusion repair and its new
   negative regression module. Preserve the original failure evidence and keep
   pre-repair test results distinct from the focused repaired-source result.
2. REL-05: classify legacy verification tools as diagnostics and add explicit
   `unproven` handling before any automation consumes their exits as acceptance.
   Avoid a second A1 QA pipeline.
3. JAN-01–04: complete the core workflow's isolated PostgreSQL/browser evidence
   and intended-route acceptance; keep optional A1 acceptance separate.
4. OCR-CORE-10/11/13/14: only then compare measured stage recovery and bounded
   graph orchestration. Define wait/resume authorization, idempotency and source
   version checks before implementing any automatic side effects.

## Source identities and limitations

Pre-repair SHA-256 identities captured during the original synthetic probe:

| File | SHA-256 |
|---|---|
| `verification/schema_validator.py` | `c51db21d79409bf4080c91e57788b633c1b1fa944be06d738008786782350046` |
| `verification/dual_framework.py` | `4a844a572ba0ccc02cdc1d5e618dbe9ebf916258a9d498eec1245bb5e5f836a9` |
| `verification/hardcode_checker.py` | `4b46fd97846b526c77b1a3c08dc0f5d1a40093355f1757390caf4d0ca4e7b27c` |
| `verification/web_search.py` | `3a48afcdf43a82a2d430bf4b0a1879fdbd2a76206f178ea2141f94f3f5bb733e` |
| `scripts/validate_change_packages.py` | `27042baa5722329ae28dccb80eef367840130231e5c82904dba167def6c842bc` |
| `scripts/run_release_reproducer.py` | `511b229a0de669c9f50716dadd3c477a73e34a6e16bc69ef574dbe7e5545280a` |
| `tests/test_validate_change_packages.py` | `7f956b6261e63601adaff84e1eaa6d4a60763a16b88fbbdad30567a5d52d693d` |
| `tests/test_release_reproducer.py` | `da4cd5b58552c55d4bb41b87c88873db40c246879a5eb145333212d20af61bff` |

This is source review plus the stated executed probes. It does not revalidate the
previous assistant's private PDF QA claim, inspect all-page previews, test all
servers/sites, apply Ansible, test PostgreSQL or establish Jan acceptance. Those
require separately scoped evidence owned by the primary and infrastructure team.
