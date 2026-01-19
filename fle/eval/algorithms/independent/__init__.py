"""
Independent Algorithm Implementations for Factorio Learning Environment

This module provides independent evaluation algorithms and utilities for running
standalone agent evaluations in the Factorio game environment. Unlike beam search
or MCTS algorithms, these run agents independently without tree search.

Main Components:
- ValueCalculator: Calculates item values based on recipes and complexity
- GymTrajectoryRunner: Handles program generation and evaluation for a single trajectory
- GymEvalConfig: Configuration for gym-based evaluation runs
"""

from .value_calculator import (
    ValueCalculator,
    Recipe,
)

from .trajectory_runner import GymTrajectoryRunner
from .config import GymEvalConfig

# Version info
__version__ = "1.0.0"

# Public API
__all__ = [
    # Main evaluation classes
    "GymTrajectoryRunner",
    "GymEvalConfig",
    # Value calculation
    "ValueCalculator",
    "Recipe",
]
