<h1 align="center">Factorio Learning Environment</h1>
<p align="center">
  <a href="https://jackhopkins.github.io/factorio-learning-environment/leaderboard">Leaderboard</a> | <a href="https://arxiv.org/abs/2503.09617">Paper</a> | <a href="https://jackhopkins.github.io/factorio-learning-environment/versions/0.3.0.html">Website</a>| <a href="https://discord.gg/zKaV2skewa">Discord (#factorio-learning-env)</a>
</p>

<p align="center">
An open source framework for developing and evaluating LLM agents in the game of <a href="https://factorio.com/">Factorio</a>.
</p>

<p align="center">
<img src="https://github.com/JackHopkins/factorio-learning-environment/raw/main/docs/assets/videos/compressed_sulfuric_acid.webp" width="485" height="364" controls/>
<img src="https://github.com/JackHopkins/factorio-learning-environment/raw/main/docs/assets/videos/compressed_red_science.webp" width="485" height="364" controls/>
</p>
<p align="center"><em>Claude Opus 4.1 Plays Factorio</em></p>

## Why FLE?

We provide two settings:

1. **Lab-play**: 24 structured tasks with fixed resources.
2. **Open-play** An unbounded task of building the largest possible factory on a procedurally generated map.

Our results demonstrate that models still lack strong spatial reasoning. In lab-play, we find that while LLMs
exhibit promising short-horizon skills, they are unable to operate effectively in constrained environments, reflecting limitations in error analysis. In open-play, while LLMs discover automation strategies that improve growth (e.g electric-powered drilling), they fail to achieve complex automation (e.g electronic-circuit manufacturing).

## Quick Links

- [Installation](#installation)
- [Documentation](https://jackhopkins.github.io/factorio-learning-environment/sphinx/build/html/)
- [Examples](#examples)
- [Contributing](#contributing)

## Installation

### Prerequisites

- Docker
- Python 3.10+
- [Factorio](https://www.factorio.com/) (version 1.1.110), only for optional rendering.

### Installation

```bash
# Core FLE SDK package
pip install factorio-learning-environment
uv add factorio-learning-environment

# With optional features
pip install factorio-learning-environment[eval]      # For running experiments
pip install factorio-learning-environment[mcp]       # For MCP protocol support  
pip install factorio-learning-environment[psql]      # For PostgreSQL support
pip install factorio-learning-environment[eval,mcp,psql]  # All features

# Using uv (recommended)
uv add factorio-learning-environment[eval]
```

### Quickstart

Use the CLI:

```bash
# Start Factorio cluster
fle cluster start

# Run evaluation trajectories (requires [eval] dependencies)
fle eval --config configs/gym_run_config.json
```

> When you run `fle init` or `fle eval` for the first time, an `.env` file and a `configs/` directory with example configurations are created automatically

## Environment

FLE is an agent evaluation environment built on the game of Factorio, a popular resource management simulation game.

Agents interact with **FLE** by code synthesis through a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program.
2. **Action**: The agent generates a Python program to perform their desired action.
3. **Feedback**: The environment executes the program, assigns variables, add classes/functions to the namespace, and provides an output stream.

## Examples

```python
# 1. Get iron patch and place mining drill
drill = place_entity(
    entity=Prototype.MiningDrill,
    position=nearest(Resource.IronOre),
    direction=Direction.NORTH
)
# 2. Add output storage
chest = place_entity_next_to(
    entity=Prototype.IronChest,
    reference_position=drill.drop_position,
    direction=Direction.SOUTH
)
# 3. Verify automation chain and observe entities
sleep(10) # Sleep for 10 seconds
assert drill.status == EntityStatus.WORKING
print(get_entities())
```

## Documentation

For complete documentation, visit: https://jackhopkins.github.io/factorio-learning-environment/sphinx/build/html/

## Contributing

Join our team and contribute to one of the AI research community's most challenging problems - building open-ended / unsaturateable evals for post-AGI frontier models. If you want to contribute, please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/JackHopkins/factorio-learning-environment)