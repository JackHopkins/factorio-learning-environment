"""
Unbounded task definitions.

This module contains unbounded task definitions as Pydantic models,
replacing the previous JSON-based definitions for better type safety,
validation, and code reusability.

Task types:
- UnboundedThroughputTaskConfig: Still tracks a specific entity but without strict quota
- DefaultTaskConfig: Open-ended tasks (legacy, shorter trajectory)
- UnboundedProductionTaskConfig: Open-play tasks that track cumulative production score
"""

from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Union
from fle.env.game_types import Prototype

# Task name constants for easy importing
IRON_GEAR_WHEEL_THROUGHPUT_UNBOUNDED = (
    "iron_gear_wheel_throughput_unbounded_steps_show_steps_true"
)
OPEN_PLAY = "open_play"
OPEN_PLAY_PRODUCTION = "open_play_production"


class UnboundedThroughputTaskConfig(BaseModel):
    """Configuration for unbounded throughput tasks."""

    task_type: Literal["unbounded_throughput"] = "unbounded_throughput"
    num_agents: int = 1
    trajectory_length: int = 16
    holdout_wait_period: int = 60
    pre_holdout_wait_period: int = 60
    show_number_of_steps_left_in_prompt: bool = True

    # These must be defined per task
    throughput_entity: Union[str, Prototype]
    goal_description: str
    task_key: str

    class Config:
        frozen = True
        extra = "forbid"
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        data = self.dict()
        # Convert Prototype to string if necessary
        if isinstance(self.throughput_entity, Prototype):
            data["throughput_entity"] = self.throughput_entity.value
            if isinstance(data["throughput_entity"], tuple):
                data["throughput_entity"] = data["throughput_entity"][0]
        return data


class DefaultTaskConfig(BaseModel):
    """Configuration for default/open-play tasks."""

    task_type: Literal["default"] = "default"
    num_agents: int = 1
    trajectory_length: int = 5000

    # These must be defined per task
    goal_description: str
    task_key: str

    class Config:
        frozen = True
        extra = "forbid"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return self.dict()


class UnboundedProductionTaskConfig(BaseModel):
    """Configuration for unbounded production tasks (build biggest factory).

    These tasks:
    - Track cumulative production score (total economic value of all production)
    - Have no quota or target - the goal is to maximize production
    - Are designed for long trajectories (5000 steps by default)
    - Use the unbounded solver and unbounded scorer
    """

    task_type: Literal["unbounded_production"] = "unbounded_production"
    num_agents: int = 1
    trajectory_length: int = Field(
        default=5000, description="Number of steps in trajectory"
    )
    holdout_wait_period: int = 60
    pre_holdout_wait_period: int = 60

    # Task description
    goal_description: str
    task_key: str

    class Config:
        frozen = True
        extra = "forbid"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return self.dict()


# Define unbounded throughput tasks
iron_gear_wheel_throughput_unbounded = UnboundedThroughputTaskConfig(
    goal_description="Create an automatic iron gear wheel factory.",
    throughput_entity=Prototype.IronGearWheel,
    task_key=IRON_GEAR_WHEEL_THROUGHPUT_UNBOUNDED,
)

# Define default/open-play tasks
open_play = DefaultTaskConfig(
    goal_description="Achieve the highest automatic production score rate",
    task_key=OPEN_PLAY,
)

# Define unbounded production tasks (for Inspect evaluation)
open_play_production = UnboundedProductionTaskConfig(
    goal_description="""Build the biggest automated factory possible.

Your goal is to maximize your automated production score income by:
- Establishing efficient automatic resource extraction (iron, copper, coal, stone)
- Building self-fueling power generation infrastructure
- Creating automated production chains for increasingly complex items with assemblers
- Scaling up production capacity over time
- Optimizing factory layout and logistics

The production score reflects the total economic value of everything your factory produces.
More complex items (circuits, science packs, etc.) are worth more than raw materials.
Ticks represent the wall-time of the environment. 

# Tips for getting started
---

## Writing Policies for Maximum Information Extraction

Each policy execution is a **sampling opportunity** against a stochastic environment. Maximize bits extracted per sample.

**Shallow scripts waste samples.** A procedural 100-line script fails at line 74 because of environmental drift. Use logical branching to deal with expected future conditions.

Adaptive policies extract information continuously:

Every if/else is a bit extracted and used
Every status check that changes behavior is information captured
Every assertion is an early exit that preserves budget for the next sample
Nested branches cover combinatorial space — A linear script tests one path. n nested binary branches cover 2^n world-states in a single policy. The structure itself is a exploration strategy.

**Principles:**

1. **Observe → Branch → Act** — Never act without observing. Never observe without branching on the result.

2. **Fail fast at gates** — Assert preconditions early. A failed assertion at line 10 lets you re-sample; failure at line 90 is wasted compute.

3. **Diff state, don't assume it** — `inventory.get()` before crafting, `entity.status` before depending on it. The environment changed since your last sample.

4. **Small action quanta** — Each block: observe, decide, act, observe result. The tighter this loop, the more adaptive the policy.

5. **Recovery is information too** — `try/except` with fallback isn't defensive coding—it's branching on implicit observations (collision detected, resource missing).

---

Focus on building sustainable, scalable automation rather than manual crafting to maximise your production score rate.""",
    task_key=OPEN_PLAY_PRODUCTION,
    trajectory_length=5000,
)


# Create dictionaries for easy lookup by task key
UNBOUNDED_THROUGHPUT_TASKS = {
    IRON_GEAR_WHEEL_THROUGHPUT_UNBOUNDED: iron_gear_wheel_throughput_unbounded,
}

DEFAULT_TASKS = {
    OPEN_PLAY: open_play,
}

UNBOUNDED_PRODUCTION_TASKS = {
    OPEN_PLAY_PRODUCTION: open_play_production,
}

# Combined lookup for all unbounded tasks
UNBOUNDED_TASKS = {
    **UNBOUNDED_THROUGHPUT_TASKS,
    **DEFAULT_TASKS,
    **UNBOUNDED_PRODUCTION_TASKS,
}


def get_unbounded_task(
    task_key: str,
) -> Union[
    UnboundedThroughputTaskConfig, DefaultTaskConfig, UnboundedProductionTaskConfig
]:
    """Get an unbounded task configuration by its key.

    Args:
        task_key: The task identifier

    Returns:
        Task configuration instance for the requested task

    Raises:
        KeyError: If the task_key doesn't exist
    """
    if task_key not in UNBOUNDED_TASKS:
        raise KeyError(f"Unknown unbounded task: {task_key}")
    return UNBOUNDED_TASKS[task_key]


def list_unbounded_tasks() -> list[str]:
    """Get a list of all available unbounded task keys."""
    return list(UNBOUNDED_TASKS.keys())
