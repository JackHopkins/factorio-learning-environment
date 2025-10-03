"""Factorio environment module."""

# Suppress slpp SyntaxWarning about invalid escape sequences
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning, module="slpp")

from fle.env.entities import *  # noqa
from fle.env.game_types import Prototype, Resource
from fle.env.instance import DirectionInternal, FactorioInstance

__all__ = [
    "FactorioInstance",
    "DirectionInternal",
    "Direction",
    "Entity",
    "Position",
    "Inventory",
    "EntityGroup",
    "Prototype",
    "Resource",
]
