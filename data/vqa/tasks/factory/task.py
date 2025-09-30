# task.py - Factory-based tasks including nearest_entity

from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.common_solvers import normalize_position_format, attach_bounding_box

from data.vqa.tasks.factory.dataset import terrain_position_dataset
from data.vqa.tasks.factory.nearest_entity.solver import (
    render_factory,
    nearest_entity_questions,
)
from data.vqa.tasks.factory.entity_status.solver import entity_status_questions
from data.vqa.tasks.terrain.task import create_factorio_instances


@task
def nearest_entity_task(
    instance, questions_per_position: int = 5, multiple_choice: bool = True
) -> Task:
    """
    Task for finding and placing entities, then asking about nearest entity positions.

    Args:
        questions_per_position: Number of questions to generate per position
        multiple_choice: If True, generate multiple choice questions
    """
    instance.reset()
    return Task(
        name="nearest_entity_task" + ("_mc" if multiple_choice else ""),
        dataset=terrain_position_dataset(),
        solver=[
            system_message("""You are analyzing a Factorio factory to answer questions about 
                entity positions. Consider the placement of various entities and their 
                relative positions."""),
            attach_bounding_box(),
            render_factory(instance),
            nearest_entity_questions(
                instance,
                questions_per_position=questions_per_position,
                multiple_choice=multiple_choice,
            ),
            normalize_position_format(),
        ],
        scorer=None,
    )


@task
def entity_status_task(
    instance, questions_per_position: int = 5, multiple_choice: bool = True
) -> Task:
    """
    Task for asking about entity statuses in a factory.

    Args:
        questions_per_position: Number of questions to generate per position
        multiple_choice: If True, generate multiple choice questions
    """
    instance.reset()
    return Task(
        name="entity_status_task" + ("_mc" if multiple_choice else ""),
        dataset=terrain_position_dataset(),
        solver=[
            system_message("""You are analyzing a Factorio factory to answer questions about 
                entity statuses. Consider whether entities are working, have power, 
                have ingredients, or have other status conditions."""),
            attach_bounding_box(),
            render_factory(instance),
            nearest_entity_questions(
                instance,
                questions_per_position=3,  # Place some entities first
                multiple_choice=multiple_choice,
            ),
            entity_status_questions(
                instance,
                questions_per_position=questions_per_position,
                multiple_choice=multiple_choice,
            ),
            normalize_position_format(),
        ],
        scorer=None,
    )


@task
def factory_task(
    instance,
    include_nearest_entity: bool = True,
    include_entity_status: bool = True,
    multiple_choice: bool = True,
) -> Task:
    """
    Comprehensive factory analysis task.

    Args:
        include_nearest_entity: Include nearest entity questions
        include_entity_status: Include entity status questions
        multiple_choice: If True, generate multiple choice questions
    """

    instance.reset()
    solvers = [
        system_message("""You are analyzing a Factorio factory to answer questions about 
            entity positions, statuses, production chains, and factory layout."""),
        attach_bounding_box(),
        render_factory(instance),
    ]

    # Add selected question types
    if include_nearest_entity:
        solvers.append(
            nearest_entity_questions(
                instance, questions_per_position=5, multiple_choice=multiple_choice
            )
        )

    if include_entity_status:
        solvers.append(
            entity_status_questions(
                instance, questions_per_position=5, multiple_choice=multiple_choice
            )
        )

    solvers.append(normalize_position_format())

    return Task(
        name="factory_task" + ("_mc" if multiple_choice else ""),
        dataset=terrain_position_dataset(),
        solver=solvers,
        scorer=None,
    )


if __name__ == "__main__":
    from inspect_ai import eval
    from data.vqa.hook import VQAPairsHook

    model = ["anthropic/claude-sonnet-4-20250514"]

    # Example 1: Run nearest entity task
    # results = eval(
    #     tasks=nearest_entity_task(
    #         questions_per_position=5,
    #         multiple_choice=True
    #     ),
    #     model=model,
    #     limit=10,
    #     log_dir="../../logs",
    #     hooks=[VQAPairsHook()]
    # )

    # Example 2: Run entity status task
    # results = eval(
    #     tasks=entity_status_task(
    #         questions_per_position=5,
    #         multiple_choice=True
    #     ),
    #     model=model,
    #     limit=10,
    #     log_dir="../../logs",
    #     hooks=[VQAPairsHook()]
    # )
    instances = create_factorio_instances()

    # Example 3: Run comprehensive factory task
    results = eval(
        tasks=factory_task(
            instances[0],
            include_nearest_entity=True,
            include_entity_status=True,
            multiple_choice=True,
        ),
        model=model,
        limit=10,
        fail_on_error=0.5,
        log_dir="../../logs",
        hooks=[VQAPairsHook()],
    )
