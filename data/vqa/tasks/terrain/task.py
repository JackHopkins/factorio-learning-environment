# task.py - Updated terrain task with nearest_buildable questions

from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.common_solvers import (
    normalize_position_format,
    attach_bounding_box
)
from data.vqa.tasks.terrain.character_localisation.solver import character_localisation_question
from data.vqa.tasks.terrain.dataset import raw_position_dataset
from data.vqa.tasks.terrain.nearest.solver import nearest_questions
from data.vqa.tasks.terrain.nearest_buildable.solver import (
    nearest_buildable_questions,
    nearest_buildable_with_resources_questions
)
from data.vqa.tasks.terrain.solver import render_terrain
from data.vqa.tasks.terrain.tile_count.solver import tile_count_questions


@task
def terrain_task(
        include_nearest: bool = True,
        include_buildable: bool = True,
        include_resource_buildable: bool = True,
        include_tile_count: bool = False,
        include_character_loc: bool = True,
        multiple_choice: bool = True
) -> Task:
    """
    Terrain analysis task including nearest buildable positions.

    Args:
        include_nearest: Include nearest resource questions
        include_buildable: Include nearest buildable position questions
        include_resource_buildable: Include resource-dependent buildable questions
        include_tile_count: Include tile counting questions
        include_character_loc: Include character localization questions
        multiple_choice: If True, generate multiple choice questions
    """

    solvers = [
        system_message("""You are analyzing Factorio terrain to answer questions about 
            resources, buildable positions, and entity placement.
            Consider terrain features, obstacles, and resource availability."""),
        attach_bounding_box(),
        render_terrain(),
    ]

    # Add selected question types
    if include_nearest:
        solvers.append(nearest_questions(multiple_choice=multiple_choice))

    if include_buildable:
        solvers.append(nearest_buildable_questions(
            questions_per_position=5,
            multiple_choice=multiple_choice
        ))

    if include_resource_buildable:
        solvers.append(nearest_buildable_with_resources_questions(
            questions_per_position=3,
            multiple_choice=multiple_choice
        ))

    if include_tile_count:
        solvers.append(tile_count_questions(multiple_choice=multiple_choice))

    if include_character_loc:
        solvers.append(character_localisation_question(multiple_choice=multiple_choice))

    return Task(
        name="terrain_task",
        dataset=raw_position_dataset(pattern="concentric"),
        solver=solvers,
        scorer=None,
    )


@task
def nearest_buildable_task(multiple_choice: bool = True) -> Task:
    """
    Task focused only on nearest buildable position questions.
    """
    return Task(
        name="nearest_buildable_task",
        dataset=raw_position_dataset(pattern="concentric"),
        solver=[
            system_message("""You are analyzing Factorio terrain to find valid building positions.
                Consider space requirements, terrain obstacles, and resource coverage."""),
            attach_bounding_box(),
            render_terrain(),
            nearest_buildable_questions(
                questions_per_position=8,
                multiple_choice=multiple_choice
            ),
            nearest_buildable_with_resources_questions(
                questions_per_position=4,
                multiple_choice=multiple_choice
            )
        ],
        scorer=None,
    )


if __name__ == "__main__":
    from inspect_ai import eval
    from data.vqa.hook import VQAPairsHook

    model = ["anthropic/claude-sonnet-4-20250514"]

    # Example 1: Run comprehensive terrain task
    results = eval(
        tasks=terrain_task(
            include_nearest=True,
            include_buildable=True,
            include_resource_buildable=True,
            multiple_choice=True
        ),
        model=model,
        limit=40,
        log_dir="../../logs/",
        hooks=[VQAPairsHook()]
    )

    # Example 2: Run focused nearest buildable task
    # results = eval(
    #     tasks=nearest_buildable_task(multiple_choice=False),
    #     model=model,
    #     limit=5,
    #     log_dir="../../logs/",
    #     hooks=[VQAPairsHook()]
    # )