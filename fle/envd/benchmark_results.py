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
from typing import Any, Literal

from pydantic import Field, model_validator

from fle.envd.benchmark import BENCHMARK_VERSION, benchmark_catalog
from fle.envd.models import (
    CapabilityRating,
    ContractEpochOutcome,
    ContractEpochSpec,
    ParticipantIdentity,
    WireModel,
)

RESULT_SCHEMA_VERSION = "1.1.0"

# Attempts which fail before the environment produces an authoritative result
# must remain visible in the run artifact for auditability, but they are not
# model losses.  Older result files omit ``status`` and are interpreted as
# completed attempts by the Pydantic default below.
AttemptStatus = Literal["completed", "harness_failure", "infrastructure_failure"]


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
    status: AttemptStatus = "completed"
    failure_category: str | None = None
    failure_message: str | None = None
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
    recorded = len(run.attempts)
    evaluated_attempts = [
        attempt for attempt in run.attempts if attempt.status == "completed"
    ]
    total = len(evaluated_attempts)
    successes = sum(attempt.success for attempt in evaluated_attempts)
    per_task: dict[str, list[BenchmarkAttempt]] = defaultdict(list)
    per_mechanic: dict[str, list[BenchmarkAttempt]] = defaultdict(list)
    for attempt in evaluated_attempts:
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

    contracts_fulfilled = int(
        round(
            sum(
                attempt.metrics.get("contracts_fulfilled", 0.0)
                for attempt in evaluated_attempts
            )
        )
    )
    contracts_total = int(
        round(
            sum(
                attempt.metrics.get("contracts_total", 0.0)
                for attempt in evaluated_attempts
            )
        )
    )

    return {
        "run_id": run.run_id,
        "model": run.model.model_dump(mode="json"),
        "suite": run.suite,
        "benchmark_split": run.benchmark_split,
        "attempt_count": total,
        "recorded_attempt_count": recorded,
        "excluded_attempt_count": recorded - total,
        "success_count": successes,
        "success_rate": successes / total if total else 0.0,
        "invalid_intervention_rate": (
            sum(attempt.invalid_interventions for attempt in evaluated_attempts)
            / max(sum(attempt.interventions for attempt in evaluated_attempts), 1)
        ),
        "retry_intervention_rate": (
            sum(attempt.retry_interventions for attempt in evaluated_attempts)
            / max(sum(attempt.interventions for attempt in evaluated_attempts), 1)
        ),
        "retry_assisted_success_rate": (
            sum(
                attempt.success and attempt.retry_interventions > 0
                for attempt in evaluated_attempts
            )
            / total
            if total
            else 0.0
        ),
        "mean_interventions": (
            sum(attempt.interventions for attempt in evaluated_attempts) / total
            if total
            else 0.0
        ),
        "contracts_fulfilled": contracts_fulfilled,
        "contracts_total": contracts_total,
        "contract_fulfillment_rate": (
            contracts_fulfilled / contracts_total if contracts_total else 0.0
        ),
        "failure_counts": {
            category: sum(
                1
                for attempt in run.attempts
                if attempt.status != "completed"
                and (attempt.failure_category or "unknown") == category
            )
            for category in sorted(
                {
                    attempt.failure_category or "unknown"
                    for attempt in run.attempts
                    if attempt.status != "completed"
                }
            )
        },
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


def _eligible_attempts(run: BenchmarkRun) -> list[BenchmarkAttempt]:
    """Return attempts with an authoritative environment evaluation."""

    return [attempt for attempt in run.attempts if attempt.status == "completed"]


def _best_task_rewards(run: BenchmarkRun) -> dict[str, float]:
    """Best capped normalized reward per task across eligible attempts only."""

    best: dict[str, float] = {}
    for attempt in _eligible_attempts(run):
        score = max(0.0, min(float(attempt.scalar_reward), 1.0))
        current = best.get(attempt.task_id)
        if current is None or score > current:
            best[attempt.task_id] = score
    return best


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _model_key(run: BenchmarkRun) -> str:
    """Return a stable participant identity including model build metadata."""

    base = f"{run.model.provider}/{run.model.name}"
    qualifiers = [
        ("revision", run.model.revision),
        ("quantization", run.model.quantization),
        ("endpoint", run.model.endpoint),
    ]
    suffix = ",".join(f"{name}={value}" for name, value in qualifiers if value)
    return f"{base}[{suffix}]" if suffix else base


def _comparison_condition(run: BenchmarkRun) -> dict[str, Any]:
    """Return fields which must match before two runs can be compared.

    ``generation_config`` is intentionally retained as a whole.  This makes a
    newly-added generation knob comparison-safe by default instead of silently
    forgetting to add it to a hand-maintained allowlist.
    """

    return {
        "result_schema_version": run.result_schema_version,
        "benchmark_version": run.benchmark_version,
        "suite": run.suite,
        "benchmark_split": run.benchmark_split,
        "repository_commit": run.repository_commit,
        "environment": run.environment,
        "generation_config": run.generation_config,
    }


def _attempt_condition(run: BenchmarkRun) -> list[dict[str, Any]]:
    """Describe the planned/effective attempt count for every task.

    The task/seed/count tuple prevents a one-sample run from being merged with
    a best-of-N run, even when both runs happen to contain the same tasks.
    """

    grouped: dict[tuple[str, int], list[BenchmarkAttempt]] = defaultdict(list)
    for attempt in run.attempts:
        grouped[(attempt.task_id, attempt.seed)].append(attempt)
    return [
        {
            "task_id": task_id,
            "seed": seed,
            "recorded_attempts": len(attempts),
            "eligible_attempts": sum(
                attempt.status == "completed" for attempt in attempts
            ),
            "attempt_indices": sorted(attempt.attempt for attempt in attempts),
        }
        for (task_id, seed), attempts in sorted(grouped.items())
    ]


def _condition_key(run: BenchmarkRun) -> str:
    import hashlib

    return hashlib.sha256(
        _canonical_json(_comparison_condition(run)).encode("utf-8")
    ).hexdigest()[:16]


def _elo_ratings(games: list[tuple[str, str, float]]) -> dict[str, float]:
    """Standard Elo over ordered ``(``a``,``b``,``score_a``)`` games."""

    ratings: dict[str, float] = defaultdict(lambda: LADDER_INITIAL_RATING)
    for a, b, score_a in games:
        rating_a = ratings[a]
        rating_b = ratings[b]
        expected_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
        ratings[a] = rating_a + LADDER_ELO_K * (score_a - expected_a)
        ratings[b] = rating_b + LADDER_ELO_K * ((1.0 - score_a) - (1.0 - expected_a))
    return dict(ratings)


def build_capability_ladder(
    runs: list[BenchmarkRun],
) -> dict[str, Any]:
    """Rank benchmark runs with an Elo over their shared tasks.

    Each shared ``(model pair, task)`` is one game: the winner is the model
    with the higher best-attempt normalized reward on that task; equal
    rewards draw. Runs are only paired when their benchmark, revision,
    environment, harness, action reference, generation settings, and attempt
    plan all match. Ineligible harness/infrastructure attempts never become
    losses or games.
    """

    # Keep one participant per submitted run.  Merging independent runs would
    # make the result depend on how many artifacts happened to be supplied,
    # and best-of-N would unfairly dominate single-attempt runs.
    base_counts: defaultdict[str, int] = defaultdict(int)
    for run in runs:
        base_counts[_model_key(run)] += 1

    per_model: dict[str, dict[str, Any]] = {}
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for run in runs:
        base_key = _model_key(run)
        condition_key = _condition_key(run)
        key = base_key
        if base_counts[base_key] > 1:
            key = f"{base_key}@{condition_key}"
        # Duplicate submissions with identical conditions still need distinct
        # participants; append the run id only when the key is already used.
        if key in per_model:
            key = f"{key}#{run.run_id}"
        groups[condition_key].append(key)
        attempts = _eligible_attempts(run)
        task_best = _best_task_rewards(run)
        attempt_condition = _attempt_condition(run)
        total = len(attempts)
        per_model[key] = {
            "model": run.model.model_dump(mode="json"),
            "runs": [run.run_id],
            "attempts": attempts,
            "task_best": task_best,
            "condition_key": condition_key,
            "attempt_condition": attempt_condition,
            "recorded_attempt_count": len(run.attempts),
            "excluded_attempt_count": len(run.attempts) - total,
            "attempt_count": total,
            "success_rate": (
                sum(attempt.success for attempt in attempts) / total if total else 0.0
            ),
            "mean_reward": (
                sum(
                    max(0.0, min(float(attempt.scalar_reward), 1.0))
                    for attempt in attempts
                )
                / total
                if total
                else 0.0
            ),
        }

    task_best_by_group: defaultdict[tuple[str, str, int], dict[str, float]] = (
        defaultdict(dict)
    )
    for condition_key, participants in groups.items():
        for participant in participants:
            attempt_plan = {
                (item["task_id"], item["seed"]): item
                for item in per_model[participant]["attempt_condition"]
            }
            for task_id, reward in per_model[participant]["task_best"].items():
                matching = [
                    item
                    for (planned_task, _seed), item in attempt_plan.items()
                    if planned_task == task_id
                ]
                if len(matching) != 1:
                    continue
                plan = matching[0]
                # Exclude only the affected task when an attempt failed in the
                # harness. Other fully evaluated tasks remain comparable.
                if plan["eligible_attempts"] != plan["recorded_attempts"]:
                    continue
                task_best_by_group[(condition_key, task_id, plan["recorded_attempts"])][
                    participant
                ] = reward

    games: list[tuple[str, str, float]] = []
    for participants_by_task in task_best_by_group.values():
        participants = sorted(participants_by_task)
        for index, a in enumerate(participants):
            for b in participants[index + 1 :]:
                reward_a = participants_by_task[a]
                reward_b = participants_by_task[b]
                if reward_a > reward_b:
                    score_a = 1.0
                elif reward_a < reward_b:
                    score_a = 0.0
                else:
                    score_a = 0.5
                games.append((a, b, score_a))

    model_keys = sorted(per_model)
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
                "recorded_attempt_count": per_model[key]["recorded_attempt_count"],
                "excluded_attempt_count": per_model[key]["excluded_attempt_count"],
                "tasks_covered": len(per_model[key]["task_best"]),
                "run_ids": sorted(per_model[key]["runs"]),
                "condition_key": per_model[key]["condition_key"],
                "attempt_condition": per_model[key]["attempt_condition"],
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
        "| rank | model | condition | elo | success | mean reward | attempts | tasks |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(ladder["ladder"], start=1):
        lines.append(
            f"| {rank} | {row['model']['name']} "
            f"({row['model']['provider']}) | `{row['condition_key']}` | "
            f"{row['elo']} | "
            f"{row['success_rate']:.2f} | {row['mean_reward']:.3f} | "
            f"{row['attempt_count']} | {row['tasks_covered']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Adaptive contract benchmark records (section 18)
# ---------------------------------------------------------------------------

ADAPTIVE_RESULT_SCHEMA_VERSION = "adaptive-result-1"


class AdaptiveEpochRecord(WireModel):
    """One committed epoch with its outcome and rating trajectory."""

    spec: ContractEpochSpec
    outcome: ContractEpochOutcome
    rating_before: CapabilityRating
    rating_after: CapabilityRating | None = None  # None when unrated
    mapped_result: Literal["win", "draw", "loss", "unrated"] = "unrated"
    extrapolation_flagged: bool = False

    @model_validator(mode="after")
    def validate_commitment(self) -> "AdaptiveEpochRecord":
        if self.outcome.commitment_hash != self.spec.commitment_hash:
            raise ValueError(
                f"Outcome commitment {self.outcome.commitment_hash[:12]!r} "
                f"does not match spec {self.spec.commitment_hash[:12]!r}"
            )
        return self


class AdaptiveSessionRecord(WireModel):
    """Portable, reconstructable record of one adaptive benchmark session."""

    result_schema_version: str = ADAPTIVE_RESULT_SCHEMA_VERSION
    benchmark_version: str
    run_id: str
    session_id: str
    started_at: datetime
    completed_at: datetime
    repository_commit: str
    participant: ParticipantIdentity
    versions: dict[str, str]
    epochs: list[AdaptiveEpochRecord] = Field(default_factory=list)
    final_rating: CapabilityRating | None = None
    model_seconds: float = Field(default=0.0, ge=0.0)
    tool_seconds: float = Field(default=0.0, ge=0.0)
    paused_wall_seconds: float = Field(default=0.0, ge=0.0)
    runner_wall_seconds: float = Field(default=0.0, ge=0.0)
    infrastructure_error_count: int = Field(default=0, ge=0)
    extrapolation_count: int = Field(default=0, ge=0)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_epochs(self) -> "AdaptiveSessionRecord":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        indexes = [epoch.spec.epoch_index for epoch in self.epochs]
        if indexes != sorted(indexes):
            raise ValueError("epoch records must be ordered by epoch index")
        if len(indexes) != len(set(indexes)):
            raise ValueError("epoch indexes must be unique within a session")
        hashes = [epoch.spec.commitment_hash for epoch in self.epochs]
        if len(hashes) != len(set(hashes)):
            raise ValueError("committed epoch specs must be unique")
        for before, after in zip(self.epochs, self.epochs[1:]):
            expected_index = after.spec.epoch_index
            if expected_index != before.spec.epoch_index + 1:
                raise ValueError("epoch indexes must be contiguous")
        return self


def validate_adaptive_session(record: AdaptiveSessionRecord) -> list[str]:
    """Return integrity errors without mutating the submitted artifact."""
    errors: list[str] = []
    for epoch in record.epochs:
        if (
            epoch.outcome.session_id != record.session_id
            or epoch.spec.session_id != record.session_id
        ):
            errors.append(f"epoch {epoch.spec.epoch_index} session id mismatch")
        if epoch.outcome.epoch_index != epoch.spec.epoch_index:
            errors.append(f"epoch {epoch.spec.epoch_index} outcome index mismatch")
        if epoch.rating_after is not None and epoch.mapped_result == "unrated":
            if epoch.outcome.status not in ("infrastructure_error", "invalid"):
                errors.append(
                    f"epoch {epoch.spec.epoch_index} rated without mapped result"
                )
    if record.final_rating is not None and record.final_rating.rated_epoch_count != sum(
        1 for e in record.epochs if e.mapped_result != "unrated"
    ):
        errors.append("final rating rated_epoch_count does not match rated epochs")
    return errors


def summarize_adaptive_session(
    record: AdaptiveSessionRecord,
) -> dict[str, Any]:
    """Section 18 published summary values."""
    epochs = record.epochs
    rated = [e for e in epochs if e.mapped_result != "unrated"]
    wins = sum(e.mapped_result == "win" for e in rated)
    draws = sum(e.mapped_result == "draw" for e in rated)
    losses = sum(e.mapped_result == "loss" for e in rated)
    unrated = len(epochs) - len(rated)

    fulfillment_by_band: dict[int, dict[str, float]] = {}
    for e in epochs:
        band = e.spec.features.stage_band
        bucket = fulfillment_by_band.setdefault(band, {"epochs": 0, "fulfilled": 0})
        bucket["epochs"] += 1
        bucket["fulfilled"] += int(e.outcome.status == "fulfilled")

    first_deliveries = sorted(
        e.outcome.first_delivery_tick
        for e in epochs
        if e.outcome.first_delivery_tick is not None
    )
    completions = sorted(
        e.outcome.completion_tick
        for e in epochs
        if e.outcome.completion_tick is not None
    )

    def quantile(values: list[int], q: float) -> int | None:
        if not values:
            return None
        index = min(int(len(values) * q), len(values) - 1)
        return values[index]

    total_requested = sum(e.outcome.requested_quantity for e in epochs)
    total_delivered = sum(e.outcome.delivered_quantity for e in epochs)

    return {
        "run_id": record.run_id,
        "participant_id": record.participant.participant_id,
        "benchmark_version": record.benchmark_version,
        "versions": record.versions,
        "rated_epoch_count": len(rated),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "unrated_epochs": unrated,
        "orders_fulfilled": sum(1 for e in epochs if e.outcome.status == "fulfilled"),
        "units_delivered": total_delivered,
        "units_requested": total_requested,
        "fulfillment_by_band": {
            str(band): {
                "fulfilled": bucket["fulfilled"],
                "epochs": bucket["epochs"],
            }
            for band, bucket in sorted(fulfillment_by_band.items())
        },
        "session_simulation_ticks": sum(
            e.outcome.simulation_ticks_used for e in epochs
        ),
        "agent_interventions": sum(e.outcome.interventions_used for e in epochs),
        "first_delivery_ticks": {
            "median": quantile(first_deliveries, 0.5),
            "p90": quantile(first_deliveries, 0.9),
        },
        "completion_ticks": {
            "median": quantile(completions, 0.5),
            "p90": quantile(completions, 0.9),
        },
        "model_seconds": round(record.model_seconds, 3),
        "tool_seconds": round(record.tool_seconds, 3),
        "paused_wall_seconds": round(record.paused_wall_seconds, 3),
        "runner_wall_seconds": round(record.runner_wall_seconds, 3),
        "infrastructure_error_count": record.infrastructure_error_count,
        "extrapolation_count": record.extrapolation_count,
        "final_rating": (
            record.final_rating.model_dump(mode="json") if record.final_rating else None
        ),
        "commitment_hashes": [e.spec.commitment_hash for e in epochs],
    }


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
            args.markdown.write_text(render_ladder_markdown(ladder), encoding="utf-8")
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
