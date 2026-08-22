# factorio-microtasks

Engine-verified Factorio microtasks for evaluating tool-using agents and
bootstrapping reinforcement learning with verifiable rewards.

The environment publishes the `api_microtasks_v1` suite from the WASLab fork of
the Factorio Learning Environment (FLE). Version 0.1.0 contains 24 real-game
tasks: 21 ready benchmark tasks and 3 tasks retained as
`calibration_required`. The default selection includes only the 21 ready tasks.

## What the model does

Each rollout leases a real Factorio 2.0.73 headless-server state from
`factorio-envd`. The model receives a compact public action reference and two
tools:

- `factorio_execute_program`: execute one short Python intervention through
  FLE's restricted, auditable action namespace.
- `factorio_observe_factory`: inspect the permitted structured game state.

The Factorio engine and objective verifier determine success. The model cannot
award itself reward, call RCON directly, or access the privileged teacher
packet. Final traces retain the scalar reward, decomposed metrics, termination
reason, state hashes, and privileged diagnostics for offline analysis or OPSD.

## Runtime requirement

This package intentionally does **not** contain Factorio binaries and does not
launch game processes. It is the Verifiers v1 taskset/control-plane adapter.
Before evaluating it, run a compatible `factorio-envd` service backed by warm
Factorio instances and make that service reachable from the evaluation worker.
Only expose `factorio-envd`; keep Factorio RCON ports private.

Configure the service URL under the taskset-owned tool config:

```toml
[[env]]
id = "factorio-microtasks"

[env.taskset]
benchmark_statuses = ["ready"]

[env.taskset.task.tools]
envd_url = "https://factorio-envd.example.internal"
request_timeout_seconds = 180.0

[env.agent.harness]
id = "bash"
max_turns = 8
```

For local development, the default URL is `http://127.0.0.1:8172`.

## Taskset configuration

| Field | Default | Meaning |
| --- | --- | --- |
| `benchmark_statuses` | `["ready"]` | Include ready tasks; add `calibration_required` explicitly for the remaining three. |
| `seed` | `0` | Base deterministic task seed. |
| `factorio_version` | `2.0.73` | Pinned engine version recorded in every task contract. |
| `action_profile` | `fle-program-v1` | Restricted program-action API profile. |
| `task.tools.envd_url` | `http://127.0.0.1:8172` | Reachable environment-service URL. |
| `task.tools.request_timeout_seconds` | `180.0` | HTTP timeout for a game intervention or observation. |

The suite identity is fixed to `api_microtasks_v1`; it cannot silently fall
back to FLE's legacy throughput task.

## Rewards and metrics

The main reward is the engine-grounded scalar emitted by `factorio-envd` after
finalization. The trace also includes:

- binary success and intervention count;
- task, throughput, automation, progress, milestone, robustness, and time
  efficiency components;
- invalid-action, manual-intervention, and resource-cost components;
- terminal state hash and termination reason;
- privileged diagnostic and state-transition packets, withheld from the
  student policy.

## Source and licensing

- Environment integration: <https://github.com/HumanDotPy/factorio-learning-environment>
- Upstream FLE: <https://github.com/JackHopkins/factorio-learning-environment>
- Environment code: MIT

Factorio is not redistributed by this package. Operators are responsible for
using the official headless server and complying with Wube's terms.

