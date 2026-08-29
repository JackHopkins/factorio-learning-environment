"""Persistent adaptive contract benchmark runner (section 15).

One backend lease and one agent conversation span the whole session.  Each
epoch: capture context, generate a bounded candidate pool, select with seeded
randomness, commit, hand the order to the agent, finalize, map the outcome,
update the rating when ratable, persist atomically, then evaluate the
stopping rule.

Clock discipline: simulation time is owned by the backend; model, tool, and
wall-clock accounting live here.  Wall-clock limits are a generous fail-safe
against hung providers -- an interruption fired while the simulation is
paused is recorded as an infrastructure error, never an order loss.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Protocol

from dotenv import load_dotenv

load_dotenv()
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from fle.envd.client import HTTPEnvironmentClient  # noqa: E402
from fle.envd.contract_features import ProductCatalog, StaticRecipeDataSource  # noqa: E402
from fle.envd.contract_generator import (  # noqa: E402
    DEFAULT_TEMPLATE_BANK,
    MIXTURE_WEIGHTS,
    ContractCandidate,
    build_epoch_spec,
    generate_candidates,
)
from fle.envd.contract_rating import (  # noqa: E402
    CalibratedDifficultyModel,
    TrueskillContractRater,
    UncalibratedDifficultyModel,
    map_outcome,
    performance_score,
)
from fle.envd.contract_selector import (  # noqa: E402
    ContractSelector,
    SelectionHistory,
)
from fle.envd.models import (  # noqa: E402
    ADAPTIVE_BENCHMARK_VERSION,
    CapabilityRating,
    CalibrationManifest,
    ContractEpochSpec,
    FactorioTaskSpec,
    ParticipantIdentity,
    ProductDemandSpec,
    SelectorWeights,
    SessionStoppingConfig,
)
from fle.envd.benchmark_results import (  # noqa: E402
    AdaptiveEpochRecord,
    AdaptiveSessionRecord,
    validate_adaptive_session,
)
from fle.envd.action_reference import ACTION_PROFILE_REFERENCE  # noqa: E402
from fle.envd.capability_graph import (  # noqa: E402
    build_capability_graph,
    compare_capability_snapshots,
)
from fle.envd.capability_certificates import ledger_from_epochs  # noqa: E402
from fle.envd.contract_policy import EvidenceDrivenCustomerPolicy  # noqa: E402
from fle.envd.knowledge import (  # noqa: E402
    ApiReference,
    GameDataReference,
    load_game_data,
)
from scripts import hermes_benchmark as hermes_harness  # noqa: E402
from scripts.factorio_codex_mcp import (  # noqa: E402
    ALL_TOOLS as FACTORIO_MCP_TOOLS,
    MEMORY_TOOL_NAMES,
    _bounded_json_text,
    tools_for_profile,
)

RUNNER_VERSION = "adaptive-runner-v3"
ATOMIC_JSON_MAX_REPLACE_ATTEMPTS = 5
ATOMIC_JSON_REPLACE_BACKOFF_SECONDS = 0.05
ATOMIC_JSON_REPLACE_BACKOFF_MAX_SECONDS = 0.5

# Keep the operating objective useful to the agent without exposing benchmark
# internals such as selection, rating, or qualification policy.
FACTORY_ROLE_OBJECTIVE = (
    "Operate and expand an automated Factorio factory capable of reliably "
    "supplying changing customer demand. Favor durable automation, balanced "
    "throughput, and reusable infrastructure. End-to-end throughput is "
    "tested without agent actions. Customer depots credit only "
    "inserter-fed factory output; direct hand delivery is audit-only."
)

FREEPLAY_TASK_ID = "adaptive_contract_session_v1"
CUSTOMER_DEPOT_LOCATION = (
    "the persistent customer depot is a pre-existing row of immutable sink "
    "chests six tiles west and ten tiles north of your starting character "
    "(relative anchor -6, -10; Factorio entity centers may use half-tile "
    "coordinates). The authoritative chest IDs and exact positions are listed "
    "under customer_depots in factorio_observe_factory; player-built chests "
    "never count"
)


def freeplay_task_spec() -> FactorioTaskSpec:
    """The single persistent lease task for one adaptive session."""
    from fle.envd.models import VerifierSpec

    return FactorioTaskSpec(
        task_id=FREEPLAY_TASK_ID,
        goal=(
            "Fulfil each customer order as it arrives. The factory persists "
            "between orders; infrastructure you build remains available."
        ),
        task_family="open_play",
        adaptive_contract_session=True,
        objectives=[],
        verifier=VerifierSpec(implementation="objective_engine_v1"),
        max_interventions=None,
        holdout_seconds=0,
    )


# ---------------------------------------------------------------------------
# Agent session protocol and harnesses
# ---------------------------------------------------------------------------


class AgentEpochTelemetry:
    def __init__(
        self,
        *,
        model_seconds: float = 0.0,
        tool_seconds: float = 0.0,
        turns: int = 0,
        transport_errors: int = 0,
        prompt_chars: int = 0,
        response_chars: int = 0,
        invocations: int = 0,
        continuation_reasons: list[str] | None = None,
        provider_step_finish_reasons: list[str] | None = None,
        stop_reason: str | None = None,
        failure_category: str | None = None,
    ):
        self.model_seconds = model_seconds
        self.tool_seconds = tool_seconds
        self.turns = turns
        self.transport_errors = transport_errors
        self.prompt_chars = prompt_chars
        self.response_chars = response_chars
        # ``invocations`` counts provider processes, not model/tool turns.  It
        # is useful for diagnosing context-limit continuations without making
        # those continuations an evaluation budget.
        self.invocations = invocations
        self.continuation_reasons = list(continuation_reasons or [])
        self.provider_step_finish_reasons = list(
            provider_step_finish_reasons or []
        )
        self.stop_reason = stop_reason
        self.failure_category = failure_category

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_seconds": self.model_seconds,
            "tool_seconds": self.tool_seconds,
            "turns": self.turns,
            "transport_errors": self.transport_errors,
            "prompt_chars": self.prompt_chars,
            "response_chars": self.response_chars,
            "invocations": self.invocations,
            "continuation_reasons": list(self.continuation_reasons),
            "provider_step_finish_reasons": list(
                self.provider_step_finish_reasons
            ),
            "stop_reason": self.stop_reason,
            "failure_category": self.failure_category,
        }


class AgentSession(Protocol):
    async def start(self, system_prompt: str) -> None: ...

    async def run_epoch(self, order_prompt: str) -> AgentEpochTelemetry: ...

    async def close(self) -> None: ...


class ScriptedAgentSession:
    """Deterministic harness for tests: replays scripted responses."""

    harness_version = "scripted-v1"
    SYSTEM_PROMPT = "scripted-agent-v1"

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.system_prompt: str | None = None
        self.closed = False

    async def start(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt

    async def run_epoch(self, order_prompt: str) -> AgentEpochTelemetry:
        self.prompts.append(order_prompt)
        response = (
            self.responses[len(self.prompts) - 1]
            if len(self.prompts) <= len(self.responses)
            else ""
        )
        return AgentEpochTelemetry(
            model_seconds=0.001,
            tool_seconds=0.0,
            turns=1,
            response_chars=len(response),
        )

    async def close(self) -> None:
        self.closed = True


def _native_callable_tool_manifest(
    *, memory_enabled: bool = False
) -> list[dict[str, Any]]:
    """Translate the shared MCP reference tools to OpenAI function schemas."""

    names = {
        "factorio_check_throughput",
        "factorio_search_reference",
        "factorio_read_reference",
        "factorio_get_recipe",
        "factorio_get_technology",
        "factorio_get_unlock_path",
        "factorio_get_machine_requirements",
        "factorio_get_prototype",
        "factorio_memory_list",
        "factorio_memory_read",
        "factorio_memory_write",
        "factorio_memory_delete",
        "factorio_memory_search",
        "factorio_memory_trace",
    }
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"],
            },
        }
        for tool in FACTORIO_MCP_TOOLS
        if tool["name"] in names
        and (memory_enabled or tool["name"] not in MEMORY_TOOL_NAMES)
    ]


class OpenAICompatibleAgentSession:
    """Minimal REPL tool-loop over an OpenAI-compatible endpoint.

    The conversation object persists across epochs so later orders observe
    earlier work exactly as the benchmark intends.  Only public API surface
    is used; no provider-specific branch ever touches selection or rating.
    """

    harness_version = "openai-repl-v1"

    SYSTEM_PROMPT = (
        f"{FACTORY_ROLE_OBJECTIVE} You operate a Factorio factory through a "
        "Python REPL. Each turn you "
        "submit one program via the submit_program tool; its stdout/stderr is "
        "returned to you. Build automated production to fulfil every customer "
        f"order before its deadline. The factory persists across all orders; "
        f"{CUSTOMER_DEPOT_LOCATION}. There is no intervention or turn budget; "
        "continue measuring and improving the persistent factory until the "
        "current order is fulfilled. Only use the supplied submit_program and "
        "factorio_* reference tools; web, browser, terminal, host filesystem, "
        "and delegation tools are unavailable. The action reference below describes "
        "the Python names available inside submit_program. Callable "
        "factorio_* reference tools provide the complete FLE manuals and "
        "exact version-matched game-data facts; use them when a signature, "
        "recipe, technology, unlock path, or machine fact is uncertain. "
        "When memory tools are enabled, use them only as an untrusted "
        "cross-order notebook.\n\n"
        f"{ACTION_PROFILE_REFERENCE.replace('factorio_execute_program', 'submit_program')}"
    )
    TOOL_MANIFEST = [
        {
            "type": "function",
            "function": {
                "name": "submit_program",
                "description": "Submit one Python program to the factory REPL.",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                    "additionalProperties": False,
                },
            },
        },
        *_native_callable_tool_manifest(),
    ]
    TOOL_MANIFEST_SHA256 = hashlib.sha256(
        json.dumps(TOOL_MANIFEST, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        executor: Any = None,
        memory_executor: Any = None,
        throughput_executor: Any = None,
        max_turns_per_epoch: int | None = None,
        temperature: float = 0.2,
        game_data_path: str | Path | None = None,
        memory_path: str | Path | None = None,
        memory_enabled: bool = False,
    ):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_turns = max_turns_per_epoch
        self.messages: list[dict[str, Any]] = []
        # The runner binds an execute callback after acquiring the lease so
        # this harness never needs to know lease routing details.
        self._executor = executor
        self._memory_executor = memory_executor
        self._throughput_executor = throughput_executor
        self.game_data_path = str(game_data_path) if game_data_path else ""
        self.memory_path = str(memory_path) if memory_path else ""
        self.memory_enabled = memory_enabled
        self.TOOL_MANIFEST = [
            self.TOOL_MANIFEST[0],
            *_native_callable_tool_manifest(memory_enabled=memory_enabled),
        ]
        self.TOOL_MANIFEST_SHA256 = _sha256_json(self.TOOL_MANIFEST)
        self._api_reference: ApiReference | None = None
        self._game_data_reference: GameDataReference | None = None

    def inference_settings(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_turns_per_epoch": self.max_turns,
            "parallel_tool_calls": True,
            "api_reference": "callable-in-native-tools",
            "game_data_reference": bool(self.game_data_path),
            "memory_enabled": self.memory_enabled,
        }

    def bind_executor(self, executor: Any) -> None:
        self._executor = executor

    def bind_memory_executor(self, executor: Any) -> None:
        self._memory_executor = executor

    async def start(self, system_prompt: str | None = None) -> None:
        self.messages.append(
            {"role": "system", "content": system_prompt or self.SYSTEM_PROMPT}
        )

    async def _execute(
        self,
        code: str,
        request_id: str,
    ) -> tuple[str, str | None]:
        if self._executor is None:
            return "error: no environment bound", None
        result = await self._executor(code, request_id=request_id)
        terminal_reason = getattr(result, "terminal_reason", None)
        if terminal_reason is None and hasattr(result, "events"):
            terminal_reason = next(
                (
                    event.kind
                    for event in result.events
                    if event.kind in {"contract_fulfilled", "contract_expired"}
                ),
                None,
            )
        if hasattr(result, "event"):
            # Keep the model-facing output compatible with the original
            # session while retaining terminal metadata for the harness.
            text = str(result.event.result)
        elif isinstance(result, str):
            text = result
        else:
            text = str(result)
        return text[:8000], terminal_reason

    def _reference_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Resolve a read-only reference locally for the native provider loop."""

        if self._api_reference is None:
            self._api_reference = ApiReference()
        if self._game_data_reference is None:
            self._game_data_reference, _ = load_game_data(self.game_data_path or None)
        api = self._api_reference
        game = self._game_data_reference
        if name == "factorio_search_reference":
            query = str(arguments.get("query", ""))
            kinds = arguments.get("kinds")
            if kinds is not None and not isinstance(kinds, list):
                raise ValueError("kinds must be a list")
            requested = {str(kind).lower() for kind in (kinds or [])}
            api_results = []
            if not requested or "api" in requested:
                api_results = api.search(query, kinds={"api"}, limit=100)["results"]
                for result in api_results:
                    result["canonical_id"] = result.pop("document_id")
            game_results = game.search(
                query,
                kinds=requested - {"api"} if requested else None,
                limit=100,
            )["results"]
            results = sorted(
                api_results + game_results,
                key=lambda item: (item.get("kind", ""), item.get("canonical_id", "")),
            )
            from fle.envd.knowledge import _paginate

            page, next_cursor = _paginate(
                results,
                int(arguments.get("limit", 20)),
                arguments.get("cursor"),
            )
            return {
                "schema_version": "knowledge-reference-v1",
                "api_reference_id": "fle-api-reference-v1",
                "api_reference_sha256": api.reference_hash,
                "game_data_reference_id": game.reference_id,
                "game_data_reference_sha256": game.reference_hash,
                "query": query,
                "results": page,
                "next_cursor": next_cursor,
            }
        if name == "factorio_read_reference":
            document_id = str(arguments["document_id"])
            if document_id.startswith("api/") or document_id.startswith("api:") or not any(
                document_id.startswith(prefix)
                for prefix in ("recipe:", "technology:", "prototype:")
            ):
                return api.read(
                    document_id,
                    section=(
                        str(arguments["section"])
                        if arguments.get("section") is not None
                        else None
                    ),
                    cursor=arguments.get("cursor"),
                    max_chars=int(arguments.get("max_chars", 12000)),
                )
            kind, _, identifier = document_id.partition(":")
            if kind == "recipe":
                return game.recipe(identifier)
            if kind == "technology":
                return game.technology(identifier)
            if kind == "prototype":
                return game.prototype(identifier)
            raise KeyError(f"unknown reference document: {document_id}")
        if name == "factorio_get_recipe":
            return game.recipe(str(arguments["item_or_recipe_id"]))
        if name == "factorio_get_technology":
            return game.technology(str(arguments["technology_id"]))
        if name == "factorio_get_unlock_path":
            return game.unlock_path(str(arguments["item_or_recipe_id"]))
        if name == "factorio_get_machine_requirements":
            return game.machine_requirements(str(arguments["recipe_id"]))
        if name == "factorio_get_prototype":
            return game.prototype(str(arguments["prototype_id"]))
        raise KeyError(f"unknown reference tool: {name}")

    async def _auxiliary_call(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> tuple[str, str | None]:
        if name == "factorio_check_throughput":
            if self._throughput_executor is None:
                raise RuntimeError("native throughput executor is not bound")
            result = await self._throughput_executor(request_id=request_id)
            if hasattr(result, "model_dump"):
                result = result.model_dump(mode="json")
            terminal = (
                f"contract_{result.get('contract_status')}"
                if isinstance(result, dict)
                and result.get("contract_status") != "open"
                else None
            )
            return _bounded_json_text(result), terminal
        if name.startswith("factorio_memory_"):
            if not self.memory_enabled:
                raise RuntimeError(
                    "session memory is disabled for this evaluation profile; "
                    "rerun with --memory-profile stateful to enable it"
                )
            if self._memory_executor is None:
                raise RuntimeError("native memory executor is not bound")
            result = await self._memory_executor(name, arguments)
            if hasattr(result, "model_dump"):
                result = result.model_dump(mode="json")
            if not isinstance(result, dict):
                result = {"result": result}
            return _bounded_json_text(result), None
        return _bounded_json_text(self._reference_call(name, arguments)), None

    @staticmethod
    def _synthetic_tool_result(
        call_id: str, terminal_reason: str
    ) -> tuple[dict[str, Any], str]:
        """Return a protocol-valid result for a call skipped after termination."""

        message = (
            "error: tool call skipped because the environment reached terminal "
            f"state {terminal_reason!r} after an earlier call"
        )
        return (
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": message,
            },
            message,
        )

    async def run_epoch(self, order_prompt: str) -> AgentEpochTelemetry:
        started = time.perf_counter()
        telemetry = AgentEpochTelemetry()
        self.messages.append({"role": "user", "content": order_prompt})
        tools = self.TOOL_MANIFEST
        try:
            turn = 0
            while self.max_turns is None or turn < self.max_turns:
                turn += 1
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=tools,
                    parallel_tool_calls=True,
                    temperature=self.temperature,
                )
                choice = response.choices[0]
                message = choice.message
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments,
                                },
                            }
                            for call in (message.tool_calls or [])
                        ]
                        or None,
                    }
                )
                if not message.tool_calls:
                    break
                telemetry.turns += 1
                finished_epoch = False
                terminal_reason = None
                for call in message.tool_calls:
                    if terminal_reason is not None:
                        tool_message, output = self._synthetic_tool_result(
                            call.id,
                            terminal_reason,
                        )
                        self.messages.append(tool_message)
                        continue

                    tool_started = time.perf_counter()
                    try:
                        try:
                            arguments = json.loads(call.function.arguments or "{}")
                            if not isinstance(arguments, dict):
                                raise ValueError("tool arguments must be a JSON object")
                            if call.function.name == "submit_program":
                                code = arguments.get("code", "")
                                if not isinstance(code, str) or not code.strip():
                                    raise ValueError(
                                        "submit_program requires non-empty code"
                                    )
                                output, terminal = await self._execute(
                                    code,
                                    request_id=call.id,
                                )
                            elif call.function.name.startswith("factorio_"):
                                output, terminal = await self._auxiliary_call(
                                    call.function.name,
                                    arguments,
                                    request_id=call.id,
                                )
                            else:
                                raise ValueError(
                                    f"unknown tool {call.function.name}"
                                )
                        except (ValueError, TypeError, json.JSONDecodeError) as exc:
                            output = f"error: {type(exc).__name__}: {exc}"
                            terminal = None
                        except Exception as exc:  # noqa: BLE001 - return a tool result
                            # Every requested call needs a matching tool message;
                            # callers can decide whether to retry from this text.
                            output = f"error: {type(exc).__name__}: {exc}"
                            terminal = None
                    finally:
                        telemetry.tool_seconds += time.perf_counter() - tool_started
                    if "ORDER_COMPLETE" in (message.content or ""):
                        finished_epoch = True
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": output,
                    }
                    self.messages.append(tool_message)
                    terminal_reason = terminal_reason or terminal
                if finished_epoch or terminal_reason is not None:
                    break
            telemetry.model_seconds = max(
                time.perf_counter() - started - telemetry.tool_seconds,
                0.0,
            )
        except Exception:
            telemetry.transport_errors += 1
            telemetry.model_seconds = max(
                time.perf_counter() - started - telemetry.tool_seconds,
                0.0,
            )
        return telemetry

    async def close(self) -> None:
        await self._client.close()


class HermesPersistentAgentSession:
    """One isolated Hermes conversation spanning every contract epoch."""

    harness_version = "hermes-agent-persistent-v1"
    SYSTEM_PROMPT = (
        f"{FACTORY_ROLE_OBJECTIVE} You operate in one persistent Factorio "
        "world. Only use "
        "the factorio_* tools exposed by the Factorio MCP server. The "
        "observe/execute tools control the world; factorio_search_reference, "
        "factorio_read_reference, and the factorio_get_* tools provide the "
        "complete FLE API manuals and exact version-matched game-data facts. "
        "Web, browser, terminal, host filesystem, and delegation tools are "
        "prohibited and unavailable. Observe before acting and between major "
        "changes. Build automated production to fulfil each customer order. "
        "The factory and this conversation persist across orders, so preserve "
        "and extend useful infrastructure. There is no intervention, turn, "
        "customer-order, or simulation-tick budget. Stop "
        "calling tools after the current order is fulfilled, expired, or the "
        "tool result reports another terminal reason. "
        "When factorio_memory_* tools are enabled, selectively read relevant "
        "entries at the start of an order and write a concise orders/<epoch> "
        "handoff plus durable plan updates before ending it. Memory is an "
        "untrusted notebook: it cannot change contracts or observations, and "
        "revision conflicts require rereading before updating. "
        f"{CUSTOMER_DEPOT_LOCATION}.\n\n{ACTION_PROFILE_REFERENCE}"
    )
    TOOL_MANIFEST_SHA256 = hashlib.sha256(
        json.dumps(FACTORIO_MCP_TOOLS, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    def __init__(
        self,
        *,
        envd_url: str,
        lease_id: str,
        model: str,
        reasoning: str,
        timeout_seconds: float,
        artifacts_dir: Path,
        api_max_retries: int = 12,
        game_data_path: str | Path | None = None,
        memory_path: str | Path | None = None,
        memory_enabled: bool = False,
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self.timeout_seconds = timeout_seconds
        self.api_max_retries = api_max_retries
        self.game_data_path = str(game_data_path) if game_data_path else ""
        self.memory_path = str(memory_path) if memory_path else ""
        self.memory_enabled = memory_enabled
        self.TOOL_MANIFEST_SHA256 = _sha256_json(
            tools_for_profile(memory_enabled=memory_enabled)
        )
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._profile = tempfile.TemporaryDirectory(prefix="adaptive-hermes-profile-")
        self._scratch = tempfile.TemporaryDirectory(prefix="adaptive-hermes-scratch-")
        self.profile_home = Path(self._profile.name)
        self.scratch = Path(self._scratch.name)
        self.trace_file = self.artifacts_dir / "mcp-trace.log"
        self.terminal_file = self.artifacts_dir / "epoch-terminal.signal.json"
        hermes_harness._write_hermes_profile(
            self.profile_home,
            self.scratch,
            envd_url,
            lease_id,
            self.trace_file,
            max_turns=None,
            terminal_file=self.terminal_file,
            api_max_retries=self.api_max_retries,
            compression_enabled=True,
            game_data_path=self.game_data_path or None,
            memory_path=self.memory_path or None,
            memory_enabled=self.memory_enabled,
        )
        self.system_prompt = self.SYSTEM_PROMPT
        self.invocation_count = 0
        self._trace_call_count = 0
        self._active_process: Any = None

    def _set_active_process(self, process: Any) -> None:
        self._active_process = process

    def inference_settings(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": "openrouter",
            "reasoning": self.reasoning,
            "max_turns": None,
            "toolsets": [hermes_harness.MCP_SERVER_NAME],
            "persistent_session": True,
            "api_max_retries": self.api_max_retries,
            "compression": {"enabled": True, "threshold": 0.50},
            "api_reference": "callable-in-mcp",
            "game_data_reference": bool(self.game_data_path),
            "memory_enabled": self.memory_enabled,
        }

    async def start(self, system_prompt: str | None = None) -> None:
        self.system_prompt = system_prompt or self.SYSTEM_PROMPT

    async def run_epoch(self, order_prompt: str) -> AgentEpochTelemetry:
        epoch_number = self.invocation_count + 1
        prompt = (
            f"{self.system_prompt}\n\n{order_prompt}"
            if self.invocation_count == 0
            else (
                "Continue the same persistent benchmark session. A new "
                f"customer order is now active.\n\n{order_prompt}"
            )
        )
        usage_file = self.artifacts_dir / f"epoch-{epoch_number:04d}.usage.json"
        self.terminal_file.unlink(missing_ok=True)
        args = SimpleNamespace(
            timeout_seconds=self.timeout_seconds,
            reasoning=self.reasoning,
        )
        started = time.perf_counter()
        invocation_task = asyncio.create_task(
            asyncio.to_thread(
                hermes_harness._run_hermes,
                self.profile_home,
                self.scratch,
                usage_file,
                prompt,
                self.model,
                args,
                resume_latest=self.invocation_count > 0,
                toolsets=hermes_harness.MCP_SERVER_NAME,
                process_callback=self._set_active_process,
            )
        )
        terminal_observed = False
        while not invocation_task.done():
            await asyncio.sleep(0.25)
            if self.terminal_file.exists():
                terminal_observed = True
                terminal_payload = self.terminal_file.read_text(
                    encoding="utf-8", errors="replace"
                )
                (
                    self.artifacts_dir / f"epoch-{epoch_number:04d}.terminal.json"
                ).write_text(terminal_payload, encoding="utf-8")
                # Give the MCP response a moment to flush, then end this
                # Hermes invocation. The persistent session remains resumable.
                await asyncio.sleep(0.5)
                if (
                    self._active_process is not None
                    and self._active_process.poll() is None
                ):
                    hermes_harness._terminate_process_tree(self._active_process)
                break
        invocation = await invocation_task
        elapsed = time.perf_counter() - started
        self.invocation_count += 1
        (self.artifacts_dir / f"epoch-{epoch_number:04d}.hermes.log").write_text(
            invocation.output,
            encoding="utf-8",
        )
        trace_text = (
            self.trace_file.read_text(encoding="utf-8", errors="replace")
            if self.trace_file.exists()
            else ""
        )
        trace_call_count = trace_text.count("tools/call")
        epoch_tool_calls = max(trace_call_count - self._trace_call_count, 0)
        self._trace_call_count = trace_call_count
        return AgentEpochTelemetry(
            model_seconds=elapsed,
            tool_seconds=0.0,
            turns=epoch_tool_calls,
            transport_errors=int(
                invocation.failure_category is not None and not terminal_observed
            ),
            prompt_chars=len(prompt),
            response_chars=len(invocation.output),
        )

    async def close(self) -> None:
        if self._active_process is not None and self._active_process.poll() is None:
            hermes_harness._terminate_process_tree(self._active_process)
        self._scratch.cleanup()
        self._profile.cleanup()


def _parse_opencode_jsonl(output: str) -> tuple[list[dict[str, Any]], int]:
    """Parse JSON events from OpenCode's line-oriented output.

    OpenCode can prefix or suffix its JSON stream with human-readable process
    diagnostics. Those lines are retained in the raw artifact but are not
    treated as protocol events. The malformed count is included in the audit
    record so a provider stream that is otherwise empty is diagnosable.
    """

    events: list[dict[str, Any]] = []
    malformed = 0
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(event, dict):
            events.append(event)
    return events, malformed


def _event_field(event: dict[str, Any], field: str) -> Any:
    """Read a field from the top-level or common OpenCode event envelopes."""

    if field in event:
        return event[field]
    for envelope_name in ("part", "properties", "metadata", "data"):
        envelope = event.get(envelope_name)
        if isinstance(envelope, dict) and field in envelope:
            return envelope[field]
    return None


def _parse_opencode_session_ids(output: str) -> list[str]:
    events, _ = _parse_opencode_jsonl(output)
    session_ids: list[str] = []
    for event in events:
        for field in ("sessionID", "sessionId", "session_id"):
            value = _event_field(event, field)
            if isinstance(value, str) and value and value not in session_ids:
                session_ids.append(value)
                break
    return session_ids


def _parse_opencode_step_finish_reasons(output: str) -> list[str]:
    """Return normalized provider reasons from ``step_finish`` events."""

    events, _ = _parse_opencode_jsonl(output)
    reasons: list[str] = []
    for event in events:
        event_type = str(event.get("type", "")).lower()
        if event_type != "step_finish":
            continue
        reason = _event_field(event, "reason")
        if reason is None:
            continue
        normalized = str(reason).strip().lower()
        if normalized:
            reasons.append(normalized)
    return reasons


class OpenCodePersistentAgentSession:
    """One isolated OpenCode session spanning every contract epoch."""

    harness_version = "opencode-persistent-v1"
    SYSTEM_PROMPT = HermesPersistentAgentSession.SYSTEM_PROMPT
    TOOL_MANIFEST_SHA256 = HermesPersistentAgentSession.TOOL_MANIFEST_SHA256

    def __init__(
        self,
        *,
        envd_url: str,
        lease_id: str,
        model: str,
        reasoning: str | None,
        timeout_seconds: float,
        artifacts_dir: Path,
        command: str | None = None,
        game_data_path: str | Path | None = None,
        memory_path: str | Path | None = None,
        memory_enabled: bool = False,
        api_max_retries: int = 12,
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self.variant = "xhigh" if reasoning == "max" else reasoning
        self.timeout_seconds = timeout_seconds
        self.artifacts_dir = artifacts_dir
        self.game_data_path = str(game_data_path) if game_data_path else ""
        self.memory_path = str(memory_path) if memory_path else ""
        self.memory_enabled = memory_enabled
        self.api_max_retries = max(int(api_max_retries), 0)
        self.TOOL_MANIFEST_SHA256 = _sha256_json(
            tools_for_profile(memory_enabled=memory_enabled)
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._scratch = tempfile.TemporaryDirectory(prefix="adaptive-opencode-scratch-")
        self.scratch = Path(self._scratch.name)
        self.trace_file = self.artifacts_dir / "mcp-trace.log"
        self.terminal_file = self.artifacts_dir / "epoch-terminal.signal.json"
        self.command = self._resolve_command(command)
        self.system_prompt = self.SYSTEM_PROMPT
        self.invocation_count = 0
        self.session_id: str | None = None
        self._trace_call_count = 0
        self._active_process: subprocess.Popen[str] | None = None
        self._write_project_config(envd_url, lease_id)

    @staticmethod
    def _resolve_command(command: str | None) -> str:
        resolved = shutil.which(command or "opencode") or (command or "")
        candidate = Path(resolved) if resolved else None
        if candidate and candidate.suffix.lower() in {".cmd", ".ps1"}:
            binary = (
                candidate.parent
                / "node_modules"
                / "opencode-ai"
                / "bin"
                / "opencode.exe"
            )
            if binary.exists():
                return str(binary)
        if candidate and candidate.exists():
            return str(candidate)
        appdata = os.environ.get("APPDATA")
        if appdata:
            binary = (
                Path(appdata)
                / "npm"
                / "node_modules"
                / "opencode-ai"
                / "bin"
                / "opencode.exe"
            )
            if binary.exists():
                return str(binary)
        raise RuntimeError(
            "OpenCode CLI not found; install it with `npm install -g opencode-ai`"
        )

    def _write_project_config(self, envd_url: str, lease_id: str) -> None:
        config = {
            "$schema": "https://opencode.ai/config.json",
            "default_agent": "factorio-eval",
            "agent": {
                "factorio-eval": {
                    "description": "Isolated persistent Factorio benchmark agent",
                    "mode": "primary",
                    "model": self.model,
                    "prompt": self.SYSTEM_PROMPT,
                    "permission": {"*": "deny", "factorio_*": "allow"},
                }
            },
            "mcp": {
                "factorio": {
                    "type": "local",
                    "command": [
                        sys.executable,
                        str(REPO / "scripts" / "factorio_codex_mcp.py"),
                    ],
                    "cwd": str(REPO),
                    "environment": {
                        "ENVD_URL": envd_url,
                        "LEASE_ID": lease_id,
                        "MCP_TRACE_FILE": str(self.trace_file),
                        "MCP_TERMINAL_FILE": str(self.terminal_file),
                        "FACTORIO_GAME_DATA_FILE": self.game_data_path,
                        "MEMORY_PATH": self.memory_path,
                        "MEMORY_ENABLED": "1" if self.memory_enabled else "0",
                    },
                    "enabled": True,
                    "timeout": 600_000,
                }
            },
            "compaction": {"auto": True, "prune": True},
        }
        (self.scratch / "opencode.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

    def inference_settings(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.model.split("/", 1)[0]
            if "/" in self.model
            else "opencode",
            "reasoning": self.reasoning,
            "variant": self.variant,
            "max_turns": None,
            "toolsets": ["factorio"],
            "persistent_session": True,
            "automatic_compaction": True,
            "tool_permissions": {"factorio_*": "allow", "*": "deny"},
            "api_reference": "callable-in-mcp",
            "game_data_reference": bool(self.game_data_path),
            "memory_enabled": self.memory_enabled,
            "api_max_retries": self.api_max_retries,
        }

    async def start(self, system_prompt: str | None = None) -> None:
        self.system_prompt = system_prompt or self.SYSTEM_PROMPT

    @staticmethod
    def _parse_session_id(output: str) -> str | None:
        session_ids = _parse_opencode_session_ids(output)
        return session_ids[0] if session_ids else None

    @staticmethod
    def _parse_step_finish_reasons(output: str) -> list[str]:
        """Expose provider step reasons for tests and audit tooling."""

        return _parse_opencode_step_finish_reasons(output)

    def _invoke(self, prompt: str) -> SimpleNamespace:
        command = [
            self.command,
            "run",
            "--pure",
            "--format",
            "json",
            "--model",
            self.model,
            "--agent",
            "factorio-eval",
            "--dir",
            str(self.scratch),
        ]
        if self.session_id:
            command.extend(["--session", self.session_id])
        if self.variant and self.variant.lower() not in {"none", "default"}:
            command.extend(["--variant", self.variant])
        command.append(prompt)
        process = subprocess.Popen(
            command,
            cwd=self.scratch,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._active_process = process
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            hermes_harness._terminate_process_tree(process)
            stdout, stderr = process.communicate()
        finally:
            self._active_process = None
        return SimpleNamespace(
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
        )

    def _capture_terminal_signal(self, epoch_number: int) -> dict[str, Any] | None:
        """Copy and parse the authoritative MCP terminal signal, if present."""

        if not self.terminal_file.exists():
            return None
        raw = self.terminal_file.read_text(encoding="utf-8", errors="replace")
        (self.artifacts_dir / f"epoch-{epoch_number:04d}.terminal.json").write_text(
            raw,
            encoding="utf-8",
        )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw, "reason": "malformed_terminal_signal"}
        if isinstance(payload, dict):
            return payload
        return {"payload": payload, "reason": "invalid_terminal_signal"}

    @staticmethod
    def _terminal_reason(payload: dict[str, Any] | None) -> str:
        if not payload:
            return "unknown"
        for key in ("reason", "terminal_reason", "status"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "unknown"

    @staticmethod
    def _continuation_prompt() -> str:
        return (
            "The previous OpenCode provider step ended with reason:length. "
            "The current customer order is still active. Continue the same "
            "persistent benchmark session after automatic context compaction; "
            "do not start a new session, reset the factory, or claim completion "
            "without verifying the order. Continue using the Factorio tools "
            "until the MCP environment reports an authoritative terminal state."
        )

    def _write_epoch_audit(
        self,
        *,
        epoch_number: int,
        session_id: str | None,
        invocation_records: list[dict[str, Any]],
        continuation_reasons: list[str],
        provider_step_finish_reasons: list[str],
        terminal_payload: dict[str, Any] | None,
        stop_reason: str,
        failure_category: str | None,
    ) -> None:
        """Persist the provider state machine decisions for later calibration."""

        _atomic_json(
            self.artifacts_dir / f"epoch-{epoch_number:04d}.opencode.audit.json",
            {
                "schema_version": "opencode-epoch-audit-v1",
                "epoch_index": epoch_number,
                "session_id": session_id,
                "provider_invocations": len(invocation_records),
                "invocations": invocation_records,
                "continuation_reasons": list(continuation_reasons),
                "provider_step_finish_reasons": list(
                    provider_step_finish_reasons
                ),
                "terminal_observed": terminal_payload is not None,
                "terminal_reason": self._terminal_reason(terminal_payload),
                "stop_reason": stop_reason,
                "failure_category": failure_category,
            },
        )

    async def run_epoch(self, order_prompt: str) -> AgentEpochTelemetry:
        epoch_number = self.invocation_count + 1
        prompt = (
            order_prompt
            if self.invocation_count == 0
            else (
                "Continue the same persistent benchmark session. A new "
                f"customer order is now active.\n\n{order_prompt}"
            )
        )
        self.terminal_file.unlink(missing_ok=True)
        started = time.perf_counter()
        terminal_payload: dict[str, Any] | None = None
        attempt_outputs: list[str] = []
        invocation_records: list[dict[str, Any]] = []
        continuation_reasons: list[str] = []
        provider_step_finish_reasons: list[str] = []
        prompt_chars = 0
        failure_category: str | None = None
        stop_reason = "unknown"
        current_prompt = prompt

        # A logical invocation may be retried for a provider rate limit. A
        # length result is different: it is a successful provider boundary
        # that requires an unbounded continuation in the same OpenCode
        # session, so it deliberately does not consume api_max_retries.
        while True:
            prompt_chars += len(current_prompt)
            logical_outputs: list[str] = []
            invocation: SimpleNamespace | None = None
            retry_exhausted = False
            for retry_attempt in range(self.api_max_retries + 1):
                invocation_task = asyncio.create_task(
                    asyncio.to_thread(self._invoke, current_prompt)
                )
                while not invocation_task.done():
                    await asyncio.sleep(0.25)
                    if terminal_payload is None:
                        terminal_payload = self._capture_terminal_signal(epoch_number)
                    if terminal_payload is not None:
                        # The MCP signal is authoritative. Stop the provider
                        # process after it is observed, but still collect its
                        # already-buffered JSONL for the audit artifact.
                        await asyncio.sleep(0.5)
                        if (
                            self._active_process is not None
                            and self._active_process.poll() is None
                        ):
                            hermes_harness._terminate_process_tree(self._active_process)
                        break
                invocation = await invocation_task
                stdout = str(getattr(invocation, "stdout", "") or "")
                stderr = str(getattr(invocation, "stderr", "") or "")
                attempt_text = stdout
                if stderr:
                    attempt_text += "\n--- stderr ---\n" + stderr
                logical_outputs.append(attempt_text)

                session_ids = _parse_opencode_session_ids(stdout)
                session_error: str | None = None
                if session_ids:
                    if self.session_id is None:
                        self.session_id = session_ids[0]
                    elif any(session_id != self.session_id for session_id in session_ids):
                        session_error = "opencode_session_changed"
                reasons = _parse_opencode_step_finish_reasons(stdout)
                provider_step_finish_reasons.extend(reasons)
                if terminal_payload is None:
                    # The process can exit before the polling loop gets a
                    # chance to observe a signal written at the same instant.
                    terminal_payload = self._capture_terminal_signal(epoch_number)

                trace_text = (
                    self.trace_file.read_text(encoding="utf-8", errors="replace")
                    if self.trace_file.exists()
                    else ""
                )
                calls_started = trace_text.count("tools/call") > self._trace_call_count
                normalized_stdout = stdout.replace(" ", "")
                retryable = (
                    terminal_payload is None
                    and not bool(getattr(invocation, "timed_out", False))
                    and not calls_started
                    and getattr(invocation, "returncode", None) not in {0, None}
                    and (
                        '"isRetryable":true' in normalized_stdout
                        or '"statusCode":429' in normalized_stdout
                        or "Rate limit exceeded" in stdout
                    )
                )
                invocation_records.append(
                    {
                        "invocation": len(invocation_records) + 1,
                        "retry_attempt": retry_attempt,
                        "returncode": getattr(invocation, "returncode", None),
                        "timed_out": bool(getattr(invocation, "timed_out", False)),
                        "session_ids": session_ids,
                        "step_finish_reasons": reasons,
                        "retryable": retryable,
                        "retry_exhausted": bool(
                            retryable and retry_attempt >= self.api_max_retries
                        ),
                        "action": (
                            "provider_retry"
                            if retryable and retry_attempt < self.api_max_retries
                            else "evaluate"
                        ),
                    }
                )
                if retryable and retry_attempt < self.api_max_retries:
                    await asyncio.sleep(min(2**retry_attempt, 60))
                    continue
                retry_exhausted = bool(retryable)

                if session_error is not None:
                    failure_category = session_error
                    stop_reason = "provider_session_changed"
                elif terminal_payload is not None:
                    stop_reason = (
                        "contract_terminal:" + self._terminal_reason(terminal_payload)
                    )
                elif bool(getattr(invocation, "timed_out", False)):
                    failure_category = "provider_timeout"
                    stop_reason = "provider_timeout_without_terminal"
                elif reasons and reasons[-1] == "length":
                    # Context exhaustion is recoverable. The first provider
                    # event established the session ID; without it a
                    # same-session continuation cannot be made safely.
                    if self.session_id is None:
                        failure_category = "opencode_session_missing"
                        stop_reason = "length_without_resumable_session"
                    else:
                        continuation_reasons.append("reason:length")
                        stop_reason = "continuing_after_reason:length"
                        current_prompt = self._continuation_prompt()
                        if len(logical_outputs) > 1:
                            attempt_outputs.append(
                                "\n--- provider retry ---\n".join(logical_outputs)
                            )
                        else:
                            attempt_outputs.append(logical_outputs[0])
                        attempt_outputs.append(
                            "\n--- provider continuation "
                            f"{len(continuation_reasons)}: reason:length ---\n"
                        )
                        break
                elif retry_exhausted:
                    failure_category = "provider_rate_limit"
                    stop_reason = "provider_retry_exhausted_without_terminal"
                else:
                    # A provider process reaching EOF is not an order result.
                    # In particular, a clean exit with reason=stop or no
                    # reason must never turn into a rated partial outcome.
                    failure_category = "provider_exit_without_terminal"
                    stop_reason = (
                        "provider_exit_without_contract_terminal"
                        if getattr(invocation, "returncode", None) in {0, None}
                        else "provider_nonzero_exit_without_contract_terminal"
                    )
                break

            # ``break`` above exits the inner retry loop. A length result uses
            # the continuation branch and must re-enter the outer loop.
            if continuation_reasons and stop_reason == "continuing_after_reason:length":
                continue
            if logical_outputs:
                if len(logical_outputs) > 1:
                    attempt_outputs.append(
                        "\n--- provider retry ---\n".join(logical_outputs)
                    )
                else:
                    attempt_outputs.append(logical_outputs[0])
            break

        if invocation is None:
            # Defensive guard: the loop always invokes at least once, but a
            # classified harness failure is preferable to an assertion that
            # could accidentally be turned into a rated order result.
            failure_category = failure_category or "harness_no_invocation"
            stop_reason = "harness_no_invocation"
        elapsed = time.perf_counter() - started
        self.invocation_count += 1
        combined_output = "\n".join(attempt_outputs)
        (self.artifacts_dir / f"epoch-{epoch_number:04d}.opencode.jsonl").write_text(
            combined_output, encoding="utf-8"
        )
        trace_text = (
            self.trace_file.read_text(encoding="utf-8", errors="replace")
            if self.trace_file.exists()
            else ""
        )
        trace_call_count = trace_text.count("tools/call")
        epoch_tool_calls = max(trace_call_count - self._trace_call_count, 0)
        self._trace_call_count = trace_call_count
        self._write_epoch_audit(
            epoch_number=epoch_number,
            session_id=self.session_id,
            invocation_records=invocation_records,
            continuation_reasons=continuation_reasons,
            provider_step_finish_reasons=provider_step_finish_reasons,
            terminal_payload=terminal_payload,
            stop_reason=stop_reason,
            failure_category=failure_category,
        )
        return AgentEpochTelemetry(
            model_seconds=elapsed,
            tool_seconds=0.0,
            turns=epoch_tool_calls,
            transport_errors=int(failure_category is not None),
            prompt_chars=prompt_chars,
            response_chars=len(combined_output),
            invocations=len(invocation_records),
            continuation_reasons=continuation_reasons,
            provider_step_finish_reasons=provider_step_finish_reasons,
            stop_reason=stop_reason,
            failure_category=failure_category,
        )

    async def close(self) -> None:
        if self._active_process is not None and self._active_process.poll() is None:
            hermes_harness._terminate_process_tree(self._active_process)
        self._scratch.cleanup()


# ---------------------------------------------------------------------------
# Selection + commitment
# ---------------------------------------------------------------------------


def render_order_prompt(
    spec: ContractEpochSpec, *, memory_enabled: bool = False
) -> str:
    memory_instruction = (
        "At this order boundary, selectively read relevant session memory; "
        "before stopping, record a short handoff under "
        f"orders/{spec.epoch_index} with delivery, capability progress, "
        "blockers, and the next likely step. "
        if memory_enabled
        else ""
    )
    lines = spec.products or (
        ProductDemandSpec(product=spec.item_name, quantity=float(spec.quantity)),
    )
    demand = ", ".join(
        f"{round(line.quantity)} x {line.product}" for line in lines
    )
    service = (
        "This is a sustained-throughput order: deliveries are scored across "
        "the entire window, so an end-of-window burst does not substitute for "
        "steady production. You may call factorio_check_throughput to measure "
        "the unattended depot rate; it advances factory time. "
        if spec.order_kind == "sustained"
        else ""
    )
    return (
        f"CUSTOMER ORDER #{spec.epoch_index}\n"
        f"Deliver {demand} into the customer depot "
        f"within {spec.deadline_ticks} ticks ({spec.deadline_ticks // 3600} "
        "minutes of factory time). Deliveries count only when they cross "
        f"into the pre-existing depot chests; {CUSTOMER_DEPOT_LOCATION}. "
        "Feed a depot with an inserter: direct insert_item delivery is recorded "
        "for audit but does not fulfill the order. Depot contents are consumed "
        "immediately, so its inventory will normally appear empty. "
        f"{service}{memory_instruction}Current inventory "
        "and infrastructure remain "
        "yours to use. Reply with programs that advance fulfillment; the "
        "order cannot be changed now."
    )


def build_candidate_pool(
    *,
    context,
    catalog: ProductCatalog,
    difficulty_model,
    selection_history: SelectionHistory,
    remaining_session_ticks: int | None,
    calibration_manifest: CalibrationManifest | None,
    pool_size_per_template: int = 3,
    allow_stage_stretch: bool = False,
) -> list[ContractCandidate]:
    candidates: list[ContractCandidate] = []
    envelope = calibration_manifest.supported_ranges if calibration_manifest else None
    # Family-level repetition counts for the generator's rejection policy:
    # map the selector's per-product ledger onto crafting categories.
    recent_family_counts: dict[str, int] = {}
    for product_id, count in selection_history.family_counts.items():
        facts = catalog.facts(product_id)
        if facts is not None:
            family = facts.recipe.category
            recent_family_counts[family] = recent_family_counts.get(family, 0) + count
    for template in DEFAULT_TEMPLATE_BANK.all():
        candidates.extend(
            generate_candidates(
                template=template,
                generation_seed=_generation_seed(context, template),
                context=context,
                catalog=catalog,
                difficulty_model=difficulty_model,
                remaining_session_ticks=remaining_session_ticks,
                recent_family_counts=recent_family_counts,
                calibration_envelope=envelope,
                pool_size=pool_size_per_template,
                allow_stage_stretch=allow_stage_stretch,
            )
        )
    return candidates


def _generation_seed(context, template) -> int:
    import hashlib

    payload = json.dumps(
        [context.state_digest, template.template_id],
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


# ---------------------------------------------------------------------------
# Session loop
# ---------------------------------------------------------------------------


def stopping_rule_met(
    rating: CapabilityRating,
    completed_epochs: int,
    session_ticks: int,
    interventions: int,
    mandatory_coverage_complete: bool,
    config: SessionStoppingConfig,
    *,
    failed_deliveries: int = 0,
    wall_seconds: float = 0.0,
) -> bool:
    """Stop on explicit hard limits, or on a coverage-qualified sigma target."""
    if wall_seconds >= config.wall_clock_failsafe_seconds:
        return True
    if (
        config.max_failed_deliveries is not None
        and failed_deliveries >= config.max_failed_deliveries
    ):
        return True
    if (
        config.max_rated_epochs is not None
        and rating.rated_epoch_count >= config.max_rated_epochs
    ):
        return True
    if config.max_session_ticks is not None and session_ticks >= config.max_session_ticks:
        return True
    if (
        config.max_session_interventions is not None
        and interventions >= config.max_session_interventions
    ):
        return True
    return bool(
        mandatory_coverage_complete
        and config.target_sigma is not None
        and rating.sigma <= config.target_sigma
    )


async def run_session(args: argparse.Namespace) -> AdaptiveSessionRecord:
    from fle.envd.benchmark_results import summarize_adaptive_session

    started_at = datetime.now(timezone.utc)
    recipes, technologies = _load_recipe_dump(args.recipe_dump)
    # Reference construction scans the complete API corpus.  It is evaluator
    # setup, not model wall-clock time, so compute identity inputs before the
    # session failsafe starts.
    api_reference_hash = ApiReference().reference_hash
    # Hash the exact export payload, including version, prototype, and machine
    # metadata when present.  The candidate catalog still consumes the
    # validated recipe/technology projections below, while MCP lookups use the
    # same source file unchanged.
    game_data_reference, _ = load_game_data(args.recipe_dump)
    game_data_reference_hash = game_data_reference.reference_hash
    session_wall_start = time.perf_counter()

    manifest: CalibrationManifest | None = None
    if args.calibration_manifest and Path(args.calibration_manifest).exists():
        manifest = CalibrationManifest.model_validate_json(
            Path(args.calibration_manifest).read_text(encoding="utf-8")
        )
        if not manifest.accepted:
            raise ValueError(
                "Calibration manifest is not accepted by the official gates"
            )

    difficulty_model = (
        CalibratedDifficultyModel(manifest)
        if manifest
        else UncalibratedDifficultyModel()
    )
    rater = TrueskillContractRater()
    selector = ContractSelector(weights=SelectorWeights(), manifest=manifest)
    history = SelectionHistory()
    customer_policy = EvidenceDrivenCustomerPolicy()

    catalog_source = StaticRecipeDataSource(
        recipes, technologies, game_version="2.0.73"
    )
    catalog = ProductCatalog(catalog_source)

    record_path = Path(args.output).resolve()
    trajectory_dir = record_path.parent / f"{record_path.stem}-epochs"
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    memory_profile = getattr(args, "memory_profile", "disabled")
    if memory_profile not in {"disabled", "stateful"}:
        raise ValueError("memory_profile must be 'disabled' or 'stateful'")
    memory_enabled = memory_profile == "stateful"
    # This path is intentionally passed only to the isolated MCP process as a
    # stable run identity.  Memory mutations are served by envd and the model
    # never receives a filesystem tool or this path.
    memory_path = record_path.parent / f"{record_path.stem}.memory.json"

    rating = rater.initial_rating()
    epochs: list[AdaptiveEpochRecord] = []
    model_seconds_total = 0.0
    tool_seconds_total = 0.0
    transport_failures = 0
    extrapolation_count = 0
    infrastructure_error_count = 0
    termination_reason = "unknown"
    session_id = f"adaptive-{started_at.strftime('%Y%m%dT%H%M%SZ')}-{args.run_id}"

    participant: ParticipantIdentity | None = None
    async with HTTPEnvironmentClient(args.envd_url) as client:
        lease = await client.lease(freeplay_task_spec())

        async def _executor(
            code: str,
            *,
            request_id: str | None = None,
        ) -> Any:
            result = await client.execute(
                lease.lease_id,
                code,
                request_id=request_id,
            )
            return result

        async def _memory_executor(
            name: str,
            arguments: dict[str, Any],
        ) -> Any:
            """Route native memory calls through the same lease service API."""

            if name == "factorio_memory_list":
                return await client.memory_list(
                    lease.lease_id,
                    prefix=str(arguments.get("prefix", "")),
                    limit=int(arguments.get("limit", 50)),
                    cursor=(
                        str(arguments["cursor"])
                        if arguments.get("cursor") is not None
                        else None
                    ),
                )
            if name == "factorio_memory_read":
                return await client.memory_read(
                    lease.lease_id,
                    str(arguments["key"]),
                )
            if name == "factorio_memory_write":
                return await client.memory_write(
                    lease.lease_id,
                    str(arguments["key"]),
                    str(arguments["content"]),
                    expected_revision=(
                        int(arguments["expected_revision"])
                        if arguments.get("expected_revision") is not None
                        else None
                    ),
                )
            if name == "factorio_memory_delete":
                return await client.memory_delete(
                    lease.lease_id,
                    str(arguments["key"]),
                    expected_revision=(
                        int(arguments["expected_revision"])
                        if arguments.get("expected_revision") is not None
                        else None
                    ),
                )
            if name == "factorio_memory_search":
                return await client.memory_search(
                    lease.lease_id,
                    str(arguments["query"]),
                    limit=int(arguments.get("limit", 20)),
                    cursor=(
                        str(arguments["cursor"])
                        if arguments.get("cursor") is not None
                        else None
                    ),
                )
            if name == "factorio_memory_trace":
                return await client.memory_trace(
                    lease.lease_id,
                    limit=int(arguments.get("limit", 100)),
                    cursor=(
                        str(arguments["cursor"])
                        if arguments.get("cursor") is not None
                        else None
                    ),
                )
            raise ValueError(f"unknown memory tool: {name}")

        async def _throughput_executor(
            *, request_id: str | None = None
        ) -> Any:
            return await client.check_contract_throughput(
                lease.lease_id,
                request_id=(
                    f"native-throughput:{request_id}" if request_id else None
                ),
            )

        agent: AgentSession
        if args.scripted_responses:
            agent = ScriptedAgentSession(json.loads(args.scripted_responses))
        elif getattr(args, "harness", "native") == "hermes":
            agent = HermesPersistentAgentSession(
                envd_url=args.envd_url,
                lease_id=lease.lease_id,
                model=args.model,
                reasoning=getattr(args, "reasoning", "max"),
                timeout_seconds=getattr(
                    args,
                    "epoch_harness_timeout_seconds",
                    args.wall_clock_failsafe_seconds,
                ),
                artifacts_dir=record_path.parent / "hermes",
                api_max_retries=getattr(args, "hermes_api_max_retries", 12),
                game_data_path=args.recipe_dump,
                memory_path=memory_path,
                memory_enabled=memory_enabled,
            )
        elif getattr(args, "harness", "native") == "opencode":
            agent = OpenCodePersistentAgentSession(
                envd_url=args.envd_url,
                lease_id=lease.lease_id,
                model=args.model,
                reasoning=getattr(args, "reasoning", None),
                timeout_seconds=getattr(
                    args,
                    "epoch_harness_timeout_seconds",
                    args.wall_clock_failsafe_seconds,
                ),
                artifacts_dir=record_path.parent / "opencode",
                command=getattr(args, "opencode_command", None),
                game_data_path=args.recipe_dump,
                memory_path=memory_path,
                memory_enabled=memory_enabled,
            )
        else:
            agent = OpenAICompatibleAgentSession(
                base_url=args.model_base_url,
                api_key=(
                    args.api_key
                    or (
                        os.environ.get("OPEN_ROUTER_API_KEY", "")
                        if args.provider.lower() in {"openrouter", "stealth"}
                        else os.environ.get("OPENAI_API_KEY", "")
                    )
                ),
                model=args.model,
                executor=_executor,
                memory_executor=_memory_executor,
                throughput_executor=_throughput_executor,
                max_turns_per_epoch=args.max_turns_per_epoch,
                temperature=args.temperature,
                game_data_path=args.recipe_dump,
                memory_path=memory_path,
                memory_enabled=memory_enabled,
            )

        active_spec: ContractEpochSpec | None = None
        mandatory_bands: set[int] = set()
        mandatory_mixtures: set[str] = set()
        epoch_index = 1
        async def _renew_environment_lease() -> None:
            await client.get_contract_session_state(lease.lease_id)

        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(
                record_path.parent,
                args.run_id,
                lease_keepalive=_renew_environment_lease,
            )
        )
        try:
            system_prompt = getattr(agent, "SYSTEM_PROMPT", "scripted-agent-v1")
            await agent.start(system_prompt)
            if isinstance(
                agent,
                (
                    OpenAICompatibleAgentSession,
                    HermesPersistentAgentSession,
                    OpenCodePersistentAgentSession,
                ),
            ):
                tool_manifest_hash = agent.TOOL_MANIFEST_SHA256
                inference_settings = agent.inference_settings()
            else:
                tool_manifest_hash = _sha256_json([])
                inference_settings = {"harness": agent.harness_version}
            participant = ParticipantIdentity(
                provider=args.provider,
                model_snapshot=args.model,
                harness_version=getattr(agent, "harness_version", args.harness_version),
                system_prompt_hash=_sha256_text(system_prompt),
                tool_manifest_hash=tool_manifest_hash,
                inference_settings_hash=_sha256_json(inference_settings),
                api_reference_hash=api_reference_hash,
                game_data_reference_hash=game_data_reference_hash,
                memory_implementation_version=(
                    "session-memory-v1" if memory_enabled else "disabled"
                ),
                memory_initial_state_hash=_sha256_json(
                    {"profile": memory_profile, "entries": []}
                ),
                graph_visibility_policy="privileged_only",
            )

            while True:
                state_before = await client.get_contract_session_state(lease.lease_id)
                elapsed_wall_seconds = time.perf_counter() - session_wall_start
                remaining_wall_seconds = (
                    args.wall_clock_failsafe_seconds - elapsed_wall_seconds
                )
                if remaining_wall_seconds <= 0:
                    termination_reason = "wall_clock_failsafe"
                    break
                remaining_session_ticks = (
                    None
                    if args.max_session_ticks is None
                    else max(
                        args.max_session_ticks - state_before.session_simulation_ticks,
                        0,
                    )
                )
                if remaining_session_ticks == 0:
                    termination_reason = "session_tick_limit"
                    break
                context = await client.capture_contract_context(
                    lease.lease_id, session_id, epoch_index
                )
                pool = build_candidate_pool(
                    context=context,
                    catalog=catalog,
                    difficulty_model=difficulty_model,
                    selection_history=history,
                    remaining_session_ticks=remaining_session_ticks,
                    calibration_manifest=manifest,
                )
                accepted_pool = [candidate for candidate in pool if candidate.accepted]
                if not accepted_pool:
                    # Repetition controls must not become an implicit order
                    # ceiling when only one progression family is reachable.
                    # Retry without recent-history penalties; genuine stage,
                    # reachability, and feasibility rejection still applies.
                    pool = build_candidate_pool(
                        context=context,
                        catalog=catalog,
                        difficulty_model=difficulty_model,
                        selection_history=SelectionHistory(),
                        remaining_session_ticks=remaining_session_ticks,
                        calibration_manifest=manifest,
                    )
                    accepted_pool = [
                        candidate for candidate in pool if candidate.accepted
                    ]
                    if not accepted_pool:
                        termination_reason = "candidate_pool_exhausted"
                        break
                mandatory_bands, mandatory_mixtures = _refresh_coverage_obligations(
                    required_bands=mandatory_bands,
                    required_mixtures=mandatory_mixtures,
                    reachable_bands={
                        candidate.features.stage_band
                        for candidate in accepted_pool
                        if candidate.features is not None
                    },
                    reachable_mixtures={
                        candidate.mixture_class for candidate in accepted_pool
                    },
                    history=history,
                )
                # Session IDs contain a wall-clock timestamp for artifact
                # identity. Never let that timestamp perturb order selection:
                # identical run IDs, base seeds, and factory states must replay
                # the same candidate sequence.
                selection_seed = _selection_seed(args.run_id, epoch_index, args.seed)
                plan = customer_policy.choose(
                    pool,
                    context=context,
                    catalog=catalog,
                    difficulty_model=difficulty_model,
                    selection_seed=selection_seed,
                    rating=rating,
                )
                candidate = plan.candidate
                scored = selector.score_candidates(pool, rating, history)
                spec = build_epoch_spec(
                    session_id=session_id,
                    epoch_index=epoch_index,
                    selection_seed=selection_seed,
                    candidate=candidate,
                    context=context,
                    benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
                    calibration_version=(
                        manifest.calibration_version if manifest else "uncalibrated"
                    ),
                    order_kind=plan.order_kind,
                    products=plan.products,
                    policy_evidence=plan.evidence,
                )
                _persist_selection_audit(
                    trajectory_dir=trajectory_dir,
                    context=context,
                    pool=pool,
                    scored=scored,
                    selected=candidate,
                    spec=spec,
                    rating=rating,
                )
                await client.begin_contract_epoch(
                    lease.lease_id,
                    spec,
                    request_id=f"{session_id}:begin:{epoch_index}",
                )
                active_spec = spec
                history.record(candidate.features, candidate.mixture_class)
                # Publish an empty/previous-epoch session shell immediately so
                # live dashboards can join active-order.json before a long
                # first contract finishes.
                progress_vector, portfolio_evidence = build_progress_report(epochs)
                _persist(
                    record_path,
                    epochs,
                    participant,
                    args,
                    started_at,
                    session_id,
                    rating,
                    model_seconds_total,
                    tool_seconds_total,
                    infrastructure_error_count,
                    extrapolation_count,
                    progress_vector=progress_vector,
                    portfolio_evidence=portfolio_evidence,
                )
                epoch_wall_start = time.perf_counter()
                infrastructure_interrupt = False
                try:
                    if isinstance(
                        agent,
                        (HermesPersistentAgentSession, OpenCodePersistentAgentSession),
                    ):
                        # Let the harness process-tree timeout fire before the
                        # outer coroutine timeout, avoiding orphaned children.
                        agent.timeout_seconds = min(
                            agent.timeout_seconds,
                            max(remaining_wall_seconds - 5.0, 1.0),
                        )
                    telemetry = await asyncio.wait_for(
                        agent.run_epoch(
                            render_order_prompt(spec, memory_enabled=memory_enabled)
                        ),
                        timeout=remaining_wall_seconds,
                    )
                    infrastructure_interrupt = telemetry.transport_errors > 0
                except asyncio.TimeoutError:
                    telemetry = AgentEpochTelemetry()
                    infrastructure_interrupt = True
                    telemetry.transport_errors = 1
                except Exception:
                    # Provider, protocol, JSON, and tool-transport failures
                    # are harness failures, never evidence that the model
                    # lost the committed order.
                    telemetry = AgentEpochTelemetry(transport_errors=1)
                    infrastructure_interrupt = True
                model_seconds_total += telemetry.model_seconds
                tool_seconds_total += telemetry.tool_seconds
                transport_failures += telemetry.transport_errors
                if spec.order_kind == "sustained" and not infrastructure_interrupt:
                    try:
                        await client.check_contract_throughput(
                            lease.lease_id,
                            authoritative=True,
                            request_id=f"{session_id}:qualify:{epoch_index}",
                        )
                    except Exception:
                        # Qualification evidence is additive. A verifier-side
                        # probe failure must not erase the continuous score.
                        pass
                epoch_wall_seconds = time.perf_counter() - epoch_wall_start
                try:
                    outcome = await client.finalize_contract_epoch(
                        lease.lease_id,
                        spec.epoch_index,
                        spec.commitment_hash,
                        infrastructure_interrupt=infrastructure_interrupt,
                        request_id=f"{session_id}:finalize:{epoch_index}",
                    )
                except Exception as exc:
                    _persist_active_interruption(record_path.parent, spec, exc)
                    raise
                active_spec = None
                outcome = outcome.model_copy(
                    update={
                        "model_seconds": telemetry.model_seconds,
                        "tool_seconds": telemetry.tool_seconds,
                        "runner_wall_seconds": epoch_wall_seconds,
                    }
                )
                post_context = None
                capability_delta = None
                capability_graph_before = None
                capability_graph_after = None
                try:
                    # Capture the post-order state before the next order is
                    # generated.  This is passive evidence and does not alter
                    # the committed outcome or its rating mapping.
                    post_context = await client.capture_contract_context(
                        lease.lease_id, session_id, epoch_index
                    )
                    capability_graph_before = build_capability_graph(
                        context,
                        catalog,
                        target_product=spec.item_name,
                    )
                    capability_graph_after = build_capability_graph(
                        post_context,
                        catalog,
                        target_product=spec.item_name,
                    )
                    capability_delta = compare_capability_snapshots(
                        context,
                        post_context,
                        target_product=spec.item_name,
                        catalog=catalog,
                    )
                    outcome = outcome.model_copy(
                        update={"capability_delta": capability_delta}
                    )
                except Exception:
                    # A missing diagnostic capture must not convert an
                    # otherwise authoritative delivery into a harness loss.
                    post_context = None
                if outcome.status == "infrastructure_error":
                    infrastructure_error_count += 1
                score = None if infrastructure_interrupt else performance_score(outcome)
                mapped = None if score is None else map_outcome(outcome)
                extrapolation_flagged = bool(
                    manifest
                    and CalibratedDifficultyModel(manifest).out_of_envelope(
                        candidate.features
                    )
                )
                extrapolation_count += int(extrapolation_flagged)
                rating_before = rating
                rating_after = None
                if score is not None and not extrapolation_flagged:
                    uncertainty = _contract_uncertainty(manifest, candidate.features)
                    rating_after = rater.update_continuous(
                        rating,
                        spec.effective_difficulty,
                        uncertainty,
                        score,
                    )
                    rating = rating_after
                epochs.append(
                    AdaptiveEpochRecord(
                        spec=spec,
                        outcome=outcome,
                        rating_before=rating_before,
                        rating_after=rating_after,
                        mapped_result=mapped or "unrated",
                        extrapolation_flagged=extrapolation_flagged,
                        post_context=post_context,
                        capability_graph_before=capability_graph_before,
                        capability_graph_after=capability_graph_after,
                        capability_delta=capability_delta,
                    )
                )
                progress_vector, portfolio_evidence = build_progress_report(epochs)
                _persist(
                    record_path,
                    epochs,
                    participant,
                    args,
                    started_at,
                    session_id,
                    rating,
                    model_seconds_total,
                    tool_seconds_total,
                    infrastructure_error_count,
                    extrapolation_count,
                    progress_vector=progress_vector,
                    portfolio_evidence=portfolio_evidence,
                )
                _persist_active_outcome(record_path.parent, spec, outcome)
                customer_policy.observe(spec, outcome, post_context)

                # Provider or harness failures leave the persistent model
                # conversation in an unknown state. End the session instead
                # of committing fresh orders in a rapid failure loop.
                if infrastructure_interrupt:
                    termination_reason = "infrastructure_interrupt"
                    break

                state = await client.get_contract_session_state(lease.lease_id)
                coverage_complete = history.mandatory_coverage_complete(
                    required_bands=mandatory_bands,
                    required_mixtures=mandatory_mixtures,
                )
                if stopping_rule_met(
                    rating,
                    state.completed_epoch_count,
                    state.session_simulation_ticks,
                    state.agent_interventions,
                    mandatory_coverage_complete=coverage_complete,
                    config=SessionStoppingConfig(
                        target_sigma=args.target_sigma,
                        max_rated_epochs=args.max_rated_epochs,
                        max_session_ticks=args.max_session_ticks,
                        max_session_interventions=args.max_session_interventions,
                        max_failed_deliveries=args.max_failed_deliveries,
                        wall_clock_failsafe_seconds=(args.wall_clock_failsafe_seconds),
                    ),
                    failed_deliveries=sum(
                        epoch.outcome.status in {"partial", "expired", "abandoned"}
                        for epoch in epochs
                    ),
                    wall_seconds=time.perf_counter() - session_wall_start,
                ):
                    failed_deliveries = sum(
                        epoch.outcome.status in {"partial", "expired", "abandoned"}
                        for epoch in epochs
                    )
                    termination_reason = (
                        "failed_delivery_limit"
                        if args.max_failed_deliveries is not None
                        and failed_deliveries >= args.max_failed_deliveries
                        else "configured_stopping_rule"
                    )
                    break
                epoch_index += 1
        finally:
            # Every cleanup layer is independent: an open epoch is first
            # converted into an infrastructure outcome, then the session is
            # finalized, the lease is released, and the provider is closed.
            try:
                if active_spec is not None:
                    try:
                        await client.finalize_contract_epoch(
                            lease.lease_id,
                            active_spec.epoch_index,
                            active_spec.commitment_hash,
                            infrastructure_interrupt=True,
                            request_id=f"{session_id}:cleanup:{active_spec.epoch_index}",
                        )
                    except Exception:
                        pass
            finally:
                try:
                    await client.finalize_contract_session(lease.lease_id)
                except Exception:
                    pass
                finally:
                    try:
                        await client.release(lease.lease_id)
                    except Exception:
                        pass
                    finally:
                        try:
                            await agent.close()
                        except Exception:
                            pass
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)

    progress_vector, portfolio_evidence = build_progress_report(epochs)
    record = AdaptiveSessionRecord(
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        run_id=args.run_id,
        session_id=session_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        repository_commit=_git_commit(),
        participant=participant,
        versions={
            "runner": RUNNER_VERSION,
            "harness": participant.harness_version,
            "calibration": (
                manifest.calibration_version if manifest else "uncalibrated"
            ),
            "game": "2.0.73",
        },
        epochs=epochs,
        final_rating=rating,
        model_seconds=model_seconds_total,
        tool_seconds=tool_seconds_total,
        paused_wall_seconds=0.0,
        runner_wall_seconds=time.perf_counter() - session_wall_start,
        infrastructure_error_count=infrastructure_error_count,
        extrapolation_count=extrapolation_count,
        notes=_persistence_notes(
            notes=[
                f"transport_failures={transport_failures}",
                f"termination_reason={termination_reason}",
            ],
            progress_vector=progress_vector,
            portfolio_evidence=portfolio_evidence,
        ),
    )
    errors = validate_adaptive_session(record)
    if errors:
        raise RuntimeError("invalid session record:\n" + "\n".join(errors))
    _atomic_json(record_path, record.model_dump(mode="json"))
    print(json.dumps(summarize_adaptive_session(record), indent=2, sort_keys=True))
    return record


def rating_before_of(
    epochs: list[AdaptiveEpochRecord], fallback: CapabilityRating
) -> CapabilityRating:
    """Latest posterior strictly before the current epoch (audit aid)."""
    return epochs[-1].rating_after if epochs and epochs[-1].rating_after else fallback


def _contract_uncertainty(manifest, features):
    from fle.envd.contract_rating import contract_uncertainty

    return contract_uncertainty(manifest=manifest, features=features)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return _sha256_text(payload)


def _refresh_coverage_obligations(
    *,
    required_bands: set[int],
    required_mixtures: set[str],
    reachable_bands: set[int],
    reachable_mixtures: set[str],
    history: SelectionHistory,
) -> tuple[set[int], set[str]]:
    """Refresh only currently reachable, not-yet-observed obligations.

    A later progression snapshot can expose new bands or mixture classes.  An
    obligation absent from the current accepted pool is retired so an
    exhausted or no-longer-reachable branch cannot prevent stopping forever.
    """
    _ = required_bands, required_mixtures
    return (
        reachable_bands - set(history.band_counts),
        reachable_mixtures - set(history.mixture_counts),
    )


def _selection_seed(run_id: str, epoch_index: int, base_seed: int) -> int:
    import hashlib

    payload = json.dumps([run_id, epoch_index, base_seed]).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def build_progress_report(
    epochs: list[AdaptiveEpochRecord],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Summarize observed capability evidence without asserting autonomy.

    Detailed snapshots and deltas remain on each epoch record.  This compact
    report is stored in session notes so consumers that only understand the
    existing wire model can still discover progress evidence.
    """

    deltas = [
        epoch.capability_delta or epoch.outcome.capability_delta
        for epoch in epochs
    ]
    deltas = [delta for delta in deltas if delta is not None]
    ledger = ledger_from_epochs(epochs)
    vector = ledger.current_progress().model_dump(mode="json")
    vector["evidence_status"] = (
        "autonomous_qualified"
        if vector["certified_capability_count"] > 0
        else "observed_only"
    )
    vector["structural_delta_summary"] = {
        "meaningful_progress_epochs": sum(
            int(delta.meaningful_progress) for delta in deltas
        ),
        "path_nodes_crossed": sum(delta.path_progress for delta in deltas),
        "new_technologies": sorted(
            {item for delta in deltas for item in delta.new_technologies}
        ),
        "new_recipes": sorted(
            {item for delta in deltas for item in delta.new_recipes}
        ),
        "new_machines": sorted(
            {item for delta in deltas for item in delta.new_machines}
        ),
        "newly_producing": sorted(
            {item for delta in deltas for item in delta.newly_producing}
        ),
    }
    portfolio = [
        certificate.model_dump(mode="json")
        for certificate in ledger.certificates
    ]
    return vector, portfolio


def _persistence_notes(
    *,
    notes: list[str] | None = None,
    progress_vector: Any = None,
    portfolio_evidence: Any = None,
) -> list[str]:
    """Encode optional runner evidence through the existing notes field."""

    result = list(notes or [])
    for label, value in (
        ("progress_vector_v1", progress_vector),
        ("portfolio_evidence_v1", portfolio_evidence),
    ):
        if value is not None:
            # Serialization here is deliberate: hooks must be portable JSON,
            # and failures should occur before constructing a session record.
            result.append(
                f"{label}={json.dumps(value, sort_keys=True, separators=(',', ':'))}"
            )
    return result


def _persist(
    record_path: Path,
    epochs: list[AdaptiveEpochRecord],
    participant: ParticipantIdentity,
    args: argparse.Namespace,
    started_at: datetime,
    session_id: str,
    rating: CapabilityRating,
    model_seconds: float,
    tool_seconds: float,
    infra_count: int,
    extrapolation_count: int,
    *,
    progress_vector: Any = None,
    portfolio_evidence: Any = None,
    notes: list[str] | None = None,
) -> None:
    """Atomically persist the session-so-far after every epoch."""
    snapshot = AdaptiveSessionRecord(
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        run_id=args.run_id,
        session_id=session_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        repository_commit=_git_commit(),
        participant=participant,
        versions={"runner": RUNNER_VERSION, "harness": participant.harness_version},
        epochs=list(epochs),
        final_rating=rating,
        model_seconds=model_seconds,
        tool_seconds=tool_seconds,
        infrastructure_error_count=infra_count,
        extrapolation_count=extrapolation_count,
        notes=_persistence_notes(
            notes=notes,
            progress_vector=progress_vector,
            portfolio_evidence=portfolio_evidence,
        ),
    )
    _atomic_json(
        record_path.with_suffix(".partial.json"), snapshot.model_dump(mode="json")
    )


async def _heartbeat_loop(
    output_dir: Path,
    run_id: str,
    *,
    lease_keepalive: Callable[[], Awaitable[None]] | None = None,
) -> None:
    path = output_dir / "heartbeat.json"
    last_keepalive = 0.0
    keepalive_status = "disabled" if lease_keepalive is None else "pending"
    keepalive_error: str | None = None
    try:
        while True:
            now = time.monotonic()
            if lease_keepalive is not None and now - last_keepalive >= 60.0:
                try:
                    await lease_keepalive()
                    keepalive_status = "ok"
                    keepalive_error = None
                except Exception as exc:  # noqa: BLE001 - telemetry must survive
                    keepalive_status = "error"
                    keepalive_error = f"{type(exc).__name__}: {exc}"
                last_keepalive = now
            try:
                _atomic_json(
                    path,
                    {
                        "schema_version": "adaptive-run-heartbeat-v1",
                        "run_id": run_id,
                        "status": "running",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "process_id": os.getpid(),
                        "lease_keepalive_status": keepalive_status,
                        "lease_keepalive_error": keepalive_error,
                    },
                )
            except OSError:
                # Antivirus/indexer contention on Windows must not terminate
                # telemetry while the benchmark itself continues running.
                pass
            await asyncio.sleep(5)
    finally:
        _atomic_json(
            path,
            {
                "schema_version": "adaptive-run-heartbeat-v1",
                "run_id": run_id,
                "status": "stopped",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "process_id": os.getpid(),
                "lease_keepalive_status": keepalive_status,
                "lease_keepalive_error": keepalive_error,
            },
        )


def _persist_selection_audit(
    *,
    trajectory_dir: Path,
    context: Any,
    pool: list[ContractCandidate],
    scored: list[Any],
    selected: ContractCandidate,
    spec: ContractEpochSpec,
    rating: CapabilityRating,
) -> None:
    """Write the committed order and its probabilistic selection evidence."""

    payload = {
        "status": "committed",
        "epoch_index": spec.epoch_index,
        "captured_context": context.model_dump(mode="json"),
        "rating_before": rating.model_dump(mode="json"),
        "mixture_weights": MIXTURE_WEIGHTS,
        "candidate_pool": [candidate.model_dump(mode="json") for candidate in pool],
        "scored_candidates_in_selected_mixture": [
            {
                "candidate": item.candidate.model_dump(mode="json"),
                "score": item.score,
                "components": item.components,
            }
            for item in scored
        ],
        "selected_candidate": selected.model_dump(mode="json"),
        "committed_spec": spec.model_dump(mode="json"),
    }
    epoch_path = trajectory_dir / f"epoch-{spec.epoch_index:04d}.selection.json"
    _atomic_json(epoch_path, payload)
    _atomic_json(trajectory_dir.parent / "active-order.json", payload)


def _persist_active_outcome(
    output_dir: Path,
    spec: ContractEpochSpec,
    outcome: Any,
) -> None:
    _atomic_json(
        output_dir / "active-order.json",
        {
            "status": outcome.status,
            "epoch_index": spec.epoch_index,
            "committed_spec": spec.model_dump(mode="json"),
            "outcome": outcome.model_dump(mode="json"),
        },
    )


def _persist_active_interruption(
    output_dir: Path,
    spec: ContractEpochSpec,
    error: Exception,
) -> None:
    """Make an unfinalized committed epoch explicit to artifact consumers."""

    _atomic_json(
        output_dir / "active-order.json",
        {
            "status": "interrupted",
            "epoch_index": spec.epoch_index,
            "committed_spec": spec.model_dump(mode="json"),
            "termination_reason": "epoch_finalization_failed",
            "infrastructure_error": {
                "category": type(error).__name__,
                "message": str(error)[:500],
            },
        },
    )


def _atomic_json(
    path: Path,
    payload: Any,
    *,
    max_replace_attempts: int = ATOMIC_JSON_MAX_REPLACE_ATTEMPTS,
    backoff_seconds: float = ATOMIC_JSON_REPLACE_BACKOFF_SECONDS,
    max_backoff_seconds: float = ATOMIC_JSON_REPLACE_BACKOFF_MAX_SECONDS,
) -> None:
    """Write JSON via a same-directory temp file and bounded replace retries.

    Windows antivirus and indexers can briefly hold either path.  Keeping the
    temporary file beside the destination preserves ``os.replace`` atomicity;
    retries address transient sharing violations without an unbounded loop.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    attempts = max(int(max_replace_attempts), 1)
    delay = max(float(backoff_seconds), 0.0)
    delay_cap = max(float(max_backoff_seconds), delay)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(attempts):
            try:
                os.replace(temporary, path)
                return
            except OSError:
                if attempt + 1 >= attempts:
                    raise
                if delay:
                    time.sleep(delay)
                    delay = min(delay * 2, delay_cap)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            # A sharing violation can also affect cleanup.  The bounded write
            # has already raised its replace error, so do not mask it here.
            pass


def _git_commit() -> str:
    import subprocess

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), text=True
        ).strip()
    except Exception:
        return "unknown"


def _load_recipe_dump(
    path: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path:
        raise ValueError(
            "An authoritative non-empty recipe dump is required; "
            "pass --recipe-dump PATH."
        )
    recipe_path = Path(path)
    if not recipe_path.exists():
        raise ValueError(f"Recipe dump does not exist: {recipe_path}")
    try:
        data = json.loads(recipe_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read recipe dump {recipe_path}: {exc}") from exc
    if isinstance(data, list):
        recipes = data
        technologies: list[dict[str, Any]] = []
    elif isinstance(data, dict):
        recipes = data.get("recipes")
        technologies = data.get("technologies", [])
    else:
        recipes = None
        technologies = []
    if not isinstance(recipes, list) or not recipes:
        raise ValueError(
            f"Recipe dump {recipe_path} must be a non-empty JSON list of recipes "
            "or an object containing a non-empty recipes list"
        )
    if any(
        not isinstance(recipe, dict)
        or not isinstance(recipe.get("name"), str)
        or not recipe["name"].strip()
        for recipe in recipes
    ):
        raise ValueError(
            f"Recipe dump {recipe_path} contains an entry without a non-empty name"
        )
    if not isinstance(technologies, list) or any(
        not isinstance(technology, dict)
        or not isinstance(technology.get("name"), str)
        or not technology["name"].strip()
        or not isinstance(technology.get("unlocked_recipes", []), list)
        for technology in technologies
    ):
        raise ValueError(
            f"Recipe dump {recipe_path} contains an invalid technology entry"
        )
    return recipes, technologies


def _display_name_component(value: str) -> str:
    """Convert a model/harness identifier into a readable run-ID component."""

    tokens = re.findall(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*", value)
    return "-".join(
        token if token[:1].isdigit() else token[:1].upper() + token[1:]
        for token in tokens
    )


def _display_model_name(model: str) -> str:
    _, _, name = model.rpartition("/")
    name = name or model
    # Provider aliases commonly appended to model IDs are operational
    # metadata, not part of the human-readable benchmark run name.
    name = re.sub(
        r"(?:[-_:](?:contributor[-_]?free|free|latest|preview|default))+$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    return _display_name_component(name) or "Model"


def default_adaptive_run_id(
    model: str,
    harness: str,
    *,
    now: datetime | None = None,
    collision: bool = False,
) -> str:
    """Build the date-first adaptive run ID used when ``--run-id`` is omitted."""

    timestamp = now or datetime.now(timezone.utc)
    harness_name = {
        "opencode": "OpenCode",
        "hermes": "Hermes",
        "native": "Native",
    }.get(harness.lower(), _display_name_component(harness) or "Harness")
    base = (
        f"{timestamp.strftime('%m-%d-%Y')}-"
        f"{_display_model_name(model)}-{harness_name}"
    )
    if collision:
        base += f"-{timestamp.strftime('%H-%M-%S')}"
    return base


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--model-base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--provider", default="local")
    parser.add_argument(
        "--harness",
        choices=("native", "hermes", "opencode"),
        default="native",
        help="Agentic execution surface; recorded in participant identity",
    )
    parser.add_argument(
        "--reasoning",
        default="max",
        help="Reasoning effort or model variant passed to the selected harness",
    )
    parser.add_argument(
        "--epoch-harness-timeout-seconds",
        type=float,
        default=24 * 3600.0,
        help="Per-order harness process failsafe; not an agent turn budget",
    )
    parser.add_argument(
        "--hermes-api-max-retries",
        type=int,
        default=12,
        help=(
            "Provider attempts per Hermes model turn; retries use Hermes' "
            "Retry-After-aware jittered exponential backoff"
        ),
    )
    parser.add_argument(
        "--opencode-command",
        default=None,
        help="Optional path to the OpenCode CLI executable",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration-manifest", default=None)
    parser.add_argument(
        "--recipe-dump",
        default=None,
        help=(
            "Authoritative JSON recipe list, or an object with recipes and "
            "technologies lists"
        ),
    )
    parser.add_argument(
        "--max-turns-per-epoch",
        type=int,
        default=None,
        help="Optional per-order model-turn cap; unlimited by default",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--wall-clock-failsafe-seconds", type=float, default=24 * 3600.0
    )
    parser.add_argument(
        "--max-failed-deliveries",
        type=int,
        default=None,
        help=(
            "Optional emergency stop after this many failed deliveries; "
            "unset keeps the session on its wall-clock/configured limits."
        ),
    )
    parser.add_argument(
        "--memory-profile",
        choices=("disabled", "stateful"),
        default="disabled",
        help=(
            "Expose the lease-scoped model memory tools. Disabled is the "
            "default comparison profile; stateful persists memory across "
            "customer epochs without granting host filesystem access."
        ),
    )
    parser.add_argument("--target-sigma", type=float, default=None)
    parser.add_argument("--max-rated-epochs", type=int, default=None)
    parser.add_argument("--max-session-ticks", type=int, default=None)
    parser.add_argument("--max-session-interventions", type=int, default=None)
    parser.add_argument(
        "--harness-version", default=OpenAICompatibleAgentSession.harness_version
    )
    parser.add_argument("--system-prompt-hash", default="unspecified")
    parser.add_argument(
        "--tool-manifest-hash",
        default=OpenAICompatibleAgentSession.TOOL_MANIFEST_SHA256,
    )
    parser.add_argument("--inference-settings-hash", default="unspecified")
    parser.add_argument(
        "--scripted-responses",
        default=None,
        help="JSON list of scripted responses (test harness)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.run_id is None:
        now = datetime.now(timezone.utc)
        # The output path is the durable collision signal: rerunning a command
        # against an existing result gets a readable clock suffix, while fresh
        # runs remain easy to scan in the frontend.
        args.run_id = default_adaptive_run_id(
            args.model,
            args.harness,
            now=now,
            collision=args.output.exists(),
        )
    asyncio.run(run_session(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
