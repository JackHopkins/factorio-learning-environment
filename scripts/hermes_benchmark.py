"""Benchmark Factorio tasks through Hermes Agent as the harness.

Each attempt gets an isolated Hermes profile and a fresh envd lease.  The
profile enables only the Factorio MCP server, while the prompt is rendered
from the same public task/action contract used by native agents.  Results are
portable ``BenchmarkRun`` records and keep harness failures auditable without
turning them into model losses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from fle.envd.action_reference import (  # noqa: E402
    ACTION_PROFILE_REFERENCE_ID,
    ACTION_PROFILE_REFERENCE_SHA256,
)
from fle.envd.benchmark import (  # noqa: E402
    benchmark_catalog,
    get_benchmark_task,
)
from fle.envd.benchmark_results import (  # noqa: E402
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
    validate_against_catalog,
)
from fle.envd.client import HTTPEnvironmentClient  # noqa: E402
from fle.envd.curriculum import BUILTIN_TASKS, get_builtin_task  # noqa: E402
from fle.envd.task_builder import render_task_prompt  # noqa: E402

HERMES = (
    os.environ.get("HERMES_BIN")
    or shutil.which("hermes")
    or os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "hermes",
        "hermes-agent",
        "bin",
        "hermes.exe",
    )
)
PYTHON = os.environ.get("FLE_PYTHON", sys.executable)
MCP_SERVER = str(REPO / "scripts" / "factorio_codex_mcp.py")
MCP_SERVER_NAME = "factorio"

_USAGE_KEYS = {
    "input_tokens": ("input_tokens", "prompt_tokens", "input"),
    "output_tokens": ("output_tokens", "completion_tokens", "output"),
    "cached_tokens": (
        "cache_read_input_tokens",
        "cache_read_tokens",
        "cached_tokens",
        "cache_read",
        "cached",
    ),
    "cache_write_tokens": ("cache_write_input_tokens", "cache_write_tokens"),
    "reasoning_tokens": ("reasoning_tokens", "reasoning"),
    "api_calls": ("api_calls", "api_call_count", "requests"),
    "estimated_cost_usd": ("estimated_cost_usd", "estimated_cost", "cost_usd"),
    "actual_cost_usd": ("actual_cost_usd", "actual_cost"),
}

_EMPTY_USAGE = {
    "input_tokens": 0.0,
    "output_tokens": 0.0,
    "cached_tokens": 0.0,
    "cache_write_tokens": 0.0,
    "reasoning_tokens": 0.0,
    "api_calls": 0.0,
    "estimated_cost_usd": 0.0,
    "actual_cost_usd": 0.0,
}


_SPEC_OVERRIDES: dict[str, Any] = {}


def _task_spec(task_id: str):
    if task_id in _SPEC_OVERRIDES:
        return _SPEC_OVERRIDES[task_id]
    if task_id in BUILTIN_TASKS:
        return get_builtin_task(task_id)
    return get_benchmark_task(task_id).task_spec


def build_prompt(spec) -> str:
    """Render the canonical task/action contract for Hermes."""

    canonical = render_task_prompt(spec)
    return (
        "You are being evaluated on one Factorio task. Follow the task and "
        "public action profile below exactly. The only tools available to "
        "you are the two Factorio MCP tools exposed by this harness: "
        "mcp__factorio__factorio_observe_factory and "
        "mcp__factorio__factorio_execute_program. Call observe first. "
        "Pass ordinary short Python in the execute tool's `code` argument, "
        "one intervention per call. Do not use shell, filesystem, browser, "
        "web, imports, reflection, or any other tool. Measure the resulting "
        "factory before stopping and do not claim completion in text.\n\n"
        f"{canonical}\n\n"
        "When the objective is satisfied, stop calling tools."
    )


def _extract_usage(output: str) -> dict[str, float]:
    """Extract usage counters from provider output as a last-resort fallback."""

    totals = dict(_EMPTY_USAGE)
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
                if isinstance(value, (int, float)) and value >= 0:
                    totals[bucket] += float(value)
                    break
    # Do not scan JSON lines a second time: that would double count each
    # provider usage object.
    for line in output.splitlines():
        if "{" in line or "}" in line:
            continue
        for bucket, keys in _USAGE_KEYS.items():
            for key in keys:
                match = re.search(rf"\b{re.escape(key)}\s*[=:]\s*(\d+(?:\.\d+)?)", line)
                if match:
                    totals[bucket] += float(match.group(1))
                    break
    return totals


def _session_usage(profile_home: Path) -> dict[str, float]:
    """Read usage from this attempt's isolated Hermes state database."""

    import sqlite3

    values = dict(_EMPTY_USAGE)
    database = profile_home / "state.db"
    if not database.exists():
        return values
    try:
        conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=5)
        row = conn.execute("""
            SELECT input_tokens, output_tokens, cache_read_tokens,
                   cache_write_tokens, reasoning_tokens, api_call_count,
                   estimated_cost_usd, actual_cost_usd
            FROM sessions ORDER BY last_activity_at DESC LIMIT 1
            """).fetchone()
        conn.close()
    except sqlite3.Error:
        return values
    if row is None:
        return values
    keys = list(values)
    values.update({key: float(value or 0) for key, value in zip(keys, row)})
    return values


def _read_usage_file(path: Path) -> dict[str, float]:
    """Normalize Hermes ``-z --usage-file`` output."""

    if not path.exists():
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(report, dict):
        return {}
    aliases = {
        "input_tokens": ("input_tokens", "prompt_tokens"),
        "output_tokens": ("output_tokens", "completion_tokens"),
        "cached_tokens": ("cache_read_tokens", "cache_read_input_tokens"),
        "cache_write_tokens": ("cache_write_tokens",),
        "reasoning_tokens": ("reasoning_tokens",),
        "api_calls": ("api_calls", "api_call_count"),
        "estimated_cost_usd": ("estimated_cost_usd",),
        "actual_cost_usd": ("actual_cost_usd",),
    }
    values: dict[str, float] = {}
    for destination, candidates in aliases.items():
        for candidate in candidates:
            value = report.get(candidate)
            if isinstance(value, (int, float)) and value >= 0:
                values[destination] = float(value)
                break
    return values


def _merge_usage(profile_home: Path, usage_file: Path, output: str) -> dict[str, float]:
    """Prefer the one-shot report, then the isolated DB, then text parsing."""

    usage = dict(_EMPTY_USAGE)
    usage.update(_session_usage(profile_home))
    report = _read_usage_file(usage_file)
    # Hermes writes a report even when the provider fails.  If present, its
    # zero values are authoritative and must not be replaced by fallback data.
    usage.update(report)
    parsed = _extract_usage(output)
    for key, value in parsed.items():
        if key not in report and usage.get(key, 0) == 0 and value > 0:
            usage[key] = value
    return usage


def _cache_hit_rate(usage: dict[str, float]) -> float:
    cached = max(float(usage.get("cached_tokens", 0)), 0.0)
    uncached = max(float(usage.get("input_tokens", 0)), 0.0)
    written = max(float(usage.get("cache_write_tokens", 0)), 0.0)
    prompt_tokens = uncached + cached + written
    if prompt_tokens <= 0:
        return 0.0
    return round(min(max(cached / prompt_tokens, 0.0), 1.0), 4)


@dataclass(frozen=True)
class HermesInvocation:
    output: str
    returncode: int | None
    failure_category: str | None = None
    failure_message: str | None = None


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """Terminate a Hermes process and all descendants."""

    if os.name == "nt":
        # Hermes may launch Python/Node children. subprocess timeout observes
        # only the executable and can leave descendants holding our pipes open.
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                process.kill()
            except ProcessLookupError:
                pass


def _classify_nonzero_exit(returncode: int | None, output: str) -> tuple[str, str]:
    lower = output.lower()
    if re.search(r"\b(429|quota|rate[ -]?limit|too many requests)\b", lower):
        return "provider_quota", "provider quota or rate limit"
    if re.search(
        r"\b(401|403|408|500|502|503|504|api key|authentication|unauthorized|forbidden|provider error|httpx|connection refused|connection reset|dns|network|ssl|timed out|gateway|service unavailable|internal server error|overloaded)\b",
        lower,
    ):
        return "provider_error", "provider or transport error"
    if re.search(
        r"(tool.?call|function.?call|invalid json|malformed|parse error|schema validation|no final response)",
        lower,
    ):
        return "parser_error", "Hermes/model output could not be parsed"
    return "hermes_exit", f"Hermes exited with status {returncode}"


def _classify_output_failure(output: str) -> tuple[str, str] | None:
    """Recognize failures Hermes may report while still exiting successfully."""

    lower = output.lower()
    if re.search(
        r"api call failed after \d+ retries.*(?:http\s*)?429|"
        r"(?:http\s*)?429.*(?:quota|rate[ -]?limit)|"
        r"free-models-per-day",
        lower,
        flags=re.DOTALL,
    ):
        return "provider_quota", "provider quota or rate limit"
    if re.search(
        r"api call failed after \d+ retries|"
        r"(?:authentication|unauthorized|api key) (?:failed|error|invalid)|"
        r"connection (?:refused|failed)|"
        r"no reply:\s*the model returned empty content",
        lower,
    ):
        return "provider_error", "provider or transport error"
    # Some routes serialize a would-be tool call as ordinary assistant text.
    # Hermes then exits 0 without ever dispatching the MCP tool.
    if re.search(
        r'\{\s*"name"\s*:\s*"tool_call"\s*,\s*"args"\s*:',
        output,
    ):
        return "parser_error", "model tool call was returned as assistant text"
    return None


def _run_hermes(
    profile_home: Path,
    scratch: Path,
    usage_file: Path,
    prompt: str,
    model: str,
    args: argparse.Namespace,
    *,
    resume_latest: bool = False,
    toolsets: str = MCP_SERVER_NAME,
    process_callback: Any = None,
) -> HermesInvocation:
    """Run Hermes one-shot with process-tree cleanup and explicit isolation."""

    env = dict(os.environ)
    env.update(
        {
            "HERMES_HOME": str(profile_home),
            "HERMES_IGNORE_RULES": "1",
            "HERMES_YOLO_MODE": "1",
            "HERMES_ACCEPT_HOOKS": "1",
        }
    )
    command = [
        HERMES,
        "--ignore-rules",
        "--yolo",
    ]
    if resume_latest:
        command.extend(
            ["--resume", "latest", "--in", str(scratch), "--no-restore-cwd"]
        )
    command.extend([
        "-z",
        prompt,
        "--usage-file",
        str(usage_file),
        "--provider",
        "openrouter",
        "-m",
        model,
        "--reasoning",
        str(args.reasoning),
        "--toolsets",
        toolsets,
    ])
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    popen_kwargs: dict[str, Any] = {
        "cwd": str(scratch),
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = creationflags
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(command, **popen_kwargs)
    except OSError as exc:
        message = f"{type(exc).__name__}: {exc}"
        return HermesInvocation(
            output=f"[hermes launch failed] {message}",
            returncode=None,
            failure_category="launch_error",
            failure_message=message,
        )
    if process_callback is not None:
        process_callback(process)

    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=float(args.timeout_seconds))
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        partial_stdout = exc.stdout or ""
        partial_stderr = exc.stderr or ""
        if isinstance(partial_stdout, bytes):
            partial_stdout = partial_stdout.decode("utf-8", errors="replace")
        if isinstance(partial_stderr, bytes):
            partial_stderr = partial_stderr.decode("utf-8", errors="replace")
        _terminate_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                # Do not wait indefinitely on an orphaned descendant that kept
                # an inherited pipe open. Partial output is sufficient for
                # failure classification; closing local handles lets the
                # benchmark continue to the lease finalizer.
                stdout, stderr = partial_stdout, partial_stderr
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except OSError:
                            pass
        if not stdout:
            stdout = partial_stdout
        if not stderr:
            stderr = partial_stderr
    output = (stdout or "") + "\n" + (stderr or "")
    if process_callback is not None:
        process_callback(None)
    if timed_out:
        return HermesInvocation(
            output=output + "\n[hermes timed out]",
            returncode=process.returncode,
            failure_category="timeout",
            failure_message=f"exceeded {args.timeout_seconds:g}s timeout",
        )
    if process.returncode:
        category, message = _classify_nonzero_exit(process.returncode, output)
        return HermesInvocation(
            output=output,
            returncode=process.returncode,
            failure_category=category,
            failure_message=message,
        )
    output_failure = _classify_output_failure(output)
    if output_failure is not None:
        category, message = output_failure
        return HermesInvocation(
            output=output,
            returncode=process.returncode,
            failure_category=category,
            failure_message=message,
        )
    if not output.strip():
        return HermesInvocation(
            output=output,
            returncode=process.returncode,
            failure_category="empty_response",
            failure_message="Hermes produced no response",
        )
    return HermesInvocation(output=output, returncode=process.returncode)


def _write_hermes_profile(
    profile_home: Path,
    scratch: Path,
    envd_url: str,
    lease_id: str,
    trace_file: Path,
    max_turns: int | None,
    terminal_file: Path | None = None,
    api_max_retries: int = 3,
    compression_enabled: bool = False,
) -> None:
    """Write a minimal profile without touching the user's Hermes config."""

    profile_home.mkdir(parents=True, exist_ok=True)
    mcp_env = {
        "ENVD_URL": envd_url,
        "LEASE_ID": lease_id,
        "MCP_TRACE_FILE": str(trace_file),
    }
    if terminal_file is not None:
        mcp_env["MCP_TERMINAL_FILE"] = str(terminal_file)
    config = {
        "model": {
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
        },
        "agent": {
            "max_turns": max_turns,
            "api_max_retries": api_max_retries,
            "disabled_toolsets": [
                "web",
                "terminal",
                "file",
                "browser",
                "skills",
                "memory",
                "delegate",
                "delegation",
                "computer_use",
            ],
        },
        # A named MCP server in an explicit platform list is the supported
        # Hermes allowlist form: no built-in toolsets are expanded.
        "platform_toolsets": {"cli": [MCP_SERVER_NAME]},
        "mcp_servers": {
            MCP_SERVER_NAME: {
                "command": PYTHON,
                "args": [MCP_SERVER],
                "env": mcp_env,
            }
        },
        "terminal": {
            "backend": "local",
            "cwd": str(scratch),
            "home_mode": "profile",
        },
        "memory": {"memory_enabled": False},
        "compression": {
            "enabled": compression_enabled,
            "threshold": 0.50,
        },
    }
    # JSON is valid YAML and avoids a runtime dependency solely for profile
    # creation. Hermes accepts JSON syntax in config.yaml.
    (profile_home / "config.yaml").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    # Isolated profiles need the provider credential: copy the OpenRouter
    # key from the repo .env into the profile .env.
    openrouter_key = os.environ.get("OPEN_ROUTER_API_KEY")
    if openrouter_key:
        (profile_home / ".env").write_text(
            f"OPENROUTER_API_KEY={openrouter_key}\n", encoding="utf-8"
        )


def _effective_max_turns(spec, configured_max_turns: int) -> int | None:
    """Contract sessions use their wall-clock lifecycle, not a turn budget."""
    if spec.customer is not None or spec.adaptive_contract_session:
        return None
    return configured_max_turns


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
            if attempt + 1 < tries:
                await asyncio.sleep(3 * (attempt + 1))
    raise RuntimeError(f"finalize failed after {tries} tries") from last


def _failed_attempt(
    spec,
    task_id: str,
    attempt_index: int,
    elapsed: float,
    category: str,
    message: str,
) -> BenchmarkAttempt:
    return BenchmarkAttempt(
        task_id=task_id,
        task_fingerprint=spec.fingerprint,
        attempt=attempt_index,
        seed=spec.seed,
        success=False,
        scalar_reward=0.0,
        interventions=0,
        elapsed_seconds=max(elapsed, 0.0),
        termination_reason="harness_failure",
        status=(
            "infrastructure_failure"
            if category
            in {"lease_error", "finalize_error", "provider_quota", "provider_error"}
            else "harness_failure"
        ),
        failure_category=category,
        failure_message=message[:1000],
    )


async def run_attempt(
    model: str, task_id: str, attempt_index: int, args: argparse.Namespace
) -> tuple[BenchmarkAttempt, dict[str, Any]]:
    spec = _task_spec(task_id)
    wall_start = time.perf_counter()
    try:
        async with HTTPEnvironmentClient(args.envd_url) as client:
            try:
                lease = await client.lease(spec)
            except Exception as exc:  # noqa: BLE001 - preserve failed attempt
                elapsed = time.perf_counter() - wall_start
                message = f"{type(exc).__name__}: {exc}"
                attempt = _failed_attempt(
                    spec, task_id, attempt_index, elapsed, "lease_error", message
                )
                return attempt, {
                    "model": model,
                    "task_id": task_id,
                    "attempt": attempt_index,
                    "status": attempt.status,
                    "failure_category": attempt.failure_category,
                    "failure_message": message,
                }

            invocation = HermesInvocation(
                output="[harness did not start]",
                returncode=None,
                failure_category="harness_error",
                failure_message="Hermes invocation did not start",
            )
            usage = dict(_EMPTY_USAGE)
            snapshot = None
            finalize_error: Exception | None = None
            try:
                with (
                    tempfile.TemporaryDirectory(
                        prefix="hermes-scratch-"
                    ) as scratch_name,
                    tempfile.TemporaryDirectory(
                        prefix="hermes-profile-"
                    ) as profile_name,
                ):
                    scratch = Path(scratch_name)
                    profile_home = Path(profile_name)
                    usage_file = scratch / "usage.json"
                    trace_file = scratch / "mcp-trace.log"
                    try:
                        _write_hermes_profile(
                            profile_home,
                            scratch,
                            args.envd_url,
                            lease.lease_id,
                            trace_file,
                            _effective_max_turns(spec, args.max_turns),
                        )
                        invocation = _run_hermes(
                            profile_home,
                            scratch,
                            usage_file,
                            build_prompt(spec),
                            model,
                            args,
                        )
                    except Exception as exc:  # noqa: BLE001 - finalize lease below
                        message = f"{type(exc).__name__}: {exc}"
                        invocation = HermesInvocation(
                            output=f"[harness error] {message}",
                            returncode=None,
                            failure_category="harness_error",
                            failure_message=message,
                        )
                    try:
                        usage = _merge_usage(
                            profile_home, usage_file, invocation.output
                        )
                    except Exception as exc:  # noqa: BLE001 - usage is non-scoring
                        message = f"{type(exc).__name__}: {exc}"
                        invocation = HermesInvocation(
                            output=f"{invocation.output}\n[usage error] {message}",
                            returncode=invocation.returncode,
                            failure_category=(
                                invocation.failure_category or "usage_error"
                            ),
                            failure_message=invocation.failure_message or message,
                        )
            except Exception as exc:  # noqa: BLE001 - finalize lease below
                message = f"{type(exc).__name__}: {exc}"
                invocation = HermesInvocation(
                    output=f"[harness error] {message}",
                    returncode=None,
                    failure_category="harness_error",
                    failure_message=message,
                )
            finally:
                try:
                    snapshot = await _finalize_with_retry(client, lease.lease_id)
                except Exception as exc:  # noqa: BLE001 - cannot score no snapshot
                    finalize_error = exc
                    try:
                        await client.release(lease.lease_id)
                    except Exception:
                        pass
            elapsed = time.perf_counter() - wall_start

    except Exception as exc:  # noqa: BLE001 - transport/setup failure
        elapsed = time.perf_counter() - wall_start
        message = f"{type(exc).__name__}: {exc}"
        attempt = _failed_attempt(
            spec, task_id, attempt_index, elapsed, "harness_error", message
        )
        return attempt, {
            "model": model,
            "task_id": task_id,
            "attempt": attempt_index,
            "status": attempt.status,
            "failure_category": attempt.failure_category,
            "failure_message": message,
        }

    if finalize_error is not None or snapshot is None:
        message = (
            f"{type(finalize_error).__name__}: {finalize_error}"
            if finalize_error is not None
            else "no finalize snapshot returned"
        )
        attempt = _failed_attempt(
            spec, task_id, attempt_index, elapsed, "finalize_error", message
        )
        detail = {
            "model": model,
            "task_id": task_id,
            "attempt": attempt_index,
            "status": attempt.status,
            "failure_category": attempt.failure_category,
            "failure_message": message,
            "usage": usage,
            "transcript_tail": invocation.output[-4000:],
        }
        return attempt, detail

    events = snapshot.action_events or []
    status = "completed" if invocation.failure_category is None else "harness_failure"
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
        status=status,
        failure_category=invocation.failure_category,
        failure_message=invocation.failure_message,
        metrics={
            "contracts": float(snapshot.rewards.contracts),
            "contract_penalty": float(snapshot.rewards.contract_penalty),
            "contracts_fulfilled": float(
                snapshot.metrics.get("customer_orders_fulfilled", 0.0)
            ),
            "contracts_total": float(
                snapshot.metrics.get("customer_orders_total", 0.0)
            ),
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cached_tokens": usage["cached_tokens"],
            "cache_write_tokens": usage["cache_write_tokens"],
            "reasoning_tokens": usage["reasoning_tokens"],
            "api_calls": usage["api_calls"],
            "estimated_cost_usd": usage["estimated_cost_usd"],
            "actual_cost_usd": usage["actual_cost_usd"],
            "cache_hit_rate": _cache_hit_rate(usage),
        },
    )
    detail = {
        "model": model,
        "task_id": task_id,
        "attempt": attempt_index,
        "status": status,
        "failure_category": invocation.failure_category,
        "failure_message": invocation.failure_message,
        "success": bool(snapshot.success),
        "scalar_reward": float(snapshot.scalar_reward),
        "interventions": len(events),
        "termination_reason": snapshot.termination_reason,
        "contracts_fulfilled": float(
            snapshot.metrics.get("customer_orders_fulfilled", 0.0)
        ),
        "contracts_total": float(
            snapshot.metrics.get("customer_orders_total", 0.0)
        ),
        "usage": usage,
        "final_inventory": (
            dict(snapshot.privileged_diagnostics.inventory)
            if snapshot.privileged_diagnostics is not None
            else {}
        ),
        "transcript_tail": invocation.output[-4000:],
    }
    return attempt, detail


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        commit = completed.stdout.strip()
        return commit or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _select_task_ids(args: argparse.Namespace) -> list[str]:
    if getattr(args, "spec_file", None):
        # Custom spec mode: the file provides a full FactorioTaskSpec that
        # bypasses catalog selection entirely (e.g. customer contracts).
        from fle.envd.models import FactorioTaskSpec

        data = json.loads(Path(args.spec_file).read_text(encoding="utf-8"))
        # Computed fields serialize but are not accepted back as inputs.
        data.pop("fingerprint", None)
        if isinstance(data.get("customer"), dict):
            data["customer"].pop("commitment", None)
        if isinstance(data.get("perturbations"), dict):
            data["perturbations"].pop("commitment", None)
        spec = FactorioTaskSpec.model_validate(data)
        _SPEC_OVERRIDES[spec.task_id] = spec
        return [spec.task_id]
    catalog = {task.task_id: task for task in benchmark_catalog()}
    requested_status = getattr(args, "status", "ready")
    requested_suite = getattr(args, "suite", "api_microtasks_v1")
    requested_split = getattr(args, "split", "development")
    if args.task_id:
        task_ids = list(dict.fromkeys(args.task_id))
        unknown = sorted(task_id for task_id in task_ids if task_id not in catalog)
        if unknown:
            raise SystemExit(f"unknown benchmark task id(s): {', '.join(unknown)}")
    else:
        task_ids = [
            task.task_id
            for task in catalog.values()
            if task.suite == requested_suite
            and task.benchmark_split == requested_split
            and (requested_status == "all" or task.status == requested_status)
        ]
    selected = [catalog[task_id] for task_id in task_ids]
    if requested_status != "all":
        invalid_status = [
            task.task_id for task in selected if task.status != requested_status
        ]
        if invalid_status:
            raise SystemExit(
                f"task selection contains status-ineligible task(s) for "
                f"--status {requested_status}: {', '.join(invalid_status)}"
            )
    mismatched = [
        task.task_id
        for task in selected
        if task.suite != requested_suite or task.benchmark_split != requested_split
    ]
    if mismatched:
        raise SystemExit(
            f"task selection does not match suite={requested_suite!r}, "
            f"split={requested_split!r}: {', '.join(mismatched)}"
        )
    if not task_ids:
        raise SystemExit(
            f"no tasks selected for suite={requested_suite!r}, "
            f"split={requested_split!r}, status={requested_status!r}"
        )
    return task_ids


def _safe_model_name(model: str) -> str:
    _, _, name = model.rpartition("/")
    return name.replace("/", "_").replace(":", "-")


async def main_async(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise SystemExit("--models must contain at least one non-empty model")
    if args.attempts < 1:
        raise SystemExit("--attempts must be at least 1")
    if args.max_turns < 1:
        raise SystemExit("--max-turns must be at least 1")
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be positive")
    task_ids = _select_task_ids(args)
    effective_max_turns = (
        None
        if any(
            _effective_max_turns(_task_spec(task_id), args.max_turns) is None
            for task_id in task_ids
        )
        else args.max_turns
    )
    suite = getattr(args, "suite", "api_microtasks_v1")
    split = getattr(args, "split", "development")
    status = getattr(args, "status", "ready")
    print(
        f"[hermes-bench] {len(task_ids)} {suite} tasks "
        f"(split={split}, status={status})",
        flush=True,
    )

    for model in models:
        started_at = datetime.now(timezone.utc)
        attempts: list[BenchmarkAttempt] = []
        details: list[dict[str, Any]] = []
        for task_id in task_ids:
            for attempt_index in range(args.attempts):
                print(
                    f"[hermes-bench] {model} :: {task_id} :: attempt {attempt_index}",
                    flush=True,
                )
                attempt, detail = await run_attempt(model, task_id, attempt_index, args)
                attempts.append(attempt)
                details.append(detail)
                # Persist incrementally so harness failures are never lost.
                (output_dir / f"{_safe_model_name(model)}-details.json").write_text(
                    json.dumps(details, indent=2), encoding="utf-8"
                )
                print(
                    f"    -> status={attempt.status} success={attempt.success} "
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
            suite=suite,
            benchmark_split=split,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            repository_commit=_git_commit(),
            environment={
                "os": platform.platform(),
                "python": platform.python_version(),
                "harness_binary": str(HERMES),
                "envd_url": args.envd_url,
                "selection_status": status,
            },
            generation_config={
                "harness": "hermes-agent",
                "harness_mode": "oneshot",
                "provider": "openrouter",
                "reasoning": args.reasoning,
                "max_turns": effective_max_turns,
                "timeout_seconds": args.timeout_seconds,
                "attempts_per_task": args.attempts,
                "toolsets": [MCP_SERVER_NAME],
                "web_search_enabled": False,
                "action_reference_id": ACTION_PROFILE_REFERENCE_ID,
                "action_reference_sha256": ACTION_PROFILE_REFERENCE_SHA256,
            },
            attempts=attempts,
        )
        # Custom-spec runs (e.g. customer contracts) are not catalog members.
        if not getattr(args, "spec_file", None):
            errors = validate_against_catalog(run)
            if errors:
                raise RuntimeError(
                    "generated benchmark run failed validation:\n" + "\n".join(errors)
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
    parser.add_argument("--task-id", action="append", default=[], dest="task_id")
    parser.add_argument(
        "--spec-file",
        default=None,
        help=(
            "Path to a serialized FactorioTaskSpec. Bypasses catalog "
            "selection and runs this single spec (e.g. customer contracts)."
        ),
    )
    parser.add_argument("--suite", default="api_microtasks_v1")
    parser.add_argument(
        "--split",
        choices=["development", "validation", "test"],
        default="development",
    )
    parser.add_argument(
        "--status",
        choices=["ready", "calibration_required", "spec_only", "planned", "all"],
        default="ready",
    )
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--output-dir", default="benchmark/results/hermes-runs")
    parser.add_argument("--timeout-seconds", type=float, default=150.0)
    parser.add_argument("--max-turns", type=int, default=24)
    parser.add_argument(
        "--reasoning",
        default="low",
        choices=["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"],
        help="Reasoning effort hint (stealth/reasoning models default to max).",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
