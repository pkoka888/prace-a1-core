# Plan 2026-09-06-FREE-VISION-PROVIDER-SAFETY — Free Vision Provider Discovery and Operational Safety

**Status**: planned
**Milestone**: M1A–M2
**Parent**: PLAN-FREE-MODEL

## Purpose

Implement bounded free-vision provider discovery and operational safety for the
OCR pipeline: remove paid/full-scan discovery paths, enforce exact endpoint/model
eligibility with fresh pricing evidence, scope quota pools to actual shared
upstream limits, allow independent pool attempts within the attempt budget,
and keep AF2 synthetic agent evaluation on a separate evaluation lane.

Replaces and extends the provider-safety portion of PLAN-FREE-MODEL.
AF2 synthetic agent evaluation (formerly AF2) remains a separate workstream
with independent quota reporting.

## Technical defaults (locked)

- Only free-tier endpoints authorized; exact endpoint/model required with fresh
  zero-price evidence per request
- OpenRouter always requires the exact `:free` suffix; a provider-level free tier
  must never admit the provider's paid models
- Live synthetic probes require actual preflight evidence of zero price; record
  unavailable pricing as unknown, never a fabricated `"0.00"`
- Preserve OpenRouter and Kilo. Use direct adapters initially; LiteLLM is a
  deferred transport substitution, not a prerequisite
- Local processing remains functional without external providers
- Default tests mock providers; live synthetic probes require explicit invocation

## Provider discovery scope

Provider **discovery** means: fetching provider model lists, pricing tiers,
free-tier endpoint availability, and capability metadata. Discovery does NOT
send document content, OCR input, or any pixel data to external providers.

## Dependencies

| Gate | ID | Reason |
|---|---|---|
| evidence-only | PLAN-INFRA | Operating model and architecture baseline bound evaluation |
| evidence-only | OCR-SHARED-CORE-LOCAL | Document core provides the OCR adapter interface |

## Tasks

### FREE-VISION-1: Audit and remove paid/full-scan paths

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- Code audit finds zero live paths that send document bytes to paid endpoints
- `config/free-model-eval/policy.json` contains only exact endpoint/model entries
  where the model ID ends with `:free` (OpenRouter) or the provider has a verified
  free-tier policy that excludes paid models
- Test suite `tests/test_vision_provider_safety.py`:
  - Mock test: attempt to send full scan to paid endpoint; assertion that
    request was never made (mock verifies zero calls)
  - Mock test: attempt to send full scan to free endpoint without metadata-only
    wrapper; assertion that raw bytes were not transmitted
- No string-rejection approach; tests prove the prohibition works

**Failure cases**:
- Mock test finds paid endpoint called → FAIL
- Mock test finds full scan bytes transmitted to any external provider → FAIL
- Tests rely on string matching instead of behavioral proof → FAIL

---

### FREE-VISION-2: Provider capability discovery

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- `VisionProviderRegistry.discover()` fetches provider model/pricing/capability
  metadata via a dedicated discovery adapter
- Discovery adapter sends only: provider endpoint URL, authentication token
  (if required), and the query `{"models": true}` or equivalent
- No document bytes, no OCR input, no pixel data transmitted during discovery
- Discovery response cached with TTL of 3600 seconds; cache key is provider
  name only (no document identifiers)
- Discovery adapter for each provider implements the `ProviderDiscovery` interface

**Failure cases**:
- Document content transmitted during discovery → FAIL
- Discovery cached without expiry → FAIL
- Cache key contains document identifier → FAIL

---

### FREE-VISION-3: Synthetic capability tests

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- `tests/test_vision_capability_synthetic.py` runs synthetic document crops
  (pre-authorized synthetic fixture set) against free-tier providers
- Tests use synthetic field crops, not real scans or employee records
- Each test records: provider, model, date, purpose, input_type ("synthetic_crop"),
  output_verdict, cost (actual price from provider response, or "unknown" if
  pricing unavailable), duration_ms
- Unit tests use mocked pricing to verify behavior without network calls
- Live synthetic probes: require explicit opt-in flag; preflight verifies free
  tier availability; if pricing cannot be confirmed, cost is recorded as unknown

**Failure cases**:
- Tests use real employee scan → FAIL
- Fabricated cost value used when pricing is unavailable → FAIL (record as unknown)
- Live probe runs without explicit opt-in flag → FAIL

---

### FREE-VISION-4: Exact endpoint/model eligibility

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- Eligibility check enforced at call time requires ALL of:
  1. Exact endpoint/model pair in `config/free-model-eval/policy.json`
  2. OpenRouter: model ID ends with `:free`; non-OpenRouter: provider has a
     verified free-tier policy document
  3. Fresh zero-price evidence: preflight call to the exact endpoint confirms
     the specific request is price-listed at zero
  4. Quota reservation succeeded (atomic reservation, see FREE-VISION-5)
- Pre-request eligibility: unknown or unavailable pricing at pre-request time
  means the request is not dispatched. Pricing "unknown" is a pre-flight
  failure, not a dispatchable outcome.
- Post-request reporting: after a successful free-tier request, if the provider
  does not report usage cost, the cost may be recorded as "unknown" for
  audit/reporting purposes. This does not retroactively authorize the request.
- No blanket provider-level free tier that admits paid models
- No model promoted from `unknown` to `approved` without passing synthetic
  capability test (FREE-VISION-3)

**Failure cases**:
- Model called without exact endpoint in policy → FAIL
- OpenRouter model without `:free` suffix called → FAIL
- Provider-level free tier admits the provider's paid models → FAIL
- Dispatch attempted when pricing is unknown or unavailable at pre-request time → FAIL

---

### FREE-VISION-5: Upstream quota pools scoped to shared limits

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- `src/free_model_eval/quota.py` tracks upstream provider quota:
  `daily_calls`, `daily_cost`, `daily_errors`, `rate_limit_remaining`
  per provider+endpoint key (not per model globally)
- Quota pools are scoped to the actual shared account/IP/model limits:
  - OpenRouter: shared account-level quota (all `:free` models share one account)
  - Kilo direct: shared IP-level quota
  - Future providers: scoped to their actual upstream limit structure
- AF2 workload and vision/OCR workload share the same pool only where they share
  the same upstream account/IP limit
- Atomic reservation: before every external call, `quota.reserve()` is called;
  if reservation fails (quota exhausted or rate limited), the call is not made
- Reservation is per-request; each page/document makes an independent reservation

**Failure cases**:
- External call made without quota reservation → FAIL
- AF2 and vision workloads use separate counters when they share the same upstream limit → FAIL
- Quota pool scoped too broadly (e.g., per-model when upstream limit is per-account) → FAIL

---

### FREE-VISION-6: Bounded retry and independent pool attempts

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- On 429 or quota exhaustion: attempt another independently eligible free pool
  within the overall attempt budget (max 2 provider pools attempted per request)
- If all eligible pools are exhausted: defer the task (mark as `deferred`);
  deferred tasks are re-queued after backoff interval (configurable, default 300s)
- "Fallback" means retrying the same exhausted pool; this is prohibited.
  "Independent pool attempt" means trying a different provider/pool that is
  independently eligible — this is permitted within the attempt budget
- Exhaustion event logged: timestamp, provider, model, reason ("429" | "quota_exhausted"),
  action ("independent_pool_attempt" | "deferred"), pools_remaining, retry_at
- No fallback to paid model under any circumstance
- Task marked `failed` only on unrecoverable error; quota exhaustion always defers

**Failure cases**:
- Paid model called → FAIL
- Same exhausted pool retried without new quota → FAIL (must defer)
- Independent pool attempt counted as fallback → FAIL
- Task marked `failed` when quota is exhausted → FAIL (must defer)

---

### FREE-VISION-7: Sanitized audit

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- Audit log entry for every external call: timestamp, provider, model,
  input_type ("synthetic_crop" | "real_document"), output_verdict,
  cost (actual price string from provider, "0.00", or "unknown"),
  duration_ms, reservation_id, workload_tag ("af2" | "vision")
- No employee identifiers, real names, document bytes, or field content in audit log
- Audit log readable by operator without PII exposure
- Audit log structured (JSON) and queryable

**Failure cases**:
- Employee identifier in audit log → FAIL (PII breach)
- Document bytes in audit log → FAIL (PII breach)
- Audit log not structured or queryable → FAIL

---

### FREE-VISION-8: AF2 separate evaluation lane

**Owner**: primary agent; Codex integrates and accepts

**Acceptance evidence**:
- AF2 evaluation (synthetic receipt review, code draft, trace protocol) runs
  under `tests/test_free_model_eval_af2_*`
- AF2 uses the same quota pool structure but reports independently:
  `workload_tag: af2` vs `workload_tag: vision`
- AF2 evaluation does not determine OCR provider eligibility
- AF2 test isolation: AF2 tests mock their own external calls unless running
  live probes with explicit opt-in; when live AF2 probes run, they decrement
  the shared upstream quota pool
- AF2 cost reported separately in audit log for attribution

**Failure cases**:
- AF2 tests bypass the quota pool mechanism → FAIL
- AF2 results used to determine OCR provider eligibility → FAIL
- AF2 running with real employee data → FAIL

---

## Completion criteria

| Criterion | Evidence |
|---|---|
| No paid model called | `tests/test_vision_provider_safety.py` mock verifies zero paid calls |
| Exact endpoint/model required | Only entries with confirmed free-tier pricing in policy |
| Discovery is metadata-only | Zero pixel data transmitted during capability discovery |
| Fresh pricing evidence | Cost from actual provider response or recorded as unknown |
| Quota pools scoped to actual limits | Shared account/IP scope verified per provider type |
| Independent pool attempts within budget | Max 2 provider pools attempted; exhausted → deferred |
| AF2 lane separate | Audit records distinguish workload_tag |

## Exit evidence

Free-vision evaluation uses exact endpoint/model pairs with verified free-tier
pricing. No paid discovery paths and no full-scan external transmission.
Quota pools are scoped to actual upstream account/IP limits. Independent pool
attempts are permitted within the attempt budget; exhausted pools defer, not fail.
AF2 and vision workloads share quota where they share upstream limits, with
independent reporting. Audit logs are operator-readable without PII exposure.
