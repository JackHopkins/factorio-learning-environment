"""Condensed prompt experiments eval set.

This file contains experiments comparing condensed vs full system prompts,
with and without image history pruning.

Experimental Matrix (2x2 factorial design):
┌─────────────────────┬─────────────────────┬─────────────────────────────┐
│                     │ All Images          │ Latest Image Only           │
├─────────────────────┼─────────────────────┼─────────────────────────────┤
│ Full Prompt (~28k)  │ full_prompt         │ full_prompt_latest_image    │
│                     │ (control)           │                             │
├─────────────────────┼─────────────────────┼─────────────────────────────┤
│ Condensed (~10k)    │ condensed_prompt    │ condensed_prompt_latest_img │
└─────────────────────┴─────────────────────┴─────────────────────────────┘

Run all condensed prompt experiments:

    inspect eval-set fle/eval/inspect_integration/condensed_prompt_experiments.py \\
        --log-dir logs-condensed-experiments \\
        --max-tasks 4

Or run from fle CLI:

    fle inspect-eval --eval-set-file fle/eval/inspect_integration/condensed_prompt_experiments.py \\
        --log-dir logs-condensed-experiments \\
        --max-tasks 4

Run specific experiments:

    inspect eval condensed_prompt_experiments.py@open_play_full_prompt \\
        --model anthropic/claude-sonnet-4-20250514

Experiments evaluate:
1. Score impact: Does condensed prompt hurt factory-building performance?
2. Latency impact: How much faster is inference with smaller system prompt?
3. Image history: Does pruning images affect visual reasoning quality?
4. Combined: What's the maximum context reduction with acceptable score loss?
"""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect_integration.solver_variants import (
    factorio_full_prompt_solver,
    factorio_full_prompt_latest_image_solver,
    factorio_condensed_prompt_solver,
    factorio_condensed_prompt_latest_image_solver,
)
from fle.eval.inspect_integration.scorers import (
    production_score,
    achievements,
    technologies,
)
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)


# Solver mapping for condensed prompt experiments
CONDENSED_PROMPT_SOLVER_MAP = {
    "full_prompt": factorio_full_prompt_solver,
    "full_prompt_latest_image": factorio_full_prompt_latest_image_solver,
    "condensed_prompt": factorio_condensed_prompt_solver,
    "condensed_prompt_latest_image": factorio_condensed_prompt_latest_image_solver,
}


def _create_condensed_prompt_task(solver_name: str) -> Task:
    """Create an open_play experiment task with a specific solver variant."""
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(OPEN_PLAY_PRODUCTION)

    solver_fn = CONDENSED_PROMPT_SOLVER_MAP.get(solver_name)
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
            for i in range(4)
        ],
        solver=solver_fn(),
        scorer=[production_score(), achievements(), technologies()],
        name=f"open_play_{solver_name}",
    )


# =============================================================================
# CONTROL: Full Prompt with All Images
# =============================================================================


@task
def open_play_full_prompt():
    """Control: Full system prompt (~28k tokens) with all images kept.

    This is the baseline experiment for comparison. Uses:
    - Full system prompt with complete API documentation
    - All images kept in message history
    - Standard message trimming (25 -> 16 messages)

    Expected characteristics:
    - Highest token usage per step
    - Slowest inference (largest context)
    - Best API understanding (most detailed docs)
    - Full visual history for comparison

    This serves as the control condition against which we measure:
    1. Score regression from condensed prompts
    2. Latency improvement from context reduction
    """
    return _create_condensed_prompt_task("full_prompt")


# =============================================================================
# EXPERIMENT 1: Full Prompt, Latest Image Only
# =============================================================================


@task
def open_play_full_prompt_latest_image():
    """Full system prompt with only the latest image shown.

    Uses the full ~28k token system prompt but strips images from message
    history, keeping only the most recent image. This tests whether the
    model needs visual history for effective factory building.

    Configuration:
    - Full system prompt (~28k tokens)
    - Images stripped from history
    - Only latest image shown

    Expected characteristics:
    - Moderate token reduction (images are ~1-2k tokens each)
    - Faster inference than control (fewer image tokens)
    - Tests: Is visual history important for reasoning?

    Key question: Does the model need to compare past images to current,
    or is the current image + text history sufficient?
    """
    return _create_condensed_prompt_task("full_prompt_latest_image")


# =============================================================================
# EXPERIMENT 2: Condensed Prompt, All Images
# =============================================================================


@task
def open_play_condensed_prompt():
    """Condensed system prompt (~10k tokens) with all images kept.

    Uses a pre-condensed version of the system prompt generated by
    Claude Opus 4.5. Preserves all essential API semantics while
    reducing token count by ~65%.

    Configuration:
    - Condensed system prompt (~10k tokens vs ~28k)
    - All images kept in history
    - Standard message trimming

    Expected characteristics:
    - ~65% reduction in system prompt tokens
    - Faster time-to-first-token
    - Lower cost per step
    - Tests: Can the model work with concise documentation?

    Key question: Does the model understand the API equally well
    with condensed vs full documentation?
    """
    return _create_condensed_prompt_task("condensed_prompt")


# =============================================================================
# EXPERIMENT 3: Condensed Prompt, Latest Image Only (Maximum Reduction)
# =============================================================================


@task
def open_play_condensed_prompt_latest_image():
    """Condensed system prompt with only the latest image.

    Combines both context reduction strategies for maximum efficiency:
    1. Condensed system prompt (~10k tokens vs ~28k)
    2. Image history stripping (only latest image shown)

    This is the most aggressive context reduction while still
    maintaining visual feedback capability.

    Configuration:
    - Condensed system prompt (~10k tokens)
    - Images stripped from history
    - Only latest image shown

    Expected characteristics:
    - Maximum token reduction
    - Fastest inference
    - Lowest cost per step
    - Tests: Combined impact of both reductions

    Key question: What's the cumulative score impact of both
    reductions? Is it additive, sub-additive, or super-additive?
    """
    return _create_condensed_prompt_task("condensed_prompt_latest_image")


# =============================================================================
# Utility Functions
# =============================================================================


def list_condensed_prompt_experiments():
    """Print all available condensed prompt experiment tasks."""
    print("=" * 70)
    print("CONDENSED PROMPT EXPERIMENTS")
    print("=" * 70)
    print()
    print("Experimental Matrix (2x2 factorial design):")
    print()
    print("┌─────────────────────┬─────────────────────┬─────────────────────────────┐")
    print("│                     │ All Images          │ Latest Image Only           │")
    print("├─────────────────────┼─────────────────────┼─────────────────────────────┤")
    print("│ Full Prompt (~28k)  │ full_prompt         │ full_prompt_latest_image    │")
    print("│                     │ (control)           │                             │")
    print("├─────────────────────┼─────────────────────┼─────────────────────────────┤")
    print("│ Condensed (~10k)    │ condensed_prompt    │ condensed_prompt_latest_img │")
    print("└─────────────────────┴─────────────────────┴─────────────────────────────┘")
    print()
    print("Available tasks:")
    for solver_name, solver_fn in CONDENSED_PROMPT_SOLVER_MAP.items():
        docstring = solver_fn.__doc__ or "No description"
        first_line = docstring.split("\n")[0].strip()
        print(f"  open_play_{solver_name}: {first_line}")
    print()
    print("Run all experiments:")
    print(
        "  inspect eval-set condensed_prompt_experiments.py --log-dir logs --max-tasks 4"
    )
    print()
    print("Run specific experiments:")
    print("  inspect eval condensed_prompt_experiments.py@open_play_full_prompt")
    print("  inspect eval condensed_prompt_experiments.py@open_play_condensed_prompt")
    print()
    print("Analysis questions:")
    print("  1. Score impact: condensed vs full prompt")
    print("  2. Latency impact: latest-image vs all-images")
    print("  3. Combined: maximum reduction with acceptable score loss")


if __name__ == "__main__":
    list_condensed_prompt_experiments()
