"""Context reduction solver experiments eval set.

This file contains solver variants focused on reducing context size through
different strategies: removing images, stripping image history, or keeping
only reasoning blocks.

Run all context reduction experiments with:

    inspect eval-set fle/eval/inspect_integration/context_reduction_experiments.py \
        --log-dir logs-context-experiments \
        --max-tasks 4

Or run from fle CLI:

    fle inspect-eval --eval-set-file fle/eval/inspect_integration/context_reduction_experiments.py \
        --log-dir logs-context-experiments \
        --max-tasks 4

Or run specific tasks:

    inspect eval context_reduction_experiments.py@open_play_text_only \
        --model openai/gpt-4o

Available context reduction solver variants:
- text_only: No images at all, pure text observations (fastest inference)
- no_image_history: Strips images from history, only shows latest image (1 image/step)
- reasoning_only: Keeps reasoning blocks, strips code from history
- pruned_gamestate: Strips game state from history, keeps only program output
- condensed_prompt: Uses ~10k token system prompt instead of ~28k (Opus 4.5 condensed)
"""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect_integration.solver_variants import (
    factorio_text_only_solver,
    factorio_no_image_history_solver,
    factorio_reasoning_only_solver,
    factorio_aggressive_trim_solver,
    factorio_pruned_gamestate_solver,
    factorio_condensed_prompt_solver,
)
from fle.eval.inspect_integration.scorers import production_score, technologies
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)


# Solver mapping for context reduction experiment variants
CONTEXT_REDUCTION_SOLVER_MAP = {
    "text_only": factorio_text_only_solver,
    "no_image_history": factorio_no_image_history_solver,
    "reasoning_only": factorio_reasoning_only_solver,
    "aggressive_trim": factorio_aggressive_trim_solver,
    "pruned_gamestate": factorio_pruned_gamestate_solver,
    "condensed_prompt": factorio_condensed_prompt_solver,
}


def _create_context_reduction_task(solver_name: str) -> Task:
    """Create an open_play experiment task with a specific context reduction solver."""
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(OPEN_PLAY_PRODUCTION)

    solver_fn = CONTEXT_REDUCTION_SOLVER_MAP.get(solver_name)
    if not solver_fn:
        raise ValueError(f"Unknown context reduction solver: {solver_name}")

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


@task
def open_play_aggressive_trim():
    """Open play with aggressive-trim solver (keeps only 8 messages)."""
    return _create_context_reduction_task("aggressive_trim")


# =============================================================================
# Context Reduction Solver Experiment Tasks
# =============================================================================


@task
def open_play_text_only():
    """Text-only solver: No images at all, pure text observations.

    Completely disables image generation and rendering.
    Fastest possible inference due to minimal context.

    Benefits:
    - Maximum speed, minimal token usage
    - No image processing overhead
    - Works with non-multimodal models

    Trade-offs:
    - No visual feedback
    - Harder spatial reasoning without visual context
    - Must rely entirely on text entity descriptions
    """
    return _create_context_reduction_task("text_only")


@task
def open_play_no_image_history():
    """No-image-history solver: Strips images from history, shows only latest.

    Only the LATEST image is shown - older images are converted to text-only.
    This significantly reduces context size while still providing visual feedback.

    Benefits:
    - ~50-70% context reduction for image-heavy trajectories
    - Still provides current visual state
    - Good balance of speed and visual awareness

    Trade-offs:
    - Model can't reference older images for comparison
    - Can't visually track changes over time
    """
    return _create_context_reduction_task("no_image_history")


@task
def open_play_reasoning_only():
    """Reasoning-only solver: Keeps reasoning blocks, strips code from history.

    The key insight: the reasoning/thinking conveys what the code should do,
    so we don't need to keep the actual code in history. This dramatically
    reduces context size while maintaining the agent's understanding of
    what was attempted and why.

    Message format:
    - System: Full system prompt (cached)
    - History: Reasoning-only messages (code stripped)
    - Latest user: Full current observation

    Benefits:
    - ~60-80% context reduction vs full history
    - Maintains reasoning continuity and intent
    - Model understands what was tried and why

    Trade-offs:
    - Model can't see exact code from previous steps
    - May repeat similar code patterns
    - Relies on reasoning quality for context
    """
    return _create_context_reduction_task("reasoning_only")


@task
def open_play_pruned_gamestate():
    """Pruned-gamestate solver: Strips game state from history, keeps only program output.

    This solver prunes historical user messages to only keep program output (stdout/stderr),
    removing all game state observations from history. The current game state is always
    provided in full.

    Message format:
    - System: Full system prompt (cached)
    - Assistant messages: Full (reasoning and code preserved)
    - Historical user messages: Only program output - game state [omitted]
    - Latest user: Full current game state observation

    Benefits:
    - ~40-60% context reduction on user messages
    - Program output tells model what happened (success/error)
    - Current state tells model what to do next
    - Historical game states are redundant (current reflects cumulative changes)

    Trade-offs:
    - Model can't reference exact historical game states
    - Can't compare past vs current entity positions from text
    - Must infer past state from program outputs
    """
    return _create_context_reduction_task("pruned_gamestate")


@task
def open_play_condensed_prompt():
    """Condensed-prompt solver: Uses ~10k token system prompt instead of ~28k.

    This solver uses a pre-condensed version of the system prompt generated
    by Claude Opus 4.5. The condensed prompt preserves all essential API
    semantics while reducing token count by ~65%.

    Key differences from full prompt:
    - Types section: Compact notation, essential attributes only
    - Methods section: Concise signatures with key parameters
    - Manual: Core concepts only, no verbose examples
    - Task instructions: Streamlined strategy guidance

    Benefits:
    - ~65% reduction in system prompt tokens (28k -> 10k)
    - Faster time-to-first-token on every step
    - Lower cost per step
    - More headroom for context growth before trimming

    Trade-offs:
    - Less verbose explanations
    - Fewer examples in documentation
    - Model must infer from concise descriptions

    This experiment evaluates:
    1. Score impact: Does condensed prompt hurt factory-building performance?
    2. Latency impact: How much faster is inference with smaller prompt?
    """
    return _create_context_reduction_task("condensed_prompt")


# =============================================================================
# Utility Functions
# =============================================================================


def list_context_reduction_experiments():
    """Print all available context reduction experiment tasks."""
    print("Available context reduction solver experiments:")
    print("=" * 60)
    for solver_name, solver_fn in CONTEXT_REDUCTION_SOLVER_MAP.items():
        docstring = solver_fn.__doc__ or "No description"
        first_line = docstring.split("\n")[0].strip()
        print(f"  open_play_{solver_name}: {first_line}")
    print()
    print("Run all context reduction experiments:")
    print(
        "  inspect eval-set context_reduction_experiments.py --log-dir logs --max-tasks 4"
    )
    print()
    print("Or from fle CLI:")
    print(
        "  fle inspect-eval --eval-set-file fle/eval/inspect_integration/context_reduction_experiments.py \\"
    )
    print("      --log-dir logs --max-tasks 4")
    print()
    print("Run specific experiments:")
    print("  inspect eval context_reduction_experiments.py@open_play_text_only")


if __name__ == "__main__":
    list_context_reduction_experiments()
