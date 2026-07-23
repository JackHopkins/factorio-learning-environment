"""Built-in task specifications for the first persistent Factorio curriculum."""

from collections.abc import Callable

from fle.envd.models import (
    ConstraintSpec,
    CurriculumSpec,
    FactorioTaskSpec,
    ObjectiveSpec,
    ProvisioningSpec,
    VerifierSpec,
)
from fle.envd.task_builder import DEFAULT_KNOWLEDGE_SOURCES


def early_automation_progression_task() -> FactorioTaskSpec:
    """Bootstrap from freeplay-like equipment into automated red science."""

    return FactorioTaskSpec(
        task_id="progression_early_automation_v1",
        backend_task_id="open_play",
        goal=(
            "Bootstrap basic industry, research automation, and sustain automatic "
            "automation-science-pack production."
        ),
        task_family="progression",
        objectives=[
            ObjectiveSpec(
                objective_id="research-automation",
                kind="research",
                description="Research the automation technology.",
                target="automation",
                comparator="eq",
                threshold=1,
                weight=1.0,
            ),
            ObjectiveSpec(
                objective_id="build-assembler",
                kind="entity_exists",
                description="Build at least one assembling machine 1.",
                target="assembling-machine-1",
                comparator="gte",
                threshold=1,
                weight=0.5,
            ),
            ObjectiveSpec(
                objective_id="sustain-red-science",
                kind="throughput",
                description=(
                    "Automatically produce at least five automation science packs "
                    "in each 60-second verification window."
                ),
                target="automation-science-pack",
                comparator="gte",
                threshold=5,
                window_seconds=60,
                weight=1.5,
                parameters={"automatic": True},
            ),
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Use no more than 64 intervention programs.",
                limit=64,
            ),
            ConstraintSpec(
                constraint_id="manual-craft-budget",
                kind="max_manual_crafts",
                description="Use no more than 100 manual crafting operations.",
                limit=100,
            ),
            ConstraintSpec(
                constraint_id="action-profile",
                kind="required_action_profile",
                description="Use the auditable FLE program action profile.",
                limit="fle-program-v1",
            ),
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            mode="all_required",
            scalarization="weighted_sum",
            holdout_windows=3,
        ),
        curriculum=CurriculumSpec(
            stage="early-game",
            suggested_strategies=[
                "opd",
                "opsd",
                "actor_critic",
                "offline_replay",
            ],
            episode_mode="persistent",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        provisioning=ProvisioningSpec(
            starting_inventory={"burner-mining-drill": 1, "stone-furnace": 1},
            all_technologies_researched=False,
        ),
        max_interventions=64,
        holdout_seconds=60,
    )


def automation_research_milestone_task() -> FactorioTaskSpec:
    """Research Automation from a compact, physically usable lab bootstrap."""

    return FactorioTaskSpec(
        task_id="milestone_research_automation_v1",
        backend_task_id="open_play",
        goal="Power a laboratory and complete the Automation technology.",
        task_family="milestone",
        objectives=[
            ObjectiveSpec(
                objective_id="research-automation",
                kind="research",
                description="Complete the Automation technology.",
                target="automation",
                comparator="eq",
                threshold=1,
            )
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Use no more than 16 intervention programs.",
                limit=16,
            ),
            ConstraintSpec(
                constraint_id="action-profile",
                kind="required_action_profile",
                description="Use the auditable FLE program action profile.",
                limit="fle-program-v1",
            ),
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="binary",
        ),
        curriculum=CurriculumSpec(
            stage="early-game",
            suggested_strategies=["sft", "opd", "opsd", "grpo", "evaluation"],
            episode_mode="independent",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        provisioning=ProvisioningSpec(
            starting_inventory={
                "lab": 1,
                "automation-science-pack": 20,
                "boiler": 1,
                "offshore-pump": 1,
                "steam-engine": 1,
                "pipe": 20,
                "small-electric-pole": 20,
                "coal": 100,
            },
            all_technologies_researched=False,
            # Factorio 2.0 makes these zero-cost trigger technologies rather
            # than lab research. Automation cannot start unless both are
            # already unlocked in this compact post-trigger bootstrap state.
            researched_technologies=[
                "steam-power",
                "automation-science-pack",
            ],
        ),
        max_interventions=16,
        holdout_seconds=0,
    )


def circuit_no_manual_crafting_task() -> FactorioTaskSpec:
    """Build real circuit automation without using hand crafting."""

    return FactorioTaskSpec(
        task_id="robustness_circuit_no_manual_v1",
        backend_task_id="electronic_circuit_throughput",
        goal=(
            "Sustain electronic-circuit production without using manual crafting."
        ),
        task_family="robustness",
        objectives=[
            ObjectiveSpec(
                objective_id="circuit-throughput",
                kind="throughput",
                description=(
                    "Automatically produce at least 16 electronic circuits in "
                    "each 60-second verification window."
                ),
                target="electronic-circuit",
                comparator="gte",
                threshold=16,
                window_seconds=60,
                parameters={"automatic": True},
            )
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="no-manual-crafts",
                kind="max_manual_crafts",
                description="Do not manually craft any item.",
                limit=0,
            ),
            ConstraintSpec(
                constraint_id="forbid-craft-tool",
                kind="forbidden_action",
                description="Do not call the manual craft tool.",
                limit="craft_item",
            ),
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Use no more than 24 intervention programs.",
                limit=24,
            ),
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="weighted_sum",
            holdout_windows=2,
        ),
        curriculum=CurriculumSpec(
            stage="intermediate-lab",
            suggested_strategies=["grpo", "process_grpo", "evaluation"],
            episode_mode="independent",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        max_interventions=24,
        holdout_seconds=60,
    )


def productive_survival_task() -> FactorioTaskSpec:
    """Require production while retaining character survival as a hard objective."""

    return FactorioTaskSpec(
        task_id="robustness_productive_survival_v1",
        backend_task_id="iron_plate_throughput",
        goal=(
            "Sustain automatic iron-plate production for one minute without "
            "the character dying."
        ),
        task_family="robustness",
        objectives=[
            ObjectiveSpec(
                objective_id="iron-throughput",
                kind="throughput",
                description="Produce at least 16 iron plates in 60 seconds.",
                target="iron-plate",
                comparator="gte",
                threshold=16,
                window_seconds=60,
            ),
            ObjectiveSpec(
                objective_id="survive",
                kind="survival",
                description="Remain alive for at least 3,600 simulation ticks.",
                comparator="gte",
                threshold=3600,
            ),
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Use no more than 24 intervention programs.",
                limit=24,
            )
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="weighted_sum",
            holdout_windows=1,
        ),
        curriculum=CurriculumSpec(
            stage="intermediate-lab",
            suggested_strategies=["process_grpo", "actor_critic", "evaluation"],
            episode_mode="checkpoint_chunk",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        max_interventions=24,
        holdout_seconds=60,
    )


def efficient_iron_throughput_task() -> FactorioTaskSpec:
    """Exercise throughput, extraction cost, and pollution simultaneously."""

    return FactorioTaskSpec(
        task_id="robustness_efficient_iron_v1",
        backend_task_id="iron_plate_throughput",
        goal=(
            "Sustain iron-plate production within raw-resource and pollution "
            "budgets."
        ),
        task_family="robustness",
        objectives=[
            ObjectiveSpec(
                objective_id="iron-throughput",
                kind="throughput",
                description="Produce at least 16 iron plates in 60 seconds.",
                target="iron-plate",
                comparator="gte",
                threshold=16,
                window_seconds=60,
            )
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="raw-extraction-budget",
                kind="max_resource_cost",
                description="Extract no more than 100 weighted raw resources.",
                limit=100,
                parameters={"basis": "extracted"},
            ),
            ConstraintSpec(
                constraint_id="pollution-budget",
                kind="max_pollution",
                description="Emit no more than 1,000 pollution during the task.",
                limit=1000,
                parameters={"basis": "emitted"},
            ),
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Use no more than 24 intervention programs.",
                limit=24,
            ),
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="weighted_sum",
            holdout_windows=1,
        ),
        curriculum=CurriculumSpec(
            stage="intermediate-lab",
            suggested_strategies=["process_grpo", "actor_critic", "evaluation"],
            episode_mode="checkpoint_chunk",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        max_interventions=24,
        holdout_seconds=60,
    )


def rocket_launch_milestone_task() -> FactorioTaskSpec:
    """A late-game assembly/launch milestone with real silo mechanics."""

    return FactorioTaskSpec(
        task_id="milestone_launch_rocket_v1",
        backend_task_id="open_play",
        goal="Assemble rocket parts in a powered silo and launch one rocket.",
        task_family="milestone",
        objectives=[
            ObjectiveSpec(
                objective_id="launch-rocket",
                kind="rocket_launch",
                description="Increase the engine rocket-launch counter.",
                comparator="increases",
                threshold=0,
            )
        ],
        constraints=[
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Use no more than 48 intervention programs.",
                limit=48,
            )
        ],
        verifier=VerifierSpec(
            implementation="objective_engine_v1",
            scalarization="binary",
        ),
        curriculum=CurriculumSpec(
            stage="late-game",
            suggested_strategies=[
                "opsd",
                "actor_critic",
                "offline_replay",
                "evaluation",
            ],
            prerequisite_task_ids=["progression_early_automation_v1"],
            episode_mode="checkpoint_chunk",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        provisioning=ProvisioningSpec(
            starting_inventory={
                "rocket-silo": 1,
                "low-density-structure": 1000,
                "processing-unit": 1000,
                "rocket-fuel": 1000,
                "solar-panel": 200,
                "substation": 20,
            },
            all_technologies_researched=True,
            character_inventory_slots_bonus=200,
        ),
        max_interventions=48,
        holdout_seconds=0,
    )


BUILTIN_TASKS: dict[str, Callable[[], FactorioTaskSpec]] = {
    "milestone_launch_rocket_v1": rocket_launch_milestone_task,
    "milestone_research_automation_v1": automation_research_milestone_task,
    "progression_early_automation_v1": early_automation_progression_task,
    "robustness_circuit_no_manual_v1": circuit_no_manual_crafting_task,
    "robustness_efficient_iron_v1": efficient_iron_throughput_task,
    "robustness_productive_survival_v1": productive_survival_task,
}


def get_builtin_task(task_id: str) -> FactorioTaskSpec:
    try:
        return BUILTIN_TASKS[task_id]()
    except KeyError as exc:
        raise KeyError(
            f"Unknown built-in Factorio task {task_id!r}; "
            f"available: {', '.join(sorted(BUILTIN_TASKS))}"
        ) from exc
