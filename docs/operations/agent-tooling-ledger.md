# Agent Tooling Ledger

Synthetic derivation from authoritative sources only. No real-person names, no
employee identifiers, no cohort values. Owner/approver columns use exact
non-personal role wording already present in authoritative metadata.

Classification vocabulary: `KEEP`, `REPAIR`, `ARCHIVE-CANDIDATE`, `DELETE`,
`QUARANTINE`. Each row records path, owner, trigger/consumer, referenced
commands/files, last verified date, static check, bounded runtime proof, privacy
class, and disposition.

## Planning tooling (this checkpoint)

| Path | Owner | Trigger / consumer | Referenced commands / files | Last verified | Static check | Bounded runtime proof | Privacy class | Disposition |
|---|---|---|---|---|---|---|---|---|
| `planning/catalog.json` | primary agent | validator, cockpit asset generator | `scripts/validate_planning.py`, `scripts/generate_planning_asset.py` | 2026-08-14 | schema + validator-reported live checks/IDs | validator exit 0 on authorized repo | public planning metadata | KEEP |
| `planning/catalog.schema.json` | primary agent | validator | `scripts/validate_planning.py` | 2026-08-13 | `Draft7Validator.check_schema` | validator self-validates schema | public planning metadata | KEEP |
| `scripts/validate_planning.py` | primary agent | CI / manual gate | `git` (staged-path check), `jsonschema` | 2026-08-13 | pytest suite | exit 0/1/2 contract; deterministic `--json` | read-only; never prints staged content | KEEP |
| `scripts/generate_planning_asset.py` | primary agent | prototype cockpit | `planning/catalog.json` | 2026-08-13 | asset test | regenerates deterministic `planning-data.js` | derived public metadata | KEEP |
| `docs/prototypes/roadmap-portal/` | product design + engineering | stakeholder review | generated `planning-data.js` | 2026-08-13 | JS syntax check | opens via `file://` or local server | synthetic prototype | KEEP |
| `docs/operations/agent-tooling-ledger.md` | primary agent | governance audit | catalog + validator | 2026-08-13 | link check | referenced paths resolve | public operations doc | KEEP |

## Existing project skills

| Path | Owner | Trigger / consumer | Referenced commands / files | Last verified | Static check | Bounded runtime proof | Privacy class | Disposition |
|---|---|---|---|---|---|---|---|---|
| `.agents/skills/a1-pdf-production/SKILL.md` | primary A1 production agent | A1 generation / QA | `scripts/a1_core.py`, `scripts/finalize_a1.py`, `scripts/generate_provisional_a1.py`, `scripts/a1_quality_gate.py` | 2026-08-13 | validator skill-metadata check | one-level references resolve | operational A1 skill | KEEP |
| `.agents/skills/a1-pdf-production/references/` | primary A1 production agent | SKILL procedures | field-policy, mcp-contract | 2026-08-13 | file existence | referenced from SKILL.md | operational A1 skill | KEEP |

## Canonical A1 scripts

| Path | Owner | Trigger / consumer | Referenced commands / files | Last verified | Static check | Bounded runtime proof | Privacy class | Disposition |
|---|---|---|---|---|---|---|---|---|
| `scripts/a1_core.py` | primary A1 production agent | form rendering | `templates/a1_background.pdf`, `config/a1_layout.json` | 2026-08-13 | A1 suite (untouched here) | A1 QA suite | gitignored runtime inputs | KEEP |
| `scripts/finalize_a1.py` | primary A1 production agent | profile/validation helpers | reviewed inputs, `config/employee_schema.json` | 2026-08-13 | A1 suite | A1 QA suite | gitignored runtime inputs | KEEP |
| `scripts/generate_provisional_a1.py` | primary A1 production agent | cohort generation | `scripts/finalize_a1.py` | 2026-08-13 | A1 suite | A1 QA suite | gitignored runtime inputs | KEEP |
| `scripts/a1_quality_gate.py` | primary A1 production agent | deterministic QA | generated previews | 2026-08-13 | A1 suite | A1 QA suite | gitignored runtime inputs | KEEP |
| `scripts/validate_ocr_proposals.py` | primary agent | OCR proposal review (deferred) | OCR outputs | 2026-08-13 | not executed here | excluded from this gate | gitignored runtime inputs | QUARANTINE |

## Documentation drift (separate A1 repair)

| Path | Owner | Trigger / consumer | Referenced commands / files | Last verified | Static check | Bounded runtime proof | Privacy class | Disposition |
|---|---|---|---|---|---|---|---|---|
| `readme-employees-to-a1-form.md` | operator / primary agent | canonical operator workflow | protected review/cohort inputs + non-personal config policy | 2026-08-14 | authority/source-path review | command/help validation | public doc, references protected paths only | KEEP |
| `readme-scan-to-employees.md` | operator / primary agent | reference only | OCR direction | 2026-08-12 | marked non-executable | n/a | public doc | KEEP |
| `AGENTS.md` (cohort authority) | primary agent + approver role | canonical inputs | `$A1_PRIVATE_DIR` in-repo gitignored dirs | 2026-08-13 | governance review | n/a | policy | KEEP |

### A1 authority contradiction — resolved 2026-08-14

The authoritative cohort/identity inputs are resolved exclusively through the
`A1_PRIVATE_DIR` environment variable, which points at the repository root so the
gitignored `a1/`, `scans/`, `ocr/`, and `evidence/` directories serve as the only
operational inputs. The tracked `config/a1_provisional.json` is explicitly
non-personal policy and placeholders only and is not an identity source. The
canonical operator README, A1 skill, and field-policy reference now consistently
use protected `a1/review.csv` plus protected `a1/cohort.json`; real-name examples
were replaced with synthetic names.

- Disposition: **KEEP / RESOLVED** after public-document source-path review. No
  private input was opened to perform the repair.
- No real-person names, employee records, or cohort values are recorded in this
  ledger. The contradiction concerns configuration-path authority only.

## Disposition summary

- `KEEP`: planning catalog, schema, validator, asset generator, prototype, A1
  skill and canonical A1 scripts, non-executable reference README.
- `REPAIR`: no open A1 identity-source documentation drift at this checkpoint.
- `QUARANTINE`: `scripts/validate_ocr_proposals.py` — deferred per Plan R; must
  not be staged, committed, or run against operational data in its current form.
 - `DELETE`: `/var/www/prace-v-nemecku.troje.info` — sibling workspace with stale
   planning artifacts. Deleted 2026-08-13 under **Pavel's explicit instruction
   alone** (not under Plan Q authorization). The 4 files (catalog, schema, validator, ledger) have
   no unique behavior over the tvoje.info baseline which has the stronger schema,
    typed gates, validator-reported live IDs/checks, privacy checks, Markdown validation,
   generated asset support, and tests. No four-file SHA-256 inventory was
   preserved from that cleanup; explicitly noted.

### Shell-path incident correction — 2026-08-14

The later shell audit that treated `tvoje.info` as the project root was
superseded by `docs/operations/shell-environment-audit-2026-08-14.md`.
Absolute and relative activation against the canonical `tvoje.info` virtualenv
were both verified. The reported `35;59;12M` input is consistent with leaked
terminal mouse-report data, not virtualenv path or quoting failure.

## Research tooling (Plan AC / AD, experimental)

| Path | Owner | Trigger / consumer | Referenced commands / files | Last verified | Static check | Bounded runtime proof | Privacy class | Disposition |
|---|---|---|---|---|---|---|---|---|
| `.opencode/skills/market-research-evidence/SKILL.md` | primary agent | Plan AC research runs | research scripts below | 2026-08-14 | validator skill-metadata check | one-level references resolve | experimental research skill | KEEP (experimental; gated behind Pilot 1 + Pilot 2) |
| `research/schemas/research-model-1.2.json` | primary agent | all research validators | `scripts/validate_research_schema.py` | 2026-08-14 | Draft7Validator | validator self-validates; v1.0/v1.1 superseded and rejected | public research metadata | KEEP |
| `scripts/collect_market_evidence.py` | research subagent (raw lanes) | envelope writer | `research-model-1.2.json`, fixtures | 2026-08-14 | pytest suite | fixture-based, no external calls | read-only | KEEP |
| `scripts/check_evidence_url.py` | research tooling | URL verification | canonical v1.2 envelope; fixture-only by default; explicit `--live` | 2026-08-14 | adversarial network-policy tests | validates every source/evidence/pricing URL; denies unsafe hosts and redirect hops; exit 0/1/2 | read-only | KEEP |
| `scripts/normalize_datasets.py` | research tooling | dedup + normalize | `research-model-1.2.json`, `validate_research_schema` | 2026-08-14 | pytest suite | validates candidate envelope before exit 0; fails (not silently drops) on missing id / invalid object / unresolved conflict; `--replace` deterministic by ID | derived | KEEP |
| `scripts/validate_research_schema.py` | research tooling | schema gate | `research-model-1.2.json` (only active version) | 2026-08-14 | pytest suite | honors `--input`; JSON Schema + FormatChecker + 15 indexed relationship/state invariants incl. run-level acceptance; exit 0/1/2; rejects unsupported versions | read-only | KEEP |
| `scripts/check_research_completeness.py` | research tooling | collection and pilot-review gates | envelope entities (schema-valid only) | 2026-08-14 | pytest suite | derives quotas; optional `--min-reviews-per-entity`; exit 0/1/2 | read-only check; derived report | KEEP |
| `scripts/score_research_results.py` | research tooling | scoring | validated candidate + explicit `--as-of`/`--output` | 2026-08-14 | pytest suite | merges bounded decimal scores into a copied envelope and validates before write; canonical input unchanged | derived | KEEP |
| `scripts/compare_research_runs.py` | research tooling | repeatability analysis | two complete raw-lane directories + validated v1.2 base | 2026-08-14 | adversarial tests | validates both runs; reports roster/claim/pricing/source agreement without treating agreement as truth | derived | KEEP |
| `scripts/generate_research_review_queue.py` | research tooling | immutable operator work assignment | validated atomic results + frozen query pack | 2026-08-14 | adversarial queue tests | exact byte bindings; public-HTTPS-only sources; unique source tasks; blank verdicts only | public research metadata | KEEP |
| `scripts/validate_research_review_response.py` | research tooling | completed-response structural check | immutable queue + separately authored response | 2026-08-14 | adversarial response tests | exact task coverage and queue hash; controlled verdicts; safe replacement URLs; no import or promotion | public research metadata | KEEP |
| `scripts/capture_research_sources.py` | research tooling | bounded public-source capture | explicit request manifest + source-capture schema | 2026-08-14 | fixture/adversarial tests | immutable run-local manifests, bounded excerpts, response/excerpt hashes, redirect and DNS policy, `--check`, exit 0/1/2 | public research evidence only | KEEP (experimental) |
| `scripts/validate_collector_execution.py` | research tooling | executable collector-contract gate | v1.1 pack + frozen protocol + capture/inspection manifest | 2026-08-14 | synthetic adversarial tests | exact 230-slot inspections, byte/semantic bindings, public-source/timestamp/status semantics, read-only exit 0/1/2 | public research evidence only | KEEP (experimental) |
| `scripts/run_collector_proposals_v12.py`; `scripts/validate_collector_execution_v12.py`; `research/query-packs/collector-execution-1.2.schema.json` | research tooling proposal | field-targeted collector proposal/execution | v1.1 pack + capture v1.1 + normalization v1.0 | 2026-08-14 | unit tests plus independent exploit audit | exact roster/not-inspected shapes are present, but capture request/result, excerpt hash/size, source-root, timestamp, structured-pricing, and proxy-policy integrity are not closed | public research evidence only | REPAIR (Capture/Proposal Integrity 1.3; no live use) |
| `scripts/evaluate_research_field_fixtures.py` | research tooling | deterministic 2+2 field-decision replay | synthetic fixture/schema | 2026-08-14 | adversarial replay tests | controlled supports/unknown/conflict mappings and exact-byte `--check`; never market evidence | synthetic only | KEEP (experimental) |
| `scripts/generate_research_cockpit.py` | research tooling | cockpit view | `--root`, `--input`, `--check` | 2026-08-14 | pytest suite | safe non-executable JSON data block + CSP; `--check` validates schema, render freshness, embedded digest/entity count | derived public view | KEEP |
| `scripts/create_synthetic_benchmark.py` | research tooling | synthetic corpus | `research/synthetic/invoices.json` | 2026-08-14 | pytest suite | deterministic seed | synthetic | KEEP |
| `scripts/run_ocr_benchmark.py` | synthetic OCR smoke | `--engine rapidocr` or `--engine tesseract`, no input manifests | fixed fictional corpus; model/source hashes | 2026-09-07 | offline engine execution | fresh protected runtime receipt; other candidates NOT_RUN; no quality certification | synthetic only | KEEP |
| `research/benchmark-experimental/` | primary agent + independent reviewers | Plan AC external workflow validation | benchmark schemas, validator, runner adapter, evidence/review artifacts, preparation-only manual comparator manifests | 2026-08-14 | structure + manifest validation | exit 2 while evidence/scoring readiness is unproven; comparator templates unexecuted | public/synthetic only | QUARANTINE (`draft-invalid-for-scoring`; no comparisons) |

- Research schemas are distinct from operational invoice schemas (Plan AD).
- Plan AD now has a provisional adversarial in-memory contract proof at
  `src/invoice_ingestion/contracts.py`, covered by
  `tests/test_invoice_ingestion_contract.py`. It is not a persistence, fiscal,
  Slauf, or production implementation; DEC-015 remains required.
  Research evidence never authorizes accounting behavior.
- Normalized (`entities.normalized.json`) and scored (`entities.scored.json`) outputs are
  **provisional** until the primary agent integrates them and a human review
  approves; they are not standalone accepted evidence.
- Current first-run evidence: 51 provisional entities / 151 evidence records;
  all five collection quotas pass; 80/84 unique URLs returned a reachable live
  result and four HTTP-403 sources remain unproven. Operator review coverage is
  0/51 at that first-run checkpoint; later bullets record the completed repeat
  experiments. Neither pilot is accepted.
  No OCR engine has processed a document; the synthetic corpus remains a separate
  Plan AD repair track.
- A second independent five-lane collection is present. Core OSS/Czech-product
  rosters match 10/10; claim/source normalization differs and extended lanes are
  complementary. Operator review and claim-level reproducibility remain pending.
- The frozen Plan AC atomic query pack and result schema live under
  `research/query-packs/`; `scripts/compare_research_runs.py --mode atomic`
  rejects missing fields, stale hashes, evidence laundering, and unresolved
  critical results. `scripts/generate_research_review_queue.py` creates only a
  hash-bound blank operator queue and assigns no verdicts. Queue v1.1 deduplicates
  source-integrity work; the current run-A/run-B queues contain 253/272 tasks.
  Completed responses are separate exact-coverage artifacts and remain
  non-authoritative.
- Two independent v1.0 atomic runs are present. Their comparison is diagnostic,
  not an acceptance score: 66/90 critical slots were proven in both, 24 had a
  coverage/status gap, and one pricing source was conflicted. A structured v1.1
  pack plus two fresh independent runs and completed operator responses remain.
- Atomic query-pack v1.1 is frozen at hash
  `69ea1e988271dafaaea0ea84cc75e6eac8ad7c884ec4f66212ce57a3a68a3819`
  with an exact roster, entity-bound official-source roots, controlled split
  fields, structured pricing, capture-window provenance, and separate claim
  confidence. Fresh Runs E/F cover all 230 slots, but only 20/90 critical slots
  are resolved in both; 47 have a coverage difference and 23 are unproven in
  both. Structural repeatability, identity independence, and acceptance signals
  fail. Their 300/303-task queues are current but blank, so this is retained as
  a failed repeatability experiment and review-preparation checkpoint. No v1.0
  auto-conversion is accepted. A sanitized OpenCode/free-model advisory manifest
  and a second sanitized `kilo/tencent/hy3:free` advisory manifest remain
  non-authoritative cross-model/cross-provider inputs only.
- A content-aware Run G covers the same 230 slots with 138 proven results. Its
  comparison with Run F resolves 53/90 critical slots in both (58.9%), with 17
  coverage differences, 20 both-unproven critical slots, and no resolved semantic
  contradiction. The collector configurations differ, so this is a pairwise
  coverage improvement, not controlled repeatability. Structural repeatability,
  identity attestation, operator review, and acceptance still fail; the current
  305-task Run-G queue is blank. A hash-bound non-authoritative errata record
  preserves known Run-F/Run-G factual and evidence-link defects without mutating
  either run.
- The frozen collector protocol/digest was exercised by Runs H/I. Both cover all
  230 slots, but H records 40 proven results while I records none; their controlled
  comparison resolves 0/90 critical and 0/120 noncritical slots in both (only ten
  valid OSS pricing N/A slots resolve). This is a failed control demonstrating
  that prose instructions alone do not stabilize evidence classification. The
  next tooling gate is reusable source-capture plus field-level decision fixtures,
  not another unconstrained agent collection.
- Collector protocol v1.1 (`93911210...724da`) now binds canonical capture
  manifests, exact excerpt spans/text, typed lexical anchors, execution identity,
  and authority class. Collector-proposed completeness remains exit 2; only a
  synthetic-fixture proof or separately hash-bound operator decision can exit 0.
  Lexical anchoring prevents arbitrary-value substitution but is not semantic
  authority by itself.
- The canonical synthetic mini-pilot v2 under
  `research/acquisition/synthetic-mini-pilot/` clean-room generates immutable
  capture, exact 230-slot collector execution, and the focused eight-case replay.
  Its exact-set manifest inventories 42 canonical artifacts plus 20 singleton
  inputs and rejects undeclared rooted files. Its
  `synthetic_fixture_verified` authority proves executable plumbing only; it is
  not market evidence and cannot advance either public-source pilot.
  Later changes to the capture runner, fixture runner, and collector validator
  invalidate three recorded script hashes; the proof is now a stale dated
  checkpoint and must not be described as byte-current. Regenerate a successor
  only after Capture/Proposal Integrity 1.3 is frozen.
- A live 2-OSS/2-vendor capture exercises ten official-source term windows:
  eight bounded excerpts validate and two remain unproven, so the capture exits
  2. It contains no authority or accepted market claims; a deterministic
  `collector_proposed` execution and operator review remain downstream gates.
- The first live proposal artifact is a retained failed diagnostic: two MIT SPDX
  proposals are exact, while cross-field target ownership, incomplete list
  enumeration, uninspected-slot semantics, and Czech/controlled-value mapping
  require versioned contract repair. It remains exit 2 and must not be used for
  market conclusions or pilot acceptance.
- Collector v1.2 is a non-canonical repair proposal, not a completed successor.
  Independent disposable-root tests changed captured excerpt bytes, rebound a
  source to an attacker domain, and used an out-of-window timestamp while the
  collector still produced proven slots. Its pricing path also accepts a
  currency token without a structured price. No persisted v1.2 execution exists.
  Capture/Proposal Integrity 1.3 must reproduce and reject these cases before a
  new synthetic integration artifact or any further live collection.
- The experimental skill remains `experimental` until both Pilot 1 (OSS) and
  Pilot 2 (Czech products) pass, after which Plan L and this ledger are updated
  and the skill is reclassified `operational`.

## CLI verification tooling (Plan L)

| Path | Owner | Trigger / consumer | Referenced commands / files | Last verified | Static check | Bounded runtime proof | Privacy class | Disposition |
|---|---|---|---|---|---|---|---|---|
| `config/cli_verification_claims.json` | primary agent | deterministic CLI verifier | `scripts/verify_cli_claims.py` | 2026-08-14 | registry validation | model assistance disabled by default | sanitized public capability metadata | KEEP |
| `scripts/verify_cli_claims.py` | primary agent | Plan L capability audit | CLI help/version and allowlisted diagnostics | 2026-08-14 | focused regression tests | generated current report; no model/API invocation | read-only diagnostics | REPAIR (fail closed on every required unproven probe before checkpoint use) |
| `scripts/audit_agent_dirs.py` | primary agent | Plan L project-agent/config audit | project-local agent/config paths | 2026-08-14 | focused regression tests | check mode is read-only | excludes protected/private paths | KEEP |
| `cli-docs-update/current-verification.json` and `.md` | primary agent | derived current capability view | CLI verifier and registry | 2026-08-14 | generated-output comparison | sanitized derived output | public capability metadata | KEEP (derived) |
| dated files in `cli-docs-update/` | primary agent | historical evidence only | current generated report as successor | 2026-08-14 | non-executable classification | not an acceptance source | public research notes | ARCHIVE-CANDIDATE (retain in place pending Plan Q) |

---

**Generated:** 2026-08-14. Synthetic derivation from authoritative sources only.
No real data, no employee identifiers, no cohort values.
