# DeepSeek V4 Flash Factorio microbenchmark baseline

## Result

DeepSeek V4 Flash completed **3 of 21** ready Factorio microtasks in the strict
one-attempt condition, for a success rate of **14.29%**.

| Field | Value |
| --- | --- |
| Model | `deepseek-v4-flash` |
| Provider | DeepSeek official API |
| API observation date | 2026-08-09 |
| Benchmark | `api_microtasks_v1` / `0.2.0-dev` |
| Attempts | 1 per task, 21 total |
| Tool-error retries | 0 |
| Temperature | 0.1 |
| Maximum output tokens | 2,048 per turn |
| Context budget | 18,000 characters |
| Thinking mode | API default (enabled); not overridden by the harness |
| Factorio | 2.0.73, real headless engine |
| Action profile | `fle-program-v1` |
| Repository commit | `1f595d75f1704a4ab582996069339a0c7b6fc266` |
| Run ID | `api_microtasks_v1-20260809T125610Z` |
| Wall clock | 388.256 seconds |

The official API exposed the stable model IDs `deepseek-v4-flash` and
`deepseek-v4-pro`. It did not expose a dated revision identifier, so the run
records the stable API ID and observation date rather than inventing a model
revision.

## Passed tasks

| Task | Interventions | Invalid interventions | Time (seconds) |
| --- | ---: | ---: | ---: |
| `micro_craft_iron_gear_v1` | 1 | 0 | 4.819 |
| `micro_transfer_to_chest_v1` | 1 | 0 | 8.279 |
| `micro_place_roboport_v1` | 5 | 2 | 42.452 |

The successes cluster around direct inventory operations and one placement
task. No automatic-production, chemistry, research, oil, smelting, or recipe
configuration task passed in this run.

## Failure profile

The model made 68 interventions, 32 of which were invalid, yielding a **47.06%**
invalid-intervention rate. Terminal outcomes were:

| Termination reason | Count |
| --- | ---: |
| Success | 3 |
| Invalid action | 7 |
| Intervention limit | 5 |
| No progress | 5 |
| Constraint violation | 1 |

Trajectory inspection shows model/API competence failures rather than a broken
tool transport or verifier. Recurring mistakes included:

- importing `factorio`, `fle`, `api`, or `entities` despite the public prompt
  explicitly prohibiting imports;
- attempting blocked reflection with `dir` and `type`;
- confusing resources with prototypes, such as nonexistent
  `Prototype.CoalOre` instead of `Resource.Coal`;
- calling FLE tools with invented signatures such as `get_entity(name=...)`;
- treating a returned `Position` as an entity and accessing `.position` again;
- trying to set a furnace recipe through the generic entity-recipe operation.

Valid tool calls, engine state mutations, state hashes, task finalization, and
reward computation all worked in the same run. The environment service did not
crash or leak a lease.

## Cost and token accounting

Across 86 model turns, the run used:

| Token channel | Tokens |
| --- | ---: |
| Prompt total | 200,488 |
| Prompt cache hits | 93,056 |
| Prompt cache misses | 107,432 |
| Completion | 29,191 |

Using the DeepSeek pricing visible on the run date ($0.0028/M cached input,
$0.14/M uncached input, and $0.28/M output), estimated inference cost was
**$0.023475**. This excludes local CPU and negligible storage costs.

## Integrity and limitations

- `fle-benchmark-results validate` accepted all catalog fingerprints.
- The result, summary, and 21 trajectory files were scanned against the active
  API credential; zero files contained it.
- Programs ran through the restricted FLE namespace and policy guard.
- The local Windows/Docker runtime reports `process_isolation=false`; this is
  not the future AgentENV microVM deployment condition.
- The benchmark task code was committed at the recorded repository revision.
  The worktree also contained unrelated, uncommitted Prime/DSpark integration
  documentation, which did not alter the benchmark or runtime code.
- One attempt per task is not a stable capability estimate. A preceding
  11-task development run scored 3/11 and disagreed with the full run on some
  individual tasks. The publishable comparison condition should use at least
  three attempts per task.

## Artifacts

- `benchmark/results/deepseek-v4-flash-full-strict-1x.json`
- `benchmark/results/deepseek-v4-flash-full-strict-1x.summary.json`
- `benchmark/results/deepseek-v4-flash-full-strict-1x-trajectories/`

DeepSeek API model and pricing reference:
<https://api-docs.deepseek.com/quick_start/pricing>
