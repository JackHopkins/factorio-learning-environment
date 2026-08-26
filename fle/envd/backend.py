from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from fle.commons.constants import REWARD_OVERRIDE_KEY
from fle.commons.models.game_state import GameState
from fle.env import FactorioInstance
from fle.envd.blueprints import BlueprintStore
from fle.envd.contract_features import (
    ProductCatalog,
    NamespaceRecipeDataSource,
    capture_context_snapshot,
)
from fle.envd.errors import (
    CommitmentMismatch,
    EpochAlreadyActive,
    EpochMismatch,
    NoActiveEpoch,
)
from fle.envd.customer import (
    DELIVERY_BUCKET_TICKS,
    ActiveOrder,
    ContractEngine,
    DeliveryBucket,
)
from fle.envd.perturbations import PerturbationEngine
from fle.envd.models import (
    ActionEvent,
    ActiveContractState,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ContractEpochSpec,
    ContractSessionState,
    ContractSessionSummary,
    ExecutionResult,
    FactorioTaskSpec,
    BlueprintSummary,
    Observation,
    OpenContractView,
    PrivilegedTransitionPacket,
    RewardVector,
    StateQualitySnapshot,
    VerificationSnapshot,
    VerifierEvent,
    canonical_hash,
)
from fle.envd.objective_engine import (
    TelemetryFrame,
    _numeric_dict,
    _objective_telemetry,
    build_state_quality_snapshot,
    capture_telemetry,
    compare_state_quality,
    measure_autonomous_holdout,
    verify_native,
)
from fle.eval.tasks import TaskFactory

# Objective kinds whose evaluation matches against full per-entity details.
# When a task uses none of them, per-intervention telemetry can take the
# cheap aggregate-census path instead of serializing every entity.
_ENTITY_DETAIL_KINDS = {
    "entity_exists",
    "entity_status",
    "entity_recipe",
    "entity_inventory",
    "entity_position",
}


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _instance_state_hash(instance: FactorioInstance, *, research_state=None) -> str:
    raw = GameState.from_instance(instance, research_state=research_state).to_raw()
    state = __import__("json").loads(raw)
    state.pop("timestamp", None)
    return canonical_hash(state)


class _NativeFreeplayTask:
    """Minimal stand-in for registry tasks on native objective-engine specs.

    Contract and other native specs verify through ``objective_engine_v1``;
    they never call the legacy ``task.verify`` path, so a full registry task
    is unnecessary provisioning baggage.
    """

    def __init__(self, task: FactorioTaskSpec):
        self.starting_inventory = task.provisioning.starting_inventory or {}
        self.all_technology_reserached = bool(
            task.provisioning.all_technologies_researched
        )
        self.holdout_wait_period = task.holdout_seconds

    def setup_instance(self, instance) -> None:
        return None


class FactorioWorker(ABC):
    """One exclusively leased Factorio simulation worker."""

    worker_id: str

    @abstractmethod
    def start_task(self, task: FactorioTaskSpec) -> str:
        """Reset and provision the task, returning its initial state hash."""

    @abstractmethod
    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        pass

    @abstractmethod
    def observe(self, lease_id: str) -> Observation:
        pass

    @abstractmethod
    def finalize(
        self, lease_id: str, task: FactorioTaskSpec, events: list[ActionEvent]
    ) -> VerificationSnapshot:
        pass

    @abstractmethod
    def release(self) -> None:
        pass


class FLEWorker(FactorioWorker):
    """Factorio worker backed by an existing FLE RCON instance."""

    def __init__(self, worker_id: str, instance: FactorioInstance):
        self.worker_id = worker_id
        self.instance = instance
        self.task = None
        self.task_spec: FactorioTaskSpec | None = None
        self.initial_telemetry: TelemetryFrame | None = None
        self.current_quality: StateQualitySnapshot | None = None
        self.privileged_transitions: list[PrivilegedTransitionPacket] = []
        self._action_events: list[ActionEvent] = []
        self._executed_tools_current: list[str] = []
        self._capture_tool_calls = False
        self.customer_engine: ContractEngine | None = None
        self._customer_events: list[dict] = []
        # Adaptive contract session state (section 14).  The factory is never
        # reset between epochs; only the active order lifecycle rotates.
        self.contract_session_id: str | None = None
        self._contract_baseline_tick: int | None = None
        self._active_order: ActiveOrder | None = None
        self._active_epoch_index: int | None = None
        self._active_commitment_hash: str | None = None
        self._epoch_start_tick: int | None = None
        self._epoch_interventions_base: int = 0
        self._completed_epochs: int = 0
        self._epoch_records: list[ContractEpochOutcome] = []
        self._flow_history: list[tuple[int, dict[str, float]]] = []
        self._observed_unlocked: set[str] = set()
        self._recipe_catalog: ProductCatalog | None = None
        self._last_capture_watermark: tuple[str, int, int, str] | None = None
        self.perturbation_engine: PerturbationEngine | None = None
        self._disruption_events: list[dict] = []
        # Per-capture-cycle caches. The game is paused between interventions,
        # so research and the world hash cannot change while a lease idles;
        # both are invalidated whenever execution may mutate the world.
        self._research_cache = None
        self._state_hash_cache: str | None = None
        self._state_hash_dirty = True
        self._adaptive_depot_placed = False
        for tool_name in getattr(self.instance, "controllers", {}):

            def record_tool(_tool, *_args, _name=tool_name, **_kwargs):
                if self._capture_tool_calls:
                    self._executed_tools_current.append(_name)

            self.instance.pre_tool_hooks.setdefault(tool_name, []).append(record_tool)

    @classmethod
    def connect(
        cls,
        worker_id: str,
        tcp_port: int,
        address: str = "localhost",
    ) -> "FLEWorker":
        instance = FactorioInstance(
            address=address,
            tcp_port=tcp_port,
            fast=True,
            cache_scripts=True,
            inventory={},
            all_technologies_researched=False,
            clear_entities=False,
        )
        return cls(worker_id, instance)

    _SCENARIO_CHECKPOINT = "scenario:default_lab_scenario"

    def start_task(self, task: FactorioTaskSpec) -> str:
        supported = {
            "scenario": "default_lab_scenario",
            "factorio_version": "2.0.73",
            "action_profile": "fle-program-v1",
        }
        requested = {
            "scenario": task.scenario,
            "factorio_version": task.factorio_version,
            "action_profile": task.action_profile,
        }
        unsupported = {
            key: {"requested": requested[key], "supported": expected}
            for key, expected in supported.items()
            if requested[key] != expected
        }
        # Seeds are honored where infrastructure allows: map generation is a
        # container-launch concern, so workers accept any declared value.
        restore_raw: str | None = None
        checkpoint_id = task.checkpoint_id or self._SCENARIO_CHECKPOINT
        if checkpoint_id != self._SCENARIO_CHECKPOINT:
            if not checkpoint_id.startswith("lifecycle:"):
                unsupported["checkpoint_id"] = {
                    "requested": checkpoint_id,
                    "supported": (
                        f"{self._SCENARIO_CHECKPOINT} or lifecycle:<lineage>:ep<N>"
                    ),
                }
            else:
                from fle.envd.lifecycle import CheckpointPool

                restored = CheckpointPool().get(checkpoint_id)
                if restored is None:
                    raise ValueError(
                        f"Checkpoint {checkpoint_id!r} not found in "
                        "FLE_LIFECYCLE_DIR pool"
                    )
                restore_raw = restored[1]
        if unsupported:
            raise ValueError(
                "The first envd backend only supports the pinned default world: "
                f"{unsupported}"
            )
        try:
            fle_task = TaskFactory.create_task(task.backend_task_id or task.task_id)
        except KeyError:
            if task.backend_task_id is not None:
                raise
            if task.verifier.implementation != "objective_engine_v1":
                raise
            # Native specs verify through the objective engine and do not
            # require a legacy registry task.
            fle_task = _NativeFreeplayTask(task)
        if hasattr(fle_task, "holdout_wait_period"):
            fle_task.holdout_wait_period = task.holdout_seconds
        provisioning = task.provisioning
        self.instance.initial_inventory = (
            provisioning.starting_inventory
            if provisioning.starting_inventory is not None
            else fle_task.starting_inventory
        )
        all_research = (
            provisioning.all_technologies_researched
            if provisioning.all_technologies_researched is not None
            else fle_task.all_technology_reserached
        )
        if restore_raw is not None:
            state = GameState.parse_raw(restore_raw)
            # Continuations resume in place: repositioning to spawn would
            # break inherited-factory semantics.
            self.instance.reset(
                game_state=state,
                reset_position=False,
                all_technologies_researched=all_research,
            )
        else:
            # Independent benchmark leases must not inherit the previous
            # agent's location. Reach-limited actions otherwise become
            # task-order dependent after any rollout that moves the character.
            self.instance.reset(
                reset_position=True,
                all_technologies_researched=all_research,
            )
        fle_task.setup_instance(self.instance)
        self.instance.rcon_client.send_command(
            "/sc game.forces.player.character_inventory_slots_bonus = "
            f"{provisioning.character_inventory_slots_bonus}"
        )
        if provisioning.starting_inventory is not None:
            self.instance.first_namespace._set_inventory(
                provisioning.starting_inventory
            )
        for technology in provisioning.researched_technologies:
            technology_name = json.dumps(technology)
            self.instance.rcon_client.send_command(
                "/sc local technology = "
                f"game.forces.player.technologies[{technology_name}]; "
                "if technology then technology.researched = true end"
            )
        self.instance._verified_rocket_launches = 0
        _objective_telemetry(self.instance.first_namespace, reset=True)
        self._epoch_game_tick = self._read_game_tick()
        self._customer_events = []
        self._adaptive_depot_placed = False
        self._active_order = None
        self._active_epoch_index = None
        self._active_commitment_hash = None
        self._epoch_start_tick = None
        self._contract_baseline_tick = None
        self.contract_session_id = None
        self._completed_epochs = 0
        self._epoch_records = []
        self._flow_history = []
        self._observed_unlocked = set()
        self._last_capture_watermark = None
        self.customer_engine = self._setup_customer(task)
        self._disruption_events = []
        self.perturbation_engine = (
            PerturbationEngine(task.perturbations)
            if task.perturbations is not None
            else None
        )
        if self.perturbation_engine is not None:
            # Hidden shocks scheduled at tick 0 are part of the initial
            # world: they apply before the first observation so the initial
            # state hash and telemetry include the damage.
            self._fire_due_shocks(0)
        self._attach_blueprint_store(task)
        self.instance.set_speed(10)
        self.instance.pause()
        self.task = fle_task
        self.task_spec = task
        self._research_cache = None
        self._state_hash_cache = None
        self._state_hash_dirty = True
        targets = [
            objective.target for objective in task.objectives if objective.target
        ]
        self.initial_telemetry = self._capture_frame(targets)
        initial_state_hash = self._current_state_hash()
        self.current_quality = build_state_quality_snapshot(
            task,
            self.initial_telemetry,
            self.initial_telemetry,
            state_hash=initial_state_hash,
        )
        self.privileged_transitions = []
        self._action_events = []
        return initial_state_hash

    def _scores(self) -> tuple[float, float]:
        production, automated = self.instance.first_namespace.score()
        return float(production or 0), float(automated or 0)

    # -- telemetry caching ---------------------------------------------------

    def _current_state_hash(self) -> str:
        """World hash, memoized across the paused window between actions."""

        if self._state_hash_dirty or self._state_hash_cache is None:
            if self._research_cache is None:
                self._research_cache = (
                    self.instance.first_namespace._save_research_state()
                )
            self._state_hash_cache = _instance_state_hash(
                self.instance, research_state=self._research_cache
            )
            self._state_hash_dirty = False
        return self._state_hash_cache

    def _needs_entity_details(self) -> bool:
        spec = self.task_spec
        return any(
            objective.kind in _ENTITY_DETAIL_KINDS
            for objective in (spec.objectives if spec else [])
        )

    def _capture_frame(self, targets: list[str]) -> TelemetryFrame:
        """Telemetry for one capture cycle.

        Research is fetched at most once per cycle and shared with the state
        hash. When no objective consumes per-entity details, the census tool
        replaces the full entity dump (~120ms of Lua serialization plus
        pydantic parsing on even modest factories).
        """

        namespace = self.instance.first_namespace
        if self._research_cache is None:
            self._research_cache = namespace._save_research_state()
        if not self._needs_entity_details():
            return self._light_telemetry(namespace, targets)
        return capture_telemetry(
            self.instance, targets, research_state=self._research_cache
        )

    @staticmethod
    def _target_recipes(namespace: Any, targets: list[str]) -> dict[str, Any]:
        recipes: dict[str, Any] = {}
        for target in sorted(set(targets)):
            try:
                recipes[target] = _jsonable(namespace.get_prototype_recipe(target))
            except Exception as exc:
                recipes[target] = {"available": False, "error": str(exc)}
        return recipes

    def _light_telemetry(self, namespace: Any, targets: list[str]) -> TelemetryFrame:
        """Census-based telemetry frame without per-entity details.

        Research names still populate ``researched`` so dominance comparison
        keeps detecting technology loss; only the heavyweight per-technology
        metadata and entity details are omitted.
        """

        from fle.commons.models.achievements import ProductionFlows

        engine = _objective_telemetry(namespace)
        flows = ProductionFlows.from_dict(namespace._get_production_stats())
        production_score, automated_score = namespace.score()

        census_response: dict = {}
        try:
            census_response = namespace._entity_census() or {}
        except Exception:
            census_response = {}

        entity_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        status_by_name: dict[str, dict[str, int]] = {}
        for name, statuses in (census_response.get("census") or {}).items():
            name_statuses = {
                str(status): int(count) for status, count in (statuses or {}).items()
            }
            total_for_name = sum(name_statuses.values())
            entity_counts[name] = entity_counts.get(name, 0) + total_for_name
            merged = status_by_name.setdefault(name, {})
            for status, count in name_statuses.items():
                status_counts[status] = status_counts.get(status, 0) + count
                merged[status] = merged.get(status, 0) + count

        researched: dict[str, bool] = {}
        current_research = None
        research_progress = 0.0
        research_state = self._research_cache
        if research_state is not None:
            try:
                researched = {
                    str(name): bool(tech.researched)
                    for name, tech in research_state.technologies.items()
                }
                if research_state.current_research:
                    current_research = str(research_state.current_research)
                research_progress = float(research_state.research_progress or 0)
            except Exception:
                pass

        return TelemetryFrame(
            tick=int(self.instance.get_elapsed_ticks()),
            inventory=_numeric_dict(namespace.inspect_inventory()),
            flows=flows,
            production_score=float(production_score or 0),
            automated_production_score=float(automated_score or 0),
            researched=researched,
            technologies={},
            current_research=current_research,
            research_progress=research_progress,
            entity_counts=entity_counts,
            entity_status_counts=status_counts,
            entity_status_by_name=status_by_name,
            entity_details=[],
            rocket_launches=int(engine.get("rockets_launched", 0) or 0),
            target_recipes=self._target_recipes(namespace, targets),
            character_alive=bool(engine.get("character_alive", True)),
            character_health=(
                float(engine["character_health"])
                if isinstance(engine.get("character_health"), (int, float))
                else None
            ),
            deaths=list(engine.get("deaths", []) or []),
            death_count=int(engine.get("death_count", 0) or 0),
            respawn_count=int(engine.get("respawn_count", 0) or 0),
            last_respawn_tick=(
                int(engine["last_respawn_tick"])
                if isinstance(engine.get("last_respawn_tick"), (int, float))
                else None
            ),
            resource_depletions=list(engine.get("resource_depletions", []) or []),
            pollution_total=float(engine.get("pollution_total", 0) or 0),
            pollution_emitted=float(engine.get("pollution_emitted", 0) or 0),
            produced=_numeric_dict(engine.get("produced", {})),
            consumed=_numeric_dict(engine.get("consumed", {})),
        )

    # -- customer contract plumbing -----------------------------------------

    _DEPOT_OFFSET = (-6.0, -10.0)

    def _setup_customer(self, task: FactorioTaskSpec) -> ContractEngine | None:
        """Place immutable sink depots and arm the hidden demand schedule."""

        spec = task.customer
        if spec is None:
            try:
                # Adaptive open-play sessions have no hidden schedule, but
                # still need a real customer-owned sink for each committed
                # order.  Place the depots once at lease start so the agent can
                # discover and use them across all epochs.
                if task.adaptive_contract_session:
                    placement = self.instance.first_namespace._customer_depot(
                        "place", self._DEPOT_OFFSET[0], self._DEPOT_OFFSET[1], 8, True
                    )
                    if not isinstance(placement, dict) or not placement.get("placed"):
                        raise RuntimeError(
                            "Could not place adaptive customer sink depots"
                        )
                    self._adaptive_depot_placed = True
                else:
                    self.instance.first_namespace._customer_depot("clear")
            except Exception:
                if not task.adaptive_contract_session:
                    pass
                else:
                    raise
            return None
        anchor_x, anchor_y = self._DEPOT_OFFSET
        placement = self.instance.first_namespace._customer_depot(
            "place", anchor_x, anchor_y, spec.depot_chests, True
        )
        if isinstance(placement, dict) and not placement.get("placed"):
            raise RuntimeError(
                "Could not place customer sink depots near the spawn area"
            )
        engine = ContractEngine(spec)
        # Orders may be issued at tick 0; reveal them before the first action.
        self._customer_events.extend(engine.sync(0, []))
        return engine

    def _sync_customer(self) -> list[VerifierEvent]:
        """Pull sink telemetry and advance the contract clock to now."""

        engine = self.customer_engine
        if engine is None:
            return []
        telemetry: dict = {}
        try:
            telemetry = self.instance.first_namespace._customer_depot("telemetry") or {}
        except Exception:
            telemetry = {}
        current_tick = int(telemetry.get("tick") or 0)
        raw_buckets = telemetry.get("buckets") or {}
        if isinstance(raw_buckets, dict):
            # slpp decodes Lua arrays as index-keyed dicts.
            raw_bucket_list = [
                raw_buckets[key] for key in sorted(raw_buckets, key=lambda k: int(k))
            ]
        else:
            raw_bucket_list = list(raw_buckets)
        buckets = [
            DeliveryBucket(
                start_tick=int(bucket.get("start_tick") or 0),
                items={
                    str(item): float(count)
                    for item, count in (bucket.get("items") or {}).items()
                },
            )
            for bucket in raw_bucket_list
        ]
        events = engine.sync(current_tick, buckets)
        verifier_events = [
            VerifierEvent(
                event_id=f"contract:{payload['order_id']}:{payload['event']}",
                kind=payload["event"],
                tick=payload["tick"],
                source="verifier",
                payload=payload,
            )
            for payload in events
        ]
        self._customer_events.extend(events)
        return verifier_events

    def _contracts_view(self) -> list[OpenContractView]:
        engine = self.customer_engine
        contracts = list(engine.student_view()) if engine is not None else []
        if self._active_order is not None:
            contracts.append(self._active_order.student_view())
        return contracts

    def _sync_active_order(self) -> list[VerifierEvent]:
        """Credit adaptive-order deliveries and advance its authoritative clock."""

        order = self._active_order
        if order is None or order.status != "open":
            return []
        payloads: list[dict] = []
        for bucket_tick, bucket_items in self._drain_delivery_buckets():
            expiry = order.sync(bucket_tick)
            if expiry:
                payloads.append(expiry)
            delivery = order.attribute(
                float(bucket_items.get(order.item_name, 0.0)), bucket_tick
            )
            if delivery:
                payloads.append(delivery)
        current_tick = self._read_game_tick()
        relative_tick = max(current_tick - getattr(self, "_epoch_game_tick", 0), 0)
        terminal = order.sync(relative_tick)
        if terminal:
            payloads.append(terminal)
        self._customer_events.extend(payloads)
        return [
            VerifierEvent(
                event_id=(
                    f"adaptive-contract:{self._active_epoch_index}:"
                    f"{payload['event']}:{payload['tick']}"
                ),
                kind=str(payload["event"]),
                tick=int(payload["tick"]),
                source="verifier",
                payload=payload,
            )
            for payload in payloads
        ]

    # -- adaptive contract epoch lifecycle (section 14) -----------------------

    @property
    def contract_catalog(self) -> ProductCatalog:
        """Memoized recipe catalog over the live namespace (per worker)."""
        if self._recipe_catalog is None:
            self._recipe_catalog = ProductCatalog(
                NamespaceRecipeDataSource(self.instance.first_namespace)
            )
        return self._recipe_catalog

    def capture_contract_context(
        self, session_id: str, epoch_index: int
    ) -> ContractContextSnapshot:
        """Passive snapshot; never mutates simulation state."""
        if self.task is None:
            raise RuntimeError("Worker has no active task")
        namespace = self.instance.first_namespace
        tick = self._read_game_tick()
        relative_tick = max(tick - getattr(self, "_epoch_game_tick", 0), 0)
        # Sample cumulative outputs for the rate windows before freezing.
        try:
            stats = namespace._get_production_stats() or {}
            outputs_now = {
                str(item): float(amount or 0.0)
                for item, amount in (stats.get("output") or {}).items()
            }
        except Exception:
            outputs_now = {}
        self._record_flow_sample(relative_tick, outputs_now)
        snapshot = capture_context_snapshot(
            namespace,
            session_id=session_id,
            epoch_index=epoch_index,
            captured_tick=relative_tick,
            map_seed_hash=self.contract_map_seed_hash(),
            prior_watermark=self._last_capture_watermark,
            flow_history=self._flow_history,
            observed_unlocked_recipes=self._observed_unlocked,
        )
        self._last_capture_watermark = snapshot.watermark()
        return snapshot

    def _record_flow_sample(self, tick: int, outputs: dict[str, float]) -> None:
        """Ring-buffer of cumulative output samples (capped, deduplicated)."""
        if self._flow_history and self._flow_history[-1][0] == tick:
            self._flow_history[-1] = (tick, outputs)
        else:
            self._flow_history.append((tick, outputs))
        if len(self._flow_history) > 64:
            del self._flow_history[: len(self._flow_history) - 64]

    def contract_map_seed_hash(self) -> str:
        try:
            seed = self.instance.rcon_client.send_command(
                "/sc rcon.print(game.default_map_gen_settings.seed)"
            )
            return hashlib.sha256(str(seed).strip().encode()).hexdigest()[:32]
        except Exception:
            return "unknown"

    def _prior_contract_watermark(
        self, session_id: str
    ) -> tuple[str, int, int, str] | None:
        if (
            self._last_capture_watermark is not None
            and self._last_capture_watermark[0] == session_id
        ):
            return self._last_capture_watermark
        return None

    def begin_contract_epoch(self, spec: ContractEpochSpec) -> ActiveContractState:
        if self.task is None:
            raise RuntimeError("Worker has no active task")
        if self._active_order is not None:
            raise EpochAlreadyActive(
                f"Lease {self.worker_id} already holds an open epoch "
                f"(index {self._active_epoch_index})"
            )
        expected = self._completed_epochs + 1
        if spec.epoch_index != expected:
            raise EpochMismatch(
                f"Expected epoch index {expected}, got {spec.epoch_index}"
            )
        if (
            self.contract_session_id is not None
            and spec.session_id != self.contract_session_id
        ):
            raise EpochMismatch("Session id cannot change within one lease")

        now = self._read_game_tick()
        relative_now = max(now - getattr(self, "_epoch_game_tick", 0), 0)
        order = ActiveOrder(
            item_name=spec.item_name,
            requested_quantity=spec.quantity,
            deadline_ticks=spec.deadline_ticks,
            activation_tick=relative_now,
        )
        self.contract_session_id = spec.session_id
        if self._contract_baseline_tick is None:
            self._contract_baseline_tick = now
        self._active_order = order
        self._active_epoch_index = spec.epoch_index
        self._active_commitment_hash = spec.commitment_hash
        self._epoch_start_tick = now
        self._epoch_interventions_base = len(self._action_events)
        # Orders may complete at tick 0 of the window only through deliveries;
        # arm the clock without advancing it.
        self._customer_events.append(
            {"event": "contract_issued", "order": spec.item_name, "tick": relative_now}
        )
        return ActiveContractState(
            lease_id=self.worker_id,
            session_id=spec.session_id,
            epoch_index=spec.epoch_index,
            spec_commitment_hash=spec.commitment_hash,
            open_order=order.student_view(),
            epoch_start_tick=relative_now,
        )

    def finalize_contract_epoch(
        self,
        epoch_index: int,
        commitment_hash: str,
        *,
        abandon: bool = False,
        infrastructure_interrupt: bool = False,
    ) -> ContractEpochOutcome:
        order = self._active_order
        if order is None or self._active_epoch_index is None:
            raise NoActiveEpoch("No open contract epoch on this lease")
        if epoch_index != self._active_epoch_index:
            raise EpochMismatch(
                f"Active epoch is {self._active_epoch_index}, got {epoch_index}"
            )
        if (
            self._active_commitment_hash is not None
            and commitment_hash != self._active_commitment_hash
        ):
            raise CommitmentMismatch("Finalization commitment does not match epoch")
        # Attribute sink deliveries up to now, then close out.  Sync schedule
        # engines and pull sink telemetry first.
        self._sync_customer()
        current_tick = self._read_game_tick()
        relative_tick = max(current_tick - getattr(self, "_epoch_game_tick", 0), 0)
        for bucket_tick, bucket_items in self._drain_delivery_buckets():
            amount = float(bucket_items.get(order.item_name, 0.0))
            if amount <= 0:
                continue
            # Close the order at the bucket boundary before attributing it;
            # this makes late deliveries impossible while retaining all
            # qualifying buckets already observed before an interruption.
            if not (abandon or infrastructure_interrupt):
                expiry_event = order.sync(bucket_tick)
                if expiry_event:
                    self._customer_events.append(expiry_event)
            event = order.attribute(amount, bucket_tick)
            if event:
                self._customer_events.append(event)
        # Drain qualifying deliveries before abandonment so an interrupted
        # provider does not erase the partial work completed before failure.
        if (abandon or infrastructure_interrupt) and order.status == "open":
            order.abandon(relative_tick)
        outcome_state = order.evaluate(relative_tick)
        if order.status == "open":
            expiry_event = order.sync(relative_tick)
            if expiry_event:
                self._customer_events.append(expiry_event)
            outcome_state = order.evaluate(relative_tick)

        delivered_int = min(
            int(round(outcome_state.delivered_quantity)),
            outcome_state.requested_quantity,
        )
        ratio = outcome_state.completion_ratio

        status_map = {
            "fulfilled": "fulfilled",
            "partial": "partial",
            "expired": "expired",
            "abandoned": "abandoned",
        }
        # Section 5: an infrastructure interruption is never recorded as an
        # order loss; delivery accounting stays in the retained record.
        status = status_map[outcome_state.status]
        if infrastructure_interrupt:
            status = "infrastructure_error"
        interventions_used = len(self._action_events) - self._epoch_interventions_base
        record = ContractEpochOutcome(
            session_id=self.contract_session_id or "",
            epoch_index=epoch_index,
            commitment_hash=commitment_hash,
            status=status,
            delivered_quantity=delivered_int,
            requested_quantity=outcome_state.requested_quantity,
            completion_ratio=round(ratio, 6),
            simulation_ticks_used=relative_tick - (self._epoch_start_tick_relative()),
            interventions_used=interventions_used,
            model_seconds=0.0,  # runner-owned clocks (section 5)
            tool_seconds=0.0,
            runner_wall_seconds=0.0,
            first_delivery_tick=(outcome_state.first_delivery_tick),
            completion_tick=outcome_state.completion_tick,
            terminal_state_digest=self._current_state_hash(),
        )
        self._epoch_records.append(record)
        self._completed_epochs += 1
        # Active customer state cleared after finalization (section 14).
        self._active_order = None
        self._active_epoch_index = None
        self._active_commitment_hash = None
        self._epoch_start_tick = None
        return record

    def _epoch_start_tick_relative(self) -> int:
        if self._epoch_start_tick is None:
            return 0
        return max(self._epoch_start_tick - getattr(self, "_epoch_game_tick", 0), 0)

    def _drain_delivery_buckets(self) -> list[tuple[int, dict[str, float]]]:
        """Pull sink telemetry as chronological (tick, items) samples."""
        engine_telemetry: dict = {}
        try:
            engine_telemetry = (
                self.instance.first_namespace._customer_depot("telemetry") or {}
            )
        except Exception:
            return []
        current_tick = int(engine_telemetry.get("tick") or 0)
        raw_buckets = engine_telemetry.get("buckets") or {}
        if isinstance(raw_buckets, dict):
            raw_list = [
                raw_buckets[key] for key in sorted(raw_buckets, key=lambda k: int(k))
            ]
        else:
            raw_list = list(raw_buckets)
        samples: list[tuple[int, dict[str, float]]] = []
        for bucket in raw_list:
            start = int(bucket.get("start_tick") or 0)
            end = start + DELIVERY_BUCKET_TICKS - 1
            items = {
                str(item): float(count)
                for item, count in (bucket.get("items") or {}).items()
            }
            samples.append((min(end, current_tick) or start, items))
        return sorted(samples, key=lambda s: s[0])

    def get_contract_session_state(self) -> ContractSessionState:
        now = self._read_game_tick()
        baseline = self._contract_baseline_tick
        session_ticks = max(now - baseline, 0) if baseline is not None else 0
        epoch_ticks = (
            max(now - self._epoch_start_tick, 0)
            if self._epoch_start_tick is not None
            else 0
        )
        return ContractSessionState(
            lease_id=self.worker_id,
            session_id=self.contract_session_id or "",
            session_simulation_ticks=session_ticks,
            epoch_simulation_ticks=epoch_ticks,
            completed_epoch_count=self._completed_epochs,
            active_epoch_index=self._active_epoch_index,
            active_commitment_hash=None,  # service layer fills from its ledger
            agent_interventions=len(self._action_events),
        )

    def finalize_contract_session(self) -> ContractSessionSummary:
        if self._active_order is not None:
            raise EpochAlreadyActive("Cannot finalize a session with an open epoch")
        total_delivered = sum(r.delivered_quantity for r in self._epoch_records)
        total_requested = sum(r.requested_quantity for r in self._epoch_records)
        return ContractSessionSummary(
            session_id=self.contract_session_id or "",
            session_simulation_ticks=self.get_contract_session_state().session_simulation_ticks,
            epochs=list(self._epoch_records),
            fulfilled_epochs=sum(
                1 for r in self._epoch_records if r.status == "fulfilled"
            ),
            total_delivered=total_delivered,
            total_requested=total_requested,
        )

    # -- episode clock -------------------------------------------------------

    def _read_game_tick(self) -> int:
        try:
            response = self.instance.rcon_client.send_command(
                "/sc rcon.print(game.tick)"
            )
            return int(str(response).strip() or 0)
        except Exception:
            return 0

    def _episode_tick(self) -> int:
        """Canonical episode-relative simulation tick (game.tick - epoch).

        All schedule semantics -- contract deadlines, disruption triggers --
        run on this clock so timing cannot drift against absolute server
        ticks accumulated across episodes on one worker.
        """

        return max(self._read_game_tick() - getattr(self, "_epoch_game_tick", 0), 0)

    # -- perturbations -------------------------------------------------------

    def _fire_due_shocks(
        self, episode_tick: int, stats: dict | None = None
    ) -> list[VerifierEvent]:
        engine = self.perturbation_engine
        if engine is None:
            return []

        def _fire(command: str, params: dict) -> dict:
            try:
                return (
                    self.instance.first_namespace._perturbation(command, params) or {}
                )
            except Exception as exc:  # noqa: BLE001 - degrade to failed
                return {"error": str(exc)}

        events = engine.sync(episode_tick, stats, _fire)
        verifier_events = [
            VerifierEvent(
                event_id=(
                    f"perturbation:{payload['perturbation_id']}:{payload['event']}"
                ),
                kind=(
                    payload["event"]
                    if payload["event"]
                    in ("perturbation_applied", "recovery_completed")
                    else "custom"
                ),
                tick=(
                    payload.get("applied_tick")
                    or payload.get("recovered_tick", episode_tick)
                ),
                source="verifier",
                payload=payload,
            )
            for payload in events
        ]
        self._disruption_events.extend(events)
        return verifier_events

    def _sync_perturbations(self) -> list[VerifierEvent]:
        """Fire due disruptions and update recovery tracking."""

        if self.perturbation_engine is None:
            return []
        stats: dict = {}
        try:
            stats = self.instance.first_namespace._get_production_stats() or {}
        except Exception:
            stats = {}
        return self._fire_due_shocks(self._episode_tick(), stats=stats)

    def _attach_blueprint_store(self, task: FactorioTaskSpec) -> None:
        """Provision the generation-scoped blueprint library (or ephemeral)."""

        namespace = self.instance.first_namespace
        scope = task.blueprint_scope
        store = None
        if scope:
            try:
                store = BlueprintStore(scope=scope)
            except Exception:
                store = None
        namespace._blueprint_store = store

    def _blueprint_summaries(self) -> list[BlueprintSummary]:
        namespace = self.instance.first_namespace
        store = getattr(namespace, "_ephemeral_blueprints", None)
        scoped = getattr(namespace, "_blueprint_store", None)
        active = scoped or store
        if active is None:
            return []
        try:
            summaries = active.list_summaries()
        except Exception:
            return []
        return [BlueprintSummary(**summary) for summary in summaries]

    def export_game_state(self) -> str | None:
        """Serialize the live world for lifecycle checkpointing.

        Trainer-side callers persist the returned blob through a
        ``CheckpointPool``; a later lease restores it via
        ``FactorioTaskSpec`` provisioning of that state.
        """

        try:
            return GameState.from_instance(self.instance).to_raw()
        except Exception:
            return None

    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        before, _ = self._scores()
        started = datetime.now(timezone.utc)
        # The world may mutate during evaluation; both caches are invalid
        # from this point until the next capture cycle completes.
        self._state_hash_dirty = True
        self._research_cache = None
        self._executed_tools_current = []
        self._capture_tool_calls = True
        self.instance.set_speed_and_unpause(10)
        try:
            _, duration, result = self.instance.eval(code, timeout=120)
        finally:
            self._capture_tool_calls = False
            # Model generation and network latency must not advance simulation time.
            self.instance.pause()
        result_text = str(result)
        error = "error" in result_text.lower() or "exception:" in result_text.lower()
        forbidden_actions = {
            str(action)
            for constraint in (self.task_spec.constraints if self.task_spec else [])
            if constraint.kind == "forbidden_action"
            for action in constraint.parameters.get(
                "actions",
                [constraint.limit] if constraint.limit is not None else [],
            )
        }
        executed_tools = list(self._executed_tools_current)
        # FactorioNamespace.eval_with_timeout always calls score() after the
        # submitted program. That verifier-internal call is not a policy action.
        if executed_tools and executed_tools[-1] == "score":
            executed_tools.pop()
        policy_violations = [
            tool for tool in executed_tools if tool in forbidden_actions
        ]
        targets = [
            objective.target
            for objective in (self.task_spec.objectives if self.task_spec else [])
            if objective.target
        ]
        throughput_measurements: dict[str, list[float]] = {}
        holdout_ticks = 0
        transition_holdout = (
            self.task_spec.verifier.transition_holdout_seconds
            if self.task_spec
            and self.task_spec.verifier.implementation == "objective_engine_v1"
            and self.task_spec.verifier.emit_transition_comparisons
            else 0
        )
        if transition_holdout and self.task_spec is not None:
            self.instance.set_speed_and_unpause(10)
            try:
                current_frame, throughput_measurements, holdout_ticks = (
                    measure_autonomous_holdout(
                        self.instance,
                        self.task_spec,
                        transition_holdout,
                    )
                )
            finally:
                self.instance.pause()
        else:
            current_frame = self._capture_frame(targets)

        after = current_frame.production_score
        automated = current_frame.automated_production_score
        state_hash = self._current_state_hash()
        character_died = bool(
            self.initial_telemetry
            and current_frame.death_count > self.initial_telemetry.death_count
        )
        terminal_reason = "character_died" if character_died else None
        event = ActionEvent(
            sequence=sequence,
            code_sha256=hashlib.sha256(code.encode()).hexdigest(),
            started_at=started,
            duration_seconds=duration,
            reward_delta=after - before,
            error=error,
            result=result_text,
            ticks=current_frame.tick,
            executed_tools=executed_tools,
            policy_violations=policy_violations,
        )
        self._action_events.append(event)
        if (
            self.task_spec is not None
            and self.initial_telemetry is not None
            and self.task_spec.verifier.implementation == "objective_engine_v1"
            and self.task_spec.verifier.emit_transition_comparisons
        ):
            current_quality = build_state_quality_snapshot(
                self.task_spec,
                self.initial_telemetry,
                current_frame,
                state_hash=state_hash,
                action_events=self._action_events,
                throughput_measurements=throughput_measurements,
                horizon_ticks=holdout_ticks,
            )
            previous_quality = self.current_quality
            if previous_quality is not None:
                self.privileged_transitions.append(
                    PrivilegedTransitionPacket(
                        task_id=self.task_spec.task_id,
                        sequence=sequence,
                        previous=previous_quality,
                        current=current_quality,
                        comparison=compare_state_quality(
                            previous_quality,
                            current_quality,
                        ),
                    )
                )
            self.current_quality = current_quality
        verifier_event = VerifierEvent(
            event_id=f"action:{sequence}",
            kind="invalid_action" if error else "intervention_executed",
            tick=event.ticks,
            source="environment",
            payload={
                "sequence": sequence,
                "code_sha256": event.code_sha256,
                "duration_seconds": duration,
                "executed_tools": executed_tools,
                "policy_violations": policy_violations,
            },
            evidence={"result": result_text} if error else {},
            reward_channels={"invalid_action": -1.0} if error else {},
        )
        emitted_events = [verifier_event]
        emitted_events.extend(self._sync_customer())
        emitted_events.extend(self._sync_active_order())
        emitted_events.extend(self._sync_perturbations())
        if character_died:
            deaths = current_frame.deaths
            latest_death = deaths[-1] if deaths else {}
            emitted_events.append(
                VerifierEvent(
                    event_id=f"lifecycle:death:action:{sequence}",
                    kind="character_died",
                    tick=int(latest_death.get("tick", event.ticks)),
                    source="engine",
                    payload={
                        "sequence": sequence,
                        "train_involved": latest_death.get("train") is not None,
                    },
                    evidence=latest_death,
                )
            )
        return ExecutionResult(
            lease_id=lease_id,
            event=event,
            production_score=after,
            automated_production_score=automated,
            state_hash=state_hash,
            events=emitted_events,
            terminal_reason=terminal_reason,
        )

    def observe(self, lease_id: str) -> Observation:
        self._sync_active_order()
        production, automated = self._scores()
        namespace = self.instance.first_namespace
        inventory = _jsonable(namespace.inspect_inventory())
        stats = _jsonable(namespace._get_production_stats())
        return Observation(
            lease_id=lease_id,
            task_id=self.task_spec.task_id if self.task_spec else "unknown",
            ticks=self.instance.get_elapsed_ticks(),
            inventory=inventory,
            production_score=production,
            automated_production_score=automated,
            production=stats,
            state_hash=self._current_state_hash(),
            contracts=self._contracts_view(),
            blueprints=self._blueprint_summaries(),
        )

    def finalize(
        self, lease_id: str, task: FactorioTaskSpec, events: list[ActionEvent]
    ) -> VerificationSnapshot:
        if self.task is None:
            raise RuntimeError("Worker has no active task")

        production, automated = self._scores()
        if task.verifier.implementation == "objective_engine_v1":
            if self.initial_telemetry is None:
                raise RuntimeError("Native verifier has no initial telemetry")
            self._sync_customer()
            if self.perturbation_engine is not None:
                self._sync_perturbations()
                disruption_summary = self.perturbation_engine.summary()
            else:
                disruption_summary = None
            customer_result = None
            if self.customer_engine is not None:
                customer_result = self.customer_engine.evaluate(
                    self.customer_engine.current_tick,
                    receipt_context={
                        "lease_id": lease_id,
                        "task_id": task.task_id,
                        "worker_id": self.worker_id,
                    },
                )
            self.instance.set_speed_and_unpause(10)
            try:
                # Holdout windows advance the world; the memoized hash must
                # not survive them.
                self._state_hash_dirty = True
                self._research_cache = None
                native = verify_native(
                    self.instance,
                    task,
                    events,
                    self.initial_telemetry,
                    customer_result=customer_result,
                )
            finally:
                self.instance.pause()
            return VerificationSnapshot(
                lease_id=lease_id,
                task_id=task.task_id,
                task_fingerprint=task.fingerprint,
                success=native.success,
                scalar_reward=native.scalar_reward,
                rewards=native.rewards,
                metrics=native.metrics,
                evidence={
                    "verifier": "objective_engine_v1",
                    "task_family": task.task_family,
                    "backend_task_id": task.backend_task_id or task.task_id,
                    "objective_ids": [
                        objective.objective_id for objective in task.objectives
                    ],
                    "scalarization": task.verifier.scalarization,
                    **(
                        {
                            "customer_commitment": customer_result.commitment,
                            "customer_receipt_mac": customer_result.receipt_mac,
                        }
                        if customer_result is not None
                        else {}
                    ),
                    **(
                        {"disruption_summary": disruption_summary}
                        if disruption_summary is not None
                        else {}
                    ),
                },
                terminal_state_hash=self._current_state_hash(),
                action_events=events,
                events=[
                    *[
                        VerifierEvent(
                            event_id=f"action:{event.sequence}",
                            kind=(
                                "invalid_action"
                                if event.error
                                else "intervention_executed"
                            ),
                            tick=event.ticks,
                            source="environment",
                            payload={
                                "sequence": event.sequence,
                                "code_sha256": event.code_sha256,
                            },
                            reward_channels=(
                                {"invalid_action": -1.0} if event.error else {}
                            ),
                        )
                        for event in events
                    ],
                    *[
                        VerifierEvent(
                            event_id=(
                                f"contract:{payload['order_id']}:{payload['event']}"
                            ),
                            kind=payload["event"],
                            tick=payload["tick"],
                            source="verifier",
                            payload=payload,
                        )
                        for payload in self._customer_events
                    ],
                    *[
                        VerifierEvent(
                            event_id=(
                                f"perturbation:{payload['perturbation_id']}:"
                                f"{payload['event']}"
                            ),
                            kind=(
                                payload["event"]
                                if payload["event"]
                                in ("perturbation_applied", "recovery_completed")
                                else "custom"
                            ),
                            tick=(
                                payload.get("applied_tick")
                                or payload.get("recovered_tick", 0)
                            ),
                            source="verifier",
                            payload=payload,
                        )
                        for payload in self._disruption_events
                    ],
                    *native.events,
                ],
                termination_reason=native.termination_reason,
                privileged_diagnostics=native.diagnostics,
                privileged_transitions=self.privileged_transitions,
            )

        self.instance.set_speed_and_unpause(10)
        try:
            response = self.task.verify(production, self.instance, step_statistics={})
        finally:
            self.instance.pause()
        metrics = _jsonable(response.meta)
        scalar = float(metrics.get(REWARD_OVERRIDE_KEY, float(response.success)))
        throughput = max(
            (
                float(value)
                for key, value in metrics.items()
                if "throughput" in str(key).lower() and isinstance(value, (int, float))
            ),
            default=0.0,
        )
        invalid = -float(sum(event.error for event in events))
        primary_objective = task.objectives[0] if task.objectives else None
        verification_event = VerifierEvent(
            event_id="verification:final",
            kind="objective_satisfied" if response.success else "objective_failed",
            tick=self.instance.get_elapsed_ticks(),
            source="verifier",
            objective_id=(
                primary_objective.objective_id if primary_objective else None
            ),
            payload={
                "success": bool(response.success),
                "scalar_reward": scalar,
                "task_family": task.task_family,
            },
            evidence={"metrics": metrics},
            reward_channels={
                "task": float(response.success),
                "throughput": throughput,
            },
        )
        return VerificationSnapshot(
            lease_id=lease_id,
            task_id=task.task_id,
            task_fingerprint=task.fingerprint,
            success=bool(response.success),
            scalar_reward=scalar,
            rewards=RewardVector(
                task=float(response.success),
                throughput=throughput,
                automation=max(automated, 0.0),
                progress=production,
                invalid_action=invalid,
            ),
            metrics={
                **metrics,
                "production_score": production,
                "automated_production_score": automated,
                "automation_reward": max(automated, 0.0),
                "automation_reward_basis": "nonnegative_legacy_net_value_delta",
                "interventions": len(events),
                "scored_interventions": sum(
                    not event.evaluation_retry for event in events
                ),
                "evaluation_retries": sum(event.evaluation_retry for event in events),
            },
            evidence={
                "verifier": type(self.task).__name__,
                "task_family": task.task_family,
                "backend_task_id": task.backend_task_id or task.task_id,
                "objective_ids": [
                    objective.objective_id for objective in task.objectives
                ],
                "scalarization": task.verifier.scalarization,
            },
            terminal_state_hash=self._current_state_hash(),
            action_events=events,
            events=[
                *[
                    VerifierEvent(
                        event_id=f"action:{event.sequence}",
                        kind=(
                            "invalid_action" if event.error else "intervention_executed"
                        ),
                        tick=event.ticks,
                        source="environment",
                        payload={
                            "sequence": event.sequence,
                            "code_sha256": event.code_sha256,
                            "evaluation_retry": event.evaluation_retry,
                        },
                        reward_channels=(
                            {"invalid_action": -1.0} if event.error else {}
                        ),
                    )
                    for event in events
                ],
                verification_event,
                VerifierEvent(
                    event_id="verification:completed",
                    kind="verification_completed",
                    tick=self.instance.get_elapsed_ticks(),
                    source="verifier",
                    payload={"success": bool(response.success)},
                ),
            ],
            termination_reason=(
                "success"
                if response.success
                else (
                    "character_died"
                    if int(
                        _objective_telemetry(self.instance.first_namespace).get(
                            "death_count", 0
                        )
                        or 0
                    )
                    else "finalized"
                )
            ),
        )

    def release(self) -> None:
        # Release is the last-resort cleanup path used when a provider or
        # transport fails before the runner can finalize its open epoch.
        if self._active_order is not None and self._active_epoch_index is not None:
            try:
                self.finalize_contract_epoch(
                    self._active_epoch_index,
                    self._active_commitment_hash or "",
                    infrastructure_interrupt=True,
                )
            except Exception:
                # Continue releasing the Factorio lease even if telemetry is
                # unavailable; the caller must never strand a worker.
                self._active_order = None
                self._active_epoch_index = None
                self._active_commitment_hash = None
        self.instance.pause()
        self.customer_engine = None
        self._customer_events = []
        self.perturbation_engine = None
        self._disruption_events = []
        try:
            namespace = self.instance.first_namespace
            namespace._blueprint_store = None
            if hasattr(namespace, "_ephemeral_blueprints"):
                delattr(namespace, "_ephemeral_blueprints")
        except Exception:
            pass
        try:
            if self.task_spec is not None and hasattr(
                self.instance.first_namespace, "_customer_depot"
            ):
                self.instance.first_namespace._customer_depot("clear")
        except Exception:
            pass
        self.task = None
        self.task_spec = None
        self._active_order = None
        self._active_epoch_index = None
        self._active_commitment_hash = None
        self._epoch_start_tick = None
        self.contract_session_id = None
        self._contract_baseline_tick = None
        self._completed_epochs = 0
        self._epoch_records = []
        self._adaptive_depot_placed = False
        self.initial_telemetry = None
        self.current_quality = None
        self.privileged_transitions = []
        self._action_events = []
