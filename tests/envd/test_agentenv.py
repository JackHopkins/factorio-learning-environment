from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from fastapi.testclient import TestClient

from fle.envd.agentenv import (
    AgentEnvConfig,
    AgentEnvEnvironmentGateway,
    AgentEnvHTTPClient,
)
from fle.envd.api import create_agentenv_app
from fle.envd.models import (
    ActionEvent,
    ExecutionResult,
    FactorioTaskSpec,
    Lease,
    Observation,
    RewardVector,
    VerificationSnapshot,
)

pytestmark = pytest.mark.no_factorio


class FakeAgentEnvControl:
    def __init__(self):
        self.next_sandbox = 0
        self.inner_leases: dict[str, Lease] = {}
        self.deleted: list[str] = []
        self.paused: set[str] = set()
        self.closed = False

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    async def create_sandbox(self, metadata: dict[str, str]) -> dict[str, Any]:
        sandbox_id = f"sandbox-{self.next_sandbox}"
        self.next_sandbox += 1
        return {"sandboxID": sandbox_id, "metadata": metadata}

    async def delete_sandbox(self, sandbox_id: str) -> None:
        self.deleted.append(sandbox_id)
        self.inner_leases.pop(sandbox_id, None)

    async def pause_sandbox(self, sandbox_id: str) -> None:
        self.paused.add(sandbox_id)

    async def resume_sandbox(self, sandbox_id: str) -> dict[str, Any]:
        self.paused.discard(sandbox_id)
        return {"sandboxID": sandbox_id}

    async def refresh_sandbox(self, sandbox_id: str) -> None:
        assert sandbox_id in self.inner_leases

    async def fork_sandbox(self, sandbox_id: str, count: int) -> list[dict[str, Any]]:
        source = self.inner_leases[sandbox_id]
        outcomes = []
        for _ in range(count):
            child_id = f"sandbox-{self.next_sandbox}"
            self.next_sandbox += 1
            self.inner_leases[child_id] = source.model_copy(deep=True)
            outcomes.append({"sandbox": {"sandboxID": child_id}})
        return outcomes

    async def checkpoint_sandbox(
        self, sandbox_id: str, name: str | None = None
    ) -> dict[str, Any]:
        return {"snapshotID": name or f"snapshot-{sandbox_id}"}

    async def guest_request(
        self,
        sandbox_id: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        if method == "POST" and path == "/v1/leases":
            task = FactorioTaskSpec.model_validate(kwargs["json"]["task"])
            now = datetime.now(timezone.utc)
            lease = Lease(
                lease_id=f"inner-{sandbox_id}",
                worker_id="factorio-0",
                task=task,
                initial_state_hash=f"initial-{sandbox_id}",
                created_at=now,
                expires_at=now + timedelta(minutes=15),
                tool_error_retry_budget=kwargs["json"]["tool_error_retry_budget"],
            )
            self.inner_leases[sandbox_id] = lease
            return lease.model_dump(mode="json", exclude_computed_fields=True)
        inner = self.inner_leases[sandbox_id]
        if method == "DELETE":
            return None
        if method == "POST" and path.endswith("/execute"):
            event = ActionEvent(
                sequence=1,
                code_sha256="code",
                started_at=datetime.now(timezone.utc),
                duration_seconds=0.01,
                result="ok",
                ticks=60,
            )
            return ExecutionResult(
                lease_id=inner.lease_id,
                event=event,
                production_score=1,
                automated_production_score=1,
                state_hash=f"state-{sandbox_id}",
            ).model_dump(mode="json")
        if method == "GET" and path.endswith("/observe"):
            return Observation(
                lease_id=inner.lease_id,
                task_id=inner.task.task_id,
                ticks=60,
                state_hash=f"state-{sandbox_id}",
            ).model_dump(mode="json")
        if method == "POST" and path.endswith("/finalize"):
            return VerificationSnapshot(
                lease_id=inner.lease_id,
                task_id=inner.task.task_id,
                task_fingerprint=inner.task.fingerprint,
                success=True,
                scalar_reward=1,
                rewards=RewardVector(task=1),
                terminal_state_hash=f"state-{sandbox_id}",
            ).model_dump(mode="json")
        raise AssertionError(f"unexpected guest request: {method} {path}")

    async def wait_guest_health(self, sandbox_id: str) -> dict[str, Any]:
        return {"status": "ok", "sandbox_id": sandbox_id}

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_agentenv_http_client_uses_control_and_proxy_contract():
    requests: list[tuple[str, str, dict[str, str], Any]] = []

    async def capture(request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else None
        requests.append(
            (
                request.method,
                request.path,
                {key.lower(): value for key, value in request.headers.items()},
                body,
            )
        )
        if request.path == "/sandboxes":
            return web.json_response({"sandboxID": "sandbox-http"}, status=201)
        if request.path.endswith("/fork"):
            return web.json_response(
                [{"sandbox": {"sandboxID": "sandbox-child"}}],
                status=201,
            )
        if request.path.endswith("/timeout"):
            return web.Response(status=204)
        return web.json_response({"status": "ok"})

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", capture)
    server = TestServer(app)
    await server.start_server()
    client = AgentEnvHTTPClient(
        AgentEnvConfig(
            api_url=str(server.make_url("")).rstrip("/"),
            api_key="secret",
            template_id="factorio-template",
        )
    )
    try:
        created = await client.create_sandbox({"task_id": "task"})
        assert created["sandboxID"] == "sandbox-http"
        await client.guest_request("sandbox-http", "GET", "/v1/health")
        await client.refresh_sandbox("sandbox-http")
        forked = await client.fork_sandbox("sandbox-http", 1)
        assert forked[0]["sandbox"]["sandboxID"] == "sandbox-child"
    finally:
        await client.close()
        await server.close()

    create_request = requests[0]
    assert create_request[0:2] == ("POST", "/sandboxes")
    assert create_request[2]["x-api-key"] == "secret"
    assert create_request[3]["templateID"] == "factorio-template"
    assert create_request[3]["autoPause"] is True

    proxy_request = requests[1]
    assert proxy_request[1] == "/proxy/v1/health"
    assert proxy_request[2]["x-agentenv-sandbox-id"] == "sandbox-http"
    assert proxy_request[2]["x-agentenv-target-port"] == "8172"


def test_agentenv_gateway_proxies_and_forks_live_lease(task_spec):
    control = FakeAgentEnvControl()
    config = AgentEnvConfig(
        api_url="http://agentenv.test",
        template_id="factorio-template",
        capacity=4,
    )
    gateway = AgentEnvEnvironmentGateway(config, control=control)

    with TestClient(create_agentenv_app(gateway)) as client:
        health = client.get("/v1/health")
        assert health.status_code == 200
        assert health.json()["capabilities"]["features"]["clone"] is True
        assert health.json()["capabilities"]["features"]["process_isolation"] is True

        created = client.post(
            "/v1/leases",
            json={
                "task": task_spec.model_dump(mode="json", exclude_computed_fields=True),
                "tool_error_retry_budget": 2,
            },
        )
        assert created.status_code == 201
        source = created.json()
        assert source["worker_id"] == "agentenv:sandbox-0"

        forked = client.post(
            f"/v1/leases/{source['lease_id']}/fork",
            json={"count": 2},
        )
        assert forked.status_code == 201
        branches = forked.json()["branches"]
        assert len(branches) == 2
        assert len({branch["lease_id"] for branch in branches}) == 2
        assert all(
            branch["initial_state_hash"] == source["initial_state_hash"]
            for branch in branches
        )

        branch_id = branches[0]["lease_id"]
        observation = client.get(f"/v1/leases/{branch_id}/observe")
        assert observation.status_code == 200
        assert observation.json()["lease_id"] == branch_id

        execution = client.post(
            f"/v1/leases/{branch_id}/execute",
            json={"code": "print('branch')"},
        )
        assert execution.status_code == 200
        assert execution.json()["lease_id"] == branch_id

        assert client.post(f"/v1/leases/{branch_id}/pause").status_code == 204
        assert "sandbox-1" in control.paused
        resumed = client.post(f"/v1/leases/{branch_id}/resume")
        assert resumed.status_code == 200
        assert "sandbox-1" not in control.paused

        checkpoint = client.post(
            f"/v1/leases/{branch_id}/checkpoints",
            json={"name": "after-branch"},
        )
        assert checkpoint.status_code == 201
        assert checkpoint.json()["checkpoint_id"] == "after-branch"

        final = client.post(f"/v1/leases/{branch_id}/finalize")
        assert final.status_code == 200
        assert final.json()["lease_id"] == branch_id

        assert client.delete(f"/v1/leases/{branch_id}").status_code == 204
        assert "sandbox-1" in control.deleted

    assert control.closed is True


def test_agentenv_gateway_enforces_declared_capacity(task_spec):
    control = FakeAgentEnvControl()
    gateway = AgentEnvEnvironmentGateway(
        AgentEnvConfig(
            api_url="http://agentenv.test",
            template_id="factorio-template",
            capacity=1,
        ),
        control=control,
    )

    with TestClient(create_agentenv_app(gateway)) as client:
        payload = {
            "task": task_spec.model_dump(mode="json", exclude_computed_fields=True)
        }
        assert client.post("/v1/leases", json=payload).status_code == 201
        rejected = client.post("/v1/leases", json=payload)
        assert rejected.status_code == 503
