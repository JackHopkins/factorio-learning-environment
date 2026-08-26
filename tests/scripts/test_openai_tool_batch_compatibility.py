"""OpenAI-compatible batches remain ordered and protocol-valid on termination."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from fle.envd.models import ActionEvent, ExecutionResult
from scripts.adaptive_contract_benchmark import OpenAICompatibleAgentSession

pytestmark = pytest.mark.no_factorio


def _tool_call(call_id: str, code: str):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name="submit_program",
            arguments=json.dumps({"code": code}),
        ),
    )


def test_native_batch_stops_after_terminal_and_synthesizes_remaining_results():
    calls = [_tool_call("call-1", "first()"), _tool_call("call-2", "second()")]

    class Completions:
        def __init__(self):
            self.requests = 0
            self.request_kwargs = None

        async def create(self, **kwargs):
            self.requests += 1
            self.request_kwargs = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="tool_calls",
                        message=SimpleNamespace(content="", tool_calls=calls),
                    )
                ]
            )

    completions = Completions()
    session = object.__new__(OpenAICompatibleAgentSession)
    session._client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    session.model = "test-model"
    session.temperature = 0.0
    session.max_turns = 4
    session.messages = []
    executed: list[str] = []

    async def execute(code: str, *, request_id=None):
        executed.append(code)
        return ExecutionResult(
            lease_id="lease",
            event=ActionEvent(
                sequence=1,
                code_sha256="a" * 64,
                started_at=datetime.now(timezone.utc),
                duration_seconds=0.01,
                result="terminal result",
            ),
            production_score=0,
            automated_production_score=0,
            state_hash="state",
            terminal_reason="contract_expired",
        )

    session._executor = execute
    telemetry = asyncio.run(session.run_epoch("order"))

    assert telemetry.transport_errors == 0
    assert executed == ["first()"]
    assert completions.requests == 1
    assert completions.request_kwargs["parallel_tool_calls"] is True
    tool_messages = [message for message in session.messages if message["role"] == "tool"]
    assert [message["tool_call_id"] for message in tool_messages] == [
        "call-1",
        "call-2",
    ]
    assert "skipped" in tool_messages[1]["content"]
    assert "contract_expired" in tool_messages[1]["content"]
