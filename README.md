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
- [Reliable Video Run](#reliable-video-run)
- [Contributing](#contributing)

## Installation

### Prerequisites

- Docker
- Python 3.10+
- [Factorio](https://www.factorio.com/) (version 1.1.110), only for optional rendering.

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

## Reliable Video Run

Use the wrapper script to run an agent trajectory and generate:

- step screenshots (`step_000.png` ...),
- `run.mp4`,
- trajectory logs.

```bash
# Recommended default-lab run on reserved port 41000
./run_video_reliable.sh 41000
```

Select scenario profile explicitly:

```bash
WORLD_PROFILE=default_lab_scenario ./run_video_reliable.sh
WORLD_PROFILE=open_world ./run_video_reliable.sh
```

Optional run length/task overrides:

```bash
ENV_ID=iron_gear_wheel_throughput MAX_STEPS=10 ./run_video_reliable.sh 41000
```

Key behavior of this workflow:

- Uses model `claude-sonnet-4-6`.
- Uses real benchmark rendering (`SCREENSHOT_BACKEND=benchmark`).
- Runs save-per-step + catch-up rendering via `render_saves.py`.
- Enforces world preflight checks unless `SKIP_WORLD_CHECK=1` is manually set.

Artifacts are written to:

- Screenshots/video: `.fle/run_screenshots/v<version>/`
- Logs: `.fle/trajectory_logs/v<version>/`
- Saves used for rendering: `/tmp/fle-run-saves/v<version>/`

## Environment

FLE is an agent evaluation environment built on the game of Factorio, a popular resource management simulation game.

Agents interact with **FLE** by code synthesis through a **REPL** (Read-Eval-Print-Loop) pattern:

1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program.
2. **Action**: The agent generates a Python program to perform their desired action.
3. **Feedback**: The environment executes the program, assigns variables, add classes/functions to the namespace, and provides an output stream.

## Contributing

Join our team and contribute to one of the AI research community's most challenging problems - building open-ended / unsaturateable evals for post-AGI frontier models. If you want to contribute, please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/JackHopkins/factorio-learning-environment)
