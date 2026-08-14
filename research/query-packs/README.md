# Plan AC atomic query pack

`plan-ac-core-1.0.json` freezes the questions used by repeatable Pilot 1
(`oss_invoice`) and Pilot 2 (`czech_invoice_software`). A collector must answer
every field for every included entity, including explicit `unproven` answers;
it must not omit a field merely because no source was found.

Each lane also freezes its exact ten-entity roster. Atomic inputs with a missing,
additional, substituted, or cross-lane entity are invalid even when every
submitted entity has complete fields. Collectors must load the pack immediately
before producing a result and copy its current version and hash; they must not
reuse a hash captured before the roster or questions were finalized.

The pack hash is SHA-256 over compact, key-sorted UTF-8 JSON after removing the
top-level `query_pack_hash` member. Atomic result files bind both the semantic
version and this hash. Changing any question, field classification, comparison
rule, or vocabulary therefore requires a new pack version and hash.

Validate and compare two independently collected atomic result files with:

```bash
venv/bin/python scripts/compare_research_runs.py \
  --mode atomic \
  --query-pack research/query-packs/plan-ac-core-1.0.json \
  --left-results path/to/left.json \
  --right-results path/to/right.json \
  --output path/to/comparison.json
```

Exit `0` means structurally comparable, not factually correct. Critical,
noncritical, and pricing disagreements are reported separately. Missing fields,
unknown vocabulary values, stale pack hashes, and broken evidence ownership fail
with exit `1`. The legacy `--mode raw` lane comparison remains available for the
two pre-query-pack collections.

`critical_gate_passed` additionally requires every critical result in both runs
to be `proven`; matching `unproven`, `conflicted`, or `not_applicable` answers are
reported as agreement for transparency but remain unresolved and cannot pass the
gate.

## v1.1 collection contract

`plan-ac-core-1.1.json` supersedes v1.0 for future collection without rewriting
the two preserved v1.0 runs. It freezes canonical entity root URLs separately
from feature evidence and replaces ambiguous compound questions with atomic,
controlled fields. Native/backend Czech OCR, invoice extraction boundary,
correction versus approval, files versus named integrations, API versus
intake/synchronization, accounting systems versus formats, customer segments,
and issued-invoice creation versus dispatch are distinct facts.

Results use `atomic-results-1.1`. Every run records a distinct collector,
collection method, source-policy version, and start/completion timestamps. Every
piece of evidence has a retrieval timestamp and a public HTTPS URL. `proven`
means verified evidence supports the claim. Required `claim_confidence`
separately records whether support is an official/vendor self-description,
independent corroboration, or repository metadata. A reachable vendor page is
not independent confirmation.

Lists use controlled identifiers and state whether collection was complete for
the frozen sources or partial. Pricing is structured into disclosure, currency,
VAT, period, unit, and tier facts; prose remains a non-comparable note. Mutable
GitHub snapshots require exact timestamps.

The v1.1 comparator assigns every slot to exactly one primary outcome:
`semantic_match`, `semantic_conflict`, `coverage_difference`, `both_unproven`,
`resolved_not_applicable`, or `snapshot_drift`. Counts reconcile to
`total_slots`. Applicability and confidence differences are reported separately
and do not manufacture factual disagreement. Matching unknowns are never semantic
agreement, and mutable snapshot drift is not a contradiction.

Each frozen entity now carries an explicit `allowed_official_source_roots` list.
Evidence labelled official or repository metadata must fall under one of those
HTTPS path roots; evidence labelled independent must not. This prevents a
collector from turning an arbitrary reachable URL into apparently official or
independent support merely by changing an enum.

The pack also freezes a capture window. Collection start/completion, evidence
retrieval, mutable snapshots, and `as_of` must be consistent with that window.
Provenance records the collector kind, execution-instance ID, operator-attested
or unverified identity state, and a configuration digest. Merely changing a
free-text collector label is not proof of independence.

`structural_repeatability_passed` requires the complete frozen roster and no
critical semantic, coverage, unresolved, applicability, or confidence drift.
The separate `independence.verified` result requires two operator-attested,
distinct collector/execution identities running the same configuration digest.
`acceptance_signal_passed` additionally refuses critical facts supported only by
matching vendor self-report. Even that signal is not Plan AC acceptance:
`operator_acceptance` remains `not_evaluated` until a separately bound review is
performed.

The current v1.1 pack hash is
`69ea1e988271dafaaea0ea84cc75e6eac8ad7c884ec4f66212ce57a3a68a3819`.
Files bound to the former `6f03bf...` draft remain historical evidence and must
not be edited in place. A conforming run requires a genuine recollection against
the new root policy and capture window, the new provenance fields, and the new
hash. Because v1.1 changes semantics and value shapes, v1.0 runs likewise cannot
be converted and described as independent v1.1 recollections.
