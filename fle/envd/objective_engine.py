"""Native multi-objective verification and privileged Factorio diagnostics."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

from fle.commons.models.achievements import ProductionFlows
from fle.env.utils.achievements import calculate_achievements
from fle.envd.models import (
    ActionEvent,
    BottleneckSignal,
    CharacterDeath,
    ConstraintEvaluation,
    FactorioTaskSpec,
    FutureProbeResult,
    LifecycleStatus,
    ObjectiveEvaluation,
    ObjectiveSpec,
    PrivilegedDiagnosticPacket,
    RewardVector,
    StateDimensionDelta,
    StateQualityComparison,
    StateQualitySnapshot,
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
                for _, item in sorted(raw.items(), key=lambda pair: int(str(pair[0])))
            ]
        except (TypeError, ValueError):
            return []
    return []


def _flow_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
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
    return float(sum(float(craft.get("crafted_count", 0)) for craft in flows.crafted))


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
    entity_details: list[dict[str, Any]]
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


def capture_telemetry(
    instance: Any,
    targets: Iterable[str] = (),
    *,
    research_state=None,
) -> TelemetryFrame:
    namespace = instance.first_namespace
    engine = _objective_telemetry(namespace)
    flows = ProductionFlows.from_dict(namespace._get_production_stats())
    production_score, automated_score = namespace.score()
    if research_state is None:
        research = namespace._save_research_state()
    else:
        research = research_state
    entities = list(_leaf_entities(namespace.get_entities()))

    entity_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    status_by_name: dict[str, dict[str, int]] = {}
    entity_details: list[dict[str, Any]] = []
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
        detail = _jsonable(entity)
        if isinstance(detail, dict):
            detail["name"] = name
            detail["status"] = status
            entity_details.append(detail)

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
            str(research.current_research)
            if research and research.current_research
            else None
        ),
        research_progress=float(research.research_progress if research else 0),
        entity_counts=entity_counts,
        entity_status_counts=status_counts,
        entity_status_by_name=status_by_name,
        entity_details=entity_details,
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
        return value >= threshold, (
            min(max(value / threshold, 0.0), 1.0) if threshold else 1.0
        )
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


def _matching_entities(frame: TelemetryFrame, target: str) -> list[dict[str, Any]]:
    return [
        entity
        for entity in frame.entity_details
        if str(entity.get("name", "")) == target
    ]


def _recipe_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name")
        if name is not None:
            return str(name)
    return str(value)


_ENTITY_INVENTORY_FIELDS = {
    "assembling_machine_input",
    "assembling_machine_output",
    "assembling_machine_modules",
    "fuel",
    "furnace_source",
    "furnace_result",
    "inventory",
    "lab_input",
    "lab_modules",
    "rocket_inventory",
    "turret_ammo",
}


def _inventory_amount(entity: dict[str, Any], item: str) -> float:
    total = 0.0
    for field_name in _ENTITY_INVENTORY_FIELDS:
        inventory = entity.get(field_name)
        if not isinstance(inventory, dict):
            continue
        amount = inventory.get(item, 0)
        if isinstance(amount, (int, float)):
            total += float(amount)
    return total


def _position_matches(
    entity: dict[str, Any], x: float, y: float, tolerance: float
) -> bool:
    position = entity.get("position")
    if not isinstance(position, dict):
        return False
    actual_x = position.get("x")
    actual_y = position.get("y")
    if not isinstance(actual_x, (int, float)) or not isinstance(actual_y, (int, float)):
        return False
    return math.dist((float(actual_x), float(actual_y)), (x, y)) <= tolerance


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
                final.flows.output.get(target, 0) - initial.flows.output.get(target, 0)
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
    elif objective.kind == "entity_status":
        if target is None:
            return _unsupported_objective(objective, "entity target missing")
        statuses = {str(status) for status in objective.parameters.get("statuses", [])}
        if not statuses:
            return _unsupported_objective(
                objective, "entity_status requires parameters.statuses"
            )
        baseline = float(
            sum(
                initial.entity_status_by_name.get(target, {}).get(status, 0)
                for status in statuses
            )
        )
        value = float(
            sum(
                final.entity_status_by_name.get(target, {}).get(status, 0)
                for status in statuses
            )
        )
        evidence.update(
            {
                "accepted_statuses": sorted(statuses),
                "observed_statuses": final.entity_status_by_name.get(target, {}),
            }
        )
    elif objective.kind == "entity_recipe":
        if target is None:
            return _unsupported_objective(objective, "entity target missing")
        recipe = objective.parameters.get("recipe")
        if not recipe:
            return _unsupported_objective(
                objective, "entity_recipe requires parameters.recipe"
            )
        baseline = float(
            sum(
                _recipe_name(entity.get("recipe")) == str(recipe)
                for entity in _matching_entities(initial, target)
            )
        )
        final_entities = _matching_entities(final, target)
        value = float(
            sum(
                _recipe_name(entity.get("recipe")) == str(recipe)
                for entity in final_entities
            )
        )
        evidence.update(
            {
                "required_recipe": str(recipe),
                "observed_recipes": [
                    _recipe_name(entity.get("recipe")) for entity in final_entities
                ],
            }
        )
    elif objective.kind == "entity_inventory":
        if target is None:
            return _unsupported_objective(objective, "entity target missing")
        item = objective.parameters.get("item")
        if not item:
            return _unsupported_objective(
                objective, "entity_inventory requires parameters.item"
            )
        baseline = sum(
            _inventory_amount(entity, str(item))
            for entity in _matching_entities(initial, target)
        )
        value = sum(
            _inventory_amount(entity, str(item))
            for entity in _matching_entities(final, target)
        )
        evidence.update(
            {
                "item": str(item),
                "inventory_fields": sorted(_ENTITY_INVENTORY_FIELDS),
            }
        )
    elif objective.kind == "entity_position":
        if target is None:
            return _unsupported_objective(objective, "entity target missing")
        x = objective.parameters.get("x")
        y = objective.parameters.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return _unsupported_objective(
                objective, "entity_position requires numeric parameters.x and y"
            )
        tolerance = float(objective.parameters.get("tolerance", 0.25))
        baseline = float(
            sum(
                _position_matches(entity, float(x), float(y), tolerance)
                for entity in _matching_entities(initial, target)
            )
        )
        final_entities = _matching_entities(final, target)
        value = float(
            sum(
                _position_matches(entity, float(x), float(y), tolerance)
                for entity in final_entities
            )
        )
        evidence.update(
            {
                "target_position": {"x": float(x), "y": float(y)},
                "tolerance": tolerance,
                "observed_positions": [
                    entity.get("position") for entity in final_entities
                ],
            }
        )
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
        value = float(sum(not event.evaluation_retry for event in events))
        satisfied = value <= float(constraint.limit)
        evidence.update(
            {
                "total_interventions": len(events),
                "evaluation_retries": sum(event.evaluation_retry for event in events),
            }
        )
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
            amount * float(weights.get(name, 1.0)) for name, amount in deltas.items()
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
    elif constraint.kind == "required_action":
        required = {
            str(action)
            for action in constraint.parameters.get(
                "actions",
                [constraint.limit] if constraint.limit is not None else [],
            )
        }
        counts = {
            action: sum(
                tool == action for event in events for tool in event.executed_tools
            )
            for action in required
        }
        minimum_calls = int(constraint.parameters.get("minimum_calls", 1))
        missing = [action for action, count in counts.items() if count < minimum_calls]
        value = float(sum(counts.values()))
        satisfied = bool(required) and not missing
        evidence.update(
            {
                "required_actions": sorted(required),
                "minimum_calls_each": minimum_calls,
                "observed_calls": counts,
                "missing_actions": missing,
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


_MILESTONE_OBJECTIVE_KINDS = {
    "research",
    "entity_exists",
    "entity_recipe",
    "rocket_launch",
}


def _weighted_progress(results: list[ObjectiveEvaluation]) -> float:
    supported = [result for result in results if result.supported]
    total_weight = sum(max(result.weight, 0.0) for result in supported)
    if total_weight <= 0:
        return 0.0
    return min(
        max(
            sum(result.normalized_score * max(result.weight, 0.0) for result in supported)
            / total_weight,
            0.0,
        ),
        1.0,
    )


def build_state_quality_snapshot(
    task: FactorioTaskSpec,
    initial: TelemetryFrame,
    current: TelemetryFrame,
    *,
    state_hash: str,
    action_events: list[ActionEvent] | None = None,
    throughput_measurements: dict[str, list[float]] | None = None,
    horizon_ticks: int = 0,
    future_probes: list[FutureProbeResult] | None = None,
) -> StateQualitySnapshot:
    """Build a typed, task-conditioned summary without inventing missing signal."""

    events = action_events or []
    measurements = throughput_measurements or {}
    objective_results = [
        evaluate_objective(
            objective,
            initial,
            current,
            measurements.get(objective.objective_id),
        )
        for objective in task.objectives
    ]
    constraint_results = [
        evaluate_constraint(task, constraint, initial, current, events)
        for constraint in task.constraints
    ]
    milestone_results = [
        result
        for result in objective_results
        if result.kind in _MILESTONE_OBJECTIVE_KINDS and result.supported
    ]
    throughput_results = [
        result
        for result in objective_results
        if result.kind == "throughput" and result.supported
    ]

    automatic = calculate_achievements(initial.flows, current.flows)["dynamic"]
    manual = _flow_delta(_manual_outputs(initial.flows), _manual_outputs(current.flows))
    automatic_total = sum(max(float(value), 0.0) for value in automatic.values())
    manual_total = sum(max(float(value), 0.0) for value in manual.values())
    automation_quality = (
        automatic_total / (automatic_total + manual_total)
        if automatic_total + manual_total > 0
        else None
    )
    bottlenecks = _bottlenecks(current)
    operational_health = None
    if current.entity_status_counts:
        operational_health = max(
            1.0 - min(sum(signal.severity for signal in bottlenecks), 1.0),
            0.0,
        )

    probes = future_probes or []
    future_option_value = (
        sum(probe.normalized_score for probe in probes) / len(probes)
        if probes
        else None
    )
    invariant_violations = [
        f"constraint:{result.constraint_id}"
        for result in constraint_results
        if result.supported and not result.satisfied
    ]
    if current.death_count > initial.death_count or not current.character_alive:
        invariant_violations.append("character_survival")

    produced = (
        _flow_delta(initial.produced, current.produced)
        if current.produced
        else _flow_delta(initial.flows.output, current.flows.output)
    )
    consumed = (
        _flow_delta(initial.consumed, current.consumed)
        if current.consumed
        else _flow_delta(initial.flows.input, current.flows.input)
    )
    raw_names = {
        "iron-ore",
        "copper-ore",
        "coal",
        "stone",
        "crude-oil",
        "uranium-ore",
        "wood",
    }
    deaths = [
        CharacterDeath.model_validate(death)
        for death in current.deaths[len(initial.deaths) :]
    ]
    return StateQualitySnapshot(
        task_id=task.task_id,
        state_hash=state_hash,
        tick=current.tick,
        horizon_ticks=max(horizon_ticks, 0),
        objective_progress=_weighted_progress(objective_results),
        milestone_progress=(
            _weighted_progress(milestone_results) if milestone_results else None
        ),
        sustained_capability=(
            _weighted_progress(throughput_results) if throughput_results else None
        ),
        automation_quality=automation_quality,
        operational_health=operational_health,
        future_option_value=future_option_value,
        safety=(
            1.0
            if current.character_alive and current.death_count == initial.death_count
            else 0.0
        ),
        production_score=current.production_score,
        automated_production_score=current.automated_production_score,
        objective_evaluations=objective_results,
        constraint_evaluations=constraint_results,
        automated_production={
            str(key): float(value) for key, value in automatic.items()
        },
        manual_production=manual,
        bottlenecks=bottlenecks,
        researched_technologies=sorted(
            name for name, researched in current.researched.items() if researched
        ),
        entity_counts=current.entity_counts,
        lifecycle=LifecycleStatus(
            character_alive=current.character_alive,
            character_health=current.character_health,
            death_count=max(current.death_count - initial.death_count, 0),
            deaths=deaths,
            respawn_count=max(current.respawn_count - initial.respawn_count, 0),
            last_respawn_tick=current.last_respawn_tick,
            character_recreated_after_death=bool(deaths and current.character_alive),
        ),
        resource_accounting={
            "raw_extracted": {
                name: amount for name, amount in produced.items() if name in raw_names
            },
            "raw_consumed": {
                name: amount for name, amount in consumed.items() if name in raw_names
            },
            "all_produced": produced,
            "all_consumed": consumed,
        },
        pollution={
            "total": current.pollution_total,
            "emitted_delta": max(
                current.pollution_emitted - initial.pollution_emitted, 0.0
            ),
        },
        future_probes=probes,
        invariant_violations=sorted(set(invariant_violations)),
        caveats=[
            (
                "This is a task-conditioned partial-order summary, not a universal "
                "scalar measure of factory quality."
            ),
            (
                "Sustained capability is omitted unless an autonomous holdout was "
                "measured for a throughput objective."
            ),
            "Future option value is omitted unless identical branch probes were run.",
        ],
    )


def compare_state_quality(
    previous: StateQualitySnapshot,
    current: StateQualitySnapshot,
    *,
    tolerance: float = 1e-6,
) -> StateQualityComparison:
    """Compare states conservatively: mixed trade-offs remain incomparable."""

    if previous.task_id != current.task_id:
        raise ValueError("State quality snapshots must belong to the same task")
    dimensions = (
        "objective_progress",
        "milestone_progress",
        "sustained_capability",
        "automation_quality",
        "operational_health",
        "future_option_value",
        "safety",
    )
    deltas: list[StateDimensionDelta] = []
    improvements: list[str] = []
    regressions: list[str] = []
    for dimension in dimensions:
        before = getattr(previous, dimension)
        after = getattr(current, dimension)
        if before is None or after is None:
            continue
        delta = float(after) - float(before)
        if delta > tolerance:
            classification = "improved"
            improvements.append(dimension)
        elif delta < -tolerance:
            classification = "regressed"
            regressions.append(dimension)
        else:
            classification = "preserved"
        deltas.append(
            StateDimensionDelta(
                dimension=dimension,
                previous=float(before),
                current=float(after),
                delta=delta,
                classification=classification,
            )
        )

    previous_violations = set(previous.invariant_violations)
    current_violations = set(current.invariant_violations)
    new_violations = sorted(current_violations - previous_violations)
    resolved_violations = sorted(previous_violations - current_violations)
    previous_research = set(previous.researched_technologies)
    current_research = set(current.researched_technologies)
    lost_research = sorted(previous_research - current_research)
    if lost_research:
        new_violations.extend(f"research_lost:{name}" for name in lost_research)

    previous_probes = {
        probe.probe_id: probe.normalized_score for probe in previous.future_probes
    }
    current_probes = {
        probe.probe_id: probe.normalized_score for probe in current.future_probes
    }
    for probe_id in sorted(previous_probes.keys() & current_probes.keys()):
        delta = current_probes[probe_id] - previous_probes[probe_id]
        name = f"future_probe:{probe_id}"
        if delta > tolerance:
            improvements.append(name)
        elif delta < -tolerance:
            regressions.append(name)
        deltas.append(
            StateDimensionDelta(
                dimension=name,
                previous=previous_probes[probe_id],
                current=current_probes[probe_id],
                delta=delta,
                classification=(
                    "improved"
                    if delta > tolerance
                    else "regressed"
                    if delta < -tolerance
                    else "preserved"
                ),
            )
        )

    improvements.extend(f"invariant_resolved:{name}" for name in resolved_violations)
    regressions.extend(f"invariant_violated:{name}" for name in new_violations)
    material_change = bool(improvements or regressions)
    if new_violations:
        verdict = "regresses"
        explanation = "A hard invariant was newly violated."
    elif improvements and not regressions:
        verdict = "dominates"
        explanation = "At least one comparable quality dimension improved and none regressed."
    elif regressions and not improvements:
        verdict = "regresses"
        explanation = "At least one comparable quality dimension regressed and none improved."
    else:
        verdict = "incomparable"
        explanation = (
            "The states contain material trade-offs."
            if material_change
            else "No material change was established on comparable dimensions."
        )

    previous_top = previous.bottlenecks[0] if previous.bottlenecks else None
    current_top = current.bottlenecks[0] if current.bottlenecks else None
    bottleneck_shift = None
    if (
        previous_top is not None
        and current_top is not None
        and (
            previous_top.category != current_top.category
            or not math.isclose(previous_top.severity, current_top.severity)
        )
    ):
        bottleneck_shift = {
            "from": previous_top.model_dump(mode="json"),
            "to": current_top.model_dump(mode="json"),
        }
    return StateQualityComparison(
        task_id=current.task_id,
        previous_state_hash=previous.state_hash,
        current_state_hash=current.state_hash,
        verdict=verdict,
        material_change=material_change,
        dimension_deltas=deltas,
        improvements=sorted(set(improvements)),
        regressions=sorted(set(regressions)),
        preserved_invariants=sorted(
            current_research
            | {
                name
                for name in previous_violations
                if name in current_violations
            }
        ),
        new_invariant_violations=sorted(set(new_violations)),
        resolved_invariant_violations=resolved_violations,
        bottleneck_shift=bottleneck_shift,
        explanation=explanation,
    )


def measure_autonomous_holdout(
    instance: Any,
    task: FactorioTaskSpec,
    seconds: int,
) -> tuple[TelemetryFrame, dict[str, list[float]], int]:
    """Advance the untouched factory and measure target output over one window."""

    targets = [objective.target for objective in task.objectives if objective.target]
    before = capture_telemetry(instance, targets)
    instance.first_namespace.sleep(seconds)
    after = capture_telemetry(instance, targets)
    measurements: dict[str, list[float]] = {}
    achievements = calculate_achievements(before.flows, after.flows)["dynamic"]
    for objective in task.objectives:
        if objective.kind == "throughput" and objective.target:
            observed = float(achievements.get(str(objective.target), 0.0))
            declared_window = int(objective.window_seconds or seconds)
            projected_to_declared_window = (
                observed * declared_window / seconds if seconds else observed
            )
            measurements[objective.objective_id] = [
                projected_to_declared_window
            ]
    return after, measurements, max(after.tick - before.tick, 0)


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
    scored_interventions = sum(not event.evaluation_retry for event in action_events)
    if scored_interventions >= task.max_interventions:
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
        result for spec, result in zip(task.objectives, objectives) if spec.required
    ]
    constraints_pass = all(
        result.supported and result.satisfied for result in constraints
    )
    if not constraints_pass:
        return False
    if not required:
        return True
    if task.verifier.mode == "all_required":
        return all(result.supported and result.satisfied for result in required)
    if task.verifier.mode == "any_required":
        return any(result.supported and result.satisfied for result in required)
    total_weight = sum(result.weight for result in required) or 1.0
    score = (
        sum(result.normalized_score * result.weight for result in required)
        / total_weight
    )
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
    quality = (
        sum(result.normalized_score * result.weight for result in objectives)
        / total_weight
    )
    if task.verifier.scalarization == "lexicographic":
        return float(success) + 0.1 * quality
    return quality


def verify_native(
    instance: Any,
    task: FactorioTaskSpec,
    action_events: list[ActionEvent],
    initial: TelemetryFrame,
    customer_result: Any | None = None,
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
    contract_event_payloads: list[dict[str, Any]] = []
    if customer_result is not None:
        from fle.envd.customer import success_from_evaluation

        contract_satisfied = success_from_evaluation(customer_result, task.customer)
        objectives.append(
            ObjectiveEvaluation(
                objective_id="customer:contracts",
                kind="contract_fulfillment",
                supported=True,
                satisfied=contract_satisfied,
                value=customer_result.aggregate_ratio,
                baseline=None,
                threshold=task.customer.success_ratio,
                normalized_score=min(max(customer_result.net_reward, 0.0), 1.0),
                weight=1.0,
                evidence={
                    "commitment": customer_result.commitment,
                    "engine_version": customer_result.engine_version,
                    "finalized_at_tick": customer_result.finalized_at_tick,
                    "aggregate_ratio": customer_result.aggregate_ratio,
                    "fulfillment_reward": customer_result.fulfillment_reward,
                    "penalty": customer_result.penalty,
                    "net_reward": customer_result.net_reward,
                    "unattributed_deliveries": customer_result.unattributed,
                    "receipt_mac": customer_result.receipt_mac,
                    "order_results": [
                        result.as_payload()
                        for result in customer_result.order_results
                    ],
                },
            )
        )
        for result in customer_result.order_results:
            kind = (
                "contract_fulfilled"
                if result.ratio + 1e-9 >= 1.0 and result.status != "expired"
                else "contract_expired"
            )
            contract_event_payloads.append(
                {
                    "event_id": f"customer:{result.order_id}",
                    "kind": kind,
                    "payload": result.as_payload(),
                    "channels": {
                        "contracts": result.ratio * result.weight,
                        "contract_penalty": -result.lateness_penalty * result.weight,
                    },
                }
            )
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
    resource_depletions = final.resource_depletions[len(initial.resource_depletions) :]
    executed_tools = [tool for event in action_events for tool in event.executed_tools]
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
            (
                "Raw-resource cost is derived from engine production-flow counters; "
                "task specifications must choose extracted or consumed semantics."
            ),
            (
                "Tool-policy auditing records actual FLE controller calls, but cannot "
                "classify arbitrary computation inside a submitted Python program."
            ),
        ],
    )

    tick = final.tick
    verifier_events: list[VerifierEvent] = []
    for payload in contract_event_payloads:
        verifier_events.append(
            VerifierEvent(
                event_id=payload["event_id"],
                kind=payload["kind"],
                tick=final.tick,
                source="verifier",
                payload=payload["payload"],
                evidence={"commitment": customer_result.commitment},
                reward_channels=payload["channels"],
            )
        )
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
        float(result.value or 0) for result in objectives if result.kind == "throughput"
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
    customer_metrics: dict[str, Any] = {}
    contract_channels: dict[str, float] = {}
    if customer_result is not None:
        customer_receipt = dict(customer_result.receipt)
        customer_receipt.pop("receipt_context", None)
        customer_metrics = {
            "customer_commitment": customer_result.commitment,
            "customer_aggregate_ratio": customer_result.aggregate_ratio,
            "customer_fulfillment_reward": customer_result.fulfillment_reward,
            "customer_penalty": customer_result.penalty,
            "customer_net_reward": customer_result.net_reward,
            "customer_unattributed_deliveries": customer_result.unattributed,
            "customer_receipt_mac": customer_result.receipt_mac,
            "customer_receipt": {
                **customer_receipt,
                "receipt_mac": customer_result.receipt_mac,
            },
        }
        contract_channels = {
            "contracts": customer_result.fulfillment_reward,
            "contract_penalty": -customer_result.penalty,
        }
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
            **contract_channels,
        ),
        metrics={
            **customer_metrics,
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
            "scored_interventions": sum(
                not event.evaluation_retry for event in action_events
            ),
            "evaluation_retries": sum(
                event.evaluation_retry for event in action_events
            ),
            "elapsed_ticks": max(final.tick - initial.tick, 0),
        },
        events=verifier_events,
        diagnostics=diagnostics,
        termination_reason=termination_reason,
    )
