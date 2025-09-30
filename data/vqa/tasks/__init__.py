# Task modules for VQA system
from concurrent import futures
from typing import List, Tuple

from data.vqa.tasks.blueprints.denoising.task import simple_denoising_blueprint_task
from data.vqa.tasks.factory import factory_task
from data.vqa.tasks.terrain.task import terrain_task
from data.vqa.tasks.blueprints.basic.task import (
    entity_name_task,
    position_task,
    counting_task,
    entity_name_mc_task,
    position_mc_task,
    counting_mc_task,
    direction_mc_task,
    direction_task,
)

from data.vqa.tasks.blueprints.spatial_reasoning.task import (
    generate_spatial_reasoning_with_code,
    generate_spatial_context_with_code,
    spatial_context_sandbox_task,
)


from data.vqa.tasks.blueprints.denoising_qa.task import (
    denoising_blueprint_task,
    denoising_validation_task,
)

from data.vqa.tasks.blueprints.action_prediction.task import (
    action_sequence_generation_task,
    next_action_prediction_task,
    construction_order_task,
    comprehensive_action_task,
)

from data.vqa.tasks.blueprints.contrastive_alignment.task import (
    contrastive_blueprint_labelling_task,
    contrastive_alignment_task,
)

__all__ = [
    # Basic tasks
    "entity_name_task",
    "position_task",
    "counting_task",
    "entity_name_mc_task",
    "position_mc_task",
    "counting_mc_task",
    "direction_mc_task",
    "direction_task",
    # Spatial reasoning tasks
    "generate_spatial_reasoning_with_code",
    "generate_spatial_context_with_code",
    "spatial_context_sandbox_task",
    # Denoising tasks
    "denoising_blueprint_task",
    "denoising_validation_task",
    "simple_denoising_blueprint_task",
    # Action prediction tasks
    "action_sequence_generation_task",
    "next_action_prediction_task",
    "construction_order_task",
    "comprehensive_action_task",
    # Contrastive alignment tasks
    "contrastive_blueprint_labelling_task",
    "contrastive_alignment_task",
    # Factory and terrain tasks
    "factory_task",
    "terrain_task",
]

from fle.commons.cluster_ips import get_local_container_ips

from fle.env import FactorioInstance


def create_factorio_instances() -> List[FactorioInstance]:
    """Create Factorio instances in parallel from local servers"""

    def init_instance(params: Tuple[str, int, int]) -> FactorioInstance:
        ip, udp_port, tcp_port = params
        instance = FactorioInstance(
            address=ip,
            tcp_port=tcp_port,
            bounding_box=200,
            fast=True,
            cache_scripts=False,
            inventory={},
        )
        instance.speed(100)
        return instance

    ips, udp_ports, tcp_ports = get_local_container_ips()
    with futures.ThreadPoolExecutor() as executor:
        return list(executor.map(init_instance, zip(ips, udp_ports, tcp_ports)))


if __name__ == "__main__":
    from inspect_ai import eval
    from data.vqa.hook import VQAPairsHook

    model = ["anthropic/claude-sonnet-4-20250514"]

    instances = create_factorio_instances()

    if len(instances) < 4:
        raise ValueError("At least 4 factorio instances are required")

    questions_per_blueprint = 20
    # Example 3: Run comprehensive factory task
    results = eval(
        tasks=[
            factory_task(instances[0], multiple_choice=True),
            factory_task(instances[1], multiple_choice=False),
            terrain_task(instances[2], multiple_choice=True),
            terrain_task(instances[3], multiple_choice=False),
            denoising_blueprint_task(qa_pairs_per_blueprint=questions_per_blueprint),
            simple_denoising_blueprint_task(
                qa_pairs_per_blueprint=questions_per_blueprint
            ),
            contrastive_alignment_task(limit=6, subset="title"),
            contrastive_alignment_task(limit=6, subset="purpose"),
            entity_name_mc_task(questions_per_blueprint=questions_per_blueprint),
            position_mc_task(questions_per_blueprint=questions_per_blueprint),
            counting_mc_task(questions_per_blueprint=questions_per_blueprint),
            entity_name_task(questions_per_blueprint=questions_per_blueprint),
            position_task(questions_per_blueprint=questions_per_blueprint),
            counting_task(questions_per_blueprint=questions_per_blueprint),
            direction_task(questions_per_blueprint=questions_per_blueprint),
        ],
        model=model,
        limit=25,
        fail_on_error=0.5,
        log_dir="../../logs",
        hooks=[VQAPairsHook()],
    )
    # #spatial_context_sandbox_task(qa_pairs_per_blueprint=20),
    # #direction_mc_task(questions_per_blueprint=10),
