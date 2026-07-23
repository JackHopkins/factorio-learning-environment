import pytest
from pydantic import ValidationError

from fle.envd.models import (
    ConstraintSpec,
    CurriculumSpec,
    FactorioTaskSpec,
    ObjectiveSpec,
    VerifierEvent,
    VerificationSnapshot,
    RewardVector,
)
from fle.envd.task_builder import build_task_spec, render_task_prompt
from fle.envd.curriculum import (
    early_automation_progression_task,
    automation_research_milestone_task,
    rocket_launch_milestone_task,
)

pytestmark = pytest.mark.no_factorio


def test_registered_throughput_task_becomes_general_objective_contract():
    spec = build_task_spec(
        "iron_plate_throughput",
        seed=7,
        max_interventions=12,
        holdout_seconds=30,
    )

    assert spec.task_family == "throughput"
    assert spec.seed == 7
    assert spec.curriculum.suggested_strategies == ["grpo", "evaluation"]
    assert spec.objectives == [
        ObjectiveSpec(
            objective_id="iron_plate_throughput:throughput",
            kind="throughput",
            description=spec.goal,
            target="iron-plate",
            comparator="gte",
            threshold=16,
            window_seconds=30,
            parameters={"automatic": True},
        )
    ]
    assert {constraint.kind for constraint in spec.constraints} == {
        "max_interventions",
        "required_action_profile",
    }
    assert len(spec.knowledge_sources) == 3
    assert spec.fingerprint


def test_progression_task_contract_is_not_coupled_to_throughput():
    spec = FactorioTaskSpec(
        task_id="bootstrap_automation",
        goal="Research automation and establish automatic science production.",
        task_family="progression",
        objectives=[
            ObjectiveSpec(
                objective_id="research-automation",
                kind="research",
                description="Research automation.",
                target="automation",
                comparator="eq",
                threshold=1,
            ),
            ObjectiveSpec(
                objective_id="automate-red-science",
                kind="throughput",
                description="Sustain automation science production.",
                target="automation-science-pack",
                comparator="gte",
                threshold=5,
                window_seconds=60,
            ),
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="manual-craft-budget",
                kind="max_manual_crafts",
                description="Use no more than the bootstrap manual-craft budget.",
                limit=20,
            )
        ],
        curriculum=CurriculumSpec(
            stage="early-game",
            suggested_strategies=["actor_critic", "offline_replay"],
            episode_mode="persistent",
        ),
    )

    assert spec.task_family == "progression"
    assert [objective.kind for objective in spec.objectives] == [
        "research",
        "throughput",
    ]
    assert "Research automation" in render_task_prompt(spec)


def test_registered_open_play_task_gets_persistent_strategy_metadata():
    spec = build_task_spec(
        "iron_gear_wheel_throughput_unbounded_steps_show_steps_true"
    )

    assert spec.task_family == "throughput"
    assert spec.objectives[0].comparator == "maximize"
    assert spec.curriculum.episode_mode == "persistent"
    assert "actor_critic" in spec.curriculum.suggested_strategies


def test_objective_validation_rejects_unverifiable_threshold_contract():
    with pytest.raises(ValidationError, match="requires a threshold"):
        ObjectiveSpec(
            objective_id="bad",
            kind="research",
            description="Ambiguous research objective.",
            target="automation",
        )


def test_task_rejects_duplicate_objective_ids():
    objective = ObjectiveSpec(
        objective_id="same",
        kind="rocket_launch",
        description="Launch a rocket.",
        comparator="eq",
        threshold=1,
    )
    with pytest.raises(ValidationError, match="objective ids must be unique"):
        FactorioTaskSpec(
            task_id="duplicate",
            goal="test",
            task_family="milestone",
            objectives=[objective, objective],
        )


def test_protocol_02_verifier_events_round_trip_with_named_channels():
    event = VerifierEvent(
        event_id="milestone:automation",
        kind="technology_researched",
        tick=1200,
        source="engine",
        objective_id="research-automation",
        payload={"technology": "automation"},
        evidence={"research_complete": True},
        reward_channels={"milestone": 1.0},
    )
    snapshot = VerificationSnapshot(
        lease_id="lease",
        task_id="bootstrap",
        task_fingerprint="f" * 64,
        success=True,
        scalar_reward=1.0,
        rewards=RewardVector(task=1.0, milestone=1.0),
        terminal_state_hash="s" * 64,
        events=[event],
    )

    restored = VerificationSnapshot.model_validate_json(snapshot.model_dump_json())
    assert restored.protocol_version == "0.2.1"
    assert restored.events[0].kind == "technology_researched"
    assert restored.events[0].reward_channels == {"milestone": 1.0}


def test_builtin_early_progression_task_uses_native_verifier_and_real_bootstrap():
    spec = early_automation_progression_task()

    assert spec.backend_task_id == "open_play"
    assert spec.task_family == "progression"
    assert spec.verifier.implementation == "objective_engine_v1"
    assert spec.verifier.holdout_windows == 3
    assert spec.provisioning.starting_inventory == {
        "burner-mining-drill": 1,
        "stone-furnace": 1,
    }
    assert spec.provisioning.all_technologies_researched is False
    assert {objective.kind for objective in spec.objectives} == {
        "research",
        "entity_exists",
        "throughput",
    }
    assert "actor_critic" in spec.curriculum.suggested_strategies


def test_research_and_rocket_milestones_use_real_engine_predicates():
    research = automation_research_milestone_task()
    rocket = rocket_launch_milestone_task()

    assert research.objectives[0].kind == "research"
    assert research.provisioning.all_technologies_researched is False
    assert research.provisioning.starting_inventory["lab"] == 1
    assert research.provisioning.researched_technologies == [
        "steam-power",
        "automation-science-pack",
    ]
    assert rocket.objectives[0].kind == "rocket_launch"
    assert rocket.objectives[0].comparator == "increases"
    assert rocket.provisioning.all_technologies_researched is True
    assert rocket.provisioning.starting_inventory["rocket-silo"] == 1
