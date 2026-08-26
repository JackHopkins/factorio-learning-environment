"""Compatibility checks for direct and programmatic tool-use boundaries."""

from __future__ import annotations

import asyncio
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import aiohttp
import pytest

from fle.envd.client import HTTPEnvironmentClient
from fle.envd.program_policy import validate_program
from fle.envd.service import EnvironmentService
from fle.envd.models import FactorioTaskSpec
from fle.eval.remote_agent import _skipped_tool_result
from scripts import factorio_codex_mcp
from tests.envd.conftest import FakeWorker

pytestmark = pytest.mark.no_factorio


def test_capability_manifest_describes_direct_and_composed_calling(task_spec):
    service = EnvironmentService([FakeWorker()])
    features = service.health().capabilities.features

    assert features["concurrent_request_safe"] is True
    assert features["per_lease_serial_execution"] is True
    assert features["parallel_world_mutations"] is False
    assert features["programmatic_action_composition"] is True
    assert features["provider_native_programmatic_tool_calling"] is False
    assert features["idempotent_execute_retries"] is True


def test_same_lease_parallel_requests_are_serialized_with_unique_sequences():
    service = EnvironmentService([FakeWorker()])
    task = FactorioTaskSpec(
        task_id="parallel-use",
        goal="exercise serialized requests",
        max_interventions=None,
    )
    lease = service.lease(task)

    def execute(index: int):
        return service.execute(lease.lease_id, f"program_{index}()")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(execute, range(8)))

    assert sorted(result.event.sequence for result in results) == list(range(1, 9))
    assert service.observe(lease.lease_id).production_score == 8.0


def test_programmatic_composition_is_one_validated_intervention(task_spec):
    code = (
        "coal = nearest(Resource.Coal)\n"
        "if coal:\n"
        "    move_to(coal)\n"
        "    for amount in (1, 2):\n"
        "        print(harvest_resource(coal, amount))"
    )
    validate_program(code)
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec)

    result = service.execute(lease.lease_id, code)

    assert result.event.sequence == 1
    assert result.event.error is False


def test_http_client_retries_only_keyed_ambiguous_execute():
    client = HTTPEnvironmentClient("http://envd.invalid")
    calls = []

    async def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if len(calls) == 1:
            raise aiohttp.ClientConnectionError("response lost")
        return {
            "lease_id": "lease",
            "event": {
                "sequence": 1,
                "code_sha256": "a" * 64,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": 0.01,
                "result": "ok",
            },
            "production_score": 1.0,
            "automated_production_score": 1.0,
            "state_hash": "state",
        }

    client._request = fake_request
    result = asyncio.run(
        client.execute("lease", "print('once')", request_id="logical-1")
    )

    assert result.event.sequence == 1
    assert len(calls) == 2
    assert calls[0][2]["json"] == calls[1][2]["json"]

    calls.clear()
    with pytest.raises(aiohttp.ClientConnectionError):
        asyncio.run(client.execute("lease", "print('unkeyed')"))
    assert len(calls) == 1


def test_mcp_advertises_tool_annotations_and_structured_results(monkeypatch):
    tools = {tool["name"]: tool for tool in factorio_codex_mcp.TOOLS}
    observe = tools["factorio_observe_factory"]
    execute = tools["factorio_execute_program"]

    assert observe["annotations"] == {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
    assert execute["annotations"]["readOnlyHint"] is False
    assert execute["annotations"]["destructiveHint"] is True
    assert execute["outputSchema"]["type"] == "object"

    monkeypatch.setenv("LEASE_ID", "lease-structured")
    monkeypatch.setattr(
        factorio_codex_mcp,
        "_envd",
        lambda method, path, payload=None: {"inventory": {}, "state_hash": "s0"},
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {"jsonrpc": "2.0", "id": "observe-1", "method": "initialize"}
            )
            + "\n"
            + json.dumps(
                {"jsonrpc": "2.0", "id": "tools-1", "method": "tools/list"}
            )
            + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "method": "tools/call",
                    "params": {
                        "name": "factorio_observe_factory",
                        "arguments": {},
                    },
                }
            )
            + "\n"
        ),
    )
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)

    factorio_codex_mcp.main()
    responses = [json.loads(line) for line in output.getvalue().splitlines()]

    assert responses[0]["result"]["capabilities"]["tools"]["listChanged"] is False
    assert "instructions" in responses[0]["result"]
    assert responses[2]["result"]["isError"] is False
    assert responses[2]["result"]["structuredContent"] == {
        "inventory": {},
        "state_hash": "s0",
    }


def test_mcp_pipelined_direct_calls_preserve_jsonrpc_ids(monkeypatch):
    monkeypatch.setenv("LEASE_ID", "lease-pipeline")

    def fake_envd(method, path, payload=None):
        if method == "GET":
            return {"ticks": 0, "state_hash": "s0"}
        return {
            "lease_id": "lease-pipeline",
            "event": {
                "sequence": 1,
                "error": False,
                "result": "ok",
            },
        }

    monkeypatch.setattr(factorio_codex_mcp, "_envd", fake_envd)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "observe-call",
            "method": "tools/call",
            "params": {"name": "factorio_observe_factory", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": "execute-call",
            "method": "tools/call",
            "params": {
                "name": "factorio_execute_program",
                "arguments": {"code": "print('ok')"},
            },
        },
    ]
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("\n".join(json.dumps(request) for request in requests) + "\n"),
    )
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)

    factorio_codex_mcp.main()
    responses = [json.loads(line) for line in output.getvalue().splitlines()]

    assert [response["id"] for response in responses] == [
        "observe-call",
        "execute-call",
    ]
    assert all(response["result"]["isError"] is False for response in responses)


def test_native_remote_loop_has_explicit_terminal_skip_payload():
    skipped = _skipped_tool_result("character_died")

    assert skipped["skipped"] is True
    assert skipped["terminal_reason"] == "character_died"
    assert "skipped" in skipped["error"]
