from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from fle.commons.models.achievements import ProductionFlows
from fle.commons.models.research_state import ResearchState
from fle.commons.models.technology_state import TechnologyState
from fle.env.entities import EntityStatus
from fle.envd.models import (
    ActionEvent,
    ConstraintSpec,
    CurriculumSpec,
    FactorioTaskSpec,
    FutureProbeResult,
    ObjectiveSpec,
    StateQualitySnapshot,
    VerifierSpec,
)
from fle.envd.objective_engine import (
    TelemetryFrame,
    build_state_quality_snapshot,
    capture_telemetry,
    compare_state_quality,
    evaluate_constraint,
    evaluate_objective,
    measure_autonomous_holdout,
    verify_native,
)

pytestmark = pytest.mark.no_factorio


def technology(name: str, researched: bool) -> TechnologyState:
    return TechnologyState(
        name=name,
        researched=researched,
        enabled=True,
        level=1,
        research_unit_count=10,
        research_unit_energy=30,
        prerequisites=[],
        ingredients=[],
    )


def frame(**updates) -> TelemetryFrame:
    values = {
        "tick": 0,
        "inventory": {},
        "flows": ProductionFlows(input={}, output={}, crafted=[], harvested={}),
        "production_score": 0.0,
        "automated_production_score": 0.0,
        "researched": {"automation": False},
        "technologies": {
            "automation": {
                "name": "automation",
                "researched": False,
                "prerequisites": [],
            }
        },
        "current_research": None,
        "research_progress": 0.0,
        "entity_counts": {},
        "entity_status_counts": {},
        "entity_status_by_name": {},
        "entity_details": [],
        "rocket_launches": 0,
        "target_recipes": {},
    }
    values.update(updates)
    return TelemetryFrame(**values)


def test_research_and_entity_objectives_are_engine_state_predicates():
    initial = frame(entity_counts={"assembling-machine-1": 0})
    final = frame(
        researched={"automation": True},
        entity_counts={"assembling-machine-1": 2},
        entity_status_by_name={"assembling-machine-1": {"working": 2}},
    )
    research = ObjectiveSpec(
        objective_id="research",
        kind="research",
        description="Research automation.",
        target="automation",
        comparator="eq",
        threshold=1,
    )
    entity = ObjectiveSpec(
        objective_id="assemblers",
        kind="entity_exists",
        description="Build two assemblers.",
        target="assembling-machine-1",
        comparator="gte",
        threshold=2,
    )

    assert evaluate_objective(research, initial, final).satisfied
    entity_result = evaluate_objective(entity, initial, final)
    assert entity_result.satisfied
    assert entity_result.evidence["status_counts"] == {"working": 2}


def test_entity_configuration_objectives_read_engine_entity_details():
    initial = frame()
    final = frame(
        entity_details=[
            {
                "name": "assembling-machine-1",
                "status": "working",
                "position": {"x": 4.0, "y": -2.0},
                "recipe": {"name": "iron-gear-wheel"},
                "assembling_machine_input": {"iron-plate": 6},
            }
        ],
        entity_status_by_name={"assembling-machine-1": {"working": 1}},
    )
    objectives = [
        ObjectiveSpec(
            objective_id="status",
            kind="entity_status",
            description="Assembler works.",
            target="assembling-machine-1",
            comparator="gte",
            threshold=1,
            parameters={"statuses": ["working"]},
        ),
        ObjectiveSpec(
            objective_id="recipe",
            kind="entity_recipe",
            description="Assembler has a recipe.",
            target="assembling-machine-1",
            comparator="gte",
            threshold=1,
            parameters={"recipe": "iron-gear-wheel"},
        ),
        ObjectiveSpec(
            objective_id="inventory",
            kind="entity_inventory",
            description="Assembler has plates.",
            target="assembling-machine-1",
            comparator="gte",
            threshold=5,
            parameters={"item": "iron-plate"},
        ),
        ObjectiveSpec(
            objective_id="position",
            kind="entity_position",
            description="Assembler is at the target coordinate.",
            target="assembling-machine-1",
            comparator="gte",
            threshold=1,
            parameters={"x": 4, "y": -2, "tolerance": 0.1},
        ),
    ]

    assert all(
        evaluate_objective(objective, initial, final).satisfied
        for objective in objectives
    )


def quality(**updates) -> StateQualitySnapshot:
    values = {
        "task_id": "quality-task",
        "state_hash": "state-a",
        "tick": 0,
        "objective_progress": 0.2,
        "milestone_progress": 0.0,
        "sustained_capability": 0.2,
        "automation_quality": 0.5,
        "operational_health": 0.8,
        "safety": 1.0,
        "researched_technologies": ["automation"],
    }
    values.update(updates)
    return StateQualitySnapshot(**values)


def test_state_quality_dominance_requires_non_regression_on_all_dimensions():
    previous = quality()
    current = quality(
        state_hash="state-b",
        tick=60,
        objective_progress=0.7,
        sustained_capability=0.8,
        automation_quality=0.6,
    )

    comparison = compare_state_quality(previous, current)

    assert comparison.verdict == "dominates"
    assert comparison.improvements == [
        "automation_quality",
        "objective_progress",
        "sustained_capability",
    ]
    assert comparison.regressions == []


def test_state_quality_marks_real_tradeoffs_incomparable():
    comparison = compare_state_quality(
        quality(),
        quality(
            state_hash="state-b",
            objective_progress=0.7,
            operational_health=0.3,
        ),
    )

    assert comparison.verdict == "incomparable"
    assert "objective_progress" in comparison.improvements
    assert "operational_health" in comparison.regressions


def test_state_quality_new_hard_violation_forces_regression():
    comparison = compare_state_quality(
        quality(),
        quality(
            state_hash="state-b",
            objective_progress=0.9,
            invariant_violations=["character_survival"],
            safety=0.0,
        ),
    )

    assert comparison.verdict == "regresses"
    assert comparison.new_invariant_violations == ["character_survival"]


def test_future_branch_probes_are_comparable_when_probe_ids_match():
    previous = quality(
        future_probes=[
            FutureProbeResult(probe_id="double-output", normalized_score=0.2)
        ]
    )
    current = quality(
        state_hash="state-b",
        future_probes=[
            FutureProbeResult(probe_id="double-output", normalized_score=0.8)
        ],
    )

    comparison = compare_state_quality(previous, current)

    assert comparison.verdict == "dominates"
    assert "future_probe:double-output" in comparison.improvements


def test_quality_snapshot_uses_holdout_for_sustained_capability():
    task = FactorioTaskSpec(
        task_id="quality-task",
        goal="Produce gears autonomously.",
        objectives=[
            ObjectiveSpec(
                objective_id="gear-rate",
                kind="throughput",
                description="Produce ten gears during the holdout.",
                target="iron-gear-wheel",
                comparator="gte",
                threshold=10,
                window_seconds=60,
            )
        ],
    )
    snapshot = build_state_quality_snapshot(
        task,
        frame(),
        frame(tick=3600),
        state_hash="holdout-state",
        throughput_measurements={"gear-rate": [10.0]},
        horizon_ticks=3600,
    )

    assert snapshot.sustained_capability == 1.0
    assert snapshot.objective_progress == 1.0
    assert snapshot.horizon_ticks == 3600


def test_required_action_constraint_uses_audited_tool_events():
    task = FactorioTaskSpec(task_id="tools", goal="Use a helper.")
    constraint = ConstraintSpec(
        constraint_id="required",
        kind="required_action",
        description="Use connect_entities.",
        limit="connect_entities",
    )
    event = ActionEvent(
        sequence=1,
        code_sha256="a" * 64,
        started_at=datetime.now(timezone.utc),
        duration_seconds=0.1,
        executed_tools=["get_entities", "connect_entities"],
    )

    result = evaluate_constraint(task, constraint, frame(), frame(), [event])

    assert result.supported
    assert result.satisfied
    assert result.evidence["observed_calls"] == {"connect_entities": 1}


def test_retry_event_is_exempt_from_intervention_constraint_but_still_audited():
    task = FactorioTaskSpec(task_id="retry", goal="Recover from an error.")
    constraint = ConstraintSpec(
        constraint_id="budget",
        kind="max_interventions",
        description="Use one scored intervention.",
        limit=1,
    )
    retry = ActionEvent(
        sequence=1,
        code_sha256="a" * 64,
        started_at=datetime.now(timezone.utc),
        duration_seconds=0.1,
        error=True,
        evaluation_retry=True,
    )
    success = retry.model_copy(
        update={"sequence": 2, "error": False, "evaluation_retry": False}
    )

    result = evaluate_constraint(task, constraint, frame(), frame(), [retry, success])

    assert result.satisfied
    assert result.value == 1
    assert result.evidence == {
        "total_interventions": 2,
        "evaluation_retries": 1,
    }


def test_pollution_constraint_uses_engine_emissions():
    task = FactorioTaskSpec(
        task_id="pollution",
        goal="Stay below a pollution limit.",
        task_family="robustness",
    )
    constraint = ConstraintSpec(
        constraint_id="pollution",
        kind="max_pollution",
        description="Limit pollution.",
        limit=100,
    )
    result = evaluate_constraint(
        task,
        constraint,
        frame(pollution_emitted=10),
        frame(pollution_emitted=125, pollution_total=50),
        [],
    )

    assert result.supported is True
    assert result.satisfied is False
    assert result.value == 115
    assert result.evidence["pollution_total"] == 50


def test_resource_and_forbidden_action_constraints_are_auditable():
    task = FactorioTaskSpec(
        task_id="accounting",
        goal="Stay within resource and action limits.",
        task_family="robustness",
    )
    resource = ConstraintSpec(
        constraint_id="ore",
        kind="max_resource_cost",
        description="Extract at most ten raw resources.",
        limit=10,
    )
    forbidden = ConstraintSpec(
        constraint_id="manual",
        kind="forbidden_action",
        description="Do not craft manually.",
        limit="craft_item",
    )
    event = ActionEvent(
        sequence=1,
        code_sha256="a" * 64,
        started_at=datetime.now(timezone.utc),
        duration_seconds=0.1,
        executed_tools=["inspect_inventory", "craft_item"],
        policy_violations=["craft_item"],
    )

    resource_result = evaluate_constraint(
        task,
        resource,
        frame(produced={"iron-ore": 2}),
        frame(produced={"iron-ore": 14}),
        [event],
    )
    action_result = evaluate_constraint(task, forbidden, frame(), frame(), [event])

    assert resource_result.supported is True
    assert resource_result.satisfied is False
    assert resource_result.value == 12
    assert action_result.supported is True
    assert action_result.satisfied is False
    assert action_result.evidence["observed_violations"] == ["craft_item"]


def test_survival_fails_on_engine_recorded_train_death():
    objective = ObjectiveSpec(
        objective_id="survive",
        kind="survival",
        description="Remain alive for sixty ticks.",
        comparator="gte",
        threshold=60,
    )
    initial = frame(tick=0)
    final = frame(
        tick=60,
        character_alive=False,
        death_count=1,
        deaths=[
            {
                "tick": 42,
                "player_index": 1,
                "cause": {"name": "locomotive", "type": "locomotive"},
                "train": {"id": 7, "speed": 0.8},
            }
        ],
    )

    result = evaluate_objective(objective, initial, final)

    assert result.satisfied is False
    assert result.normalized_score == 0
    assert result.evidence["death_count"] == 1


class FakeNamespace:
    def __init__(self, instance):
        self.instance = instance

    def _get_production_stats(self):
        produced = 20 if self.instance.tick >= 60 else 0
        return {
            "input": {},
            "output": {"iron-plate": produced},
            "crafted": [],
            "harvested": {},
        }

    def score(self):
        return (20, 20) if self.instance.tick >= 60 else (0, 0)

    def _save_research_state(self):
        researched = self.instance.tick >= 60
        return ResearchState(
            technologies={"automation": technology("automation", researched)},
            current_research=None,
            research_progress=0.0,
            research_queue=[],
            progress={},
        )

    def get_entities(self):
        if self.instance.tick < 60:
            return []
        return [
            SimpleNamespace(
                name="assembling-machine-1",
                status=EntityStatus.NO_INGREDIENTS,
            ),
            SimpleNamespace(name="electric-mining-drill", status=EntityStatus.NO_POWER),
        ]

    def inspect_inventory(self):
        return {"iron-plate": 20 if self.instance.tick >= 60 else 0}

    def get_prototype_recipe(self, target):
        return {"name": target, "ingredients": [{"name": "iron-ore", "count": 1}]}

    def sleep(self, seconds):
        self.instance.tick += seconds * 60


class FakeInstance:
    def __init__(self):
        self.tick = 0
        self._verified_rocket_launches = 0
        self.first_namespace = FakeNamespace(self)

    def get_elapsed_ticks(self):
        return self.tick


def test_short_transition_holdout_projects_to_declared_objective_window():
    instance = FakeInstance()
    task = FactorioTaskSpec(
        task_id="projected-throughput",
        goal="Measure a stable per-minute rate.",
        objectives=[
            ObjectiveSpec(
                objective_id="iron-throughput",
                kind="throughput",
                description="Produce iron automatically.",
                target="iron-plate",
                comparator="gte",
                threshold=120,
                window_seconds=60,
            )
        ],
    )

    final, measurements, elapsed_ticks = measure_autonomous_holdout(
        instance,
        task,
        seconds=5,
    )

    assert final.tick == 300
    assert elapsed_ticks == 300
    assert measurements == {"iron-throughput": [240.0]}


def test_native_verifier_combines_objectives_constraints_and_teacher_packet():
    instance = FakeInstance()
    initial = capture_telemetry(instance, ["iron-plate", "automation"])
    task = FactorioTaskSpec(
        task_id="early-progression",
        backend_task_id="open_play",
        goal="Research automation and sustain iron production.",
        task_family="progression",
        objectives=[
            ObjectiveSpec(
                objective_id="iron-throughput",
                kind="throughput",
                description="Produce iron automatically.",
                target="iron-plate",
                comparator="gte",
                threshold=16,
                window_seconds=1,
            ),
            ObjectiveSpec(
                objective_id="research-automation",
                kind="research",
                description="Research automation.",
                target="automation",
                comparator="eq",
                threshold=1,
            ),
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="ticks",
                kind="max_ticks",
                description="Finish within the tick budget.",
                limit=120,
            )
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="weighted_sum",
        ),
        curriculum=CurriculumSpec(
            stage="early-game",
            suggested_strategies=["actor_critic"],
            episode_mode="persistent",
        ),
    )

    result = verify_native(instance, task, [], initial)

    assert result.success
    assert result.scalar_reward == 1.0
    assert result.rewards.throughput == 20
    assert result.rewards.automation == 20
    assert result.rewards.milestone == 1
    assert result.diagnostics.objective_evaluations[0].satisfied
    assert result.diagnostics.research["relevant"]["automation"]["researched"]
    assert result.diagnostics.target_recipes["iron-plate"]["name"] == "iron-plate"
    assert {signal.category for signal in result.diagnostics.bottlenecks} == {
        "input_starvation",
        "power_shortage",
    }
    assert result.events[-1].kind == "verification_completed"


def test_automation_reward_does_not_penalize_consuming_provisioned_inputs():
    instance = FakeInstance()
    initial = capture_telemetry(instance, ["automation"])
    instance.tick = 60
    instance.first_namespace.score = lambda: (-479, -479)
    task = FactorioTaskSpec(
        task_id="provisioned-research",
        backend_task_id="open_play",
        goal="Research Automation from provisioned science packs.",
        task_family="milestone",
        objectives=[
            ObjectiveSpec(
                objective_id="research-automation",
                kind="research",
                description="Research Automation.",
                target="automation",
                comparator="eq",
                threshold=1,
            )
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="binary",
        ),
    )

    result = verify_native(instance, task, [], initial)

    assert result.success
    assert result.rewards.task == 1
    assert result.rewards.automation == 0
    assert result.metrics["automated_production_score_delta"] == -479
    assert result.metrics["automation_reward"] == 0
    assert (
        result.metrics["automation_reward_basis"]
        == "nonnegative_legacy_net_value_delta"
    )


def test_hard_constraint_failure_gates_native_scalar_reward():
    instance = FakeInstance()
    initial = capture_telemetry(instance)
    task = FactorioTaskSpec(
        task_id="constraint-gate",
        goal="Operate, but remain inside an impossible tick budget.",
        task_family="milestone",
        objectives=[
            ObjectiveSpec(
                objective_id="operate",
                kind="survival",
                description="Operate for 60 ticks.",
                comparator="gte",
                threshold=60,
            )
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="ticks",
                kind="max_ticks",
                description="Stay below one tick.",
                limit=1,
            )
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="weighted_sum",
        ),
    )
    instance.tick = 60

    result = verify_native(instance, task, [], initial)

    assert result.diagnostics.objective_evaluations[0].satisfied
    assert result.diagnostics.constraint_evaluations[0].satisfied is False
    assert result.success is False
    assert result.scalar_reward == 0.0
