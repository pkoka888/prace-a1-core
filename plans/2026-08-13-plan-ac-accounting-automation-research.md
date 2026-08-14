# Plan AC — Accounting and Invoice Automation Research

**Status:** active
**Prerequisite:** Coordinated with Plans P/N/O/J/H/M. Evidence collection proceeds in parallel; implementation is specialist-gated.
**Milestone:** M1B+research; later certified implementation
**Owner:** product engineering + Czech/German accounting specialists
**Lane:** Parallel non-blocking M1B+ research/design
**Current blocker:** Live capture and skill activation are blocked until Capture/Proposal
Integrity 1.3, a new immutable synthetic replay, and this plan's evidence, review,
and safety gates pass. Offline contract repair remains active and does not block
Release 1A.

## Objective

Design evidence basis for Czech/German invoice processing, accounting, and automation workflows. This is a discovery-only phase; definitive bookkeeping, tax calculations, and real invoice ingestion are NOT authorized here—those await specialist certification and appropriate gating.

## Scope

- Market, workflow, and architecture evidence collection (NOT implementation)
- Vendor/product capability analysis
- OSS project technical assessment
- Legal/regulatory constraints identification
- Cost/benefit estimation basis

## Work

1. **Czech-market vendor cohort** (minimum 10 records per subgroup):
   - Invoice/accounting software vendors and platforms
   - Accounting firms offering automation services
   - Individual accountants, consultants, and OSVČ-oriented offerings

2. **OSS document/invoice tooling cohort** (minimum 10 projects):
   - Invoice parsing/extraction projects
   - OCR/document automation frameworks
   - Czech language support assessment

3. **Evidence corpus** (minimum 10 studies/comparisons):
   - Czech/German accounting automation studies
   - Market statistics and benchmarks
   - Legal/tax compliance frameworks

4. **Skills and frameworks audit**:
   - Research-orchestration frameworks
   - ADR approaches for accounting decisions
   - Skill repositories for evidence synthesis

5. **Capability mapping**:
   - Received-invoice processing (extraction, validation, accounting entry)
   - Issued-invoice generation (templates, taxes, PDFs)
   - Approvals, corrections, payments, matching
   - Archive, audit trails, integrations, exports

6. **Experimental workflow validation**:
   - Pilot 1: repeatable public/synthetic evaluation of at least 10 OSS tools
   - Pilot 2: repeatable public/synthetic evaluation of at least 10 Czech products
   - External comparative benchmark against independent research systems, with
     claim-level evidence and blinded review

## Current checkpoint — benchmark quarantined

`research/benchmark-experimental/` is a repair fixture with status
`draft-invalid-for-scoring`. Its validator must return exit `2` while evidence,
independent reviews, sealed-holdout replacement, runner isolation, and factual
scoring remain unproven. It must not be used to rank systems, activate the skill,
or authorize Plan AD. A status edit alone cannot make it scoring-ready; readiness
must be derived from the complete schema, evidence, review, safety, and leakage
gates.

A preparation-only manual comparator package now exists under
`research/benchmark-experimental/comparative-runs/` for ChatGPT Deep Research,
Gemini Deep Research, Perplexity Research, and a source-bounded NotebookLM
control. Its manifests fail closed unless an operator records the exact product/
model/date, an already-included or verified-free interactive access basis, zero
incremental cost, no paid API/fallback, privacy attestations, and input/output
hashes. It contains no gold or holdout payload and executes no provider. This
preparation does not weaken the benchmark's exit-2 quarantine; no comparison may
run until the evidence/reviewer/holdout gates make the benchmark scoring-ready.

The CLI capability verifier is governed by Plan L. Its reports may document tool
availability for a research run but are not research evidence and cannot make an
AC claim verified.

## Current checkpoint — first public collection run

The first provisional collection run is present as five isolated raw lanes and a
derived candidate envelope. It contains 51 entities and 151 claim-linked evidence
records: 10 OSS projects, 10 Czech products, 10 Czech accounting-automation
services, 10 distinct OSVČ-oriented offerings, and 11 studies/statistical sources.
The normalized and scored candidates validate against research-model 1.2 and the
collection-completeness gate passes all five quotas. The generated pilot cockpit
is `docs/prototypes/research-cockpit/pilot-all.html`.

This is **collection-complete, not pilot-accepted**. The explicit review gate
currently fails because none of the 51 entities has an operator review. A bounded
live URL pass reached 80 of 84 unique URLs; four official documentation/OECD URLs
returned HTTP 403 and remain `unproven`, not invalid. At that dated checkpoint a
second collection was still pending; the later sections supersede this with the
completed repeat and atomic experiments. Human claim/citation review and a
controlled repeat remain required before either pilot can pass.

An independent second collection is stored under
`research/acquisition/repeat-2026-08-14/` and validates as a separate v1.2
candidate. The two core pilot rosters reproduce exactly (10/10 OSS and 10/10 Czech
products), but the collectors used different claim fields and source selections,
so claim-level reproducibility remains unproven. The broader firm, individual, and
study lanes selected complementary, non-overlapping entities. The deterministic
comparison at `research/processed/reproducibility-report.json` records these
differences without treating agreement as factual correctness. This satisfies the
second **collection**, not the two accepted pilot runs required by Exit.

The next repeatability checkpoint uses the frozen atomic query pack at
`research/query-packs/plan-ac-core-1.0.json`. Every OSS and Czech-product entity
must answer the same complete field set with explicit unproven states and
same-entity/same-field evidence. Critical, noncritical, and pricing agreement are
measured separately; matching unproven answers cannot pass the critical gate.
The two earlier prose-oriented collections remain provenance and must not be
retrofitted through semantic/model matching. Two fresh atomic runs are required.

`scripts/generate_research_review_queue.py` provides a deterministic,
non-authoritative operator work queue bound by hashes to its candidate and query
pack. It leaves every verdict blank and cannot modify canonical research data.
Queue v1.1 deduplicates source-integrity work by public HTTPS URL while keeping
exact claim-to-evidence/source-task links and usable canonical entity links.
Completed decisions belong in a separate exact-coverage response bound to the
queue hash and checked by `scripts/validate_research_review_response.py`; that
check performs no candidate import or authority promotion. Queue generation and
response validation are preparation for human review, not accepted review evidence.

Two independent v1.0 atomic collections are preserved at
`research/acquisition/atomic-run-{a,b}-2026-08-14.json`, each covering the exact
10+10 roster and all 190 required fields. Their blank operator queues are
hash-bound under `research/review/`. The deterministic comparison at
`research/processed/atomic-reproducibility-report.json` is diagnostic only:
generic applicability, prose/list detail, mutable GitHub snapshots, and matching
unresolved values distort its blended percentages. There were no direct
true-versus-false contradictions; 66/90 critical slots were proven in both runs,
24 had a coverage/status gap, and Updesk pricing remained a genuine source
conflict. No completed operator response exists, so neither run is accepted.

The v1.1 query pack is frozen at
`research/query-packs/plan-ac-core-1.1.json`. It introduces controlled
field-specific states, splits correction/approval and API/intake/integration,
uses structured pricing and controlled systems/formats/customer segments,
requires exact run provenance and claim confidence, and reports resolved
agreement, evidence coverage, conflicts, confidence/applicability differences,
valid N/A, and snapshot drift separately. Because this changes question
semantics and value shapes, two fresh independent v1.1 collections are required.
V1.0 records must not be automatically transformed and presented as independent
v1.1 evidence.

Two fresh v1.1 collections are now preserved as
`research/acquisition/atomic-v1.1-run-{e,f}-2026-08-14.json`, bound to query-pack
hash `69ea1e988271dafaaea0ea84cc75e6eac8ad7c884ec4f66212ce57a3a68a3819`.
Both cover the exact 20-entity roster and all 230 fields. Run E conservatively
marks 20 results proven and 210 unproven; Run F records 150 proven, 69 unproven,
10 not applicable, and one source conflict. Their comparison at
`research/processed/atomic-v1.1-reproducibility-report.json` therefore reports
only 20/90 critical slots resolved in both, 47 critical coverage differences,
23 critical slots unproven in both, and no resolved semantic contradiction.
The result fails structural repeatability, independently attested provenance,
and the acceptance signal. Hash-bound blank review queues contain 300 and 303
tasks under `research/review/`; no operator response exists. This is a valid
failed repeatability experiment and review-preparation checkpoint, not a passed
pilot. Its main finding is that source-discovery coverage is not yet repeatable.
Run E is retained as a diagnostic low-recall collection rather than silently
rewritten: an audit found many official facts its generic page inspection missed.
Run F requires an immutable correction for Fakturoid's published VAT-inclusive
price display. The comparison now binds the exact result and query-pack bytes and
passes its read-only freshness check. A content-aware third collection and
completed human responses are required before re-evaluation.

The content-aware third collection, Run G, covers all 230 fields with 138
proven, 82 unproven, and 10 not-applicable results; its 305-task blank queue is
current. Compared with Run F, 53/90 critical slots are resolved and semantically
matching, 17 have a coverage difference, and 20 remain unproven in both. The
comparison has no resolved semantic conflict, but still fails structural
repeatability and acceptance; collector identities are not operator-attested.
This raises the pairwise F/G critical-coverage statistic from 22.2% to 58.9%,
but the collector configurations differ, so it does not demonstrate controlled
repeatability or satisfy either pilot. The immutable audit errata at
`research/acquisition/atomic-v1.1-errata-2026-08-14.json` binds Runs F/G and
records the known pricing and evidence-link defects without rewriting either
run. Human review must address those findings and the remaining critical gaps.
The next controlled experiment must freeze one collector protocol/configuration
and execute two new runs with the same configuration digest, distinct execution
IDs, and operator-attested collector identities before comparison.

That protocol is now frozen at
`research/query-packs/plan-ac-collector-protocol-1.0.json`, with configuration
digest `5e7f6068904c19a64d71812120aee4f0f53e58289b617049b2fe86b4ab052caf`.
Runs H/I may execute from it with distinct agents/models, but their identities
remain unverified until the operator attests the recorded provenance.

Runs H/I have now executed with that identical digest and complete 230-slot
coverage. Run H records 40 proven, 180 unproven, and 10 not-applicable results;
Run I records 0 proven, 220 unproven, and 10 not-applicable. Their byte-bound
comparison resolves none of the 90 critical or 120 noncritical slots in both;
only the ten pack-valid OSS pricing N/A slots resolve. This controlled run pair
therefore fails repeatability even more clearly. It demonstrates that a shared
prose protocol and digest do not make field-evidence classification deterministic
across agents. Do not launch another blind collection pair: first freeze reusable
source captures and field-level extraction/decision fixtures, then test collectors
against those identical inputs before returning to live-source repetition.

The executable-collector repair is split into three bounded packages: (1) a
collector-execution schema/validator binding implementation, prompt/config/tool
versions, fetch manifests, and one field inspection per slot; (2) a safe bounded
public-source capture layer with response/excerpt hashes and redirect provenance;
and (3) a deterministic 2-OSS/2-vendor synthetic field-decision replay. These
must pass adversarial tests before any Run J or full 10+10 recollection begins.

The first implementation of all three packages is present: the collector
execution validator enforces exact 230-slot inspection and source/capture hashes;
the capture tool produces immutable bounded-excerpt manifests with public-HTTPS
and redirect/DNS protections; and the synthetic 2+2 replay covers eight field
decisions with exact-byte checking. These are tooling proofs only. They require
adversarial integration review and a capture-to-inspection mini-pilot before the
next live full-roster run. The second repair freezes collector protocol v1.1 at
digest `93911210a90f9a8d1d3e26f46a30043041e8c5c627616cea3f34c28b554724da`,
binds exact capture excerpts and typed observations, preserves source inspection
for unproven fields, and limits exit 0 to synthetic-fixture or hash-bound operator
authority. Lexical anchoring is only an anti-fabrication check, not semantic proof.

Canonical offline mini-pilot v2 now executes a deterministic collector runner
from a clean workspace, creates 20 synthetic captures and all 230 collector
slots, validates that execution, and regenerates the focused 2-OSS/2-vendor
eight-case replay. Its exact-set manifest directly inventories the capture
manifest, 20 excerpts, collector execution, and all inputs; clean-room hashes
match the canonical artifacts. Its authority is `synthetic_fixture_verified`:
this can close only the offline executable plumbing/replay proof and is not
evidence for any vendor, repository, market claim, collector identity, or
live-source repeatability.

An independent adversarial re-audit accepts this **offline synthetic tooling
gate only**: 58 focused tests pass and no critical/high tooling defect remains.
The proof is same-environment; interpreter/dependency versions are not yet part
of the manifest. Subsequent capture/collector repairs changed three bound scripts
without regenerating the immutable proof, so its current manifest is stale and
the repository-wide hash regression fails. Treat the earlier pass as a dated
checkpoint; a clean-room successor must be regenerated only after Integrity 1.3
is frozen. Plan AC, both live pilots, and the skill remain provisional.

The first bounded live capture now covers exactly Docling, invoice2data,
Fakturoid, and ÚčtoRobot across ten claim-targeted official-source requests.
Eight excerpts were captured and hash-validated; two remain honestly unproven
because the requested terms were absent or did not fit the 500-character bound.
Capture therefore exits 2, as designed. No market claim is accepted from capture
alone; the next artifact is a complete 230-slot `collector_proposed` execution
whose validator must also remain exit 2 pending operator review.

The first live proposal execution covers all 230 slots with four proposed
supports and 226 `does_not_establish` states. Its exact check passes and authority
validation correctly exits 2. Audit accepts the two MIT SPDX observations but
rejects the checkpoint as an evidence-classification gate: one capture can be
laundered across unlisted same-entity fields, the two Fakturoid lists omit named
items while appearing exhaustive, and 216 uncaptured fields are mislabeled as
inspected. Preserve this execution as diagnostic. Before a new live mini-pilot,
version the contracts to carry exact field targets, distinguish `not_inspected`,
record enumeration scope, and bind every normalized proposal to a reviewed
mapping-rule ID. Lexical anchoring remains necessary but cannot perform semantic
classification alone.

Capture contract v1.1 now carries exact query-pack `{entity_id, field_id}`
targets through every result and rejects root/path normalization ambiguity.
Normalization rules v1.0 are bound to the same pack and provide proposal-only,
operator-review-required mappings for the bounded SPDX, API, extraction,
currency, accounting-system, and export-format cases. Collector execution v1.2
has been implemented as a proposal scaffold and distinguishes `not_inspected`,
but an independent adversarial audit rejected it. The collector does not yet
revalidate the bound capture request/result, excerpt hashes and sizes, redirect
and allowed-root semantics, or the frozen collection window. Disposable tests
showed that modified excerpt bytes, a rebound attacker URL, and a 1999 retrieval
timestamp could still produce `proven` slots. Its pricing path can also promote
the isolated token `Kč` to a proven `CZK` result without a structured amount,
tier, VAT state, billing period, or unit. No persisted v1.2 live execution exists.

The next mandatory checkpoint is **Capture/Proposal Integrity 1.3**. It must bind
and semantically revalidate the exact request, capture result, redirect chain,
allowed source roots, immutable excerpt bytes/hash/size, run interval, and exact
observation spans; use structured pricing values; disable or explicitly attest
proxy behavior; and reproduce then reject every demonstrated bypass. First pass
must be a new immutable synthetic v1.2→1.3 integration artifact. Only after that
passes may a fresh bounded live 2+2 proposal be collected. The current v1.2 files
are repair candidates, not pilot evidence or an accepted collector contract.

One advisory cross-model review was run through OpenCode 1.18.18 using the
runtime-listed free `opencode/deepseek-v4-flash-free` model and only the public
v1.0 pack/report. Its useful metric criticisms agreed with the deterministic
audit, but it also made incorrect provenance/evidence assumptions. The sanitized
manifest at `research/processed/model-advisory-run-2026-08-14.json` records both;
the model output is not evidence or authority.

## Evidence States

All evidence must be marked:
- `provisional` for evidence collected during research phase
- `primary-source-verified` for vendor documentation
- `operator-verified` for workflow testing
- `specialist-verified` for tax/legal constraints

Self-reported vendor claims are recorded with `confidence: unverified` unless independently corroborated. Undisclosed OSS use is recorded as `not_publicly_disclosed`.

## Exit

The evidence corpus and capability matrix are complete, both pilots pass on two
repeatable runs, and the repaired external benchmark passes its evidence,
review, leakage, safety, and reproducibility gates. Skill activation is a
separate Plan L governance decision after those results; it is not automatic.
No outcome authorizes tax calculations or real invoice processing. The portal
scaffold does not wait for this plan; payroll remains inactive until independently
specialist-certified.

## Exclusions

- No real invoices, employee records, or PII
- No tax calculation implementation
- No authoritative bookkeeping system
- No production invoice ingestion
- No payment processing integration
