"""
Monte Carlo Tree Search (MCTS) Algorithm Implementations for Factorio Learning Environment

This module provides various MCTS implementations and utilities for tree-based search
algorithms in the Factorio game environment. It includes parallel execution, planning
variants, and specialized configurations.

Main Components:
- MCTS: Base Monte Carlo Tree Search implementation
- ParallelMCTS: Multi-instance parallel MCTS execution
- PlanningMCTS: MCTS with hierarchical planning capabilities
- ChunkedMCTS: MCTS with code chunking for structured programs
- ObjectiveMCTS: MCTS with explicit objective generation
- MCTSFactory: Factory for creating configured MCTS instances
"""

# Core MCTS implementations
from .mcts import (
    MCTS,
)

from .parallel_mcts import (
    ParallelMCTS,
)

from .planning_mcts import (
    PlanningMCTS,
    get_mining_setup,
)

from .chunked_mcts import (
    ChunkedMCTS,
)

from .objective_mcts import (
    ObjectiveMCTS,
)

from .parallel_planning_mcts import (
    ParallelPlanningMCTS,
    PlanningGroup,
)

# Configuration classes
from .parallel_mcts_config import (
    ParallelMCTSConfig,
)

from .parallel_supervised_config import (
    SupervisedExecutorConfig,
)

from .mcts_factory import (
    # Factory
    MCTSFactory,
    
    # Configuration classes
    BaseConfig,
    PlanningConfig,
    ChunkedConfig,
    ObjectiveConfig,
    SamplerConfig,
    
    # Enums
    MCTSType,
    SamplerType,
    ModelFamily,
    
    # Utility functions
    get_model_family,
    get_logit_bias,
)

# Planning data models
from .planning_models import (
    LanguageOutput,
    TaskOutput,
    InitialPlanOutput,
    Step,
    PlanOutput,
)

# Supporting classes
from .instance_group import (
    InstanceGroup,
)

from .grouped_logger import (
    GroupedFactorioLogger,
    InstanceGroupMetrics,
    InstanceMetrics,
)

from .supervised_task_executor_abc import (
    SupervisedTaskExecutorABC,
    PlanningGroupV2,
)

# Samplers (commonly used ones)
from .samplers.db_sampler import DBSampler
from .samplers.beam_sampler import BeamSampler
from .samplers.kld_achievement_sampler import KLDAchievementSampler

# Version info
__version__ = "1.0.0"

# Public API
__all__ = [
    # Core MCTS classes
    "MCTS",
    "ParallelMCTS", 
    "PlanningMCTS",
    "ChunkedMCTS",
    "ObjectiveMCTS",
    "ParallelPlanningMCTS",
    
    # Factory
    "MCTSFactory",
    
    # Configuration classes
    "ParallelMCTSConfig",
    "SupervisedExecutorConfig",
    "BaseConfig",
    "PlanningConfig", 
    "ChunkedConfig",
    "ObjectiveConfig",
    "SamplerConfig",
    
    # Enums
    "MCTSType",
    "SamplerType",
    "ModelFamily",
    
    # Planning models
    "LanguageOutput",
    "TaskOutput",
    "InitialPlanOutput",
    "Step",
    "PlanOutput",
    
    # Supporting classes
    "InstanceGroup",
    "PlanningGroup",
    "PlanningGroupV2",
    "GroupedFactorioLogger",
    "InstanceGroupMetrics", 
    "InstanceMetrics",
    "SupervisedTaskExecutorABC",
    
    # Samplers
    "DBSampler",
    "BeamSampler",
    "KLDAchievementSampler",
    
    # Utility functions
    "get_model_family",
    "get_logit_bias",
    "get_mining_setup",
]
