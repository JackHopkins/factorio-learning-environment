"""Inference-only Factorio agent loop for an OpenAI-compatible model server.

This is a preflight evaluator, not a training implementation. It deliberately
uses the same ``factorio-envd`` HTTP contract as the Verifiers v1 adapter while
remaining small enough to diagnose model-server and tool-calling problems
before Prime-RL is involved.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from fle.envd.benchmark import get_benchmark_task
from fle.envd.client import EnvironmentClientError, HTTPEnvironmentClient
from fle.envd.curriculum import BUILTIN_TASKS, get_builtin_task
from fle.envd.models import FactorioTaskSpec
from fle.envd.task_builder import render_task_prompt

FACTORIO_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "factorio_observe_factory",
            "description": (
                "Inspect the current Factorio inventory, production statistics, "
                "simulation ticks, scores, and state hash."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "factorio_execute_program",
            "description": (
                "Execute one short Python intervention through the guarded, "
                "auditable FLE program API."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "A short Python program using the public FLE API.",
                    }
                },
                "required": ["code"],
                "additionalProperties": False,
            },
        },
    },
]


def _task_spec(task_id: str) -> FactorioTaskSpec:
    if task_id in BUILTIN_TASKS:
        return get_builtin_task(task_id)
    return get_benchmark_task(task_id).task_spec


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, default=str)


def _bounded_tool_content(value: Any, max_chars: int) -> str:
    content = _json(value)
    if len(content) <= max_chars:
        return content
    removed = len(content) - max_chars
    return content[:max_chars] + f"\n... {removed} response characters truncated"


def _compact_memory(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic short-term memory without asking a second model."""

    observations: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for result in tool_results:
        name = result.get("name")
        raw = result.get("raw")
        if name == "factorio_observe_factory" and isinstance(raw, dict):
            observations.append(
                {
                    key: raw.get(key)
                    for key in (
                        "ticks",
                        "inventory",
                        "production_score",
                        "automated_production_score",
                        "production",
                        "state_hash",
                    )
                }
            )
        elif name == "factorio_execute_program" and isinstance(raw, dict):
            event = raw.get("event") if isinstance(raw.get("event"), dict) else {}
            actions.append(
                {
                    "sequence": event.get("sequence"),
                    "error": event.get("error"),
                    "evaluation_retry": event.get("evaluation_retry"),
                    "executed_tools": event.get("executed_tools"),
                    "result_tail": str(event.get("result") or "")[-800:],
                    "production_score": raw.get("production_score"),
                    "automated_production_score": raw.get("automated_production_score"),
                    "terminal_reason": raw.get("terminal_reason"),
                }
            )
        elif isinstance(raw, dict) and raw.get("error"):
            actions.append({"tool": name, "error": raw.get("error")})
    return {
        "latest_observation": observations[-1] if observations else None,
        "recent_actions": actions[-8:],
    }


def _context_messages(
    base_messages: list[dict[str, Any]],
    history_blocks: list[list[dict[str, Any]]],
    memory: dict[str, Any],
    max_chars: int,
) -> list[dict[str, Any]]:
    """Keep recent assistant/tool pairs within a conservative 8K-token budget."""

    memory_message = {
        "role": "user",
        "content": (
            "Compact runtime memory from earlier turns. Treat engine results as "
            "authoritative and continue from this state:\n" + _json(memory)
        ),
    }
    selected: list[list[dict[str, Any]]] = []
    used = len(_json(base_messages)) + len(_json(memory_message))
    for block in reversed(history_blocks):
        block_size = len(_json(block))
        if selected and used + block_size > max_chars:
            break
        if not selected and used + block_size > max_chars:
            selected.append(block)
            break
        selected.append(block)
        used += block_size
    selected.reverse()
    flattened = [item for block in selected for item in block]
    return [*base_messages, memory_message, *flattened]


async def _resolve_model(client: AsyncOpenAI, requested: str) -> str:
    if requested != "auto":
        return requested
    models = await client.models.list()
    if not models.data:
        raise RuntimeError("model server returned an empty /v1/models response")
    return models.data[0].id


async def _preflight(args: argparse.Namespace) -> dict[str, Any]:
    model_client = AsyncOpenAI(
        base_url=args.model_base_url.rstrip("/") + "/",
        api_key=args.api_key,
        timeout=args.request_timeout,
    )
    try:
        model = await _resolve_model(model_client, args.model)
    finally:
        await model_client.close()

    async with HTTPEnvironmentClient(args.envd_url, args.request_timeout) as env_client:
        health = await env_client.health()

    spec = _task_spec(args.task_id)
    return {
        "mode": "preflight",
        "model": model,
        "model_base_url": args.model_base_url,
        "envd_url": args.envd_url,
        "envd_health": health.model_dump(mode="json"),
        "task_id": spec.task_id,
        "task_fingerprint": spec.fingerprint,
        "prompt_chars": len(render_task_prompt(spec)),
    }


async def _execute_tool(
    env_client: HTTPEnvironmentClient,
    lease_id: str,
    name: str,
    arguments: str,
) -> tuple[Any, str | None]:
    try:
        parsed = json.loads(arguments or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("tool arguments must be a JSON object")
        if name == "factorio_observe_factory":
            return await env_client.observe(lease_id), None
        if name == "factorio_execute_program":
            code = parsed.get("code")
            if not isinstance(code, str) or not code.strip():
                raise ValueError("factorio_execute_program requires non-empty code")
            result = await env_client.execute(lease_id, code)
            return result, result.terminal_reason
        raise ValueError(f"unknown model tool: {name}")
    except (EnvironmentClientError, ValueError, json.JSONDecodeError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}, None


async def _rollout(args: argparse.Namespace) -> dict[str, Any]:
    spec = _task_spec(args.task_id)
    tool_error_retries = int(getattr(args, "tool_error_retries", 0))
    base_turns = args.max_turns or spec.max_interventions
    max_turns = base_turns + tool_error_retries
    model_client = AsyncOpenAI(
        base_url=args.model_base_url.rstrip("/") + "/",
        api_key=args.api_key,
        timeout=args.request_timeout,
    )
    model = await _resolve_model(model_client, args.model)
    base_messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are operating a real Factorio simulation. Use the supplied "
                "tools to inspect, intervene, measure, and debug. Never invent a "
                "tool result. Solve only the stated objective, prefer supplied "
                "inventory over unnecessary gathering, and minimize interventions. "
                "When the goal is complete or no useful action remains, answer "
                "briefly without another tool call. An engine-rejected program "
                f"may be corrected up to {tool_error_retries} extra time(s); "
                "a retry does not roll back any earlier side effects."
            ),
        },
        {"role": "user", "content": render_task_prompt(spec)},
    ]
    history_blocks: list[list[dict[str, Any]]] = []
    all_messages: list[dict[str, Any]] = list(base_messages)
    all_tool_results: list[dict[str, Any]] = []
    lease_id: str | None = None
    snapshot = None
    stop_reason = "max_turns"
    rollout_error = None
    turns: list[dict[str, Any]] = []
    started = time.perf_counter()

    try:
        async with HTTPEnvironmentClient(
            args.envd_url, args.request_timeout
        ) as env_client:
            lease = await env_client.lease(
                spec,
                tool_error_retry_budget=tool_error_retries,
            )
            lease_id = lease.lease_id
            try:
                for turn_index in range(1, max_turns + 1):
                    request_messages = _context_messages(
                        base_messages,
                        history_blocks,
                        _compact_memory(all_tool_results),
                        args.context_budget_chars,
                    )
                    request_started = time.perf_counter()
                    completion_kwargs = {
                        "model": model,
                        "messages": request_messages,
                        "tools": FACTORIO_TOOLS,
                        "tool_choice": "auto",
                        "temperature": args.temperature,
                        "max_tokens": args.max_output_tokens,
                    }
                    if bool(getattr(args, "cache_prompt", False)):
                        completion_kwargs["extra_body"] = {"cache_prompt": True}
                    completion = await model_client.chat.completions.create(
                        **completion_kwargs
                    )
                    elapsed = time.perf_counter() - request_started
                    choice = completion.choices[0]
                    assistant = choice.message.model_dump(
                        mode="json", exclude_none=True
                    )
                    all_messages.append(assistant)
                    block = [assistant]
                    turn_record: dict[str, Any] = {
                        "turn": turn_index,
                        "elapsed_seconds": round(elapsed, 3),
                        "finish_reason": choice.finish_reason,
                        "assistant": assistant,
                        "request_context_chars": len(_json(request_messages)),
                        "usage": (
                            completion.usage.model_dump(mode="json")
                            if completion.usage is not None
                            else None
                        ),
                        "tool_results": [],
                    }
                    tool_calls = choice.message.tool_calls or []
                    if not tool_calls:
                        history_blocks.append(block)
                        turns.append(turn_record)
                        stop_reason = "model_stopped"
                        break

                    terminal_reason = None
                    for tool_call in tool_calls:
                        result, terminal = await _execute_tool(
                            env_client,
                            lease_id,
                            tool_call.function.name,
                            tool_call.function.arguments,
                        )
                        raw = (
                            result.model_dump(mode="json")
                            if hasattr(result, "model_dump")
                            else result
                        )
                        content = _bounded_tool_content(raw, args.max_tool_chars)
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": content,
                        }
                        block.append(tool_message)
                        all_messages.append(tool_message)
                        tool_record = {
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": content,
                            "raw": raw,
                        }
                        all_tool_results.append(tool_record)
                        turn_record["tool_results"].append(tool_record)
                        terminal_reason = terminal_reason or terminal
                    history_blocks.append(block)
                    turns.append(turn_record)
                    if terminal_reason is not None:
                        stop_reason = terminal_reason
                        break
            except Exception as exc:
                stop_reason = "runner_error"
                rollout_error = f"{type(exc).__name__}: {exc}"
            finally:
                snapshot = await env_client.finalize(lease_id)
                await env_client.release(lease_id)
                lease_id = None
    finally:
        if lease_id is not None:
            async with HTTPEnvironmentClient(
                args.envd_url, args.request_timeout
            ) as cleanup_client:
                await cleanup_client.release(lease_id)
        await model_client.close()

    return {
        "mode": "rollout",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "model_base_url": args.model_base_url,
        "envd_url": args.envd_url,
        "task": spec.model_dump(mode="json"),
        "stop_reason": stop_reason,
        "tool_error_retry_budget": tool_error_retries,
        "rollout_error": rollout_error,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "turns": turns,
        "messages": all_messages,
        "compact_memory": _compact_memory(all_tool_results),
        "verification": (
            snapshot.model_dump(mode="json") if snapshot is not None else None
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an inference-only Factorio agent against factorio-envd."
    )
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--model-base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument(
        "--api-key",
        default=(
            os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "local-no-key"
        ),
    )
    parser.add_argument("--model", default="auto")
    parser.add_argument("--task-id", default="milestone_research_automation_v1")
    parser.add_argument("--max-turns", type=int, default=0)
    parser.add_argument(
        "--tool-error-retries",
        type=int,
        default=0,
        help=(
            "Grant this many extra model turns after engine-rejected programs. "
            "Retries are logged and are not transactional."
        ),
    )
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--max-tool-chars", type=int, default=6_000)
    parser.add_argument("--context-budget-chars", type=int, default=18_000)
    parser.add_argument("--request-timeout", type=float, default=1200.0)
    parser.add_argument(
        "--cache-prompt",
        action="store_true",
        help="Send llama.cpp's nonstandard cache_prompt request extension.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


async def _main_async(args: argparse.Namespace) -> int:
    result = await (_preflight(args) if args.preflight else _rollout(args))
    rendered = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered + "\n", encoding="utf-8")
        temporary.replace(args.output)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if args.quiet:
        verification = result.get("verification")
        print(
            json.dumps(
                {
                    "mode": result.get("mode"),
                    "task_id": result.get("task", {}).get(
                        "task_id", result.get("task_id")
                    ),
                    "model": result.get("model"),
                    "stop_reason": result.get("stop_reason"),
                    "rollout_error": result.get("rollout_error"),
                    "turn_count": len(result.get("turns", [])),
                    "success": (
                        verification.get("success")
                        if isinstance(verification, dict)
                        else None
                    ),
                    "scalar_reward": (
                        verification.get("scalar_reward")
                        if isinstance(verification, dict)
                        else None
                    ),
                    "output": str(args.output) if args.output is not None else None,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(rendered)
    verification = result.get("verification")
    if isinstance(verification, dict):
        return 0 if verification.get("success") else 2
    return 0


def main() -> int:
    return asyncio.run(_main_async(_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
