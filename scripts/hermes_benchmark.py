"""Benchmark Factorio tasks through Hermes Agent as the harness.

One harness for all models keeps comparisons clean. Produces
BenchmarkRun JSONs compatible with `fle-benchmark-results ladder`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from fle.envd.benchmark import get_benchmark_task
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
)
from fle.envd.client import HTTPEnvironmentClient
from fle.envd.curriculum import BUILTIN_TASKS, get_builtin_task

HERMES = r"C:\Users\WillR\AppData\Local\hermes\hermes-agent\bin\hermes.exe"
CONFIG = Path(r"C:\Users\WillR\AppData\Local\hermes\config.yaml")


def _task_spec(task_id: str):
    if task_id in BUILTIN_TASKS:
        return get_builtin_task(task_id)
    return get_benchmark_task(task_id).task_spec


def _rewrite_lease(lease_id: str) -> None:
    text = CONFIG.read_text(encoding="utf-8")
    text = re.sub(r'LEASE_ID: "[^"]*"', f'LEASE_ID: "{lease_id}"', text)
    CONFIG.write_text(text, encoding="utf-8")


async def _finalize_with_retry(client, lease_id: str, tries: int = 3):
    last: Exception | None = None
    for attempt in range(tries):
        try:
            snapshot = await client.finalize(lease_id)
            try:
                await client.release(lease_id)
            except Exception:
                pass
            return snapshot
        except Exception as exc:  # noqa: BLE001 - transient transport races
            last = exc
            await asyncio.sleep(3 * (attempt + 1))
    raise RuntimeError(f"finalize failed after {tries} tries") from last


def build_prompt(spec) -> str:
    goal_line = spec.goal.splitlines()[0] if spec.goal else ""
    return (
        f"Objective: {spec.goal}\n\n"
        "You control a real Factorio factory exclusively through the two "
        "factorio MCP tools: mcp__factorio__factorio_observe_factory and "
        "mcp__factorio__factorio_execute_program. Call the observe tool "
        "FIRST. Then run short Python programs via the execute tool's "
        "`code` argument (available names: inspect_inventory, craft_item, "
        "place_entity, move_to, nearest, get_entities, insert_item, "
        "extract_item, set_entity_recipe, harvest_resource). Prefer the "
        f"supplied inventory over gathering. Solve only: {goal_line}. "
        "When the objective is met, stop calling tools."
    )


_USAGE_KEYS = {
    "input_tokens": ("input_tokens", "prompt_tokens", "input"),
    "output_tokens": ("output_tokens", "completion_tokens", "output"),
    "cached_tokens": (
        "cache_read_input_tokens",
        "cached_tokens",
        "cache_read",
        "cached",
    ),
}


def _extract_usage(output: str) -> dict[str, float]:
    """Sum token counters appearing anywhere in harness output.

    Providers spell these differently (OpenAI vs Anthropic vs OpenRouter
    conventions); every recognized key contributes to its bucket. Returns
    zeros when the harness prints no usage, so records stay comparable.
    """

    totals = {"input_tokens": 0.0, "output_tokens": 0.0, "cached_tokens": 0.0}
    for match in re.finditer(r"\{[^{}]*\}", output):
        try:
            blob = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if not isinstance(blob, dict):
            continue
        for bucket, keys in _USAGE_KEYS.items():
            for key in keys:
                value = blob.get(key)
                if isinstance(value, (int, float)) and value > 0:
                    totals[bucket] += float(value)
                    break
    # Line-based fallback: "prompt_tokens=123" / "output: 456" styles.
    for bucket, keys in _USAGE_KEYS.items():
        for key in keys:
            for match in re.finditer(rf"{key}\s*[=:]\s*(\d+)", output):
                totals[bucket] += float(match.group(1))
    return totals


_HERMES_DB = Path(r"C:\Users\WillR\AppData\Local\hermes\state.db")


def _session_usage(scratch_dir: Path) -> dict[str, float]:
    """Pull authoritative usage from Hermes' store by matching session cwd."""

    import sqlite3

    empty = {
        "input_tokens": 0.0,
        "output_tokens": 0.0,
        "cached_tokens": 0.0,
        "cache_write_tokens": 0.0,
        "reasoning_tokens": 0.0,
        "api_calls": 0.0,
        "estimated_cost_usd": 0.0,
        "actual_cost_usd": 0.0,
    }
    if not _HERMES_DB.exists():
        return empty
    try:
        conn = sqlite3.connect(f"file:{_HERMES_DB}?mode=ro", uri=True, timeout=5)
        row = conn.execute(
            """
            SELECT input_tokens, output_tokens, cache_read_tokens,
                   cache_write_tokens, reasoning_tokens, api_call_count,
                   estimated_cost_usd, actual_cost_usd
            FROM sessions WHERE cwd = ?
            ORDER BY last_activity_at DESC LIMIT 1
            """,
            (str(scratch_dir),),
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return empty
    if row is None:
        return empty
    keys = list(empty)
    values = {key: float(value or 0) for key, value in zip(keys, row)}
    # Cache-write counts toward billed input on most providers.
    values["input_tokens"] += values["cache_write_tokens"]
    return values


async def run_attempt(
    model: str, task_id: str, attempt_index: int, args: argparse.Namespace
) -> tuple[BenchmarkAttempt, dict]:
    spec = _task_spec(task_id)
    async with HTTPEnvironmentClient(args.envd_url) as client:
        lease = await client.lease(spec)
        try:
            _rewrite_lease(lease.lease_id)
            scratch = Path(tempfile.mkdtemp(prefix="hermes-scratch-"))
            wall_start = time.perf_counter()
            usage_file = scratch / "usage.json"
            try:
                completed = subprocess.run(
                    [
                        HERMES,
                        "chat",
                        "-q",
                        build_prompt(spec),
                        "--provider",
                        "openrouter",
                        "-m",
                        model,
                        "--yolo",
                        "--quiet",
                        "--ignore-rules",
                        "--reasoning",
                        args.reasoning,
                        "--max-turns",
                        str(args.max_turns),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=args.timeout_seconds,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(scratch),
                )
                output = (completed.stdout or "") + "\n" + (completed.stderr or "")
            except subprocess.TimeoutExpired as exc:
                partial = exc.stdout or b""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", errors="replace")
                output = partial + "\n[hermes timed out]"
            elapsed = time.perf_counter() - wall_start
            # Authoritative usage: Hermes' own report (written even on
            # failure); fall back to the session store, then stdout parsing.
            usage = _session_usage(scratch)
            if usage_file.exists():
                try:
                    report = json.loads(usage_file.read_text(encoding="utf-8"))
                    if report.get("input_tokens"):
                        usage.update(
                            {
                                "input_tokens": float(
                                    report.get("input_tokens") or 0
                                ),
                                "output_tokens": float(
                                    report.get("output_tokens") or 0
                                ),
                                "cached_tokens": float(
                                    report.get("cache_read_tokens") or 0
                                ),
                                "cache_write_tokens": float(
                                    report.get("cache_write_tokens") or 0
                                ),
                                "reasoning_tokens": float(
                                    report.get("reasoning_tokens") or 0
                                ),
                                "api_calls": float(report.get("api_calls") or 0),
                                "estimated_cost_usd": float(
                                    report.get("estimated_cost_usd") or 0
                                ),
                            }
                        )
                except (json.JSONDecodeError, OSError):
                    pass
            parsed = _extract_usage(output)
            for key in ("input_tokens", "output_tokens", "cached_tokens"):
                if usage[key] == 0 and parsed[key] > 0:
                    usage[key] = parsed[key]
            transcript_tail = output[-4000:]
        finally:
            snapshot = await _finalize_with_retry(client, lease.lease_id)

    events = snapshot.action_events or []
    attempt = BenchmarkAttempt(
        task_id=task_id,
        task_fingerprint=snapshot.task_fingerprint,
        attempt=attempt_index,
        seed=spec.seed,
        success=bool(snapshot.success),
        scalar_reward=float(snapshot.scalar_reward),
        interventions=len(events),
        invalid_interventions=sum(1 for event in events if event.error),
        retry_interventions=sum(1 for event in events if event.evaluation_retry),
        elapsed_seconds=elapsed,
        termination_reason=snapshot.termination_reason,
        metrics={
            "contracts": float(snapshot.rewards.contracts),
            "contract_penalty": float(snapshot.rewards.contract_penalty),
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cached_tokens": usage["cached_tokens"],
            "cache_write_tokens": usage["cache_write_tokens"],
            "reasoning_tokens": usage["reasoning_tokens"],
            "api_calls": usage["api_calls"],
            "estimated_cost_usd": usage["estimated_cost_usd"],
            "actual_cost_usd": usage["actual_cost_usd"],
            "cache_hit_rate": round(
                usage["cached_tokens"] / max(usage["input_tokens"], 1), 4
            ),
        },
    )
    detail = {
        "model": model,
        "task_id": task_id,
        "attempt": attempt_index,
        "success": bool(snapshot.success),
        "scalar_reward": float(snapshot.scalar_reward),
        "interventions": len(events),
        "termination_reason": snapshot.termination_reason,
        "usage": usage,
        "final_inventory": dict(snapshot.privileged_diagnostics.inventory)
        if snapshot.privileged_diagnostics is not None
        else {},
        "transcript_tail": transcript_tail,
    }
    return attempt, detail


async def main_async(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    for model in models:
        started_at = datetime.now(timezone.utc)
        attempts: list[BenchmarkAttempt] = []
        details: list[dict] = []
        for task_id in args.task_id:
            for attempt_index in range(args.attempts):
                print(
                    f"[hermes-bench] {model} :: {task_id} :: attempt {attempt_index}",
                    flush=True,
                )
                attempt, detail = await run_attempt(
                    model, task_id, attempt_index, args
                )
                attempts.append(attempt)
                details.append(detail)
                print(
                    f"    -> success={attempt.success} "
                    f"reward={attempt.scalar_reward:.3f} "
                    f"({attempt.interventions} interventions, "
                    f"{attempt.elapsed_seconds:.0f}s)",
                    flush=True,
                )
        provider, _, name = model.rpartition("/")
        safe_name = name.replace("/", "_").replace(":", "-")
        run = BenchmarkRun(
            run_id=f"hermes-{safe_name}-{started_at.strftime('%Y%m%dT%H%M%SZ')}",
            model=ModelIdentity(name=name, provider=provider or "openrouter"),
            suite="api_microtasks_v1",
            benchmark_split="development",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            repository_commit="unknown",
            generation_config={
                "harness": "hermes-agent",
                "temperature": "provider_default",
            },
            attempts=attempts,
        )
        out_path = output_dir / f"{safe_name}-run.json"
        out_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        (output_dir / f"{safe_name}-details.json").write_text(
            json.dumps(details, indent=2), encoding="utf-8"
        )
        summary = summarize_run(run)
        (output_dir / f"{safe_name}-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"[hermes-bench] wrote {out_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", required=True)
    parser.add_argument("--task-id", action="append", required=True, dest="task_id")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--output-dir", default="benchmark/results/hermes-runs")
    parser.add_argument("--timeout-seconds", type=float, default=150.0)
    parser.add_argument("--max-turns", type=int, default=24)
    parser.add_argument(
        "--reasoning",
        default="low",
        help="Reasoning effort hint (stealth/reasoning models default to max).",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
