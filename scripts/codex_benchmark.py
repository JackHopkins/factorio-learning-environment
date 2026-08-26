"""Benchmark Factorio tasks through Codex CLI as the agentic harness.

Why this exists: some OpenRouter free models (e.g. thinkingmachines/inkling:free)
are gated to registered agentic harnesses and reject raw API clients with 403.
Routing the same tasks through Codex CLI -- a registered harness -- is the
sanctioned path.

Per attempt:
  1. lease one envd worker for the task;
  2. generate an isolated CODEX_HOME (config.toml: OpenRouter provider +
     our MCP server bound to that lease);
  3. run `codex exec` headless with the task goal as prompt;
  4. finalize the lease, record a BenchmarkAttempt-compatible JSON.

Usage:
  python scripts/codex_benchmark.py --models stealth/ox-alpha,thinkingmachines/inkling:free \
      --task-id micro_craft_iron_gear_v1 --output-dir benchmark/results/codex-smoke
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from fle.envd.benchmark import get_benchmark_task
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
)
from fle.envd.client import HTTPEnvironmentClient
from fle.envd.curriculum import get_builtin_task

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
MCP_SERVER = str(REPO_ROOT / "scripts" / "factorio_codex_mcp.py")
CODEX = r"C:\Users\WillR\AppData\Roaming\npm\codex.cmd"


def _write_codex_home(
    codex_home: Path,
    model: str,
    envd_url: str,
    lease_id: str,
) -> None:
    config = f'''model = "{model}"
model_provider = "openrouter"
model_reasoning_effort = "low"

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPEN_ROUTER_API_KEY"
requires_openai_auth = false
wire_api = "responses"

[mcp_servers.factorio]
command = "{PYTHON.replace(chr(92), '/')}"
args = ["{MCP_SERVER.replace(chr(92), '/')}"]
env = {{ ENVD_URL = "{envd_url}", LEASE_ID = "{lease_id}" }}
'''
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text(config, encoding="utf-8")


def _run_codex(codex_home: Path, prompt: str, timeout_seconds: float) -> str:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home)
    # Scratch working directory: the harness model must never read or write
    # the repository checkout it is being benchmarked by.
    scratch = Path(tempfile.mkdtemp(prefix="codex-scratch-"))
    completed = subprocess.run(
        [
            CODEX,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            str(scratch),
            prompt,
        ],
        cwd=str(scratch),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if completed.returncode != 0:
        output += f"\n[exit code {completed.returncode}]"
    return output


def _task_spec(task_id: str):
    from fle.envd.curriculum import BUILTIN_TASKS

    if task_id in BUILTIN_TASKS:
        return get_builtin_task(task_id)
    return get_benchmark_task(task_id).task_spec


async def run_attempt(
    model: str,
    task_id: str,
    attempt_index: int,
    args: argparse.Namespace,
) -> tuple[BenchmarkAttempt, dict]:
    spec = _task_spec(task_id)
    started_at = datetime.now(timezone.utc)
    async with HTTPEnvironmentClient(args.envd_url) as env_client:
        lease = await env_client.lease(spec)
        lease_id = lease.lease_id
        try:
            codex_home = Path(tempfile.mkdtemp(prefix="codex-home-"))
            _write_codex_home(codex_home, model, args.envd_url, lease_id)
            goal_line = spec.goal.splitlines()[0] if spec.goal else task_id
            prompt = (
                f"Objective: {spec.goal}\n\n"
                "You control a real Factorio factory exclusively through two "
                "MCP tools: `factorio__factorio_observe_factory` and "
                "`factorio__factorio_execute_program`. Do NOT use the shell "
                "or any other tool -- they cannot reach the factory. Call "
                "`factorio__factorio_observe_factory` first. Then intervene "
                "with short Python programs passed as the `code` argument of "
                "`factorio__factorio_execute_program`; available in-factory "
                "names include inspect_inventory, get_entities, nearest, "
                "move_to, harvest_resource, craft_item, place_entity, "
                "insert_item, extract_item, set_entity_recipe. Prefer the "
                "supplied inventory over gathering. When the objective is "
                "met, or no useful action remains, stop calling tools."
            )
            env = dict(os.environ)
            env["CODEX_HOME"] = str(codex_home)
            # Scratch working directory: the harness model must never read
            # or write the repository checkout it is being benchmarked by.
            scratch = Path(tempfile.mkdtemp(prefix="codex-scratch-"))
            wall_start = time.perf_counter()
            try:
                # Popen + explicit tree-kill: subprocess.run's timeout kills
                # only the .cmd wrapper on Windows; the node grandchild keeps
                # the pipes open and communicate() would block forever.
                process = subprocess.Popen(
                    [
                        CODEX,
                        "exec",
                        "--dangerously-bypass-approvals-and-sandbox",
                        "--skip-git-repo-check",
                        "-C",
                        str(scratch),
                        prompt,
                    ],
                    cwd=str(scratch),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                timed_out = False
                try:
                    output, _err = process.communicate(timeout=args.timeout_seconds)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                    )
                    output, _err = process.communicate()
                if timed_out:
                    output += "\n[codex timed out]"
                elif process.returncode != 0:
                    output += f"\n[exit code {process.returncode}]"
            except Exception as exc:  # noqa: BLE001 - recorded in transcript
                output = f"harness error: {type(exc).__name__}: {exc}"
            transcript_tail = output[-4000:]
            elapsed = time.perf_counter() - wall_start
        finally:
            snapshot = await env_client.finalize(lease_id)
            try:
                await env_client.release(lease_id)
            except Exception:
                pass

    events = snapshot.action_events or []
    invalid = sum(1 for event in events if event.error)
    retries = sum(1 for event in events if event.evaluation_retry)
    attempt = BenchmarkAttempt(
        task_id=task_id,
        task_fingerprint=snapshot.task_fingerprint,
        attempt=attempt_index,
        seed=spec.seed,
        success=bool(snapshot.success),
        scalar_reward=float(snapshot.scalar_reward),
        interventions=len(events),
        invalid_interventions=invalid,
        retry_interventions=retries,
        elapsed_seconds=elapsed,
        termination_reason=snapshot.termination_reason,
        metrics={
            "contracts": float(snapshot.rewards.contracts),
            "contract_penalty": float(snapshot.rewards.contract_penalty),
            "contracts_fulfilled": float(
                snapshot.metrics.get("customer_orders_fulfilled", 0.0)
            ),
            "contracts_total": float(
                snapshot.metrics.get("customer_orders_total", 0.0)
            ),
        },
    )
    detail = {
        "model": model,
        "task_id": task_id,
        "attempt": attempt_index,
        "termination_reason": snapshot.termination_reason,
        "success": bool(snapshot.success),
        "scalar_reward": float(snapshot.scalar_reward),
        "interventions": len(events),
        "contracts_fulfilled": float(
            snapshot.metrics.get("customer_orders_fulfilled", 0.0)
        ),
        "contracts_total": float(
            snapshot.metrics.get("customer_orders_total", 0.0)
        ),
        "final_inventory": dict(snapshot.privileged_diagnostics.inventory)
        if snapshot.privileged_diagnostics is not None
        else {},
        "objective_values": [
            {
                "id": e.objective_id,
                "satisfied": e.satisfied,
                "value": e.value,
            }
            for e in (
                snapshot.privileged_diagnostics.objective_evaluations
                if snapshot.privileged_diagnostics is not None
                else []
            )
        ],
        "transcript_tail": transcript_tail,
    }
    return attempt, detail


async def main_async(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    task_ids = list(args.task_id)

    for model in models:
        attempts: list[BenchmarkAttempt] = []
        details: list[dict] = []
        started_at = datetime.now(timezone.utc)
        for task_id in task_ids:
            for attempt_index in range(args.attempts):
                print(f"[codex-bench] {model} :: {task_id} :: attempt {attempt_index}")
                attempt, detail = await run_attempt(
                    model, task_id, attempt_index, args
                )
                attempts.append(attempt)
                details.append(detail)
                print(
                    f"    -> success={attempt.success} "
                    f"reward={attempt.scalar_reward:.3f} "
                    f"({attempt.interventions} interventions)"
                )
        provider, _, name = model.rpartition("/")
        run = BenchmarkRun(
            run_id=f"codex-{name.replace(':', '-')}-{started_at.strftime('%Y%m%dT%H%M%SZ')}",
            model=ModelIdentity(name=name, provider=provider or "openrouter"),
            suite="api_microtasks_v1",
            benchmark_split="development",
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=int(time.time()) - int(started_at.timestamp())),
            repository_commit="unknown",
            generation_config={
                "harness": "codex-cli",
                "temperature": args.temperature,
            },
            attempts=attempts,
        )
        safe_name = name.replace("/", "_").replace(":", "-")
        out_path = output_dir / f"{safe_name}-run.json"
        out_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        (output_dir / f"{safe_name}-details.json").write_text(
            json.dumps(details, indent=2), encoding="utf-8"
        )
        summary = summarize_run(run)
        summary["wall_clock_model"] = model
        (output_dir / f"{safe_name}-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"[codex-bench] wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", required=True, help="comma-separated OpenRouter slugs")
    parser.add_argument("--task-id", action="append", default=[], dest="task_id")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--output-dir", default="benchmark/results/codex-runs")
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--temperature", type=float, default=0.1)
    args = parser.parse_args()
    if not args.task_id:
        raise SystemExit("at least one --task-id is required")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
