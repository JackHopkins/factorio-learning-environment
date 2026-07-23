# Factorio RLVR stack boundary

Status: first vertical slice implemented, 2026-07-21

## Decision

Use the Verifiers v1 Taskset/Harness API as a pinned dependency. Do not fork or
vendor Verifiers for the first implementation. Run the initial GRPO experiment
with an unmodified, pinned Prime-RL checkout. Prime-RL already carries the exact
Verifiers commit it expects as a submodule.

Keep the three systems separated:

1. FLE owns Factorio state, actions, measurements, checkpoints, verification,
   and the environment fleet.
2. A `factorio_v1` adapter maps those capabilities onto Verifiers v1 tasks,
   state, MCP tools, traces, rewards, and metrics.
3. Prime-RL owns sampling, inference, tokenization, optimization, weight
   synchronization, and ordinary GRPO credit assignment.

The tested compatibility pins are recorded in
`integrations/prime/compatibility.toml`. Training uses Python 3.12 in a separate
environment from local FLE development.

## Why Verifiers is a dependency, not a fork

Verifiers v1 already provides the boundaries Factorio needs:

- typed deterministic and infinite tasksets;
- per-rollout task setup and finalization;
- mutable rollout state synchronized with MCP tool servers;
- framework-enforced turn, token, and wall-clock limits;
- per-rollout rewards and metrics;
- group rewards across sibling rollouts;
- trace serialization;
- local or external environment servers;
- static or elastic environment worker pools;
- harness runtimes and model-call interception.

Our novel work does not belong in those generic mechanisms. A Verifiers fork is
justified only if a missing generic lifecycle or trace capability cannot be
implemented cleanly in the Factorio adapter and is not accepted upstream.

## Runtime flow

```text
Prime-RL orchestrator
    -> Verifiers v1 EnvClient
    -> factorio_v1 taskset + task + MCP toolset
    -> factorio-envd lease API
    -> warm Factorio server pool
    -> RCON/Lua/FLE

Factorio verifier snapshot
    -> Verifiers trace rewards, metrics, and info
    -> Prime-RL rollout or persistent-episode learner
    -> task-family-specific credit assignment
    -> trainer token loss
```

For production, Prime-RL should connect to an external Verifiers environment
server placed near the CPU Factorio fleet. The orchestrator must not launch or
own individual Factorio processes.

## Verifiers v1 mapping

`FactorioTaskData` is immutable and sufficient to reproduce a task:

- task id and schema version;
- scenario and Factorio version;
- initial checkpoint hash;
- map seed;
- goal and constraints;
- holdout duration and verifier configuration;
- action-profile version.

`FactorioState` is per-rollout transient state:

- environment lease id;
- current checkpoint/state hash;
- intervention count;
- compact notebook and measurement references;
- failure and recovery counters.

`FactorioTask.setup` leases an independent copy of the declared checkpoint.
`FactorioToolset` exposes structured lookup, observation, measurement, and
auditable program execution through MCP. `FactorioTask.finalize` runs the
holdout verifier, writes a durable result snapshot into the trace, and releases
the lease. Reward methods read only that recorded snapshot. Group rewards may
compare final-state fingerprints for state-level diversity.

Task generation must be deterministic by task index. When a task uses
group-relative learning, each group member receives an independent lease of the
same checkpoint, seed, and task specification. Long progression episodes are
not assumed to use group-relative terminal rewards.

## General task protocol

Protocol 0.2 separates what the simulator verifies from how a trainer learns:

- `task_family`: throughput, construction, milestone, repair, progression,
  robustness, or open play;
- `objectives`: multiple typed predicates or optimization targets;
- `constraints`: intervention, time, manual-crafting, resource, pollution, and
  action-profile limits;
- `verifier`: required-objective composition and scalarization metadata;
- `curriculum`: stage, episode mode, prerequisites, and suggested learning
  strategies;
- `knowledge_sources`: source metadata for students, privileged teachers, or
  offline dataset builders.

Existing FLE registry tasks are translated through
`fle.envd.task_builder.build_task_spec`. The live registry remains responsible
for provisioning and legacy verification, but neither envd's wire contract nor
the Verifiers adapter assumes that every future task is a throughput task.
Custom specs may name a legacy FLE task separately with `backend_task_id`.
`objective_engine_v1` is the native multi-objective verifier. It currently
supports sustained throughput, cumulative production, research, inventory,
entity existence, verified rocket launches, and elapsed-operation objectives.
It also enforces tick, intervention, manual-crafting, and action-profile
constraints. Engine instrumentation now makes pollution, raw-resource cost,
forbidden-action inspection, resource depletion, and character death
verifiable as well. Death records include the causal entity and structured
train metadata when rolling stock is involved.

`fle.envd.curriculum.early_automation_progression_task` is the first built-in
persistent specification. It provisions freeplay-like starter equipment with
research locked, then requires automation research, an assembling machine, and
three consecutive red-science throughput windows.

The initial learning-strategy mapping is:

| Task family | Initial strategy |
|---|---|
| API grounding | selective SFT |
| Student failures and diagnosis | OPD/OPSD |
| Short repair or construction branches | GRPO |
| Bounded expansion with local process deltas | process-GRPO |
| Persistent progression | actor-critic or corrected off-policy learning |
| Successful long trajectories | offline replay and distillation |

Knowledge guides are hints for teacher-context and dataset construction, not
authoritative verifier definitions. In particular, strategy advice such as a
main bus, city blocks, or leaving expansion space must not become a mandatory
success predicate.

The current source manifest includes:

- Factorio Wiki, Quick start guide:
  https://wiki.factorio.com/Tutorial:Quick_start_guide
- VoidGrazer, High-Level Strategy for New Players:
  https://steamcommunity.com/sharedfiles/filedetails/?id=2275950965
- EarlyGuides, Start-to-endgame walkthrough:
  https://earlyguides.com/factorio/walkthrough

## Verifier events and reward channels

Protocol 0.2 also adds typed `VerifierEvent` records. Events have a stable id,
simulation tick, source, optional objective id, payload, evidence, and named
reward-channel deltas. The initial vocabulary covers interventions, invalid
actions, objective outcomes, milestones, research, bottleneck shifts,
perturbations, recovery, character death/respawn, resource depletion, terminal
classification, and final verification.

The event stream is the durable fact layer. Algorithms may scalarize its named
channels differently without rerunning Factorio. `RewardVector` retains current
task, throughput, automation, progress, invalid-action, and resource channels
and reserves explicit milestone, robustness, time-efficiency, and
manual-intervention channels.

As of protocol 0.2.1, `automation` is the nonnegative portion of FLE's legacy
automated net-production-value delta. Provisioned inputs can make the underlying
net statistic negative when they are consumed successfully, so the signed raw
delta is retained as `automated_production_score_delta` in verifier metrics
instead of being treated as negative capability reward. Resource consumption
and policy costs remain represented by their dedicated negative channels.

Every native verification produces a `PrivilegedDiagnosticPacket` containing:

- per-objective and per-constraint results with evidence;
- inventory and inventory deltas;
- total, automated, and manually crafted production;
- relevant research state and technology prerequisites;
- entity counts and operational-status counts;
- status-derived bottleneck signals;
- character health, deaths, causal entities, respawns, and terminal reason;
- total/emitted pollution and raw-resource extraction/consumption;
- actual FLE tool calls and forbidden-action violations;
- depleted-resource events;
- target recipes queried from the running engine;
- curated knowledge-source metadata and explicit telemetry caveats.

The packet is written to `trace.info["factorio_privileged_teacher"]`; it is not
returned by the student observation tool. This makes it usable for OPD/OPSD
dataset construction without leaking privileged state into ordinary rollouts.

## Required FLE extensions

The FLE fork must add a trainer-independent `factorio-envd` service with:

- `health` and capability/version negotiation;
- `lease`, `reset`, `release`, and idempotent cleanup;
- `execute_program` with atomic action/event logging;
- structured `observe`, `lookup`, and measurement probes;
- `checkpoint`, `restore`, and eventually `clone`;
- holdout execution and a versioned reward vector;
- terminal state fingerprints and state hashes;
- lease TTLs, crash recovery, and worker recycling;
- complete trajectory/event persistence.

The service, rather than Verifiers rollout state, is the authority for live
game state. Lease TTLs are mandatory because Verifiers cannot guarantee that a
task hook runs after every process or machine failure.

The first adapter should use Verifiers' built-in default harness with MCP and a
restricted runtime. We should add a custom Factorio harness only if the default
harness cannot provide the desired short-program action boundary or introduces
unacceptable tools or context behavior.

## Prime-RL fork boundary

Do not fork Prime-RL for the first GRPO smoke run. Its current implementation
already supports Verifiers v1 environment servers, rollout groups, per-token
advantage streams, GRPO, SFT, OPD, OPSD, and ECHO.

Create a WASLab Prime-RL fork when one of these becomes part of an experiment:

- Factorio process credit mapped to different turns or token spans;
- live mid-trajectory checkpoint branching;
- checkpoint-derived replay or adaptive curriculum sampling;
- policy-version pinning for long persistent episodes;
- a critic and conventional actor-critic PPO.

Process credit is a small, named Prime-RL algorithm extension because the
trainer already accepts explicit per-token advantages. Branching is a sampler
extension. Prime-RL currently requires named algorithms to be registered in its
repository rather than loaded from an arbitrary import path, so those features
cross the fork boundary.

## First vertical slice

The first runnable slice remains deliberately small. Items marked complete are
implemented in this fork:

1. **Complete:** implement a networked `factorio-envd` contract backed by a
   fixed warm pool of existing FLE instances.
2. **Partial:** add a deterministic throughput task. Procedural repair tasks are
   the next task-side extension.
3. **Partial:** expose auditable program execution and structured observation.
   Dedicated lookup and measurement probes remain to be separated from the
   existing FLE program namespace.
4. **Complete:** produce a protocol-0.2 verifier snapshot
   with typed objectives, constraints, events, named reward channels, action
   hashes, terminal state hashes, lifecycle causes, pollution/resource
   accounting, actual tool-call audits, and terminal classification.
5. **Complete at contract level:** load and exercise the task lifecycle through
   Verifiers v1 on Ubuntu/Python 3.12. A real model evaluation is next.
6. **Complete:** implement the first persistent progression task and privileged
   diagnostic packet.
7. **Pending:** run base-model evaluation across at least one short repair task
   and one persistent progression chunk.
8. **Pending:** connect the appropriate Prime-RL path per task family; reserve
   GRPO for shared-checkpoint local decisions.

Only after this slice is reliable should the environment become a distributed
lease service or Prime-RL receive Factorio-specific algorithms.

## Upstream references

- Verifiers: https://github.com/PrimeIntellect-ai/verifiers
- Prime-RL: https://github.com/PrimeIntellect-ai/prime-rl
- Verifiers v1 tasksets:
  https://github.com/PrimeIntellect-ai/verifiers/blob/main/docs/v1/tasksets.md
- Verifiers v1 harnesses:
  https://github.com/PrimeIntellect-ai/verifiers/blob/main/docs/v1/harnesses.md
- Prime-RL algorithms:
  https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/algorithms.md
