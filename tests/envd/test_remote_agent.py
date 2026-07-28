import json

import pytest

from fle.envd.models import ActionEvent, ExecutionResult, Observation
from fle.eval.remote_agent import (
    _bounded_tool_content,
    _compact_memory,
    _context_messages,
    _execute_tool,
    _task_spec,
)

pytestmark = pytest.mark.no_factorio


class FakeEnvironmentClient:
    async def observe(self, lease_id):
        return Observation(
            lease_id=lease_id,
            task_id="task",
            ticks=60,
            inventory={"iron-plate": 2},
            state_hash="state",
        )

    async def execute(self, lease_id, code):
        return ExecutionResult(
            lease_id=lease_id,
            event=ActionEvent(
                sequence=1,
                code_sha256="a" * 64,
                started_at="2026-07-26T00:00:00Z",
                duration_seconds=0.1,
                result=code,
            ),
            production_score=1,
            automated_production_score=1,
            state_hash="next",
        )


def test_remote_agent_resolves_builtin_and_benchmark_tasks():
    builtin = _task_spec("milestone_research_automation_v1")
    benchmark = _task_spec("iron_plate_throughput")

    assert builtin.task_family == "milestone"
    assert benchmark.task_family == "throughput"


def test_tool_content_truncation_is_explicit():
    content = _bounded_tool_content({"large": "x" * 100}, max_chars=25)

    assert len(content) > 25
    assert "response characters truncated" in content


def test_context_window_keeps_complete_recent_tool_blocks_and_memory():
    base = [{"role": "system", "content": "base"}]
    blocks = [
        [
            {"role": "assistant", "content": f"turn-{index}"},
            {"role": "tool", "tool_call_id": str(index), "content": "x" * 100},
        ]
        for index in range(5)
    ]

    messages = _context_messages(
        base,
        blocks,
        {"latest_observation": {"ticks": 60}},
        max_chars=500,
    )

    assert messages[0] == base[0]
    assert "Compact runtime memory" in messages[1]["content"]
    assert messages[-2]["content"] == "turn-4"
    assert messages[-1]["tool_call_id"] == "4"
    assert len([item for item in messages if item["role"] == "assistant"]) < 5


def test_context_window_preserves_thinking_mode_reasoning_payload():
    reasoning_turn = [
        {
            "role": "assistant",
            "content": None,
            "reasoning_content": "I should inspect before acting.",
            "tool_calls": [{"id": "call-1"}],
        },
        {
            "role": "tool",
            "tool_call_id": "call-1",
            "content": "{}",
        },
    ]

    messages = _context_messages(
        [{"role": "system", "content": "base"}],
        [reasoning_turn],
        {},
        max_chars=2_000,
    )

    assert messages[-2]["reasoning_content"] == ("I should inspect before acting.")


def test_compact_memory_retains_latest_observation_and_action_tail():
    memory = _compact_memory(
        [
            {
                "name": "factorio_observe_factory",
                "raw": {
                    "ticks": 120,
                    "inventory": {"lab": 1},
                    "production_score": 2,
                    "automated_production_score": 0,
                    "state_hash": "state",
                },
            },
            {
                "name": "factorio_execute_program",
                "raw": {
                    "event": {
                        "sequence": 1,
                        "error": False,
                        "evaluation_retry": True,
                        "executed_tools": ["place_entity"],
                        "result": "placed lab",
                    },
                    "production_score": 2,
                    "automated_production_score": 0,
                    "terminal_reason": None,
                },
            },
        ]
    )

    assert memory["latest_observation"]["inventory"] == {"lab": 1}
    assert memory["recent_actions"][0]["result_tail"] == "placed lab"
    assert memory["recent_actions"][0]["evaluation_retry"] is True


@pytest.mark.asyncio
async def test_remote_agent_tools_use_envd_contract():
    client = FakeEnvironmentClient()

    observation, terminal = await _execute_tool(
        client, "lease", "factorio_observe_factory", "{}"
    )
    execution, terminal_after_execution = await _execute_tool(
        client,
        "lease",
        "factorio_execute_program",
        json.dumps({"code": "print(inspect_inventory())"}),
    )

    assert observation.inventory == {"iron-plate": 2}
    assert terminal is None
    assert execution.event.result == "print(inspect_inventory())"
    assert terminal_after_execution is None


@pytest.mark.asyncio
async def test_remote_agent_returns_tool_errors_to_the_model():
    result, terminal = await _execute_tool(
        FakeEnvironmentClient(),
        "lease",
        "factorio_execute_program",
        json.dumps({"code": ""}),
    )

    assert "requires non-empty code" in result["error"]
    assert terminal is None
