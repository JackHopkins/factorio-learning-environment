"""Main Inspect task for FLE evaluations."""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
import json
from pathlib import Path
from typing import List

from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS

# Import solvers and scorers (using simple version without Docker client)
from fle.eval.inspect_integration.controlled_solver import factorio_controlled_solver
from fle.eval.inspect_integration.simple_scorer import simple_production_score


@task
def factorio_evaluation():
    """Main Inspect task for FLE evaluations"""
    return Task(
        dataset=create_factorio_dataset(),
        solver=[
            factorio_controlled_solver(),
            # simple_factorio_agent_solver(),
            # simple_cleanup_solver(),
        ],
        scorer=simple_production_score(),
    )


def create_factorio_dataset() -> List[Sample]:
    """Convert current config format to Inspect samples"""
    samples = []

    for task_key in THROUGHPUT_TASKS.keys():
        for trial in range(8):  # 8 runs per model/task combination
            samples.append(
                Sample(
                    input=f"Evaluate {task_key}",
                    target="success",
                    metadata={
                        "env_id": task_key,
                        "trajectory_length": 64,  # From task config
                        "trial": trial,
                        "expected_production_score": 100.0,
                    },
                    id=f"{task_key}_{trial}",
                )
            )

    return samples


def create_factorio_dataset_from_config(config_path: str) -> List[Sample]:
    """Convert existing gym config to Inspect samples for backward compatibility"""
    samples = []
    config_file = Path(config_path)

    with open(config_file) as f:
        config_data = json.load(f)

    for i, entry in enumerate(config_data):
        samples.append(
            Sample(
                input="Trajectory",
                metadata={
                    "env_id": entry["env_id"],
                    "trajectory_length": 64,
                    "trial": i,
                },
                target={"expected_production_score": 100.0},
                id=f"{config_file.stem}_{i}",
            )
        )

    return samples
