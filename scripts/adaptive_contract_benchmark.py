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
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol

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
    SelectorWeights,
    SessionStoppingConfig,
)
from fle.envd.benchmark_results import (  # noqa: E402
    AdaptiveEpochRecord,
    AdaptiveSessionRecord,
    validate_adaptive_session,
)
from fle.envd.action_reference import ACTION_PROFILE_REFERENCE  # noqa: E402
from scripts import hermes_benchmark as hermes_harness  # noqa: E402
from scripts.factorio_codex_mcp import TOOLS as FACTORIO_MCP_TOOLS  # noqa: E402

RUNNER_VERSION = "adaptive-runner-v1"

FREEPLAY_TASK_ID = "adaptive_contract_session_v1"
CUSTOMER_DEPOT_LOCATION = (
    "the persistent customer depot is six tiles west and ten tiles north "
    "of your starting character (relative offset -6, -10)"
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
    ):
        self.model_seconds = model_seconds
        self.tool_seconds = tool_seconds
        self.turns = turns
        self.transport_errors = transport_errors
        self.prompt_chars = prompt_chars
        self.response_chars = response_chars

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_seconds": self.model_seconds,
            "tool_seconds": self.tool_seconds,
            "turns": self.turns,
            "transport_errors": self.transport_errors,
            "prompt_chars": self.prompt_chars,
            "response_chars": self.response_chars,
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


class OpenAICompatibleAgentSession:
    """Minimal REPL tool-loop over an OpenAI-compatible endpoint.

    The conversation object persists across epochs so later orders observe
    earlier work exactly as the benchmark intends.  Only public API surface
    is used; no provider-specific branch ever touches selection or rating.
    """

    harness_version = "openai-repl-v1"

    SYSTEM_PROMPT = (
        "You operate a Factorio factory through a Python REPL. Each turn you "
        "submit one program via the submit_program tool; its stdout/stderr is "
        "returned to you. Build automated production to fulfil every customer "
        f"order before its deadline. The factory persists across all orders; "
        f"{CUSTOMER_DEPOT_LOCATION}. There is no intervention or turn budget; "
        "continue measuring and improving the persistent factory until the "
        "current order is fulfilled. The action reference below describes "
        "the Python names available inside submit_program.\n\n"
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
                },
            },
        }
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
        max_turns_per_epoch: int | None = None,
        temperature: float = 0.2,
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

    def inference_settings(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_turns_per_epoch": self.max_turns,
            "parallel_tool_calls": True,
        }

    def bind_executor(self, executor: Any) -> None:
        self._executor = executor

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
        if hasattr(result, "event"):
            # Keep the model-facing output compatible with the original
            # session while retaining terminal metadata for the harness.
            text = str(result.event.result)
        elif isinstance(result, str):
            text = result
        else:
            text = str(result)
        return text[:8000], terminal_reason

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
                            code = arguments.get("code", "")
                            if not isinstance(code, str) or not code.strip():
                                raise ValueError(
                                    "submit_program requires non-empty code"
                                )
                            output, terminal = await self._execute(
                                code,
                                request_id=call.id,
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
        "You are being evaluated in one persistent Factorio world. Only use "
        "the factorio_observe_factory and factorio_execute_program tools. "
        "Web, browser, terminal, filesystem, memory, and delegation tools are "
        "prohibited and unavailable. Observe before acting and between major "
        "changes. Build automated production to fulfil each customer order. "
        "The factory and this conversation persist across orders, so preserve "
        "and extend useful infrastructure. There is no intervention, turn, "
        "customer-order, simulation-tick, or rating-convergence budget. Stop "
        "calling tools after the current order is fulfilled, expired, or the "
        "tool result reports another terminal reason. "
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
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self.timeout_seconds = timeout_seconds
        self.api_max_retries = api_max_retries
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
    ) -> None:
        self.model = model
        self.reasoning = reasoning
        self.variant = "xhigh" if reasoning == "max" else reasoning
        self.timeout_seconds = timeout_seconds
        self.artifacts_dir = artifacts_dir
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
        }

    async def start(self, system_prompt: str | None = None) -> None:
        self.system_prompt = system_prompt or self.SYSTEM_PROMPT

    @staticmethod
    def _parse_session_id(output: str) -> str | None:
        for line in output.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            session_id = event.get("sessionID")
            if isinstance(session_id, str) and session_id:
                return session_id
        return None

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
        invocation_task = asyncio.create_task(asyncio.to_thread(self._invoke, prompt))
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
        combined_output = invocation.stdout
        if invocation.stderr:
            combined_output += "\n--- stderr ---\n" + invocation.stderr
        (self.artifacts_dir / f"epoch-{epoch_number:04d}.opencode.jsonl").write_text(
            combined_output, encoding="utf-8"
        )
        parsed_session_id = self._parse_session_id(invocation.stdout)
        if parsed_session_id:
            self.session_id = parsed_session_id
        trace_text = (
            self.trace_file.read_text(encoding="utf-8", errors="replace")
            if self.trace_file.exists()
            else ""
        )
        trace_call_count = trace_text.count("tools/call")
        epoch_tool_calls = max(trace_call_count - self._trace_call_count, 0)
        self._trace_call_count = trace_call_count
        failed = invocation.timed_out or invocation.returncode not in {0, None}
        return AgentEpochTelemetry(
            model_seconds=elapsed,
            tool_seconds=0.0,
            turns=epoch_tool_calls,
            transport_errors=int(failed and not terminal_observed),
            prompt_chars=len(prompt),
            response_chars=len(combined_output),
        )

    async def close(self) -> None:
        if self._active_process is not None and self._active_process.poll() is None:
            hermes_harness._terminate_process_tree(self._active_process)
        self._scratch.cleanup()


# ---------------------------------------------------------------------------
# Selection + commitment
# ---------------------------------------------------------------------------


def render_order_prompt(spec: ContractEpochSpec) -> str:
    return (
        f"CUSTOMER ORDER #{spec.epoch_index}\n"
        f"Deliver {spec.quantity} x {spec.item_name} into the customer depot "
        f"within {spec.deadline_ticks} ticks ({spec.deadline_ticks // 3600} "
        "minutes of factory time). Deliveries count only when they cross "
        f"into the depot chests; {CUSTOMER_DEPOT_LOCATION}. Current inventory "
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
    """Stop on safety/failure limits, or explicit post-coverage evaluation caps."""
    if wall_seconds >= config.wall_clock_failsafe_seconds:
        return True
    if (
        config.max_failed_deliveries is not None
        and failed_deliveries >= config.max_failed_deliveries
    ):
        return True
    optional_trigger = (
        (config.target_sigma is not None and rating.sigma <= config.target_sigma)
        or (
            config.max_rated_epochs is not None
            and rating.rated_epoch_count >= config.max_rated_epochs
        )
        or (
            config.max_session_ticks is not None
            and session_ticks >= config.max_session_ticks
        )
        or (
            config.max_session_interventions is not None
            and interventions >= config.max_session_interventions
        )
    )
    return mandatory_coverage_complete and optional_trigger


async def run_session(args: argparse.Namespace) -> AdaptiveSessionRecord:
    from fle.envd.benchmark_results import summarize_adaptive_session

    started_at = datetime.now(timezone.utc)
    session_wall_start = time.perf_counter()
    recipes, technologies = _load_recipe_dump(args.recipe_dump)

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

    catalog_source = StaticRecipeDataSource(
        recipes, technologies, game_version="2.0.73"
    )
    catalog = ProductCatalog(catalog_source)

    record_path = Path(args.output).resolve()
    trajectory_dir = record_path.parent / f"{record_path.stem}-epochs"
    trajectory_dir.mkdir(parents=True, exist_ok=True)

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
                max_turns_per_epoch=args.max_turns_per_epoch,
                temperature=args.temperature,
            )

        active_spec: ContractEpochSpec | None = None
        mandatory_bands: set[int] = set()
        mandatory_mixtures: set[str] = set()
        epoch_index = 1
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(record_path.parent, args.run_id)
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
                candidate, scored = selector.select(
                    pool, rating, history, selection_seed=selection_seed
                )
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
                        agent.run_epoch(render_order_prompt(spec)),
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
                epoch_wall_seconds = time.perf_counter() - epoch_wall_start
                outcome = await client.finalize_contract_epoch(
                    lease.lease_id,
                    spec.epoch_index,
                    spec.commitment_hash,
                    infrastructure_interrupt=infrastructure_interrupt,
                    request_id=f"{session_id}:finalize:{epoch_index}",
                )
                active_spec = None
                outcome = outcome.model_copy(
                    update={
                        "model_seconds": telemetry.model_seconds,
                        "tool_seconds": telemetry.tool_seconds,
                        "runner_wall_seconds": epoch_wall_seconds,
                    }
                )
                if outcome.status == "infrastructure_error":
                    infrastructure_error_count += 1
                mapped = None if infrastructure_interrupt else map_outcome(outcome)
                extrapolation_flagged = bool(
                    manifest
                    and CalibratedDifficultyModel(manifest).out_of_envelope(
                        candidate.features
                    )
                )
                extrapolation_count += int(extrapolation_flagged)
                rating_before = rating
                rating_after = None
                if mapped is not None and not extrapolation_flagged:
                    uncertainty = _contract_uncertainty(manifest, candidate.features)
                    rating_after = rater.update(
                        rating,
                        spec.effective_difficulty,
                        uncertainty,
                        mapped,
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
                    )
                )
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
                )
                _persist_active_outcome(record_path.parent, spec, outcome)

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
        notes=[
            f"transport_failures={transport_failures}",
            f"termination_reason={termination_reason}",
        ],
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
    )
    _atomic_json(
        record_path.with_suffix(".partial.json"), snapshot.model_dump(mode="json")
    )


async def _heartbeat_loop(output_dir: Path, run_id: str) -> None:
    path = output_dir / "heartbeat.json"
    try:
        while True:
            _atomic_json(
                path,
                {
                    "schema_version": "adaptive-run-heartbeat-v1",
                    "run_id": run_id,
                    "status": "running",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "process_id": os.getpid(),
                },
            )
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


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


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
        default=5,
        help="Stop after this many partial, expired, or abandoned orders",
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
        args.run_id = (
            f"adaptive-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
    asyncio.run(run_session(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
