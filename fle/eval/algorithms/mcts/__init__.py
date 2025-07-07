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

from .chunked_mcts import ChunkedMCTS
from .grouped_logger import GroupedFactorioLogger, InstanceGroupMetrics, InstanceMetrics

# Supporting classes
from .instance_group import InstanceGroup
from .logger import FactorioLogger

# Core MCTS implementations
from .mcts import MCTS
from .mcts_factory import (  # Factory; Configuration classes; Enums; Utility functions
    BaseConfig,
    ChunkedConfig,
    MCTSFactory,
    MCTSType,
    ModelFamily,
    ObjectiveConfig,
    PlanningConfig,
    SamplerConfig,
    SamplerType,
    get_logit_bias,
    get_model_family,
)
from .objective_mcts import ObjectiveMCTS
from .parallel_mcts import ParallelMCTS

# Configuration classes
from .parallel_mcts_config import ParallelMCTSConfig
from .parallel_planning_mcts import ParallelPlanningMCTS, PlanningGroup
from .parallel_supervised_config import SupervisedExecutorConfig
from .planning_mcts import PlanningMCTS, get_mining_setup

# Planning data models
from .planning_models import (
    InitialPlanOutput,
    LanguageOutput,
    PlanOutput,
    Step,
    TaskOutput,
)
from .samplers.beam_sampler import BeamSampler

# Samplers (commonly used ones)
from .samplers.db_sampler import DBSampler
from .samplers.kld_achievement_sampler import KLDiversityAchievementSampler
from .samplers.blueprint_scenario_sampler import BlueprintScenarioSampler
from .blueprints_to_programs import BlueprintsToPrograms
from .supervised_task_executor_abc import PlanningGroupV2, SupervisedTaskExecutorABC


# Public API
__all__ = [
    # Core MCTS classes
    "MCTS",
    "FactorioLogger",
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
    "KLDiversityAchievementSampler",
    "BlueprintScenarioSampler",
    "BlueprintsToPrograms",
    # Utility functions
    "get_model_family",
    "get_logit_bias",
    "get_mining_setup",
]
