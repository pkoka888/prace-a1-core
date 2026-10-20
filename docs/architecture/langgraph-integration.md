# LangGraph integration guide

Status: measured and aligned, 2026-10-20. This guide states what the
LangGraph layer is for in this repository, what it currently does, what it
must never do, and the exact commands that work. It complements the
[field → source mapping](a1-field-source-mapping.md) and the
[gap analysis](a1-gap-analysis.md).

## 1. Principle: the core stays clean, LangGraph is an optional orchestration layer

```
┌─────────────────────────────────────────────────────────┐
│  Core logic (deterministic, tested)                      │
│  - scripts/a1_core.py, scripts/finalize_a1.py            │
│  - Pure functions, no external state                     │
│  - Unit tested, reproducible                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (optional)
┌─────────────────────────────────────────────────────────┐
│  LangGraph orchestration (research/exploration)          │
│  - Research workflows                                     │
│  - OSSZ verification                                      │
│  - OCR provider fallback                                  │
│  - Human-in-the-loop review flows                         │
└─────────────────────────────────────────────────────────┘
```

**The core has no LangGraph imports.** This is a hard boundary, and it is
why the main `requirements.txt` does not list LangGraph at all: the
canonical generator must run in an environment that has never heard of it.
Installing LangGraph into the main requirements would turn an optional
research layer into a runtime dependency of the delivery path.

## 2. Measured state (2026-10-20)

| Item | State |
|---|---|
| `langgraph` | 1.2.11, installed in the venv for the isolated research experiments only; **not** in `requirements.txt` |
| `langgraph-checkpoint-sqlite` | 3.1.1, installed; pinned in `config/agent_ops_workflow.v1.requirements.txt` and declared in `config/agent_ops_workflow.v1.json` |
| `langgraph-checkpoint-postgres` | 3.1.2, installed; used by the A1 orchestrator's checkpoint path; **not** declared in either pinned file |
| `scripts/test_langgraph_install.py` | passes — spins an ephemeral PostgreSQL cluster, creates a `PostgresSaver`, saves and retrieves a checkpoint |
| `scripts/research_agent_ops_workflow.py` + `tests/test_agent_ops_workflow.py` | **37 passed in 176.67s** |
| `scripts/langgraph_a1_orchestrator.py` | runs end to end; `--resume` is still a stub |

### 2.1 How to run the agent-ops experiment

The suite refuses to run outside the repository's private runtime, by
design — `private_directory()` requires the demo directory to live under
`runtime/portal/temporary/`, to be owned by the current user and to have mode
0700, and it rejects symlinks and parent traversal. pytest's default `/tmp`
basetemp is therefore refused with
`ValueError: demo directory must remain in repository private runtime`.

```bash
mkdir -p runtime/portal/temporary/agent-ops-basetemp
venv/bin/python -m pytest tests/test_agent_ops_workflow.py -q \
    --basetemp=runtime/portal/temporary/agent-ops-basetemp
```

The suite is deliberately **not** skipped when a dependency is missing: it
states "No skipping when dependencies are absent: this suite requires the
documented research environment."

### 2.2 How to run the A1 orchestrator

```bash
export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"
venv/bin/python scripts/langgraph_a1_orchestrator.py run --dry-run \
    --review a1/review.csv --cohort a1/cohort.json
```

A dry run is now **side-effect free**: it writes nothing into the protected
output tree and reports the simulated manifest and QA report on stdout only.
See §4.3 for the defect that made that necessary.

## 3. What LangGraph may and may not own

| Use case | Verdict | Why |
|---|---|---|
| **OSSZ / institution verification** | LangGraph | multi-source, multi-step, with fallbacks and a checkpointer so a long verification resumes |
| **Institution profile update proposals** | LangGraph | step-by-step verification: try URL A → URL B → manual proposal |
| **OCR provider fallback** | LangGraph | provider fallback, retry logic, queueing for review |
| **Research workflows** | LangGraph | gather → analyse → summarise, where the branch depends on the fetch result |
| **A1 PDF generation** | not LangGraph | deterministic, no state — call `a1_core` directly |
| **Field validation and defaults** | not LangGraph | pure functions — unit tests are the right tool |
| **The 44-column CSV contract** | not LangGraph | an arity-safe contract, not a workflow |
| **The validation gates** | not LangGraph | `read_review` and `validate_review` are the authority |
| **The provisional notice and issuance workflow** | not LangGraph | binding, audited, human-gated |
| **Database writes** | not LangGraph | the Django ORM and the services layer own transactions |

### 3.1 Alignment with the six topics

LangGraph has no opinion about the data model. Mapped onto the
[one-hood-per-topic](a1-field-source-mapping.md#2-the-six-topics) structure:

| Topic | LangGraph involvement |
|---|---|
| W — person identity | none in the core path. A graph may orchestrate OCR fallback and multi-source identity research; the identity service and the field reviewer own the facts. |
| E — employer, role, situation | none. `Employment` facts are validated by the services layer; the *situation research* (registry lookups, competence rules) is a candidate graph. |
| A — activity and territory | none. Applicability is a rule, not a workflow. |
| O — institution | **the strongest candidate** — verification with fallbacks and a checkpointer, exactly the OSSZ use case. |
| C — certificate | orchestration only: resume, retry, reconcile. The generation, validation and promotion steps stay in the core. |
| P — provenance | none. Evidence is a record, not a workflow. |

## 4. Defects found by running the layer (2026-10-20)

Reading the code would not have found these. They were found by running the
tool and the suite.

### 4.1 `UnboundLocalError` on every run

`cmd_run` called `a1_private_dir()` while building the `WorkflowConfig`, and
three lines later rebound the name `a1_private_dir = a1_private_dir()`. In
Python a local assignment makes the name local for the whole function, so the
earlier call raised `UnboundLocalError: cannot access local variable
'a1_private_dir'`. Every `run` invocation failed before doing anything.

**Fixed.** The local was renamed to `private_dir` and hoisted above its first
use.

### 4.2 `Channel name 'checkpoint_id' is reserved`

The `A1State` TypedDict declared a `checkpoint_id` field. LangGraph 1.x
reserves `checkpoint_id`, `checkpoint_map`, `checkpoint_ns` and
`configurable` as channel names, and `graph.compile()` raised
`ValueError: Channel name 'checkpoint_id' is reserved`. The script had been
written against the 0.3.x API (its own docstring says `langgraph>=0.3.0`)
and had not been run against the installed 1.2.11.

**Fixed.** The channel was renamed `workflow_run_id`; the CLI argument keeps
its user-facing name. A regression test asserts that the state schema does
not intersect LangGraph's reserved set, so the next API bump cannot reintroduce
this silently.

### 4.3 A dry run wrote into the protected output tree

`--dry-run` overwrote `output/provisional/generation_manifest.json` with a
130-byte stub (`{"status": "PROVISIONAL_DRY_RUN", "generated": []}`) and
created `output/qa_report.json`.

This matters because that file is evidence. `a1_quality_gate.require_completed_generation`
reads it, requires a `run_id`, a matching receipt under `a1/receipts/`, audit
evidence, and that the declared `{path: sha256}` map matches the PDFs in the
directory exactly. A dry run that rewrites it destroys the evidence that a
real generation completed.

**Fixed.** A dry run now writes nothing: the simulated manifest and QA report
are printed to stdout, and the `output_dir.mkdir()` call moved into the
production branch so a dry run cannot even create the tree.
`tests/test_langgraph_a1_orchestrator.py` asserts the output tree is
byte-identical after a dry run, that a missing tree is not created, and that
the published manifest is untouched.

The manifest that the defect overwrote was restored from the in-tree
preserved copy of the 2026-09-16 canonical run (`run_id eb257cfb-…`, receipt
status `completed`); the restored file is 8183 bytes, mode 0600 and
byte-identical to
`output/provisional/5214b64f-7646-4764-8dde-cd95ed30d6c7/generation_manifest.json`.
The discovery inventory's 2026-09-17 record of the same file (8183 bytes,
mode 0600) matches. The exact bytes of the earlier 2026-09-08 manifest are
not recoverable: no surviving copy describes the current root PDFs, which
are a legacy mixed set including two V6-path orphans.

### 4.4 The environment did not match the declared contract

`config/agent_ops_workflow.v1.json` declares `langgraph-checkpoint-sqlite
3.1.1` and its pinned requirements file lists it, but it was not installed in
the venv — `langgraph-checkpoint-postgres` was installed instead and declared
nowhere. All 37 agent-ops tests failed at setup with
`ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'`, and
`test_pinned_experiment_dependencies` failed with
`PackageNotFoundError`.

**Resolved.** `langgraph-checkpoint-sqlite==3.1.1` was installed from the
already-pinned repository file. The suite then passes.

The remaining inconsistency is that `langgraph-checkpoint-postgres 3.1.2` is
installed and used by the A1 orchestrator but declared in neither pinned
file. It should be added to a pinned file for the orchestrator's own
experiment, so the orchestrator's dependency set is as reproducible as the
agent-ops one.

## 5. Known limits of this layer

| Limit | Detail |
|---|---|
| **A1 resume is a stub** | `--resume` prints "Full checkpoint resume requires database implementation" and exits 0. A successful exit for a no-op is the wrong contract: an operator told "resuming" would believe the run continued. The capability is proven elsewhere — the agent-ops suite covers durable resume, fault recovery and revocation on resume — so only the A1 wiring is missing |
| **No test for the A1 orchestrator's production path** | the new tests cover dry-run purity and the state schema. The production branch calls `generate_provisional_a1.py` and `a1_quality_gate.py` and is not covered end to end |
| **The agent-ops suite is slow** | 176.67s for 37 tests, because each test builds a graph, compiles it and round-trips a SQLite checkpoint. It is an isolated experiment and does not gate the main suites, but it should not be run on every commit |
| **Tracing must stay off** | the workflow sets `LANGSMITH_TRACING=false` and `LANGCHAIN_TRACING_V2=false` in `graph()`. Tracing must not be enabled for real data: an LLM-observability trace of a real case would carry PII into a third-party service |
| **LangGraph is not a licence for a second renderer** | a graph may call the core; a graph that re-implements `build_form_data` creates a second source of truth for the form |

## 6. Key rules

1. **The core is always the source of truth.** LangGraph calls the core, not
   the other way round.
2. **The core has no LangGraph imports.** It stays testable without it, and
   the main `requirements.txt` stays free of it.
3. **LangGraph workflows are optional.** Deployment does not require them.
4. **Research outputs go to `research/`**, not to production data.
5. **A dry run writes nothing.** A run that touches the protected tree is a
   production run, whatever it is called.
6. **Every dependency of an experiment is declared in a pinned file** that
   names the version, so the environment can be reconstructed from the
   repository rather than from memory.
7. **A checkpointer is not a resume.** Durable state and a working resume
   path are two different things; the agent-ops workflow has both, the A1
   orchestrator has only the first.
