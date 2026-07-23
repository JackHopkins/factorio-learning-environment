"""Discoverable, truthfully scoped Factorio benchmark catalog.

The development catalog only marks tasks ``ready`` when their provisioning and
verifier are executable today. ``calibration_required`` means the task is real
and runnable, but its budgets or difficulty have not yet been empirically
calibrated for a frozen benchmark release.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from fle.envd.curriculum import BUILTIN_TASKS, get_builtin_task
from fle.envd.models import FactorioTaskSpec, WireModel
from fle.envd.task_builder import build_task_spec
from fle.eval.tasks.task_definitions.task_registry import list_tasks_by_category

BENCHMARK_VERSION = "0.1.0-dev"

BenchmarkStatus = Literal["ready", "calibration_required", "spec_only", "planned"]
BenchmarkHorizon = Literal["short", "medium", "long", "persistent"]


class BenchmarkTask(WireModel):
    benchmark_version: str = BENCHMARK_VERSION
    task_id: str
    suite: str
    tier: int = Field(ge=0, le=5)
    status: BenchmarkStatus
    horizon: BenchmarkHorizon
    mechanics: list[str] = Field(default_factory=list)
    primary_metric: str
    benchmark_split: Literal["development", "validation", "test"] = "development"
    notes: list[str] = Field(default_factory=list)
    task_spec: FactorioTaskSpec


_TIER_1_TARGETS = {
    "coal",
    "copper-ore",
    "copper-plate",
    "iron-ore",
    "iron-plate",
    "stone",
    "stone-brick",
    "iron-gear-wheel",
    "copper-cable",
    "stone-wall",
}
_TIER_2_TARGETS = {
    "electronic-circuit",
    "inserter",
    "steel-plate",
    "engine-unit",
    "automation-science-pack",
    "logistic-science-pack",
    "piercing-rounds-magazine",
}
_TIER_3_TARGETS = {
    "crude-oil",
    "petroleum-gas",
    "plastic-bar",
    "sulfur",
    "sulfuric-acid",
    "battery",
    "advanced-circuit",
    "military-science-pack",
}


def _throughput_tier(target: str) -> int:
    if target in _TIER_1_TARGETS:
        return 1
    if target in _TIER_2_TARGETS:
        return 2
    if target in _TIER_3_TARGETS:
        return 3
    return 4


def _throughput_mechanics(target: str) -> list[str]:
    mechanics = ["automation", "sustained_throughput"]
    if target in {"coal", "copper-ore", "iron-ore", "stone", "crude-oil"}:
        mechanics.append("resource_extraction")
    if target in {"copper-plate", "iron-plate", "steel-plate", "stone-brick"}:
        mechanics.append("smelting")
    if target in {
        "crude-oil",
        "petroleum-gas",
        "plastic-bar",
        "sulfur",
        "sulfuric-acid",
        "battery",
        "advanced-circuit",
        "processing-unit",
        "chemical-science-pack",
    }:
        mechanics.extend(["fluids", "oil_processing"])
    if "science-pack" in target:
        mechanics.append("science_production")
    return sorted(set(mechanics))


def _throughput_catalog() -> list[BenchmarkTask]:
    tasks: list[BenchmarkTask] = []
    for task_id in sorted(list_tasks_by_category()["throughput"]):
        spec = build_task_spec(task_id)
        target = str(spec.objectives[0].target)
        tier = _throughput_tier(target)
        tasks.append(
            BenchmarkTask(
                task_id=task_id,
                suite="lab_throughput_v1",
                tier=tier,
                status="ready",
                horizon="short" if tier <= 2 else "medium",
                mechanics=_throughput_mechanics(target),
                primary_metric=f"{target}_per_60_seconds",
                notes=[
                    "Existing FLE lab task with holdout-based engine verification."
                ],
                task_spec=spec,
            )
        )
    return tasks


_BUILTIN_METADATA: dict[str, dict] = {
    "milestone_research_automation_v1": {
        "suite": "milestones_v1",
        "tier": 1,
        "status": "ready",
        "horizon": "short",
        "mechanics": ["electricity", "laboratory", "research"],
        "primary_metric": "automation_researched",
    },
    "progression_early_automation_v1": {
        "suite": "progression_v1",
        "tier": 2,
        "status": "calibration_required",
        "horizon": "long",
        "mechanics": [
            "bootstrap",
            "resource_extraction",
            "smelting",
            "research",
            "science_production",
        ],
        "primary_metric": "required_objectives_completed",
    },
    "robustness_circuit_no_manual_v1": {
        "suite": "robustness_v1",
        "tier": 2,
        "status": "ready",
        "horizon": "medium",
        "mechanics": ["automation", "circuits", "action_restriction"],
        "primary_metric": "verified_circuit_throughput",
    },
    "robustness_productive_survival_v1": {
        "suite": "robustness_v1",
        "tier": 2,
        "status": "ready",
        "horizon": "medium",
        "mechanics": ["automation", "smelting", "survival"],
        "primary_metric": "throughput_with_zero_deaths",
    },
    "robustness_efficient_iron_v1": {
        "suite": "efficiency_v1",
        "tier": 2,
        "status": "calibration_required",
        "horizon": "medium",
        "mechanics": [
            "automation",
            "smelting",
            "resource_accounting",
            "pollution",
        ],
        "primary_metric": "throughput_under_budgets",
    },
    "milestone_launch_rocket_v1": {
        "suite": "milestones_v1",
        "tier": 4,
        "status": "calibration_required",
        "horizon": "long",
        "mechanics": ["electricity", "rocket_silo", "late_game_assembly"],
        "primary_metric": "engine_rocket_launch_delta",
    },
}


def _builtin_catalog() -> list[BenchmarkTask]:
    tasks: list[BenchmarkTask] = []
    for task_id, metadata in sorted(_BUILTIN_METADATA.items()):
        tasks.append(
            BenchmarkTask(
                task_id=task_id,
                notes=[
                    "Native objective_engine_v1 task.",
                    (
                        "Thresholds require empirical calibration before a frozen "
                        "benchmark release."
                        if metadata["status"] == "calibration_required"
                        else "Provisioning and verifier are runnable."
                    ),
                ],
                task_spec=get_builtin_task(task_id),
                **metadata,
            )
        )
    return tasks


def benchmark_catalog() -> list[BenchmarkTask]:
    """Return the deterministic development benchmark manifest."""

    tasks = [*_throughput_catalog(), *_builtin_catalog()]
    return sorted(tasks, key=lambda task: (task.suite, task.tier, task.task_id))


def get_benchmark_task(task_id: str) -> BenchmarkTask:
    for task in benchmark_catalog():
        if task.task_id == task_id:
            return task
    available = ", ".join(task.task_id for task in benchmark_catalog())
    raise KeyError(f"Unknown benchmark task {task_id!r}; available: {available}")


def benchmark_summary() -> dict[str, object]:
    tasks = benchmark_catalog()
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "task_count": len(tasks),
        "ready_count": sum(task.status == "ready" for task in tasks),
        "calibration_required_count": sum(
            task.status == "calibration_required" for task in tasks
        ),
        "suites": sorted({task.suite for task in tasks}),
    }


assert set(_BUILTIN_METADATA) == set(BUILTIN_TASKS)
