from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from fle.envd.errors import (
    CapacityExhausted,
    CommitmentMismatch,
    EnvironmentServiceError,
    IdempotencyConflict,
    InterventionLimitReached,
    LeaseFinalized,
    LeaseNotFound,
    MemoryConflict,
    MemoryLimitExceeded,
    MemoryNotFound,
    RuntimeBackendError,
)
from fle.envd.models import (
    ContractEpochSpec,
    FactorioTaskSpec,
)
from fle.envd.service import EnvironmentService


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeaseRequest(RequestModel):
    task: FactorioTaskSpec
    tool_error_retry_budget: int = Field(default=0, ge=0, le=20)


class ExecuteRequest(RequestModel):
    code: str
    request_id: str | None = Field(default=None, min_length=1, max_length=128)


class ForkRequest(RequestModel):
    count: int = Field(default=1, ge=1, le=100)


class CheckpointRequest(RequestModel):
    name: str | None = Field(default=None, max_length=128)


class ContractEpochBeginRequest(RequestModel):
    """Privileged benchmark payload; never part of the agent tool surface."""

    spec: ContractEpochSpec
    request_id: str | None = None


class ContractEpochFinalizeRequest(RequestModel):
    epoch_index: int = Field(ge=0)
    commitment_hash: str
    abandon: bool = False
    infrastructure_interrupt: bool = False
    request_id: str | None = None


class ThroughputCheckRequest(RequestModel):
    request_id: str | None = Field(default=None, min_length=1, max_length=128)


class MemoryWriteRequest(RequestModel):
    key: str = Field(min_length=1, max_length=256)
    content: str
    expected_revision: int | None = Field(default=None, ge=0)


class MemoryDeleteRequest(RequestModel):
    key: str = Field(min_length=1, max_length=256)
    expected_revision: int | None = Field(default=None, ge=0)


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

    @app.exception_handler(CommitmentMismatch)
    async def commitment_error(_, exc: CommitmentMismatch):
        return _error(409, str(exc))

    @app.exception_handler(IdempotencyConflict)
    async def idempotency_error(_, exc: IdempotencyConflict):
        return _error(409, str(exc))

    @app.exception_handler(MemoryConflict)
    async def memory_conflict_error(_, exc: MemoryConflict):
        return _error(409, str(exc))

    @app.exception_handler(MemoryNotFound)
    async def memory_not_found_error(_, exc: MemoryNotFound):
        return _error(404, str(exc))

    @app.exception_handler(MemoryLimitExceeded)
    async def memory_limit_error(_, exc: MemoryLimitExceeded):
        return _error(413, str(exc))

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
        return service.execute(
            lease_id,
            request.code,
            request_id=request.request_id,
        )

    @app.get("/v1/leases/{lease_id}/observe")
    def observe(
        lease_id: str,
        cursor: str | None = None,
        keyframe: bool = False,
    ):
        return service.observe(
            lease_id,
            cursor=cursor,
            force_keyframe=keyframe,
        )

    @app.get("/v1/leases/{lease_id}/state/query")
    def query_state(
        lease_id: str,
        kind: str,
        item: str | None = None,
        window_seconds: int | None = None,
        since_revision: int | None = None,
        entity_type: str | None = None,
        area: str | None = None,
        changed_since: int | None = None,
        limit: int = 32,
    ):
        area_payload: dict[str, Any] | None = None
        if area:
            import json

            try:
                decoded = json.loads(area)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="area must be a JSON object with x, y, radius",
                ) from exc
            if not isinstance(decoded, dict):
                raise HTTPException(
                    status_code=422,
                    detail="area must be a JSON object with x, y, radius",
                )
            area_payload = decoded
        try:
            return service.query_state(
                lease_id,
                kind=kind,
                item=item,
                window_seconds=window_seconds,
                since_revision=since_revision,
                entity_type=entity_type,
                area=area_payload,
                changed_since=changed_since,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/v1/leases/{lease_id}/throughput-check")
    def throughput_check(lease_id: str, request: ThroughputCheckRequest):
        return service.check_contract_throughput(
            lease_id, request_id=request.request_id
        ).model_dump(mode="json")

    # -- model-managed memory; lease-scoped and never a host filesystem API --

    @app.get("/v1/leases/{lease_id}/memory")
    def memory_list(lease_id: str, prefix: str = "", limit: int = 50, cursor: str | None = None):
        return service.memory_list(lease_id, prefix=prefix, limit=limit, cursor=cursor)

    @app.get("/v1/leases/{lease_id}/memory/read")
    def memory_read(lease_id: str, key: str):
        return service.memory_read(lease_id, key)

    @app.post("/v1/leases/{lease_id}/memory/write")
    def memory_write(lease_id: str, request: MemoryWriteRequest):
        return service.memory_write(
            lease_id,
            request.key,
            request.content,
            expected_revision=request.expected_revision,
        )

    @app.post("/v1/leases/{lease_id}/memory/delete")
    def memory_delete(lease_id: str, request: MemoryDeleteRequest):
        return service.memory_delete(
            lease_id, request.key, expected_revision=request.expected_revision
        )

    @app.get("/v1/leases/{lease_id}/memory/search")
    def memory_search(lease_id: str, query: str, limit: int = 20, cursor: str | None = None):
        return service.memory_search(lease_id, query, limit=limit, cursor=cursor)

    @app.get("/v1/leases/{lease_id}/memory/trace")
    def memory_trace(lease_id: str, limit: int = 100, cursor: str | None = None):
        return service.memory_trace(lease_id, limit=limit, cursor=cursor)

    @app.post("/v1/leases/{lease_id}/finalize")
    def finalize(lease_id: str):
        return service.finalize(lease_id)

    # -- adaptive contract benchmark (privileged HTTP, never agent tools) --

    @app.get("/v1/leases/{lease_id}/contract/context")
    def contract_context(lease_id: str, session_id: str, epoch_index: int):
        return service.capture_contract_context(lease_id, session_id, epoch_index)

    @app.post("/v1/leases/{lease_id}/contract/begin", status_code=201)
    def contract_begin(lease_id: str, request: ContractEpochBeginRequest):
        return service.begin_contract_epoch(
            lease_id,
            request.spec,
            request_id=request.request_id,
        ).model_dump(mode="json")

    @app.post("/v1/leases/{lease_id}/contract/finalize")
    def contract_finalize(lease_id: str, request: ContractEpochFinalizeRequest):
        return service.finalize_contract_epoch(
            lease_id,
            request.epoch_index,
            request.commitment_hash,
            abandon=request.abandon,
            infrastructure_interrupt=request.infrastructure_interrupt,
            request_id=request.request_id,
        ).model_dump(mode="json")

    @app.post("/v1/leases/{lease_id}/contract/qualify-throughput")
    def contract_qualify_throughput(
        lease_id: str, request: ThroughputCheckRequest
    ):
        return service.check_contract_throughput(
            lease_id,
            authoritative=True,
            request_id=request.request_id,
        ).model_dump(mode="json")

    @app.get("/v1/leases/{lease_id}/contract/state")
    def contract_state(lease_id: str):
        return service.get_contract_session_state(lease_id).model_dump(mode="json")

    @app.post("/v1/leases/{lease_id}/contract/session-finalize")
    def contract_session_finalize(lease_id: str):
        return service.finalize_contract_session(lease_id).model_dump(mode="json")

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
        return await service.execute(
            lease_id,
            request.code,
            request_id=request.request_id,
        )

    @app.get("/v1/leases/{lease_id}/observe")
    async def observe(
        lease_id: str,
        cursor: str | None = None,
        keyframe: bool = False,
    ):
        return await service.observe(
            lease_id,
            cursor=cursor,
            force_keyframe=keyframe,
        )

    @app.get("/v1/leases/{lease_id}/state/query")
    async def query_state(
        lease_id: str,
        kind: str,
        item: str | None = None,
        window_seconds: int | None = None,
        since_revision: int | None = None,
        entity_type: str | None = None,
        area: str | None = None,
        changed_since: int | None = None,
        limit: int = 32,
    ):
        area_payload: dict[str, Any] | None = None
        if area:
            import json

            try:
                decoded = json.loads(area)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="area must be a JSON object with x, y, radius",
                ) from exc
            if not isinstance(decoded, dict):
                raise HTTPException(
                    status_code=422,
                    detail="area must be a JSON object with x, y, radius",
                )
            area_payload = decoded
        try:
            return await service.query_state(
                lease_id,
                kind=kind,
                item=item,
                window_seconds=window_seconds,
                since_revision=since_revision,
                entity_type=entity_type,
                area=area_payload,
                changed_since=changed_since,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/leases/{lease_id}/memory")
    async def memory_list(lease_id: str, prefix: str = "", limit: int = 50, cursor: str | None = None):
        return await service.memory_list(lease_id, prefix=prefix, limit=limit, cursor=cursor)

    @app.get("/v1/leases/{lease_id}/memory/read")
    async def memory_read(lease_id: str, key: str):
        return await service.memory_read(lease_id, key)

    @app.post("/v1/leases/{lease_id}/memory/write")
    async def memory_write(lease_id: str, request: MemoryWriteRequest):
        return await service.memory_write(
            lease_id,
            request.key,
            request.content,
            expected_revision=request.expected_revision,
        )

    @app.post("/v1/leases/{lease_id}/memory/delete")
    async def memory_delete(lease_id: str, request: MemoryDeleteRequest):
        return await service.memory_delete(
            lease_id, request.key, expected_revision=request.expected_revision
        )

    @app.get("/v1/leases/{lease_id}/memory/search")
    async def memory_search(lease_id: str, query: str, limit: int = 20, cursor: str | None = None):
        return await service.memory_search(lease_id, query, limit=limit, cursor=cursor)

    @app.get("/v1/leases/{lease_id}/memory/trace")
    async def memory_trace(lease_id: str, limit: int = 100, cursor: str | None = None):
        return await service.memory_trace(lease_id, limit=limit, cursor=cursor)

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
    audit_tcp_ports: list[int] | None = None,
) -> EnvironmentService:
    from fle.envd.backend import FLEWorker

    workers = [
        FLEWorker.connect(f"factorio-{index}", port, address)
        for index, port in enumerate(tcp_ports)
    ]
    audit_workers = [
        FLEWorker.connect(f"factorio-audit-{index}", port, address)
        for index, port in enumerate(audit_tcp_ports or [])
    ]
    return EnvironmentService(
        workers,
        lease_ttl_seconds=lease_ttl_seconds,
        audit_workers=audit_workers,
    )
