from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from pydantic import BaseModel, ConfigDict, Field

from fle.envd.errors import (
    CapacityExhausted,
    EnvironmentServiceError,
    InterventionLimitReached,
    LeaseFinalized,
    LeaseNotFound,
    RuntimeBackendError,
)
from fle.envd.models import FactorioTaskSpec
from fle.envd.service import EnvironmentService


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeaseRequest(RequestModel):
    task: FactorioTaskSpec
    tool_error_retry_budget: int = Field(default=0, ge=0, le=20)


class ExecuteRequest(RequestModel):
    code: str


class ForkRequest(RequestModel):
    count: int = Field(default=1, ge=1, le=100)


class CheckpointRequest(RequestModel):
    name: str | None = Field(default=None, max_length=128)


def _register_error_handlers(app: FastAPI) -> None:
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

    @app.exception_handler(RuntimeBackendError)
    async def runtime_error(_, exc: RuntimeBackendError):
        # Preserve actionable upstream 4xx responses, but expose infrastructure
        # failures as a gateway error rather than an internal stack trace.
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        return _error(status, str(exc))

    @app.exception_handler(EnvironmentServiceError)
    async def service_error(_, exc: EnvironmentServiceError):
        return _error(400, str(exc))


def create_app(service: EnvironmentService) -> FastAPI:
    app = FastAPI(
        title="Factorio Environment Service",
        version=service.capabilities.protocol_version,
    )

    _register_error_handlers(app)

    @app.get("/v1/health")
    def health():
        return service.health()

    @app.post("/v1/leases", status_code=201)
    def lease(request: LeaseRequest):
        return service.lease(
            request.task,
            tool_error_retry_budget=request.tool_error_retry_budget,
        ).model_dump(mode="json", exclude_computed_fields=True)

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


def create_agentenv_app(service) -> FastAPI:
    """Create the public envd gateway backed by elastic AgentENV sandboxes."""

    @asynccontextmanager
    async def lifespan(_app):
        try:
            yield
        finally:
            await service.close()

    app = FastAPI(
        title="Factorio Environment Service (AgentENV)",
        version=service.capabilities.protocol_version,
        lifespan=lifespan,
    )
    _register_error_handlers(app)

    @app.get("/v1/health")
    async def health():
        return await service.health()

    @app.post("/v1/leases", status_code=201)
    async def lease(request: LeaseRequest):
        result = await service.lease(
            request.task,
            tool_error_retry_budget=request.tool_error_retry_budget,
        )
        return result.model_dump(mode="json", exclude_computed_fields=True)

    @app.delete("/v1/leases/{lease_id}", status_code=204)
    async def release(lease_id: str):
        await service.release(lease_id)
        return Response(status_code=204)

    @app.post("/v1/leases/{lease_id}/execute")
    async def execute(lease_id: str, request: ExecuteRequest):
        return await service.execute(lease_id, request.code)

    @app.get("/v1/leases/{lease_id}/observe")
    async def observe(lease_id: str):
        return await service.observe(lease_id)

    @app.post("/v1/leases/{lease_id}/finalize")
    async def finalize(lease_id: str):
        return await service.finalize(lease_id)

    @app.post("/v1/leases/{lease_id}/fork", status_code=201)
    async def fork(lease_id: str, request: ForkRequest):
        return await service.fork(lease_id, request.count)

    @app.post("/v1/leases/{lease_id}/pause", status_code=204)
    async def pause(lease_id: str):
        await service.pause(lease_id)
        return Response(status_code=204)

    @app.post("/v1/leases/{lease_id}/resume")
    async def resume(lease_id: str):
        return await service.resume(lease_id)

    @app.post("/v1/leases/{lease_id}/checkpoints", status_code=201)
    async def checkpoint(lease_id: str, request: CheckpointRequest):
        return await service.checkpoint(lease_id, request.name)

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
