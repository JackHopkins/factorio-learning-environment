from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

PROTOCOL_VERSION = "0.3.0"
CUSTOMER_GENERATOR_VERSION = "customer-schedule-v1"
DISRUPTION_GENERATOR_VERSION = "disruption-schedule-v1"
# Adaptive contract benchmark identity.  Any change to generation, selection,
# rating, or calibration policy requires bumping the benchmark version; the
# calibration manifest version changes independently when only fitted
# parameters are re-published.
ADAPTIVE_BENCHMARK_SCHEMA_VERSION = "adaptive-contract-1"
ADAPTIVE_BENCHMARK_VERSION = "adaptive-contract-benchmark-0.5.0-dev"
CONTRACT_FEATURES_VERSION = "contract-features-v2"
CONTRACT_GENERATOR_VERSION = "contract-generator-v3"
CONTRACT_SELECTOR_VERSION = "contract-selector-v3"
CONTRACT_CALIBRATION_VERSION = "uncalibrated"  # replaced by manifests
CONTRACT_RATER_MODEL_VERSION = "trueskill-continuous-contract-v2"
PARTICIPANT_IDENTITY_VERSION = "participant-identity-v1"
TRAINING_BANK_VERSION = "training-bank-v1"
MEMORY_IMPLEMENTATION_VERSION = "session-memory-v1"
API_REFERENCE_VERSION = "fle-api-reference-v1"
GAME_DATA_REFERENCE_VERSION = "factorio-game-data-reference-v1"
CAPABILITY_GRAPH_VERSION = "capability-graph-v2"
CAPABILITY_CERTIFICATE_VERSION = "capability-certificates-v1"
FOLLOW_UP_POLICY_VERSION = "evidence-driven-customer-v2"
DELIVERY_TELEMETRY_VERSION = "depot-delivery-telemetry-v2"
STATE_OBSERVATION_VERSION = "state-observation-v1"

ContractMixtureClass = Literal["consolidation", "frontier", "stress"]
EpochOutcomeStatus = Literal[
    "fulfilled",
    "partial",
    "expired",
    "abandoned",
    "infrastructure_error",
    "invalid",
]
RatingResult = Literal["win", "draw", "loss"]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


TaskFamily = Literal[
    "throughput",
    "construction",
    "milestone",
    "repair",
    "progression",
    "robustness",
    "open_play",
]
ObjectiveKind = Literal[
    "throughput",
    "production",
    "research",
    "inventory",
    "entity_exists",
    "entity_status",
    "entity_recipe",
    "entity_inventory",
    "entity_position",
    "rocket_launch",
    "survival",
    "contract_fulfillment",
    "custom",
]
OrderKind = Literal["one_shot", "sustained"]
ContractStatus = Literal["pending", "open", "fulfilled", "expired"]
PerturbationKind = Literal[
    "resource_depletion",
    "entity_destruction",
    "enemy_wave",
]
PerturbationStatus = Literal["pending", "applied", "failed"]
RolloutSource = Literal["fresh", "inherited", "pathological"]
LineageOutcome = Literal[
    "healthy",
    "degraded_recoverable",
    "dominated",
    "horizon_reached",
]
Comparator = Literal["gte", "lte", "eq", "increases", "decreases", "maximize"]
LearningStrategy = Literal[
    "sft",
    "opd",
    "opsd",
    "grpo",
    "process_grpo",
    "actor_critic",
    "offline_replay",
    "evaluation",
]


class ObjectiveSpec(WireModel):
    """One independently verifiable desired state or state transition."""

    objective_id: str
    kind: ObjectiveKind
    description: str
    target: str | None = None
    comparator: Comparator = "gte"
    threshold: float | None = None
    window_seconds: int | None = Field(default=None, ge=0)
    required: bool = True
    weight: float = 1.0
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_threshold(self) -> "ObjectiveSpec":
        if self.comparator != "maximize" and self.threshold is None:
            raise ValueError(
                f"Objective {self.objective_id!r} requires a threshold for "
                f"comparator {self.comparator!r}"
            )
        if self.kind == "throughput" and self.window_seconds is None:
            raise ValueError("Throughput objectives require window_seconds")
        return self


class ConstraintSpec(WireModel):
    """A verifiable limit that applies throughout or at the end of a task."""

    constraint_id: str
    kind: Literal[
        "max_ticks",
        "max_interventions",
        "max_manual_crafts",
        "max_resource_cost",
        "max_pollution",
        "forbidden_action",
        "required_action",
        "required_action_profile",
        "custom",
    ]
    description: str
    limit: float | str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_limit(self) -> "ConstraintSpec":
        if self.kind != "custom" and self.limit is None:
            raise ValueError(
                f"Constraint {self.constraint_id!r} requires a limit for "
                f"kind {self.kind!r}"
            )
        return self


class VerifierSpec(WireModel):
    """How objective results become task success and an optimization signal."""

    implementation: Literal["legacy_fle_task", "objective_engine_v1"] = (
        "legacy_fle_task"
    )
    mode: Literal["all_required", "any_required", "weighted_threshold"] = "all_required"
    scalarization: Literal[
        "backend_override", "binary", "weighted_sum", "lexicographic"
    ] = "backend_override"
    success_threshold: float | None = None
    holdout_windows: int = Field(default=1, ge=1)
    emit_transition_comparisons: bool = True
    transition_holdout_seconds: int = Field(default=0, ge=0)


class ThroughputAuditSpec(WireModel):
    """Hidden two-stage autonomous qualification policy for throughput."""

    detector_window_seconds: int = Field(default=5, ge=1, le=3600)
    detector_trigger_ratio: float = Field(default=1.05, gt=0.0)
    burn_in_seconds: int = Field(default=20, ge=0, le=3600)
    holdout_seconds_min: int = Field(default=30, ge=1, le=3600)
    holdout_seconds_max: int = Field(default=60, ge=1, le=3600)
    subwindow_seconds: int = Field(default=10, ge=1, le=600)
    subwindow_floor_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    audit_game_speed: float = Field(default=50.0, gt=0.0, le=1000.0)
    require_depot_service: bool = True

    @model_validator(mode="after")
    def validate_windows(self) -> "ThroughputAuditSpec":
        if self.holdout_seconds_max < self.holdout_seconds_min:
            raise ValueError("holdout_seconds_max must be >= holdout_seconds_min")
        if self.subwindow_seconds > self.holdout_seconds_max:
            raise ValueError("subwindow_seconds cannot exceed the maximum holdout")
        if (
            self.holdout_seconds_min % self.subwindow_seconds
            or self.holdout_seconds_max % self.subwindow_seconds
        ):
            raise ValueError(
                "holdout bounds must be divisible by subwindow_seconds"
            )
        return self


class CurriculumSpec(WireModel):
    """Training metadata; it never changes the authoritative game verifier."""

    stage: str = "lab"
    suggested_strategies: list[LearningStrategy] = Field(
        default_factory=lambda: ["evaluation"]
    )
    prerequisite_task_ids: list[str] = Field(default_factory=list)
    episode_mode: Literal["independent", "checkpoint_chunk", "persistent"] = (
        "independent"
    )


class KnowledgeSourceSpec(WireModel):
    """Source metadata available to dataset builders or a privileged teacher."""

    source_id: str
    title: str
    url: str
    topics: list[str] = Field(default_factory=list)
    access: Literal["student", "privileged_teacher", "dataset_builder"] = (
        "privileged_teacher"
    )


class ProvisioningSpec(WireModel):
    """Optional overrides for a legacy FLE task's initial game state."""

    starting_inventory: dict[str, int] | None = None
    all_technologies_researched: bool | None = None
    researched_technologies: list[str] = Field(default_factory=list)
    character_inventory_slots_bonus: int = Field(default=0, ge=0, le=1000)


class ProductDemandSpec(WireModel):
    """Requested quantity of one product on a customer order."""

    product: str
    quantity: float = Field(gt=0)


class DemandOrderSpec(WireModel):
    """One hidden customer order in a pre-generated demand schedule.

    ``one_shot`` orders request total quantities delivered between
    ``issue_tick`` and ``due_tick``.  ``sustained`` orders request a steady
    rate over their window; the verifier slices the window and scores each
    slice against the requested slice quantity.
    """

    order_id: str
    kind: OrderKind = "one_shot"
    products: list[ProductDemandSpec]
    issue_tick: int = Field(ge=0)
    due_tick: int = Field(gt=0)
    grace_ticks: int = Field(default=0, ge=0)
    required: bool = True
    weight: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def validate_window(self) -> "DemandOrderSpec":
        if self.due_tick <= self.issue_tick:
            raise ValueError(
                f"Order {self.order_id!r} due_tick must be greater than issue_tick"
            )
        if len(self.products) != len({p.product for p in self.products}):
            raise ValueError(f"Order {self.order_id!r} has duplicate products")
        return self

    @property
    def close_tick(self) -> int:
        return self.due_tick + self.grace_ticks


class CustomerContractSpec(WireModel):
    """Immutable externally-owned demand schedule for one rollout.

    The full schedule ships inside the task spec (the benchmark equivalent of
    hidden unit tests) but the acting policy only ever observes orders whose
    ``issue_tick`` has already passed.  Fulfillment is measured exclusively by
    items physically crossing into customer-owned sink depots.
    """

    generator_version: str = CUSTOMER_GENERATOR_VERSION
    orders: list[DemandOrderSpec] = Field(min_length=1)
    depot_chests: int = Field(default=8, ge=1, le=64)
    lateness_penalty_weight: float = Field(default=0.0, ge=0.0)
    success_ratio: float = Field(default=1.0, gt=0.0, le=1.0)
    receipt_key_env: str = "FLE_CUSTOMER_RECEIPT_KEY"

    @model_validator(mode="after")
    def validate_order_ids(self) -> "CustomerContractSpec":
        order_ids = [order.order_id for order in self.orders]
        if len(order_ids) != len(set(order_ids)):
            raise ValueError("Customer order ids must be unique within a schedule")
        return self

    @computed_field
    @property
    def commitment(self) -> str:
        payload = json.dumps(
            [
                order.model_dump(mode="json")
                for order in sorted(
                    self.orders, key=lambda order: (order.issue_tick, order.order_id)
                )
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class PerturbationSpec(WireModel):
    """One hidden world disruption scheduled at a trigger tick.

    The schedule is immutable benchmark input; the blast radius is whatever
    exists in the live factory when it fires, and exactly what was hit is
    recorded in the emitted event payload for auditability.

    Parameter conventions by kind:

    - ``resource_depletion``: ``radius`` (tiles around target), optional
      ``resources`` filter list, optional ``position`` override.
    - ``entity_destruction``: ``count``, ``entity_types`` and/or
      ``entity_names`` filters, optional ``position`` override.
    - ``enemy_wave``: ``count``, optional ``tier`` (biter size), spawn at
      the factory perimeter.
    """

    perturbation_id: str
    kind: PerturbationKind
    trigger_tick: int = Field(ge=0)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_parameters(self) -> "PerturbationSpec":
        if self.kind == "entity_destruction":
            filters = (
                self.parameters.get("entity_types"),
                self.parameters.get("entity_names"),
            )
            if not any(filters):
                raise ValueError(
                    f"Perturbation {self.perturbation_id!r} entity_destruction "
                    "requires parameters.entity_types or parameters.entity_names"
                )
        return self


class DisruptionScheduleSpec(WireModel):
    """Immutable hidden disruption schedule for one rollout."""

    generator_version: str = DISRUPTION_GENERATOR_VERSION
    perturbations: list[PerturbationSpec] = Field(min_length=1)
    recovery_rate_threshold: float = Field(default=0.85, gt=0.0, le=1.0)
    recovery_min_ticks: int = Field(default=600, ge=0)

    @model_validator(mode="after")
    def validate_perturbation_ids(self) -> "DisruptionScheduleSpec":
        ids = [p.perturbation_id for p in self.perturbations]
        if len(ids) != len(set(ids)):
            raise ValueError("Perturbation ids must be unique within a schedule")
        return self

    @computed_field
    @property
    def commitment(self) -> str:
        payload = json.dumps(
            [
                p.model_dump(mode="json")
                for p in sorted(self.perturbations, key=lambda p: p.trigger_tick)
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class FactorioTaskSpec(WireModel):
    """Immutable inputs required to reproduce one rollout task."""

    task_id: str
    backend_task_id: str | None = None
    goal: str
    task_family: TaskFamily = "throughput"
    adaptive_contract_session: bool = Field(
        default=False,
        description=(
            "Enable the persistent customer depot used by the adaptive "
            "contract benchmark."
        ),
    )
    objectives: list[ObjectiveSpec] = Field(default_factory=list)
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    verifier: VerifierSpec = Field(default_factory=VerifierSpec)
    throughput_audit: ThroughputAuditSpec | None = None
    curriculum: CurriculumSpec = Field(default_factory=CurriculumSpec)
    knowledge_sources: list[KnowledgeSourceSpec] = Field(default_factory=list)
    provisioning: ProvisioningSpec = Field(default_factory=ProvisioningSpec)
    customer: CustomerContractSpec | None = None
    perturbations: DisruptionScheduleSpec | None = None
    blueprint_scope: str | None = Field(
        default=None,
        description=(
            "Blueprint store scope. None keeps blueprints ephemeral to the "
            "lease (benchmark default); a lineage id shares saved blueprints "
            "across a training generation."
        ),
    )
    lineage_id: str | None = Field(
        default=None,
        description="Map-lineage this episode continues, if any.",
    )
    generation_id: str | None = Field(
        default=None,
        description="Training generation this rollout belongs to.",
    )
    seed: int = 0
    scenario: str = "default_lab_scenario"
    factorio_version: str = "2.0.73"
    checkpoint_id: str = "scenario:default_lab_scenario"
    action_profile: str = "fle-program-v1"
    max_interventions: int | None = Field(
        default=8,
        ge=1,
        description=(
            "Hard intervention cap for bounded tasks. Customer contracts and "
            "adaptive sessions always normalize this to null and only track "
            "interventions as telemetry."
        ),
    )
    holdout_seconds: int = Field(default=60, ge=0)

    @model_validator(mode="after")
    def validate_objectives(self) -> "FactorioTaskSpec":
        objective_ids = [objective.objective_id for objective in self.objectives]
        if len(objective_ids) != len(set(objective_ids)):
            raise ValueError("Factorio objective ids must be unique within a task")
        constraint_ids = [constraint.constraint_id for constraint in self.constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("Factorio constraint ids must be unique within a task")
        if self.customer is not None or self.adaptive_contract_session:
            self.max_interventions = None
            self.constraints = [
                constraint
                for constraint in self.constraints
                if constraint.kind != "max_interventions"
            ]
        return self

    @computed_field
    @property
    def fingerprint(self) -> str:
        payload = self.model_dump_json(exclude={"fingerprint"})
        return hashlib.sha256(payload.encode()).hexdigest()


class LifecycleDecision(WireModel):
    """Recoverability verdict for one map lineage after an episode.

    Mirrors the ``V_continue(s) < V_restart - C_reset`` retirement rule.
    Counterfactual branch probes, when present, are the authoritative
    continuation estimate; otherwise a documented heuristic proxy is used.
    """

    lineage_id: str
    outcome: LineageOutcome
    continue_lineage: bool
    next_source: RolloutSource | None = None
    continuation_value: float = Field(ge=0.0, le=1.0)
    restart_value: float = Field(ge=0.0, le=1.0)
    reset_cost: float = Field(default=0.0, ge=0.0)
    reason: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class Lease(WireModel):
    lease_id: str
    worker_id: str
    task: FactorioTaskSpec
    initial_state_hash: str
    created_at: datetime
    expires_at: datetime
    tool_error_retry_budget: int = Field(default=0, ge=0)
    tool_error_retries_used: int = Field(default=0, ge=0)


class LeaseForkResult(WireModel):
    """Independent live branches created from one active lease."""

    source_lease_id: str
    branches: list[Lease] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class RuntimeCheckpoint(WireModel):
    """Durable runtime checkpoint metadata returned by the infrastructure layer."""

    lease_id: str
    checkpoint_id: str
    runtime_backend: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionEvent(WireModel):
    sequence: int
    code_sha256: str
    started_at: datetime
    duration_seconds: float
    reward_delta: float = 0.0
    error: bool = False
    evaluation_retry: bool = False
    result: str = ""
    ticks: int = 0
    executed_tools: list[str] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)


class CustomerDepotView(WireModel):
    """Authoritative student-visible identity for a customer delivery sink."""

    depot_id: str
    unit_number: int | None = None
    entity_name: str = "steel-chest"
    position: dict[str, float]
    surface: str | None = None
    customer_owned: bool = True
    consumes_deliveries: bool = True


class DepotDeliveryTelemetry(WireModel):
    """Auditable physical delivery measurements from customer-owned depots.

    ``raw_totals`` and the windowed rates contain only automated, simulation-
    sourced depot traffic. Direct agent insertion is retained separately as
    audit noise and never contributes to contract fulfillment.
    """

    schema_version: str = DELIVERY_TELEMETRY_VERSION
    observed_until_tick: int = Field(default=0, ge=0)
    bucket_ticks: int = Field(default=60, gt=0)
    sample_count: int = Field(default=0, ge=0)
    raw_totals: dict[str, float] = Field(default_factory=dict)
    manual_totals: dict[str, float] = Field(default_factory=dict)
    raw_rates_60s: dict[str, float] = Field(default_factory=dict)
    raw_rates_300s: dict[str, float] = Field(default_factory=dict)
    # Short-window service is useful for immediate control decisions while
    # the longer windows keep the signal stable.  The cumulative and bucket
    # histories remain authoritative inside the worker and are queryable via
    # the state-history endpoint.
    raw_rates_5s: dict[str, float] = Field(default_factory=dict)
    since_contract_totals: dict[str, float] = Field(default_factory=dict)
    recent_buckets: list[dict[str, Any]] = Field(default_factory=list)
    manual_sample_count: int = Field(default=0, ge=0)
    recent_manual_buckets: list[dict[str, Any]] = Field(default_factory=list)


class DeliveryReceipt(WireModel):
    """Objective-level feedback for an intervention that inserted items."""

    credited: dict[str, float] = Field(default_factory=dict)
    remaining: dict[str, float] = Field(default_factory=dict)
    contract_status: ContractStatus | None = None
    customer_depot_ids: list[str] = Field(default_factory=list)
    message: str


class MemoryEntry(WireModel):
    """One model-owned notebook entry; content is never interpreted by envd."""

    key: str
    content: str
    revision: int = Field(ge=1)
    content_sha256: str
    byte_size: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class MemoryMutation(WireModel):
    """Auditable write/delete event for the per-session notebook."""

    mutation_id: str
    operation: Literal["write", "delete"]
    key: str
    revision: int = Field(ge=1)
    content_sha256: str
    byte_size: int = Field(ge=0)
    expected_revision: int | None = Field(default=None, ge=0)
    occurred_at: datetime


class MemoryMutationResponse(WireModel):
    entry: MemoryEntry | None = None
    mutation: MemoryMutation


class MemoryListResponse(WireModel):
    entries: list[MemoryEntry] = Field(default_factory=list)
    next_cursor: str | None = None
    total: int = Field(ge=0)
    retained_bytes: int = Field(ge=0)


class MemorySearchHit(WireModel):
    key: str
    revision: int = Field(ge=1)
    content_sha256: str
    snippet: str


class MemorySearchResponse(WireModel):
    results: list[MemorySearchHit] = Field(default_factory=list)
    next_cursor: str | None = None
    total: int = Field(ge=0)


class MemoryTraceResponse(WireModel):
    events: list[MemoryMutation] = Field(default_factory=list)
    next_cursor: str | None = None
    total: int = Field(ge=0)


class ExecutionResult(WireModel):
    lease_id: str
    event: ActionEvent
    delivery_receipt: DeliveryReceipt | None = None
    production_score: float
    automated_production_score: float
    state_hash: str
    events: list["VerifierEvent"] = Field(default_factory=list)
    terminal_reason: str | None = None


class Observation(WireModel):
    lease_id: str
    task_id: str
    ticks: int
    inventory: dict[str, int | float] = Field(default_factory=dict)
    production_score: float = 0.0
    automated_production_score: float = 0.0
    production: dict[str, Any] = Field(default_factory=dict)
    state_hash: str
    # Revisioned model-facing state protocol.  ``cursor`` is opaque to the
    # caller; passing it back asks for the next delta.  A stale cursor causes
    # the worker to return a fresh keyframe instead of an incomplete delta.
    schema_version: str = STATE_OBSERVATION_VERSION
    revision: int = Field(default=0, ge=0)
    cursor: str = ""
    keyframe_id: str = ""
    base_revision: int = Field(default=0, ge=0)
    is_keyframe: bool = True
    cursor_expired: bool = False
    inventory_delta: dict[str, int | float] = Field(default_factory=dict)
    delta: dict[str, Any] = Field(default_factory=dict)
    entities: dict[str, Any] = Field(default_factory=dict)
    research: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, Any] = Field(default_factory=dict)
    contracts: list["OpenContractView"] = Field(default_factory=list)
    customer_depots: list[CustomerDepotView] = Field(default_factory=list)
    customer_delivery: DepotDeliveryTelemetry | None = None
    blueprints: list["BlueprintSummary"] = Field(default_factory=list)


class BlueprintSummary(WireModel):
    """Student-visible blueprint library entry (content stays server-side)."""

    name: str
    entity_count: int = 0
    times_placed: int = 0
    content_sha256: str = ""


class OpenContractView(WireModel):
    """Student-visible projection of a customer order.

    Only orders whose issue tick has passed are ever exposed.  Future demand,
    penalty weights, and verifier internals are deliberately absent.
    """

    order_id: str
    kind: OrderKind
    products: list[ProductDemandSpec]
    issued_at_tick: int
    due_tick: int
    grace_ticks: int = 0
    status: ContractStatus = "open"
    fulfilled: dict[str, float] = Field(default_factory=dict)
    remaining: dict[str, float] = Field(default_factory=dict)
    completion_ratio: float | None = Field(default=None, ge=0.0, le=1.0)


class RewardVector(WireModel):
    task: float = 0.0
    throughput: float = 0.0
    automation: float = 0.0
    progress: float = 0.0
    invalid_action: float = 0.0
    resource_cost: float = 0.0
    milestone: float = 0.0
    robustness: float = 0.0
    time_efficiency: float = 0.0
    manual_intervention: float = 0.0
    contracts: float = 0.0
    contract_penalty: float = 0.0


class ObjectiveEvaluation(WireModel):
    objective_id: str
    kind: ObjectiveKind
    supported: bool = True
    satisfied: bool
    value: float | bool | str | None = None
    baseline: float | bool | str | None = None
    threshold: float | None = None
    normalized_score: float = Field(default=0.0, ge=0.0)
    weight: float = 1.0
    evidence: dict[str, Any] = Field(default_factory=dict)


class ConstraintEvaluation(WireModel):
    constraint_id: str
    kind: str
    supported: bool = True
    satisfied: bool
    value: float | bool | str | None = None
    limit: float | str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class BottleneckSignal(WireModel):
    category: Literal[
        "input_starvation",
        "fuel_shortage",
        "power_shortage",
        "output_blocked",
        "missing_recipe",
        "research_blocked",
        "resource_depleted",
        "other",
    ]
    severity: float = Field(ge=0.0, le=1.0)
    affected_entities: int = Field(ge=0)
    statuses: dict[str, int] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class CharacterDeath(WireModel):
    tick: int = Field(ge=0)
    player_index: int = Field(ge=1)
    damage_type: str | None = None
    position: dict[str, float] = Field(default_factory=dict)
    surface: str | None = None
    cause: dict[str, Any] = Field(default_factory=dict)
    train: dict[str, Any] | None = None


class LifecycleStatus(WireModel):
    character_alive: bool = True
    character_health: float | None = None
    death_count: int = Field(default=0, ge=0)
    deaths: list[CharacterDeath] = Field(default_factory=list)
    respawn_count: int = Field(default=0, ge=0)
    last_respawn_tick: int | None = Field(default=None, ge=0)
    character_recreated_after_death: bool = False
    termination_reason: str | None = None


class FutureProbeResult(WireModel):
    """Counterfactual continuation result produced by an external branch runner."""

    probe_id: str
    description: str = ""
    normalized_score: float = Field(ge=0.0, le=1.0)
    success: bool = False
    interventions: int = Field(default=0, ge=0)
    elapsed_ticks: int = Field(default=0, ge=0)
    evidence: dict[str, Any] = Field(default_factory=dict)


class StateQualitySnapshot(WireModel):
    """Task-conditioned quality evidence for one persistent Factorio state.

    Dimension values are normalized to ``[0, 1]``. Optional dimensions are
    absent when the engine did not collect enough evidence to compare them.
    Raw evidence is retained so a teacher does not have to infer the meaning
    of an aggregate score.
    """

    schema_version: str = "0.1.0"
    task_id: str
    state_hash: str
    tick: int = Field(ge=0)
    horizon_ticks: int = Field(default=0, ge=0)
    objective_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    milestone_progress: float | None = Field(default=None, ge=0.0, le=1.0)
    sustained_capability: float | None = Field(default=None, ge=0.0, le=1.0)
    automation_quality: float | None = Field(default=None, ge=0.0, le=1.0)
    operational_health: float | None = Field(default=None, ge=0.0, le=1.0)
    future_option_value: float | None = Field(default=None, ge=0.0, le=1.0)
    safety: float = Field(default=1.0, ge=0.0, le=1.0)
    production_score: float = 0.0
    automated_production_score: float = 0.0
    objective_evaluations: list[ObjectiveEvaluation] = Field(default_factory=list)
    constraint_evaluations: list[ConstraintEvaluation] = Field(default_factory=list)
    automated_production: dict[str, float] = Field(default_factory=dict)
    manual_production: dict[str, float] = Field(default_factory=dict)
    bottlenecks: list[BottleneckSignal] = Field(default_factory=list)
    researched_technologies: list[str] = Field(default_factory=list)
    entity_counts: dict[str, int] = Field(default_factory=dict)
    lifecycle: LifecycleStatus = Field(default_factory=LifecycleStatus)
    resource_accounting: dict[str, Any] = Field(default_factory=dict)
    pollution: dict[str, float] = Field(default_factory=dict)
    future_probes: list[FutureProbeResult] = Field(default_factory=list)
    invariant_violations: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class StateDimensionDelta(WireModel):
    dimension: str
    previous: float
    current: float
    delta: float
    direction: Literal["maximize", "minimize"] = "maximize"
    classification: Literal["improved", "preserved", "regressed"]


class StateQualityComparison(WireModel):
    """Conservative partial-order comparison between two persistent states."""

    schema_version: str = "0.1.0"
    task_id: str
    previous_state_hash: str
    current_state_hash: str
    verdict: Literal["dominates", "incomparable", "regresses"]
    material_change: bool = False
    dimension_deltas: list[StateDimensionDelta] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    regressions: list[str] = Field(default_factory=list)
    preserved_invariants: list[str] = Field(default_factory=list)
    new_invariant_violations: list[str] = Field(default_factory=list)
    resolved_invariant_violations: list[str] = Field(default_factory=list)
    bottleneck_shift: dict[str, Any] | None = None
    explanation: str = ""


class PrivilegedTransitionPacket(WireModel):
    """Per-intervention state comparison retained outside student context."""

    schema_version: str = "0.1.0"
    task_id: str
    sequence: int = Field(ge=1)
    previous: StateQualitySnapshot
    current: StateQualitySnapshot
    comparison: StateQualityComparison


class PrivilegedDiagnosticPacket(WireModel):
    """Engine-derived context stored for teachers and offline analysis only."""

    schema_version: str = "0.1.0"
    task_id: str
    tick: int = Field(ge=0)
    elapsed_ticks: int = Field(ge=0)
    objective_evaluations: list[ObjectiveEvaluation] = Field(default_factory=list)
    constraint_evaluations: list[ConstraintEvaluation] = Field(default_factory=list)
    inventory: dict[str, float] = Field(default_factory=dict)
    inventory_delta: dict[str, float] = Field(default_factory=dict)
    production: dict[str, float] = Field(default_factory=dict)
    consumption: dict[str, float] = Field(default_factory=dict)
    automated_production: dict[str, float] = Field(default_factory=dict)
    manual_crafts: dict[str, float] = Field(default_factory=dict)
    research: dict[str, Any] = Field(default_factory=dict)
    entity_counts: dict[str, int] = Field(default_factory=dict)
    entity_status_counts: dict[str, int] = Field(default_factory=dict)
    bottlenecks: list[BottleneckSignal] = Field(default_factory=list)
    lifecycle: LifecycleStatus = Field(default_factory=LifecycleStatus)
    pollution: dict[str, float] = Field(default_factory=dict)
    resource_accounting: dict[str, Any] = Field(default_factory=dict)
    action_policy: dict[str, Any] = Field(default_factory=dict)
    resource_depletions: list[dict[str, Any]] = Field(default_factory=list)
    target_recipes: dict[str, Any] = Field(default_factory=dict)
    knowledge_sources: list[KnowledgeSourceSpec] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class VerifierEvent(WireModel):
    """Versioned, engine-grounded fact emitted during a rollout or verification."""

    event_id: str
    kind: Literal[
        "intervention_executed",
        "invalid_action",
        "objective_satisfied",
        "objective_failed",
        "constraint_satisfied",
        "constraint_failed",
        "milestone_reached",
        "technology_researched",
        "bottleneck_shift",
        "perturbation_applied",
        "recovery_completed",
        "contract_issued",
        "contract_progress",
        "contract_fulfilled",
        "contract_expired",
        "character_died",
        "character_respawned",
        "resource_depleted",
        "termination_classified",
        "verification_completed",
        "custom",
    ]
    tick: int = Field(ge=0)
    source: Literal["engine", "environment", "verifier"] = "environment"
    objective_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    reward_channels: dict[str, float] = Field(default_factory=dict)


class VerificationSnapshot(WireModel):
    protocol_version: str = PROTOCOL_VERSION
    lease_id: str
    task_id: str
    task_fingerprint: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool
    scalar_reward: float
    rewards: RewardVector
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    terminal_state_hash: str
    action_events: list[ActionEvent] = Field(default_factory=list)
    events: list[VerifierEvent] = Field(default_factory=list)
    termination_reason: str = "finalized"
    privileged_diagnostics: PrivilegedDiagnosticPacket | None = None
    privileged_transitions: list[PrivilegedTransitionPacket] = Field(
        default_factory=list
    )


class CapabilityManifest(WireModel):
    protocol_version: str = PROTOCOL_VERSION
    factorio_version: str = "2.0.73"
    action_profiles: list[str] = Field(default_factory=lambda: ["fle-program-v1"])
    api_reference_id: str = API_REFERENCE_VERSION
    game_data_reference_id: str = GAME_DATA_REFERENCE_VERSION
    memory_implementation_version: str = MEMORY_IMPLEMENTATION_VERSION
    features: dict[str, bool] = Field(
        default_factory=lambda: {
            "leases": True,
            "execute_program": True,
            "observations": True,
            "holdout_verification": True,
            "general_task_specs": True,
            "typed_verifier_events": True,
            "objective_engine_v1": True,
            "privileged_diagnostics": True,
            "state_quality_snapshots": True,
            "state_dominance_comparator": True,
            "privileged_transition_packets": True,
            "transition_holdouts": True,
            "future_probe_schema": True,
            "lifecycle_telemetry": True,
            "pollution_telemetry": True,
            "resource_accounting": True,
            "action_policy_audit": True,
            "program_policy_guard": True,
            # Harness-facing tool semantics.  These flags describe the
            # transport/service contract; they do not claim that a Factorio
            # worker can mutate the same world concurrently.
            "concurrent_request_safe": True,
            "per_lease_serial_execution": True,
            "parallel_world_mutations": False,
            "programmatic_action_composition": True,
            "provider_native_programmatic_tool_calling": False,
            "idempotent_execute_retries": True,
            "process_isolation": False,
            "terminal_reasons": True,
            "checkpoints": False,
            "clone": False,
            "pause_resume": False,
            "blueprint_store": True,
            "callable_api_reference": True,
            "exact_game_data_reference": True,
            "session_memory": True,
            "capability_graph_evidence": True,
            "adaptive_follow_up_policy": True,
            "autonomous_throughput_checks": True,
        }
    )


class HealthStatus(WireModel):
    status: Literal["ok", "degraded"]
    capacity: int
    available: int
    active_leases: int
    capabilities: CapabilityManifest


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Adaptive contract benchmark wire models
# ---------------------------------------------------------------------------


class ContractContextSnapshot(WireModel):
    """Passive factory measurements frozen immediately before an epoch.

    Capture may read authoritative game state but must never grant items,
    place entities, advance research, or run simulation.  The monotonic
    watermark is (session_id, epoch_index, captured_tick, state_digest);
    snapshots older than the prior finalized epoch are rejected.
    """

    schema_version: str = ADAPTIVE_BENCHMARK_SCHEMA_VERSION
    session_id: str
    epoch_index: int = Field(ge=0)
    captured_tick: int = Field(ge=0)
    technology_ids: tuple[str, ...]
    unlocked_recipe_ids: tuple[str, ...]
    inventory_counts: dict[str, int]
    placed_entity_counts: dict[str, int]
    production_rates_60s: dict[str, float]
    production_rates_300s: dict[str, float]
    # ``production_rates_*`` is retained for wire compatibility and is the
    # rate used by candidate generation.  New captures also retain the raw
    # flow-statistics projection and a provenance-safe projection whose manual
    # harvest/craft events have been removed by FLE's ``get_recent_rate``.
    raw_production_rates_60s: dict[str, float] = Field(default_factory=dict)
    raw_production_rates_300s: dict[str, float] = Field(default_factory=dict)
    automated_production_rates_60s: dict[str, float] = Field(default_factory=dict)
    automated_production_rates_300s: dict[str, float] = Field(default_factory=dict)
    power_capacity_kw: float
    power_utilization: float
    logistic_network_count: int
    train_stop_count: int
    pollution_total: float | None
    evolution_factor: float | None
    map_seed_hash: str
    state_digest: str
    # The factory band is measured from the frozen state.  ``target_band`` is
    # optional because a context is captured before candidate selection.
    factory_band: int = Field(default=0, ge=0, le=5)
    target_band: int | None = Field(default=None, ge=0, le=5)
    delivery_telemetry: DepotDeliveryTelemetry | None = None
    delivery_rates_60s: dict[str, float] = Field(default_factory=dict)
    delivery_rates_300s: dict[str, float] = Field(default_factory=dict)
    delivery_totals: dict[str, float] = Field(default_factory=dict)

    def watermark(self) -> tuple[str, int, int, str]:
        return (
            self.session_id,
            self.epoch_index,
            self.captured_tick,
            self.state_digest,
        )


class ContractDifficultyFeatures(WireModel):
    """Deterministic order features used by difficulty and selection.

    Feature definitions are frozen per calibration manifest; adding or
    redefining a feature requires a new features version.
    """

    schema_version: str = CONTRACT_FEATURES_VERSION
    product_id: str
    product_tier: int
    recipe_depth: int
    missing_technology_count: int
    missing_machine_type_count: int
    required_new_intermediate_count: int
    log_quantity: float
    deadline_ticks: int
    required_rate_per_minute: float
    existing_rate_per_minute: float
    inventory_coverage_ratio: float
    estimated_power_fraction: float
    transport_complexity: float
    stage_band: int = Field(ge=0, le=5)
    # ``stage_band`` remains the v1 wire name and is the target band for new
    # candidates. These explicit fields remove the old factory/target
    # ambiguity while keeping old consumers valid.
    factory_band: int | None = Field(default=None, ge=0, le=5)
    target_band: int | None = Field(default=None, ge=0, le=5)
    existing_delivery_rate_per_minute: float = 0.0


CapabilityNodeKind = Literal[
    "product",
    "recipe",
    "technology",
    "machine",
    "resource",
    "logistics",
    "power",
]
CapabilityNodeStatus = Literal[
    "locked",
    "reachable",
    "unlocked",
    "constructed",
    "producing",
    "delivered",
]


class CapabilityNodeEvidence(WireModel):
    """One advisory dependency-graph node and the live evidence for it."""

    node_id: str
    kind: CapabilityNodeKind
    status: CapabilityNodeStatus
    prerequisites: tuple[str, ...] = ()
    first_evidence_tick: int | None = Field(default=None, ge=0)
    latest_evidence_tick: int | None = Field(default=None, ge=0)
    production_rate_per_minute: float = 0.0
    evidence: dict[str, Any] = Field(default_factory=dict)


class CapabilityGraphSnapshot(WireModel):
    """Privileged, reproducible capability evidence for one factory snapshot."""

    schema_version: str = CAPABILITY_GRAPH_VERSION
    factorio_version: str = "unknown"
    state_digest: str
    captured_tick: int = Field(ge=0)
    nodes: list[CapabilityNodeEvidence] = Field(default_factory=list)
    advisory_frontier: tuple[str, ...] = ()
    target_path: tuple[str, ...] = ()


class CapabilityDelta(WireModel):
    """Evidence delta between the committed order's pre/post snapshots."""

    schema_version: str = CAPABILITY_GRAPH_VERSION
    before_state_digest: str
    after_state_digest: str
    target_id: str
    new_technologies: tuple[str, ...] = ()
    new_recipes: tuple[str, ...] = ()
    new_machines: tuple[str, ...] = ()
    newly_producing: tuple[str, ...] = ()
    production_rate_deltas: dict[str, float] = Field(default_factory=dict)
    path_nodes_before: tuple[str, ...] = ()
    path_nodes_after: tuple[str, ...] = ()
    path_progress: int = Field(default=0, ge=0)
    meaningful_progress: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Certified sustainable-capability evidence
# ---------------------------------------------------------------------------


CapabilityEvidenceStatus = Literal[
    "commissioned",
    "observed_sustained",
    # ``sustained`` is retained as a wire-compatible spelling for early
    # producers of this record. New records use ``observed_sustained``.
    "sustained",
    "autonomous",
    "robust",
]


class CapabilityCertificate(WireModel):
    """A bounded, auditable claim about what a factory can produce.

    A passive snapshot can establish commissioning, but it cannot establish
    autonomous operation. The latter requires an explicit qualification window
    with no agent interventions. Mixed demand vectors are represented by
    multiple entries in ``demand_vector`` and the observed/target rates use
    the same keys.
    """

    schema_version: str = CAPABILITY_CERTIFICATE_VERSION
    certificate_id: str
    capability_id: str | None = None
    session_id: str = ""
    source_state_digest: str = ""
    captured_tick: int = Field(default=0, ge=0)
    certified_at_tick: int | None = Field(default=None, ge=0)
    status: CapabilityEvidenceStatus = "commissioned"
    evidence_source: Literal["snapshot", "contract", "qualification", "stress"] = "snapshot"
    demand_vector: dict[str, float] = Field(default_factory=dict)
    target_rate_per_minute: dict[str, float] = Field(default_factory=dict)
    observed_rate_per_minute: dict[str, float] = Field(default_factory=dict)
    capability_band: int = Field(default=0, ge=0)
    prerequisite_capability_ids: tuple[str, ...] = ()
    sustained_window_ticks: int = Field(default=0, ge=0)
    qualification_window_ticks: int = Field(default=0, ge=0)
    interventions_during_window: int = Field(default=0, ge=0)
    autonomous_validation: bool = False
    robustness_checks: int = Field(default=0, ge=0)
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_claim(self) -> "CapabilityCertificate":
        if not self.demand_vector:
            raise ValueError("capability certificates require a non-empty demand_vector")
        if any(float(rate) < 0 for rate in self.demand_vector.values()):
            raise ValueError("demand_vector rates cannot be negative")
        if any(float(rate) < 0 for rate in self.target_rate_per_minute.values()):
            raise ValueError("target rates cannot be negative")
        if any(float(rate) < 0 for rate in self.observed_rate_per_minute.values()):
            raise ValueError("observed rates cannot be negative")
        if self.status in {"observed_sustained", "sustained", "autonomous", "robust"}:
            if self.sustained_window_ticks <= 0:
                raise ValueError("sustained evidence requires a positive sustained_window_ticks")
        if self.status in {"autonomous", "robust"}:
            if self.evidence_source not in {"qualification", "stress"}:
                raise ValueError("autonomous evidence must come from a qualification or stress window")
            if not self.autonomous_validation:
                raise ValueError("autonomous evidence requires autonomous_validation=True")
            if self.qualification_window_ticks <= 0:
                raise ValueError("autonomous evidence requires a positive qualification window")
            if self.interventions_during_window != 0:
                raise ValueError("autonomous evidence requires zero interventions during qualification")
        if self.status == "robust":
            if self.evidence_source != "stress" or self.robustness_checks <= 0:
                raise ValueError("robust evidence requires at least one stress/perturbation check")
        if self.capability_id is None:
            object.__setattr__(self, "capability_id", self.derived_capability_id())
        return self

    def derived_capability_id(self) -> str:
        """Return a stable key, including all lines for mixed demand vectors."""
        if len(self.demand_vector) == 1:
            return f"product:{next(iter(self.demand_vector))}"
        lines = "+".join(
            f"{product}={float(rate):g}"
            for product, rate in sorted(self.demand_vector.items())
        )
        return f"demand:{lines}"

    @property
    def products(self) -> tuple[str, ...]:
        return tuple(sorted(self.demand_vector))

    @property
    def is_sustainable(self) -> bool:
        return self.status in {"observed_sustained", "sustained", "autonomous", "robust"}

    @property
    def is_autonomous(self) -> bool:
        return self.status in {"autonomous", "robust"}


class FactoryProgressVector(WireModel):
    """Current factory capability, with dimensions kept separate.

    The vector is intentionally not collapsed into one score. Consumers may
    apply their own partial-order or lexicographic comparison while the
    ledger retains a conservative best watermark for longitudinal reporting.
    """

    schema_version: str = CAPABILITY_CERTIFICATE_VERSION
    session_id: str = ""
    captured_tick: int = Field(default=0, ge=0)
    highest_observed_band: int = Field(default=0, ge=0)
    highest_certified_band: int = Field(default=0, ge=0)
    closure_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    breadth: int = Field(default=0, ge=0)
    joint_sustained_throughput: float = Field(default=0.0, ge=0.0)
    observed_sustained_throughput: float = Field(default=0.0, ge=0.0)
    autonomy: float = Field(default=0.0, ge=0.0, le=1.0)
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    certified_capability_count: int = Field(default=0, ge=0)
    sustainable_capability_count: int = Field(default=0, ge=0)
    current_capability_ids: tuple[str, ...] = ()
    # This is a real previously observed vector, never a component-wise
    # synthetic maximum that could describe an impossible factory state.
    best_watermark: dict[str, Any] = Field(default_factory=dict)

    def order_key(self) -> tuple[float, ...]:
        return (
            float(self.highest_certified_band),
            float(self.highest_observed_band),
            float(self.closure_ratio),
            float(self.breadth),
            float(self.joint_sustained_throughput),
            float(self.autonomy),
            float(self.reliability),
        )


class CapabilityLedger(WireModel):
    """Serializable evidence ledger and current progress projection."""

    schema_version: str = CAPABILITY_CERTIFICATE_VERSION
    session_id: str = ""
    certificates: list[CapabilityCertificate] = Field(default_factory=list)
    progress_history: list[FactoryProgressVector] = Field(default_factory=list)
    best_progress: FactoryProgressVector | None = None

    def record(self, certificate: CapabilityCertificate) -> CapabilityCertificate:
        """Append evidence and refresh current/best progress projections."""
        if self.session_id and certificate.session_id and certificate.session_id != self.session_id:
            raise ValueError("certificate session_id does not match ledger session_id")
        if not self.session_id and certificate.session_id:
            self.session_id = certificate.session_id
        self.certificates.append(certificate)
        current = self.compute_progress(captured_tick=certificate.certified_at_tick or certificate.captured_tick)
        # Keep the stored watermark finite. ``current_progress`` adds the
        # serialized best vector when it is requested for reporting.
        current.best_watermark = {}
        self.progress_history.append(current)
        if self.best_progress is None or current.order_key() > self.best_progress.order_key():
            self.best_progress = current
        return certificate

    add = record

    def current_progress(self) -> FactoryProgressVector:
        """Return the projection without changing the ledger."""
        return self.compute_progress()

    def compute_progress(self, *, captured_tick: int | None = None) -> FactoryProgressVector:
        latest: dict[str, CapabilityCertificate] = {}
        for certificate in self.certificates:
            key = certificate.capability_id or certificate.derived_capability_id()
            prior = latest.get(key)
            if prior is None or (certificate.certified_at_tick or certificate.captured_tick) >= (prior.certified_at_tick or prior.captured_tick):
                latest[key] = certificate
        sustainable = [certificate for certificate in latest.values() if certificate.is_sustainable]
        sustainable_ids = {certificate.capability_id or certificate.derived_capability_id() for certificate in sustainable}
        closed = [
            certificate
            for certificate in sustainable
            if all(prerequisite in sustainable_ids for prerequisite in certificate.prerequisite_capability_ids)
        ]
        autonomous = [certificate for certificate in sustainable if certificate.is_autonomous]
        if sustainable:
            closure_ratio = len(closed) / len(sustainable)
            reliability = sum(c.reliability for c in sustainable) / len(sustainable)
        else:
            closure_ratio = 0.0
            reliability = 0.0
        if autonomous:
            autonomy = len(autonomous) / len(sustainable)
        else:
            autonomy = 0.0
        products = {product for certificate in sustainable for product in certificate.products}
        observed_joint = max(
            (
                sum(
                    certificate.observed_rate_per_minute.get(product, 0.0)
                    for product in certificate.products
                )
                for certificate in sustainable
                if len(certificate.products) > 1
            ),
            default=0.0,
        )
        if observed_joint == 0.0:
            observed_joint = sum(
                certificate.observed_rate_per_minute.get(product, 0.0)
                for certificate in sustainable
                for product in certificate.products
            )
        joint = 0.0
        for certificate in autonomous:
            if len(certificate.products) > 1:
                joint = max(joint, sum(certificate.observed_rate_per_minute.get(product, 0.0) for product in certificate.products))
        if joint == 0.0:
            joint = sum(
                certificate.observed_rate_per_minute.get(product, 0.0)
                for certificate in autonomous
                for product in certificate.products
            )
        vector = FactoryProgressVector(
            session_id=self.session_id,
            captured_tick=(captured_tick if captured_tick is not None else (self.progress_history[-1].captured_tick if self.progress_history else 0)),
            highest_observed_band=max(
                (certificate.capability_band for certificate in closed),
                default=0,
            ),
            highest_certified_band=max((certificate.capability_band for certificate in closed if certificate.is_autonomous), default=0),
            closure_ratio=closure_ratio,
            breadth=len(products),
            joint_sustained_throughput=joint,
            observed_sustained_throughput=observed_joint,
            autonomy=autonomy,
            reliability=reliability,
            certified_capability_count=len(autonomous),
            sustainable_capability_count=len(sustainable),
            current_capability_ids=tuple(sorted(sustainable_ids)),
        )
        best = self.best_progress
        if best is not None:
            vector.best_watermark = best.model_dump(mode="json")
        return vector


class CustomerFollowUp(WireModel):
    """Logged reason and target continuity decision for the next order."""

    schema_version: str = FOLLOW_UP_POLICY_VERSION
    policy: str = FOLLOW_UP_POLICY_VERSION
    reason: Literal[
        "initial",
        "fulfilled_pressure",
        "fulfilled_frontier",
        "partial_near_capacity",
        "frontier_progress_repeat",
        "frontier_progress_nearby",
        "zero_progress_backoff",
        "stretch",
    ]
    parent_epoch_index: int | None = Field(default=None, ge=0)
    parent_product_id: str | None = None
    selected_product_id: str | None = None
    selected_template_id: str | None = None
    target_path: tuple[str, ...] = ()
    stretch: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)


class ContractEpochSpec(WireModel):
    """The complete immutable definition of one benchmark epoch.

    ``commitment_hash`` covers every other field via canonical JSON; the
    outcome repeats it and finalization fails on mismatch.  Parsing a
    tampered specification fails validation because the hash is re-derived
    and compared on every load.
    """

    schema_version: str = ADAPTIVE_BENCHMARK_SCHEMA_VERSION
    benchmark_version: str = ADAPTIVE_BENCHMARK_VERSION
    calibration_version: str = CONTRACT_CALIBRATION_VERSION
    session_id: str
    epoch_index: int = Field(ge=0)
    template_id: str
    mixture_class: ContractMixtureClass = "frontier"
    generation_seed: int
    selection_seed: int
    item_name: str
    quantity: int = Field(gt=0)
    order_kind: OrderKind = "one_shot"
    products: tuple[ProductDemandSpec, ...] = ()
    deadline_ticks: int = Field(gt=0)
    intervention_budget: int | None = None
    context: ContractContextSnapshot
    features: ContractDifficultyFeatures
    raw_difficulty: float
    state_advantage: float
    effective_difficulty: float
    follow_up: CustomerFollowUp | None = None
    policy_evidence: dict[str, Any] = Field(default_factory=dict)
    factory_band: int | None = Field(default=None, ge=0, le=5)
    target_band: int | None = Field(default=None, ge=0, le=5)
    throughput_audit: ThroughputAuditSpec | None = None
    commitment_hash: str

    @model_validator(mode="after")
    def validate_products(self) -> "ContractEpochSpec":
        if not self.products:
            return self
        if self.products[0].product != self.item_name:
            raise ValueError("item_name must identify the first adaptive order line")
        if len(self.products) != len({line.product for line in self.products}):
            raise ValueError("adaptive order lines must have unique products")
        total = sum(int(round(line.quantity)) for line in self.products)
        if total != self.quantity:
            raise ValueError("quantity must equal the summed adaptive order lines")
        return self

    @model_validator(mode="after")
    def validate_commitment(self) -> "ContractEpochSpec":
        expected = compute_commitment_hash(self)
        if self.commitment_hash != expected:
            raise ValueError(
                "Epoch specification commitment mismatch: recorded "
                f"{self.commitment_hash[:12]!r} != derived {expected[:12]!r}"
            )
        return self

    @classmethod
    def create(cls, **fields: Any) -> "ContractEpochSpec":
        """Build a spec, deriving its commitment over the given fields."""
        fields.pop("commitment_hash", None)
        if not fields.get("products"):
            fields["products"] = (
                ProductDemandSpec(
                    product=str(fields["item_name"]),
                    quantity=float(fields["quantity"]),
                ),
            )
        if fields.get("order_kind") == "sustained" and "throughput_audit" not in fields:
            fields["throughput_audit"] = ThroughputAuditSpec()
        context = fields.get("context")
        features = fields.get("features")
        if fields.get("factory_band") is None and context is not None:
            fields["factory_band"] = getattr(context, "factory_band", None)
        if fields.get("target_band") is None and features is not None:
            fields["target_band"] = getattr(
                features, "target_band", None
            ) or getattr(features, "stage_band", None)
        provisional = cls.model_construct(**fields)
        return cls(
            **fields,
            commitment_hash=compute_commitment_hash(provisional),
        )


def compute_commitment_hash(spec_like: Any) -> str:
    data = getattr(spec_like, "model_dump")(exclude={"commitment_hash"}, mode="json")
    # Preserve validation of pre-v0.4 single-line commitments. New specs always
    # carry explicit products and therefore bind every new policy field.
    if not data.get("products"):
        data.pop("products", None)
        if data.get("order_kind") == "one_shot":
            data.pop("order_kind", None)
        if not data.get("policy_evidence"):
            data.pop("policy_evidence", None)
    # Parsed pre-v2 records did not contain the explicit band fields. Pydantic
    # fills them with None, so omit them only when they were not present on the
    # input model; new ``create`` calls bind them into the commitment.
    fields_set = getattr(spec_like, "model_fields_set", set())
    for field_name in ("factory_band", "target_band"):
        if data.get(field_name) is None and field_name not in fields_set:
            data.pop(field_name, None)
    # None preserves compatibility with pre-audit one-shot records even after
    # a JSON round-trip makes the field explicit. Sustained specs bind the
    # complete non-null audit policy into their commitment.
    if data.get("throughput_audit") is None:
        data.pop("throughput_audit", None)
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class ThroughputCheckResult(WireModel):
    """Depot throughput observed while the agent could not intervene."""

    schema_version: str = "autonomous-throughput-check-v1"
    lease_id: str
    session_id: str
    epoch_index: int = Field(ge=1)
    authoritative: bool = False
    start_tick: int = Field(ge=0)
    end_tick: int = Field(ge=0)
    window_ticks: int = Field(gt=0)
    delivered_by_product: dict[str, float] = Field(default_factory=dict)
    manual_delivered_by_product: dict[str, float] = Field(default_factory=dict)
    observed_rate_per_minute: dict[str, float] = Field(default_factory=dict)
    target_rate_per_minute: dict[str, float] = Field(default_factory=dict)
    line_scores: dict[str, float] = Field(default_factory=dict)
    performance_score: float = Field(ge=0.0, le=1.0)
    interventions_during_window: int = Field(default=0, ge=0)
    contract_status: ContractStatus


class ThroughputAuditResult(WireModel):
    """Privileged evidence from an intervention-free cloned simulation."""

    schema_version: str = "autonomous-throughput-audit-v1"
    lease_id: str
    session_id: str
    epoch_index: int = Field(ge=1)
    audit_worker_id: str
    candidate_tick: int = Field(ge=0)
    candidate_state_hash: str
    detector_window_seconds: int = Field(gt=0)
    detector_rates_per_minute: dict[str, float] = Field(default_factory=dict)
    target_rates_per_minute: dict[str, float] = Field(default_factory=dict)
    burn_in_seconds: int = Field(ge=0)
    holdout_seconds: int = Field(gt=0)
    holdout_ticks: int = Field(gt=0)
    subwindow_seconds: int = Field(gt=0)
    subwindow_ticks: list[int] = Field(default_factory=list)
    production_rates_per_minute: dict[str, float] = Field(default_factory=dict)
    depot_rates_per_minute: dict[str, float] = Field(default_factory=dict)
    production_subwindow_rates: dict[str, list[float]] = Field(default_factory=dict)
    depot_subwindow_rates: dict[str, list[float]] = Field(default_factory=dict)
    line_scores: dict[str, float] = Field(default_factory=dict)
    passed: bool = False
    failure_reasons: list[str] = Field(default_factory=list)


class ContractEpochOutcome(WireModel):
    """Authoritative result of one committed epoch."""

    schema_version: str = ADAPTIVE_BENCHMARK_SCHEMA_VERSION
    session_id: str
    epoch_index: int = Field(ge=0)
    commitment_hash: str
    status: EpochOutcomeStatus
    delivered_quantity: int = Field(ge=0)
    requested_quantity: int = Field(gt=0)
    delivered_by_product: dict[str, float] = Field(default_factory=dict)
    requested_by_product: dict[str, float] = Field(default_factory=dict)
    completion_ratio: float = Field(ge=0.0)
    performance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    simulation_ticks_used: int = Field(ge=0)
    interventions_used: int = Field(ge=0)
    model_seconds: float = Field(ge=0.0)
    tool_seconds: float = Field(ge=0.0)
    runner_wall_seconds: float = Field(ge=0.0)
    first_delivery_tick: int | None = None
    completion_tick: int | None = None
    terminal_state_digest: str
    capability_delta: CapabilityDelta | None = None
    factory_band: int | None = Field(default=None, ge=0, le=5)
    target_band: int | None = Field(default=None, ge=0, le=5)
    delivery_telemetry: dict[str, Any] = Field(default_factory=dict)
    autonomous_throughput: ThroughputCheckResult | None = None
    throughput_audit: ThroughputAuditResult | None = None
    throughput_audit_attempts: list[ThroughputAuditResult] = Field(
        default_factory=list
    )


class CapabilityRating(WireModel):
    """Online ability posterior for one participant series.

    Only plain floats cross the rating boundary so the underlying inference
    implementation remains replaceable and never leaks into saved records.
    """

    model_version: str = CONTRACT_RATER_MODEL_VERSION
    mu: float
    sigma: float = Field(ge=0.0)
    conservative_score: float
    rated_epoch_count: int = Field(ge=0)


class ParticipantIdentity(WireModel):
    """Rating-series identity derived from the actual model and harness.

    Changing any component starts a distinct series; ratings from different
    identities are never pooled.
    """

    schema_version: str = PARTICIPANT_IDENTITY_VERSION
    provider: str
    model_snapshot: str
    harness_version: str
    system_prompt_hash: str
    tool_manifest_hash: str
    inference_settings_hash: str
    api_reference_hash: str = ""
    game_data_reference_hash: str = ""
    memory_implementation_version: str = "disabled"
    memory_initial_state_hash: str = ""
    graph_visibility_policy: str = "privileged_only"

    @computed_field
    @property
    def participant_id(self) -> str:
        return canonical_hash(self.model_dump(exclude={"participant_id"}))


class ContractTemplateSpec(WireModel):
    """One parameterized order family in a bank.

    Product choice resolves against pinned game data at generation time;
    templates constrain the mixture class, progression bands, pressure, and
    window rather than hardcoding quantities.
    """

    template_version: str = CONTRACT_GENERATOR_VERSION
    template_id: str
    mixture_class: ContractMixtureClass
    families: tuple[str, ...] = ()
    products: tuple[str, ...] = ()  # empty = resolve from mixture rule
    stage_bands: tuple[int, ...] = Field(default=(0, 1, 2, 3, 4, 5))
    pressure_multiplier_range: tuple[float, float] = (1.2, 2.5)
    production_window_minutes_range: tuple[float, float] = (10.0, 45.0)


class SelectorWeights(WireModel):
    """Versioned candidate-scoring policy (section 13)."""

    selector_version: str = CONTRACT_SELECTOR_VERSION
    w_info: float = 1.0
    w_coverage: float = 0.6
    w_novelty: float = 0.3
    w_repeat: float = 0.4
    w_extrapolation: float = 0.8
    selection_temperature: float = Field(default=0.05, gt=0.0)


class SessionStoppingConfig(WireModel):
    """Optional evaluation stops plus contract-session safety failsafes."""

    target_sigma: float | None = Field(default=None, gt=0.0)
    max_rated_epochs: int | None = Field(default=None, ge=1)
    max_session_ticks: int | None = Field(default=None, ge=1)
    max_session_interventions: int | None = Field(default=None, ge=1)
    max_failed_deliveries: int | None = Field(default=5, ge=1)
    wall_clock_failsafe_seconds: float = Field(default=24 * 3600.0, gt=0.0)


class CalibrationManifest(WireModel):
    """Immutable published contextual-difficulty calibration (section 16).

    Out-of-envelope epochs are flagged and excluded from official rating
    unless the supported range explicitly covers them.
    """

    calibration_version: str
    benchmark_version: str
    training_data_sha256: str
    game_versions: tuple[str, ...]
    mod_versions: tuple[str, ...] = ()
    feature_schema_version: str = CONTRACT_FEATURES_VERSION
    template_bank_version: str
    partial_floor: float = Field(default=0.25, ge=0.0, le=1.0)
    partial_ceiling: float = Field(default=0.90, ge=0.0, le=1.0)
    template_intercepts: dict[str, float]
    beta_raw: dict[str, float]
    beta_state: dict[str, float]
    normalization: dict[str, tuple[float, float]]  # feature -> (mean, std)
    clipping: dict[str, tuple[float, float]]
    parameter_covariance_digest: str = ""
    supported_ranges: dict[str, tuple[float, float]]
    heldout_metrics: dict[str, float] = Field(default_factory=dict)
    implementation_commit: str = ""
    accepted: bool = False

    @model_validator(mode="after")
    def validate_thresholds(self) -> "CalibrationManifest":
        if self.partial_floor >= self.partial_ceiling:
            raise ValueError("partial_floor must be below partial_ceiling")
        return self


class ActiveContractState(WireModel):
    """Server-side projection returned when an epoch begins."""

    lease_id: str
    session_id: str
    epoch_index: int
    spec_commitment_hash: str
    open_order: OpenContractView
    epoch_start_tick: int


class ContractSessionState(WireModel):
    """Privileged lifecycle view of an adaptive contract session."""

    lease_id: str
    session_id: str
    session_simulation_ticks: int
    epoch_simulation_ticks: int
    completed_epoch_count: int
    active_epoch_index: int | None
    active_commitment_hash: str | None
    agent_interventions: int


class ContractSessionSummary(WireModel):
    """Aggregation retained through session end."""

    session_id: str
    session_simulation_ticks: int
    epochs: list[ContractEpochOutcome]
    fulfilled_epochs: int
    total_delivered: int
    total_requested: int
