---
name: market-research-evidence
description: Deterministic market, workflow, and architecture research with evidence tracking for invoice accounting automation. Uses local inputs, read-only external research, primary sources first, no paid APIs, no credentials in outputs.
---

# Market Research Evidence Collection

## Scope

Czech/German invoice/accounting automation evidence gathering for Plan AC. Research-only phase — NOT implementation authority. No tax calculations, bookkeeping, or real invoice processing.

## Authority and reading order

1. **Read [`AGENTS.md`](../../../AGENTS.md) first.** It is the binding authority for PII handling, secrets, git staging, and provider/cost policy. This skill is subordinate to it.
2. Then read the active plan ([Plan AC](../../../plans/2026-08-13-plan-ac-accounting-automation-research.md)) and the AD sibling ([Plan AD](../../../plans/2026-08-14-plan-ad-invoice-ingestion-foundation.md)).
3. Only then use the scripts and contracts below.

## Input/Output contract

- **Raw inputs**: `research/acquisition/raw/<lane>.json` — one file per lane (OSS, Czech software, Czech accounting firms, Czech individual, studies). These are written by the collector or imported from verified subagent records.
- **Canonical envelope**: `research/processed/entities.json` — the normalized, validated run envelope.
- **Schema**: `research/schemas/research-model-1.2.json` (sole active frozen version; v1.0/v1.1 are superseded and rejected by every command).
- **HTML cockpit**: `docs/prototypes/research-cockpit/index.html` — sortable/filterable, generated from the envelope.
- **Synthetic fixtures**: `research/synthetic/` (manifest `artifact_manifest.json`, invoices `invoices.json`, ground truth `ground_truth.json`).

## Collector semantics (important)

`scripts/collect_market_evidence.py` does **not** automatically research the web. It **initializes or imports raw lane records** into `research/acquisition/raw/`. Populated, verified records come from subagents or explicit fixtures; the collector never overwrites canonical processed output and never invents values.

## Output status

Normalized (`entities.normalized.json`) and scored (`scores.json`) outputs are **provisional** until the primary agent integrates them into the canonical envelope and a human review approves. Do not treat them as accepted evidence on their own.

## Deterministic scripts (implemented)

Twelve commands, all `--root`-aware:

1. `scripts/collect_market_evidence.py` — writes/imports raw lane envelopes; fixture-based, requires `--as-of`, never canonical.
2. `scripts/check_evidence_url.py` — read-only HTTP/HTTPS URL checking with allowlisting and `unproven` results (live mode optional).
3. `scripts/normalize_datasets.py` — merges raw lanes into the envelope, validates the candidate before exit 0, fails on missing IDs / invalid objects / unresolved conflicts.
4. `scripts/validate_research_schema.py` — JSON Schema validation against the frozen research-model schema plus an indexed relationship/state invariant pass; honors `--input`.
5. `scripts/check_research_completeness.py` — fixed policy quotas and required evidence coverage; derives counts from schema-valid entities.
6. `scripts/score_research_results.py` — deterministic scoring from documented evidence only; missing evidence yields `unproven`, never numeric zero.
7. `scripts/generate_research_cockpit.py` — static HTML with a safe non-executable data block, restrictive CSP, and a `--check` that validates schema, render freshness, and embedded digest/entity count.
8. `scripts/create_synthetic_benchmark.py` — generates synthetic Czech invoices (no real data) for OCR benchmarking.
9. `scripts/run_ocr_benchmark.py` — probes local engines; records `unproven` when unavailable.
10. `scripts/compare_research_runs.py` — compares two validated runs without treating agreement as truth.
11. `scripts/generate_research_review_queue.py` — creates/checks an immutable blank queue with exact input bindings and unique public-source tasks.
12. `scripts/validate_research_review_response.py` — validates a separate, exact-coverage human response; performs no import or authority promotion.

> Status: **experimental** until both Pilot 1 (OSS) and Pilot 2 (Czech products) pass and a fresh-agent forward test activates the skill.

### Current collector boundary

The offline synthetic capture→collector→replay proof is a tooling check only.
The first live v1.1 proposal is a retained failed diagnostic. The v1.2 proposal
scripts are also **repair-only**: adversarial testing showed missing capture
request/result, excerpt hash/size, allowed-root, timestamp, structured-pricing,
and proxy-policy bindings. Do not use them for a new live run or claim pilot
progress until Plan AC's Capture/Proposal Integrity 1.3 gate passes. Subagents may
audit public artifacts, but under `AGENTS.md` their implementation output is only
a proposal for primary-agent review.

## Evidence collection modes

- **Synthetic benchmark**: Use `research/synthetic/` fixtures
- **Public sources only**: Vendor sites, documentation, public GitHub repos
- **No paid APIs**: Free-tier only if provider allows
- **No credentials**: Never log/store API keys, tokens, passwords
- **Primary sources first**: Cite canonical documentation, not reposts

## Cohort requirements (Plan AC)

- Czech invoice/accounting software vendors: 10+ records
- Czech accounting firms & automation services: 10+ records
- Czech individual providers/OsvČ offers: 10+ records
- OSS invoice/document tools: 10+ records
- Czech/worldwide studies/benchmarks: 10+ records

## Missing values convention

Use exact tokens: `unknown`, `not_found`, `not_publicly_disclosed`, `not_reliably_exposed`. Never invent.

## Pinned upstream patterns

- GitHub API client: `requests` with `https://api.github.com/` static endpoint
- HTML generation: static file output; no local server required
- Schema validation: JSON Schema Draft-07 with `$ref` resolution
- Citation format: `[text](https://example.com/canonical-path)` with retrieval date

## Verification

Run `./venv/bin/python scripts/validate_research_schema.py --json` for machine output. Exit 0 = pass, 1 = failure, 2 = environment missing.

## Hand off

Report: cohort sizes, URL coverage, evidence quality score, any gaps or unverifiable claims, recommendation confidence per entity. All human corrections must be recorded with new retrieval date.
