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
    assert health.json()["capabilities"]["protocol_version"] == "0.2.1"

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
