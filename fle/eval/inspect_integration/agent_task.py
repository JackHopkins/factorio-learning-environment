"""Factorio task using custom Inspect Agent for full trajectory logging."""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from typing import List

from fle.eval.inspect_integration.solver import factorio_controlled_solver
from fle.eval.inspect_integration.scorers import simple_production_score
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS


def create_factorio_task(env_id: str):
    """Create a task with the specific env_id as the name"""

    @task
    def factorio_task():
        """Dynamic Factorio task with environment-specific name"""
        return Task(
            dataset=create_agent_dataset(),
            solver=factorio_controlled_solver(),
            scorer=simple_production_score(),
            name=env_id,  # Use the actual task name
        )

    # Set the function name to match the env_id for better logging
    factorio_task.__name__ = env_id
    return factorio_task


@task
def factorio_agent_evaluation():
    """Factorio evaluation using custom Agent with full trajectory logging"""
    # Get env_id from environment to set proper task name
    env_id = os.getenv("FLE_ENV_ID", "iron_ore_throughput")

    return Task(
        dataset=create_agent_dataset(),
        solver=factorio_controlled_solver(),  # Use controlled solver for full trajectory
        scorer=simple_production_score(),
        name=env_id,  # Use the actual task name for better identification
    )


def create_agent_dataset() -> List[Sample]:
    """Create single sample dataset - Inspect handles multiple attempts via epochs"""

    # Get configuration from environment (set by CLI)
    env_id = os.getenv("FLE_ENV_ID", "iron_ore_throughput")
    model = os.getenv("FLE_MODEL", "openai/gpt-4o-mini")

    # Get proper task description from task config
    task_config = THROUGHPUT_TASKS.get(env_id)
    if task_config:
        task_description = task_config.goal_description
        quota = task_config.quota
    else:
        task_description = f"Create an automatic {env_id.replace('_', '-')} factory"
        quota = 16

    # Create single sample - Inspect will run it multiple times via --epochs
    sample = Sample(
        input=f"Begin task: {task_description}",
        target="success",
        metadata={
            "env_id": env_id,
            "model": model,
            "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
            "expected_production_score": float(quota),
        },
        id=f"{env_id}_pass_at_evaluation",
    )

    print(f"📊 Created 1 sample for Pass@N evaluation: {env_id}, model: {model}")
    print(
        "💡 Use --pass-n 8 or --epochs 8 --epochs-reducer pass_at_8 for Pass@8 evaluation"
    )
    return [sample]
