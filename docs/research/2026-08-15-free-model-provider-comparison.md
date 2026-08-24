# Free-Model Providers and Coding Candidates — Comparison Study

**Status:** research context only; nothing in this document authorizes provider or
production activation. Follow `AGENTS.md`, `docs/security/real-data-rules.md`, and
the approved ADRs. The companion orchestration study is
`docs/research/2026-08-15-codex-opencode-free-model-orchestration.md`; this
document fills its provider-model and task-fit gaps.
**Reviewed:** 2026-08-15
**Scope:** every provider currently configured in OpenCode on this host, their
current models as advertised in the live catalog, what each is strong and weak
at, and where free-model use dominates, is recommended, or must be avoided.

## Verified local facts (read-only)

- Credentials exist in `~/.local/share/opencode/auth.json` for: `openrouter`,
  `zai`, `nvidia`, `kilo`, `minimax`, `minimax-cn`, `free-models`. Only provider
  names were inspected; no key values.
- `~/.config/opencode/env` exports `OPENROUTER_API_KEY` and `MINIMAX_API_KEY`
  (key values not printed).
- Live `opencode models` catalog (2026-08-15) advertises these OpenCode-hosted
  free candidates: `opencode/big-pickle`, `opencode/deepseek-v4-flash-free`,
  `opencode/hy3-free`, `opencode/laguna-s-2.1-free`, `opencode/mimo-v2.5-free`,
  `opencode/nemotron-3-ultra-free`, `opencode/nemotron-3.5-lightning-free`.
- The same catalog lists dozens of `openrouter/*:free` endpoints and a large
  paid roster for `openrouter`, `zai`, `nvidia`, `kilo`, `minimax`,
  `minimax-cn`.
- The loopback `127.0.0.1:4000` listener is present (consistent with the
  previously reported LiteLLM gateway). Ownership, configuration, and routes
  remain unverified and are out of scope for the first trial.
- Catalog claims and stored keys prove neither availability, zero price,
  privacy suitability, tool support, nor acceptable quality. Only canary
  results can promote a candidate.

## Gaps identified in the orchestration study

The orchestration study answers *how* to delegate, but leaves several
provider/model questions open. This document addresses each numbered gap.

1. **No per-provider free-tier model inventory.** The study names the seven
   configured credential providers but not their current free-model rosters.
   Section "Provider inventory and current models" below lists what is live.
2. **No per-model context/output limits.** Free endpoints often cap context
   below the paid model (e.g. Laguna S 2.1 free is 256K/32K; DeepSeek V4 Flash
   free on Zen is 200K/128K). Section "Model comparison table" records the
   advertised limits from the live catalog.
3. **No privacy/training matrix.** For this PII-heavy repository this is the
   most important gap. Free endpoints frequently train on prompts or retain
   them: OpenCode Zen free models state data "may be used to improve the
   model"; NVIDIA free endpoints are trial-only and log usage; Laguna S 2.1
   free states inputs/outputs may be used for training; DeepSeek stores data in
   China with training on by default. Section "Privacy and retention matrix"
   consolidates this.
4. **No rate-limit table.** OpenRouter free tier is ~50 requests/day (free
   account) or ~1,000/day after $10 of credits, at 20 RPM. Kilo free models are
   limited to 200 requests/hour per IP. MiniMax free/Starter accounts run
   ~20 RPM / 1M TPM. NVIDIA grants a free credit allowance (1,000–5,000
   credits, ~40 RPM). Section "Rate limits" records these.
5. **No "where free models dominate vs where to avoid" guidance.** The study
   has a work-class table but not a task-fit analysis. Section "Task-fit
   guidance" below is the missing analysis.
6. **Model naming/drift risk not quantified.** `:free` models rotate and are
   removed without notice; the "opencode/*-free" set is explicitly
   limited-time. The study says to record the returned model; this document
   adds that catalog snapshots must be timestamped because prices, limits, and
   availability move weekly.
7. **The LiteLLM listener** is verified present but its ownership/config is
   unverified; the study already treats it as out of scope for the first trial.
   No change.

## Provider inventory and current models

### OpenRouter (`openrouter`)

Aggregator; thousands of models behind one OpenAI-compatible API. Paid models
bill at provider rates with a small platform margin; `:free` variants cost $0
in tokens but are rate limited.

Current free (`:free`) endpoints visible in the live catalog include:
`cohere/north-mini-code:free`, `google/gemma-4-26b-a4b-it:free`,
`google/gemma-4-31b-it:free`, `liquid/lfm-2.5-2.6b:free`,
`nvidia/nemotron-3-nano-30b-a3b:free`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`,
`nvidia/nemotron-3-super-120b-a12b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`,
`nvidia/nemotron-3.5-content-safety:free`, `nvidia/nemotron-3.5-lightning:free`,
`nvidia/nemotron-nano-12b-v2-vl:free`, `nvidia/nemotron-nano-9b-v2:free`,
`openai/gpt-oss-20b:free`, `poolside/laguna-s-2.1:free`,
`poolside/laguna-xs-2.1:free`, plus the random `openrouter/free` router.

**Strong at:** breadth of choice; one key; per-provider routing controls
(`data_collection`, `zdr`, `order`, `allow_fallbacks`); cheap paid access to
models like DeepSeek V4 Flash, Hy3, GLM, Qwen, Nemotron at low per-token cost.

**Weak at / risks:** free model identity and availability change between runs;
the random router is non-reproducible; free endpoints sometimes carry reduced
context windows; provider-level data policies differ (some train on prompts);
failed free-tier requests still count against the daily quota; no free API
tier for OpenAI Codex models.

**Best fit:** research collection, exploration, one-off drafts, and
cheap-volume paid access; use explicitly named `:free` models for anything
scored, record the returned model.

### Z.AI (`zai`)

First-party Zhipu/AI GLM endpoint. Live catalog models: `glm-4.5`, `glm-4.5-air`,
`glm-4.5-flash`, `glm-4.6`, `glm-4.7`, `glm-4.7-flash`, `glm-4.7-flashx`,
`glm-5`, `glm-5-turbo`, `glm-5.1`, `glm-5.2`, plus vision variants (`glm-4.5v`,
`glm-4.6v`, `glm-5v-turbo`).

- `glm-4.7-flash` and `glm-4.5-flash` are **free** on the official API
  (input, cached input, output all $0).
- `glm-4.7` is the value champion (~$0.60 in / $2.20 out per 1M, 200K context),
  with 73.8% SWE-bench Verified — among the best open-model coding results.
- `glm-5.2` is the flagship (~$1.40 / $4.40, 1M context, 128K output).
- GLM Coding Plan is a flat subscription (Lite $18 / Pro $72 / Max $160 per
  month) with per-window prompt quotas.

**Strong at:** coding and tool use for the price; multi-turn agentic work with
interleaved/preserved thinking; cheap paid tier; MIT-licensed open weights (up
to GLM-5.2); strong value in agent frameworks (Claude Code, Cline, Roo, Kilo).

**Weak at / risks:** documented long-context degradation beyond ~100K tokens on
GLM-4.7 (forgetfulness, mixing Chinese/English, tool-call mis-formatting);
tool calls emitted inside thinking blocks caused parse failures in OpenCode;
privacy policy was unreachable (404) as of August 2026 — the "no storage"
claim could not be verified; no published SLA; free flash models are subject
to rate limits.

**Best fit:** cheap paid coding drafts and agent work where context stays under
~100K; free flash for bulk research/summarization with synthetic/public data.

### NVIDIA (`nvidia`)

First-party NVIDIA NIM endpoints via build.nvidia.com. Free developer tier:
1,000 inference credits on signup (up to 5,000 on request), ~40 requests/min,
no credit card. Some endpoints are fully free ("Free Endpoint" filter), others
consume credits. The live catalog includes `nemotron-3-ultra-550b-a55b`,
`nemotron-3-super-120b-a12b`, `nemotron-3.5-lightning-30b-a3b`,
`nemotron-3-nano-30b-a3b`, plus DeepSeek, Qwen, Gemma, Llama, and embedding
models. Nemotron 3.5 Lightning (30B-A3B) and several others show $0 cost on
models.dev for the NVIDIA provider.

**Strong at:** open Nemotron family; 1M-context Nemotron 3 Ultra (free endpoint
on OpenRouter, 1M ctx / 128K out on Zen); Lightning is a fast, efficient
high-throughput agent model; permissive OpenMDW-1.1 license; OpenAI- and
Anthropic-compatible APIs; embedding/rerank/OCR/speech models useful for the
portal later.

**Weak at / risks:** free endpoints are explicitly **trial use only — do not
submit personal or confidential data**; usage is logged for security and to
improve NVIDIA products; Nemotron models are reasoning/orchestration-focused,
not top-tier coders (Nemotron 3 Ultra ~56 on Terminal-Bench 2.1; Lightning
~24); free credit allowance, not unlimited.

**Best fit:** read-only research, exploration, summarization, reasoning-heavy
analysis on synthetic/public data; local NIM for privacy-sensitive work later
(no data leaves the host).

### Kilo (`kilo`)

Kilo AI Gateway, an OpenAI-compatible aggregator. Free models (tagged `:free`)
cost $0; anonymous and authenticated free usage is rate limited to
**200 requests/hour per IP**. Free roster visible locally includes
`tencent/hy3:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`,
`nvidia/nemotron-3.5-lightning:free`, `poolside/laguna-s-2.1:free`,
`poolside/laguna-xs-2.1:free`, plus `openrouter/free` and `kilo-auto/*` router
tiers. Supports BYOK (bring your own key) and microdollar usage tracking.

**Strong at:** one key for hundreds of models; free usage with predictable
per-IP hourly cap; `kilo-auto/free` deterministic-affinity router; tool
calling with repair; no markup on paid usage.

**Weak at / risks:** some free models require allowing data collection; free
model roster rotates as partnerships change; `kilo-auto/free` model identity
is session-dependent (not reproducible for evals); `.kilo/` is a separate
quarantined tool surface in this repository and is excluded from the first
trial.

**Best fit:** high-volume free research/exploration; fallback lane when
OpenRouter is rate-limited; not for scored evals without pinning an exact
model ID.

### MiniMax (`minimax` / `minimax-cn`)

First-party MiniMax API. `minimax` is the international endpoint
(platform.minimax.io), `minimax-cn` the China endpoint; both share the model
family. Live catalog: `MiniMax-M2`, `MiniMax-M2.1`, `MiniMax-M2.5`,
`MiniMax-M2.5-highspeed`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`,
`MiniMax-M3`.

- M2.5/M2.1/M2: ~$0.30 in / $1.20 out per 1M, 200K context. M2.5 scores
  ~80.2% SWE-bench Verified — Opus-class coding at a fraction of the price.
- M3: 1M context, same $0.30/$1.20 base (higher over 512K).
- Free/Starter accounts: ~20 RPM, 1M TPM; paid accounts up to 500 RPM / 20M TPM.
- Weights are fully open-sourced on Hugging Face.
- Recommended integration path is the Anthropic-compatible SDK/API.

**Strong at:** coding and agentic tool use per dollar (SOTA in class); low
output cost; highspeed variant for interactive work; open weights; simple
Anthropic/OpenAI-compatible integration.

**Weak at / risks:** free tier is very low throughput (20 RPM) and 1M TPM;
accounts default to account-lifetime retention with training (opt-out exists);
China/Singapore data residency unless EU endpoint selected; privacy
classification "RISKY" in third-party review; `minimax-cn` routes to China.

**Best fit:** cheap paid coding drafts once the free tier's RPM is exhausted;
open-weights local deployment for privacy later; not a first-trial free
candidate given throughput and privacy posture.

### OpenCode Zen free models (`opencode/*-free`, credential `free-models`)

OpenCode-hosted zero-cost candidates; currently `big-pickle`, `deepseek-v4-flash-free`,
`hy3-free`, `laguna-s-2.1-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`,
`nemotron-3.5-lightning-free`. These are free or promotional endpoints. The Zen
privacy page explicitly identifies some promotions as collecting data that may
be used to improve the model, and NVIDIA trial endpoints as unsuitable for
personal or confidential data. It does not establish one uniform rule for every
current `opencode/*-free` entry; unverified model-specific policy remains
unproven. Advertised context/output from the live OpenCode catalog:
`deepseek-v4-flash-free`
200K/128K, `laguna-s-2.1-free` 256K/32K, `nemotron-3-ultra-free` 1M/128K,
`nemotron-3.5-lightning-free` 262K/262K, `mimo-v2.5-free` 200K/32K,
`hy3-free` 190K/64K, and Big Pickle 200K context / 160K input / 32K output.
Other model names previously listed here were not present in the refreshed local
`opencode` namespace and must not be treated as locally available.

**Strong at:** zero-cost access to currently relevant open models (DeepSeek V4
Flash, Hy3, Laguna S 2.1, MiMo V2.5, Nemotron 3 Ultra/Lightning); US-hosted;
convenient single namespace in OpenCode; no extra gateway.

**Weak at / risks:** some free-period data may be used to improve models and
other model-specific terms are unverified;
rotation without notice; free variants have smaller context than paid (e.g.
DeepSeek V4 Flash free 200K vs 1M native); no published request quotas for the
`opencode/*-free` lane on this host yet.

**Best fit:** the primary first-trial candidates, exactly as the orchestration
study recommends — but only with synthetic/public content, read-only
permissions, and records of the returned model.

## Model comparison table (current advertised free candidates)

| Model | Params (total/active) | Advertised ctx / out (free lane) | License | Free lanes | Strengths | Weaknesses |
|---|---|---|---|---|---|---|
| DeepSeek V4 Flash | 284B / 13B MoE | Zen free 200K/128K; native 1M/384K | MIT (open) | OpenCode Zen free; cheap on OpenRouter/Zen | Agent-tuned (beats V4-Pro-Preview on agent suites); strong long-context; open weights; Responses API for Codex | Free-lane context capped; hosted API stores in China and trains by default; hallucination rate still high in independent tests; thinking mode default raises cost |
| Tencent Hy3 | 295B / 21B MoE | Zen live catalog: 190K / 64K | Apache-2.0 (open) | OpenRouter, Kilo, OpenCode Zen | Vendor/aggregator claims emphasize stable tool use and token efficiency; passed the first local factual canary | Newer model with limited independent coverage; violated the first canary's exact-output-format requirement |
| Poolside Laguna S 2.1 | 118B / 8B MoE | free 256K/32K; paid 1M/128K | OpenMDW-1.1 (open) | OpenRouter, Kilo, OpenCode Zen | Strong agentic coder in its weight class (70.2 Terminal-Bench 2.1; 78.5 SWE-Bench Multilingual tops published table); runs on a single DGX Spark at 4-bit | Free use trains on inputs/outputs; free lane caps 256K; no user-configurable thinking effort; mid-table vs frontier on hard benchmarks |
| Xiaomi MiMo V2.5 | open coding family | Zen free (unpublished ctx) | open | OpenCode Zen | Everyday coding in-class results; closes gap to frontier; MiMo-V2.5-Pro ~78.9 SWE-bench Verified, 68.4 Terminal-Bench 2.0 | Base V2.5 is a budget tier; Pro needed for frontier-adjacent results; smaller ecosystem |
| NVIDIA Nemotron 3 Ultra | 550B / 55B MoE | 1M / 128K (Zen); 1M/64K (OpenRouter free) | OpenMDW-1.1 (open) | OpenRouter, Kilo, OpenCode Zen, NVIDIA | 1M context; frontier reasoning/orchestration; planning and long-running agent workflows | Not a top coder (≈56 Terminal-Bench 2.1; Coding Index ~49th percentile); free endpoints trial-only, no personal/confidential data, logged |
| NVIDIA Nemotron 3.5 Lightning | 30B / 3B MoE | 262K / 262K | OpenMDW-1.1 (open) | OpenRouter, Kilo, OpenCode Zen, NVIDIA | Very fast, high-throughput agent workhorse; permissive license; strong gains over Nemotron 3 Nano on agentic benchmarks | Small; weak on hard coding (SWE-bench Verified ~51.6; Terminal-Bench 2.1 ~24.6); same trial/data caveats |
| GLM-4.7 Flash / 4.5 Flash (Z.AI) | open GLM family | 200K / 131K | open (up to 5.2) | Z.AI official (free) | $0 across input/output; 200K context; same family as 73.8% SWE-bench Verified GLM-4.7 | Rate-limited; GLM long-context degradation >100K; tool-call/thinking parse issues reported in agents; privacy page unreachable |
| GPT-OSS-20B (OpenRouter) | 20B | OpenRouter free | permissive | OpenRouter | OpenAI open-weights baseline; low-latency small model | Small; not competitive with the 100B+ open leaders for agentic coding |

## Rate limits (current, from provider docs)

| Provider / lane | Limit |
|---|---|
| OpenRouter `:free`, no credits | ~50 requests/day total, 20 RPM |
| OpenRouter `:free`, ≥$10 lifetime credits | ~1,000 requests/day, 20 RPM |
| Kilo free models | 200 requests/hour per IP (anonymous or authenticated) |
| MiniMax free/Starter | ~20 RPM, ~1M TPM |
| NVIDIA build.nvidia.com | ~40 requests/min; 1,000–5,000 free credits (some endpoints free) |
| Z.AI free flash | rate-limited, figure not published |
| OpenCode Zen free lane | quotas not published on this host; limited-time models |
| DeepSeek API (paid lane) | no RPM/TPM published; concurrency cap 2,500 (Flash), per account |

All figures drift; snapshot the date and re-verify before any gated trial.

## Privacy and retention matrix

Critical for this repository: **free external endpoints are not a PII path.**
`AGENTS.md`, `docs/security/real-data-rules.md`, and the orchestration study
already ban A1/employee/invoice data from free external workers; this matrix
gives the provider-specific reasons.

| Lane | Training on prompts? | Retention | Notes |
|---|---|---|---|
| OpenCode Zen zero-cost promotions | Model-specific; some documented promotions may train, others unverified | model-specific/unverified | Never infer a blanket zero-retention rule from namespace or zero price |
| NVIDIA free endpoints | Logged for security + product improvement | trial terms | "Do not submit personal or confidential data" — explicit ban |
| Poolside Laguna S 2.1 free | Yes | per provider | Free-page notice: inputs/outputs may train the model |
| DeepSeek API (direct) | Yes, training on by default (opt-out available) | data stored in China; account-lifetime | Independent review grades it AVOID for sensitive data |
| OpenRouter free | OpenRouter itself stores no prompts unless opted in | provider-dependent | Use `data_collection=deny` / `zdr` to restrict routing; check each model page |
| Kilo free | Some free models require allowing data collection | per provider | BYOK route keeps data with the provider you key |
| MiniMax free/paid | Yes, with opt-out | default account-lifetime; China/Singapore unless EU endpoint | Privacy review grade "RISKY" |
| Z.AI | Unverified (privacy page 404 as of 2026-08) | unverified | Do not rely on the "no storage" claim |

Decision rule: **no real employee, A1, invoice, or other protected data may
reach any free external model.** Free workers receive public/synthetic content
only.

## Task-fit guidance: where free models dominate, are recommended, and must be avoided

## AF2 execution correction — 2026-08-15

The first AF2 contract-echo attempt produced no valid Hy3 or DeepSeek quality
evidence. A harness sanitizer rejected legitimate typed token-usage metadata
before either trace ran; Luna was correctly not invoked. Both free models remain
unproven. Plan AF2.1 must pass before a new immutable synthetic run.

### A. Where free models dominate (best first-class fit)

1. **Web research and evidence collection** — public-source gathering,
   summarization, citation checking. Read-only, high volume, low risk. Any of
   the named free candidates (Hy3, DeepSeek V4 Flash free, Nemotron 3 Ultra
   free) works; deterministic link checks remain scripts.
2. **Repository exploration and code-path tracing** — "find where X is handled
   and cite exact paths" style tasks. OpenCode's read-only worker plus a named
   free model is the cheapest correct lane.
3. **Independent review of a bounded draft** — a fresh-model second opinion on
   a synthetic patch, with the reviewer recording the returned model.
4. **Mechanical code/test drafts in an isolated worktree** — small, exactly
   bounded edits where Codex re-runs tests and accepts/rejects.
5. **Bulk formatting, summarization, inventories** — free models only where
   deterministic scripts cannot express the task; record outputs as drafts.
6. **Cost-sensitive exploratory searches** — `openrouter/free` or
   `kilo-auto/free` for non-authoritative brainstorming, provided the returned
   model is logged and the content is public/synthetic.

### B. Where free models are recommended (with gates)

- Any task that is **bounded, read-only, synthetic-data, and verified by
  Codex** — the orchestration study's proposed trial shape.
- **Fail-safe when rate-limited:** keep a second named free model and a
  scripted retry with backoff; never a paid fallback.
- **Short-context tasks only:** keep worker context under the free lane's cap
  (e.g. 200K on DeepSeek V4 Flash free, 256K on Laguna free); plan for
  compaction.

### C. Where free models must be avoided

1. **Any real/protected data** — employees, scans, A1 artifacts, invoices,
   credentials, `.env`, secrets. Default-deny, per `AGENTS.md` and the privacy
   matrix above.
2. **Production, Git publication, deployment, and protected-data
   operations** — Codex plus existing human gates only.
3. **Architecture, security, and authority decisions** — frontier Codex
   (Sol/Terra), not free workers.
4. **Final integration and acceptance review** — Codex; free output is always a
   proposal.
5. **Reproducible evals and regression comparison** — never a random router;
   use a pinned named model and record the returned model; free availability
   changes.
6. **Long-context critical work** — free lanes cap context well below paid
   models; split or delegate only bounded slices.
7. **Anything with legal/policy exposure where provider privacy is unverified**
   — Z.AI's unverifiable privacy page and DeepSeek's China storage are hard
   stops for sensitive content.

The formula from the orchestration study still holds and is expanded here:
**deterministic scripts → cheap bounded free workers (public/synthetic only) →
Codex judgment, integration, and verification.**

## Recommended first-trial candidates (unchanged but now evidenced)

- From the OpenCode Zen free lane: **`opencode/deepseek-v4-flash-free`** and
  **`opencode/hy3-free`** — both agent/coding-oriented, free, and already
  advertised locally.
- Baseline: fast Codex (Terra/Luna), per the orchestration study.
- Optional third free lane: `opencode/laguna-s-2.1-free` or
  `opencode/nemotron-3.5-lightning-free` for a speed/capability spread, after
  the first two pass gates.
- Keep NVIDIA free endpoints and Kilo for the fallback lane only after their
  trial/data terms and per-IP caps are accepted; exclude MiniMax/Z.AI free
  from the first scored trial on throughput/privacy grounds.
- LiteLLM stays out of the first test; a separate second-stage canary remains
  specified in the orchestration study.

## Initial live investigation — 2026-08-15

### Refreshed zero-cost catalog

`opencode models opencode --verbose` reported seven active models with zero
input/output/cache price in the `opencode` namespace:

| Model | Live context/output | Tool call | Attachment | Reasoning variants |
|---|---:|---:|---:|---|
| `opencode/big-pickle` | 200K context, 160K input, 32K output | yes | no | none advertised |
| `opencode/deepseek-v4-flash-free` | 200K / 128K | yes | no | low/high/max |
| `opencode/hy3-free` | 190K / 64K | yes | no | low/medium/high |
| `opencode/laguna-s-2.1-free` | 256K / 32K | yes | no | low/medium/high |
| `opencode/mimo-v2.5-free` | 200K / 32K | yes | yes | none advertised |
| `opencode/nemotron-3-ultra-free` | 1M / 128K | yes | no | none advertised |
| `opencode/nemotron-3.5-lightning-free` | 262,144 / 262,144 | yes | no | none advertised |

This is catalog metadata, not a contractual price or capability guarantee. A
trial must snapshot it immediately before each run and reject a non-zero price
or changed model ID.

### Read-only availability canary

Both proposed primary candidates were invoked through `opencode run --pure
--agent plan --model ... --format json` with a 90-second process timeout. The
prompt allowed reads of only `README.md` and `AGENTS.md`, prohibited edits,
shell, network, external directories, and subagents, and requested one compact
JSON object with exact line citations.

| Observation | DeepSeek V4 Flash Free | Hy3 Free |
|---|---:|---:|
| Completed within timeout | yes, about 15 s | yes, about 22 s |
| Reported token cost | `$0` | `$0` |
| Tool behavior | one `read` of `README.md`; no mutation/shell/network | one `read` of `README.md`; no mutation/shell/network |
| Main repository conclusion | correct | correct |
| Output contract | valid compact JSON object | JSON wrapped in a Markdown code fence |
| Citation defect | claimed `AGENTS.md:126`; file has only 105 lines | no out-of-range numeric AGENTS citation, but cited injected AGENTS context without an observed file-read call |
| Provisional result | **fail citation gate** | **fail exact-format gate; better factual result** |

The `plan` agent's instruction context includes repository guidance, which
explains how a model can cite AGENTS facts without an explicit read event.
Future evals must distinguish prompt-injected context from tool-read evidence
and validate every returned line number mechanically.

Neither model is promoted by this canary. Hy3 becomes the provisional first
candidate for the scored trial; DeepSeek remains a comparison candidate with a
mandatory citation validator. This single run does not measure coding quality,
repeatability, rate limits, or privacy.

### Plan AF gated smoke outcome

The implemented Plan AF harness later repeated the trace smoke inside a copied
synthetic workspace with exact read-path enforcement. Both endpoints still
reported zero cost and the main repository snapshot remained unchanged, but the
matrix was correctly blocked:

- Hy3 read only `README.md` and `AGENTS.md` but failed the required fact/citation
  wire contract, scoring 30 before repeatability.
- DeepSeek attempted to read `/workspace` itself. The event validator rejected
  that directory read because the packet allowed only the two exact files; no
  output was scored.

The remaining 25 matrix trials, including the Codex Luna control, were not run.
Neither free model is promoted for trace, review, or code drafting. This outcome
supersedes the earlier provisional preference for Hy3 without changing the
synthetic-only privacy boundary.

### Planning facts now established

- Named free-model selection and non-interactive JSON event output work locally.
- `--pure` disables external plugins, but it is not an OS sandbox.
- The built-in `plan` agent prevented mutations in these runs; the permanent
  trial still needs an explicit project agent with default-deny permissions.
- Model output cannot be trusted to prove its own evidence or compliance.
- The evaluator must parse event streams, extract the final text, reject Markdown
  wrappers when raw JSON is required, validate file/line citations, inspect tool
  events, and independently check the worktree before and after every run.
- LiteLLM remains unnecessary for the first trial and unverified as a project
  dependency.

## Verification caveats

- Every model price, context window, rate limit, and privacy term above is a
  point-in-time claim from provider docs, models.dev, OpenRouter pages, or the
  live local catalog as of 2026-08-15. Re-verify before any gated trial.
- Vendor-reported benchmark numbers (SWE-bench, Terminal-Bench, agent suites)
  are not independent; treat them as directional.
- Record the actual returned model/provider/date on every scored run.

## Primary sources

- OpenCode Zen models and privacy notes — https://opencode.ai/docs/zen/
- OpenCode Go (subscription, distinct from free) — https://opencode.ai/docs/go/
- OpenRouter FAQ and rate limits — https://openrouter.ai/docs/faq and
  https://openrouter.ai/docs/api_reference/limits
- OpenRouter free-model collection — https://openrouter.ai/collections/free-models
- OpenRouter privacy: data collection and provider logging —
  https://openrouter.ai/docs/guides/privacy/data-collection and
  https://openrouter.ai/docs/guides/privacy/provider-logging
- OpenRouter provider routing (`data_collection`, `zdr`) —
  https://openrouter.ai/docs/guides/routing/provider-selection
- Z.AI pricing — https://docs.z.ai/guides/overview/pricing
- Z.AI GLM-4.7 release notes — https://z.ai/blog/glm-4.7
- NVIDIA build catalog and NIM docs — https://build.nvidia.com/ and
  https://docs.nvidia.com/nim/ (Nemotron 3.5 Lightning launch, NVIDIA API
  Trial Terms)
- Kilo Gateway docs — https://kilo.ai/docs/gateway (usage/billing,
  models-and-providers, authentication)
- MiniMax pricing and rate limits — https://platform.minimax.io/docs/guides/pricing-paygo
  and M2.5 announcement — https://www.minimax.io/blog/minimax-m25
- DeepSeek V4 preview and changelog — https://www.deepseek.com/en/news/v4-preview/
  and https://api-docs.deepseek.com/news/news260424/
- Poolside Laguna S 2.1 — https://poolside.ai/blog/introducing-laguna-s-2-1
- Tencent Hy3 — https://hy.tencent.com/research/hy3 and
  https://openrouter.ai/tencent/hy3
- Xiaomi MiMo-V2.5 / V2.5-Pro — https://mimo.xiaomi.com/mimo-v2-5/ and
  Hugging Face `XiaomiMiMo/MiMo-V2.5-Pro`
- Third-party privacy comparison — https://erkinekici.com/articles/comparing-llm-api-privacy/
