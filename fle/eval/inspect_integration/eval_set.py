"""Complete Factorio evaluation set with static task definitions using base method.

Supports two types of tasks:
1. Throughput tasks: Produce specific items at a target rate (quota-based)
2. Unbounded production tasks: Build the biggest factory (cumulative score)
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
    factorio_pruned_gamestate_solver,
)
from fle.eval.inspect_integration.scorers import (
    comprehensive_factorio_scorer,
    throughput_proportion_scorer,
    production_score_tracker,
    step_change_tracker,
    production_score,
    technologies,
    achievements,
    automated_production_score,
)
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)


# Solver mapping for dynamic selection via FLE_SOLVER env var
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
    "pruned_gamestate": factorio_pruned_gamestate_solver,
}


def get_solver_for_task(task_type: str = "throughput"):
    """Get the appropriate solver based on FLE_SOLVER env var or task type.

    Args:
        task_type: "throughput" or "unbounded"

    Returns:
        Solver function to use
    """
    solver_name = os.getenv("FLE_SOLVER")
    if solver_name and solver_name in SOLVER_MAP:
        return SOLVER_MAP[solver_name]()

    # Default based on task type
    if task_type == "unbounded":
        return factorio_unbounded_solver()
    return factorio_controlled_solver()


def _create_throughput_task(env_id: str, target=16) -> Task:
    """Base method that creates a throughput task for any environment."""
    task_config = THROUGHPUT_TASKS[env_id]
    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target=str(target),
                metadata={
                    "env_id": env_id,
                    "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
                    "expected_production_score": float(task_config.quota),
                },
                id=f"{env_id}_eval",
            )
        ],
        solver=get_solver_for_task("throughput"),
        scorer=comprehensive_factorio_scorer(),
        name=env_id,
    )


# Lightweight static task definitions using the base method
# Each task is explicitly defined with @task decorator for proper Inspect discovery


@task
def iron_ore_throughput():
    """Iron ore throughput task"""
    return _create_throughput_task("iron_ore_throughput", 16)


@task
def iron_plate_throughput():
    """Iron plate throughput task"""
    return _create_throughput_task("iron_plate_throughput", 16)


@task
def steel_plate_throughput():
    """Steel plate throughput task"""
    return _create_throughput_task("steel_plate_throughput", 16)


@task
def electronic_circuit_throughput():
    """Electronic circuit throughput task"""
    return _create_throughput_task("electronic_circuit_throughput", 16)


@task
def automation_science_pack_throughput():
    """Automation science pack throughput task"""
    return _create_throughput_task("automation_science_pack_throughput", 16)


@task
def inserter_throughput():
    """Inserter throughput task"""
    return _create_throughput_task("inserter_throughput", 16)


@task
def iron_gear_wheel_throughput():
    """Iron gear wheel throughput task"""
    return _create_throughput_task("iron_gear_wheel_throughput", 16)


@task
def crude_oil_throughput():
    """Crude oil throughput task"""
    return _create_throughput_task("crude_oil_throughput", 250)


@task
def petroleum_gas_throughput():
    """Petroleum gas throughput task"""
    return _create_throughput_task("petroleum_gas_throughput", 250)


@task
def sufuric_acid_throughput():
    """Sulfuric acid throughput task"""
    return _create_throughput_task("sufuric_acid_throughput", 16)


@task
def sulfur_throughput():
    """Sulfur throughput task"""
    return _create_throughput_task("sulfur_throughput", 16)


@task
def piercing_round_throughput():
    """Piercing round throughput task"""
    return _create_throughput_task("piercing_round_throughput", 16)


@task
def stone_wall_throughput():
    """Stone wall throughput task"""
    return _create_throughput_task("stone_wall_throughput", 16)


@task
def plastic_bar_throughput():
    """Plastic bar throughput task"""
    return _create_throughput_task("plastic_bar_throughput", 16)


@task
def advanced_circuit_throughput():
    """Advanced circuit throughput task"""
    return _create_throughput_task("advanced_circuit_throughput", 16)


@task
def processing_unit_throughput():
    """Processing unit throughput task"""
    return _create_throughput_task("processing_unit_throughput", 16)


@task
def logistics_science_pack_throughput():
    """Logistics science pack throughput task"""
    return _create_throughput_task("logistics_science_pack_throughput", 16)


# @task
# def chemical_science_pack_throughput():
#     """Chemical science pack throughput task"""
#     return _create_throughput_task("chemical_science_pack_throughput")
#
# @task
# def military_science_pack_throughput():
#     """Military science pack throughput task"""
#     return _create_throughput_task("military_science_pack_throughput")
#
# @task
# def production_science_pack_throughput():
#     """Production science pack throughput task"""
#     return _create_throughput_task("production_science_pack_throughput")
#
# @task
# def utility_science_pack_throughput():
#     """Utility science pack throughput task"""
#     return _create_throughput_task("utility_science_pack_throughput")
#
# @task
# def battery_throughput():
#     """Battery throughput task"""
#     return _create_throughput_task("battery_throughput")
#
# @task
# def engine_unit_throughput():
#     """Engine unit throughput task"""
#     return _create_throughput_task("engine_unit_throughput")
#
# @task
# def low_density_structure_throughput():
#     """Low density structure throughput task"""
#     return _create_throughput_task("low_density_structure_throughput")


# Specialized task variants with different scoring metrics


def _create_proportion_task(env_id: str) -> Task:
    """Task variant focused on throughput proportion metric."""
    task_config = THROUGHPUT_TASKS[env_id]
    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target="success",
                metadata={
                    "env_id": env_id,
                    "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
                    "expected_production_score": float(task_config.quota),
                },
                id=f"{env_id}_proportion_eval",
            )
        ],
        solver=get_solver_for_task("throughput"),
        scorer=throughput_proportion_scorer(),
        name=f"{env_id}_proportion",
    )


def _create_production_tracking_task(env_id: str) -> Task:
    """Task variant focused on overall production score tracking."""
    task_config = THROUGHPUT_TASKS[env_id]
    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target="success",
                metadata={
                    "env_id": env_id,
                    "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
                    "expected_production_score": float(task_config.quota),
                },
                id=f"{env_id}_production_eval",
            )
        ],
        solver=get_solver_for_task("throughput"),
        scorer=production_score_tracker(),
        name=f"{env_id}_production",
    )


def _create_step_change_task(env_id: str) -> Task:
    """Task variant focused on step-by-step change tracking."""
    task_config = THROUGHPUT_TASKS[env_id]
    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target="success",
                metadata={
                    "env_id": env_id,
                    "trajectory_length": int(os.getenv("FLE_TRAJECTORY_LENGTH", "64")),
                    "expected_production_score": float(task_config.quota),
                },
                id=f"{env_id}_change_eval",
            )
        ],
        solver=get_solver_for_task("throughput"),
        scorer=step_change_tracker(),
        name=f"{env_id}_step_change",
    )


# Example tasks with specialized scoring
@task
def iron_ore_throughput_proportion():
    """Iron ore throughput with proportion metric"""
    return _create_proportion_task("iron_ore_throughput")


@task
def iron_ore_throughput_production():
    """Iron ore throughput with production score tracking"""
    return _create_production_tracking_task("iron_ore_throughput")


@task
def iron_ore_throughput_step_change():
    """Iron ore throughput with step change tracking"""
    return _create_step_change_task("iron_ore_throughput")


# =============================================================================
# Unbounded Production Tasks (Open-Play / Build Biggest Factory)
# =============================================================================
def _create_unbounded_production_task(env_id: str) -> Task:
    """Create an unbounded production task for open-play evaluation.

    These tasks:
    - Track cumulative production score (total economic value)
    - Have no quota - higher is always better
    - Use 5000-step trajectories by default
    - Use the unbounded solver and scorer
    """
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(env_id)
    if not task_config:
        raise ValueError(f"Unknown unbounded production task: {env_id}")

    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target="maximize",  # No specific target for unbounded tasks
                metadata={
                    "env_id": env_id,
                    "trajectory_length": int(
                        os.getenv(
                            "FLE_TRAJECTORY_LENGTH", str(task_config.trajectory_length)
                        )
                    ),
                    "goal_description": task_config.goal_description,
                    "task_type": "unbounded_production",
                },
                id=f"{env_id}_eval",
            )
        ],
        solver=get_solver_for_task("unbounded"),
        scorer=[
            production_score(),
            technologies(),
            achievements(),
            automated_production_score(),
        ],
        name=env_id,
    )


# Main unbounded production task
@task
def open_play_production():
    """Build the biggest factory possible - tracked by cumulative production score.

    This is an unbounded task with no specific quota. The agent's goal is to
    maximize total production value over 5000 steps.
    """
    return _create_unbounded_production_task(OPEN_PLAY_PRODUCTION)


# =============================================================================
# Solver Variant Tasks (for parallel comparison)
# =============================================================================
# These tasks use explicit solver variants, allowing parallel execution with:
#   inspect eval eval_set.py@open_play_unbounded,eval_set.py@open_play_reasoning_only,...
#   --max-tasks 6 --max-connections 32


def _create_solver_variant_task(solver_name: str) -> Task:
    """Create an open_play task with a specific solver variant."""
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(OPEN_PLAY_PRODUCTION)

    # Get the solver function from the map
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


@task
def open_play_unbounded():
    """Open play with unbounded solver (baseline)."""
    return _create_solver_variant_task("unbounded")


@task
def open_play_reasoning_only():
    """Open play with reasoning-only solver (strips code from history)."""
    return _create_solver_variant_task("reasoning_only")


@task
def open_play_text_only():
    """Open play with text-only solver (no images)."""
    return _create_solver_variant_task("text_only")


@task
def open_play_hud():
    """Open play with HUD solver (fixed 3-message context + visual rendering)."""
    return _create_solver_variant_task("hud")


@task
def open_play_hud_text_only():
    """Open play with HUD solver, text only (no images)."""
    return _create_solver_variant_task("hud_text_only")


@task
def open_play_balanced():
    """Open play with balanced solver (moderate optimizations)."""
    return _create_solver_variant_task("balanced")


@task
def open_play_minimal_context():
    """Open play with minimal context solver (most aggressive optimization)."""
    return _create_solver_variant_task("minimal_context")


@task
def open_play_no_image_history():
    """Open play with no-image-history solver (strips images from history)."""
    return _create_solver_variant_task("no_image_history")


@task
def open_play_fat_hud():
    """Open play with fat HUD solver (3 images at zoom levels 16, 32, 64).

    This solver provides multi-scale visual feedback with:
    - Zoom 16: Close-up view (32x32 tiles) - detailed view of nearby entities
    - Zoom 32: Medium view (64x64 tiles) - factory overview
    - Zoom 64: Far view (128x128 tiles) - large-scale factory layout

    All images have the same pixel dimensions but show different amounts of the world.
    Higher token usage per step but enables better spatial reasoning across scales.
    """
    return _create_solver_variant_task("fat_hud")


@task
def open_play_pruned_gamestate():
    """Open play with pruned gamestate solver (strips game state from history).

    This solver prunes historical user messages to only keep program output:
    - System prompt: Full (cached)
    - Assistant messages: Full (reasoning and code preserved)
    - Historical user messages: Only program output (stdout/stderr) - game state [omitted]
    - Latest user message: Full game state observation

    The key insight: Program output tells the model what happened (success/error),
    while the current game state tells it what to do next. Historical game states
    are largely redundant since the current state reflects cumulative changes.

    Optimization: ~40-60% context reduction on user messages
    Trade-off: Model can't reference exact historical game states
    """
    return _create_solver_variant_task("pruned_gamestate")


# =============================================================================
# Task Summary and Usage Information
# =============================================================================

# List of all available task names for reference
ALL_THROUGHPUT_TASKS = list(THROUGHPUT_TASKS.keys())
ALL_UNBOUNDED_PRODUCTION_TASKS = list(UNBOUNDED_PRODUCTION_TASKS.keys())


def print_task_summary():
    """Print summary of available tasks. Call this explicitly if needed."""
    print(f"📊 Generated {len(ALL_THROUGHPUT_TASKS)} throughput task functions:")
    for i, task_name in enumerate(ALL_THROUGHPUT_TASKS):
        print(f"  {i + 1:2d}. {task_name}")

    print(
        f"\n🏭 Generated {len(ALL_UNBOUNDED_PRODUCTION_TASKS)} unbounded production task functions:"
    )
    for i, task_name in enumerate(ALL_UNBOUNDED_PRODUCTION_TASKS):
        print(f"  {i + 1:2d}. {task_name}")

    print("\n📈 Enhanced Scoring Metrics Available:")
    print("  Throughput Tasks:")
    print("    • Comprehensive scorer: All metrics combined")
    print("    • Throughput proportion: Ratio of achieved/desired throughput")
    print("    • Production score: Overall production tracking")
    print("    • Step change: Change from last step tracking")
    print("  Unbounded Tasks:")
    print("    • Unbounded production: Cumulative production score (higher is better)")
    print("    • Unbounded growth: Average production growth per step")

    print("\n💡 Usage:")
    print("  Throughput tasks:")
    print("    inspect eval factorio_eval_set.py@iron_ore_throughput --epochs 8")
    print(
        "    inspect eval factorio_eval_set.py@iron_ore_throughput_proportion --epochs 8"
    )
    print("  Unbounded production tasks:")
    print("    inspect eval factorio_eval_set.py@open_play_production --epochs 1")
    print(
        "    inspect eval factorio_eval_set.py@open_play_production_growth --epochs 1"
    )
    print("  Multiple tasks:")
    print("    inspect eval-set factorio_eval_set.py --epochs 8 --max-tasks 4")
    print("  All tasks: fle inspect-eval --eval-set --pass-n 8 --max-tasks 8")


# Only print summary when run as main script
if __name__ == "__main__":
    print_task_summary()
