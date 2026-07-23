"""Native multi-objective verification and privileged Factorio diagnostics."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Iterable

from fle.commons.models.achievements import ProductionFlows
from fle.env.utils.achievements import calculate_achievements
from fle.envd.models import (
    ActionEvent,
    BottleneckSignal,
    CharacterDeath,
    ConstraintEvaluation,
    FactorioTaskSpec,
    ObjectiveEvaluation,
    ObjectiveSpec,
    PrivilegedDiagnosticPacket,
    LifecycleStatus,
    RewardVector,
    VerifierEvent,
)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _numeric_dict(value: Any) -> dict[str, float]:
    raw = _jsonable(value)
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): float(item)
        for key, item in raw.items()
        if isinstance(item, (int, float))
    }


def _sequence(value: Any) -> list[Any]:
    raw = _jsonable(value)
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        try:
            return [
                item
                for _, item in sorted(
                    raw.items(), key=lambda pair: int(str(pair[0]))
                )
            ]
        except (TypeError, ValueError):
            return []
    return []


def _flow_delta(
    before: dict[str, float], after: dict[str, float]
) -> dict[str, float]:
    return {
        key: value - before.get(key, 0.0)
        for key, value in after.items()
        if value - before.get(key, 0.0) != 0
    }


def _manual_outputs(flows: ProductionFlows) -> dict[str, float]:
    outputs: dict[str, float] = {}
    for craft in flows.crafted:
        for item, amount in craft.get("outputs", {}).items():
            outputs[str(item)] = outputs.get(str(item), 0.0) + float(amount)
    return outputs


def _manual_craft_count(flows: ProductionFlows) -> float:
    return float(
        sum(float(craft.get("crafted_count", 0)) for craft in flows.crafted)
    )


_GROUP_MEMBERS = ("belts", "pipes", "poles", "walls", "entities")


def _leaf_entities(entities: Iterable[Any]) -> Iterable[Any]:
    for entity in entities:
        children = None
        for attribute in _GROUP_MEMBERS:
            candidate = getattr(entity, attribute, None)
            if isinstance(candidate, list):
                children = candidate
                break
        if children is None:
            yield entity
        else:
            yield from _leaf_entities(children)


@dataclass
class TelemetryFrame:
    tick: int
    inventory: dict[str, float]
    flows: ProductionFlows
    production_score: float
    automated_production_score: float
    researched: dict[str, bool]
    technologies: dict[str, dict[str, Any]]
    current_research: str | None
    research_progress: float
    entity_counts: dict[str, int]
    entity_status_counts: dict[str, int]
    entity_status_by_name: dict[str, dict[str, int]]
    rocket_launches: int
    target_recipes: dict[str, Any]
    character_alive: bool = True
    character_health: float | None = None
    deaths: list[dict[str, Any]] = field(default_factory=list)
    death_count: int = 0
    respawn_count: int = 0
    last_respawn_tick: int | None = None
    resource_depletions: list[dict[str, Any]] = field(default_factory=list)
    pollution_total: float = 0.0
    pollution_emitted: float = 0.0
    produced: dict[str, float] = field(default_factory=dict)
    consumed: dict[str, float] = field(default_factory=dict)


def _objective_telemetry(namespace: Any, reset: bool = False) -> dict[str, Any]:
    getter = getattr(namespace, "_objective_telemetry", None)
    if getter is None:
        return {}
    try:
        value = _jsonable(getter(reset))
        return value if isinstance(value, dict) else {}
    except Exception:
        # Old saves and unit fakes may not yet have the instrumentation script.
        return {}


def capture_telemetry(instance: Any, targets: Iterable[str] = ()) -> TelemetryFrame:
    namespace = instance.first_namespace
    engine = _objective_telemetry(namespace)
    flows = ProductionFlows.from_dict(namespace._get_production_stats())
    production_score, automated_score = namespace.score()
    research = namespace._save_research_state()
    entities = list(_leaf_entities(namespace.get_entities()))

    entity_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    status_by_name: dict[str, dict[str, int]] = {}
    for entity in entities:
        prototype = getattr(entity, "prototype", None)
        name = getattr(entity, "name", None)
        if not name and prototype is not None:
            value = getattr(prototype, "value", prototype)
            name = value[0] if isinstance(value, tuple) else str(value)
        name = str(name or type(entity).__name__)
        status = getattr(entity, "status", "unknown")
        status = getattr(status, "value", status)
        status = str(status)
        entity_counts[name] = entity_counts.get(name, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        per_name = status_by_name.setdefault(name, {})
        per_name[status] = per_name.get(status, 0) + 1

    technologies: dict[str, dict[str, Any]] = {}
    researched: dict[str, bool] = {}
    if research is not None:
        for name, technology in research.technologies.items():
            technologies[str(name)] = _jsonable(technology)
            researched[str(name)] = bool(technology.researched)

    target_recipes: dict[str, Any] = {}
    for target in sorted(set(targets)):
        try:
            target_recipes[target] = _jsonable(namespace.get_prototype_recipe(target))
        except Exception as exc:
            target_recipes[target] = {"available": False, "error": str(exc)}

    return TelemetryFrame(
        tick=int(instance.get_elapsed_ticks()),
        inventory=_numeric_dict(namespace.inspect_inventory()),
        flows=flows,
        production_score=float(production_score or 0),
        automated_production_score=float(automated_score or 0),
        researched=researched,
        technologies=technologies,
        current_research=(
            str(research.current_research) if research and research.current_research else None
        ),
        research_progress=float(research.research_progress if research else 0),
        entity_counts=entity_counts,
        entity_status_counts=status_counts,
        entity_status_by_name=status_by_name,
        rocket_launches=int(
            engine.get(
                "rockets_launched",
                getattr(instance, "_verified_rocket_launches", 0),
            )
            or 0
        ),
        target_recipes=target_recipes,
        character_alive=bool(engine.get("character_alive", True)),
        character_health=(
            float(engine["character_health"])
            if isinstance(engine.get("character_health"), (int, float))
            else None
        ),
        deaths=_sequence(engine.get("deaths", [])),
        death_count=int(engine.get("death_count", 0) or 0),
        respawn_count=int(engine.get("respawn_count", 0) or 0),
        last_respawn_tick=(
            int(engine["last_respawn_tick"])
            if isinstance(engine.get("last_respawn_tick"), (int, float))
            else None
        ),
        resource_depletions=_sequence(engine.get("resource_depletions", [])),
        pollution_total=float(engine.get("pollution_total", 0) or 0),
        pollution_emitted=float(engine.get("pollution_emitted", 0) or 0),
        produced=_numeric_dict(engine.get("produced", {})),
        consumed=_numeric_dict(engine.get("consumed", {})),
    )


def _compare(
    objective: ObjectiveSpec, value: float, baseline: float = 0.0
) -> tuple[bool, float]:
    threshold = float(objective.threshold or 0)
    if objective.comparator == "gte":
        return value >= threshold, min(max(value / threshold, 0.0), 1.0) if threshold else 1.0
    if objective.comparator == "lte":
        satisfied = value <= threshold
        score = 1.0 if satisfied else max(threshold / value, 0.0) if value else 1.0
        return satisfied, min(score, 1.0)
    if objective.comparator == "eq":
        return math.isclose(value, threshold), float(math.isclose(value, threshold))
    if objective.comparator == "increases":
        delta = value - baseline
        return delta > threshold, 1.0 if delta > threshold else 0.0
    if objective.comparator == "decreases":
        delta = baseline - value
        return delta > threshold, 1.0 if delta > threshold else 0.0
    if objective.comparator == "maximize":
        nonnegative = max(value, 0.0)
        return True, nonnegative / (1.0 + nonnegative)
    raise ValueError(f"Unsupported comparator: {objective.comparator}")


def _unsupported_objective(
    objective: ObjectiveSpec, reason: str
) -> ObjectiveEvaluation:
    return ObjectiveEvaluation(
        objective_id=objective.objective_id,
        kind=objective.kind,
        supported=False,
        satisfied=False,
        threshold=objective.threshold,
        normalized_score=0.0,
        weight=objective.weight,
        evidence={"reason": reason},
    )


def evaluate_objective(
    objective: ObjectiveSpec,
    initial: TelemetryFrame,
    final: TelemetryFrame,
    throughput_windows: list[float] | None = None,
) -> ObjectiveEvaluation:
    target = objective.target
    baseline = 0.0
    evidence: dict[str, Any] = {}

    if objective.kind == "throughput":
        if target is None or throughput_windows is None:
            return _unsupported_objective(
                objective, "throughput target or holdout measurements missing"
            )
        value = min(throughput_windows) if throughput_windows else 0.0
        evidence["windows"] = throughput_windows
        evidence["aggregation"] = "minimum"
    elif objective.kind == "production":
        if target is None:
            return _unsupported_objective(objective, "production target missing")
        achievements = calculate_achievements(initial.flows, final.flows)
        automatic = bool(objective.parameters.get("automatic", True))
        if automatic:
            value = float(achievements["dynamic"].get(target, 0))
            evidence["source"] = "dynamic_achievements"
        else:
            value = float(
                final.flows.output.get(target, 0)
                - initial.flows.output.get(target, 0)
            )
            evidence["source"] = "production_statistics"
    elif objective.kind == "research":
        if target is None:
            return _unsupported_objective(objective, "research target missing")
        baseline = float(initial.researched.get(target, False))
        value = float(final.researched.get(target, False))
        technology = final.technologies.get(target)
        evidence["technology"] = technology or {"known": False}
    elif objective.kind == "inventory":
        if target is None:
            return _unsupported_objective(objective, "inventory target missing")
        baseline = initial.inventory.get(target, 0.0)
        value = final.inventory.get(target, 0.0)
    elif objective.kind == "entity_exists":
        if target is None:
            return _unsupported_objective(objective, "entity target missing")
        baseline = float(initial.entity_counts.get(target, 0))
        value = float(final.entity_counts.get(target, 0))
        evidence["status_counts"] = final.entity_status_by_name.get(target, {})
    elif objective.kind == "rocket_launch":
        baseline = float(initial.rocket_launches)
        value = float(final.rocket_launches)
    elif objective.kind == "survival":
        baseline = 0.0
        value = float(final.tick - initial.tick)
        new_deaths = max(final.death_count - initial.death_count, 0)
        evidence["character_death_tracking"] = True
        evidence["death_count"] = new_deaths
        evidence["character_alive"] = final.character_alive
    else:
        return _unsupported_objective(
            objective, f"native verifier does not implement {objective.kind!r}"
        )

    satisfied, normalized = _compare(objective, value, baseline)
    if objective.kind == "survival" and not objective.parameters.get(
        "allow_death", False
    ):
        survived = final.death_count == initial.death_count
        satisfied = satisfied and survived
        if not survived:
            normalized = 0.0
    return ObjectiveEvaluation(
        objective_id=objective.objective_id,
        kind=objective.kind,
        supported=True,
        satisfied=satisfied,
        value=value,
        baseline=baseline,
        threshold=objective.threshold,
        normalized_score=normalized,
        weight=objective.weight,
        evidence=evidence,
    )


def evaluate_constraint(
    task: FactorioTaskSpec,
    constraint: Any,
    initial: TelemetryFrame,
    final: TelemetryFrame,
    events: list[ActionEvent],
) -> ConstraintEvaluation:
    value: float | str | None
    supported = True
    evidence: dict[str, Any] = {}
    if constraint.kind == "max_ticks":
        value = float(final.tick - initial.tick)
        satisfied = value <= float(constraint.limit)
    elif constraint.kind == "max_interventions":
        value = float(len(events))
        satisfied = value <= float(constraint.limit)
    elif constraint.kind == "max_manual_crafts":
        value = _manual_craft_count(final.flows) - _manual_craft_count(initial.flows)
        satisfied = value <= float(constraint.limit)
    elif constraint.kind == "required_action_profile":
        value = task.action_profile
        satisfied = value == str(constraint.limit)
    elif constraint.kind == "max_resource_cost":
        raw_resources = constraint.parameters.get(
            "resources",
            [
                "iron-ore",
                "copper-ore",
                "coal",
                "stone",
                "crude-oil",
                "uranium-ore",
                "wood",
            ],
        )
        basis = str(constraint.parameters.get("basis", "extracted"))
        source = final.produced if basis == "extracted" else final.consumed
        baseline_source = initial.produced if basis == "extracted" else initial.consumed
        weights = constraint.parameters.get("weights", {})
        deltas = {
            str(name): max(
                float(source.get(str(name), 0))
                - float(baseline_source.get(str(name), 0)),
                0.0,
            )
            for name in raw_resources
        }
        value = sum(
            amount * float(weights.get(name, 1.0))
            for name, amount in deltas.items()
        )
        satisfied = value <= float(constraint.limit)
        evidence.update({"basis": basis, "resources": deltas, "weights": weights})
    elif constraint.kind == "max_pollution":
        basis = str(constraint.parameters.get("basis", "emitted"))
        if basis == "total":
            value = final.pollution_total
        else:
            value = max(final.pollution_emitted - initial.pollution_emitted, 0.0)
        satisfied = value <= float(constraint.limit)
        evidence.update(
            {
                "basis": basis,
                "pollution_total": final.pollution_total,
                "pollution_emitted_delta": max(
                    final.pollution_emitted - initial.pollution_emitted, 0.0
                ),
            }
        )
    elif constraint.kind == "forbidden_action":
        forbidden = {
            str(value)
            for value in constraint.parameters.get(
                "actions",
                [constraint.limit] if constraint.limit is not None else [],
            )
        }
        invoked = [
            tool
            for event in events
            for tool in event.executed_tools
            if tool in forbidden
        ]
        value = float(len(invoked))
        satisfied = not invoked
        evidence.update(
            {
                "forbidden_actions": sorted(forbidden),
                "observed_violations": invoked,
                "source": "executed_tool_hooks",
            }
        )
    elif constraint.kind == "custom":
        value = None
        satisfied = False
        supported = False
        evidence["reason"] = "custom constraints require a registered verifier"
    else:
        value = None
        satisfied = False
        supported = False
        evidence["reason"] = f"unknown constraint kind {constraint.kind!r}"
    return ConstraintEvaluation(
        constraint_id=constraint.constraint_id,
        kind=constraint.kind,
        supported=supported,
        satisfied=satisfied,
        value=value,
        limit=constraint.limit,
        evidence=evidence,
    )


_BOTTLENECK_CATEGORIES = {
    "input_starvation": {
        "no_ingredients",
        "item_ingredient_shortage",
        "waiting_for_source_items",
        "no_input_fluid",
        "low_input_fluid",
        "fluid_ingredient_shortage",
        "missing_required_fluid",
    },
    "fuel_shortage": {"no_fuel"},
    "power_shortage": {
        "no_power",
        "low_power",
        "not_plugged_in_electric_network",
        "recharging_after_power_outage",
    },
    "output_blocked": {
        "full_output",
        "not_enough_space_in_output",
        "waiting_for_space_in_destination",
    },
    "missing_recipe": {"no_recipe", "recipe_not_researched"},
    "research_blocked": {"no_research_in_progress", "missing_science_packs"},
    "resource_depleted": {"no_minable_resources"},
}


def _bottlenecks(frame: TelemetryFrame) -> list[BottleneckSignal]:
    total = max(sum(frame.entity_status_counts.values()), 1)
    signals: list[BottleneckSignal] = []
    for category, statuses in _BOTTLENECK_CATEGORIES.items():
        counts = {
            status: frame.entity_status_counts.get(status, 0)
            for status in statuses
            if frame.entity_status_counts.get(status, 0)
        }
        affected = sum(counts.values())
        if affected:
            signals.append(
                BottleneckSignal(
                    category=category,
                    severity=affected / total,
                    affected_entities=affected,
                    statuses=counts,
                    evidence={"total_observed_entities": total},
                )
            )
    return sorted(signals, key=lambda signal: signal.severity, reverse=True)


@dataclass
class NativeVerificationResult:
    success: bool
    scalar_reward: float
    rewards: RewardVector
    metrics: dict[str, Any]
    events: list[VerifierEvent]
    diagnostics: PrivilegedDiagnosticPacket
    termination_reason: str


def _termination_reason(
    task: FactorioTaskSpec,
    success: bool,
    objectives: list[ObjectiveEvaluation],
    constraints: list[ConstraintEvaluation],
    action_events: list[ActionEvent],
    initial: TelemetryFrame,
    final: TelemetryFrame,
) -> str:
    if final.death_count > initial.death_count:
        return "character_died"
    if success:
        return "success"
    failed_constraints = [result for result in constraints if not result.satisfied]
    if failed_constraints:
        kinds = {result.kind for result in failed_constraints}
        if "max_interventions" in kinds:
            return "intervention_limit"
        if "max_ticks" in kinds:
            return "tick_limit"
        if "forbidden_action" in kinds:
            return "action_policy_violation"
        return "constraint_violation"
    if len(action_events) >= task.max_interventions:
        return "intervention_limit"
    if action_events and action_events[-1].error:
        return "invalid_action"
    if objectives and all(result.normalized_score <= 0 for result in objectives):
        return "no_progress"
    return "finalized"


def _success(
    task: FactorioTaskSpec,
    objectives: list[ObjectiveEvaluation],
    constraints: list[ConstraintEvaluation],
) -> bool:
    required = [
        result
        for spec, result in zip(task.objectives, objectives)
        if spec.required
    ]
    constraints_pass = all(result.supported and result.satisfied for result in constraints)
    if not constraints_pass:
        return False
    if not required:
        return True
    if task.verifier.mode == "all_required":
        return all(result.supported and result.satisfied for result in required)
    if task.verifier.mode == "any_required":
        return any(result.supported and result.satisfied for result in required)
    total_weight = sum(result.weight for result in required) or 1.0
    score = sum(
        result.normalized_score * result.weight for result in required
    ) / total_weight
    return score >= float(task.verifier.success_threshold or 1.0)


def _scalarize(
    task: FactorioTaskSpec,
    success: bool,
    objectives: list[ObjectiveEvaluation],
    constraints_pass: bool,
) -> float:
    if not constraints_pass:
        return 0.0
    if task.verifier.scalarization == "binary":
        return float(success)
    total_weight = sum(result.weight for result in objectives) or 1.0
    quality = sum(
        result.normalized_score * result.weight for result in objectives
    ) / total_weight
    if task.verifier.scalarization == "lexicographic":
        return float(success) + 0.1 * quality
    return quality


def verify_native(
    instance: Any,
    task: FactorioTaskSpec,
    action_events: list[ActionEvent],
    initial: TelemetryFrame,
) -> NativeVerificationResult:
    namespace = instance.first_namespace
    throughput_measurements: dict[str, list[float]] = {}
    for objective in task.objectives:
        if objective.kind != "throughput":
            continue
        measurements: list[float] = []
        for _ in range(task.verifier.holdout_windows):
            before = ProductionFlows.from_dict(namespace._get_production_stats())
            namespace.sleep(int(objective.window_seconds or 0))
            after = ProductionFlows.from_dict(namespace._get_production_stats())
            achievements = calculate_achievements(before, after)
            measurements.append(
                float(achievements["dynamic"].get(str(objective.target), 0))
            )
        throughput_measurements[objective.objective_id] = measurements

    targets = [objective.target for objective in task.objectives if objective.target]
    final = capture_telemetry(instance, targets)
    objectives = [
        evaluate_objective(
            objective,
            initial,
            final,
            throughput_measurements.get(objective.objective_id),
        )
        for objective in task.objectives
    ]
    constraints = [
        evaluate_constraint(task, constraint, initial, final, action_events)
        for constraint in task.constraints
    ]
    success = _success(task, objectives, constraints)
    constraints_pass = all(
        result.supported and result.satisfied for result in constraints
    )
    scalar = _scalarize(task, success, objectives, constraints_pass)

    produced = (
        _flow_delta(initial.produced, final.produced)
        if final.produced
        else _flow_delta(initial.flows.output, final.flows.output)
    )
    consumed = (
        _flow_delta(initial.consumed, final.consumed)
        if final.consumed
        else _flow_delta(initial.flows.input, final.flows.input)
    )
    automatic = calculate_achievements(initial.flows, final.flows)["dynamic"]
    manual = _flow_delta(_manual_outputs(initial.flows), _manual_outputs(final.flows))
    inventory_delta = _flow_delta(initial.inventory, final.inventory)
    relevant_research = {
        objective.target: final.technologies.get(str(objective.target), {})
        for objective in task.objectives
        if objective.kind == "research" and objective.target
    }
    termination_reason = _termination_reason(
        task, success, objectives, constraints, action_events, initial, final
    )
    death_records = [
        CharacterDeath.model_validate(death)
        for death in final.deaths[len(initial.deaths) :]
    ]
    resource_depletions = final.resource_depletions[
        len(initial.resource_depletions) :
    ]
    executed_tools = [
        tool for event in action_events for tool in event.executed_tools
    ]
    policy_violations = [
        violation for event in action_events for violation in event.policy_violations
    ]
    raw_resource_names = {
        "iron-ore",
        "copper-ore",
        "coal",
        "stone",
        "crude-oil",
        "uranium-ore",
        "wood",
    }
    raw_extracted = {
        name: amount for name, amount in produced.items() if name in raw_resource_names
    }
    raw_consumed = {
        name: amount for name, amount in consumed.items() if name in raw_resource_names
    }
    diagnostics = PrivilegedDiagnosticPacket(
        task_id=task.task_id,
        tick=final.tick,
        elapsed_ticks=max(final.tick - initial.tick, 0),
        objective_evaluations=objectives,
        constraint_evaluations=constraints,
        inventory=final.inventory,
        inventory_delta=inventory_delta,
        production=produced,
        consumption=consumed,
        automated_production={
            str(key): float(value) for key, value in automatic.items()
        },
        manual_crafts=manual,
        research={
            "researched_count": sum(final.researched.values()),
            "technology_count": len(final.researched),
            "current": final.current_research,
            "progress": final.research_progress,
            "relevant": relevant_research,
        },
        entity_counts=final.entity_counts,
        entity_status_counts=final.entity_status_counts,
        bottlenecks=_bottlenecks(final),
        lifecycle=LifecycleStatus(
            character_alive=final.character_alive,
            character_health=final.character_health,
            death_count=max(final.death_count - initial.death_count, 0),
            deaths=death_records,
            respawn_count=max(final.respawn_count - initial.respawn_count, 0),
            last_respawn_tick=final.last_respawn_tick,
            character_recreated_after_death=bool(
                death_records and final.character_alive
            ),
            termination_reason=termination_reason,
        ),
        pollution={
            "total": final.pollution_total,
            "emitted_delta": max(
                final.pollution_emitted - initial.pollution_emitted, 0.0
            ),
        },
        resource_accounting={
            "raw_extracted": raw_extracted,
            "raw_consumed": raw_consumed,
            "all_produced": produced,
            "all_consumed": consumed,
        },
        action_policy={
            "executed_tools": executed_tools,
            "violations": policy_violations,
        },
        resource_depletions=resource_depletions,
        target_recipes=final.target_recipes,
        knowledge_sources=task.knowledge_sources,
        caveats=[
            "Bottlenecks are status-derived signals, not a complete causal graph.",
            "Raw-resource cost is derived from engine production-flow counters; "
            "task specifications must choose extracted or consumed semantics.",
            "Tool-policy auditing records actual FLE controller calls, but cannot "
            "classify arbitrary computation inside a submitted Python program.",
        ],
    )

    tick = final.tick
    verifier_events: list[VerifierEvent] = []
    for objective, result in zip(task.objectives, objectives):
        kind = "objective_satisfied" if result.satisfied else "objective_failed"
        if result.satisfied and objective.kind == "research":
            kind = "technology_researched"
        elif result.satisfied and objective.kind in {
            "entity_exists",
            "rocket_launch",
        }:
            kind = "milestone_reached"
        verifier_events.append(
            VerifierEvent(
                event_id=f"objective:{objective.objective_id}",
                kind=kind,
                tick=tick,
                source="verifier",
                objective_id=objective.objective_id,
                payload={
                    "supported": result.supported,
                    "satisfied": result.satisfied,
                    "value": result.value,
                    "threshold": result.threshold,
                    "normalized_score": result.normalized_score,
                },
                evidence=result.evidence,
                reward_channels={"progress": result.normalized_score * result.weight},
            )
        )
    for result in constraints:
        verifier_events.append(
            VerifierEvent(
                event_id=f"constraint:{result.constraint_id}",
                kind=(
                    "constraint_satisfied"
                    if result.supported and result.satisfied
                    else "constraint_failed"
                ),
                tick=tick,
                source="verifier",
                payload={
                    "supported": result.supported,
                    "satisfied": result.satisfied,
                    "value": result.value,
                    "limit": result.limit,
                },
                evidence=result.evidence,
            )
        )
    for index, death in enumerate(death_records):
        verifier_events.append(
            VerifierEvent(
                event_id=f"lifecycle:death:{index + 1}",
                kind="character_died",
                tick=death.tick,
                source="engine",
                payload={
                    "player_index": death.player_index,
                    "damage_type": death.damage_type,
                    "train_involved": death.train is not None,
                },
                evidence=death.model_dump(mode="json"),
            )
        )
    for index, depletion in enumerate(resource_depletions):
        verifier_events.append(
            VerifierEvent(
                event_id=f"resource:depleted:{index + 1}",
                kind="resource_depleted",
                tick=int(depletion.get("tick", tick)),
                source="engine",
                payload={
                    "name": depletion.get("name", "unknown"),
                    "position": depletion.get("position", {}),
                },
                evidence=depletion,
            )
        )
    verifier_events.append(
        VerifierEvent(
            event_id="termination:classified",
            kind="termination_classified",
            tick=tick,
            source="verifier",
            payload={"reason": termination_reason, "success": success},
        )
    )
    verifier_events.append(
        VerifierEvent(
            event_id="verification:completed",
            kind="verification_completed",
            tick=tick,
            source="verifier",
            payload={
                "success": success,
                "scalar_reward": scalar,
                "termination_reason": termination_reason,
            },
        )
    )

    throughput = sum(
        float(result.value or 0)
        for result in objectives
        if result.kind == "throughput"
    )
    milestone = float(
        sum(
            result.satisfied
            for result in objectives
            if result.kind in {"research", "entity_exists", "rocket_launch"}
        )
    )
    manual_count = _manual_craft_count(final.flows) - _manual_craft_count(initial.flows)
    progress = sum(result.normalized_score * result.weight for result in objectives)
    automated_score_delta = (
        final.automated_production_score - initial.automated_production_score
    )
    # FLE's legacy automated score is a net-value statistic: it subtracts
    # consumed inputs. A task that provisions science packs or other inputs can
    # therefore have a negative net delta despite completing its objective.
    # Preserve that signed statistic in metrics, but do not leak it into a
    # positive-capability reward channel. Resource and intervention costs have
    # their own explicitly negative channels.
    automation_reward = max(automated_score_delta, 0.0)
    return NativeVerificationResult(
        success=success,
        scalar_reward=scalar,
        rewards=RewardVector(
            task=float(success),
            throughput=throughput,
            automation=automation_reward,
            progress=progress,
            invalid_action=-float(sum(event.error for event in action_events)),
            resource_cost=-float(sum(raw_extracted.values())),
            milestone=milestone,
            time_efficiency=-float(max(final.tick - initial.tick, 0)),
            manual_intervention=-manual_count,
        ),
        metrics={
            "objective_evaluations": [
                result.model_dump(mode="json") for result in objectives
            ],
            "constraint_evaluations": [
                result.model_dump(mode="json") for result in constraints
            ],
            "production_score": final.production_score,
            "automated_production_score": final.automated_production_score,
            "automated_production_score_delta": automated_score_delta,
            "automation_reward": automation_reward,
            "automation_reward_basis": "nonnegative_legacy_net_value_delta",
            "interventions": len(action_events),
            "elapsed_ticks": max(final.tick - initial.tick, 0),
        },
        events=verifier_events,
        diagnostics=diagnostics,
        termination_reason=termination_reason,
    )
