# Provider safety extension

Deferred extension: no provider implementation during stabilization. Offline
read-only policy review may report findings; listed write scopes become available
only after stabilization acceptance and explicit integrator ownership.


Parent: PLAN-FREE-MODEL; FREE-VISION-1 through FREE-VISION-8. This is separate from
AF2 workload scoring and is not required for the first local document workflow.
Read the full child plan, current provider config and implementation sources using
secret-safe access; never read credential values or private scan paths into prompts.

Write scope: `src/free_model_eval/` policy/quota adapters only after checking current
ownership, new synthetic tests `tests/test_free_vision_provider_safety.py`,
`scripts/list_vision_models.py`, `config/vision_models.json`, and
`docs/research/opencode-provider-safety-2026-09-06.md`.
Do not edit .env, provider accounts, billing, root OpenCode config or system services.

Implement offline first: metadata-only discovery; exact endpoint/model eligibility;
fresh zero-price evidence; atomic quota reservations shared only for actual shared
upstream account/IP pools; workload tags for AF2 versus OCR; max-two independent
eligible pools; bounded retry_at/deferred state; sanitized receipts. Test prohibited
network dispatch with mock call assertions, not only string filters. Unknown cost
in a provider response is audit information, never fabricated zero or prior eligibility.

Preserve existing providers and direct adapter boundaries. LiteLLM is optional only
if it demonstrably simplifies routing without weakening free eligibility, privacy,
quota identity or tracing. No broad migration and no default paid fallback.

The user's direct MiniMax m3/m2.7 permission concerns OpenCode agent work; do not
silently add these models to the app's free vision allowlist. App OCR provider
eligibility still follows the free-vision child plan unless the user separately
changes that application policy. No live document/model tests in this work order;
first deliver offline proof and a concrete synthetic-only dispatch proposal.
