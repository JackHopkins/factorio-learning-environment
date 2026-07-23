from __future__ import annotations

from fastapi import FastAPI, Response
from pydantic import BaseModel, ConfigDict

from fle.envd.errors import (
    CapacityExhausted,
    EnvironmentServiceError,
    InterventionLimitReached,
    LeaseFinalized,
    LeaseNotFound,
)
from fle.envd.models import FactorioTaskSpec
from fle.envd.service import EnvironmentService


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeaseRequest(RequestModel):
    task: FactorioTaskSpec


class ExecuteRequest(RequestModel):
    code: str


def create_app(service: EnvironmentService) -> FastAPI:
    app = FastAPI(
        title="Factorio Environment Service",
        version=service.capabilities.protocol_version,
    )

    @app.exception_handler(CapacityExhausted)
    async def capacity_error(_, exc: CapacityExhausted):
        return _error(503, str(exc))

    @app.exception_handler(LeaseNotFound)
    async def lease_error(_, exc: LeaseNotFound):
        return _error(404, str(exc))

    @app.exception_handler(InterventionLimitReached)
    async def limit_error(_, exc: InterventionLimitReached):
        return _error(409, str(exc))

    @app.exception_handler(LeaseFinalized)
    async def finalized_error(_, exc: LeaseFinalized):
        return _error(409, str(exc))

    @app.exception_handler(EnvironmentServiceError)
    async def service_error(_, exc: EnvironmentServiceError):
        return _error(400, str(exc))

    @app.get("/v1/health")
    def health():
        return service.health()

    @app.post("/v1/leases", status_code=201)
    def lease(request: LeaseRequest):
        return service.lease(request.task).model_dump(
            mode="json", exclude_computed_fields=True
        )

    @app.delete("/v1/leases/{lease_id}", status_code=204)
    def release(lease_id: str):
        service.release(lease_id)
        return Response(status_code=204)

    @app.post("/v1/leases/{lease_id}/execute")
    def execute(lease_id: str, request: ExecuteRequest):
        return service.execute(lease_id, request.code)

    @app.get("/v1/leases/{lease_id}/observe")
    def observe(lease_id: str):
        return service.observe(lease_id)

    @app.post("/v1/leases/{lease_id}/finalize")
    def finalize(lease_id: str):
        return service.finalize(lease_id)

    return app


def _error(status_code: int, detail: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content={"detail": detail})


def build_live_service(
    tcp_ports: list[int],
    address: str = "localhost",
    lease_ttl_seconds: int = 900,
) -> EnvironmentService:
    from fle.envd.backend import FLEWorker

    workers = [
        FLEWorker.connect(f"factorio-{index}", port, address)
        for index, port in enumerate(tcp_ports)
    ]
    return EnvironmentService(workers, lease_ttl_seconds=lease_ttl_seconds)
