# task.py - Updated terrain task with nearest_buildable questions
from concurrent import futures
from typing import List, Tuple

from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.common_solvers import attach_bounding_box
from data.vqa.tasks.terrain.character_localisation.solver import (
    character_localisation_question,
)
from data.vqa.tasks.terrain.dataset import raw_position_dataset
from data.vqa.tasks.terrain.nearest.solver import nearest_questions
from data.vqa.tasks.terrain.nearest_buildable.solver import (
    nearest_buildable_questions,
    nearest_buildable_with_resources_questions,
)
from data.vqa.tasks.terrain.solver import render_terrain
from data.vqa.tasks.terrain.tile_count.solver import tile_count_questions
from fle.commons.cluster_ips import get_local_container_ips
from fle.env import FactorioInstance


@task
def terrain_task(
    instance,
    include_nearest: bool = True,
    include_buildable: bool = True,
    include_resource_buildable: bool = True,
    include_tile_count: bool = False,
    include_character_loc: bool = True,
    multiple_choice: bool = True,
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
        render_terrain(instance),
    ]

    # Add selected question types
    if include_nearest:
        solvers.append(nearest_questions(multiple_choice=multiple_choice))

    if include_buildable:
        solvers.append(
            nearest_buildable_questions(
                questions_per_position=5, multiple_choice=multiple_choice
            )
        )

    if include_resource_buildable:
        solvers.append(
            nearest_buildable_with_resources_questions(
                questions_per_position=3, multiple_choice=multiple_choice
            )
        )

    if include_tile_count:
        solvers.append(tile_count_questions(multiple_choice=multiple_choice))

    if include_character_loc:
        solvers.append(character_localisation_question(multiple_choice=multiple_choice))

    return Task(
        name="terrain_task" + ("_mc" if multiple_choice else ""),
        dataset=raw_position_dataset(pattern="concentric"),
        solver=solvers,
        scorer=None,
    )


@task
def nearest_buildable_task(instance, multiple_choice: bool = True) -> Task:
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
            render_terrain(instance),
            nearest_buildable_questions(
                questions_per_position=8, multiple_choice=multiple_choice
            ),
            nearest_buildable_with_resources_questions(
                questions_per_position=4, multiple_choice=multiple_choice
            ),
        ],
        scorer=None,
    )


def create_factorio_instances() -> List[FactorioInstance]:
    def init_instance(params: Tuple[str, int, int]) -> FactorioInstance:
        ip, udp_port, tcp_port = params
        return FactorioInstance(
            address=ip,
            tcp_port=tcp_port,
            bounding_box=200,
            fast=True,
            cache_scripts=False,
            inventory={},
            all_technologies_researched=False,
        )

    ips, udp_ports, tcp_ports = get_local_container_ips()
    with futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))


if __name__ == "__main__":
    from inspect_ai import eval
    from data.vqa.hook import VQAPairsHook

    model = ["anthropic/claude-sonnet-4-20250514"]

    instance = create_factorio_instances()[-1]
    # instance.reset()
    # Example 1: Run comprehensive terrain task
    results = eval(
        tasks=[
            terrain_task(
                instance,
                include_nearest=True,
                include_buildable=True,
                include_resource_buildable=True,
                multiple_choice=True,
            ),
            terrain_task(
                instance,
                include_nearest=True,
                include_buildable=True,
                include_resource_buildable=True,
                multiple_choice=False,
            ),
        ],
        model=model,
        limit=10,
        log_dir="../../logs/",
        fail_on_error=0.5,
        hooks=[VQAPairsHook()],
    )

    # Example 2: Run focused nearest buildable task
    # results = eval(
    #     tasks=nearest_buildable_task(multiple_choice=False),
    #     model=model,
    #     limit=5,
    #     log_dir="../../logs/",
    #     hooks=[VQAPairsHook()]
    # )
