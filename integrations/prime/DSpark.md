# DSpark rollout inference

DSpark is the preferred rollout accelerator when a compatible target-specific
speculator exists. It changes how tokens are proposed and verified, not the
RL objective. Under strict rejection sampling, accepted tokens still follow
the target policy distribution.

## Non-negotiable correctness profile

Use all of the following:

```toml
[inference.vllm_extra]
speculative_config = { method = "dspark", model = "<target-matched-vllm-speculator>", num_speculative_tokens = 7, rejection_sample_method = "strict" }
```

- The speculator must be trained for the exact target model/tokenizer family.
- Use vLLM's strict rejection sampler.
- Keep DSpark's verification schedule causal. The DSpark paper's production
  global-search relaxation is not the default for RL data because it consults
  future-token confidence and relaxes the paper's lossless argument.
- Sampling log probabilities stored by Prime-RL must be target-policy
  log probabilities for the selected tokens, never draft-model probabilities.
- Tool calling and structured outputs must pass the same parser tests as
  non-speculative inference.

The matching requirement is operationally important. DeepSpec's public DSpark
checkpoints cover Qwen3 4B/8B/14B and Gemma 4 12B. A DeepSeek, Kimi, or custom
RL policy needs its own matching checkpoint or a separately released one.
Do not silently fall back to an unrelated draft model.

## Prime-RL boundary

Prime-RL 0.7 already exposes `inference.vllm_extra`, so DSpark does not require
a Prime-RL source fork. This repository pins a Prime-RL revision using vLLM
0.26 because the prior vLLM 0.24 pin predates the supported DSpark deployment
path.

In a disaggregated prefill/decode deployment, apply DSpark only to the decode
workers through Prime-RL's decode-side vLLM overrides. The prefill workers do
not benefit from speculative token generation.

## RL-specific risks

### Draft staleness

The target policy changes during RL. Strict verification preserves
distributional correctness when the draft becomes stale, but acceptance and
speedup decline. Log these against policy version:

- accepted tokens per verification step;
- acceptance rate by draft position;
- draft and target verification latency;
- target tokens per wall-clock second;
- GPU-seconds per accepted target token;
- acceptance versus policy KL from the draft's training checkpoint.

Start with a frozen speculator. Refresh or fine-tune it only when measured
acceptance falls below the break-even point; do not couple draft updates to
every policy synchronization.

### Log-probability parity

Prime-RL uses rollout-time target log probabilities for importance ratios.
vLLM documents speculative decoding as lossless but does not promise
bit-identical log-probability numerics across batching and hardware. Therefore
distributional correctness alone is insufficient for this stack.

Before training, compare speculative and ordinary serving on the same pinned
model, tokenizer, sampler configuration, prompts, and hardware:

1. greedy token/output equality;
2. sampled token-frequency agreement over many seeds;
3. selected-token target log-probability error;
4. tool-call and structured-output validity;
5. Prime-RL mismatch-KL and importance-ratio distributions;
6. throughput at the Factorio rollout concurrency and context-length profile.

Do not begin the paid RL run unless these gates pass. A speedup measured on
single-turn short prompts is not sufficient evidence for long, growing
Factorio trajectories.

## Rollout progression

1. Run `rl-smoke.toml` without speculation and retain its traces.
2. Run `rl-dspark-smoke.toml` with the same seed/task batch.
3. Compare reward, stop reasons, tool validity, sampled log probabilities, and
   trajectory hashes where greedy equality applies.
4. Benchmark concurrency and context-length buckets.
5. Enable DSpark for the first paid run only after the strict path wins on
   target tokens per dollar.

If no compatible speculator exists for the chosen policy, ordinary vLLM is the
correct fallback until a draft is trained. "DSpark required" means the rollout
architecture must support and prefer it—not that an incompatible checkpoint
should be forced into a run.
