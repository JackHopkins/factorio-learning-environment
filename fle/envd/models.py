from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

PROTOCOL_VERSION = "0.3.0"


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
    "custom",
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


class FactorioTaskSpec(WireModel):
    """Immutable inputs required to reproduce one rollout task."""

    task_id: str
    backend_task_id: str | None = None
    goal: str
    task_family: TaskFamily = "throughput"
    objectives: list[ObjectiveSpec] = Field(default_factory=list)
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    verifier: VerifierSpec = Field(default_factory=VerifierSpec)
    curriculum: CurriculumSpec = Field(default_factory=CurriculumSpec)
    knowledge_sources: list[KnowledgeSourceSpec] = Field(default_factory=list)
    provisioning: ProvisioningSpec = Field(default_factory=ProvisioningSpec)
    seed: int = 0
    scenario: str = "default_lab_scenario"
    factorio_version: str = "2.0.73"
    checkpoint_id: str = "scenario:default_lab_scenario"
    action_profile: str = "fle-program-v1"
    max_interventions: int = Field(default=8, ge=1)
    holdout_seconds: int = Field(default=60, ge=0)

    @model_validator(mode="after")
    def validate_objectives(self) -> "FactorioTaskSpec":
        objective_ids = [objective.objective_id for objective in self.objectives]
        if len(objective_ids) != len(set(objective_ids)):
            raise ValueError("Factorio objective ids must be unique within a task")
        constraint_ids = [constraint.constraint_id for constraint in self.constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("Factorio constraint ids must be unique within a task")
        return self

    @computed_field
    @property
    def fingerprint(self) -> str:
        payload = self.model_dump_json(exclude={"fingerprint"})
        return hashlib.sha256(payload.encode()).hexdigest()


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


class ExecutionResult(WireModel):
    lease_id: str
    event: ActionEvent
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
            "process_isolation": False,
            "terminal_reasons": True,
            "checkpoints": False,
            "clone": False,
            "pause_resume": False,
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
