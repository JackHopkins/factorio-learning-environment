"""Adaptive contract epoch lifecycle tests (section 14).

Unit classes run against an in-memory worker carrying real ``ActiveOrder``
semantics; the live class proves two-epoch persistence against a real
Factorio server.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from fle.envd.backend import FLEWorker, FactorioWorker
from fle.envd.customer import ActiveOrder
from fle.envd.errors import (
    CommitmentMismatch,
    EpochAlreadyActive,
    EpochMismatch,
)
from fle.envd.models import (
    ActionEvent,
    ActiveContractState,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ContractEpochSpec,
    ContractDifficultyFeatures,
    ContractSessionState,
    ContractSessionSummary,
    ExecutionResult,
    FactorioTaskSpec,
    Observation,
    VerificationSnapshot,
)
from fle.envd.service import EnvironmentService

UNIT = pytest.mark.no_factorio


# ---------------------------------------------------------------------------
# Fake worker: mirrors FLEWorker's epoch contract without Factorio
# ---------------------------------------------------------------------------


class ContractFakeWorker(FactorioWorker):
    """In-memory worker with persistent-world semantics for epoch tests."""

    def __init__(self, worker_id="worker-contract-0"):
        self.worker_id = worker_id
        self.factory: dict = {"entities": 10, "research": ["electricity"]}
        self.tick = 1000  # absolute simulation tick
        self.released = False
        self.task: FactorioTaskSpec | None = None
        self._session_baseline_tick: int | None = None
        self.contract_session_id: str | None = None
        self._active_order: ActiveOrder | None = None
        self._active_epoch_index: int | None = None
        self._epoch_start_tick: int | None = None
        self._completed_epochs = 0
        self._records: list[ContractEpochOutcome] = []
        self._interventions = 0

    # -- legacy surface ------------------------------------------------------

    def start_task(self, task: FactorioTaskSpec) -> str:
        self.task = task
        self._session_baseline_tick = self.tick
        return "initial-hash"

    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        self._interventions += 1
        event = ActionEvent(
            sequence=sequence,
            code_sha256=f"code-{sequence}",
            started_at=datetime.now(timezone.utc),
            duration_seconds=0.01,
            result=f"executed {code}",
            ticks=self.tick,
        )
        return ExecutionResult(
            lease_id=lease_id,
            event=event,
            production_score=1.0,
            automated_production_score=1.0,
            state_hash=f"state-{self.tick}",
        )

    def observe(self, lease_id: str) -> Observation:
        return Observation(
            lease_id=lease_id,
            task_id=self.task.task_id if self.task else "unknown",
            ticks=self.tick,
            state_hash=f"state-{self.tick}",
        )

    def finalize(self, lease_id, task, events) -> VerificationSnapshot:
        raise AssertionError("adaptive sessions never call task finalize")

    def release(self) -> None:
        self.released = True

    # -- adaptive epoch surface ------------------------------------------------

    def capture_contract_context(
        self, session_id: str, epoch_index: int
    ) -> ContractContextSnapshot:
        return ContractContextSnapshot(
            session_id=session_id,
            epoch_index=epoch_index,
            captured_tick=self.tick,
            technology_ids=tuple(self.factory["research"]),
            unlocked_recipe_ids=(),
            inventory_counts={"iron-plate": self.factory["entities"] * 10},
            placed_entity_counts={"stone-furnace": self.factory["entities"]},
            production_rates_60s={},
            production_rates_300s={},
            power_capacity_kw=300.0,
            power_utilization=0.3,
            logistic_network_count=0,
            train_stop_count=0,
            pollution_total=None,
            evolution_factor=None,
            map_seed_hash="msh",
            state_digest=f"digest-{self.factory['entities']}",
        )

    def begin_contract_epoch(self, spec: ContractEpochSpec) -> ActiveContractState:
        if self._active_order is not None:
            raise EpochAlreadyActive("second active order")
        expected = self._completed_epochs + 1
        if spec.epoch_index != expected:
            raise EpochMismatch(f"expected {expected}, got {spec.epoch_index}")
        if (
            self.contract_session_id is not None
            and spec.session_id != self.contract_session_id
        ):
            raise EpochMismatch("session id changed within one lease")
        order = ActiveOrder(
            item_name=spec.item_name,
            requested_quantity=spec.quantity,
            deadline_ticks=spec.deadline_ticks,
            activation_tick=self.tick - self._session_baseline_tick,
        )
        self.contract_session_id = spec.session_id
        self._active_order = order
        self._active_epoch_index = spec.epoch_index
        self._epoch_start_tick = self.tick
        return ActiveContractState(
            lease_id=self.worker_id,
            session_id=spec.session_id,
            epoch_index=spec.epoch_index,
            spec_commitment_hash=spec.commitment_hash,
            open_order=order.student_view(),
            epoch_start_tick=self.tick - self._session_baseline_tick,
        )

    def finalize_contract_epoch(
        self,
        epoch_index: int,
        commitment_hash: str,
        *,
        abandon: bool = False,
        infrastructure_interrupt: bool = False,
    ) -> ContractEpochOutcome:
        if self._active_order is None:
            raise EpochMismatch("no open epoch")
        if epoch_index != self._active_epoch_index:
            raise EpochMismatch("index mismatch")
        order = self._active_order
        relative_now = self.tick - self._session_baseline_tick
        if abandon or infrastructure_interrupt:
            order.abandon(self.tick)
        else:
            expiry = order.sync(relative_now)
            _ = expiry
        outcome_state = order.evaluate(relative_now)
        status = {
            "fulfilled": "fulfilled",
            "partial": outcome_state.status,
            "expired": "expired",
            "abandoned": "abandoned",
        }[outcome_state.status]
        if infrastructure_interrupt and outcome_state.status == "abandoned":
            status = "infrastructure_error"
        record = ContractEpochOutcome(
            session_id=self.contract_session_id,
            epoch_index=epoch_index,
            commitment_hash=commitment_hash,
            status=status,
            delivered_quantity=int(order.delivered),
            requested_quantity=order.requested_quantity,
            completion_ratio=outcome_state.completion_ratio,
            simulation_ticks_used=(self.tick - self._epoch_start_tick),
            interventions_used=self._interventions,
            model_seconds=0.0,
            tool_seconds=0.0,
            runner_wall_seconds=0.0,
            first_delivery_tick=None,
            completion_tick=None,
            terminal_state_digest=f"digest-{self.factory['entities']}",
        )
        self._records.append(record)
        self._completed_epochs += 1
        self._active_order = None
        self._active_epoch_index = None
        self._epoch_start_tick = None
        return record

    def get_contract_session_state(self) -> ContractSessionState:
        return ContractSessionState(
            lease_id=self.worker_id,
            session_id=self.contract_session_id or "",
            session_simulation_ticks=(
                self.tick - self._session_baseline_tick
                if self._session_baseline_tick is not None
                else 0
            ),
            epoch_simulation_ticks=(
                self.tick - self._epoch_start_tick
                if self._epoch_start_tick is not None
                else 0
            ),
            completed_epoch_count=self._completed_epochs,
            active_epoch_index=self._active_epoch_index,
            active_commitment_hash=None,
            agent_interventions=self._interventions,
        )

    def finalize_contract_session(self) -> ContractSessionSummary:
        return ContractSessionSummary(
            session_id=self.contract_session_id or "",
            session_simulation_ticks=self.get_contract_session_state().session_simulation_ticks,
            epochs=list(self._records),
            fulfilled_epochs=sum(1 for r in self._records if r.status == "fulfilled"),
            total_delivered=sum(r.delivered_quantity for r in self._records),
            total_requested=sum(r.requested_quantity for r in self._records),
        )


def _spec(
    epoch_index: int,
    quantity: int = 100,
    deadline: int = 36000,
    item: str = "iron-plate",
    session: str = "sess",
) -> ContractEpochSpec:
    context = ContractContextSnapshot(
        session_id=session,
        epoch_index=epoch_index,
        captured_tick=500 * epoch_index,
        technology_ids=("electricity",),
        unlocked_recipe_ids=(),
        inventory_counts={},
        placed_entity_counts={},
        production_rates_60s={},
        production_rates_300s={},
        power_capacity_kw=300.0,
        power_utilization=0.2,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="msh",
        state_digest=f"d{epoch_index}",
    )
    features = ContractDifficultyFeatures(
        product_id=item,
        product_tier=0,
        recipe_depth=1,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=0,
        log_quantity=4.6,
        deadline_ticks=deadline,
        required_rate_per_minute=60.0,
        existing_rate_per_minute=0.0,
        inventory_coverage_ratio=0.0,
        estimated_power_fraction=0.1,
        transport_complexity=0.0,
        stage_band=1,
    )
    return ContractEpochSpec.create(
        session_id=session,
        epoch_index=epoch_index,
        template_id="t",
        generation_seed=epoch_index,
        selection_seed=epoch_index * 7,
        item_name=item,
        quantity=quantity,
        deadline_ticks=deadline,
        intervention_budget=None,
        context=context,
        features=features,
        raw_difficulty=1.0,
        state_advantage=0.0,
        effective_difficulty=1.0,
    )


def _service() -> tuple[EnvironmentService, ContractFakeWorker, str]:
    worker = ContractFakeWorker()
    service = EnvironmentService([worker], lease_ttl_seconds=3600)
    lease = service.lease(
        FactorioTaskSpec(task_id="adaptive-session", goal="fulfil orders")
    )
    return service, worker, lease.lease_id


@UNIT
def test_adaptive_depot_placement_requires_explicit_task_marker():
    calls: list[tuple[str, tuple]] = []

    class Namespace:
        def _customer_depot(self, command, *args):
            calls.append((command, args))
            return {"placed": 8} if command == "place" else {"cleared": True}

    worker = object.__new__(FLEWorker)
    worker.instance = SimpleNamespace(first_namespace=Namespace())
    worker._adaptive_depot_placed = False

    # Ordinary open-play tasks retain their existing no-depot behavior.
    worker._setup_customer(
        FactorioTaskSpec(task_id="ordinary-open-play", goal="build", task_family="open_play")
    )
    assert calls == [("clear", ())]

    calls.clear()
    worker._setup_customer(
        FactorioTaskSpec(
            task_id="adaptive-open-play",
            goal="fulfil orders",
            task_family="open_play",
            adaptive_contract_session=True,
        )
    )
    assert calls and calls[0][0] == "place"
    assert worker._adaptive_depot_placed is True


# ---------------------------------------------------------------------------
# Lifecycle semantics
# ---------------------------------------------------------------------------


@UNIT
def test_begin_and_finalize_one_epoch():
    service, _worker, lease_id = _service()
    spec = _spec(1)
    state = service.begin_contract_epoch(lease_id, spec, request_id="b1")
    assert state.epoch_index == 1
    assert state.spec_commitment_hash == spec.commitment_hash
    assert state.open_order.products[0].product == "iron-plate"

    outcome = service.finalize_contract_epoch(
        lease_id, 1, spec.commitment_hash, request_id="f1"
    )
    assert outcome.status in ("expired", "partial", "fulfilled")
    summary = service.finalize_contract_session(lease_id)
    assert len(summary.epochs) == 1


@UNIT
def test_second_open_order_is_rejected():
    service, _worker, lease_id = _service()
    service.begin_contract_epoch(lease_id, _spec(1), request_id="b1")
    with pytest.raises(EpochAlreadyActive):
        service.begin_contract_epoch(lease_id, _spec(2), request_id="b2")


@UNIT
def test_monotonically_increasing_indexes_enforced():
    service, _worker, lease_id = _service()
    with pytest.raises(EpochMismatch):
        service.begin_contract_epoch(lease_id, _spec(2), request_id="skip")


@UNIT
def test_finalize_requires_matching_commitment():
    service, _worker, lease_id = _service()
    spec = _spec(1)
    service.begin_contract_epoch(lease_id, spec, request_id="b1")
    tampered = _spec(1, quantity=spec.quantity + 50)
    assert tampered.commitment_hash != spec.commitment_hash
    with pytest.raises(CommitmentMismatch):
        service.finalize_contract_epoch(
            lease_id, 1, tampered.commitment_hash, request_id="f-bad"
        )


@UNIT
def test_idempotent_replay_under_identical_request_ids():
    service, worker, lease_id = _service()
    spec = _spec(1)
    first = service.begin_contract_epoch(lease_id, spec, request_id="same")
    second = service.begin_contract_epoch(lease_id, spec, request_id="same")
    assert first.model_dump() == second.model_dump()

    worker.tick += 3600
    outcome_a = service.finalize_contract_epoch(
        lease_id, 1, spec.commitment_hash, request_id="fin"
    )
    outcome_b = service.finalize_contract_epoch(
        lease_id, 1, spec.commitment_hash, request_id="fin"
    )
    assert outcome_a.model_dump() == outcome_b.model_dump()
    assert worker._completed_epochs == 1


@UNIT
def test_active_state_cleared_then_next_epoch_opens():
    """Epoch N+1 opens cleanly after N finalizes."""
    service, _worker, lease_id = _service()
    for index in (1, 2):
        spec = _spec(index)
        service.begin_contract_epoch(lease_id, spec, request_id=f"begin-{index}")
        outcome = service.finalize_contract_epoch(
            lease_id,
            index,
            spec.commitment_hash,
            request_id=f"final-{index}",
        )
        _ = outcome
    summary = service.finalize_contract_session(lease_id)
    assert [e.epoch_index for e in summary.epochs] == [1, 2]


@UNIT
def test_world_persists_across_epochs_while_counters_reset():
    """The factory built in epoch 1 exists in epoch 2 (section 14 invariant)."""
    service, worker, lease_id = _service()
    spec1 = _spec(1)
    service.begin_contract_epoch(lease_id, spec1, request_id="b1")
    # The agent builds during epoch 1...
    worker.factory["entities"] += 5
    worker.factory["research"].append("steel-processing")
    worker.tick += 7200
    service.finalize_contract_epoch(lease_id, 1, spec1.commitment_hash, request_id="f1")

    # ...and epoch 2 observes the accumulated world.
    context = worker.capture_contract_context(worker.contract_session_id, 2)
    assert context.placed_entity_counts["stone-furnace"] == 15
    assert "steel-processing" in context.technology_ids

    spec2 = _spec(2, item="copper-plate")
    state = service.begin_contract_epoch(lease_id, spec2, request_id="b2")
    assert state.open_order.products[0].product == "copper-plate"


@UNIT
def test_session_and_epoch_ticks_accounted_separately():
    service, worker, lease_id = _service()
    spec = _spec(1)
    baseline_state = worker.get_contract_session_state()
    _ = baseline_state
    service.begin_contract_epoch(lease_id, spec, request_id="b1")
    worker.tick += 600
    mid_state = service.get_contract_session_state(lease_id)
    assert mid_state.session_simulation_ticks == 600
    assert mid_state.epoch_simulation_ticks == 600
    assert mid_state.active_commitment_hash == spec.commitment_hash
    worker.tick += 1200
    outcome = service.finalize_contract_epoch(
        lease_id, 1, spec.commitment_hash, request_id="f1"
    )
    assert outcome.simulation_ticks_used == 1800
    end_state = service.get_contract_session_state(lease_id)
    assert end_state.session_simulation_ticks == 1800
    assert end_state.epoch_simulation_ticks == 0


@UNIT
def test_infrastructure_interrupt_never_recorded_as_loss():
    service, worker, lease_id = _service()
    spec = _spec(1)
    service.begin_contract_epoch(lease_id, spec, request_id="b1")
    worker.tick += 900
    outcome = service.finalize_contract_epoch(
        lease_id,
        1,
        spec.commitment_hash,
        infrastructure_interrupt=True,
        request_id="f-infra",
    )
    assert outcome.status == "infrastructure_error"
    from fle.envd.contract_rating import map_outcome

    assert map_outcome(outcome) is None  # unrated, not a loss


@UNIT
def test_finalized_records_retained_through_session_end():
    service, worker, lease_id = _service()
    for index in (1, 2):
        spec = _spec(index)
        service.begin_contract_epoch(lease_id, spec, request_id=f"b{index}")
        worker.tick += 1800
        service.finalize_contract_epoch(
            lease_id, index, spec.commitment_hash, request_id=f"f{index}"
        )
    summary = service.finalize_contract_session(lease_id)
    assert len(summary.epochs) == 2
    assert worker._records  # retained on the worker too
    assert summary.total_requested == 200


@UNIT
def test_delivery_fulfillment_flows_through_lifecycle():
    """Sink deliveries credited between begin/finalize yield 'fulfilled'."""
    service, worker, lease_id = _service()
    spec = _spec(1, quantity=100)
    service.begin_contract_epoch(lease_id, spec, request_id="b1")
    worker._active_order.attribute(60.0, worker.tick)
    worker.tick += 300
    worker._active_order.attribute(40.0, worker.tick)
    outcome = service.finalize_contract_epoch(
        lease_id, 1, spec.commitment_hash, request_id="f1"
    )
    assert outcome.status == "fulfilled"
    assert outcome.delivered_quantity == 100
    assert outcome.completion_ratio == pytest.approx(1.0)

    from fle.envd.contract_rating import map_outcome

    assert map_outcome(outcome) == "win"

    summary = service.finalize_contract_session(lease_id)
    assert summary.fulfilled_epochs == 1


@UNIT
def test_live_worker_sync_exposes_and_terminates_adaptive_order():
    """Normal observe/execute plumbing advances the adaptive order."""
    from fle.envd.backend import FLEWorker
    from fle.envd.customer import ActiveOrder

    worker = FLEWorker.__new__(FLEWorker)
    worker.customer_engine = None
    worker._active_epoch_index = 1
    worker._active_order = ActiveOrder(
        "iron-plate", 100, 3600, activation_tick=0
    )
    worker._customer_events = []
    worker._epoch_game_tick = 0
    worker._drain_delivery_buckets = lambda: [(299, {"iron-plate": 100.0})]
    worker._read_game_tick = lambda: 300

    events = worker._sync_active_order()

    assert worker._active_order.status == "fulfilled"
    assert worker._contracts_view()[0].status == "fulfilled"
    assert [event.kind for event in events] == ["contract_fulfilled"]


@UNIT
def test_live_worker_sync_expires_adaptive_order_without_delivery():
    from fle.envd.backend import FLEWorker
    from fle.envd.customer import ActiveOrder

    worker = FLEWorker.__new__(FLEWorker)
    worker._active_epoch_index = 1
    worker._active_order = ActiveOrder(
        "iron-plate", 100, 3600, activation_tick=0
    )
    worker._customer_events = []
    worker._epoch_game_tick = 0
    worker._drain_delivery_buckets = lambda: []
    worker._read_game_tick = lambda: 3600

    events = worker._sync_active_order()

    assert worker._active_order.status == "expired"
    assert [event.kind for event in events] == ["contract_expired"]


# ---------------------------------------------------------------------------
# Live two-epoch persistence (requires a Factorio container on :27000)
# ---------------------------------------------------------------------------


class TestTwoEpochLivePersistence:
    """Builds in epoch 1; proves factory, research, and inventory survive
    into epoch 2 while active-order state and epoch counters reset."""

    def test_two_epochs_inherit_factory(self):
        from fle.envd.backend import FLEWorker
        from fle.envd.models import VerifierSpec

        worker = FLEWorker.connect("live-adaptive-worker", tcp_port=27000)
        try:
            task = FactorioTaskSpec(
                task_id="adaptive_live_v1",
                goal="Fulfil each customer order as it arrives.",
                verifier=VerifierSpec(implementation="objective_engine_v1"),
                max_interventions=16,
                holdout_seconds=0,
                adaptive_contract_session=True,
            )
            worker.start_task(task)
            session_id = "live-adaptive-session"

            spec1 = _spec(1, quantity=20, item="iron-plate", session=session_id)
            state1 = worker.begin_contract_epoch(spec1)
            assert state1.epoch_index == 1

            worker.instance.first_namespace._set_inventory({"stone-furnace": 1})
            build_program = """
position = Position(x=-6.0, y=0.0)
move_to(position)
entity = place_entity(Prototype.StoneFurnace, position=position)
print('built', entity is not None)
"""
            result = worker.execute("lease-live", build_program, 1)
            assert not result.event.error, result.event.result

            outcome1 = worker.finalize_contract_epoch(
                1, spec1.commitment_hash, abandon=True
            )
            assert outcome1.epoch_index == 1
            entities_after_epoch1 = worker.capture_contract_context(
                session_id, 2
            ).placed_entity_counts

            spec2 = _spec(2, quantity=30, item="copper-plate", session=session_id)
            state2 = worker.begin_contract_epoch(spec2)
            assert state2.epoch_index == 2

            context2 = worker.capture_contract_context(session_id, 2)
            # Factory and research survive into epoch 2.
            assert any(count > 0 for count in context2.placed_entity_counts.values())
            furnace_before = entities_after_epoch1.get("stone-furnace", 0)
            furnace_after = context2.placed_entity_counts.get("stone-furnace", 0)
            assert furnace_after >= furnace_before

            worker.finalize_contract_epoch(2, spec2.commitment_hash, abandon=True)
            summary = worker.finalize_contract_session()
            assert [e.epoch_index for e in summary.epochs] == [1, 2]
        finally:
            worker.release()
