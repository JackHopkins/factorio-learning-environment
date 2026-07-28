from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fle.envd.backend import FactorioWorker
from fle.envd.errors import (
    CapacityExhausted,
    InterventionLimitReached,
    LeaseFinalized,
    LeaseNotFound,
)
from fle.envd.models import (
    ActionEvent,
    CapabilityManifest,
    ExecutionResult,
    FactorioTaskSpec,
    HealthStatus,
    Lease,
    Observation,
    VerificationSnapshot,
    VerifierEvent,
)
from fle.envd.program_policy import ProgramPolicyViolation, validate_program


@dataclass
class _LeaseRecord:
    lease: Lease
    worker: FactorioWorker
    events: list[ActionEvent] = field(default_factory=list)
    snapshot: VerificationSnapshot | None = None
    terminal_reason: str | None = None
    released: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)


class EnvironmentService:
    """Thread-safe lease manager over a fixed warm pool of Factorio workers."""

    def __init__(
        self,
        workers: list[FactorioWorker],
        lease_ttl_seconds: int = 900,
        capabilities: CapabilityManifest | None = None,
    ):
        if not workers:
            raise ValueError("EnvironmentService requires at least one worker")
        if lease_ttl_seconds < 1:
            raise ValueError("lease_ttl_seconds must be positive")
        worker_ids = [worker.worker_id for worker in workers]
        if len(worker_ids) != len(set(worker_ids)):
            raise ValueError("Factorio worker ids must be unique")

        self._workers = {worker.worker_id: worker for worker in workers}
        self._leases: dict[str, _LeaseRecord] = {}
        self._busy_workers: set[str] = set()
        self._lease_ttl = timedelta(seconds=lease_ttl_seconds)
        self._lock = threading.RLock()
        self.capabilities = capabilities or CapabilityManifest()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def reap_expired(self) -> list[str]:
        now = self._now()
        with self._lock:
            expired = [
                lease_id
                for lease_id, record in self._leases.items()
                if record.lease.expires_at <= now
            ]
        for lease_id in expired:
            self.release(lease_id)
        return expired

    def health(self) -> HealthStatus:
        self.reap_expired()
        with self._lock:
            available = len(self._workers) - len(self._busy_workers)
            return HealthStatus(
                status="ok" if available or self._leases else "degraded",
                capacity=len(self._workers),
                available=available,
                active_leases=len(self._leases),
                capabilities=self.capabilities,
            )

    def lease(
        self,
        task: FactorioTaskSpec,
        *,
        tool_error_retry_budget: int = 0,
    ) -> Lease:
        if tool_error_retry_budget < 0:
            raise ValueError("tool_error_retry_budget cannot be negative")
        self.reap_expired()
        with self._lock:
            worker = next(
                (
                    candidate
                    for worker_id, candidate in self._workers.items()
                    if worker_id not in self._busy_workers
                ),
                None,
            )
            if worker is None:
                raise CapacityExhausted("No Factorio workers are currently available")
            self._busy_workers.add(worker.worker_id)

        try:
            initial_state_hash = worker.start_task(task)
        except Exception:
            with self._lock:
                self._busy_workers.discard(worker.worker_id)
            raise

        created = self._now()
        lease = Lease(
            lease_id=str(uuid.uuid4()),
            worker_id=worker.worker_id,
            task=task,
            initial_state_hash=initial_state_hash,
            created_at=created,
            expires_at=created + self._lease_ttl,
            tool_error_retry_budget=tool_error_retry_budget,
        )
        with self._lock:
            self._leases[lease.lease_id] = _LeaseRecord(lease=lease, worker=worker)
        return lease

    def _record(self, lease_id: str) -> _LeaseRecord:
        self.reap_expired()
        with self._lock:
            record = self._leases.get(lease_id)
        if record is None:
            raise LeaseNotFound(f"Unknown or expired lease: {lease_id}")
        return record

    def _renew(self, record: _LeaseRecord) -> None:
        record.lease.expires_at = self._now() + self._lease_ttl

    def execute(self, lease_id: str, code: str) -> ExecutionResult:
        if not code.strip():
            raise ValueError("code must not be empty")
        record = self._record(lease_id)
        with record.lock:
            if record.released:
                raise LeaseNotFound(f"Released lease: {lease_id}")
            if record.snapshot is not None:
                raise LeaseFinalized(f"Lease is already finalized: {lease_id}")
            if record.terminal_reason is not None:
                raise LeaseFinalized(
                    "Lease reached terminal environment state: "
                    f"{record.terminal_reason}"
                )
            scored_interventions = sum(
                not event.evaluation_retry for event in record.events
            )
            if scored_interventions >= record.lease.task.max_interventions:
                raise InterventionLimitReached(
                    "Task allows at most "
                    f"{record.lease.task.max_interventions} scored interventions "
                    "plus its configured tool-error retries"
                )
            sequence = len(record.events) + 1
            try:
                validate_program(code)
            except ProgramPolicyViolation as exc:
                # Policy rejections are evaluation outcomes, not malformed HTTP
                # requests. Preserve them in the trajectory so retry budgets,
                # invalid-action rewards, and failure analysis remain honest.
                started_at = self._now()
                started = time.perf_counter()
                observation = record.worker.observe(lease_id)
                violation = str(exc)
                event = ActionEvent(
                    sequence=sequence,
                    code_sha256=sha256(code.encode("utf-8")).hexdigest(),
                    started_at=started_at,
                    duration_seconds=time.perf_counter() - started,
                    error=True,
                    result=f"ProgramPolicyViolation: {violation}",
                    ticks=observation.ticks,
                    policy_violations=[violation],
                )
                result = ExecutionResult(
                    lease_id=lease_id,
                    event=event,
                    production_score=observation.production_score,
                    automated_production_score=observation.automated_production_score,
                    state_hash=observation.state_hash,
                    events=[
                        VerifierEvent(
                            event_id=f"action:{sequence}",
                            kind="invalid_action",
                            tick=observation.ticks,
                            source="environment",
                            payload={
                                "sequence": sequence,
                                "code_sha256": event.code_sha256,
                                "policy_violations": [violation],
                            },
                            reward_channels={"invalid_action": -1.0},
                        )
                    ],
                )
            else:
                result = record.worker.execute(lease_id, code, sequence=sequence)
            if (
                result.event.error
                and record.lease.tool_error_retries_used
                < record.lease.tool_error_retry_budget
            ):
                result.event.evaluation_retry = True
                record.lease.tool_error_retries_used += 1
            record.events.append(result.event)
            record.terminal_reason = result.terminal_reason
            self._renew(record)
            return result

    def observe(self, lease_id: str) -> Observation:
        record = self._record(lease_id)
        with record.lock:
            if record.released:
                raise LeaseNotFound(f"Released lease: {lease_id}")
            observation = record.worker.observe(lease_id)
            self._renew(record)
            return observation

    def finalize(self, lease_id: str) -> VerificationSnapshot:
        record = self._record(lease_id)
        with record.lock:
            if record.released:
                raise LeaseNotFound(f"Released lease: {lease_id}")
            if record.snapshot is not None:
                return record.snapshot
            record.snapshot = record.worker.finalize(
                lease_id, record.lease.task, list(record.events)
            )
            self._renew(record)
            return record.snapshot

    def release(self, lease_id: str) -> bool:
        with self._lock:
            record = self._leases.pop(lease_id, None)
            if record is None:
                return False
        with record.lock:
            record.released = True
            record.worker.release()
        with self._lock:
            self._busy_workers.discard(record.worker.worker_id)
        return True

    def close(self) -> None:
        with self._lock:
            lease_ids = list(self._leases)
        for lease_id in lease_ids:
            self.release(lease_id)
