"""Build versioned envd task specifications from FLE's legacy task registry.

The registry remains the authority for provisioning existing FLE tasks. This
module translates those definitions into a trainer-neutral objective contract,
so Prime-RL is no longer coupled to the throughput task class.
"""

from __future__ import annotations

from typing import Any

from fle.envd.action_reference import ACTION_PROFILE_REFERENCE
from fle.envd.models import (
    ConstraintSpec,
    CurriculumSpec,
    FactorioTaskSpec,
    KnowledgeSourceSpec,
    ObjectiveSpec,
    ThroughputAuditSpec,
    VerifierSpec,
)
from fle.eval.tasks.task_definitions.task_registry import get_task_config

DEFAULT_KNOWLEDGE_SOURCES = [
    KnowledgeSourceSpec(
        source_id="factorio-wiki-quick-start",
        title="Factorio Wiki: Quick start guide",
        url="https://wiki.factorio.com/Tutorial:Quick_start_guide",
        topics=[
            "resource_extraction",
            "smelting",
            "electricity",
            "automation",
            "research",
        ],
    ),
    KnowledgeSourceSpec(
        source_id="voidgrazer-high-level-strategy",
        title="High-Level Strategy for New Players",
        url="https://steamcommunity.com/sharedfiles/filedetails/?id=2275950965",
        topics=[
            "progression_phases",
            "expandability",
            "automation",
            "oil_processing",
            "logistics",
        ],
    ),
    KnowledgeSourceSpec(
        source_id="earlyguides-walkthrough",
        title="Factorio Walkthrough: Start to Endgame",
        url="https://earlyguides.com/factorio/walkthrough",
        topics=[
            "progression_phases",
            "oil_processing",
            "trains",
            "defense",
            "endgame",
        ],
        access="dataset_builder",
    ),
]


def _raw_config(task_id: str) -> dict[str, Any]:
    config = get_task_config(task_id)
    if hasattr(config, "to_dict"):
        return config.to_dict()
    return config.model_dump()


def _objective_from_config(task_id: str, config: dict[str, Any]) -> ObjectiveSpec:
    task_type = str(config.get("task_type", "default"))
    goal = str(config.get("goal_description") or task_id)
    target = config.get("throughput_entity")
    if task_type == "throughput":
        return ObjectiveSpec(
            objective_id=f"{task_id}:throughput",
            kind="throughput",
            description=goal,
            target=str(target),
            comparator="gte",
            threshold=float(config["quota"]),
            window_seconds=int(config.get("holdout_wait_period", 60)),
            parameters={"automatic": True},
        )
    if task_type == "unbounded_throughput":
        return ObjectiveSpec(
            objective_id=f"{task_id}:maximize-throughput",
            kind="throughput",
            description=goal,
            target=str(target),
            comparator="maximize",
            window_seconds=int(config.get("holdout_wait_period", 60)),
            parameters={"automatic": True},
        )
    return ObjectiveSpec(
        objective_id=f"{task_id}:custom",
        kind="custom",
        description=goal,
        comparator="maximize",
        parameters={"legacy_task_type": task_type},
    )


def build_task_spec(
    task_id: str,
    *,
    seed: int = 0,
    scenario: str = "default_lab_scenario",
    factorio_version: str = "2.0.73",
    checkpoint_id: str = "scenario:default_lab_scenario",
    action_profile: str = "fle-program-v1",
    max_interventions: int = 8,
    holdout_seconds: int | None = None,
) -> FactorioTaskSpec:
    """Translate any registered FLE task into the generalized wire contract."""

    config = _raw_config(task_id)
    task_type = str(config.get("task_type", "default"))
    goal = str(config.get("goal_description") or task_id)
    objective = _objective_from_config(task_id, config)
    if holdout_seconds is None:
        holdout_seconds = int(config.get("holdout_wait_period", 60))
    elif objective.kind == "throughput":
        objective = objective.model_copy(update={"window_seconds": holdout_seconds})
    if objective.kind == "throughput":
        if objective.comparator == "maximize":
            goal = (
                f"Maximize automatic production of {objective.target} over each "
                f"{holdout_seconds}-second in-game verification window."
            )
        else:
            goal = (
                f"Automatically produce at least {objective.threshold:g} "
                f"{objective.target} per {holdout_seconds} in-game seconds."
            )
        objective = objective.model_copy(update={"description": goal})

    family = "throughput" if "throughput" in task_type else "open_play"
    strategies = (
        ["grpo", "evaluation"]
        if task_type == "throughput"
        else ["actor_critic", "offline_replay", "evaluation"]
    )
    return FactorioTaskSpec(
        task_id=task_id,
        goal=goal,
        task_family=family,
        objectives=[objective],
        constraints=[
            ConstraintSpec(
                constraint_id="intervention-budget",
                kind="max_interventions",
                description="Do not exceed the rollout intervention budget.",
                limit=max_interventions,
            ),
            ConstraintSpec(
                constraint_id="action-profile",
                kind="required_action_profile",
                description="Use only the configured auditable action profile.",
                limit=action_profile,
            ),
        ],
        verifier=VerifierSpec(
            implementation=(
                "objective_engine_v1"
                if task_type == "throughput"
                else "legacy_fle_task"
            ),
            mode="all_required",
            scalarization="backend_override",
            holdout_windows=1,
        ),
        throughput_audit=(
            ThroughputAuditSpec(require_depot_service=False)
            if task_type == "throughput"
            else None
        ),
        curriculum=CurriculumSpec(
            stage="lab" if task_type == "throughput" else "open-play",
            suggested_strategies=strategies,
            episode_mode="independent" if task_type == "throughput" else "persistent",
        ),
        knowledge_sources=DEFAULT_KNOWLEDGE_SOURCES,
        seed=seed,
        scenario=scenario,
        factorio_version=factorio_version,
        checkpoint_id=checkpoint_id,
        action_profile=action_profile,
        max_interventions=max_interventions,
        holdout_seconds=holdout_seconds,
    )


def render_task_prompt(task: FactorioTaskSpec) -> str:
    objective_lines = "\n".join(
        f"- {objective.description}" for objective in task.objectives
    )
    constraint_lines = "\n".join(
        f"- {constraint.description}" for constraint in task.constraints
    )
    verification = (
        "The Factorio engine and task verifier determine success. Do not claim "
        "completion without measuring the resulting factory."
    )
    return (
        f"Goal: {task.goal}\n\nObjectives:\n{objective_lines or '- Open-ended goal'}"
        f"\n\nConstraints:\n{constraint_lines or '- None'}\n\n"
        "Use factorio_observe_factory to inspect the simulation and "
        "factorio_execute_program for one short intervention at a time. "
        f"{verification}\n\nAction profile reference:\n{ACTION_PROFILE_REFERENCE}"
    )
