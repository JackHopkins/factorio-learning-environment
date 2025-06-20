# Factorio Gym Registry

This module provides a registry system for Factorio gym environments that allows you to create environments using the standard `gym.make()` interface.

## Overview

The registry system automatically discovers all task definitions in `eval/tasks/task_definitions/` and registers them as gym environments. This means you can create any Factorio environment using the familiar `gym.make()` pattern.

## Features

- **Automatic Discovery**: Automatically discovers all task definitions in `eval/tasks/task_definitions/`
- **Gym Integration**: All environments are registered with `gym` and can be created using `gym.make()`
- **Task Metadata**: Provides access to task descriptions, configurations, and metadata
- **Multi-agent Support**: Supports both single-agent and multi-agent environments
- **Command-line Tools**: Built-in tools for exploring and testing environments

## Quick Start

### 1. List Available Environments

```python
from gym_env.registry import list_available_environments

# Get all available environment IDs
env_ids = list_available_environments()
print(f"Available environments: {env_ids}")
```

Or use the command-line tool:

```bash
python env/src/gym_env/example_usage.py --list
```

### 2. Create an Environment

```python
import gym

# Create any available environment
env = gym.make("Factorio-iron_ore_throughput_16-v0")
```

### 3. Use the Environment

```python
# Reset the environment
obs = env.reset(options={'game_state': None})

# Take an action
action = Action(
    agent_idx=0,  # Which agent takes the action
    code='print("Hello Factorio!")',  # Python code to execute
    game_state=None,  # game state to reset to before running code
)

# Execute the action
obs, reward, terminated, truncated, info = env.step(action)

# Clean up
env.close()
```

## Available Environments

The registry automatically discovers all JSON task definition files and creates corresponding gym environments. Environment IDs follow the pattern:

```
Factorio-{task_key}-v0
```

### Example Environment IDs

- `Factorio-iron_ore_throughput_16-v0` - Iron ore production task
- `Factorio-iron_plate_throughput_16-v0` - Iron plate production task
- `Factorio-crude_oil_throughput_16-v0` - Crude oil production task
- `Factorio-open_play-v0` - Open-ended factory building
- `Factorio-automation_science_pack_throughput_16-v0` - Science pack production

## Command-Line Tools

### Environment Explorer

The `example_usage.py` script provides both interactive examples and command-line tools:

```bash
# Run interactive examples
python env/src/gym_env/example_usage.py

# List all environments
python env/src/gym_env/example_usage.py --list

# Show detailed information
python env/src/gym_env/example_usage.py --detail

# Search for specific environments
python env/src/gym_env/example_usage.py --search iron

# Output in gym.make() format
python env/src/gym_env/example_usage.py --gym-format
```

## API Reference

### Registry Functions

#### `list_available_environments() -> List[str]`
Returns a list of all registered environment IDs.

#### `get_environment_info(env_id: str) -> Optional[Dict[str, Any]]`
Returns detailed information about a specific environment.

#### `register_all_environments() -> None`
Manually trigger environment discovery and registration.

### Environment Creation

#### `gym.make(env_id: str, **kwargs) -> FactorioGymEnv`
Creates a Factorio gym environment. The environment will:
1. Load the task configuration from the JSON file
2. Create a Factorio instance
3. Set up the task environment
4. Return a ready-to-use gym environment

## Environment Interface

All environments follow the standard gym interface:

### Action Space
```python
{
    'agent_idx': Discrete(instance.num_agents),  # Index of the agent taking the action
    'game_state': Text(max_length=1000000),  # The game state to reset to before running code (GameState.to_raw() str)
    'code': Text(max_length=10000)  # The Python code to execute
}
```

### Observation Space
The observation space includes:
- `raw_text`: Output from the last action
- `entities`: List of entities on the map
- `inventory`: Current inventory state
- `research`: Research progress and technologies
- `game_info`: Game state (tick, time, speed)
- `score`: Current score
- `flows`: Production statistics
- `task_verification`: Task completion status
- `messages`: Inter-agent messages
- `serialized_functions`: Available functions

### Methods

- `reset(options: Dict[str, Any], seed: Optional[int] = None) -> Dict[str, Any]`
- `step(action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]`
- `close() -> None`

## Task Definitions

Task definitions are JSON files located in `eval/tasks/task_definitions/`. Each file defines:

```json
{
    "task_type": "throughput",
    "config": {
        "goal_description": "Create an automatic iron ore factory...",
        "throughput_entity": "iron-ore",
        "quota": 16,
        "trajectory_length": 128,
        "task_key": "iron_ore_throughput_16"
    }
}
```

## Adding New Tasks

To add a new task:

1. Create a JSON file in `eval/tasks/task_definitions/`
2. Define the task configuration following the existing format
3. The registry will automatically discover and register the new environment

## Complete Example

Here's a complete example that demonstrates the full workflow:

```python
import gym
from gym_env.registry import list_available_environments, get_environment_info
from gym_env.action import Action

# 1. List available environments
env_ids = list_available_environments()
print(f"Found {len(env_ids)} environments")

# 2. Get information about a specific environment
info = get_environment_info("Factorio-iron_ore_throughput_16-v0")
print(f"Description: {info['description']}")

# 3. Create the environment
env = gym.make("Factorio-iron_ore_throughput_16-v0")

# 4. Use the environment
obs = env.reset(options={'game_state': None})
print(f"Initial observation keys: {list(obs.keys())}")

# 5. Take actions
current_state = None
for step in range(5):
    action = Action(
        agent_idx=0,
        game_state=current_state,
        code=f'print("Step {step}: Hello Factorio!")'
    )
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated
    current_state = info['output_game_state']
    print(f"Step {step}: Reward={reward}, Done={done}")
    
    if done:
        break

# 6. Clean up
env.close()
```

## Requirements

- Factorio containers must be running and accessible
- All dependencies from the main project must be installed
- The task definitions directory must be accessible

## Error Handling

The registry includes error handling for:
- Missing task definition files
- Invalid JSON configurations
- Missing Factorio containers
- Environment creation failures

If an environment fails to load, a warning will be printed but the registry will continue to load other environments.

## Troubleshooting

### Environment Creation Fails

If `gym.make()` fails with connection errors:
1. Ensure Factorio containers are running
2. Check that the cluster setup is working
3. Verify network connectivity

### No Environments Found

If no environments are listed:
1. Check that the task definitions directory exists
2. Verify JSON files are valid
3. Check file permissions

### Import Errors

If you get import errors:
1. Ensure you're running from the correct directory
2. Check that all dependencies are installed
3. Verify the Python path includes the project root

## Advanced Usage

### Custom Environment Registration

You can also register custom environments programmatically:

```python
from gym_env.registry import _registry

_registry.register_environment(
    env_id="Factorio-CustomTask-v0",
    task_key="custom_task",
    task_config_path="/path/to/custom_task.json",
    description="My custom task",
    num_agents=2
)
```

### Multi-Agent Environments

The registry supports multi-agent environments. When creating a multi-agent environment, specify the number of agents:

```python
# Create a multi-agent environment
env = gym.make("Factorio-MultiAgentTask-v0")

# Actions for different agents
action1 = Action(agent_idx=0, code='print("Agent 0 action")', game_state=None)
action2 = Action(agent_idx=1, code='print("Agent 1 action")', game_state=None)
```

## Testing

Run the test suite to verify the registry is working correctly:

```bash
python env/tests/gym_env/test_registry.py
```

This registry system provides a clean, standardized interface for working with Factorio gym environments, making it easy to experiment with different tasks and integrate with existing gym-based frameworks. 