"""
Beam Search Algorithm Implementation for Factorio Learning Environment

This module provides parallel beam search algorithms for exploring and optimizing
strategies in the Factorio game environment. It includes both standard beam search
and milestone-based variants.

Main Components:
- ParallelBeamSearch: Main parallel beam search implementation
- BeamSearch: Individual beam search component
- BeamGroup: Represents a single beam position
- MilestonesBeamSearchExecutor: Beam search with milestone support
"""

from .beam_search import (
    # Main classes
    ParallelBeamSearch,
    BeamSearch,
    BeamGroup,
    ParallelBeamConfig,
    # Model utilities
    ModelFamily,
    get_model_family,
    get_logit_bias,
)

from .beam_search_milestones import (
    MilestonesBeamSearchExecutor,
)

# Version info
__version__ = "1.0.0"

# Public API
__all__ = [
    # Main beam search classes
    "ParallelBeamSearch",
    "BeamSearch",
    "BeamGroup",
    "ParallelBeamConfig",
    # Milestones variant
    "MilestonesBeamSearchExecutor",
    # Model utilities
    "ModelFamily",
    "get_model_family",
    "get_logit_bias",
]
