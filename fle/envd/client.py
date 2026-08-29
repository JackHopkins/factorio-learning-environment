from __future__ import annotations

import asyncio
import json
import sys
from types import TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:  # pragma: no cover - 3.10 support
    from typing_extensions import Self

import aiohttp

from fle.envd.models import (
    ActiveContractState,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ContractEpochSpec,
    ContractSessionState,
    ContractSessionSummary,
    ExecutionResult,
    FactorioTaskSpec,
    HealthStatus,
    Lease,
    LeaseForkResult,
    MemoryEntry,
    MemoryListResponse,
    MemoryMutationResponse,
    MemorySearchResponse,
    MemoryTraceResponse,
    Observation,
    RuntimeCheckpoint,
    ThroughputCheckResult,
    VerificationSnapshot,
)


class EnvironmentClientError(RuntimeError):
    pass


class HTTPEnvironmentClient:
    def __init__(self, base_url: str, timeout_seconds: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        await self._get_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def _request(self, method: str, path: str, **kwargs):
        session = await self._get_session()
        async with session.request(
            method, f"{self.base_url}{path}", **kwargs
        ) as response:
            if response.status >= 400:
                try:
                    body = await response.json()
                    detail = body.get("detail", body)
                except Exception:
                    detail = await response.text()
                raise EnvironmentClientError(
                    f"envd {method} {path} failed ({response.status}): {detail}"
                )
            if response.status == 204:
                return None
            return await response.json()

    async def health(self) -> HealthStatus:
        return HealthStatus.model_validate(await self._request("GET", "/v1/health"))

    async def lease(
        self,
        task: FactorioTaskSpec,
        *,
        tool_error_retry_budget: int = 0,
    ) -> Lease:
        data = await self._request(
            "POST",
            "/v1/leases",
            json={
                "task": task.model_dump(mode="json", exclude_computed_fields=True),
                "tool_error_retry_budget": tool_error_retry_budget,
            },
        )
        return Lease.model_validate(data)

    async def execute(
        self,
        lease_id: str,
        code: str,
        *,
        request_id: str | None = None,
    ) -> ExecutionResult:
        attempts = 2 if request_id is not None else 1
        for attempt in range(attempts):
            try:
                data = await self._request(
                    "POST",
                    f"/v1/leases/{lease_id}/execute",
                    json={"code": code, "request_id": request_id},
                )
                break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt + 1 >= attempts:
                    raise
        return ExecutionResult.model_validate(data)

    async def observe(
        self,
        lease_id: str,
        *,
        cursor: str | None = None,
        force_keyframe: bool = False,
    ) -> Observation:
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if force_keyframe:
            params["keyframe"] = "true"
        data = await self._request(
            "GET", f"/v1/leases/{lease_id}/observe", params=params or None
        )
        return Observation.model_validate(data)

    async def query_state(
        self,
        lease_id: str,
        *,
        kind: str,
        item: str | None = None,
        window_seconds: int | None = None,
        since_revision: int | None = None,
        entity_type: str | None = None,
        area: dict[str, object] | None = None,
        changed_since: int | None = None,
        limit: int = 32,
    ) -> dict[str, object]:
        params = {
            key: value
            for key, value in {
                "kind": kind,
                "item": item,
                "window_seconds": window_seconds,
                "since_revision": since_revision,
                "entity_type": entity_type,
                "area": json.dumps(area, separators=(",", ":"))
                if area is not None
                else None,
                "changed_since": changed_since,
                "limit": limit,
            }.items()
            if value is not None
        }
        return await self._request(
            "GET", f"/v1/leases/{lease_id}/state/query", params=params
        )

    async def check_contract_throughput(
        self,
        lease_id: str,
        *,
        authoritative: bool = False,
        request_id: str | None = None,
    ) -> ThroughputCheckResult:
        endpoint = (
            "contract/qualify-throughput" if authoritative else "throughput-check"
        )
        data = await self._request(
            "POST",
            f"/v1/leases/{lease_id}/{endpoint}",
            json={"request_id": request_id},
        )
        return ThroughputCheckResult.model_validate(data)

    # -- model-managed session memory ---------------------------------------

    async def memory_list(
        self,
        lease_id: str,
        *,
        prefix: str = "",
        limit: int = 50,
        cursor: str | None = None,
    ) -> MemoryListResponse:
        params = {"prefix": prefix, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._request("GET", f"/v1/leases/{lease_id}/memory", params=params)
        return MemoryListResponse.model_validate(data)

    async def memory_read(self, lease_id: str, key: str) -> MemoryEntry:
        data = await self._request(
            "GET", f"/v1/leases/{lease_id}/memory/read", params={"key": key}
        )
        return MemoryEntry.model_validate(data)

    async def memory_write(
        self,
        lease_id: str,
        key: str,
        content: str,
        *,
        expected_revision: int | None = None,
    ) -> MemoryMutationResponse:
        data = await self._request(
            "POST",
            f"/v1/leases/{lease_id}/memory/write",
            json={
                "key": key,
                "content": content,
                "expected_revision": expected_revision,
            },
        )
        return MemoryMutationResponse.model_validate(data)

    async def memory_delete(
        self,
        lease_id: str,
        key: str,
        *,
        expected_revision: int | None = None,
    ) -> MemoryMutationResponse:
        data = await self._request(
            "POST",
            f"/v1/leases/{lease_id}/memory/delete",
            json={"key": key, "expected_revision": expected_revision},
        )
        return MemoryMutationResponse.model_validate(data)

    async def memory_search(
        self,
        lease_id: str,
        query: str,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> MemorySearchResponse:
        params = {"query": query, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._request(
            "GET", f"/v1/leases/{lease_id}/memory/search", params=params
        )
        return MemorySearchResponse.model_validate(data)

    async def memory_trace(
        self,
        lease_id: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> MemoryTraceResponse:
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._request(
            "GET", f"/v1/leases/{lease_id}/memory/trace", params=params
        )
        return MemoryTraceResponse.model_validate(data)

    async def finalize(self, lease_id: str) -> VerificationSnapshot:
        data = await self._request("POST", f"/v1/leases/{lease_id}/finalize")
        return VerificationSnapshot.model_validate(data)

    async def release(self, lease_id: str) -> None:
        await self._request("DELETE", f"/v1/leases/{lease_id}")

    async def fork(self, lease_id: str, count: int = 1) -> LeaseForkResult:
        data = await self._request(
            "POST", f"/v1/leases/{lease_id}/fork", json={"count": count}
        )
        return LeaseForkResult.model_validate(data)

    async def pause(self, lease_id: str) -> None:
        await self._request("POST", f"/v1/leases/{lease_id}/pause")

    async def resume(self, lease_id: str) -> Lease:
        data = await self._request("POST", f"/v1/leases/{lease_id}/resume")
        return Lease.model_validate(data)

    async def checkpoint(
        self, lease_id: str, name: str | None = None
    ) -> RuntimeCheckpoint:
        data = await self._request(
            "POST",
            f"/v1/leases/{lease_id}/checkpoints",
            json={"name": name},
        )
        return RuntimeCheckpoint.model_validate(data)

    # -- adaptive contract benchmark (privileged HTTP) -----------------------

    async def capture_contract_context(
        self, lease_id: str, session_id: str, epoch_index: int
    ) -> ContractContextSnapshot:
        data = await self._request(
            "GET",
            f"/v1/leases/{lease_id}/contract/context"
            f"?session_id={session_id}&epoch_index={epoch_index}",
        )
        return ContractContextSnapshot.model_validate(data)

    async def begin_contract_epoch(
        self,
        lease_id: str,
        spec: ContractEpochSpec,
        *,
        request_id: str | None = None,
    ) -> ActiveContractState:
        data = await self._request(
            "POST",
            f"/v1/leases/{lease_id}/contract/begin",
            json={
                "spec": spec.model_dump(mode="json"),
                "request_id": request_id,
            },
        )
        return ActiveContractState.model_validate(data)

    async def finalize_contract_epoch(
        self,
        lease_id: str,
        epoch_index: int,
        commitment_hash: str,
        *,
        abandon: bool = False,
        infrastructure_interrupt: bool = False,
        request_id: str | None = None,
    ) -> ContractEpochOutcome:
        data = await self._request(
            "POST",
            f"/v1/leases/{lease_id}/contract/finalize",
            json={
                "epoch_index": epoch_index,
                "commitment_hash": commitment_hash,
                "abandon": abandon,
                "infrastructure_interrupt": infrastructure_interrupt,
                "request_id": request_id,
            },
        )
        return ContractEpochOutcome.model_validate(data)

    async def get_contract_session_state(self, lease_id: str) -> ContractSessionState:
        data = await self._request("GET", f"/v1/leases/{lease_id}/contract/state")
        return ContractSessionState.model_validate(data)

    async def finalize_contract_session(self, lease_id: str) -> ContractSessionSummary:
        data = await self._request(
            "POST", f"/v1/leases/{lease_id}/contract/session-finalize"
        )
        return ContractSessionSummary.model_validate(data)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
