from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from fle.commons.models.game_state import GameState
from fle.envd.backend import FLEWorker, ThroughputAuditCandidate
from fle.envd.customer import ActiveOrder
from fle.envd.errors import LeaseFinalized
from fle.envd.models import (
    ContractContextSnapshot,
    ContractDifficultyFeatures,
    ContractEpochSpec,
    ExecutionResult,
    FactorioTaskSpec,
    ThroughputAuditResult,
    ThroughputAuditSpec,
)
from fle.envd.service import EnvironmentService
from tests.envd.conftest import FakeWorker


pytestmark = pytest.mark.no_factorio


def _epoch_spec(*, order_kind: str = "sustained", audit=None) -> ContractEpochSpec:
    context = ContractContextSnapshot(
        session_id="session-1",
        epoch_index=1,
        captured_tick=100,
        technology_ids=("electricity",),
        unlocked_recipe_ids=(),
        inventory_counts={},
        placed_entity_counts={},
        production_rates_60s={},
        production_rates_300s={},
        power_capacity_kw=100.0,
        power_utilization=0.0,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="map",
        state_digest="state",
    )
    features = ContractDifficultyFeatures(
        product_id="iron-plate",
        product_tier=0,
        recipe_depth=1,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=0,
        log_quantity=5.3,
        deadline_ticks=3600,
        required_rate_per_minute=200.0,
        existing_rate_per_minute=0.0,
        inventory_coverage_ratio=0.0,
        estimated_power_fraction=0.1,
        transport_complexity=0.0,
        stage_band=1,
    )
    fields = dict(
        session_id="session-1",
        epoch_index=1,
        template_id="throughput",
        generation_seed=11,
        selection_seed=12,
        item_name="iron-plate",
        quantity=200,
        order_kind=order_kind,
        deadline_ticks=3600,
        intervention_budget=None,
        context=context,
        features=features,
        raw_difficulty=1.0,
        state_advantage=0.0,
        effective_difficulty=1.0,
    )
    if audit is not None:
        fields["throughput_audit"] = audit
    return ContractEpochSpec.create(**fields)


def test_throughput_audit_spec_validates_windows_and_sustained_default_is_committed():
    with pytest.raises(ValidationError, match="holdout_seconds_max"):
        ThroughputAuditSpec(holdout_seconds_min=20, holdout_seconds_max=10)
    with pytest.raises(ValidationError, match="subwindow_seconds"):
        ThroughputAuditSpec(holdout_seconds_max=10, subwindow_seconds=11)

    sustained = _epoch_spec()
    assert sustained.throughput_audit == ThroughputAuditSpec()

    payload = sustained.model_dump(mode="json", exclude={"commitment_hash"})
    payload["throughput_audit"]["burn_in_seconds"] += 1
    with pytest.raises(ValidationError, match="commitment mismatch"):
        ContractEpochSpec.model_validate(
            {**payload, "commitment_hash": sustained.commitment_hash}
        )

    assert _epoch_spec(order_kind="one_shot").throughput_audit is None


class _CandidateWorker(FakeWorker):
    def __init__(self, worker_id="agent-worker"):
        super().__init__(worker_id)
        self._candidate = None
        self.recorded: list[ThroughputAuditResult] = []
        self.accepted: list[ThroughputAuditResult] = []

    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        result = super().execute(lease_id, code, sequence)
        self._candidate = SimpleNamespace(candidate_tick=sequence * 60)
        return result

    def pop_throughput_audit_candidate(self):
        candidate, self._candidate = self._candidate, None
        return candidate

    def record_throughput_audit(self, result: ThroughputAuditResult) -> None:
        self.recorded.append(result)

    def accept_throughput_audit(self, result: ThroughputAuditResult) -> None:
        self.accepted.append(result)


def _audit_result(*, passed: bool, calls: int = 0) -> ThroughputAuditResult:
    return ThroughputAuditResult(
        lease_id="lease",
        session_id="session-1",
        epoch_index=1,
        audit_worker_id="audit-worker",
        candidate_tick=60,
        candidate_state_hash="candidate-state",
        detector_window_seconds=5,
        detector_rates_per_minute={"iron-plate": 220.0},
        target_rates_per_minute={"iron-plate": 200.0},
        burn_in_seconds=20,
        holdout_seconds=30,
        holdout_ticks=1800,
        subwindow_seconds=10,
        subwindow_ticks=[600, 600, 600],
        production_rates_per_minute={"iron-plate": 200.0},
        depot_rates_per_minute={"iron-plate": 200.0},
        production_subwindow_rates={"iron-plate": [200.0, 200.0, 200.0]},
        depot_subwindow_rates={"iron-plate": [200.0, 200.0, 200.0]},
        line_scores={"iron-plate": 1.0 if passed else 0.0},
        passed=passed,
        failure_reasons=[] if passed else [f"failed-attempt-{calls}"],
    )


class _AuditWorker(FakeWorker):
    def __init__(self, result_factory, *, fail_first=False):
        super().__init__("audit-worker")
        self.result_factory = result_factory
        self.fail_first = fail_first
        self.calls = 0
        self.accepted: list[ThroughputAuditResult] = []

    def run_throughput_audit(self, candidate):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("audit process failed")
        return self.result_factory(self.calls)

    def accept_throughput_audit(self, result: ThroughputAuditResult) -> None:
        self.accepted.append(result)


def test_service_passes_candidate_audit_and_terminates_immediately():
    agent = _CandidateWorker()
    auditor = _AuditWorker(lambda calls: _audit_result(passed=True, calls=calls))
    service = EnvironmentService([agent], audit_workers=[auditor])
    lease = service.lease(FactorioTaskSpec(task_id="throughput", goal="produce"))

    result = service.execute(lease.lease_id, "step()")

    audit_event = next(
        event
        for event in result.events
        if event.payload.get("event") == "throughput_audit_passed"
    )
    assert audit_event.payload == {"event": "throughput_audit_passed"}
    assert result.terminal_reason == "throughput_audit_passed"
    assert auditor.calls == 1
    assert len(agent.recorded) == 1
    assert agent.recorded[0].passed is True
    assert len(agent.accepted) == 1
    assert agent.accepted[0] is agent.recorded[0]
    with pytest.raises(LeaseFinalized, match="throughput_audit_passed"):
        service.execute(lease.lease_id, "step_again()")

    snapshot = service.finalize(lease.lease_id)
    assert snapshot.action_events[0].sequence == 1
    service.close()


def test_service_keeps_rollout_open_when_candidate_audit_fails():
    agent = _CandidateWorker()
    auditor = _AuditWorker(lambda calls: _audit_result(passed=False, calls=calls))
    service = EnvironmentService([agent], audit_workers=[auditor])
    lease = service.lease(FactorioTaskSpec(task_id="throughput", goal="produce"))

    failed = service.execute(lease.lease_id, "step()")
    continued = service.execute(lease.lease_id, "step_again()")

    audit_event = next(
        event
        for event in failed.events
        if event.payload.get("event") == "throughput_audit_failed"
    )
    assert audit_event.payload == {"event": "throughput_audit_failed"}
    assert failed.terminal_reason is None
    assert continued.event.sequence == 2
    assert auditor.calls == 2
    assert len(agent.recorded) == 2
    assert all(not audit.passed for audit in agent.recorded)
    assert agent.accepted == []
    service.close()


def test_audit_worker_slot_is_released_when_audit_raises():
    agent = _CandidateWorker()
    auditor = _AuditWorker(
        lambda calls: _audit_result(passed=False, calls=calls), fail_first=True
    )
    service = EnvironmentService([agent], audit_workers=[auditor])
    lease = service.lease(FactorioTaskSpec(task_id="throughput", goal="produce"))

    errored = service.execute(lease.lease_id, "step()")
    assert any(
        event.payload.get("event") == "throughput_audit_error"
        for event in errored.events
    )
    assert service._busy_audit_workers == set()

    # A second candidate must be able to acquire the same reserved worker.
    recovered = service.execute(lease.lease_id, "step_again()")
    assert any(
        event.payload.get("event") == "throughput_audit_failed"
        for event in recovered.events
    )
    assert len(agent.recorded) == 1
    assert auditor.calls == 2
    assert service._busy_audit_workers == set()
    service.close()


def test_active_order_certificate_is_terminal_and_preserves_audit_evidence():
    order = ActiveOrder(
        "iron-plate",
        200,
        3600,
        activation_tick=100,
        order_kind="sustained",
    )
    evidence = {
        "passed": True,
        "holdout_seconds": 40,
        "production_subwindow_rates": {"iron-plate": [200.0, 210.0]},
    }

    event = order.certify_sustained(250, evidence)

    assert event["event"] == "contract_fulfilled"
    assert order.status == "fulfilled"
    assert order.completion_tick == 250
    assert order.student_view().status == "fulfilled"
    outcome = order.evaluate()
    assert outcome.completion_ratio == 1.0
    assert outcome.delivered_quantity == 0.0
    assert outcome.delivery_telemetry["autonomous_qualification"] == evidence
    with pytest.raises(ValueError, match="open sustained"):
        order.certify_sustained(300, evidence)

    one_shot = ActiveOrder("iron-plate", 1, 60, activation_tick=0)
    with pytest.raises(ValueError, match="sustained"):
        one_shot.certify_sustained(1, evidence)


class _FakeDepot:
    def adopt(self, specs):
        return {"adopted": len(specs)}

    def __call__(self, command):
        assert command == "telemetry"
        return {}


class _FakeProductionNamespace:
    def __init__(self, rates_per_minute):
        self.rates_per_minute = list(rates_per_minute)
        self._customer_depot = _FakeDepot()
        self.reset()

    def reset(self):
        self.index = 0
        self.total = 0.0

    def sleep(self, seconds):
        rate = self.rates_per_minute[min(self.index, len(self.rates_per_minute) - 1)]
        self.total += rate * seconds / 60.0
        self.index += 1

    def _get_production_stats(self):
        return {
            "input": {},
            "output": {"iron-plate": self.total},
            "crafted": [],
            "harvested": {},
        }


class _FakeProductionInstance:
    def __init__(self, rates_per_minute):
        self.first_namespace = _FakeProductionNamespace(rates_per_minute)
        self.speeds = []

    def reset(self, **kwargs):
        assert kwargs["clear_entities"] is True
        self.first_namespace.reset()

    def set_speed_and_unpause(self, speed):
        self.speeds.append(speed)

    def pause(self):
        return None


def _production_candidate(*, rates, audit):
    return ThroughputAuditCandidate(
        lease_id="lease",
        session_id="session-1",
        epoch_index=1,
        state=GameState(entities="", inventories=[], research=None),
        state_hash="candidate-state",
        candidate_tick=0,
        detector_rates={"iron-plate": 220.0},
        target_rates={"iron-plate": 200.0},
        depot_specs=[],
        audit_spec=audit,
        commitment_hash="commitment",
    )


def test_audit_uses_subwindow_floor_not_average_for_bursty_production():
    audit = ThroughputAuditSpec(
        burn_in_seconds=0,
        holdout_seconds_min=30,
        holdout_seconds_max=30,
        subwindow_seconds=10,
        require_depot_service=False,
    )
    worker = FLEWorker.__new__(FLEWorker)
    worker.worker_id = "audit-worker"
    worker.instance = _FakeProductionInstance([500.0, 500.0, 0.0])

    result = worker.run_throughput_audit(
        _production_candidate(rates=[500.0, 500.0, 0.0], audit=audit)
    )

    assert result.production_subwindow_rates["iron-plate"] == [
        pytest.approx(500.0),
        pytest.approx(500.0),
        pytest.approx(0.0),
    ]
    assert result.production_rates_per_minute["iron-plate"] == pytest.approx(
        1000.0 / 3.0
    )
    assert result.passed is False
    assert result.line_scores["iron-plate"] == pytest.approx(0.0)
    assert result.failure_reasons == [
        "iron-plate:rate_or_subwindow_below_threshold"
    ]


def test_randomized_holdout_length_uses_hidden_entropy_within_bounds(monkeypatch):
    audit = ThroughputAuditSpec(
        burn_in_seconds=0,
        holdout_seconds_min=30,
        holdout_seconds_max=60,
        subwindow_seconds=10,
        require_depot_service=False,
    )
    instance = _FakeProductionInstance([200.0] * 8)
    worker = FLEWorker.__new__(FLEWorker)
    worker.worker_id = "audit-worker"
    worker.instance = instance
    candidate = _production_candidate(rates=[200.0] * 8, audit=audit)

    monkeypatch.setattr("fle.envd.backend.secrets.randbelow", lambda _span: 0)
    first = worker.run_throughput_audit(candidate)
    monkeypatch.setattr("fle.envd.backend.secrets.randbelow", lambda span: span - 1)
    second = worker.run_throughput_audit(candidate)

    assert first.holdout_seconds == 30
    assert first.holdout_seconds % 10 == 0
    assert second.holdout_seconds == 60
    assert first.passed is True
    assert second.passed is True
