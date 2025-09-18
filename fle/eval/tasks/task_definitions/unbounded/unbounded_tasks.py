"""
Unbounded task definitions.

This module contains unbounded task definitions as Pydantic models,
replacing the previous JSON-based definitions for better type safety,
validation, and code reusability.
"""

from pydantic import BaseModel
from typing import Literal, Dict, Any, Union
from fle.env.game_types import Prototype

# Task name constants for easy importing
IRON_GEAR_WHEEL_THROUGHPUT_UNBOUNDED = (
    "iron_gear_wheel_throughput_unbounded_steps_show_steps_true"
)
OPEN_PLAY = "open_play"


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


# Define unbounded throughput tasks
iron_gear_wheel_throughput_unbounded = UnboundedThroughputTaskConfig(
    goal_description="Create an automatic iron gear wheel factory.",
    throughput_entity=Prototype.IronGearWheel,
    task_key=IRON_GEAR_WHEEL_THROUGHPUT_UNBOUNDED,
)

# Define default/open-play tasks
open_play = DefaultTaskConfig(
    goal_description="- Build the biggest possible factory\n- Maximise automation, efficiency and scale",
    task_key=OPEN_PLAY,
)


# Create dictionaries for easy lookup by task key
UNBOUNDED_THROUGHPUT_TASKS = {
    IRON_GEAR_WHEEL_THROUGHPUT_UNBOUNDED: iron_gear_wheel_throughput_unbounded,
}

DEFAULT_TASKS = {
    OPEN_PLAY: open_play,
}

# Combined lookup for all unbounded tasks
UNBOUNDED_TASKS = {
    **UNBOUNDED_THROUGHPUT_TASKS,
    **DEFAULT_TASKS,
}


def get_unbounded_task(
    task_key: str,
) -> Union[UnboundedThroughputTaskConfig, DefaultTaskConfig]:
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
