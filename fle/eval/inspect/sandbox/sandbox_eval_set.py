"""Factorio evaluation tasks using Inspect sandbox containers.

This is a thin wrapper around the shared eval_set that configures tasks
to use sandbox solvers and per-sample Docker sandbox containers.

Usage:
    inspect eval fle/eval/inspect/sandbox/sandbox_eval_set.py@iron_ore_throughput
    inspect eval fle/eval/inspect/sandbox/sandbox_eval_set.py@open_play_production
"""

import os
from pathlib import Path

from inspect_ai import Task, task

from fle.eval.inspect.eval_set import (
    create_throughput_task,
    create_unbounded_production_task,
    THROUGHPUT_TASKS,
    OPEN_PLAY_PRODUCTION,
)
from fle.eval.inspect.sandbox.sandbox_solver import (
    factorio_sandbox_controlled_solver,
    factorio_sandbox_unbounded_solver,
)

COMPOSE_PATH = str(Path(__file__).parent / "compose.yaml")

SANDBOX_CONFIG = ("docker", COMPOSE_PATH)


def _sandbox_throughput(env_id: str, target: int = 16) -> Task:
    return create_throughput_task(
        env_id,
        target=target,
        solver=factorio_sandbox_controlled_solver(),
        sandbox=SANDBOX_CONFIG,
    )


def _sandbox_unbounded(env_id: str) -> Task:
    return create_unbounded_production_task(
        env_id,
        solver=factorio_sandbox_unbounded_solver(),
        sandbox=SANDBOX_CONFIG,
    )


# ---- Throughput tasks ----


@task
def iron_ore_throughput():
    return _sandbox_throughput("iron_ore_throughput", 16)


@task
def iron_plate_throughput():
    return _sandbox_throughput("iron_plate_throughput", 16)


@task
def steel_plate_throughput():
    return _sandbox_throughput("steel_plate_throughput", 16)


@task
def electronic_circuit_throughput():
    return _sandbox_throughput("electronic_circuit_throughput", 16)


@task
def automation_science_pack_throughput():
    return _sandbox_throughput("automation_science_pack_throughput", 16)


@task
def inserter_throughput():
    return _sandbox_throughput("inserter_throughput", 16)


@task
def iron_gear_wheel_throughput():
    return _sandbox_throughput("iron_gear_wheel_throughput", 16)


@task
def crude_oil_throughput():
    return _sandbox_throughput("crude_oil_throughput", 250)


@task
def petroleum_gas_throughput():
    return _sandbox_throughput("petroleum_gas_throughput", 250)


@task
def sufuric_acid_throughput():
    return _sandbox_throughput("sufuric_acid_throughput", 16)


@task
def sulfur_throughput():
    return _sandbox_throughput("sulfur_throughput", 16)


@task
def piercing_round_throughput():
    return _sandbox_throughput("piercing_round_throughput", 16)


@task
def stone_wall_throughput():
    return _sandbox_throughput("stone_wall_throughput", 16)


@task
def plastic_bar_throughput():
    return _sandbox_throughput("plastic_bar_throughput", 16)


@task
def advanced_circuit_throughput():
    return _sandbox_throughput("advanced_circuit_throughput", 16)


@task
def processing_unit_throughput():
    return _sandbox_throughput("processing_unit_throughput", 16)


@task
def logistics_science_pack_throughput():
    return _sandbox_throughput("logistics_science_pack_throughput", 16)


# ---- Unbounded tasks ----


@task
def open_play_production():
    return _sandbox_unbounded(OPEN_PLAY_PRODUCTION)
