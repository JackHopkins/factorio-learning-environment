from __future__ import annotations

from types import TracebackType
from typing import Self

import aiohttp

from fle.envd.models import (
    ExecutionResult,
    FactorioTaskSpec,
    HealthStatus,
    Lease,
    LeaseForkResult,
    Observation,
    RuntimeCheckpoint,
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

    async def execute(self, lease_id: str, code: str) -> ExecutionResult:
        data = await self._request(
            "POST", f"/v1/leases/{lease_id}/execute", json={"code": code}
        )
        return ExecutionResult.model_validate(data)

    async def observe(self, lease_id: str) -> Observation:
        data = await self._request("GET", f"/v1/leases/{lease_id}/observe")
        return Observation.model_validate(data)

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

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
