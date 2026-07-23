import pytest

from fle.envd.benchmark import (
    BENCHMARK_VERSION,
    benchmark_catalog,
    benchmark_summary,
    get_benchmark_task,
)
from fle.envd.curriculum import BUILTIN_TASKS
from fle.eval.tasks.task_definitions.task_registry import (
    create_task,
    list_tasks_by_category,
)

pytestmark = pytest.mark.no_factorio


def test_development_catalog_is_large_unique_and_reproducible():
    catalog = benchmark_catalog()
    task_ids = [task.task_id for task in catalog]

    assert len(catalog) >= 36
    assert len(task_ids) == len(set(task_ids))
    assert all(task.benchmark_version == BENCHMARK_VERSION for task in catalog)
    assert all(task.task_spec.fingerprint for task in catalog)
    assert benchmark_catalog() == catalog


def test_all_ready_tasks_have_executable_verifiers_and_real_objectives():
    catalog = benchmark_catalog()

    for task in catalog:
        if task.status != "ready":
            continue
        assert task.task_spec.objectives
        assert all(
            objective.kind != "custom" for objective in task.task_spec.objectives
        )
        assert task.task_spec.verifier.implementation in {
            "legacy_fle_task",
            "objective_engine_v1",
        }


def test_every_builtin_task_is_classified_in_the_benchmark():
    classified = {
        task.task_id
        for task in benchmark_catalog()
        if task.task_id in BUILTIN_TASKS
    }

    assert classified == set(BUILTIN_TASKS)


def test_new_base_game_throughput_tasks_are_registered_and_runnable():
    expected = {
        "coal_throughput",
        "copper_cable_throughput",
        "copper_ore_throughput",
        "copper_plate_throughput",
        "stone_brick_throughput",
        "stone_throughput",
    }

    assert expected <= set(list_tasks_by_category()["throughput"])
    for task_id in expected:
        task = create_task(task_id)
        assert task.throughput_entity
        assert task.quota == 16


def test_catalog_exposes_real_progression_robustness_and_milestone_tasks():
    research = get_benchmark_task("milestone_research_automation_v1")
    no_manual = get_benchmark_task("robustness_circuit_no_manual_v1")
    survival = get_benchmark_task("robustness_productive_survival_v1")
    rocket = get_benchmark_task("milestone_launch_rocket_v1")

    assert research.status == "ready"
    assert research.task_spec.objectives[0].kind == "research"
    assert {constraint.kind for constraint in no_manual.task_spec.constraints} >= {
        "max_manual_crafts",
        "forbidden_action",
    }
    assert {objective.kind for objective in survival.task_spec.objectives} == {
        "throughput",
        "survival",
    }
    assert rocket.task_spec.objectives[0].kind == "rocket_launch"
    assert rocket.status == "calibration_required"


def test_summary_distinguishes_ready_from_uncalibrated_tasks():
    summary = benchmark_summary()

    assert summary["benchmark_version"] == BENCHMARK_VERSION
    assert summary["task_count"] >= 36
    assert summary["ready_count"] > summary["calibration_required_count"]
    assert "lab_throughput_v1" in summary["suites"]
