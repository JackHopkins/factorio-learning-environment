"""
Unified task registry for all task definitions.

This module provides a central registry for all task configurations,
eliminating the need for try-except blocks and providing clear task discovery.
"""

from typing import Dict, Any
from pydantic import BaseModel

# Import task configurations from all modules
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import (
    THROUGHPUT_TASKS,
    list_throughput_tasks,
)
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_TASKS,
    list_unbounded_tasks,
)
from fle.eval.tasks.task_definitions.multiagent.multiagent_tasks import (
    MULTIAGENT_TASKS,
    list_multiagent_tasks,
)

# Import task classes for type mapping
from fle.eval.tasks import (
    ThroughputTask,
    UnboundedThroughputTask,
    DefaultTask,
    TaskABC,
)


class TaskRegistry:
    """Central registry for all task definitions."""

    def __init__(self):
        """Initialize the task registry with all available tasks."""
        # Combine all task dictionaries
        self._all_tasks = {}

        # Add throughput tasks
        self._all_tasks.update(THROUGHPUT_TASKS)

        # Add unbounded tasks
        self._all_tasks.update(UNBOUNDED_TASKS)

        # Add multiagent tasks
        self._all_tasks.update(MULTIAGENT_TASKS)

        # Map task types to their implementation classes
        self._task_type_to_class = {
            "throughput": ThroughputTask,
            "unbounded_throughput": UnboundedThroughputTask,
            "default": DefaultTask,
        }

    def get_task_config(self, task_key: str) -> BaseModel:
        """Get a task configuration by its key.

        Args:
            task_key: The task identifier

        Returns:
            Task configuration instance

        Raises:
            KeyError: If the task_key doesn't exist
        """
        if task_key not in self._all_tasks:
            available = list(self._all_tasks.keys())
            raise KeyError(
                f"Unknown task: {task_key}. "
                f"Available tasks: {', '.join(available[:5])}..."
                f" ({len(available)} total)"
            )
        return self._all_tasks[task_key]

    def create_task(self, task_key: str) -> TaskABC:
        """Create a task instance from its key.

        Args:
            task_key: The task identifier

        Returns:
            TaskABC instance ready to use

        Raises:
            KeyError: If the task_key doesn't exist
            ValueError: If the task type is not supported
        """
        # Get the configuration
        task_config = self.get_task_config(task_key)

        # Convert to dictionary
        config_dict = task_config.to_dict()

        # Extract and remove task type and num_agents
        task_type = config_dict.pop("task_type")
        config_dict.pop("num_agents", None)  # Remove if present

        # Get the appropriate task class
        if task_type not in self._task_type_to_class:
            raise ValueError(f"Unsupported task type: {task_type}")

        task_class = self._task_type_to_class[task_type]

        # Create and return the task instance
        return task_class(**config_dict)

    def list_all_tasks(self) -> list[str]:
        """Get a list of all available task keys."""
        return list(self._all_tasks.keys())

    def list_tasks_by_category(self) -> Dict[str, list[str]]:
        """Get tasks organized by category."""
        return {
            "throughput": list_throughput_tasks(),
            "unbounded": list_unbounded_tasks(),
            "multiagent": list_multiagent_tasks(),
        }

    def get_task_info(self, task_key: str) -> Dict[str, Any]:
        """Get detailed information about a task.

        Args:
            task_key: The task identifier

        Returns:
            Dictionary with task information including type, description, etc.
        """
        config = self.get_task_config(task_key)
        config_dict = config.to_dict()

        return {
            "task_key": task_key,
            "task_type": config_dict.get("task_type"),
            "num_agents": config_dict.get("num_agents", 1),
            "goal_description": config_dict.get("goal_description"),
            "trajectory_length": config_dict.get("trajectory_length"),
        }

    def task_exists(self, task_key: str) -> bool:
        """Check if a task exists in the registry.

        Args:
            task_key: The task identifier

        Returns:
            True if the task exists, False otherwise
        """
        return task_key in self._all_tasks


# Create a global registry instance
_task_registry = TaskRegistry()


# Export convenient functions
def get_task_config(task_key: str) -> BaseModel:
    """Get a task configuration by its key."""
    return _task_registry.get_task_config(task_key)


def create_task(task_key: str) -> TaskABC:
    """Create a task instance from its key."""
    return _task_registry.create_task(task_key)


def list_all_tasks() -> list[str]:
    """Get a list of all available task keys."""
    return _task_registry.list_all_tasks()


def list_tasks_by_category() -> Dict[str, list[str]]:
    """Get tasks organized by category."""
    return _task_registry.list_tasks_by_category()


def get_task_info(task_key: str) -> Dict[str, Any]:
    """Get detailed information about a task."""
    return _task_registry.get_task_info(task_key)


def task_exists(task_key: str) -> bool:
    """Check if a task exists in the registry."""
    return _task_registry.task_exists(task_key)
