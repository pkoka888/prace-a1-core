# Model assistance in CLI claim verification

## Decision

The core verifier must remain model-free. A language model is useful only as an
optional, non-authoritative assistant for unresolved semantic work:

1. Propose narrow searches of official documentation.
2. Map sanitized excerpts into a candidate evidence schema.
3. Flag conflicting wording for a deterministic probe or human review.

It must not execute commands, inspect credentials or private configuration,
read employee/A1 data, or convert missing evidence into a factual verdict.

## Temperature is not a global solution

For focused extraction and evidence classification, configure temperature
`0.0` or the lowest value supported by the selected model. Leave `top_p`
unset; changing both makes evaluation harder. This reduces deliberate sampling
but does not guarantee identical results across calls, model revisions,
hardware, routing, or provider implementations.

The recommendation is therefore:

| Work | Temperature | Reasoning effort | Authority |
|---|---:|---|---|
| Runtime/config checks | No model | No model | Deterministic |
| Exact extraction into JSON | 0 or lowest supported | Low | Advisory |
| Contradiction analysis | 0 or lowest supported | Medium | Advisory |
| Search-query generation | 0–0.2 if supported | Low | Advisory |
| Creative hypothesis generation | Separate workflow | Evaluated per task | Never verification evidence |

For a material unresolved claim, run two independent advisory samples. Accept
agreement only as a reason to run the proposed probe—not as verification.
Disagreement remains `NOT_TESTED`.

## Product-specific findings

- OpenCode exposes per-agent `temperature`, `top_p`, model selection, step
  limits, and provider-specific reasoning options. Its documentation recommends
  low temperature for analysis but also notes model-specific defaults.
- Kilo exposes per-agent temperature from `0.0` to `1.0`, plus model-specific
  reasoning variants. Some models explicitly do not support temperature.
- Codex and current OpenAI reasoning models emphasize `reasoning.effort` rather
  than treating temperature as a universal quality setting. Official guidance
  recommends comparing settings on representative tasks.
- Cline exposes model and reasoning-effort selection in the installed CLI. Its
  `--json` option controls task-event serialization, not output correctness.
- Hermes exposes model/provider selection and `--yolo`, but no safe local
  evidence established a universal temperature flag. Do not invent one.

## Optimization principles

1. Deterministic probes first; model judgment only for residual ambiguity.
2. One normalized evidence object per claim, with stable evidence IDs.
3. Structured JSON output with an allowlisted candidate status vocabulary.
4. Pin product/model versions and record retrieval dates.
5. Evaluate on a small fixed claim set before changing model, prompt,
   temperature, or reasoning effort.
6. Track accuracy, unsupported-claim rate, disagreement rate, latency, tokens,
   and cost. Lower temperature is not an optimization unless those measurements
   improve or remain stable.
7. Use only verified-free endpoints allowed by repository policy; never enable
   paid fallback. External input must be public or sanitized.

## Primary sources

- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenCode agents and temperature](https://dev.opencode.ai/docs/agents/)
- [Kilo custom subagents](https://kilo.ai/docs/customize/custom-subagents)
- [Kilo custom models](https://kilo.ai/docs/code-with-ai/agents/custom-models)
- [Effect of sampling temperature on problem solving](https://arxiv.org/abs/2402.05201)
- [Long-form factuality in large language models](https://papers.neurips.cc/paper_files/paper/2024/file/937ae0e83eb08d2cb8627fe1def8c751-Paper-Conference.pdf)

The studies support using temperature zero as a reproducibility control, not as
proof of correctness. The problem-solving study found no statistically
significant performance change from temperature 0.0 to 1.0 on its evaluated
tasks, reinforcing the need for task-specific evaluation rather than folklore.
