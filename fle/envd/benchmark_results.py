"""Portable manifests and result records for the Factorio benchmark.

The JSON format is intentionally provider-neutral so local models, hosted APIs,
and Prime-RL evaluations can publish comparable artifacts to GitHub.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from fle.envd.benchmark import BENCHMARK_VERSION, benchmark_catalog
from fle.envd.models import WireModel

RESULT_SCHEMA_VERSION = "1.0.0"


class ModelIdentity(WireModel):
    name: str
    provider: str
    revision: str | None = None
    quantization: str | None = None
    endpoint: str | None = None


class BenchmarkAttempt(WireModel):
    task_id: str
    task_fingerprint: str
    attempt: int = Field(ge=0)
    seed: int
    success: bool
    scalar_reward: float
    interventions: int = Field(ge=0)
    invalid_interventions: int = Field(default=0, ge=0)
    retry_interventions: int = Field(default=0, ge=0)
    elapsed_seconds: float = Field(ge=0)
    termination_reason: str | None = None
    trajectory_artifact: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class BenchmarkRun(WireModel):
    result_schema_version: str = RESULT_SCHEMA_VERSION
    benchmark_version: str = BENCHMARK_VERSION
    run_id: str
    model: ModelIdentity
    suite: str = "api_microtasks_v1"
    benchmark_split: str | None = None
    started_at: datetime
    completed_at: datetime
    repository_commit: str
    environment: dict[str, Any] = Field(default_factory=dict)
    generation_config: dict[str, Any] = Field(default_factory=dict)
    attempts: list[BenchmarkAttempt]

    @model_validator(mode="after")
    def validate_run(self) -> "BenchmarkRun":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        keys = [
            (attempt.task_id, attempt.seed, attempt.attempt)
            for attempt in self.attempts
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("attempt keys must be unique within a benchmark run")
        return self


def validate_against_catalog(run: BenchmarkRun) -> list[str]:
    """Return catalog-integrity errors without changing the submitted record."""

    errors: list[str] = []
    if run.benchmark_version != BENCHMARK_VERSION:
        errors.append(
            f"benchmark version {run.benchmark_version!r} does not match "
            f"{BENCHMARK_VERSION!r}"
        )
    catalog = {
        task.task_id: task
        for task in benchmark_catalog()
        if task.suite == run.suite
        and (run.benchmark_split is None or task.benchmark_split == run.benchmark_split)
    }
    for attempt in run.attempts:
        task = catalog.get(attempt.task_id)
        if task is None:
            errors.append(
                f"{attempt.task_id!r} is not in suite {run.suite!r}"
                + (
                    f" split {run.benchmark_split!r}"
                    if run.benchmark_split is not None
                    else ""
                )
            )
            continue
        if attempt.task_fingerprint != task.task_spec.fingerprint:
            errors.append(f"{attempt.task_id!r} fingerprint does not match the catalog")
    return errors


def summarize_run(run: BenchmarkRun) -> dict[str, Any]:
    catalog = {task.task_id: task for task in benchmark_catalog()}
    total = len(run.attempts)
    successes = sum(attempt.success for attempt in run.attempts)
    per_task: dict[str, list[BenchmarkAttempt]] = defaultdict(list)
    per_mechanic: dict[str, list[BenchmarkAttempt]] = defaultdict(list)
    for attempt in run.attempts:
        per_task[attempt.task_id].append(attempt)
        mechanics = (
            catalog[attempt.task_id].mechanics if attempt.task_id in catalog else []
        )
        for mechanic in mechanics:
            per_mechanic[mechanic].append(attempt)

    def score(attempts: list[BenchmarkAttempt]) -> float:
        return (
            sum(attempt.success for attempt in attempts) / len(attempts)
            if attempts
            else 0.0
        )

    return {
        "run_id": run.run_id,
        "model": run.model.model_dump(mode="json"),
        "suite": run.suite,
        "benchmark_split": run.benchmark_split,
        "attempt_count": total,
        "success_count": successes,
        "success_rate": successes / total if total else 0.0,
        "invalid_intervention_rate": (
            sum(attempt.invalid_interventions for attempt in run.attempts)
            / max(sum(attempt.interventions for attempt in run.attempts), 1)
        ),
        "retry_intervention_rate": (
            sum(attempt.retry_interventions for attempt in run.attempts)
            / max(sum(attempt.interventions for attempt in run.attempts), 1)
        ),
        "retry_assisted_success_rate": (
            sum(
                attempt.success and attempt.retry_interventions > 0
                for attempt in run.attempts
            )
            / total
            if total
            else 0.0
        ),
        "mean_interventions": (
            sum(attempt.interventions for attempt in run.attempts) / total
            if total
            else 0.0
        ),
        "per_task_success_rate": {
            task_id: score(attempts) for task_id, attempts in sorted(per_task.items())
        },
        "per_mechanic_success_rate": {
            mechanic: score(attempts)
            for mechanic, attempts in sorted(per_mechanic.items())
        },
    }


def benchmark_manifest() -> dict[str, Any]:
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tasks": [task.model_dump(mode="json") for task in benchmark_catalog()],
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("output", type=Path)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("result", type=Path)
    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("result", type=Path)
    args = parser.parse_args()

    if args.command == "manifest":
        _write_json(args.output, benchmark_manifest())
        return

    run = BenchmarkRun.model_validate_json(args.result.read_text(encoding="utf-8"))
    errors = validate_against_catalog(run)
    if errors:
        raise SystemExit("\n".join(errors))
    if args.command == "validate":
        print(f"valid: {run.run_id}")
    else:
        print(json.dumps(summarize_run(run), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
