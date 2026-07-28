"""AgentENV-backed elastic Factorio environment gateway.

Each AgentENV microVM runs one Factorio server and one ordinary factorio-envd
service. The outer gateway owns infrastructure lifecycle and rewrites public
lease identifiers while the inner service remains authoritative for game state,
actions, rewards, and verification.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import aiohttp

from fle.envd.errors import CapacityExhausted, LeaseNotFound, RuntimeBackendError
from fle.envd.models import (
    CapabilityManifest,
    ExecutionResult,
    FactorioTaskSpec,
    HealthStatus,
    Lease,
    LeaseForkResult,
    Observation,
    RuntimeCheckpoint,
    VerificationSnapshot,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentEnvConfig:
    api_url: str
    template_id: str
    api_key: str = "dummy"
    guest_envd_port: int = 8172
    capacity: int = 64
    sandbox_timeout_seconds: int = 1800
    lease_ttl_seconds: int = 86400
    startup_timeout_seconds: float = 180.0
    request_timeout_seconds: float = 240.0
    health_poll_seconds: float = 0.5

    def __post_init__(self) -> None:
        if not self.api_url:
            raise ValueError("AgentENV api_url is required")
        if not self.template_id:
            raise ValueError("AgentENV template_id is required")
        if not 1 <= self.guest_envd_port <= 65535:
            raise ValueError("guest_envd_port must be a valid TCP port")
        if self.capacity < 1:
            raise ValueError("AgentENV capacity must be positive")
        if self.sandbox_timeout_seconds < 1:
            raise ValueError("sandbox_timeout_seconds must be positive")
        if self.lease_ttl_seconds < 1:
            raise ValueError("lease_ttl_seconds must be positive")


class AgentEnvControl(Protocol):
    async def health(self) -> dict[str, Any]: ...

    async def create_sandbox(self, metadata: dict[str, str]) -> dict[str, Any]: ...

    async def delete_sandbox(self, sandbox_id: str) -> None: ...

    async def pause_sandbox(self, sandbox_id: str) -> None: ...

    async def resume_sandbox(self, sandbox_id: str) -> dict[str, Any]: ...

    async def refresh_sandbox(self, sandbox_id: str) -> None: ...

    async def fork_sandbox(
        self, sandbox_id: str, count: int
    ) -> list[dict[str, Any]]: ...

    async def checkpoint_sandbox(
        self, sandbox_id: str, name: str | None = None
    ) -> dict[str, Any]: ...

    async def guest_request(
        self,
        sandbox_id: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any: ...

    async def wait_guest_health(self, sandbox_id: str) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class AgentEnvHTTPClient:
    """Minimal client for the AgentENV control plane and reverse proxy."""

    def __init__(self, config: AgentEnvConfig):
        self.config = config
        self.base_url = config.api_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        *,
        proxy_sandbox_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        session = await self._get_session()
        headers = dict(kwargs.pop("headers", {}))
        headers.setdefault("X-API-Key", self.config.api_key)
        if proxy_sandbox_id is not None:
            headers["x-agentenv-sandbox-id"] = proxy_sandbox_id
            headers["x-agentenv-target-port"] = str(self.config.guest_envd_port)
        async with session.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            **kwargs,
        ) as response:
            if response.status >= 400:
                try:
                    payload = await response.json()
                    detail = payload.get("message", payload.get("detail", payload))
                except (aiohttp.ContentTypeError, ValueError):
                    detail = await response.text()
                raise RuntimeBackendError(
                    f"AgentENV {method} {path} failed ({response.status}): {detail}",
                    status_code=response.status,
                )
            if response.status == 204:
                return None
            return await response.json()

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def create_sandbox(self, metadata: dict[str, str]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/sandboxes",
            json={
                "templateID": self.config.template_id,
                "timeout": self.config.sandbox_timeout_seconds,
                "autoPause": True,
                "autoResume": {"enabled": True},
                "allow_internet_access": False,
                "metadata": metadata,
            },
        )

    async def delete_sandbox(self, sandbox_id: str) -> None:
        await self._request("DELETE", f"/sandboxes/{sandbox_id}")

    async def pause_sandbox(self, sandbox_id: str) -> None:
        await self._request("POST", f"/sandboxes/{sandbox_id}/pause")

    async def resume_sandbox(self, sandbox_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/sandboxes/{sandbox_id}/resume",
            json={"timeout": self.config.sandbox_timeout_seconds},
        )

    async def refresh_sandbox(self, sandbox_id: str) -> None:
        await self._request(
            "POST",
            f"/sandboxes/{sandbox_id}/timeout",
            json={"timeout": self.config.sandbox_timeout_seconds},
        )

    async def fork_sandbox(self, sandbox_id: str, count: int) -> list[dict[str, Any]]:
        result = await self._request(
            "POST",
            f"/sandboxes/{sandbox_id}/fork",
            json={"count": count, "timeout": self.config.sandbox_timeout_seconds},
        )
        if not isinstance(result, list):
            raise RuntimeBackendError("AgentENV fork returned a non-list response")
        return result

    async def checkpoint_sandbox(
        self, sandbox_id: str, name: str | None = None
    ) -> dict[str, Any]:
        payload = {"name": name} if name else {}
        result = await self._request(
            "POST",
            f"/sandboxes/{sandbox_id}/snapshots",
            json=payload,
        )
        if not isinstance(result, dict):
            raise RuntimeBackendError("AgentENV checkpoint returned no metadata")
        return result

    async def guest_request(
        self,
        sandbox_id: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        guest_path = path if path.startswith("/") else f"/{path}"
        return await self._request(
            method,
            f"/proxy{guest_path}",
            proxy_sandbox_id=sandbox_id,
            **kwargs,
        )

    async def wait_guest_health(self, sandbox_id: str) -> dict[str, Any]:
        deadline = (
            asyncio.get_running_loop().time() + self.config.startup_timeout_seconds
        )
        last_error: Exception | None = None
        while asyncio.get_running_loop().time() < deadline:
            try:
                result = await self.guest_request(sandbox_id, "GET", "/v1/health")
                if isinstance(result, dict) and result.get("status") in {
                    "ok",
                    "degraded",
                }:
                    return result
            except (aiohttp.ClientError, RuntimeBackendError) as exc:
                last_error = exc
            await asyncio.sleep(self.config.health_poll_seconds)
        raise RuntimeBackendError(
            f"factorio-envd did not become healthy in sandbox {sandbox_id}: "
            f"{last_error or 'timeout'}",
            status_code=504,
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


@dataclass
class _AgentEnvLeaseRecord:
    lease: Lease
    sandbox_id: str
    inner_lease_id: str
    lock: asyncio.Lock
    paused: bool = False


class AgentEnvEnvironmentGateway:
    """Elastic envd-compatible lease service backed by AgentENV microVMs."""

    def __init__(
        self,
        config: AgentEnvConfig,
        control: AgentEnvControl | None = None,
    ):
        self.config = config
        self.control = control or AgentEnvHTTPClient(config)
        self.capabilities = CapabilityManifest(
            features={
                **CapabilityManifest().features,
                "process_isolation": True,
                "checkpoints": True,
                "clone": True,
                "pause_resume": True,
            }
        )
        self._leases: dict[str, _AgentEnvLeaseRecord] = {}
        self._pending = 0
        self._lock = asyncio.Lock()

    async def _reserve_capacity(self) -> None:
        async with self._lock:
            if len(self._leases) + self._pending >= self.config.capacity:
                raise CapacityExhausted(
                    "AgentENV Factorio sandbox capacity is exhausted"
                )
            self._pending += 1

    async def _finish_reservation(self) -> None:
        async with self._lock:
            self._pending -= 1

    async def _record(self, lease_id: str) -> _AgentEnvLeaseRecord:
        async with self._lock:
            record = self._leases.get(lease_id)
        if record is None:
            raise LeaseNotFound(f"Unknown AgentENV lease: {lease_id}")
        if record.lease.expires_at <= datetime.now(timezone.utc):
            await self.release(lease_id)
            raise LeaseNotFound(f"Expired AgentENV lease: {lease_id}")
        return record

    def _public_lease(
        self,
        *,
        inner: Lease,
        sandbox_id: str,
        lease_id: str | None = None,
        created_at: datetime | None = None,
    ) -> Lease:
        created = created_at or datetime.now(timezone.utc)
        return inner.model_copy(
            update={
                "lease_id": lease_id or str(uuid.uuid4()),
                "worker_id": f"agentenv:{sandbox_id}",
                "created_at": created,
                "expires_at": created
                + timedelta(seconds=self.config.lease_ttl_seconds),
            }
        )

    async def reap_expired(self) -> list[str]:
        now = datetime.now(timezone.utc)
        async with self._lock:
            expired = [
                lease_id
                for lease_id, record in self._leases.items()
                if record.lease.expires_at <= now
            ]
        for lease_id in expired:
            try:
                await self.release(lease_id)
            except RuntimeBackendError:
                pass
        return expired

    async def _touch(self, record: _AgentEnvLeaseRecord) -> None:
        await self.control.refresh_sandbox(record.sandbox_id)
        record.lease.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.config.lease_ttl_seconds
        )

    async def health(self) -> HealthStatus:
        await self.reap_expired()
        await self.control.health()
        async with self._lock:
            active = len(self._leases)
            pending = self._pending
        return HealthStatus(
            status="ok",
            capacity=self.config.capacity,
            available=max(self.config.capacity - active - pending, 0),
            active_leases=active,
            capabilities=self.capabilities,
        )

    async def lease(
        self,
        task: FactorioTaskSpec,
        *,
        tool_error_retry_budget: int = 0,
    ) -> Lease:
        await self.reap_expired()
        await self._reserve_capacity()
        sandbox_id: str | None = None
        try:
            sandbox = await self.control.create_sandbox(
                {
                    "service": "factorio-envd",
                    "task_id": task.task_id,
                    "task_fingerprint": task.fingerprint,
                }
            )
            sandbox_id = str(sandbox["sandboxID"])
            await self.control.wait_guest_health(sandbox_id)
            inner_data = await self.control.guest_request(
                sandbox_id,
                "POST",
                "/v1/leases",
                json={
                    "task": task.model_dump(mode="json", exclude_computed_fields=True),
                    "tool_error_retry_budget": tool_error_retry_budget,
                },
            )
            inner = Lease.model_validate(inner_data)
            public = self._public_lease(inner=inner, sandbox_id=sandbox_id)
            record = _AgentEnvLeaseRecord(
                lease=public,
                sandbox_id=sandbox_id,
                inner_lease_id=inner.lease_id,
                lock=asyncio.Lock(),
            )
            async with self._lock:
                self._leases[public.lease_id] = record
            return public
        except Exception:
            if sandbox_id is not None:
                try:
                    await self.control.delete_sandbox(sandbox_id)
                except Exception:
                    logger.exception(
                        "Failed to delete AgentENV sandbox %s after lease failure",
                        sandbox_id,
                    )
            raise
        finally:
            await self._finish_reservation()

    async def execute(self, lease_id: str, code: str) -> ExecutionResult:
        record = await self._record(lease_id)
        async with record.lock:
            result = ExecutionResult.model_validate(
                await self.control.guest_request(
                    record.sandbox_id,
                    "POST",
                    f"/v1/leases/{record.inner_lease_id}/execute",
                    json={"code": code},
                )
            )
            if result.event.evaluation_retry:
                record.lease.tool_error_retries_used += 1
            await self._touch(record)
            return result.model_copy(update={"lease_id": lease_id})

    async def observe(self, lease_id: str) -> Observation:
        record = await self._record(lease_id)
        async with record.lock:
            result = Observation.model_validate(
                await self.control.guest_request(
                    record.sandbox_id,
                    "GET",
                    f"/v1/leases/{record.inner_lease_id}/observe",
                )
            )
            await self._touch(record)
            return result.model_copy(update={"lease_id": lease_id})

    async def finalize(self, lease_id: str) -> VerificationSnapshot:
        record = await self._record(lease_id)
        async with record.lock:
            result = VerificationSnapshot.model_validate(
                await self.control.guest_request(
                    record.sandbox_id,
                    "POST",
                    f"/v1/leases/{record.inner_lease_id}/finalize",
                )
            )
            await self._touch(record)
            return result.model_copy(update={"lease_id": lease_id})

    async def fork(self, lease_id: str, count: int) -> LeaseForkResult:
        if not 1 <= count <= 100:
            raise ValueError("fork count must be between 1 and 100")
        source = await self._record(lease_id)
        async with self._lock:
            available = self.config.capacity - len(self._leases) - self._pending
            if count > available:
                raise CapacityExhausted(
                    f"Requested {count} branches but only {available} slots are free"
                )
            self._pending += count
        branches: list[Lease] = []
        failures: list[str] = []
        try:
            async with source.lock:
                outcomes = await self.control.fork_sandbox(source.sandbox_id, count)
                await self._touch(source)
            for outcome in outcomes:
                sandbox = outcome.get("sandbox")
                if not sandbox:
                    failures.append(str(outcome.get("error", "unknown fork failure")))
                    continue
                sandbox_id = str(sandbox["sandboxID"])
                try:
                    await self.control.wait_guest_health(sandbox_id)
                    branch = self._public_lease(
                        inner=source.lease.model_copy(
                            update={"lease_id": source.inner_lease_id}
                        ),
                        sandbox_id=sandbox_id,
                    )
                    record = _AgentEnvLeaseRecord(
                        lease=branch,
                        sandbox_id=sandbox_id,
                        inner_lease_id=source.inner_lease_id,
                        lock=asyncio.Lock(),
                    )
                    async with self._lock:
                        self._leases[branch.lease_id] = record
                    branches.append(branch)
                except Exception as exc:
                    failures.append(f"{sandbox_id}: {exc}")
                    logger.exception(
                        "AgentENV branch sandbox %s failed readiness", sandbox_id
                    )
                    try:
                        await self.control.delete_sandbox(sandbox_id)
                    except RuntimeBackendError as cleanup_error:
                        failures.append(f"{sandbox_id} cleanup: {cleanup_error}")
            return LeaseForkResult(
                source_lease_id=lease_id,
                branches=branches,
                failures=failures,
            )
        finally:
            async with self._lock:
                self._pending -= count

    async def pause(self, lease_id: str) -> None:
        record = await self._record(lease_id)
        async with record.lock:
            await self.control.pause_sandbox(record.sandbox_id)
            record.paused = True

    async def resume(self, lease_id: str) -> Lease:
        record = await self._record(lease_id)
        async with record.lock:
            await self.control.resume_sandbox(record.sandbox_id)
            await self.control.wait_guest_health(record.sandbox_id)
            record.paused = False
            record.lease.expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=self.config.lease_ttl_seconds
            )
            return record.lease

    async def checkpoint(
        self, lease_id: str, name: str | None = None
    ) -> RuntimeCheckpoint:
        record = await self._record(lease_id)
        async with record.lock:
            result = await self.control.checkpoint_sandbox(record.sandbox_id, name)
        checkpoint_id = result.get("snapshotID") or result.get("templateID")
        if not checkpoint_id:
            raise RuntimeBackendError(
                "AgentENV checkpoint response did not contain snapshotID or templateID"
            )
        return RuntimeCheckpoint(
            lease_id=lease_id,
            checkpoint_id=str(checkpoint_id),
            runtime_backend="agentenv",
        )

    async def release(self, lease_id: str) -> bool:
        async with self._lock:
            record = self._leases.pop(lease_id, None)
        if record is None:
            return False
        async with record.lock:
            try:
                await self.control.guest_request(
                    record.sandbox_id,
                    "DELETE",
                    f"/v1/leases/{record.inner_lease_id}",
                )
            except RuntimeBackendError:
                pass
            try:
                await self.control.delete_sandbox(record.sandbox_id)
            except RuntimeBackendError as exc:
                if exc.status_code != 404:
                    raise
        return True

    async def close(self) -> None:
        async with self._lock:
            lease_ids = list(self._leases)
        for lease_id in lease_ids:
            try:
                await self.release(lease_id)
            except Exception:
                logger.exception("Failed to release AgentENV lease %s", lease_id)
        await self.control.close()
