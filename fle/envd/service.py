from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

from fle.envd.backend import FactorioWorker
from fle.envd.errors import (
    CapacityExhausted,
    CommitmentMismatch,
    IdempotencyConflict,
    InterventionLimitReached,
    LeaseFinalized,
    LeaseNotFound,
    MemoryConflict,
    MemoryLimitExceeded,
    MemoryNotFound,
)
from fle.envd.models import (
    ActionEvent,
    ActiveContractState,
    CapabilityManifest,
    ContractEpochOutcome,
    ContractEpochSpec,
    ContractSessionState,
    ContractSessionSummary,
    ExecutionResult,
    FactorioTaskSpec,
    HealthStatus,
    Lease,
    Observation,
    VerificationSnapshot,
    VerifierEvent,
)
from fle.envd.memory import SessionMemory
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
    execute_request_cache: dict[str, tuple[str, ExecutionResult]] = field(
        default_factory=dict
    )
    # Adaptive contract session bookkeeping (section 14).  Idempotency caches
    # replay identical requests without re-touching the simulation.
    active_commitment_hash: str | None = None
    epoch_request_cache: dict[tuple[str, str], Any] = field(default_factory=dict)
    session_summary: ContractSessionSummary | None = None
    # Model-managed memory is lease-scoped so it survives MCP subprocess
    # restarts while remaining isolated from every other evaluation session.
    memory: SessionMemory = field(default_factory=SessionMemory)


class EnvironmentService:
    """Thread-safe lease manager over a fixed warm pool of Factorio workers."""

    def __init__(
        self,
        workers: list[FactorioWorker],
        lease_ttl_seconds: int = 900,
        capabilities: CapabilityManifest | None = None,
        audit_workers: list[FactorioWorker] | None = None,
    ):
        if not workers:
            raise ValueError("EnvironmentService requires at least one worker")
        if lease_ttl_seconds < 1:
            raise ValueError("lease_ttl_seconds must be positive")
        worker_ids = [worker.worker_id for worker in workers]
        if len(worker_ids) != len(set(worker_ids)):
            raise ValueError("Factorio worker ids must be unique")
        audit_workers = list(audit_workers or [])
        audit_ids = [worker.worker_id for worker in audit_workers]
        if len(audit_ids) != len(set(audit_ids)):
            raise ValueError("Factorio audit worker ids must be unique")
        if set(worker_ids) & set(audit_ids):
            raise ValueError("Lease and audit worker ids must be disjoint")

        self._workers = {worker.worker_id: worker for worker in workers}
        self._audit_workers = {
            worker.worker_id: worker for worker in audit_workers
        }
        self._busy_audit_workers: set[str] = set()
        self._leases: dict[str, _LeaseRecord] = {}
        self._busy_workers: set[str] = set()
        self._lease_ttl = timedelta(seconds=lease_ttl_seconds)
        self._lock = threading.RLock()
        self._audit_condition = threading.Condition(self._lock)
        self.capabilities = capabilities or CapabilityManifest()
        if audit_workers:
            features = dict(self.capabilities.features)
            features.update(
                {
                    "clone": True,
                    "autonomous_throughput_audits": True,
                    "reserved_audit_workers": True,
                }
            )
            self.capabilities = self.capabilities.model_copy(
                update={"features": features}
            )
        for worker in workers:
            worker.set_throughput_audit_enabled(bool(audit_workers))

    def _run_throughput_audit(self, candidate):
        if not self._audit_workers:
            return None
        deadline = time.monotonic() + 30.0
        with self._audit_condition:
            while True:
                worker = next(
                    (
                        candidate_worker
                        for worker_id, candidate_worker in self._audit_workers.items()
                        if worker_id not in self._busy_audit_workers
                    ),
                    None,
                )
                if worker is not None:
                    self._busy_audit_workers.add(worker.worker_id)
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("No throughput audit worker became available")
                self._audit_condition.wait(timeout=remaining)
        try:
            return worker.run_throughput_audit(candidate)
        finally:
            with self._audit_condition:
                self._busy_audit_workers.discard(worker.worker_id)
                self._audit_condition.notify()

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

    def execute(
        self,
        lease_id: str,
        code: str,
        *,
        request_id: str | None = None,
    ) -> ExecutionResult:
        if not code.strip():
            raise ValueError("code must not be empty")
        code_sha256 = sha256(code.encode("utf-8")).hexdigest()
        record = self._record(lease_id)
        with record.lock:
            if record.released:
                raise LeaseNotFound(f"Released lease: {lease_id}")
            if request_id is not None:
                cached = record.execute_request_cache.get(request_id)
                if cached is not None:
                    cached_hash, cached_result = cached
                    if cached_hash != code_sha256:
                        raise IdempotencyConflict(
                            f"Execute request_id {request_id!r} was already used "
                            "for a different program"
                        )
                    self._renew(record)
                    return cached_result.model_copy(deep=True)
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
            intervention_limit = record.lease.task.max_interventions
            if (
                intervention_limit is not None
                and scored_interventions >= intervention_limit
            ):
                raise InterventionLimitReached(
                    "Task allows at most "
                    f"{intervention_limit} scored interventions "
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
                    code_sha256=code_sha256,
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
                candidate = record.worker.pop_throughput_audit_candidate()
                if candidate is not None:
                    try:
                        audit = self._run_throughput_audit(candidate)
                    except Exception as exc:  # audit failure is not policy failure
                        result.events.append(
                            VerifierEvent(
                                event_id=f"throughput-audit-error:{sequence}",
                                kind="custom",
                                tick=result.event.ticks,
                                source="verifier",
                                payload={
                                    "event": "throughput_audit_error",
                                    "error": f"{type(exc).__name__}: {exc}",
                                },
                            )
                        )
                    else:
                        if audit is not None:
                            record.worker.record_throughput_audit(audit)
                            result.events.append(
                                VerifierEvent(
                                    event_id=f"throughput-audit:{sequence}",
                                    kind="custom",
                                    tick=result.event.ticks,
                                    source="verifier",
                                    payload={
                                        "event": "throughput_audit_passed"
                                        if audit.passed
                                        else "throughput_audit_failed",
                                    },
                                )
                            )
                            if audit.passed:
                                record.worker.accept_throughput_audit(audit)
                                result.terminal_reason = "throughput_audit_passed"
            if (
                result.event.error
                and record.lease.tool_error_retries_used
                < record.lease.tool_error_retry_budget
            ):
                result.event.evaluation_retry = True
                record.lease.tool_error_retries_used += 1
            record.events.append(result.event)
            record.terminal_reason = result.terminal_reason
            if request_id is not None:
                record.execute_request_cache[request_id] = (
                    code_sha256,
                    result.model_copy(deep=True),
                )
            self._renew(record)
            return result

    def observe(
        self,
        lease_id: str,
        *,
        cursor: str | None = None,
        force_keyframe: bool = False,
    ) -> Observation:
        record = self._record(lease_id)
        with record.lock:
            if record.released:
                raise LeaseNotFound(f"Released lease: {lease_id}")
            if cursor is None and not force_keyframe:
                # Keep existing worker implementations (and lightweight test
                # doubles) source-compatible.  FLEWorker still emits the
                # revisioned stream when the cursor is omitted.
                observation = record.worker.observe(lease_id)
            else:
                observation = record.worker.observe(
                    lease_id,
                    cursor=cursor,
                    force_keyframe=force_keyframe,
                )
            self._renew(record)
            return observation

    def query_state(
        self,
        lease_id: str,
        *,
        kind: str,
        item: str | None = None,
        window_seconds: int | None = None,
        since_revision: int | None = None,
        entity_type: str | None = None,
        area: dict[str, Any] | None = None,
        changed_since: int | None = None,
        limit: int = 32,
    ) -> dict[str, Any]:
        """Return bounded public state history from the leased worker."""

        record = self._live_record(lease_id)
        with record.lock:
            query = getattr(record.worker, "query_state", None)
            if query is None:
                raise NotImplementedError("state history is unavailable for this worker")
            result = query(
                lease_id,
                kind=kind,
                item=item,
                window_seconds=window_seconds,
                since_revision=since_revision,
                entity_type=entity_type,
                area=area,
                changed_since=changed_since,
                limit=limit,
            )
            self._renew(record)
            return result

    def check_contract_throughput(
        self,
        lease_id: str,
        *,
        authoritative: bool = False,
        request_id: str | None = None,
    ):
        """Run one idempotent, intervention-free depot-throughput probe."""

        record = self._live_record(lease_id)
        method = "qualify-throughput" if authoritative else "check-throughput"
        with record.lock:
            cached_hit, cached = self._replay(record, method, request_id)
            if cached_hit:
                self._renew(record)
                return cached
            result = record.worker.check_contract_throughput(
                lease_id, authoritative=authoritative
            )
            if request_id:
                record.epoch_request_cache[(method, request_id)] = result
            self._renew(record)
            return result

    # -- model-managed session memory ---------------------------------------

    def memory_list(
        self,
        lease_id: str,
        *,
        prefix: str = "",
        limit: int = 50,
        cursor: str | int | None = None,
    ):
        record = self._live_record(lease_id)
        with record.lock:
            self._renew(record)
            return record.memory.list(prefix=prefix, limit=limit, cursor=cursor)

    def memory_read(self, lease_id: str, key: str):
        record = self._live_record(lease_id)
        with record.lock:
            self._renew(record)
            return record.memory.read(key)

    def memory_write(
        self,
        lease_id: str,
        key: str,
        content: str,
        *,
        expected_revision: int | None = None,
    ):
        record = self._live_record(lease_id)
        with record.lock:
            result = record.memory.write(
                key,
                content,
                expected_revision=expected_revision,
            )
            self._renew(record)
            return result

    def memory_delete(
        self,
        lease_id: str,
        key: str,
        *,
        expected_revision: int | None = None,
    ):
        record = self._live_record(lease_id)
        with record.lock:
            result = record.memory.delete(
                key,
                expected_revision=expected_revision,
            )
            self._renew(record)
            return result

    def memory_search(
        self,
        lease_id: str,
        query: str,
        *,
        limit: int = 20,
        cursor: str | int | None = None,
    ):
        record = self._live_record(lease_id)
        with record.lock:
            self._renew(record)
            return record.memory.search(query, limit=limit, cursor=cursor)

    def memory_trace(
        self,
        lease_id: str,
        *,
        limit: int = 100,
        cursor: str | int | None = None,
    ):
        record = self._live_record(lease_id)
        with record.lock:
            self._renew(record)
            return record.memory.trace(limit=limit, cursor=cursor)

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

    # -- adaptive contract epoch lifecycle (section 14) -----------------------

    def _live_record(self, lease_id: str) -> _LeaseRecord:
        record = self._record(lease_id)
        if record.released:
            raise LeaseNotFound(f"Released lease: {lease_id}")
        return record

    def _replay(
        self,
        record: _LeaseRecord,
        method: str,
        request_id: str | None,
    ) -> tuple[bool, Any]:
        if request_id is None:
            return False, None
        cached = record.epoch_request_cache.get((method, request_id))
        return (True, cached) if cached is not None else (False, None)

    def begin_contract_epoch(
        self,
        lease_id: str,
        spec: ContractEpochSpec,
        *,
        request_id: str | None = None,
    ) -> ActiveContractState:
        """Activate one committed order; the factory is never reset."""
        if request_id:
            self.reap_expired()
            with self._lock:
                record = self._leases.get(lease_id)
                if record is not None:
                    cached_hit, cached = self._replay(record, "begin", request_id)
                    if cached_hit:
                        return cached
        record = self._live_record(lease_id)
        with record.lock:
            if record.snapshot is not None:
                raise LeaseFinalized(f"Lease is already finalized: {lease_id}")
            state = record.worker.begin_contract_epoch(spec)
            record.active_commitment_hash = spec.commitment_hash
            if request_id:
                record.epoch_request_cache[("begin", request_id)] = state
            return state

    def finalize_contract_epoch(
        self,
        lease_id: str,
        epoch_index: int,
        commitment_hash: str,
        *,
        abandon: bool = False,
        infrastructure_interrupt: bool = False,
        request_id: str | None = None,
    ) -> ContractEpochOutcome:
        """Close the open epoch; fails on hash, session, or epoch mismatch."""
        if request_id:
            with self._lock:
                record = self._leases.get(lease_id)
                if record is not None:
                    cached_hit, cached = self._replay(record, "finalize", request_id)
                    if cached_hit and not abandon:
                        return cached
        record = self._live_record(lease_id)
        with record.lock:
            stored_hash = record.active_commitment_hash
            if stored_hash is not None and stored_hash != commitment_hash:
                raise CommitmentMismatch(
                    "Finalization commitment does not match the committed "
                    "epoch specification"
                )
            outcome = record.worker.finalize_contract_epoch(
                epoch_index,
                commitment_hash,
                abandon=abandon,
                infrastructure_interrupt=infrastructure_interrupt,
            )
            record.active_commitment_hash = None
            if request_id and not abandon:
                record.epoch_request_cache[("finalize", request_id)] = outcome
            return outcome

    def capture_contract_context(
        self,
        lease_id: str,
        session_id: str,
        epoch_index: int,
    ):
        """Passive context snapshot for selection; privileged HTTP only."""
        record = self._live_record(lease_id)
        with record.lock:
            return record.worker.capture_contract_context(session_id, epoch_index)

    def get_contract_session_state(self, lease_id: str) -> ContractSessionState:
        record = self._record(lease_id)
        with record.lock:
            if record.released:
                raise LeaseNotFound(f"Released lease: {lease_id}")
            state = record.worker.get_contract_session_state()
            # The adaptive benchmark polls this endpoint as its lease
            # keepalive while a provider call or retry backoff is in flight.
            self._renew(record)
            return state.model_copy(
                update={"active_commitment_hash": record.active_commitment_hash}
            )

    def finalize_contract_session(
        self,
        lease_id: str,
        *,
        request_id: str | None = None,
    ) -> ContractSessionSummary:
        record = self._live_record(lease_id)
        with record.lock:
            if record.session_summary is not None:
                return record.session_summary
            summary = record.worker.finalize_contract_session()
            record.session_summary = summary
            return summary

    def release(self, lease_id: str) -> bool:
        with self._lock:
            record = self._leases.pop(lease_id, None)
            if record is None:
                return False
        with record.lock:
            record.released = True
            try:
                record.worker.release()
            finally:
                with self._lock:
                    self._busy_workers.discard(record.worker.worker_id)
        return True

    def close(self) -> None:
        with self._lock:
            lease_ids = list(self._leases)
        for lease_id in lease_ids:
            self.release(lease_id)
        deadline = time.monotonic() + 30.0
        with self._audit_condition:
            while self._busy_audit_workers:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return
                self._audit_condition.wait(timeout=remaining)
        for worker in self._audit_workers.values():
            worker.release()
