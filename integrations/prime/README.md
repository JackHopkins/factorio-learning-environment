# Prime-RL handoff

This directory is the reproducible boundary between FLE and Prime-RL. FLE is
installed into Prime-RL's Python 3.12 environment; Prime-RL and Verifiers are
not vendored into this repository.

## 1. Start the Factorio fleet and environment service

On a Windows development machine:

```powershell
uv sync --extra prime
uv run fle cluster start -n 4
uv run fle-envd --factorio-address 127.0.0.1 --rcon-ports 27000,27001,27002,27003
```

On an Ubuntu training cluster, prefer the AgentENV deployment in
`integrations/agentenv/README.md`. Prime-RL and Verifiers still use the same
`envd_url`; they do not call AgentENV directly. The commands above remain the
portable fallback. Expose only `factorio-envd` to the training network and keep
Factorio RCON ports private.

## 2. Create the pinned Prime-RL checkout on Ubuntu

From this FLE checkout:

```bash
python integrations/prime/bootstrap.py ../prime-rl-factorio
cd ../prime-rl-factorio
uv sync --all-extras --all-packages
uv pip install -e ../FactorioEnv
```

The bootstrap script refuses to mutate an existing checkout at the wrong
revision. The required Prime-RL and Verifiers commits live in
`compatibility.toml` and are checked independently.

## 3. Validate the taskset before renting GPUs

```bash
uv run python -c "from verifiers.v1.loaders import taskset_class; print(taskset_class('factorio_v1'))"
curl http://127.0.0.1:8172/v1/health
```

If Prime-RL and `factorio-envd` are on different machines, replace every
`127.0.0.1` URL with a routable private service address. The MCP tool process
and task lifecycle both use this URL.

The first native persistent task can be selected in the Verifiers taskset
configuration with:

```toml
builtin_task_ids = ["progression_early_automation_v1"]
```

When `builtin_task_ids` or explicit `task_specs` are supplied, the default
legacy throughput task list is not loaded. The progression task uses
`objective_engine_v1`, three sustained holdout windows, locked research, and
freeplay-like starter equipment.

Lifecycle termination is propagated immediately from `factorio-envd` into the
Verifiers stop condition. Final traces retain `termination_reason` plus a
privileged packet containing death cause (including train metadata), pollution,
raw-resource accounting, resource depletion, and actual FLE tool-call policy
violations. This packet remains outside the normal student observation.

Ready benchmark suites can be selected directly:

```toml
benchmark_suites = ["lab_throughput_v1", "robustness_v1"]
benchmark_statuses = ["ready"]
```

The development catalog and readiness policy are documented in
`docs/benchmark-v0.2.md`. The short API benchmark can be selected with:

```toml
benchmark_suites = ["api_microtasks_v1"]
benchmark_statuses = ["ready"]
```

Use `fle-benchmark` before training to collect comparable inference-only
baselines from any OpenAI-compatible model endpoint. Its result schema,
catalog-fingerprint validation, and GitHub submission policy are documented in
`benchmark/README.md`.

Every task prompt includes a compact public FLE action and lookup reference.
`factorio-envd` rejects ordinary host access, reflection, and direct
`FactorioInstance`/RCON use before executing a model program. This is a
fairness and defense-in-depth guard, not a complete Python sandbox. The health
manifest always reports `program_policy_guard=true`. The local Docker/RCON
runtime reports `process_isolation=false`; the AgentENV production gateway
reports `process_isolation=true` because each lease runs in a disposable
Firecracker microVM. Generated programs still receive only the restricted FLE
namespace rather than arbitrary guest shell access.

## 4. Run the smoke configuration

Copy `rl-smoke.toml` into the Prime-RL checkout, update `envd_url`, then launch
it with Prime-RL's documented RL entrypoint. The file intentionally performs
only two optimization steps. It proves trace/reward/trainer plumbing; it is not
a capability experiment.

The first run uses Prime-RL without source changes. Fork Prime-RL only when we
add per-turn Factorio advantages, live checkpoint-derived sampling, or policy
version pinning. Fork Verifiers only if a missing generic lifecycle or trace
feature cannot be implemented in this adapter and cannot be upstreamed.

## 5. Qualify DSpark before paid rollouts

Prime-RL's generic `inference.vllm_extra` field is sufficient to configure
vLLM's DSpark speculative decoder; no trainer fork is required. Use
`rl-dspark-smoke.toml` only with a target-matched speculator and retain strict
rejection sampling.

The correctness and performance gates are documented in [DSpark.md](DSpark.md).
Run the non-speculative and DSpark smoke configurations against the same task
batch before enabling it for a paid rollout. Strict verification preserves the
target distribution, but an RL-updated policy can make a frozen draft stale
and erase the speedup without corrupting samples.
