"""Complete Factorio evaluation set with static task definitions using base method."""

import os
from inspect_ai import Task, task
from inspect_ai.dataset import Sample

from fle.eval.inspect_integration.controlled_solver import factorio_controlled_solver
from fle.eval.inspect_integration.enhanced_scorer import (
    comprehensive_factorio_scorer,
    throughput_proportion_scorer,
    production_score_tracker,
    step_change_tracker,
)
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS


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


# List of all available task names for reference
ALL_THROUGHPUT_TASKS = list(THROUGHPUT_TASKS.keys())

print(f"📊 Generated {len(ALL_THROUGHPUT_TASKS)} throughput task functions:")
for i, task_name in enumerate(ALL_THROUGHPUT_TASKS):
    print(f"  {i + 1:2d}. {task_name}")

print("\n📈 Enhanced Scoring Metrics Available:")
print("  • Comprehensive scorer: All metrics combined")
print("  • Throughput proportion: Ratio of achieved/desired throughput")
print("  • Production score: Overall production tracking")
print("  • Step change: Change from last step tracking")

print("\n💡 Usage:")
print(
    "  Comprehensive: inspect eval factorio_eval_set.py@iron_ore_throughput --epochs 8"
)
print(
    "  Proportion focus: inspect eval factorio_eval_set.py@iron_ore_throughput_proportion --epochs 8"
)
print(
    "  Production tracking: inspect eval factorio_eval_set.py@iron_ore_throughput_production --epochs 8"
)
print(
    "  Step change analysis: inspect eval factorio_eval_set.py@iron_ore_throughput_step_change --epochs 8"
)
print(
    "  Multiple tasks: inspect eval-set factorio_eval_set.py --epochs 8 --max-tasks 4"
)
print("  All tasks: fle inspect-eval --eval-set --pass-n 8 --max-tasks 8")
