"""Run a model across a Factorio benchmark suite and emit publishable JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

from fle.envd.action_reference import (
    ACTION_PROFILE_REFERENCE_ID,
    ACTION_PROFILE_REFERENCE_SHA256,
)
from fle.envd.benchmark import BenchmarkTask, benchmark_catalog
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
    validate_against_catalog,
)
from fle.eval.remote_agent import _rollout


def select_benchmark_tasks(
    *,
    suite: str,
    statuses: set[str],
    split: str | None,
    task_ids: set[str] | None = None,
) -> list[BenchmarkTask]:
    selected = [
        task
        for task in benchmark_catalog()
        if task.suite == suite
        and task.status in statuses
        and (split is None or task.benchmark_split == split)
        and (task_ids is None or task.task_id in task_ids)
    ]
    if task_ids is not None:
        missing = sorted(task_ids - {task.task_id for task in selected})
        if missing:
            raise ValueError(
                "requested tasks were excluded or unknown: " + ", ".join(missing)
            )
    if not selected:
        known_suites = sorted({task.suite for task in benchmark_catalog()})
        raise ValueError(
            f"benchmark selection matched no tasks; known suites: {known_suites}"
        )
    return selected


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


async def run_benchmark(args: argparse.Namespace) -> BenchmarkRun:
    tasks = select_benchmark_tasks(
        suite=args.suite,
        statuses=set(args.status),
        split=args.split,
        task_ids=set(args.task_id) if args.task_id else None,
    )
    if args.limit is not None:
        tasks = tasks[: args.limit]
    started_at = datetime.now(timezone.utc)
    run_id = args.run_id or (f"{args.suite}-{started_at.strftime('%Y%m%dT%H%M%SZ')}")
    trajectory_dir = args.output.parent / f"{args.output.stem}-trajectories"
    attempts: list[BenchmarkAttempt] = []
    resolved_model = args.model

    for task in tasks:
        for attempt_index in range(args.attempts):
            rollout_args = SimpleNamespace(
                envd_url=args.envd_url,
                model_base_url=args.model_base_url,
                api_key=args.api_key,
                model=args.model,
                task_id=task.task_id,
                max_turns=args.max_turns,
                tool_error_retries=args.tool_error_retries,
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
                max_tool_chars=args.max_tool_chars,
                context_budget_chars=args.context_budget_chars,
                request_timeout=args.request_timeout,
                cache_prompt=args.cache_prompt,
            )
            rollout = await _rollout(rollout_args)
            resolved_model = str(rollout["model"])
            trajectory_path = trajectory_dir / (
                f"{task.task_id}-attempt-{attempt_index}.json"
            )
            _atomic_json(trajectory_path, rollout)
            verification = rollout.get("verification") or {}
            events = verification.get("action_events") or []
            attempts.append(
                BenchmarkAttempt(
                    task_id=task.task_id,
                    task_fingerprint=task.task_spec.fingerprint,
                    attempt=attempt_index,
                    seed=task.task_spec.seed,
                    success=bool(verification.get("success", False)),
                    scalar_reward=float(verification.get("scalar_reward", 0)),
                    interventions=len(events),
                    invalid_interventions=sum(
                        bool(event.get("error")) for event in events
                    ),
                    retry_interventions=sum(
                        bool(event.get("evaluation_retry")) for event in events
                    ),
                    elapsed_seconds=float(rollout["elapsed_seconds"]),
                    termination_reason=(
                        verification.get("termination_reason")
                        or rollout.get("stop_reason")
                    ),
                    trajectory_artifact=str(
                        trajectory_path.relative_to(args.output.parent)
                    ).replace("\\", "/"),
                    metrics={
                        str(key): float(value)
                        for key, value in (verification.get("metrics") or {}).items()
                        if isinstance(value, (int, float))
                    },
                )
            )
            print(
                json.dumps(
                    {
                        "task_id": task.task_id,
                        "attempt": attempt_index,
                        "success": bool(verification.get("success", False)),
                        "reward": verification.get("scalar_reward", 0),
                        "elapsed_seconds": rollout["elapsed_seconds"],
                    }
                ),
                flush=True,
            )

    run = BenchmarkRun(
        run_id=run_id,
        model=ModelIdentity(
            name=resolved_model,
            provider=args.provider,
            revision=args.model_revision,
            quantization=args.quantization,
        ),
        suite=args.suite,
        benchmark_split=args.split,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        repository_commit=args.repository_commit or _git_commit(),
        environment={
            "envd_url": args.envd_url,
            "factorio_version": sorted(
                {task.task_spec.factorio_version for task in tasks}
            ),
            "action_profiles": sorted(
                {task.task_spec.action_profile for task in tasks}
            ),
        },
        generation_config={
            "temperature": args.temperature,
            "max_output_tokens": args.max_output_tokens,
            "max_turns_override": args.max_turns,
            "tool_error_retries": args.tool_error_retries,
            "context_budget_chars": args.context_budget_chars,
            "attempts_per_task": args.attempts,
            "selected_statuses": args.status,
            "cache_prompt_extension": args.cache_prompt,
            "action_reference_id": ACTION_PROFILE_REFERENCE_ID,
            "action_reference_sha256": ACTION_PROFILE_REFERENCE_SHA256,
        },
        attempts=attempts,
    )
    errors = validate_against_catalog(run)
    if errors:
        raise RuntimeError("invalid benchmark result:\n" + "\n".join(errors))
    return run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--model-base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument(
        "--api-key",
        default=None,
        help=(
            "API key for the inference route. Defaults are resolved from the "
            "--provider: openrouter reads OPEN_ROUTER_API_KEY, zen reads "
            "OPENCODE_ZEN_API_KEY; otherwise DEEPSEEK_API_KEY then "
            "OPENAI_API_KEY."
        ),
    )
    parser.add_argument("--model", default="auto")
    parser.add_argument("--provider", default="local")
    parser.add_argument("--model-revision")
    parser.add_argument("--quantization")
    parser.add_argument("--suite", default="api_microtasks_v1")
    parser.add_argument("--status", action="append", default=[])
    parser.add_argument("--split", choices=["development", "validation", "test"])
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-turns", type=int, default=0)
    parser.add_argument("--tool-error-retries", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--max-tool-chars", type=int, default=6_000)
    parser.add_argument("--context-budget-chars", type=int, default=18_000)
    parser.add_argument("--request-timeout", type=float, default=1200.0)
    parser.add_argument("--cache-prompt", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--repository-commit")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _resolve_api_key(provider: str) -> str:
    """Provider-aware key resolution so a DeepSeek key never leaks to an
    OpenRouter endpoint (and vice versa)."""

    provider = (provider or "").lower()
    if provider == "openrouter":
        return (
            os.getenv("OPEN_ROUTER_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "local-no-key"
        )
    if provider in {"zen", "opencode", "opencodezen"}:
        return (
            os.getenv("OPENCODE_ZEN_API_KEY")
            or os.getenv("OPEN_CODE_ZEN_API_KEY")
            or os.getenv("ZEN_API_KEY")
            or os.getenv("OPENCODE_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "local-no-key"
        )
    return (
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or "local-no-key"
    )


def main() -> int:
    args = _parser().parse_args()
    if args.attempts < 1:
        raise SystemExit("--attempts must be positive")
    if args.tool_error_retries < 0:
        raise SystemExit("--tool-error-retries cannot be negative")
    if not args.status:
        args.status = ["ready"]
    if args.api_key is None:
        args.api_key = _resolve_api_key(args.provider)
    started = time.perf_counter()
    run = asyncio.run(run_benchmark(args))
    _atomic_json(args.output, run.model_dump(mode="json"))
    summary = summarize_run(run)
    summary["wall_clock_seconds"] = round(time.perf_counter() - started, 3)
    _atomic_json(args.output.with_suffix(".summary.json"), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
