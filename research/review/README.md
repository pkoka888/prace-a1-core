# Plan AC operator review handoff

The generated queue is an immutable, non-authoritative work assignment. It is
bound to the exact atomic result and query-pack bytes and contains blank operator
fields only. Generate or check it with:

```bash
venv/bin/python scripts/generate_research_review_queue.py \
  --input research/acquisition/atomic-run-a-2026-08-14.json \
  --query-pack research/query-packs/plan-ac-core-1.0.json \
  --output research/review/atomic-run-a-queue.json --check
```

Queue v1.1 has one entity task per frozen-roster entity, one claim task per
atomic field result, and one source-integrity task per unique public HTTPS URL.
Claims list every evidence ID and link to the corresponding source-task IDs.
Entity tasks use the proven `canonical_repository` or `canonical_product_url`
result for their public link and display name.

Both frozen atomic formats are supported. With `atomic-results-1.0`, entity
identity comes from the legacy canonical-URL result. With
`atomic-results-1.1`, it comes from the pack's frozen `canonical_root_url` and
the queue preserves schema-validated collection provenance, structured values
(including pricing), claim confidence, applicability, enumeration scope,
capture timestamp, and evidence metadata. Loader dispatch follows the declared
pack/result format pair and cross-version pairs fail closed. Source-integrity
tasks are deduplicated by exact public HTTPS URL while each evidence ID remains
linked to exactly one source task. Operator fields always remain blank.

Do not enter decisions into the queue. Record a completed review in a separate
JSON file conforming to `review-response.schema.json`. It must repeat every task
ID exactly once and bind the queue's exact path, version, and SHA-256. Then run:

```bash
venv/bin/python scripts/validate_research_review_response.py \
  --queue research/review/atomic-run-a-queue.json \
  --input path/to/completed-response.json
```

A pass proves only structural completeness, current queue binding, controlled
verdicts, a review time after the bound collection (and not in the future), and
offline public-HTTPS safety for replacement links. It performs no
import, does not modify research candidates, and cannot change evidence, plan,
skill, or decision authority. Independent review quality and Plan AC acceptance
remain separate gates.
