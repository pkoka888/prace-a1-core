# Codex, OpenCode, and Free-Model Orchestration Study

**Status:** recommendation for bounded synthetic trials; no provider or production
activation is authorized by this document.
**Reviewed:** 2026-08-15
**Scope:** reduce expensive-context use during complex repository work while
preserving Codex as the authority, integrator, and final verifier.
**Companion:** provider inventory, per-model strengths/weaknesses, rate limits,
privacy/training matrix, and task-fit guidance ("where free models dominate /
recommended / avoid") live in
`docs/research/2026-08-15-free-model-provider-comparison.md`; see also the gaps
it fills against this study.

## Executive decision

Adopt a **Codex-led hybrid** if the synthetic trials pass:

1. Codex owns goals/plans, decomposition, protected-data boundaries, acceptance
   criteria, integration, and final review.
2. OpenCode runs bounded, disposable worker jobs against an explicit allowlist of
   free models. Workers receive a small task packet and return files or a
   structured report; they do not receive the full Codex conversation.
3. Start by calling providers directly through OpenCode. Introduce the existing
   loopback LiteLLM gateway only after trials show a real need for centralized
   fallback, quotas, routing, or usage telemetry.

This saves Codex context only when delegation is artifact-based. Starting another
agent with the complete conversation merely copies the context cost. Each worker
should receive paths, a bounded question, constraints, acceptance command, and an
output schema—not the whole planning history.

## Verified local facts

Read-only checks on 2026-08-15 established:

- Codex CLI `0.147.0` supports non-interactive `exec`, review, profiles, explicit
  model choice, sandbox selection, and local OSS providers through Ollama or LM
  Studio.
- OpenCode `1.18.18` has configured credentials for OpenRouter, Z.AI, Nvidia,
  Kilo Gateway, two MiniMax endpoints, and `free-models`. No keys were printed.
- The runtime model catalog advertised these OpenCode-hosted free candidates:
  `opencode/deepseek-v4-flash-free`, `opencode/hy3-free`,
  `opencode/laguna-s-2.1-free`, `opencode/mimo-v2.5-free`, and
  `opencode/nemotron-3-ultra-free`.
- Kilo advertises a free router and several free endpoints, but `.kilo/` is a
  separate quarantined tool surface and is not part of the first trial.
- A service listens on loopback `127.0.0.1:4000`, consistent with the previously
  reported LiteLLM gateway. Its configuration, ownership, authentication, and
  provider routes were not inspected and remain unproven.

Advertised models and stored credentials do not prove availability, zero price,
privacy suitability, tool support, or acceptable quality. Only canary results can
promote a candidate.

## Three candidate architectures

### 1. Codex-native orchestration only

Codex uses its own plans/goals and bounded subagents, selecting a smaller Codex
model or lower reasoning effort for routine work and a frontier Codex model for
architecture, integration, and high-risk review.

**Advantages:** one permission model; strongest integration with repository
instructions; clean task steering and synthesis; least operational complexity.

**Disadvantages:** this does not use third-party free inference; native Codex
subagents are Codex models, not arbitrary OpenCode providers. OpenAI API Codex
models do not have a free API tier, so API use must not be described as free.

**Best use:** final plans, security/privacy decisions, cross-package integration,
hard debugging, acceptance review, and any task involving ambiguous authority.

**Gap mitigation:** use lower-cost/faster Codex variants and lower reasoning only
after representative evals; keep prompts lean; delegate only independent bounded
workstreams; persist conclusions in repository artifacts instead of relying on a
single long conversation.

### 2. Codex-led OpenCode worker pool — recommended first trial

Codex writes a small JSON/Markdown task packet. A wrapper invokes `opencode run`
with an explicitly named model and a restricted agent. The worker can be
read-only for research/review or write only to a dedicated scratch/worktree path
for code drafts. Codex reads the returned artifact, reruns deterministic tests,
and either accepts, repairs, or rejects it.

**Advantages:** uses the providers already configured; OpenCode supports per-agent
models, subagents, maximum-step limits, and granular permissions; no additional
gateway is required; failures are isolated; context transfer is controllable.

**Disadvantages:** free-model availability and quality drift; inconsistent tool
calling and patch discipline; rate limits; multiple providers see prompts;
potential hidden context expansion by the worker; Codex must still verify every
result.

**Gap mitigation:** fixed model allowlist rather than a random router for coding;
read-only default; deny external directories, secrets, Git writes, network, and
subagent spawning unless a trial needs them; cap steps and wall time; use
synthetic fixtures only; require structured receipts and deterministic acceptance
commands; record the actual returned model; never auto-promote worker output.

### 3. Codex-led OpenCode through LiteLLM

OpenCode connects to an OpenAI-compatible model alias exposed by the existing
loopback LiteLLM proxy. LiteLLM owns provider credentials, aliases, retry/fallback,
quotas, and usage metadata. Codex remains the external orchestrator and verifier.

**Advantages:** one local endpoint; centralized routing and rate limits; provider
fallbacks without changing worker prompts; virtual keys and per-project budgets;
consistent logs and model aliases.

**Disadvantages:** another security- and reliability-critical service; fallback
can silently change model behavior; the existing instance has unknown ownership
and policy; telemetry may capture prompts; Responses/tool semantics may differ
across providers; it does not make paid models free.

**Gap mitigation:** sysadmin-owned configuration; loopback only; dedicated virtual
key and zero monetary budget for the trial; explicit aliases with no paid
fallback; content logging disabled or redacted; returned provider/model recorded;
health checks and fail-closed timeouts; pin gateway version/config; do not share
the host-wide gateway until tenant isolation is proven.

## Why not use the random free router for coding

OpenRouter's `openrouter/free` selects a compatible free model at random. It is
useful as a low-risk research fallback, but it makes coding evals and regression
reproduction weaker because model identity and behavior can change between runs.
OpenRouter also documents low free-model limits and variable availability. Use a
specific `:free` model for a scored trial; consider the random router only for
non-authoritative brainstorming with the returned model recorded.

Provider privacy is also not uniform. Free routing must remain limited to public
repository content and synthetic data, with provider training/data-policy
settings reviewed before activation.

## Proposed model policy for implementation

| Work class | Default | Escalate when |
|---|---|---|
| Authority, architecture, security, final integration | frontier Codex, medium/high reasoning | evidence conflicts, high blast radius, or repeated failed reviews |
| Bounded repository exploration and independent review | fast/lower-cost Codex or read-only free OpenCode candidate | incomplete evidence or cross-cutting interpretation |
| Mechanical code/test draft with exact interfaces | best canary-passing named free OpenCode model | tests fail twice, patch crosses scope, or reviewer finds semantic errors |
| Bulk formatting, inventories, deterministic generation | scripts first; model only for exceptions | ambiguity requires judgment |
| Protected/private/real data, production, Git publication | Codex plus existing human gates | never delegated to free external models in the initial policy |

The key optimization is not “free model everywhere.” It is **scripts for
deterministic work, cheap workers for bounded drafts, Codex for judgment and
integration**.

## Initial synthetic trial

Run this as a separate, reversible Plan L experiment. Do not activate a project
skill or automatic orchestration yet.

1. Create a read-only OpenCode worker with `edit`, external-directory access,
   Git mutation, and unsafe shell commands denied. Disable conversation sharing.
2. Select two named free models from the live catalog. Do not use Kilo or the
   random router in the first comparison.
3. Give both models the same three synthetic tasks:
   - locate and summarize a small public code path with exact citations;
   - propose a patch for a deliberately broken fixture and return unified diff;
   - add a small test in an isolated temporary worktree and run one allowlisted
     test command.
4. Compare against a fast Codex baseline using task success, unsupported claims,
   diff correctness, tests, tool-policy violations, latency, input/output tokens,
   retries, and actual model/provider.
5. Repeat each task at least three times. A candidate is eligible only if it has
   zero permission violations, zero secret/private-path access, reproducible
   structured output, and an agreed success threshold on code and evidence.
6. Only then test LiteLLM with one explicit free-only alias and no fallback. Add
   fallback only after the single-model path is observable and fail-closed.

### Promotion gates

- **Research worker:** may be promoted after citation accuracy and privacy gates.
- **Code-draft worker:** additionally requires clean patches and deterministic
  tests across repeated runs.
- **Autonomous writer:** not proposed. Codex must review and integrate outputs.
- **Automatic router/skill:** only after repeated trials, a frozen config schema,
  receipts, timeouts, and rollback instructions.

## Recommended orchestration state

Use Codex Plan mode to freeze the experiment specification and exact files. Use a
Codex goal only after the experiment has deterministic gates and is expected to
span multiple sessions. The durable state should be the plan, task packets,
receipts, and eval results in Git—not hidden conversation state in either tool.

## Primary sources

- OpenAI, [Model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- OpenAI, [Codex use cases](https://developers.openai.com/codex/use-cases)
- OpenAI, [GPT-5-Codex API model](https://developers.openai.com/api/docs/models/gpt-5-codex)
- OpenCode, [Agents](https://opencode.ai/docs/agents)
- OpenCode, [Permissions](https://opencode.ai/docs/permissions)
- OpenCode, [Providers](https://opencode.ai/docs/providers)
- LiteLLM, [Getting started and proxy overview](https://docs.litellm.ai/)
- OpenRouter, [Free Models Router](https://openrouter.ai/docs/guides/routing/routers/free-router)
- OpenRouter, [FAQ and free-model rate limits](https://openrouter.ai/docs/faq)
- OpenRouter, [Provider routing and data-policy controls](https://openrouter.ai/docs/guides/routing/provider-selection)

