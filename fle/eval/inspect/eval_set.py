"""Shared task factory functions for Factorio Inspect evaluations.

Provides create_throughput_task() and create_unbounded_production_task()
that both integration/ and sandbox/ eval sets use. The solver and sandbox
configuration are injected by the caller, keeping task definitions DRY.
"""

import os
from typing import List, Optional, Tuple, Union

from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.solver import Solver

from fle.eval.inspect.integration.scorers import (
    comprehensive_factorio_scorer,
    production_score,
    technologies,
    achievements,
    automated_production_score,
    code,
)
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)

# Re-export for convenience
__all__ = [
    "create_throughput_task",
    "create_unbounded_production_task",
    "THROUGHPUT_TASKS",
    "UNBOUNDED_PRODUCTION_TASKS",
    "OPEN_PLAY_PRODUCTION",
]


SandboxConfig = Optional[Tuple[str, str]]


def create_throughput_task(
    env_id: str,
    target: int = 16,
    solver: Optional[Solver] = None,
    sandbox: SandboxConfig = None,
) -> Task:
    """Create a throughput task for any environment.

    Args:
        env_id: Environment identifier (must be a key in THROUGHPUT_TASKS).
        target: Target production score string for the Sample.
        solver: Solver instance to use. If None, caller must set it.
        sandbox: Optional sandbox tuple, e.g. ("docker", "/path/to/compose.yaml").
    """
    task_config = THROUGHPUT_TASKS[env_id]

    sample_kwargs = dict(
        input=f"Begin task: {task_config.goal_description}",
        target=str(target),
        metadata={
            "env_id": env_id,
            "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
            "expected_production_score": float(task_config.quota),
        },
        id=f"{env_id}_eval",
    )
    if sandbox is not None:
        sample_kwargs["sandbox"] = sandbox

    task_kwargs = dict(
        dataset=[Sample(**sample_kwargs)],
        solver=solver,
        scorer=comprehensive_factorio_scorer(),
        name=env_id,
    )
    if sandbox is not None:
        task_kwargs["sandbox"] = sandbox

    return Task(**task_kwargs)


def create_unbounded_production_task(
    env_id: str,
    solver: Optional[Solver] = None,
    sandbox: SandboxConfig = None,
) -> Task:
    """Create an unbounded production task for open-play evaluation.

    Args:
        env_id: Environment identifier (must be a key in UNBOUNDED_PRODUCTION_TASKS).
        solver: Solver instance to use. If None, caller must set it.
        sandbox: Optional sandbox tuple, e.g. ("docker", "/path/to/compose.yaml").
    """
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(env_id)
    if not task_config:
        raise ValueError(f"Unknown unbounded production task: {env_id}")

    sample_kwargs = dict(
        input=f"Begin task: {task_config.goal_description}",
        target=task_config.goal_description,
        metadata={
            "env_id": env_id,
            "trajectory_length": int(
                os.getenv("FLE_TRAJECTORY_LENGTH", str(task_config.trajectory_length))
            ),
            "goal_description": task_config.goal_description,
            "task_type": "unbounded_production",
        },
        id=f"{env_id}_eval",
    )
    if sandbox is not None:
        sample_kwargs["sandbox"] = sandbox

    task_kwargs = dict(
        dataset=[Sample(**sample_kwargs)],
        solver=solver,
        scorer=[
            production_score(),
            technologies(),
            achievements(),
            automated_production_score(),
            code(),
        ],
        name=env_id,
    )
    if sandbox is not None:
        task_kwargs["sandbox"] = sandbox

    return Task(**task_kwargs)
