# Task modules for VQA system

from .blueprints.basic.task import (
    entity_name_task,
    position_task,
    counting_task
)

from .blueprints.spatial_reasoning.task import (
    generate_spatial_reasoning_with_code,
    generate_spatial_context_with_code
)


from .blueprints.denoising_qa.task import (
    denoising_blueprint_task,
    denoising_validation_task
)

from .blueprints.action_prediction.task import (
    action_sequence_generation_task,
    next_action_prediction_task,
    construction_order_task,
    comprehensive_action_task
)

from .blueprints.contrastive_alignment.task import (
    contrastive_blueprint_labelling_task,
)

__all__ = [
    # Basic tasks
    "entity_name_task",
    "position_task",
    "counting_task",
    
    # Spatial reasoning tasks
    "generate_spatial_reasoning_with_code",
    "generate_spatial_context_with_code",
    
    # Denoising tasks
    "denoising_blueprint_task",
    "denoising_validation_task",
    
    # Action prediction tasks
    "action_sequence_generation_task",
    "next_action_prediction_task", 
    "construction_order_task",
    "comprehensive_action_task",

    # Contrastive alignment tasks
    "contrastive_blueprint_labelling_task",

]