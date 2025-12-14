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
from fle.eval.inspect_integration.scorers import (
    comprehensive_factorio_scorer,
    throughput_proportion_scorer,
    production_score_tracker,
    step_change_tracker,
    unbounded_production_scorer,
    unbounded_growth_scorer,
)
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import (
    UNBOUNDED_PRODUCTION_TASKS,
    OPEN_PLAY_PRODUCTION,
)


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
        solver=factorio_controlled_solver(),
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
        solver=factorio_controlled_solver(),
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
        solver=factorio_controlled_solver(),
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
        solver=factorio_controlled_solver(),
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
        solver=factorio_unbounded_solver(),
        scorer=unbounded_production_scorer(),
        name=env_id,
    )


def _create_unbounded_growth_task(env_id: str) -> Task:
    """Create an unbounded task focused on growth rate metric."""
    task_config = UNBOUNDED_PRODUCTION_TASKS.get(env_id)
    if not task_config:
        raise ValueError(f"Unknown unbounded production task: {env_id}")

    return Task(
        dataset=[
            Sample(
                input=f"Begin task: {task_config.goal_description}",
                target="maximize",
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
                id=f"{env_id}_growth_eval",
            )
        ],
        solver=factorio_unbounded_solver(),
        scorer=unbounded_growth_scorer(),
        name=f"{env_id}_growth",
    )


# Main unbounded production task
@task
def open_play_production():
    """Build the biggest factory possible - tracked by cumulative production score.

    This is an unbounded task with no specific quota. The agent's goal is to
    maximize total production value over 5000 steps.
    """
    return _create_unbounded_production_task(OPEN_PLAY_PRODUCTION)


@task
def open_play_production_growth():
    """Build the biggest factory - tracked by production growth rate.

    Same as open_play_production but scored by average growth per step
    rather than final production score.
    """
    return _create_unbounded_growth_task(OPEN_PLAY_PRODUCTION)


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
