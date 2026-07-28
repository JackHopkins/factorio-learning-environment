import pytest

from fle.eval.benchmark_agent import select_benchmark_tasks

pytestmark = pytest.mark.no_factorio


def test_benchmark_runner_selects_ready_microtask_split():
    tasks = select_benchmark_tasks(
        suite="api_microtasks_v1",
        statuses={"ready"},
        split="development",
    )

    assert len(tasks) == 11
    assert all(task.status == "ready" for task in tasks)
    assert all(task.benchmark_split == "development" for task in tasks)


def test_benchmark_runner_rejects_excluded_explicit_task():
    with pytest.raises(ValueError, match="excluded or unknown"):
        select_benchmark_tasks(
            suite="api_microtasks_v1",
            statuses={"ready"},
            split="development",
            task_ids={"micro_power_assembler_v1"},
        )
