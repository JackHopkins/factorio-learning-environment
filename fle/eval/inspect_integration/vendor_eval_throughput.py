"""Vendor evaluation throughput test suite for xAI submission.

This module creates 32 throughput test samples distributed across the available
throughput tasks, designed to be run with Harbor and compatible with the
vendor-eval-kit collection format.

Models to evaluate via OpenRouter:
- anthropic/claude-opus-4-6
- openai/gpt-5.3-codex
- xai/grok-4.20-beta (or grok-4, fallback: grok-code-fast-1)

Usage:
    # Run evaluation with Harbor (using OpenRouter)
    harbor run \
      -p /path/to/factorio-tasks \
      -m openrouter/anthropic/claude-opus-4-6 \
      -m openrouter/openai/gpt-5.3-codex \
      -m openrouter/x-ai/grok-4.20-beta \
      -a terminus-2 \
      -k 8 \
      --job-name vendor-eval \
      --jobs-dir eval_results

    # Or run with Inspect AI directly
    inspect eval fle/eval/inspect_integration/vendor_eval_throughput.py@vendor_eval_32 \
      --model openrouter/anthropic/claude-opus-4-6 \
      --model openrouter/openai/gpt-5.3-codex \
      --model openrouter/x-ai/grok-4.20-beta \
      --max-tasks 8

    # After running, collect results with vendor-eval-kit
    vendor-eval collect eval_results -o eval_csvs/
"""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect_integration.solver import factorio_controlled_solver
from fle.eval.inspect_integration.scorers import comprehensive_factorio_scorer
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import (
    THROUGHPUT_TASKS,
    # Import specific task keys for clarity
    IRON_ORE_THROUGHPUT,
    IRON_PLATE_THROUGHPUT,
    STEEL_PLATE_THROUGHPUT,
    ELECTRONIC_CIRCUIT_THROUGHPUT,
    AUTOMATION_SCIENCE_PACK_THROUGHPUT,
    INSERTER_THROUGHPUT,
    IRON_GEAR_WHEEL_THROUGHPUT,
    CRUDE_OIL_THROUGHPUT,
    PETROLEUM_GAS_THROUGHPUT,
    SUFURIC_ACID_THROUGHPUT,
    SULFUR_THROUGHPUT,
    PLASTIC_BAR_THROUGHPUT,
    ADVANCED_CIRCUIT_THROUGHPUT,
    PROCESSING_UNIT_THROUGHPUT,
    LOGISTICS_SCIENCE_PACK_THROUGHPUT,
    BATTERY_THROUGHPUT,
)


# Select 16 representative tasks covering difficulty spectrum
# These will be duplicated to create 32 total samples
SELECTED_TASKS = [
    # Tier 1 - Basic tasks (simple mining/smelting)
    IRON_ORE_THROUGHPUT,
    IRON_PLATE_THROUGHPUT,
    # Tier 2 - Simple components
    IRON_GEAR_WHEEL_THROUGHPUT,
    INSERTER_THROUGHPUT,
    # Tier 3 - Electronics
    ELECTRONIC_CIRCUIT_THROUGHPUT,
    AUTOMATION_SCIENCE_PACK_THROUGHPUT,
    # Tier 4 - Advanced materials
    STEEL_PLATE_THROUGHPUT,
    PLASTIC_BAR_THROUGHPUT,
    # Tier 5 - Oil processing
    CRUDE_OIL_THROUGHPUT,
    PETROLEUM_GAS_THROUGHPUT,
    # Tier 6 - Chemicals
    SULFUR_THROUGHPUT,
    SUFURIC_ACID_THROUGHPUT,
    # Tier 7 - Advanced components
    ADVANCED_CIRCUIT_THROUGHPUT,
    BATTERY_THROUGHPUT,
    # Tier 8 - Complex manufacturing
    PROCESSING_UNIT_THROUGHPUT,
    LOGISTICS_SCIENCE_PACK_THROUGHPUT,
]


def _create_vendor_eval_samples(task_keys: list[str], k: int = 2) -> list[Sample]:
    """Create k samples for each task in task_keys.

    Args:
        task_keys: List of task keys to create samples for
        k: Number of rollouts per task (default: 2, so 16 tasks * 2 = 32 samples)

    Returns:
        List of Sample objects
    """
    samples = []

    for task_key in task_keys:
        task_config = THROUGHPUT_TASKS[task_key]

        # Create k samples for this task
        for i in range(k):
            sample = Sample(
                input=f"Begin task: {task_config.goal_description}",
                target=str(task_config.quota),
                metadata={
                    "env_id": task_key,
                    "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
                    "expected_production_score": float(task_config.quota),
                    "rollout_id": i,
                    "vendor_eval": True,  # Flag for export compatibility
                },
                id=f"{task_key}_rollout_{i}",
            )
            samples.append(sample)

    return samples


@task
def vendor_eval_32():
    """32 throughput test samples for vendor eval (16 tasks × 2 rollouts).

    This evaluation creates 32 test samples by running 2 rollouts of each of
    16 selected throughput tasks, covering a spectrum of difficulty from basic
    mining to complex manufacturing.

    Designed for use with Harbor and vendor-eval-kit:
    - Compatible with ATIF trajectory export
    - Includes comprehensive scoring metrics
    - Supports OpenRouter model routing

    Task distribution:
    - Tier 1-2: Basic materials (4 tasks × 2 = 8 samples)
    - Tier 3-4: Components (4 tasks × 2 = 8 samples)
    - Tier 5-6: Oil & chemicals (4 tasks × 2 = 8 samples)
    - Tier 7-8: Advanced manufacturing (4 tasks × 2 = 8 samples)
    """
    return Task(
        dataset=_create_vendor_eval_samples(SELECTED_TASKS, k=2),
        solver=factorio_controlled_solver(),
        scorer=comprehensive_factorio_scorer(),
        name="vendor_eval_32",
    )


@task
def vendor_eval_32_k4():
    """32 throughput test samples for vendor eval (8 tasks × 4 rollouts).

    Alternative configuration using 4 rollouts per task on a smaller set
    of 8 representative tasks. Same total sample count but higher k value
    for better pass@k metrics.
    """
    # Select 8 most representative tasks
    core_tasks = [
        IRON_ORE_THROUGHPUT,  # Basic mining
        IRON_PLATE_THROUGHPUT,  # Basic smelting
        ELECTRONIC_CIRCUIT_THROUGHPUT,  # Basic electronics
        STEEL_PLATE_THROUGHPUT,  # Intermediate smelting
        CRUDE_OIL_THROUGHPUT,  # Oil extraction
        PLASTIC_BAR_THROUGHPUT,  # Oil processing
        ADVANCED_CIRCUIT_THROUGHPUT,  # Advanced electronics
        LOGISTICS_SCIENCE_PACK_THROUGHPUT,  # Complex manufacturing
    ]

    return Task(
        dataset=_create_vendor_eval_samples(core_tasks, k=4),
        solver=factorio_controlled_solver(),
        scorer=comprehensive_factorio_scorer(),
        name="vendor_eval_32_k4",
    )


@task
def vendor_eval_full():
    """Full throughput evaluation: all 24 tasks × 1 rollout (24 samples).

    Comprehensive evaluation across all available throughput tasks.
    Use this to get broad coverage of all task types with single rollouts.
    """
    all_task_keys = list(THROUGHPUT_TASKS.keys())

    return Task(
        dataset=_create_vendor_eval_samples(all_task_keys, k=1),
        solver=factorio_controlled_solver(),
        scorer=comprehensive_factorio_scorer(),
        name="vendor_eval_full",
    )


@task
def vendor_eval_32_k8():
    """32 throughput test samples for vendor eval (4 tasks × 8 rollouts).

    High k-value configuration for better statistical significance.
    Uses 4 core tasks representing key difficulty levels.

    Recommended for final vendor submission with k=8 requirement.
    """
    core_tasks = [
        IRON_ORE_THROUGHPUT,  # Tier 1: Basic
        ELECTRONIC_CIRCUIT_THROUGHPUT,  # Tier 3: Electronics
        PLASTIC_BAR_THROUGHPUT,  # Tier 4: Oil processing
        LOGISTICS_SCIENCE_PACK_THROUGHPUT,  # Tier 8: Complex
    ]

    return Task(
        dataset=_create_vendor_eval_samples(core_tasks, k=8),
        solver=factorio_controlled_solver(),
        scorer=comprehensive_factorio_scorer(),
        name="vendor_eval_32_k8",
    )


# =============================================================================
# Helper function for programmatic use
# =============================================================================


def create_vendor_eval_task(
    task_keys: list[str] | None = None, k: int = 2, name: str = "vendor_eval_custom"
) -> Task:
    """Create a custom vendor eval task with specified tasks and k value.

    Args:
        task_keys: List of task keys to include (default: SELECTED_TASKS)
        k: Number of rollouts per task
        name: Task name for the evaluation

    Returns:
        Task object ready for Inspect eval

    Example:
        # Create custom task with specific selection
        custom_task = create_vendor_eval_task(
            task_keys=[IRON_ORE_THROUGHPUT, STEEL_PLATE_THROUGHPUT],
            k=4,
            name="vendor_eval_metals"
        )
    """
    if task_keys is None:
        task_keys = SELECTED_TASKS

    return Task(
        dataset=_create_vendor_eval_samples(task_keys, k=k),
        solver=factorio_controlled_solver(),
        scorer=comprehensive_factorio_scorer(),
        name=name,
    )


# =============================================================================
# Task Summary
# =============================================================================

if __name__ == "__main__":
    print("🏭 Vendor Eval Throughput Test Suite")
    print("=" * 60)
    print()
    print("Available evaluation configurations:")
    print()
    print("1. vendor_eval_32 (default)")
    print("   - 16 tasks × 2 rollouts = 32 samples")
    print("   - Balanced coverage across difficulty tiers")
    print()
    print("2. vendor_eval_32_k4")
    print("   - 8 tasks × 4 rollouts = 32 samples")
    print("   - Better pass@4 statistics")
    print()
    print("3. vendor_eval_32_k8")
    print("   - 4 tasks × 8 rollouts = 32 samples")
    print("   - Optimal for vendor submission (k=8 requirement)")
    print()
    print("4. vendor_eval_full")
    print("   - All 24 tasks × 1 rollout = 24 samples")
    print("   - Comprehensive task coverage")
    print()
    print("Selected tasks for vendor_eval_32:")
    for i, task_key in enumerate(SELECTED_TASKS, 1):
        task_config = THROUGHPUT_TASKS[task_key]
        print(f"  {i:2d}. {task_key}: {task_config.goal_description[:60]}...")
    print()
    print("Usage examples:")
    print()
    print("# With Inspect AI:")
    print("inspect eval vendor_eval_throughput.py@vendor_eval_32_k8 \\")
    print("  --model openrouter/anthropic/claude-opus-4-6 \\")
    print("  --model openrouter/openai/gpt-5.3-codex \\")
    print("  --model openrouter/x-ai/grok-4.20-beta")
    print()
    print("# With Harbor:")
    print("harbor run \\")
    print("  -p /path/to/factorio-tasks \\")
    print("  -m openrouter/anthropic/claude-opus-4-6 \\")
    print("  -m openrouter/openai/gpt-5.3-codex \\")
    print("  -m openrouter/x-ai/grok-4.20-beta \\")
    print("  -a terminus-2 \\")
    print("  -k 8 \\")
    print("  --job-name vendor-eval \\")
    print("  --jobs-dir eval_results")
