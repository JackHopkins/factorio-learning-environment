from __future__ import annotations

import hashlib
import json
import math
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fle.commons.constants import REWARD_OVERRIDE_KEY
from fle.commons.models.game_state import GameState
from fle.commons.models.research_state import ResearchState, research_state_identity
from fle.env import FactorioInstance
from fle.envd.blueprints import BlueprintStore
from fle.envd.contract_features import (
    NamespaceRecipeDataSource,
    ProductCatalog,
    capture_context_snapshot,
)
from fle.envd.customer import (
    DELIVERY_BUCKET_TICKS,
    ActiveOrder,
    ContractEngine,
    DeliveryBucket,
)
from fle.envd.errors import (
    CommitmentMismatch,
    EpochAlreadyActive,
    EpochMismatch,
    NoActiveEpoch,
)
from fle.envd.models import (
    ActionEvent,
    ActiveContractState,
    BlueprintSummary,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ContractEpochSpec,
    ContractSessionState,
    ContractSessionSummary,
    CustomerDepotView,
    DepotDeliveryTelemetry,
    DeliveryReceipt,
    ExecutionResult,
    FactorioTaskSpec,
    Observation,
    OpenContractView,
    PrivilegedTransitionPacket,
    RewardVector,
    StateQualitySnapshot,
    ThroughputCheckResult,
    ThroughputAuditResult,
    VerificationSnapshot,
    VerifierEvent,
    canonical_hash,
)
from fle.env.utils.achievements import calculate_achievements
from fle.commons.models.achievements import ProductionFlows
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
from fle.envd.perturbations import PerturbationEngine
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

# The model-facing observation stream is intentionally much shorter than the
# authoritative worker ledgers.  Old production/delivery/action records stay
# available to typed history queries, while only this many compact snapshots
# are needed to validate cursors and calculate a delta.
MODEL_OBSERVATION_HISTORY_LIMIT = 256
MODEL_OBSERVATION_KEYFRAME_INTERVAL = 20
MODEL_OBSERVATION_KEYFRAME_TICKS = 5 * 60 * 60
MODEL_HISTORY_QUERY_LIMIT = 128


@dataclass(frozen=True)
class ThroughputAuditCandidate:
    """Private snapshot captured only after the cheap detector fires."""

    lease_id: str
    session_id: str
    epoch_index: int
    state: GameState
    state_hash: str
    candidate_tick: int
    detector_rates: dict[str, float]
    target_rates: dict[str, float]
    depot_specs: list[dict[str, Any]]
    audit_spec: Any
    commitment_hash: str


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


def _numeric_mapping(value: Any) -> dict[str, float]:
    """Coerce a Factorio counter mapping without preserving Lua wrappers."""

    raw = _jsonable(value)
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for key, item in raw.items():
        if isinstance(item, bool):
            continue
        try:
            number = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            result[str(key)] = number
    return result


def _normalise_counter_mapping(value: Any) -> dict[str, int | float]:
    """Serialize counters compactly while keeping integer quantities readable."""

    result: dict[str, int | float] = {}
    for key, number in _numeric_mapping(value).items():
        result[key] = int(number) if number.is_integer() else round(number, 6)
    return result


def _counter_delta(
    before: dict[str, float], after: dict[str, float]
) -> dict[str, int | float]:
    values: dict[str, int | float] = {}
    for key in sorted(set(before) | set(after)):
        change = after.get(key, 0.0) - before.get(key, 0.0)
        if abs(change) <= 1e-9:
            continue
        values[key] = int(change) if change.is_integer() else round(change, 6)
    return values


def _compact_counter_mapping(value: dict[str, float]) -> dict[str, int | float]:
    return _normalise_counter_mapping(value)


def _empty_research_state() -> ResearchState:
    """Provide a serializable placeholder when only the identity is available."""

    return ResearchState(
        technologies={},
        current_research=None,
        research_progress=0.0,
        research_queue=[],
        progress={},
    )


def _instance_state_hash(
    instance: FactorioInstance,
    *,
    research_state=None,
    research_identity: dict[str, Any] | None = None,
) -> str:
    # A compact identity does not satisfy GameState's full research model, but
    # the rest of the world capture still benefits from the same serializer.
    # Use an empty model as a carrier and replace it with the identity below.
    state_for_capture = research_state
    if state_for_capture is not None and not isinstance(
        state_for_capture, ResearchState
    ):
        if research_identity is None:
            research_identity = research_state_identity(state_for_capture)
        state_for_capture = _empty_research_state()
    if state_for_capture is None and research_identity is not None:
        state_for_capture = _empty_research_state()
    captured_state = GameState.from_instance(
        instance, research_state=state_for_capture
    )
    raw = json.loads(captured_state.to_raw())
    raw.pop("timestamp", None)
    raw["research"] = research_state_identity(
        captured_state.research if research_identity is None else research_identity
    )
    return canonical_hash(raw)


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
    def observe(
        self,
        lease_id: str,
        *,
        cursor: str | None = None,
        force_keyframe: bool = False,
    ) -> Observation:
        pass

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
        """Return public state history when a worker implements that surface."""

        raise NotImplementedError

    def check_contract_throughput(
        self, lease_id: str, *, authoritative: bool = False
    ) -> ThroughputCheckResult:
        """Advance an intervention-free qualification window."""
        raise NotImplementedError

    def pop_throughput_audit_candidate(self) -> ThroughputAuditCandidate | None:
        return None

    def run_throughput_audit(
        self, candidate: ThroughputAuditCandidate
    ) -> ThroughputAuditResult:
        raise NotImplementedError

    def accept_throughput_audit(self, result: ThroughputAuditResult) -> None:
        raise NotImplementedError

    def record_throughput_audit(self, result: ThroughputAuditResult) -> None:
        return None

    def set_throughput_audit_enabled(self, enabled: bool) -> None:
        return None

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
        self._active_epoch_spec: ContractEpochSpec | None = None
        self._active_factory_band: int | None = None
        self._active_target_band: int | None = None
        self._epoch_start_tick: int | None = None
        self._epoch_interventions_base: int = 0
        self._completed_epochs: int = 0
        self._epoch_records: list[ContractEpochOutcome] = []
        self._flow_history: list[tuple[int, dict[str, float]]] = []
        # Authoritative production samples are compact cumulative counters;
        # they do not contain the per-craft payload that made old observations
        # grow without bound.
        self._production_history: list[dict[str, Any]] = []
        self._contract_production_baseline: dict[str, dict[str, float]] = {
            "input": {},
            "output": {},
        }
        # Sink buckets are drained for order attribution, but their physical
        # timing is retained independently for raw-coverage and throughput
        # diagnostics.
        self._delivery_history: list[tuple[int, dict[str, float]]] = []
        self._delivery_raw_totals: dict[str, float] = {}
        self._manual_delivery_history: list[tuple[int, dict[str, float]]] = []
        self._manual_delivery_totals: dict[str, float] = {}
        self._delivery_observed_tick: int = 0
        self._contract_delivery_baseline: dict[str, float] = {}
        self._observed_unlocked: set[str] = set()
        self._recipe_catalog: ProductCatalog | None = None
        self._last_capture_watermark: tuple[str, int, int, str] | None = None
        self._authoritative_throughput_check: ThroughputCheckResult | None = None
        self._throughput_audit_result: ThroughputAuditResult | None = None
        self._throughput_audit_attempts: list[ThroughputAuditResult] = []
        self._pending_throughput_candidate: ThroughputAuditCandidate | None = None
        self._executing_lease_id: str | None = None
        self._throughput_detector_dirty = False
        self._throughput_audit_enabled = False
        self._throughput_audit_retry_after_tick = 0
        self.perturbation_engine: PerturbationEngine | None = None
        self._disruption_events: list[dict] = []
        # Per-capture-cycle caches. The game is paused between interventions,
        # so research and the world hash cannot change while a lease idles;
        # both are invalidated whenever execution may mutate the world.
        self._research_cache = None
        self._state_hash_cache: str | None = None
        self._state_hash_dirty = True
        self._adaptive_depot_placed = False
        self._customer_depots_cache: list[CustomerDepotView] = []
        # Revisioned model-facing observation state.  The source ledgers above
        # remain authoritative; this ring only backs cursor validation and
        # delta construction.
        self._observation_revision = 0
        self._observation_history: list[dict[str, Any]] = []
        self._latest_model_state: dict[str, Any] | None = None
        # Append-only compact transitions back historical public queries.  It
        # intentionally stores deltas, not a second copy of every snapshot.
        self._public_state_history: list[dict[str, Any]] = []
        self._observation_nonce = secrets.token_hex(8)
        self._observation_keyframe_revision = 0
        self._observation_keyframe_id = ""
        self._observation_keyframe_pending = True
        for tool_name in getattr(self.instance, "controllers", {}):

            def record_tool(_tool, *_args, _name=tool_name, **_kwargs):
                if self._capture_tool_calls and _name != "get_recent_rate":
                    self._executed_tools_current.append(_name)

            self.instance.pre_tool_hooks.setdefault(tool_name, []).append(record_tool)

            def detect_throughput(_tool, _result, _name=tool_name):
                if _name not in {"get_recent_rate", "score"}:
                    self._throughput_detector_dirty = True

            self.instance.post_tool_hooks.setdefault(tool_name, []).append(
                detect_throughput
            )

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
        self._customer_depots_cache = []
        self._active_order = None
        self._active_epoch_index = None
        self._active_commitment_hash = None
        self._active_epoch_spec = None
        self._active_factory_band = None
        self._active_target_band = None
        self._epoch_start_tick = None
        self._contract_baseline_tick = None
        self.contract_session_id = None
        self._completed_epochs = 0
        self._epoch_records = []
        self._flow_history = []
        self._production_history = []
        self._contract_production_baseline = {"input": {}, "output": {}}
        self._delivery_history = []
        self._delivery_raw_totals = {}
        self._manual_delivery_history = []
        self._manual_delivery_totals = {}
        self._delivery_observed_tick = 0
        self._contract_delivery_baseline = {}
        self._observed_unlocked = set()
        self._last_capture_watermark = None
        self._authoritative_throughput_check = None
        self._throughput_audit_result = None
        self._throughput_audit_attempts = []
        self._throughput_audit_retry_after_tick = 0
        self._pending_throughput_candidate = None
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
        self._observation_revision = 0
        self._observation_history = []
        self._latest_model_state = None
        self._public_state_history = []
        self._observation_nonce = secrets.token_hex(8)
        self._observation_keyframe_revision = 0
        self._observation_keyframe_id = ""
        self._observation_keyframe_pending = True
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
            research_state = self._research_cache
            research_identity = None
            if research_state is None:
                namespace = self.instance.first_namespace
                try:
                    captured = namespace._save_research_state()
                except Exception:
                    # Full research saves contain static prerequisites and
                    # ingredients and may exceed Factorio's RCON response
                    # limit. Retry through the sparse identity form so a
                    # terminal contract digest can still be produced.
                    try:
                        captured = namespace._save_research_state(compact=True)
                    except Exception:
                        captured = None
                    research_identity = research_state_identity(captured)
                else:
                    if isinstance(captured, ResearchState):
                        research_state = captured
                        self._research_cache = captured
                    else:
                        # Keep malformed tool output out of GameState while
                        # retaining any identity fields it did provide.
                        research_identity = research_state_identity(captured)
            self._state_hash_cache = _instance_state_hash(
                self.instance,
                research_state=research_state,
                research_identity=research_identity,
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

    @staticmethod
    def _lua_array(value: Any) -> list[Any]:
        if isinstance(value, dict):

            def sort_key(key: Any) -> tuple[int, str]:
                try:
                    return (0, f"{int(key):020d}")
                except (TypeError, ValueError):
                    return (1, str(key))

            return [value[key] for key in sorted(value, key=sort_key)]
        return list(value or [])

    def _cache_customer_depots(self, telemetry: dict[str, Any]) -> None:
        raw_depots = self._lua_array(telemetry.get("depots"))
        depots: list[CustomerDepotView] = []
        for index, raw in enumerate(raw_depots, start=1):
            if not isinstance(raw, dict) or not raw.get("valid", True):
                continue
            position = raw.get("position") or {}
            if not isinstance(position, dict):
                continue
            try:
                x = float(position["x"])
                y = float(position["y"])
            except (KeyError, TypeError, ValueError):
                continue
            unit_number = raw.get("unit_number")
            try:
                parsed_unit = int(unit_number) if unit_number is not None else None
            except (TypeError, ValueError):
                parsed_unit = None
            depot_id = (
                f"customer-depot-{parsed_unit}"
                if parsed_unit is not None
                else f"customer-depot-{index}"
            )
            depots.append(
                CustomerDepotView(
                    depot_id=depot_id,
                    unit_number=parsed_unit,
                    entity_name="steel-chest",
                    position={"x": x, "y": y},
                    surface=(str(raw["surface"]) if raw.get("surface") else None),
                )
            )
        if "depots" in telemetry:
            self._customer_depots_cache = depots

    @staticmethod
    def _parse_delivery_buckets(
        telemetry: dict[str, Any],
        *,
        item_field: str = "items",
    ) -> tuple[int, list[tuple[int, dict[str, float]]]]:
        """Normalize Lua/RCON delivery buckets to chronological samples."""

        current_tick = int(telemetry.get("tick") or 0)
        raw_buckets = telemetry.get("buckets") or []
        if isinstance(raw_buckets, dict):
            raw_buckets = [
                raw_buckets[key]
                for key in sorted(raw_buckets, key=lambda key: int(key))
            ]
        samples: list[tuple[int, dict[str, float]]] = []
        for bucket in raw_buckets:
            if not isinstance(bucket, dict):
                continue
            start = int(bucket.get("start_tick") or 0)
            end = start + DELIVERY_BUCKET_TICKS - 1
            sample_tick = min(max(current_tick, start), end)
            items = {
                str(item): float(count)
                for item, count in (bucket.get(item_field) or {}).items()
                if float(count or 0.0) > 0
            }
            if items:
                samples.append((sample_tick, items))
        return current_tick, sorted(samples, key=lambda sample: sample[0])

    def _record_delivery_samples(
        self,
        telemetry: dict[str, Any],
        samples: list[tuple[int, dict[str, float]]],
    ) -> None:
        """Retain physical sink traffic after the Lua delta log is drained."""

        history = getattr(self, "_delivery_history", None)
        if history is None:
            history = self._delivery_history = []
        raw_totals = getattr(self, "_delivery_raw_totals", None)
        if raw_totals is None:
            raw_totals = self._delivery_raw_totals = {}
        current_tick = int(telemetry.get("tick") or 0)
        self._delivery_observed_tick = max(
            getattr(self, "_delivery_observed_tick", 0), current_tick
        )
        for sample_tick, items in samples:
            history.append((sample_tick, dict(items)))
            for item, amount in items.items():
                raw_totals[item] = raw_totals.get(item, 0.0) + amount
        # Lua's cumulative counter remains authoritative if the process has
        # observed a bucket before this Python worker was restarted.
        reported = telemetry.get("raw_delivery_totals") or telemetry.get(
            "delivered_total"
        )
        if isinstance(reported, dict):
            for item, amount in reported.items():
                raw_totals[str(item)] = max(
                    raw_totals.get(str(item), 0.0), float(amount or 0.0)
                )
        # Keep the compact physical ledger authoritative for the lifetime of
        # the run. Model observations expose only a bounded recent projection;
        # historical queries read this ledger instead of the snapshot ring.

    def _record_manual_delivery_samples(
        self,
        telemetry: dict[str, Any],
        samples: list[tuple[int, dict[str, float]]],
    ) -> None:
        """Retain direct agent-to-depot traffic as non-crediting audit data."""

        history = getattr(self, "_manual_delivery_history", None)
        if history is None:
            history = self._manual_delivery_history = []
        totals = getattr(self, "_manual_delivery_totals", None)
        if totals is None:
            totals = self._manual_delivery_totals = {}
        for sample_tick, items in samples:
            history.append((sample_tick, dict(items)))
            for item, amount in items.items():
                totals[item] = totals.get(item, 0.0) + amount
        reported = telemetry.get("manual_delivery_totals")
        if isinstance(reported, dict):
            for item, amount in reported.items():
                totals[str(item)] = max(
                    totals.get(str(item), 0.0), float(amount or 0.0)
                )
        # Manual traffic follows the same retention rule as raw delivery. It
        # remains separate so direct insertion can never become credited flow.

    def _delivery_telemetry_snapshot(
        self, *, recent_limit: int = 120
    ) -> DepotDeliveryTelemetry:
        """Build a stable raw-delivery view for observations and contexts."""

        history = list(getattr(self, "_delivery_history", []))
        observed = max(
            getattr(self, "_delivery_observed_tick", 0),
            max((tick for tick, _ in history), default=0),
        )
        totals = {
            str(item): round(float(amount), 6)
            for item, amount in getattr(self, "_delivery_raw_totals", {}).items()
            if amount > 0
        }
        manual_history = list(getattr(self, "_manual_delivery_history", []))
        manual_totals = {
            str(item): round(float(amount), 6)
            for item, amount in getattr(self, "_manual_delivery_totals", {}).items()
            if amount > 0
        }

        def rate(window_ticks: int) -> dict[str, float]:
            cutoff = observed - window_ticks
            values: dict[str, float] = {}
            for tick, items in history:
                if cutoff < tick <= observed:
                    for item, amount in items.items():
                        values[item] = values.get(item, 0.0) + amount
            minutes = window_ticks / 3600.0
            return {
                item: round(amount / minutes, 6)
                for item, amount in values.items()
                if amount > 0
            }

        recent = [
            {
                "start_tick": max(
                    tick - DELIVERY_BUCKET_TICKS + 1, 0
                ),
                "end_tick": tick,
                "items": {
                    item: round(float(amount), 6) for item, amount in items.items()
                },
            }
            for tick, items in history[-max(0, recent_limit) :]
        ]
        return DepotDeliveryTelemetry(
            observed_until_tick=observed,
            bucket_ticks=DELIVERY_BUCKET_TICKS,
            sample_count=len(history),
            raw_totals=totals,
            manual_totals=manual_totals,
            raw_rates_60s=rate(3600),
            raw_rates_300s=rate(18000),
            raw_rates_5s=rate(300),
            since_contract_totals={
                str(item): round(
                    max(
                        float(amount)
                        - getattr(self, "_contract_delivery_baseline", {}).get(
                            item, 0.0
                        ),
                        0.0,
                    ),
                    6,
                )
                for item, amount in totals.items()
                if amount
                > getattr(self, "_contract_delivery_baseline", {}).get(item, 0.0)
            },
            recent_buckets=recent,
            manual_sample_count=len(manual_history),
            recent_manual_buckets=[
                {
                    "start_tick": max(tick - DELIVERY_BUCKET_TICKS + 1, 0),
                    "end_tick": tick,
                    "items": {
                        item: round(float(amount), 6)
                        for item, amount in items.items()
                    },
                }
                for tick, items in manual_history[-max(0, recent_limit) :]
            ],
        )

    def _delivery_totals(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for contract in self._contracts_view():
            for item, amount in contract.fulfilled.items():
                totals[item] = totals.get(item, 0.0) + float(amount)
        return totals

    def _delivery_receipt(
        self,
        executed_tools: list[str],
        delivered_before: dict[str, float],
    ) -> DeliveryReceipt | None:
        attempted_insert = "insert_item" in executed_tools
        contracts = self._contracts_view()
        delivered_after = self._delivery_totals()
        credited = {
            item: round(amount - delivered_before.get(item, 0.0), 4)
            for item, amount in delivered_after.items()
            if amount - delivered_before.get(item, 0.0) > 1e-9
        }
        if not attempted_insert and not credited:
            return None
        remaining: dict[str, float] = {}
        for contract in contracts:
            for item, amount in contract.remaining.items():
                remaining[item] = remaining.get(item, 0.0) + float(amount)
        open_contract = next(
            (contract for contract in contracts if contract.status == "open"),
            contracts[-1] if contracts else None,
        )
        if credited:
            message = (
                "Automated customer delivery credited. Depot inventories are "
                "drained immediately, so an empty depot is expected."
            )
        elif contracts:
            message = (
                "No customer delivery was credited by this intervention. "
                "Customer contracts credit only automated inserter-fed traffic "
                "into customer_depot_ids; direct agent insertion is audit-only."
            )
        else:
            message = "No customer contract is currently active."
        return DeliveryReceipt(
            credited=credited,
            remaining={item: round(amount, 4) for item, amount in remaining.items()},
            contract_status=open_contract.status if open_contract else None,
            customer_depot_ids=[
                depot.depot_id for depot in self._customer_depots_cache
            ],
            message=message,
        )

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
                    depot_telemetry = (
                        self.instance.first_namespace._customer_depot("telemetry")
                        or {}
                    )
                    self._cache_customer_depots(depot_telemetry)
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
        depot_telemetry = (
            self.instance.first_namespace._customer_depot("telemetry") or {}
        )
        self._cache_customer_depots(depot_telemetry)
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
        self._cache_customer_depots(telemetry)
        current_tick, raw_bucket_list = self._parse_delivery_buckets(telemetry)
        self._record_delivery_samples(telemetry, raw_bucket_list)
        _, manual_bucket_list = self._parse_delivery_buckets(
            telemetry, item_field="manual_items"
        )
        self._record_manual_delivery_samples(telemetry, manual_bucket_list)
        buckets = [
            DeliveryBucket(
                start_tick=max(
                    sample_tick - (sample_tick % DELIVERY_BUCKET_TICKS), 0
                ),
                items=items,
            )
            for sample_tick, items in raw_bucket_list
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
            for line in order.products:
                delivery = order.attribute(
                    float(bucket_items.get(line.product, 0.0)),
                    bucket_tick,
                    product=line.product,
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
            delivery_telemetry=self._delivery_telemetry_snapshot(),
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
            products=spec.products or None,
            order_kind=spec.order_kind,
        )
        self.contract_session_id = spec.session_id
        if self._contract_baseline_tick is None:
            self._contract_baseline_tick = now
        self._active_order = order
        self._active_epoch_index = spec.epoch_index
        self._active_commitment_hash = spec.commitment_hash
        self._active_epoch_spec = spec
        self._active_factory_band = (
            spec.factory_band
            if spec.factory_band is not None
            else spec.context.factory_band
        )
        self._active_target_band = (
            spec.target_band
            if spec.target_band is not None
            else (
                spec.features.target_band
                if spec.features.target_band is not None
                else spec.features.stage_band
            )
        )
        self._epoch_start_tick = now
        self._epoch_interventions_base = len(self._action_events)
        # Epoch-relative production and delivery aggregates start at the
        # committed order boundary.  They are public operational counters,
        # independent of the hidden rating/audit ledgers.
        self._contract_production_baseline = self._production_counters()
        self._contract_delivery_baseline = dict(self._delivery_raw_totals)
        self._observation_keyframe_pending = True
        self._authoritative_throughput_check = None
        self._throughput_audit_result = None
        self._throughput_audit_attempts = []
        self._throughput_audit_retry_after_tick = 0
        self._pending_throughput_candidate = None
        # Orders may complete at tick 0 of the window only through deliveries;
        # arm the clock without advancing it.
        self._customer_events.append(
            {
                "event": "contract_issued",
                "order": spec.item_name,
                "products": [line.model_dump() for line in order.products],
                "kind": spec.order_kind,
                "tick": relative_now,
            }
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
            # Close the order at the bucket boundary before attributing it;
            # this makes late deliveries impossible while retaining all
            # qualifying buckets already observed before an interruption.
            if not (abandon or infrastructure_interrupt):
                expiry_event = order.sync(bucket_tick)
                if expiry_event:
                    self._customer_events.append(expiry_event)
            for line in order.products:
                amount = float(bucket_items.get(line.product, 0.0))
                if amount <= 0:
                    continue
                event = order.attribute(amount, bucket_tick, product=line.product)
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
            round(outcome_state.delivered_quantity),
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
            delivered_by_product={
                product: round(amount, 6)
                for product, amount in outcome_state.delivered_by_product.items()
            },
            requested_by_product=dict(outcome_state.requested_by_product),
            completion_ratio=round(ratio, 6),
            performance_score=round(ratio, 6),
            simulation_ticks_used=max(
                relative_tick
                - self._epoch_start_tick_relative()
                - (
                    self._authoritative_throughput_check.window_ticks
                    if self._authoritative_throughput_check is not None
                    and self._throughput_audit_result is None
                    else 0
                ),
                0,
            ),
            interventions_used=interventions_used,
            model_seconds=0.0,  # runner-owned clocks (section 5)
            tool_seconds=0.0,
            runner_wall_seconds=0.0,
            first_delivery_tick=(outcome_state.first_delivery_tick),
            completion_tick=outcome_state.completion_tick,
            terminal_state_digest=self._current_state_hash(),
            factory_band=self._active_factory_band,
            target_band=self._active_target_band,
            delivery_telemetry={
                "physical": self._delivery_telemetry_snapshot().model_dump(
                    mode="json"
                ),
                "order": outcome_state.delivery_telemetry,
            },
            autonomous_throughput=self._authoritative_throughput_check,
            throughput_audit=self._throughput_audit_result,
            throughput_audit_attempts=list(self._throughput_audit_attempts),
        )
        self._epoch_records.append(record)
        self._completed_epochs += 1
        # Active customer state cleared after finalization (section 14).
        self._active_order = None
        self._active_epoch_index = None
        self._active_commitment_hash = None
        self._active_epoch_spec = None
        self._active_factory_band = None
        self._active_target_band = None
        self._epoch_start_tick = None
        self._authoritative_throughput_check = None
        self._throughput_audit_result = None
        self._throughput_audit_attempts = []
        self._throughput_audit_retry_after_tick = 0
        self._pending_throughput_candidate = None
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
        self._cache_customer_depots(engine_telemetry)
        _current_tick, samples = self._parse_delivery_buckets(engine_telemetry)
        self._record_delivery_samples(engine_telemetry, samples)
        _, manual_samples = self._parse_delivery_buckets(
            engine_telemetry, item_field="manual_items"
        )
        self._record_manual_delivery_samples(engine_telemetry, manual_samples)
        return samples

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

    def _maybe_capture_throughput_candidate(self) -> None:
        """Run the cheap detector after a public tool and snapshot once."""

        order = self._active_order
        spec = getattr(self, "_active_epoch_spec", None)
        lease_id = self._executing_lease_id
        if not self._throughput_audit_enabled or lease_id is None:
            return
        if (
            self._pending_throughput_candidate is not None
            or self._throughput_audit_result is not None
            or self._episode_tick() < self._throughput_audit_retry_after_tick
        ):
            return
        if (
            order is not None
            and spec is not None
            and order.status == "open"
            and order.order_kind == "sustained"
            and spec.throughput_audit is not None
        ):
            audit = spec.throughput_audit
            deadline_minutes = max(order.deadline_ticks / 3600.0, 1e-9)
            targets = {
                line.product: float(line.quantity) / deadline_minutes
                for line in order.products
            }
            session_id = self.contract_session_id or ""
            epoch_index = self._active_epoch_index or 1
            commitment_hash = self._active_commitment_hash or ""
            depot_specs = [
                {"position": dict(depot.position), "surface": depot.surface}
                for depot in self._customer_depots_cache
            ]
        else:
            task = self.task_spec
            audit = task.throughput_audit if task is not None else None
            objectives = [
                objective
                for objective in (task.objectives if task is not None else [])
                if objective.kind == "throughput"
                and objective.comparator == "gte"
                and objective.target is not None
                and objective.threshold is not None
                and objective.window_seconds
            ]
            if audit is None or not objectives:
                return
            targets = {
                str(objective.target): float(objective.threshold)
                / (float(objective.window_seconds) / 60.0)
                for objective in objectives
            }
            session_id = task.task_id
            epoch_index = 1
            commitment_hash = task.fingerprint
            depot_specs = []
        previous_capture = self._capture_tool_calls
        self._capture_tool_calls = False
        try:
            rates: dict[str, float] = {}
            for product in targets:
                result = self.instance.first_namespace._get_recent_rate(
                    product, audit.detector_window_seconds
                )
                if not isinstance(result, dict) or result.get("error"):
                    return
                rates[product] = float(result.get("dynamic_per_minute", 0.0))
            if any(
                rates.get(product, 0.0) < target * audit.detector_trigger_ratio
                for product, target in targets.items()
            ):
                return
            research = self.instance.first_namespace._save_research_state()
            state = GameState.from_instance(self.instance, research_state=research)
            raw = json.loads(state.to_raw())
            raw.pop("timestamp", None)
            state_hash = canonical_hash(raw)
            self._pending_throughput_candidate = ThroughputAuditCandidate(
                lease_id=lease_id,
                session_id=session_id,
                epoch_index=epoch_index,
                state=state,
                state_hash=state_hash,
                candidate_tick=self._episode_tick(),
                detector_rates=rates,
                target_rates=targets,
                depot_specs=depot_specs,
                audit_spec=audit,
                commitment_hash=commitment_hash,
            )
        finally:
            self._capture_tool_calls = previous_capture

    def set_throughput_audit_enabled(self, enabled: bool) -> None:
        self._throughput_audit_enabled = bool(enabled)

    def pop_throughput_audit_candidate(self) -> ThroughputAuditCandidate | None:
        candidate = self._pending_throughput_candidate
        self._pending_throughput_candidate = None
        return candidate

    @staticmethod
    def _audit_production_delta(
        before: ProductionFlows, after: ProductionFlows, product: str
    ) -> float:
        achievements = calculate_achievements(before, after)
        return float(achievements["dynamic"].get(product, 0.0))

    def run_throughput_audit(
        self, candidate: ThroughputAuditCandidate
    ) -> ThroughputAuditResult:
        """Restore a candidate into this reserved worker and test autonomy."""

        audit = candidate.audit_spec
        self.instance.reset(
            game_state=candidate.state,
            all_technologies_researched=False,
            clear_entities=True,
        )
        self.instance.pause()
        adopted = self.instance.first_namespace._customer_depot.adopt(
            candidate.depot_specs
        )

        def advance(seconds: int) -> int:
            if seconds <= 0:
                return 0
            start_tick = self._read_game_tick()
            self.instance.set_speed_and_unpause(audit.audit_game_speed)
            try:
                self.instance.first_namespace.sleep(seconds)
            finally:
                self.instance.pause()
            observed_ticks = max(self._read_game_tick() - start_tick, 0)
            return observed_ticks or seconds * 60

        def depot_totals() -> dict[str, float]:
            telemetry = self.instance.first_namespace._customer_depot("telemetry") or {}
            return {
                str(key): float(value)
                for key, value in (telemetry.get("raw_delivery_totals") or {}).items()
            }

        advance(audit.burn_in_seconds)
        before_flows = ProductionFlows.from_dict(
            self.instance.first_namespace._get_production_stats()
        )
        before_depot = depot_totals()
        subwindow = audit.subwindow_seconds
        min_chunks = audit.holdout_seconds_min // subwindow
        max_chunks = audit.holdout_seconds_max // subwindow
        chunks = min_chunks + secrets.randbelow(max_chunks - min_chunks + 1)
        holdout_seconds = chunks * subwindow
        production_windows = {product: [] for product in candidate.target_rates}
        depot_windows = {product: [] for product in candidate.target_rates}
        subwindow_ticks: list[int] = []
        last_flows = before_flows
        last_depot = before_depot
        for _ in range(chunks):
            elapsed_ticks = advance(subwindow)
            subwindow_ticks.append(elapsed_ticks)
            elapsed_minutes = elapsed_ticks / 3600.0
            current_flows = ProductionFlows.from_dict(
                self.instance.first_namespace._get_production_stats()
            )
            current_depot = depot_totals()
            for product in candidate.target_rates:
                produced = self._audit_production_delta(
                    last_flows, current_flows, product
                )
                delivered = max(
                    current_depot.get(product, 0.0)
                    - last_depot.get(product, 0.0),
                    0.0,
                )
                production_windows[product].append(
                    produced / max(elapsed_minutes, 1e-9)
                )
                depot_windows[product].append(
                    delivered / max(elapsed_minutes, 1e-9)
                )
            last_flows = current_flows
            last_depot = current_depot

        production_rates = {
            product: sum(values) / len(values)
            for product, values in production_windows.items()
        }
        depot_rates = {
            product: sum(values) / len(values)
            for product, values in depot_windows.items()
        }
        line_scores: dict[str, float] = {}
        failures: list[str] = []
        adopted_count = int(adopted.get("adopted", 0)) if isinstance(adopted, dict) else 0
        for product, target in candidate.target_rates.items():
            ratios = [production_rates.get(product, 0.0) / max(target, 1e-9)]
            floor = target * audit.subwindow_floor_ratio
            ratios.append(
                min(production_windows.get(product) or [0.0]) / max(floor, 1e-9)
            )
            if audit.require_depot_service:
                ratios.append(depot_rates.get(product, 0.0) / max(target, 1e-9))
                ratios.append(
                    min(depot_windows.get(product) or [0.0]) / max(floor, 1e-9)
                )
            line_scores[product] = min(min(ratios), 1.0)
            if line_scores[product] < 1.0 - 1e-9:
                failures.append(f"{product}:rate_or_subwindow_below_threshold")
        if audit.require_depot_service and adopted_count < len(candidate.depot_specs):
            failures.append("customer_depot_clone_incomplete")
        return ThroughputAuditResult(
            lease_id=candidate.lease_id,
            session_id=candidate.session_id,
            epoch_index=candidate.epoch_index,
            audit_worker_id=self.worker_id,
            candidate_tick=candidate.candidate_tick,
            candidate_state_hash=candidate.state_hash,
            detector_window_seconds=audit.detector_window_seconds,
            detector_rates_per_minute=candidate.detector_rates,
            target_rates_per_minute=candidate.target_rates,
            burn_in_seconds=audit.burn_in_seconds,
            holdout_seconds=holdout_seconds,
            holdout_ticks=sum(subwindow_ticks),
            subwindow_seconds=subwindow,
            subwindow_ticks=subwindow_ticks,
            production_rates_per_minute=production_rates,
            depot_rates_per_minute=depot_rates,
            production_subwindow_rates=production_windows,
            depot_subwindow_rates=depot_windows,
            line_scores=line_scores,
            passed=not failures,
            failure_reasons=failures,
        )

    def accept_throughput_audit(self, result: ThroughputAuditResult) -> None:
        order = self._active_order
        if order is None:
            if (
                not result.passed
                or self.task_spec is None
                or result.session_id != self.task_spec.task_id
            ):
                raise RuntimeError("Throughput audit does not match the active task")
            self._throughput_audit_result = result
            return
        if (
            order.status != "open"
            or not result.passed
            or result.session_id != (self.contract_session_id or "")
            or result.epoch_index != self._active_epoch_index
        ):
            raise RuntimeError("Throughput audit does not match the active order")
        self._throughput_audit_result = result
        event = order.certify_sustained(
            self._episode_tick(), result.model_dump(mode="json")
        )
        self._customer_events.append(event)

    def record_throughput_audit(self, result: ThroughputAuditResult) -> None:
        self._throughput_audit_attempts.append(result)
        if not result.passed:
            detector_seconds = (
                self._active_epoch_spec.throughput_audit.detector_window_seconds
                if self._active_epoch_spec is not None
                and self._active_epoch_spec.throughput_audit is not None
                else 5
            )
            self._throughput_audit_retry_after_tick = (
                self._episode_tick() + detector_seconds * 60
            )

    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        before, _ = self._scores()
        delivered_before = self._delivery_totals()
        started = datetime.now(timezone.utc)
        # The world may mutate during evaluation; both caches are invalid
        # from this point until the next capture cycle completes.
        self._state_hash_dirty = True
        self._research_cache = None
        self._executed_tools_current = []
        self._capture_tool_calls = True
        self._executing_lease_id = lease_id
        self._throughput_detector_dirty = False
        self.instance.set_speed_and_unpause(10)
        try:
            _, duration, result = self.instance.eval(code, timeout=120)
        finally:
            self._capture_tool_calls = False
            # Model generation and network latency must not advance simulation time.
            self.instance.pause()
        try:
            if self._throughput_detector_dirty:
                self._maybe_capture_throughput_candidate()
        finally:
            self._executing_lease_id = None
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
        delivery_receipt = self._delivery_receipt(executed_tools, delivered_before)
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
            delivery_receipt=delivery_receipt,
            production_score=after,
            automated_production_score=automated,
            state_hash=state_hash,
            events=emitted_events,
            terminal_reason=terminal_reason,
        )

    # -- revisioned model-facing state -------------------------------------

    def _production_counters(self, stats: dict[str, Any] | None = None) -> dict[str, dict[str, float]]:
        if stats is None:
            try:
                stats = _jsonable(self.instance.first_namespace._get_production_stats())
            except Exception:
                stats = {}
        stats = stats if isinstance(stats, dict) else {}
        return {
            "input": _numeric_mapping(stats.get("input", {})),
            "output": _numeric_mapping(stats.get("output", {})),
        }

    def _record_production_sample(
        self,
        tick: int,
        counters: dict[str, dict[str, float]],
        *,
        revision: int = 0,
    ) -> None:
        history = getattr(self, "_production_history", None)
        if history is None:
            history = self._production_history = []
        sample = {
            "tick": int(tick),
            "revision": int(revision),
            "input": dict(counters.get("input", {})),
            "output": dict(counters.get("output", {})),
        }
        if history and history[-1]["tick"] == sample["tick"]:
            # A repeated capture at a paused tick should refresh counters,
            # rather than create a fake zero-length rate sample.
            if sample["revision"]:
                history[-1]["revision"] = sample["revision"]
            history[-1]["input"] = sample["input"]
            history[-1]["output"] = sample["output"]
        else:
            history.append(sample)
        # Contract-feature capture uses the older output-only history. Keep it
        # in sync so existing candidate generation retains its semantics.
        self._record_flow_sample(int(tick), dict(counters.get("output", {})))

    @staticmethod
    def _window_counter_rate(
        samples: list[dict[str, Any]], field: str, window_seconds: int
    ) -> dict[str, int | float]:
        if len(samples) < 2:
            return {}
        ordered = sorted(samples, key=lambda sample: int(sample.get("tick", 0)))
        latest = ordered[-1]
        latest_tick = int(latest.get("tick", 0))
        cutoff = latest_tick - max(int(window_seconds), 1) * 60
        baseline = next(
            (
                sample
                for sample in reversed(ordered[:-1])
                if int(sample.get("tick", 0)) <= cutoff
            ),
            ordered[0],
        )
        baseline_tick = int(baseline.get("tick", 0))
        span_ticks = latest_tick - baseline_tick
        if span_ticks <= 0:
            return {}
        latest_values = _numeric_mapping(latest.get(field, {}))
        baseline_values = _numeric_mapping(baseline.get(field, {}))
        minutes = span_ticks / 3600.0
        values: dict[str, int | float] = {}
        for item in sorted(set(latest_values) | set(baseline_values)):
            amount = max(latest_values.get(item, 0.0) - baseline_values.get(item, 0.0), 0.0)
            if amount <= 1e-9:
                continue
            rate = amount / minutes
            values[item] = int(rate) if rate.is_integer() else round(rate, 6)
        return values

    def _compact_production_snapshot(
        self,
        stats: dict[str, Any],
        tick: int,
        *,
        record_sample: bool = True,
    ) -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
        counters = self._production_counters(stats)
        if record_sample:
            self._record_production_sample(tick, counters)
        history = list(getattr(self, "_production_history", []))
        baseline = getattr(
            self,
            "_contract_production_baseline",
            {"input": {}, "output": {}},
        )
        raw_rates = {
            "5s": self._window_counter_rate(history, "output", 5),
            "60s": self._window_counter_rate(history, "output", 60),
            "300s": self._window_counter_rate(history, "output", 300),
        }
        automated_rates: dict[str, dict[str, int | float]] = {
            "5s": {},
            "60s": {},
            "300s": {},
        }
        automated_available = False
        recent_rate = getattr(self.instance.first_namespace, "_get_recent_rate", None)
        if recent_rate is not None:
            # Keep this bounded: the model needs rates for the active output
            # frontier, not a second serialization of every production item.
            for item in sorted(counters["output"])[:32]:
                for window in (5, 60, 300):
                    try:
                        response = _jsonable(recent_rate(item, window))
                    except Exception:
                        response = None
                    if not isinstance(response, dict) or response.get("error"):
                        continue
                    dynamic = response.get("dynamic_per_minute")
                    if dynamic is None:
                        continue
                    try:
                        number = max(float(dynamic), 0.0)
                    except (TypeError, ValueError):
                        continue
                    automated_rates[f"{window}s"][item] = (
                        int(number) if number.is_integer() else round(number, 6)
                    )
                    automated_available = True
        compact = {
            "input": _compact_counter_mapping(counters["input"]),
            "output": _compact_counter_mapping(counters["output"]),
            "raw_rates_5s": raw_rates["5s"],
            "raw_rates_60s": raw_rates["60s"],
            "raw_rates_300s": raw_rates["300s"],
            "automated_rates_5s": automated_rates["5s"],
            "automated_rates_60s": automated_rates["60s"],
            "automated_rates_300s": automated_rates["300s"],
            "automated_rates_available": automated_available,
            "since_contract": {
                "raw_input": _counter_delta(
                    baseline.get("input", {}), counters["input"]
                ),
                "raw_output": _counter_delta(
                    baseline.get("output", {}), counters["output"]
                ),
            },
        }
        return compact, counters

    def _entity_summary(self) -> dict[str, Any]:
        response: dict[str, Any] = {}
        try:
            response = _jsonable(self.instance.first_namespace._entity_census() or {})
        except Exception:
            response = {}
        counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        status_by_name: dict[str, dict[str, int]] = {}
        census = response.get("census") if isinstance(response, dict) else {}
        for name, statuses in (census or {}).items():
            per_name: dict[str, int] = {}
            for status, count in (statuses or {}).items():
                try:
                    number = int(count)
                except (TypeError, ValueError):
                    continue
                per_name[str(status)] = number
                status_counts[str(status)] = status_counts.get(str(status), 0) + number
            if per_name:
                clean_name = str(name)
                counts[clean_name] = sum(per_name.values())
                status_by_name[clean_name] = per_name
        return {
            "total": sum(counts.values()),
            "counts": dict(sorted(counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "status_by_name": {
                name: status_by_name[name] for name in sorted(status_by_name)
            },
        }

    def _research_summary(self, counters: dict[str, dict[str, float]]) -> dict[str, Any]:
        state = getattr(self, "_research_cache", None)
        if state is None:
            try:
                state = self.instance.first_namespace._save_research_state(compact=True)
                self._research_cache = state
            except Exception:
                state = None
        identity = research_state_identity(state)
        researched = {
            str(name): value
            for name, value in (identity.get("researched") or {}).items()
        }
        unlocked = set(getattr(self, "_observed_unlocked", set()))
        # Newer research-state producers may provide the enabled recipe set
        # directly.  Keep this optional so compact legacy saves remain valid;
        # the live namespace still contributes production-backed evidence below.
        if isinstance(state, dict):
            for field in ("unlocked_recipe_ids", "unlocked_recipes"):
                values = state.get(field, ())
                if isinstance(values, dict):
                    values = values.keys()
                if isinstance(values, (list, tuple, set)):
                    unlocked.update(str(item).strip('"') for item in values if item)
        # Non-zero output is direct evidence that its recipe was available.
        unlocked.update(str(item) for item in counters.get("output", {}))
        self._observed_unlocked = set(unlocked)
        return {
            "researched": dict(sorted(researched.items())),
            "disabled": list(identity.get("disabled", [])),
            "current_research": identity.get("current_research"),
            "research_progress": identity.get("research_progress", 0),
            "research_queue": list(identity.get("research_queue", [])),
            "unlocked_recipe_ids": sorted(unlocked),
            # Private comparison sets stay in the worker record and are never
            # serialized into the model-facing response.
            "_researched_set": set(researched),
            "_unlocked_set": unlocked,
        }

    @staticmethod
    def _contract_map(contracts: list[Any]) -> dict[str, dict[str, Any]]:
        values: dict[str, dict[str, Any]] = {}
        for contract in contracts:
            raw = _jsonable(contract)
            if isinstance(raw, dict):
                values[str(raw.get("order_id", len(values)))] = raw
        return values

    def _error_summary(self) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        for event in getattr(self, "_action_events", []):
            raw = _jsonable(event)
            if not isinstance(raw, dict) or not raw.get("error"):
                continue
            errors.append(
                {
                    "sequence": raw.get("sequence"),
                    "ticks": raw.get("ticks"),
                    "result": str(raw.get("result", ""))[:2000],
                    "policy_violations": list(raw.get("policy_violations", [])),
                }
            )
        distinct: list[dict[str, Any]] = []
        seen: set[str] = set()
        for error in reversed(errors):
            fingerprint = json.dumps(error.get("result", ""), sort_keys=True)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            distinct.append(error)
            if len(distinct) >= 8:
                break
        latest = errors[-1] if errors else None
        # A successful intervention clears the unresolved public error; the
        # full action ledger remains queryable for diagnosis.
        last_event = getattr(self, "_action_events", [])[-1:]
        unresolved = latest if last_event and bool(getattr(last_event[0], "error", False)) else None
        return {
            "latest": latest,
            "unresolved": [unresolved] if unresolved is not None else [],
            "distinct": list(reversed(distinct)),
            "error_count": len(errors),
            "_keys": {
                f"{item.get('sequence')}:{item.get('result', '')}" for item in errors
            },
        }

    def _model_state_snapshot(self, lease_id: str) -> dict[str, Any]:
        namespace = self.instance.first_namespace
        try:
            tick = int(self.instance.get_elapsed_ticks())
        except Exception:
            tick = int(self._read_game_tick())
        try:
            inventory = _normalise_counter_mapping(namespace.inspect_inventory())
        except Exception:
            inventory = {}
        try:
            stats = _jsonable(namespace._get_production_stats() or {})
        except Exception:
            stats = {}
        production, counters = self._compact_production_snapshot(stats, tick)
        entities = self._entity_summary()
        research = self._research_summary(counters)
        contracts = _jsonable(self._contracts_view())
        delivery = self._delivery_telemetry_snapshot(recent_limit=16).model_dump(
            mode="json"
        )
        return {
            "lease_id": lease_id,
            "task_id": self.task_spec.task_id if self.task_spec else "unknown",
            "ticks": tick,
            "inventory": inventory,
            "production": production,
            "production_counters": counters,
            "production_score": self._scores()[0],
            "automated_production_score": self._scores()[1],
            "state_hash": self._current_state_hash(),
            "entities": entities,
            "research": research,
            "contracts": contracts if isinstance(contracts, list) else [],
            "contract_map": self._contract_map(contracts if isinstance(contracts, list) else []),
            "customer_depots": _jsonable(list(self._customer_depots_cache)),
            "customer_delivery": delivery,
            "delivery_totals": _numeric_mapping(delivery.get("raw_totals", {})),
            "manual_delivery_totals": _numeric_mapping(delivery.get("manual_totals", {})),
            "blueprints": _jsonable(self._blueprint_summaries()),
            "errors": self._error_summary(),
        }

    @staticmethod
    def _observation_comparison_state(state: dict[str, Any]) -> dict[str, Any]:
        """Keep only fields needed to compare adjacent model observations.

        The latest full state is retained separately for current retrieval. A
        cursor ring entry must not duplicate delivery windows, blueprints, or
        other payloads that are already available from the current keyframe or
        the append-only public transition ledger.
        """

        research = state.get("research") or {}
        errors = state.get("errors") or {}
        return {
            "revision": state.get("revision"),
            "ticks": state.get("ticks"),
            "inventory": dict(state.get("inventory") or {}),
            "production_counters": {
                "input": dict(
                    (state.get("production_counters") or {}).get("input", {})
                ),
                "output": dict(
                    (state.get("production_counters") or {}).get("output", {})
                ),
            },
            "delivery_totals": dict(state.get("delivery_totals") or {}),
            "manual_delivery_totals": dict(
                state.get("manual_delivery_totals") or {}
            ),
            "entities": {
                "counts": dict((state.get("entities") or {}).get("counts", {}))
            },
            "research": {
                "_researched_set": set(research.get("_researched_set", set())),
                "_unlocked_set": set(research.get("_unlocked_set", set())),
            },
            "contract_map": _jsonable(state.get("contract_map") or {}),
            "errors": {
                "_keys": set(errors.get("_keys", set())),
                "distinct": _jsonable(errors.get("distinct", [])),
            },
        }

    @staticmethod
    def _state_delta(
        before: dict[str, Any] | None,
        after: dict[str, Any],
        revision: int,
    ) -> dict[str, Any]:
        if before is None:
            return {
                "from_revision": None,
                "to_revision": revision,
                "inventory": {},
                "production": {"input": {}, "output": {}},
                "delivery": {"automated": {}, "manual": {}},
                "entities": {"added": {}, "removed": {}, "changed": {}},
                "research": {"newly_researched": [], "newly_unlocked": []},
                "contracts": {"changed": list(after.get("contracts", []))},
                "errors": {"new": []},
            }
        before_counters = before.get("production_counters", {})
        after_counters = after.get("production_counters", {})
        before_entities = (before.get("entities") or {}).get("counts", {})
        after_entities = (after.get("entities") or {}).get("counts", {})
        added: dict[str, int] = {}
        removed: dict[str, int] = {}
        changed: dict[str, dict[str, int]] = {}
        for name in sorted(set(before_entities) | set(after_entities)):
            old = int(before_entities.get(name, 0))
            new = int(after_entities.get(name, 0))
            if new > old:
                added[name] = new - old
            elif old > new:
                removed[name] = old - new
            if old != new:
                changed[name] = {"before": old, "after": new}
        before_research = (before.get("research") or {}).get("_researched_set", set())
        after_research = (after.get("research") or {}).get("_researched_set", set())
        before_unlocked = (before.get("research") or {}).get("_unlocked_set", set())
        after_unlocked = (after.get("research") or {}).get("_unlocked_set", set())
        before_contracts = before.get("contract_map", {})
        after_contracts = after.get("contract_map", {})
        changed_contracts = [
            after_contracts[name]
            for name in sorted(set(before_contracts) | set(after_contracts))
            if before_contracts.get(name) != after_contracts.get(name)
            and name in after_contracts
        ]
        before_errors = (before.get("errors") or {}).get("_keys", set())
        after_errors = (after.get("errors") or {}).get("_keys", set())
        new_errors = [
            item
            for item in (after.get("errors") or {}).get("distinct", [])
            if f"{item.get('sequence')}:{item.get('result', '')}" in after_errors - before_errors
        ]
        return {
            "from_revision": before.get("revision"),
            "to_revision": revision,
            "from_tick": before.get("ticks"),
            "to_tick": after.get("ticks"),
            "inventory": _counter_delta(before.get("inventory", {}), after.get("inventory", {})),
            "production": {
                "input": _counter_delta(
                    before_counters.get("input", {}), after_counters.get("input", {})
                ),
                "output": _counter_delta(
                    before_counters.get("output", {}), after_counters.get("output", {})
                ),
            },
            "delivery": {
                "automated": _counter_delta(
                    before.get("delivery_totals", {}), after.get("delivery_totals", {})
                ),
                "manual": _counter_delta(
                    before.get("manual_delivery_totals", {}),
                    after.get("manual_delivery_totals", {}),
                ),
            },
            "entities": {"added": added, "removed": removed, "changed": changed},
            "research": {
                "newly_researched": sorted(set(after_research) - set(before_research)),
                "newly_unlocked": sorted(set(after_unlocked) - set(before_unlocked)),
            },
            "contracts": {"changed": changed_contracts},
            "errors": {"new": new_errors},
        }

    def _observation_cursor(self, revision: int) -> str:
        return f"{getattr(self, '_observation_nonce', '')}.{revision}"

    def _cursor_revision(self, cursor: str | None) -> int | None:
        if not cursor or not isinstance(cursor, str):
            return None
        nonce, separator, raw_revision = cursor.rpartition(".")
        if not separator or nonce != getattr(self, "_observation_nonce", ""):
            return None
        try:
            return int(raw_revision)
        except (TypeError, ValueError):
            return None

    def observe(
        self,
        lease_id: str,
        *,
        cursor: str | None = None,
        force_keyframe: bool = False,
    ) -> Observation:
        self._sync_customer()
        self._sync_active_order()
        history = getattr(self, "_observation_history", None)
        if history is None:
            history = self._observation_history = []
        previous = history[-1] if history else None
        revision = int(getattr(self, "_observation_revision", 0)) + 1
        state = self._model_state_snapshot(lease_id)
        state["revision"] = revision
        self._record_production_sample(
            int(state["ticks"]), state["production_counters"], revision=revision
        )
        transition = self._state_delta(previous, state, revision)
        requested_revision = self._cursor_revision(cursor)
        cursor_expired = bool(
            cursor is not None
            and (
                requested_revision is None
                or previous is None
                or requested_revision != previous.get("revision")
            )
        )
        base_revision = int(getattr(self, "_observation_keyframe_revision", 0))
        keyframe_id = str(getattr(self, "_observation_keyframe_id", ""))
        due_to_cadence = bool(
            previous
            and (
                revision - base_revision >= MODEL_OBSERVATION_KEYFRAME_INTERVAL
                or int(state["ticks"])
                - int(getattr(self, "_observation_keyframe_tick", state["ticks"]))
                >= MODEL_OBSERVATION_KEYFRAME_TICKS
            )
        )
        is_keyframe = bool(
            previous is None
            or force_keyframe
            or cursor_expired
            or getattr(self, "_observation_keyframe_pending", True)
            or due_to_cadence
        )
        if is_keyframe:
            base_revision = revision
            keyframe_id = f"kf:{getattr(self, '_observation_nonce', '')}:{revision}"
            self._observation_keyframe_revision = revision
            self._observation_keyframe_id = keyframe_id
            self._observation_keyframe_tick = int(state["ticks"])
            self._observation_keyframe_pending = False
        state["base_revision"] = base_revision
        state["keyframe_id"] = keyframe_id
        state["cursor"] = self._observation_cursor(revision)
        self._observation_revision = revision
        public_history = getattr(self, "_public_state_history", None)
        if public_history is None:
            public_history = self._public_state_history = []
        public_history.append(
            {
                "revision": revision,
                "ticks": state["ticks"],
                "base_revision": base_revision,
                "keyframe_id": keyframe_id,
                "inventory_delta": transition["inventory"],
                "production": transition["production"],
                "delivery": transition["delivery"],
                "entities": transition["entities"],
                "research": transition["research"],
                "contracts": transition["contracts"],
                "errors": transition["errors"],
            }
        )
        # Persist only compact state snapshots for model cursor validation.
        self._latest_model_state = state
        history.append(self._observation_comparison_state(state))
        if len(history) > MODEL_OBSERVATION_HISTORY_LIMIT:
            del history[: len(history) - MODEL_OBSERVATION_HISTORY_LIMIT]
            # Do not let the next delta depend on a comparison snapshot that
            # was just compacted away. The following observation establishes a
            # fresh base before more deltas are emitted.
            self._observation_keyframe_pending = True

        production, automated = (
            float(state["production_score"]),
            float(state["automated_production_score"]),
        )
        research = dict(state["research"])
        research.pop("_researched_set", None)
        research.pop("_unlocked_set", None)
        research["newly_researched_since_previous"] = transition["research"][
            "newly_researched"
        ]
        research["newly_unlocked_since_previous"] = transition["research"][
            "newly_unlocked"
        ]
        public_delta = {} if is_keyframe else transition
        return Observation(
            lease_id=lease_id,
            task_id=state["task_id"],
            ticks=state["ticks"],
            inventory=state["inventory"],
            production_score=production,
            automated_production_score=automated,
            production=state["production"],
            state_hash=state["state_hash"],
            revision=revision,
            cursor=state["cursor"],
            keyframe_id=keyframe_id,
            base_revision=base_revision,
            is_keyframe=is_keyframe,
            cursor_expired=cursor_expired,
            inventory_delta=transition["inventory"],
            delta=public_delta,
            entities=state["entities"],
            research=research,
            errors={
                key: value
                for key, value in state["errors"].items()
                if not key.startswith("_")
            },
            contracts=[OpenContractView.model_validate(item) for item in state["contracts"]],
            customer_depots=[
                CustomerDepotView.model_validate(item)
                for item in state["customer_depots"]
            ],
            customer_delivery=DepotDeliveryTelemetry.model_validate(
                state["customer_delivery"]
            ),
            blueprints=[
                BlueprintSummary.model_validate(item) for item in state["blueprints"]
            ],
        )

    def _public_epoch_outcome(self, outcome: ContractEpochOutcome) -> dict[str, Any]:
        """Strip rating/audit internals before historical contract retrieval."""

        return {
            "session_id": outcome.session_id,
            "epoch_index": outcome.epoch_index,
            "status": outcome.status,
            "delivered_quantity": outcome.delivered_quantity,
            "requested_quantity": outcome.requested_quantity,
            "delivered_by_product": dict(outcome.delivered_by_product),
            "requested_by_product": dict(outcome.requested_by_product),
            "completion_ratio": outcome.completion_ratio,
            "simulation_ticks_used": outcome.simulation_ticks_used,
            "interventions_used": outcome.interventions_used,
            "first_delivery_tick": outcome.first_delivery_tick,
            "completion_tick": outcome.completion_tick,
            "terminal_state_digest": outcome.terminal_state_digest,
        }

    def _query_entity_details(
        self,
        *,
        entity_type: str | None,
        area: dict[str, Any] | None,
        limit: int,
    ) -> dict[str, Any]:
        """Best-effort bounded detail lookup using the existing FLE API."""

        if not entity_type and not area:
            return {}
        try:
            from fle.env.entities import Position
            from fle.env.game_types import Prototype

            prototype = None
            if entity_type:
                wanted = str(entity_type).strip().lower().replace("_", "-")
                for candidate in Prototype:
                    value = candidate.value[0]
                    if str(value).lower() == wanted or candidate.name.lower().replace("_", "-") == wanted:
                        prototype = candidate
                        break
                if prototype is None:
                    return {"entities": [], "error": f"unknown entity type: {entity_type}"}
            kwargs: dict[str, Any] = {}
            if area:
                x = float(area.get("x", 0.0))
                y = float(area.get("y", 0.0))
                radius = max(0.0, min(float(area.get("radius", 1000.0)), 1000.0))
                kwargs.update(position=Position(x=x, y=y), radius=radius)
            if prototype is None:
                values = self.instance.first_namespace.get_entities(**kwargs)
            else:
                values = self.instance.first_namespace.get_entities(prototype, **kwargs)
            result: list[dict[str, Any]] = []
            for value in list(values or [])[:limit]:
                raw = _jsonable(value)
                if not isinstance(raw, dict):
                    continue
                # Entity inventories and nested prototype payloads can be very
                # large; queries return identity/status/location only.
                result.append(
                    {
                        key: raw[key]
                        for key in (
                            "name",
                            "prototype",
                            "type",
                            "status",
                            "position",
                            "direction",
                            "unit_number",
                            "recipe",
                        )
                        if key in raw
                    }
                )
            return {"entities": result, "returned": len(result)}
        except Exception as exc:  # noqa: BLE001 - query is best effort
            return {"entities": [], "error": f"entity query unavailable: {exc}"}

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
        """Read bounded public state history without exposing verifier internals."""

        allowed = {
            "inventory",
            "production",
            "delivery",
            "entities",
            "research",
            "contracts",
            "errors",
        }
        kind = str(kind).lower()
        if kind not in allowed:
            raise ValueError(f"kind must be one of {sorted(allowed)}")
        limit = max(1, min(int(limit), MODEL_HISTORY_QUERY_LIMIT))
        self._sync_customer()
        self._sync_active_order()
        current = getattr(self, "_latest_model_state", None)
        if current is None:
            current = self._model_state_snapshot(lease_id)
        revision = int(current.get("revision", getattr(self, "_observation_revision", 0)))
        if since_revision is not None:
            try:
                since_revision = int(since_revision)
            except (TypeError, ValueError) as exc:
                raise ValueError("since_revision must be an integer") from exc
        if changed_since is not None:
            try:
                changed_since = int(changed_since)
            except (TypeError, ValueError) as exc:
                raise ValueError("changed_since must be an integer") from exc
        result: dict[str, Any] = {
            "schema_version": "state-history-v1",
            "lease_id": lease_id,
            "kind": kind,
            "revision": revision,
            "cursor": current.get("cursor", ""),
            "keyframe_id": current.get("keyframe_id", ""),
            "history_truncated": False,
        }
        if kind == "inventory":
            public_history = list(getattr(self, "_public_state_history", []))
            samples = [
                {
                    "revision": transition.get("revision"),
                    "ticks": transition.get("ticks"),
                    "delta": transition.get("inventory_delta", {}),
                }
                for transition in public_history
                if since_revision is None
                or int(transition.get("revision", 0)) > since_revision
            ]
            result["current"] = current.get("inventory", {})
            result["samples"] = samples[-limit:]
            result["history_truncated"] = len(samples) > limit
        elif kind == "production":
            samples = list(getattr(self, "_production_history", []))
            cutoff_tick = None
            if window_seconds is not None:
                cutoff_tick = int(current.get("ticks", 0)) - max(0, int(window_seconds)) * 60
            selected = [
                sample
                for sample in samples
                if (since_revision is None or int(sample.get("revision", 0)) > since_revision)
                and (cutoff_tick is None or int(sample.get("tick", 0)) >= cutoff_tick)
                and (item is None or item in sample.get("output", {}) or item in sample.get("input", {}))
            ]
            if item:
                selected = [
                    {
                        **sample,
                        "input": {item: sample.get("input", {}).get(item, 0)} if item in sample.get("input", {}) else {},
                        "output": {item: sample.get("output", {}).get(item, 0)} if item in sample.get("output", {}) else {},
                    }
                    for sample in selected
                ]
            result["current"] = current.get("production", {})
            result["samples"] = selected[-limit:]
            result["history_truncated"] = len(selected) > limit
        elif kind == "delivery":
            telemetry = current.get("customer_delivery", {})
            full_buckets = [
                {
                    "tick": tick,
                    "items": dict(items),
                }
                for tick, items in getattr(self, "_delivery_history", [])
            ]
            cutoff_tick = None
            if window_seconds is not None:
                cutoff_tick = int(current.get("ticks", 0)) - max(0, int(window_seconds)) * 60
            if since_revision is not None:
                revision_ticks = [
                    int(state.get("ticks", 0))
                    for state in getattr(self, "_public_state_history", [])
                    if int(state.get("revision", 0)) <= since_revision
                ]
                if revision_ticks:
                    cutoff_tick = max(cutoff_tick or 0, revision_ticks[-1])
            selected = [
                bucket
                for bucket in full_buckets
                if (cutoff_tick is None or int(bucket["tick"]) > cutoff_tick)
                and (item is None or item in bucket.get("items", {}))
            ]
            if item:
                selected = [
                    {**bucket, "items": {item: bucket["items"].get(item, 0)}}
                    for bucket in selected
                ]
            result["current"] = telemetry
            result["samples"] = selected[-limit:]
            result["history_truncated"] = len(selected) > limit
        elif kind == "entities":
            mutations = []
            public_history = list(getattr(self, "_public_state_history", []))
            for transition in public_history:
                state_revision = int(transition.get("revision", 0))
                floor = changed_since if changed_since is not None else since_revision
                if floor is not None and state_revision <= floor:
                    continue
                delta = transition.get("entities", {})
                if any(delta.values()):
                    mutations.append(
                        {
                            "revision": state_revision,
                            "ticks": transition.get("ticks"),
                            **delta,
                        }
                    )
            result["current"] = current.get("entities", {})
            result["mutations"] = mutations[-limit:]
            result["history_truncated"] = len(mutations) > limit
            result.update(self._query_entity_details(entity_type=entity_type, area=area, limit=limit))
        elif kind == "research":
            changes = []
            public_history = list(getattr(self, "_public_state_history", []))
            for transition in public_history:
                state_revision = int(transition.get("revision", 0))
                if since_revision is not None and state_revision <= since_revision:
                    continue
                delta = transition.get("research", {})
                if delta.get("newly_researched") or delta.get("newly_unlocked"):
                    changes.append(
                        {
                            "revision": state_revision,
                            "ticks": transition.get("ticks"),
                            **delta,
                        }
                    )
            result["current"] = {
                key: value
                for key, value in (current.get("research") or {}).items()
                if not key.startswith("_")
            }
            result["changes"] = changes[-limit:]
            result["history_truncated"] = len(changes) > limit
        elif kind == "contracts":
            result["current"] = current.get("contracts", [])
            result["history"] = [
                self._public_epoch_outcome(outcome)
                for outcome in list(getattr(self, "_epoch_records", []))[-limit:]
            ]
            result["history_truncated"] = len(getattr(self, "_epoch_records", [])) > limit
        elif kind == "errors":
            errors = []
            for event in getattr(self, "_action_events", []):
                raw = _jsonable(event)
                if isinstance(raw, dict) and raw.get("error"):
                    errors.append(
                        {
                            "sequence": raw.get("sequence"),
                            "ticks": raw.get("ticks"),
                            "result": str(raw.get("result", ""))[:2000],
                            "policy_violations": list(raw.get("policy_violations", [])),
                        }
                    )
            result["current"] = {
                key: value
                for key, value in (current.get("errors") or {}).items()
                if not key.startswith("_")
            }
            result["history"] = errors[-limit:]
            result["history_truncated"] = len(errors) > limit
        return result

    def check_contract_throughput(
        self, lease_id: str, *, authoritative: bool = False
    ) -> ThroughputCheckResult:
        """Measure depot service while no agent program is running."""

        order = self._active_order
        epoch_index = self._active_epoch_index
        if order is None or epoch_index is None:
            raise NoActiveEpoch("No active contract epoch on this lease")
        if order.order_kind != "sustained":
            raise RuntimeError("Throughput checks require a sustained order")
        audit = getattr(self, "_throughput_audit_result", None)
        if authoritative and audit is not None and audit.passed:
            line_scores = {
                product: min(
                    audit.depot_rates_per_minute.get(product, 0.0)
                    / max(target, 1e-9),
                    1.0,
                )
                for product, target in audit.target_rates_per_minute.items()
            }
            result = ThroughputCheckResult(
                lease_id=lease_id,
                session_id=self.contract_session_id or "",
                epoch_index=epoch_index,
                authoritative=True,
                start_tick=audit.candidate_tick + audit.burn_in_seconds * 60,
                end_tick=(
                    audit.candidate_tick
                    + (audit.burn_in_seconds + audit.holdout_seconds) * 60
                ),
                window_ticks=audit.holdout_seconds * 60,
                delivered_by_product={
                    product: rate * audit.holdout_seconds / 60.0
                    for product, rate in audit.depot_rates_per_minute.items()
                },
                manual_delivered_by_product={
                    product: 0.0 for product in audit.target_rates_per_minute
                },
                observed_rate_per_minute=audit.depot_rates_per_minute,
                target_rate_per_minute=audit.target_rates_per_minute,
                line_scores=line_scores,
                performance_score=(
                    sum(line_scores.values()) / len(line_scores)
                    if line_scores
                    else 0.0
                ),
                interventions_during_window=0,
                contract_status="fulfilled",
            )
            self._authoritative_throughput_check = result
            return result
        if not authoritative and order.status != "open":
            raise RuntimeError("The sustained order is no longer open")

        if order.status == "open":
            self._sync_active_order()
        else:
            self._drain_delivery_buckets()
        if not authoritative and order.status != "open":
            raise RuntimeError("The sustained order expired before the check began")
        before_auto = dict(self._delivery_raw_totals)
        before_manual = dict(self._manual_delivery_totals)

        deadline_minutes = max(order.deadline_ticks / 3600.0, 1e-9)
        targets = {
            line.product: float(line.quantity) / deadline_minutes
            for line in order.products
        }
        desired_seconds = max(
            (120.0 / max(rate, 1e-9) for rate in targets.values()),
            default=60.0,
        )
        window_seconds = max(60, min(300, math.ceil(desired_seconds)))
        window_ticks = window_seconds * 60
        if not authoritative:
            window_ticks = min(window_ticks, order.remaining_ticks)
            if window_ticks <= 0:
                raise RuntimeError("No contract time remains for a throughput check")
            window_seconds = max(1, math.ceil(window_ticks / 60))

        start_tick = self._episode_tick()
        self._state_hash_dirty = True
        self._research_cache = None
        self.instance.set_speed_and_unpause(10)
        try:
            self.instance.first_namespace.sleep(window_seconds)
        finally:
            self.instance.pause()

        if order.status == "open":
            self._sync_active_order()
        else:
            self._drain_delivery_buckets()
        end_tick = self._episode_tick()
        actual_ticks = max(end_tick - start_tick, 1)
        actual_minutes = actual_ticks / 3600.0

        delivered = {
            product: round(
                max(
                    self._delivery_raw_totals.get(product, 0.0)
                    - before_auto.get(product, 0.0),
                    0.0,
                ),
                6,
            )
            for product in targets
        }
        manual = {
            product: round(
                max(
                    self._manual_delivery_totals.get(product, 0.0)
                    - before_manual.get(product, 0.0),
                    0.0,
                ),
                6,
            )
            for product in targets
        }
        rates = {
            product: round(amount / actual_minutes, 6)
            for product, amount in delivered.items()
        }
        line_scores = {
            product: round(
                min(rates.get(product, 0.0) / max(target, 1e-9), 1.0), 6
            )
            for product, target in targets.items()
        }
        result = ThroughputCheckResult(
            lease_id=lease_id,
            session_id=self.contract_session_id or "",
            epoch_index=epoch_index,
            authoritative=authoritative,
            start_tick=start_tick,
            end_tick=end_tick,
            window_ticks=actual_ticks,
            delivered_by_product=delivered,
            manual_delivered_by_product=manual,
            observed_rate_per_minute=rates,
            target_rate_per_minute={
                product: round(rate, 6) for product, rate in targets.items()
            },
            line_scores=line_scores,
            performance_score=(
                sum(line_scores.values()) / len(line_scores) if line_scores else 0.0
            ),
            interventions_during_window=0,
            contract_status=order.status,
        )
        if authoritative:
            self._authoritative_throughput_check = result
        return result

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
            precomputed_throughput = None
            if self._throughput_audit_result is not None:
                precomputed_throughput = {}
                for objective in task.objectives:
                    if objective.kind != "throughput" or objective.target is None:
                        continue
                    window_seconds = float(objective.window_seconds or 60)
                    rates = self._throughput_audit_result.production_subwindow_rates.get(
                        str(objective.target), []
                    )
                    precomputed_throughput[objective.objective_id] = [
                        rate * window_seconds / 60.0 for rate in rates
                    ]
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
                    precomputed_throughput_measurements=precomputed_throughput,
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
                            "throughput_audit": self._throughput_audit_result.model_dump(
                                mode="json"
                            )
                        }
                        if self._throughput_audit_result is not None
                        else {}
                    ),
                    **(
                        {
                            "customer_commitment": customer_result.commitment,
                            "customer_receipt_mac": customer_result.receipt_mac,
                            "customer_delivery_telemetry": (
                                self._delivery_telemetry_snapshot().model_dump(
                                    mode="json"
                                )
                            ),
                            "customer_order_delivery_telemetry": (
                                customer_result.delivery_telemetry
                            ),
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
                self._active_epoch_spec = None
                self._active_factory_band = None
                self._active_target_band = None
        self.instance.pause()
        self.customer_engine = None
        self._customer_events = []
        self._customer_depots_cache = []
        self._throughput_audit_result = None
        self._throughput_audit_attempts = []
        self._pending_throughput_candidate = None
        self._throughput_audit_retry_after_tick = 0
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
        self._active_factory_band = None
        self._active_target_band = None
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
