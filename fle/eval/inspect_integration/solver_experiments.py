"""Solver variant experiments eval set.

This file contains all solver variant tasks for parallel comparison experiments.
Run all experiments with:

    inspect eval-set fle/eval/inspect_integration/solver_experiments.py \
        --log-dir logs-solver-experiments \
        --max-tasks 8

Or run specific tasks:

    inspect eval solver_experiments.py@open_play_fat_hud,solver_experiments.py@open_play_hud \
        --max-tasks 2

Available solver variants:
- unbounded: Baseline unbounded solver (full context)
- controlled: Controlled solver for throughput tasks
- no_image_history: Strips images from history, only shows latest
- aggressive_trim: Keeps only 8 recent messages
- text_only: No images at all, text observations only
- minimal_context: Most aggressive - no entities, no images, 6 messages
- hud: Fixed 3-message context with visual rendering
- hud_text_only: Fixed 3-message context, no images
- fat_hud: Fixed context with 3 images at zoom levels 16, 32, 64
- balanced: Moderate optimizations (strips old images, 12 messages)
- reasoning_only: Keeps reasoning blocks, strips code from history
"""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect_integration.solver import (
    factorio_controlled_solver,
    factorio_unbounded_solver,
)
from fle.eval.inspect_integration.solver_variants import (
    factorio_no_image_history_solver,
    factorio_aggressive_trim_solver,
    factorio_text_only_solver,
    factorio_minimal_context_solver,
    factorio_hud_solver,
    factorio_hud_text_only_solver,
    factorio_fat_hud_solver,
    factorio_balanced_solver,
    factorio_reasoning_only_solver,
)
from fle.eval.inspect_integration.scorers import (
    production_score,
    technologies,
    achievements,
)
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)


# Solver mapping for all experiment variants
SOLVER_MAP = {
    "unbounded": factorio_unbounded_solver,
    "controlled": factorio_controlled_solver,
    "no_image_history": factorio_no_image_history_solver,
    "aggressive_trim": factorio_aggressive_trim_solver,
    "text_only": factorio_text_only_solver,
    "minimal_context": factorio_minimal_context_solver,
    "hud": factorio_hud_solver,
    "hud_text_only": factorio_hud_text_only_solver,
    "fat_hud": factorio_fat_hud_solver,
    "balanced": factorio_balanced_solver,
    "reasoning_only": factorio_reasoning_only_solver,
}


def _create_experiment_task(solver_name: str) -> Task:
    """Create an open_play experiment task with a specific solver variant."""
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(OPEN_PLAY_PRODUCTION)

    solver_fn = SOLVER_MAP.get(solver_name)
    if not solver_fn:
        raise ValueError(f"Unknown solver: {solver_name}")

    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target="maximize",
                metadata={
                    "env_id": OPEN_PLAY_PRODUCTION,
                    "trajectory_length": int(
                        os.getenv(
                            "FLE_TRAJECTORY_LENGTH", str(task_config.trajectory_length)
                        )
                    ),
                    "goal_description": task_config.goal_description,
                    "task_type": "unbounded_production",
                    "solver_variant": solver_name,
                },
                id=f"open_play_{solver_name}_eval_{i}",
            )
            for i in range(32)
        ],
        solver=solver_fn(),
        scorer=[production_score(), technologies(), achievements()],
        name=f"open_play_{solver_name}",
    )


# =============================================================================
# Solver Experiment Tasks
# =============================================================================
# Each task uses a specific solver variant for parallel comparison.
# Run with: inspect eval-set solver_experiments.py --log-dir logs --max-tasks 8


@task
def open_play_unbounded():
    """Baseline: Full unbounded solver with complete context."""
    return _create_experiment_task("unbounded")


@task
def open_play_no_image_history():
    """Experiment: Strip images from history, only show latest image."""
    return _create_experiment_task("no_image_history")


@task
def open_play_aggressive_trim():
    """Experiment: Keep only 8 recent messages (aggressive trimming)."""
    return _create_experiment_task("aggressive_trim")


@task
def open_play_text_only():
    """Experiment: No images at all, text observations only."""
    return _create_experiment_task("text_only")


@task
def open_play_minimal_context():
    """Experiment: Most aggressive - no entities, no images, 6 messages."""
    return _create_experiment_task("minimal_context")


@task
def open_play_hud():
    """Experiment: Fixed 3-message HUD context with visual rendering."""
    return _create_experiment_task("hud")


@task
def open_play_hud_text_only():
    """Experiment: Fixed 3-message HUD context, no images."""
    return _create_experiment_task("hud_text_only")


@task
def open_play_fat_hud():
    """Experiment: Fixed HUD with 3 images at zoom levels 16, 32, 64."""
    return _create_experiment_task("fat_hud")


@task
def open_play_balanced():
    """Experiment: Moderate optimizations (strips old images, 12 messages)."""
    return _create_experiment_task("balanced")


@task
def open_play_reasoning_only():
    """Experiment: Keep reasoning blocks, strip code from history."""
    return _create_experiment_task("reasoning_only")


# =============================================================================
# Utility Functions
# =============================================================================


def list_experiments():
    """Print all available experiment tasks."""
    print("Available solver experiments:")
    print("=" * 60)
    for solver_name, solver_fn in SOLVER_MAP.items():
        docstring = solver_fn.__doc__ or "No description"
        first_line = docstring.split("\n")[0].strip()
        print(f"  open_play_{solver_name}: {first_line}")
    print()
    print("Run all experiments:")
    print("  inspect eval-set solver_experiments.py --log-dir logs --max-tasks 8")
    print()
    print("Run specific experiments:")
    print(
        "  inspect eval solver_experiments.py@open_play_hud,solver_experiments.py@open_play_fat_hud"
    )


if __name__ == "__main__":
    list_experiments()
