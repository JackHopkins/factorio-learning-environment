"""Record defensively brokered, context-blind Codex benchmark attempts.

The evaluated subagent receives only the public task packet and returns one
program without tools. This script is the trusted broker: it alone talks to
envd, writes engine trajectories, and assembles validated benchmark results.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fle.envd.benchmark import benchmark_catalog
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
    validate_against_catalog,
)
from fle.envd.client import HTTPEnvironmentClient
from fle.envd.task_builder import render_task_prompt


def _task(task_id: str):
    return next(
        task
        for task in benchmark_catalog()
        if task.task_id == task_id
        and task.suite == "api_microtasks_v1"
        and task.status == "ready"
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


async def _execute(args: argparse.Namespace) -> None:
    task = _task(args.task_id)
    code = base64.b64decode(args.code_base64).decode("utf-8")
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    async with HTTPEnvironmentClient(args.envd_url, args.timeout) as client:
        lease = await client.lease(task.task_spec, tool_error_retry_budget=0)
        initial = await client.observe(lease.lease_id)
        try:
            result = await client.execute(lease.lease_id, code)
            post = await client.observe(lease.lease_id)
            verification = await client.finalize(lease.lease_id)
        finally:
            await client.release(lease.lease_id)
    completed_at = datetime.now(timezone.utc)
    trajectory = {
        "mode": "defensive_context_blind_subagent",
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "provider": "openai-codex/brokered-subagent",
        "blindness": {
            "conversation_context": "none",
            "environment_access": "broker_only",
            "filesystem_access": "prohibited_by_protocol",
            "filesystem_os_isolation": False,
            "agent_reported_tool_calls_used": False,
            "parent_tool_trace_available": False,
            "fresh_agent_per_task": True,
        },
        "run_at": completed_at.isoformat(),
        "started_at": started_at.isoformat(),
        "canonical_task_prompt": render_task_prompt(task.task_spec),
        "subagent_packet_recorded": False,
        "task": task.task_spec.model_dump(mode="json"),
        "initial_observation": initial.model_dump(mode="json"),
        "actions": [{"code": code, "result": result.model_dump(mode="json")}],
        "post_action_observations": [post.model_dump(mode="json")],
        "verification": verification.model_dump(mode="json"),
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(args.output, trajectory)
    print(
        json.dumps(
            {
                "task_id": task.task_id,
                "success": verification.success,
                "reward": verification.scalar_reward,
                "invalid": sum(event.error for event in verification.action_events),
                "output": str(args.output),
            }
        )
    )


def _assemble(args: argparse.Namespace) -> None:
    tasks = [
        task
        for task in benchmark_catalog()
        if task.suite == "api_microtasks_v1"
        and task.status == "ready"
        and task.benchmark_split == args.split
    ]
    attempts: list[BenchmarkAttempt] = []
    starts: list[datetime] = []
    completions: list[datetime] = []
    for task in tasks:
        path = args.trajectory_dir / f"{task.task_id}-attempt-0.json"
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        verification = trajectory["verification"]
        events = verification.get("action_events") or []
        starts.append(datetime.fromisoformat(trajectory["started_at"]))
        completions.append(datetime.fromisoformat(trajectory["run_at"]))
        attempts.append(
            BenchmarkAttempt(
                task_id=task.task_id,
                task_fingerprint=task.task_spec.fingerprint,
                attempt=0,
                seed=task.task_spec.seed,
                success=bool(verification["success"]),
                scalar_reward=float(verification["scalar_reward"]),
                interventions=len(events),
                invalid_interventions=sum(bool(event["error"]) for event in events),
                retry_interventions=sum(
                    bool(event["evaluation_retry"]) for event in events
                ),
                elapsed_seconds=float(trajectory["elapsed_seconds"]),
                termination_reason=verification.get("termination_reason"),
                trajectory_artifact=str(path.relative_to(args.output.parent)).replace(
                    "\\", "/"
                ),
                metrics={
                    str(key): float(value)
                    for key, value in verification.get("metrics", {}).items()
                    if isinstance(value, (int, float))
                },
            )
        )
    started_at = min(starts)
    run = BenchmarkRun(
        run_id=(
            f"{args.slug}-blind-{args.split}-"
            f"{started_at.strftime('%Y%m%dT%H%M%SZ')}"
        ),
        model=ModelIdentity(
            name=args.model,
            provider="openai-codex/brokered-subagent",
            revision=f"Codex desktop 2026-07-27; effort={args.reasoning_effort}",
        ),
        suite="api_microtasks_v1",
        benchmark_split=args.split,
        started_at=started_at,
        completed_at=max(completions),
        repository_commit=_git_commit(),
        environment={
            "envd_url": args.envd_url,
            "factorio_version": ["2.0.73"],
            "action_profiles": ["fle-program-v1"],
            "runtime": "windows-local-docker-rcon",
            "defensive_context_blind": True,
            "os_enforced_filesystem_isolation": False,
        },
        generation_config={
            "fork_turns": "none",
            "reasoning_effort": args.reasoning_effort,
            "fresh_agent_per_task": True,
            "agent_tools_permitted": [],
            "environment_access": "trusted_broker_only",
            "packet_mode": "manually_brokered_public_api_subset",
            "subagent_packet_recorded": False,
            "parent_tool_trace_available": False,
            "interventions_requested_per_task": 1,
            "tool_error_retries": 0,
            "attempts_per_task": 1,
        },
        attempts=attempts,
    )
    errors = validate_against_catalog(run)
    if errors:
        raise RuntimeError("invalid result:\n" + "\n".join(errors))
    _write_json(args.output, run.model_dump(mode="json"))
    _write_json(args.output.with_suffix(".summary.json"), summarize_run(run))
    print(json.dumps(summarize_run(run), indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("execute")
    execute.add_argument("--task-id", required=True)
    execute.add_argument("--model", required=True)
    execute.add_argument("--reasoning-effort", required=True)
    execute.add_argument("--code-base64", required=True)
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--envd-url", default="http://127.0.0.1:8172")
    execute.add_argument("--timeout", type=float, default=1200)
    assemble = commands.add_parser("assemble")
    assemble.add_argument("--model", required=True)
    assemble.add_argument("--reasoning-effort", required=True)
    assemble.add_argument("--slug", required=True)
    assemble.add_argument("--split", default="development")
    assemble.add_argument("--trajectory-dir", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)
    assemble.add_argument("--envd-url", default="http://127.0.0.1:8172")
    args = parser.parse_args()
    if args.command == "execute":
        asyncio.run(_execute(args))
    else:
        _assemble(args)


if __name__ == "__main__":
    main()
