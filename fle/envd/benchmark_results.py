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


# ---------------------------------------------------------------------------
# Capability ladder
# ---------------------------------------------------------------------------

LADDER_ELO_K = 32.0
LADDER_INITIAL_RATING = 1200.0


def _best_task_rewards(run: BenchmarkRun) -> dict[str, float]:
    """Best capped normalized reward per task across this run's attempts."""

    best: dict[str, float] = {}
    for attempt in run.attempts:
        score = max(0.0, min(float(attempt.scalar_reward), 1.0))
        current = best.get(attempt.task_id)
        if current is None or score > current:
            best[attempt.task_id] = score
    return best


def _elo_ratings(games: list[tuple[str, str, float]]) -> dict[str, float]:
    """Standard Elo over ordered ``(``a``,``b``,``score_a``)`` games."""

    ratings: dict[str, float] = defaultdict(lambda: LADDER_INITIAL_RATING)
    for a, b, score_a in games:
        rating_a = ratings[a]
        rating_b = ratings[b]
        expected_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
        ratings[a] = rating_a + LADDER_ELO_K * (score_a - expected_a)
        ratings[b] = rating_b + LADDER_ELO_K * (
            (1.0 - score_a) - (1.0 - expected_a)
        )
    return dict(ratings)


def build_capability_ladder(
    runs: list[BenchmarkRun],
) -> dict[str, Any]:
    """Rank benchmark runs with an Elo over their shared tasks.

    Each shared ``(model pair, task)`` is one game: the winner is the model
    with the higher best-attempt normalized reward on that task; equal
    rewards draw. Models that share no tasks are not compared directly.
    Aggregates (success rate, mean reward) cover every attempted task,
    including tasks unique to one model.
    """

    per_model: dict[str, dict[str, Any]] = {}
    task_best: dict[str, dict[str, float]] = defaultdict(dict)

    for run in runs:
        key = f"{run.model.provider}/{run.model.name}"
        entry = per_model.setdefault(
            key,
            {
                "model": run.model.model_dump(mode="json"),
                "runs": [],
                "attempts": [],
                "task_best": {},
            },
        )
        entry["runs"].append(run.run_id)
        entry["attempts"].extend(run.attempts)
        for task_id, reward in _best_task_rewards(run).items():
            current = entry["task_best"].get(task_id)
            if current is None or reward > current:
                entry["task_best"][task_id] = reward
            existing = task_best[task_id].get(key)
            if existing is None or reward > existing:
                task_best[task_id][key] = reward

    for key, entry in per_model.items():
        attempts = entry["attempts"]
        total = len(attempts)
        successes = sum(attempt.success for attempt in attempts)
        entry["attempt_count"] = total
        entry["success_rate"] = successes / total if total else 0.0
        entry["mean_reward"] = (
            sum(
                max(0.0, min(float(attempt.scalar_reward), 1.0))
                for attempt in attempts
            )
            / total
            if total
            else 0.0
        )

    model_keys = sorted(per_model)
    games: list[tuple[str, str, float]] = []
    for task_id in sorted(task_best):
        participants = sorted(
            model for model in model_keys if task_id in per_model[model]["task_best"]
        )
        for index, a in enumerate(participants):
            for b in participants[index + 1 :]:
                reward_a = per_model[a]["task_best"][task_id]
                reward_b = per_model[b]["task_best"][task_id]
                if reward_a > reward_b:
                    score_a = 1.0
                elif reward_a < reward_b:
                    score_a = 0.0
                else:
                    score_a = 0.5
                games.append((a, b, score_a))

    ratings = _elo_ratings(games)
    ladder_rows = sorted(
        (
            {
                "model_key": key,
                "model": per_model[key]["model"],
                "elo": round(ratings.get(key, LADDER_INITIAL_RATING), 1),
                "success_rate": round(per_model[key]["success_rate"], 4),
                "mean_reward": round(per_model[key]["mean_reward"], 4),
                "attempt_count": per_model[key]["attempt_count"],
                "tasks_covered": len(per_model[key]["task_best"]),
                "run_ids": sorted(per_model[key]["runs"]),
            }
            for key in model_keys
        ),
        key=lambda row: (-row["elo"], row["model_key"]),
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_version": BENCHMARK_VERSION,
        "elo_k": LADDER_ELO_K,
        "initial_rating": LADDER_INITIAL_RATING,
        "game_count": len(games),
        "ladder": ladder_rows,
    }


def render_ladder_markdown(ladder: dict[str, Any]) -> str:
    lines = [
        "# Factorio benchmark capability ladder",
        "",
        f"- generated: `{ladder['generated_at']}`",
        f"- benchmark version: `{ladder['benchmark_version']}`",
        f"- Elo K={ladder['elo_k']}, initial {ladder['initial_rating']}, "
        f"{ladder['game_count']} shared-task games",
        "",
        "| rank | model | elo | success | mean reward | attempts | tasks |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(ladder["ladder"], start=1):
        lines.append(
            f"| {rank} | {row['model']['name']} "
            f"({row['model']['provider']}) | {row['elo']} | "
            f"{row['success_rate']:.2f} | {row['mean_reward']:.3f} | "
            f"{row['attempt_count']} | {row['tasks_covered']} |"
        )
    lines.append("")
    return "\n".join(lines)


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
    ladder_parser = subparsers.add_parser(
        "ladder", help="Rank multiple result files with an Elo over shared tasks"
    )
    ladder_parser.add_argument("results", nargs="+", type=Path)
    ladder_parser.add_argument("--output", type=Path, default=None)
    ladder_parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "manifest":
        _write_json(args.output, benchmark_manifest())
        return

    if args.command == "ladder":
        runs = [
            BenchmarkRun.model_validate_json(path.read_text(encoding="utf-8"))
            for path in args.results
        ]
        for run, path in zip(runs, args.results):
            errors = validate_against_catalog(run)
            if errors:
                raise SystemExit(f"{path}:\n" + "\n".join(errors))
        ladder = build_capability_ladder(runs)
        if args.output is not None:
            _write_json(args.output, ladder)
        if args.markdown is not None:
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(
                render_ladder_markdown(ladder), encoding="utf-8"
            )
        print(json.dumps(ladder, indent=2, sort_keys=True))
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
