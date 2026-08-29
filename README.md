<h1 align="center">Factorio Learning Environment</h1>
<p align="center">
  <a href="https://jackhopkins.github.io/factorio-learning-environment/leaderboard">Leaderboard</a> | <a href="https://arxiv.org/abs/2503.09617">Paper</a> | <a href="https://jackhopkins.github.io/factorio-learning-environment/versions/0.3.0.html">Website</a> | <a href="https://jackhopkins.github.io/factorio-learning-environment/sphinx/build/html/">Documentation</a> | <a href="https://discord.gg/zKaV2skewa">Discord (#factorio-learning-env)</a>
</p>

<p align="center">
An open source framework for developing and evaluating LLM agents in the game of <a href="https://factorio.com/">Factorio</a>.
</p>

<p align="center">
<img src="https://github.com/JackHopkins/factorio-learning-environment/raw/main/docs/assets/videos/compressed_sulfuric_acid.webp" width="485" height="364" controls/>
<img src="https://github.com/JackHopkins/factorio-learning-environment/raw/main/docs/assets/videos/compressed_red_science.webp" width="485" height="364" controls/>
</p>
<p align="center"><em>Claude Opus 4.1 Plays Factorio</em></p>

## Quick Links

- [Installation](#installation)
- [Environment](#environment)
- [Contributing](#contributing)

## Installation

### Prerequisites

- Docker
- Python 3.10+
- [Factorio](https://www.factorio.com/) (version 2.0.73 or later), only for optional rendering.

```bash
# Core FLE SDK package
pip install factorio-learning-environment

# With optional features
pip install factorio-learning-environment[eval]      # For running experiments
pip install factorio-learning-environment[mcp]       # For MCP protocol support  
pip install factorio-learning-environment[psql]      # For PostgreSQL support
pip install factorio-learning-environment[eval,mcp,psql]  # All features

# Using uv (recommended)
uv sync
```

### Quickstart

Use the CLI:

```bash
# Activate venv
source .venv/bin/activate

# Start Factorio cluster
fle cluster start

# Run evaluation trajectories (requires [eval] dependencies)
fle eval --config configs/gym_run_config.json
```

## Environment

FLE is an agent evaluation environment built on the game of Factorio, a popular resource management simulation game.

Agents interact with **FLE** by code synthesis through a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program.
2. **Action**: The agent generates a Python program to perform their desired action.
3. **Feedback**: The environment executes the program, assigns variables, add classes/functions to the namespace, and provides an output stream.

## WASLab extension stack

This fork extends upstream FLE with a sealed, externally-scored benchmark and
training substrate. The REPL workflow above is unchanged; new work targets the
`factorio-envd` lease service and its native verifier:

```bash
# Start the Factorio pool, then the environment service
fle cluster start -n 4
uv run python -m fle.envd --runtime local --rcon-ports 27000 --audit-rcon-ports 27001 --port 8172
```

- **Customer contracts** — hidden, deterministically-generated demand streams;
  fulfillment is measured only by items crossing into immutable customer-owned
  sink depots, scored as `R = Σ wⱼ·(accepted/requested) − λ·Σ wⱼ·(1 − rⱼ)` and
  sealed with HMAC receipts. Reward hacking surface: internal production counts
  pay nothing.
- **World disruptions** — hidden shock schedules (resource exhaustion, power
  loss, severed logistics, biter waves) with per-product-network recovery
  measurement (`T_recovery`), so the optimal system cannot build a static
  factory and stop thinking.
- **Blueprint library** — agents save reusable factory fragments during
  training; placement debits exact materials and construction time. Scopes
  follow the generation lifecycle: evaluation runs stay ephemeral.
- **Map lifecycle manager** — generation quotas (fresh / inherited /
  pathological), recoverability-based retirement
  (`V_continue < V_restart − C_reset`), checkpoint persistence for
  continuation episodes.

Task specs carry these as additive fingerprint-covered fields (`customer`,
`perturbations`, `blueprint_scope`, `lineage_id`, `generation_id`); the
Verifiers v1 adapter (`factorio_v1`) maps snapshots to rewards, metrics, and
privileged-teacher packets for Prime-RL. See
[the contract benchmark substrate](docs/architecture/factorio-contract-benchmark.md)
and [the RLVR stack boundary](docs/architecture/factorio-rlvr-stack.md).

RolloutPlane provides the rollout control plane and evidence ledger for
training runs against this environment, and
[RolloutPlane Viz](https://github.com/HumanDotPy/RolloutPlaneViz) is the evidence
workbench for it. Both stay out of the rollout hot path.

## Contributing

Join our team and contribute to one of the AI research community's most challenging problems - building open-ended / unsaturateable evals for post-AGI frontier models. If you want to contribute, please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/JackHopkins/factorio-learning-environment)
