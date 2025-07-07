"""
Independent Algorithm Implementations for Factorio Learning Environment

This module provides independent evaluation algorithms and utilities for running
standalone agent evaluations in the Factorio game environment. Unlike beam search
or MCTS algorithms, these run agents independently without tree search.

Main Components:
- TrajectoryRunner: Main class for running agent trajectories
- SimpleFactorioEvaluator: Evaluates individual programs in Factorio
- ValueCalculator: Calculates item values based on recipes and complexity
- EvalConfig: Configuration for evaluation runs
"""

from .simple_evaluator import (
    SimpleFactorioEvaluator,
)

from .trajectory_runner import (
    TrajectoryRunner,
    EvalConfig,
    create_factorio_instance,
    run_process,
    get_next_version,
)

from .value_calculator import (
    ValueCalculator,
    Recipe,
)

# Version info
__version__ = "1.0.0"

# Public API
__all__ = [
    # Main evaluation classes
    "TrajectoryRunner",
    "SimpleFactorioEvaluator",
    "EvalConfig",
    # Value calculation
    "ValueCalculator",
    "Recipe",
    # Utility functions
    "create_factorio_instance",
    "run_process",
    "get_next_version",
]
