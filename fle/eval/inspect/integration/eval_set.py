"""Factorio evaluation set using integration (host-side) solvers.

Uses the shared task factories from fle.eval.inspect.eval_set with
integration-specific solvers that talk directly to Factorio containers
managed by SimpleServerPool.
"""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect.eval_set import (
    create_throughput_task,
    create_unbounded_production_task,
    THROUGHPUT_TASKS,
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)
from fle.eval.inspect.integration.solver import (
    factorio_controlled_solver,
    factorio_unbounded_solver,
)
from fle.eval.inspect.integration.solver_variants import (
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
from fle.eval.inspect.integration.scorers import (
    comprehensive_factorio_scorer,
    throughput_proportion_scorer,
    production_score_tracker,
    step_change_tracker,
    production_score,
    technologies,
    achievements,
    automated_production_score,
    code,
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
    """Get the appropriate solver based on FLE_SOLVER env var or task type."""
    solver_name = os.getenv("FLE_SOLVER")
    if solver_name and solver_name in SOLVER_MAP:
        return SOLVER_MAP[solver_name]()
    if task_type == "unbounded":
        return factorio_unbounded_solver()
    return factorio_controlled_solver()


# =============================================================================
# Throughput tasks
# =============================================================================


def _throughput(env_id: str, target: int = 16) -> Task:
    return create_throughput_task(
        env_id, target=target, solver=get_solver_for_task("throughput")
    )


@task
def iron_ore_throughput():
    """Iron ore throughput task"""
    return _throughput("iron_ore_throughput", 16)


@task
def iron_plate_throughput():
    """Iron plate throughput task"""
    return _throughput("iron_plate_throughput", 16)


@task
def steel_plate_throughput():
    """Steel plate throughput task"""
    return _throughput("steel_plate_throughput", 16)


@task
def electronic_circuit_throughput():
    """Electronic circuit throughput task"""
    return _throughput("electronic_circuit_throughput", 16)


@task
def automation_science_pack_throughput():
    """Automation science pack throughput task"""
    return _throughput("automation_science_pack_throughput", 16)


@task
def inserter_throughput():
    """Inserter throughput task"""
    return _throughput("inserter_throughput", 16)


@task
def iron_gear_wheel_throughput():
    """Iron gear wheel throughput task"""
    return _throughput("iron_gear_wheel_throughput", 16)


@task
def crude_oil_throughput():
    """Crude oil throughput task"""
    return _throughput("crude_oil_throughput", 250)


@task
def petroleum_gas_throughput():
    """Petroleum gas throughput task"""
    return _throughput("petroleum_gas_throughput", 250)


@task
def sufuric_acid_throughput():
    """Sulfuric acid throughput task"""
    return _throughput("sufuric_acid_throughput", 16)


@task
def sulfur_throughput():
    """Sulfur throughput task"""
    return _throughput("sulfur_throughput", 16)


@task
def piercing_round_throughput():
    """Piercing round throughput task"""
    return _throughput("piercing_round_throughput", 16)


@task
def stone_wall_throughput():
    """Stone wall throughput task"""
    return _throughput("stone_wall_throughput", 16)


@task
def plastic_bar_throughput():
    """Plastic bar throughput task"""
    return _throughput("plastic_bar_throughput", 16)


@task
def advanced_circuit_throughput():
    """Advanced circuit throughput task"""
    return _throughput("advanced_circuit_throughput", 16)


@task
def processing_unit_throughput():
    """Processing unit throughput task"""
    return _throughput("processing_unit_throughput", 16)


@task
def logistics_science_pack_throughput():
    """Logistics science pack throughput task"""
    return _throughput("logistics_science_pack_throughput", 16)


# =============================================================================
# Specialized scoring variants
# =============================================================================


def _create_proportion_task(env_id: str) -> Task:
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
# Unbounded Production Tasks
# =============================================================================


@task
def open_play_production():
    """Build the biggest factory possible - tracked by cumulative production score."""
    return create_unbounded_production_task(
        OPEN_PLAY_PRODUCTION,
        solver=get_solver_for_task("unbounded"),
    )


# =============================================================================
# Solver Variant Tasks (for parallel comparison)
# =============================================================================


def _create_solver_variant_task(solver_name: str) -> Task:
    """Create an open_play task with a specific solver variant."""
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
        scorer=[
            production_score(),
            automated_production_score(),
            technologies(),
            achievements(),
            code(),
        ],
        name=f"open_play_{solver_name}",
    )


@task
def open_play_unbounded():
    """Open play with unbounded solver (baseline)."""
    return _create_solver_variant_task("unbounded")


@task
def open_play_reasoning_only():
    """Open play with reasoning-only solver."""
    return _create_solver_variant_task("reasoning_only")


@task
def open_play_text_only():
    """Open play with text-only solver (no images)."""
    return _create_solver_variant_task("text_only")


@task
def open_play_hud():
    """Open play with HUD solver."""
    return _create_solver_variant_task("hud")


@task
def open_play_hud_text_only():
    """Open play with HUD solver, text only (no images)."""
    return _create_solver_variant_task("hud_text_only")


@task
def open_play_balanced():
    """Open play with balanced solver."""
    return _create_solver_variant_task("balanced")


@task
def open_play_minimal_context():
    """Open play with minimal context solver."""
    return _create_solver_variant_task("minimal_context")


@task
def open_play_no_image_history():
    """Open play with no-image-history solver."""
    return _create_solver_variant_task("no_image_history")


@task
def open_play_fat_hud():
    """Open play with fat HUD solver (3 images at zoom levels 16, 32, 64)."""
    return _create_solver_variant_task("fat_hud")


@task
def open_play_pruned_gamestate():
    """Open play with pruned gamestate solver."""
    return _create_solver_variant_task("pruned_gamestate")


# =============================================================================
# Summary
# =============================================================================

ALL_THROUGHPUT_TASKS = list(THROUGHPUT_TASKS.keys())
ALL_UNBOUNDED_PRODUCTION_TASKS = list(UNBOUNDED_PRODUCTION_TASKS.keys())


def print_task_summary():
    """Print summary of available tasks."""
    print(f"Throughput tasks ({len(ALL_THROUGHPUT_TASKS)}):")
    for i, name in enumerate(ALL_THROUGHPUT_TASKS):
        print(f"  {i + 1:2d}. {name}")
    print(f"\nUnbounded tasks ({len(ALL_UNBOUNDED_PRODUCTION_TASKS)}):")
    for i, name in enumerate(ALL_UNBOUNDED_PRODUCTION_TASKS):
        print(f"  {i + 1:2d}. {name}")


if __name__ == "__main__":
    print_task_summary()
