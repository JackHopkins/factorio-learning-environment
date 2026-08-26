from datetime import datetime, timezone

import pytest

from fle.envd.benchmark import BENCHMARK_VERSION, get_benchmark_task
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
    validate_against_catalog,
)

pytestmark = pytest.mark.no_factorio


def test_result_record_validates_catalog_fingerprints_and_summarizes():
    task = get_benchmark_task("micro_place_lab_v1")
    now = datetime.now(timezone.utc)
    run = BenchmarkRun(
        run_id="local-model-micro-v1",
        benchmark_version=BENCHMARK_VERSION,
        model=ModelIdentity(name="test-model", provider="local"),
        started_at=now,
        completed_at=now,
        repository_commit="0123456789abcdef",
        attempts=[
            BenchmarkAttempt(
                task_id=task.task_id,
                task_fingerprint=task.task_spec.fingerprint,
                attempt=0,
                seed=0,
                success=True,
                scalar_reward=1,
                interventions=2,
                retry_interventions=1,
                elapsed_seconds=1.5,
                metrics={"contracts_fulfilled": 2.0, "contracts_total": 3.0},
            )
        ],
    )

    assert validate_against_catalog(run) == []
    summary = summarize_run(run)
    assert summary["success_rate"] == 1
    assert summary["retry_intervention_rate"] == 0.5
    assert summary["retry_assisted_success_rate"] == 1
    assert summary["per_mechanic_success_rate"]["placement"] == 1
    assert summary["contracts_fulfilled"] == 2
    assert summary["contracts_total"] == 3
    assert summary["contract_fulfillment_rate"] == pytest.approx(2 / 3)


def test_result_record_rejects_unknown_fingerprint():
    task = get_benchmark_task("micro_place_lab_v1")
    now = datetime.now(timezone.utc)
    run = BenchmarkRun(
        run_id="bad-fingerprint",
        model=ModelIdentity(name="test-model", provider="local"),
        started_at=now,
        completed_at=now,
        repository_commit="0123456789abcdef",
        attempts=[
            BenchmarkAttempt(
                task_id=task.task_id,
                task_fingerprint="bad",
                attempt=0,
                seed=0,
                success=False,
                scalar_reward=0,
                interventions=1,
                elapsed_seconds=1,
            )
        ],
    )

    assert "fingerprint" in validate_against_catalog(run)[0]
