# Factorio microbenchmark results

This directory is the publication boundary for reproducible model baselines.
The authoritative task catalog lives in `fle.envd.benchmark`; generated
manifests and submitted results are artifacts of that code.

## Layout

```text
benchmark/
  manifests/   generated versioned task catalogs
  results/     validated model run JSON
```

Full trajectories are written beside each result in a
`<run-name>-trajectories/` directory. Keep them for auditability; a leaderboard
number without the corresponding engine trace is not a complete submission.

## Generate the manifest

```bash
fle-benchmark-results manifest \
  benchmark/manifests/benchmark-0.2.0-dev.json
```

## Run a baseline

Start the Factorio fleet, `factorio-envd`, and an OpenAI-compatible model
server. Then run:

```bash
fle-benchmark \
  --suite api_microtasks_v1 \
  --status ready \
  --attempts 3 \
  --model-base-url http://127.0.0.1:18080/v1 \
  --output benchmark/results/model-name.json
```

The ready suite currently contains 21 tasks. For inexpensive calibration,
start with the 11-task development split and one attempt:

```bash
fle-benchmark \
  --suite api_microtasks_v1 \
  --status ready \
  --split development \
  --attempts 1 \
  --output runtime/model-development.json
```

Use `--split development` while debugging. Validation and test scores should
only be published from a clean run with fixed generation settings. Include the
model revision and quantization where applicable:

```bash
fle-benchmark \
  --model my-org/my-model \
  --model-revision abc123 \
  --quantization Q4_K_XL \
  --provider local \
  --output benchmark/results/model-name-q4.json
```

## First developer baseline

The first complete real-engine run is
`results/gpt-5.6-sol-developer.json`: GPT-5.6-Sol authored the intervention
programs through Codex and completed 19 of 21 ready tasks with no retry
allowance. It is intentionally labeled `openai-codex/manual-tools` and
`non_blind=true`. Repository familiarity makes it a developer baseline and
harness shakeout, not a blind API-sampled model score.

The reproducible policy is retained in `codex_developer_baseline.py`, and all
21 engine trajectories are stored next to the result.

## Defensive context-blind development runs

The `gpt-5.6-{terra-max,sol-medium,sol-xhigh}-blind-development` results use a
fresh `fork_turns=none` Codex subagent for every task. The subagent receives a
public task/API packet, is forbidden from using tools, and returns one program
to `blind_subagent_broker.py`. Only the trusted broker can lease or execute the
Factorio environment.

These runs are context-blind and broker-isolated, but not OS-enforced
source-blind runs: Codex subagents share the host filesystem, and the parent
does not receive an independently auditable child tool-call trace. The result
metadata records that limitation explicitly. Do not relabel them as
filesystem-sandboxed results.

The initial developer and context-blind runs were collected while the
benchmark implementation was still an uncommitted worktree on top of
`1d20388`. Their records retain that historical HEAD and explicitly set
`repository_worktree_dirty_at_run=true`. They are development calibration
artifacts, not clean-checkout reproducibility claims.

## DeepSeek V4 Flash strict API baseline

`results/deepseek-v4-flash-full-strict-1x.json` is the first complete hosted
API baseline collected through the minimal OpenAI-compatible tool harness. It
uses `deepseek-v4-flash`, one attempt per ready task, temperature 0.1, no tool
error retries, and the API's default thinking mode. It completed 3 of 21 tasks
(14.29%) with 32 invalid interventions out of 68 total interventions.

This is a valid but provisional one-sample baseline. A preceding development
run produced different outcomes on several tasks, so capability comparisons
should use the planned three-attempt condition. The full technical report is
in `docs/evaluations/2026-08-09-deepseek-v4-flash.md`.

## Submission policy

A pull request adding results should contain:

1. The validated run JSON and summary JSON.
2. All referenced trajectory artifacts.
3. An immutable model identifier when available.
4. The repository commit recorded by the runner.
5. Hardware/runtime notes sufficient to interpret latency (latency is not a
   capability score).
6. The tool-error retry budget. Runs with different retry budgets are separate
   evaluation conditions.

Run `fle-benchmark-results validate <result.json>` before opening the pull
request. Do not hand-edit success values or task fingerprints.
