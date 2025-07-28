# Task modules for VQA system

from .basic.task import (
    basic_entity_name_task,
    basic_position_task, 
    basic_counting_task,
    comprehensive_basic_task
)

from data.vqa.tasks.spatial_reasoning.task import (
    generate_spatial_reasoning_with_code,
    generate_spatial_context_with_code
)


from .denoising.task import (
    denoising_blueprint_task,
    denoising_validation_task
)

from .action_prediction.task import (
    action_sequence_generation_task,
    next_action_prediction_task,
    construction_order_task,
    comprehensive_action_task
)

from .productivity_planning.task import (
    throughput_prediction_task,
    bottleneck_analysis_task,
    optimization_planning_task,
    comprehensive_productivity_task
)

from .contrastive_alignment.task import (
    contrastive_blueprint_labelling_task,

)

__all__ = [
    # Basic tasks
    "basic_entity_name_task",
    "basic_position_task", 
    "basic_counting_task",
    "comprehensive_basic_task",
    
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
    
    # Productivity planning tasks
    "throughput_prediction_task",
    "bottleneck_analysis_task",
    "optimization_planning_task",
    "comprehensive_productivity_task",
    
    # Contrastive alignment tasks
    "contrastive_blueprint_labelling_task",

]