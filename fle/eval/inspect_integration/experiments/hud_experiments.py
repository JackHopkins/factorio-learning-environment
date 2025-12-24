"""HUD solver experiments eval set.

This file contains HUD (Heads-Up Display) solver variant tasks for comparison experiments.
HUD solvers use a fixed context window that doesn't grow with trajectory length.

Run all HUD experiments with:

    inspect eval-set fle/eval/inspect_integration/hud_experiments.py \
        --log-dir logs-hud-experiments \
        --max-tasks 4

Or run from fle CLI:

    fle inspect-eval --eval-set-file fle/eval/inspect_integration/hud_experiments.py \
        --log-dir logs-hud-experiments \
        --max-tasks 4

Or run specific tasks:

    inspect eval hud_experiments.py@open_play_hud,hud_experiments.py@open_play_fat_hud \
        --max-tasks 2

Available HUD solver variants:
- hud: Fixed 3-message context with visual rendering (1 image)
- hud_text_only: Fixed 3-message context, no images
- fat_hud: Fixed context with 3 images at zoom levels 16, 32, 64
"""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect_integration.solver_variants import (
    factorio_hud_solver,
    factorio_hud_text_only_solver,
    factorio_fat_hud_solver,
)
from fle.eval.inspect_integration.scorers import production_score, technologies
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)


# Solver mapping for HUD experiment variants
HUD_SOLVER_MAP = {
    "hud": factorio_hud_solver,
    "hud_text_only": factorio_hud_text_only_solver,
    "fat_hud": factorio_fat_hud_solver,
}


def _create_hud_experiment_task(solver_name: str) -> Task:
    """Create an open_play experiment task with a specific HUD solver variant."""
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(OPEN_PLAY_PRODUCTION)

    solver_fn = HUD_SOLVER_MAP.get(solver_name)
    if not solver_fn:
        raise ValueError(f"Unknown HUD solver: {solver_name}")

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
                id=f"open_play_{solver_name}_eval",
            )
        ],
        solver=solver_fn(),
        scorer=[production_score(), technologies()],
        name=f"open_play_{solver_name}",
    )


# =============================================================================
# HUD Solver Experiment Tasks
# =============================================================================
# Each task uses a specific HUD solver variant for parallel comparison.
# Run with: inspect eval-set hud_experiments.py --log-dir logs --max-tasks 4


@task
def open_play_hud():
    """HUD solver: Fixed 3-message context with visual rendering (1 image).

    Uses a fixed message format each step:
    - System: Full system prompt
    - Assistant: Accumulated reasoning diary
    - User: HUD with current state, saved vars, last code/output + rendered image

    Benefits:
    - Bounded context regardless of trajectory length
    - Consistent context structure each step
    - Visual feedback for spatial reasoning

    Trade-offs:
    - Model must rely on diary and saved vars for continuity
    - No access to raw conversation history
    """
    return _create_hud_experiment_task("hud")


@task
def open_play_hud_text_only():
    """HUD solver: Fixed 3-message context, text only (no images).

    Uses a fixed message format each step:
    - System: Full system prompt
    - Assistant: Accumulated reasoning diary
    - User: HUD with current state, saved vars, last code/output (no image)

    Benefits:
    - Maximum context reduction with bounded history
    - Fastest inference due to no image processing
    - Consistent context structure

    Trade-offs:
    - No visual feedback
    - Relies entirely on text observations for spatial reasoning
    """
    return _create_hud_experiment_task("hud_text_only")


@task
def open_play_fat_hud():
    """HUD solver: Fixed context with 3 images at zoom levels 16, 32, 64.

    Uses a fixed message format each step with multiple visual perspectives:
    - System: Full system prompt
    - Assistant: Accumulated reasoning diary
    - User: HUD with 3 images at different zoom levels plus state info

    The three zoom levels provide:
    - Zoom 16 (Close): Detailed view of immediate surroundings (32x32 tiles)
    - Zoom 32 (Medium): Factory overview (64x64 tiles)
    - Zoom 64 (Far): Large-scale layout view (128x128 tiles)

    Benefits:
    - Rich multi-scale visual feedback
    - Better spatial reasoning across different scales
    - Bounded context regardless of trajectory length

    Trade-offs:
    - Higher token usage per step due to 3 images
    - Still relies on diary for continuity
    """
    return _create_hud_experiment_task("fat_hud")


# =============================================================================
# Utility Functions
# =============================================================================


def list_hud_experiments():
    """Print all available HUD experiment tasks."""
    print("Available HUD solver experiments:")
    print("=" * 60)
    for solver_name, solver_fn in HUD_SOLVER_MAP.items():
        docstring = solver_fn.__doc__ or "No description"
        first_line = docstring.split("\n")[0].strip()
        print(f"  open_play_{solver_name}: {first_line}")
    print()
    print("Run all HUD experiments:")
    print("  inspect eval-set hud_experiments.py --log-dir logs --max-tasks 4")
    print()
    print("Or from fle CLI:")
    print(
        "  fle inspect-eval --eval-set-file fle/eval/inspect_integration/hud_experiments.py \\"
    )
    print("      --log-dir logs --max-tasks 4")
    print()
    print("Run specific experiments:")
    print(
        "  inspect eval hud_experiments.py@open_play_hud,hud_experiments.py@open_play_fat_hud"
    )


if __name__ == "__main__":
    list_hud_experiments()
