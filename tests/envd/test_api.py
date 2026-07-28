import pytest
from fastapi.testclient import TestClient

from fle.envd.api import create_app
from fle.envd.service import EnvironmentService
from tests.envd.conftest import FakeWorker

pytestmark = pytest.mark.no_factorio


def test_http_contract(task_spec):
    service = EnvironmentService([FakeWorker()])
    client = TestClient(create_app(service))

    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["capabilities"]["protocol_version"] == "0.3.0"

    response = client.post(
        "/v1/leases",
        json={"task": task_spec.model_dump(mode="json", exclude_computed_fields=True)},
    )
    assert response.status_code == 201
    lease = response.json()
    assert "fingerprint" not in lease["task"]

    execution = client.post(
        f"/v1/leases/{lease['lease_id']}/execute",
        json={"code": "print('hello')"},
    )
    assert execution.status_code == 200
    assert execution.json()["event"]["sequence"] == 1

    rejected = client.post(
        f"/v1/leases/{lease['lease_id']}/execute",
        json={"code": "import os"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["event"]["sequence"] == 2
    assert rejected.json()["event"]["error"] is True
    assert "imports are restricted" in rejected.json()["event"]["result"]
    assert rejected.json()["events"][0]["kind"] == "invalid_action"

    final = client.post(f"/v1/leases/{lease['lease_id']}/finalize")
    assert final.status_code == 200
    assert final.json()["success"] is True

    repeated = client.post(f"/v1/leases/{lease['lease_id']}/finalize")
    assert repeated.json() == final.json()
    assert (
        client.post(
            f"/v1/leases/{lease['lease_id']}/execute",
            json={"code": "print('too late')"},
        ).status_code
        == 409
    )

    assert client.delete(f"/v1/leases/{lease['lease_id']}").status_code == 204


def test_http_lease_accepts_bounded_tool_error_retry_budget(task_spec):
    service = EnvironmentService([FakeWorker()])
    client = TestClient(create_app(service))

    response = client.post(
        "/v1/leases",
        json={
            "task": task_spec.model_dump(mode="json", exclude_computed_fields=True),
            "tool_error_retry_budget": 2,
        },
    )

    assert response.status_code == 201
    assert response.json()["tool_error_retry_budget"] == 2
    assert response.json()["tool_error_retries_used"] == 0
