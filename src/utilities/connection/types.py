from dataclasses import dataclass
from typing import Optional, Union, List, Dict, Tuple
from enum import Enum

from factorio_entities import (
    Entity, Position, EntityGroup, BeltGroup,
    FluidHandler, Inserter, MiningDrill, TransportBelt,
    PumpJack, OffshorePump, Boiler, Generator, PipeGroup
)
from factorio_types import Prototype

class ConnectionError(Exception):
    """Base exception for connection-related errors"""
    pass

class InvalidConnectionTypeError(ConnectionError):
    """Raised when an invalid connection type is provided"""
    pass

class ConnectionPathError(ConnectionError):
    """Raised when a path cannot be found between points"""
    pass

@dataclass
class ConnectionContext:
    """Context object containing all information needed for a connection"""
    source_position: Position
    target_position: Position
    source_entity: Optional[Entity] = None
    target_entity: Optional[Entity] = None
    connection_type: Optional[Prototype] = None
    x_sign: float = 0
    y_sign: float = 0

    @property
    def is_fluid_connection(self) -> bool:
        return (
            isinstance(self.source_entity, FluidHandler) and
            isinstance(self.target_entity, FluidHandler)
        )

@dataclass
class PathResult:
    """Result of path finding operation"""
    success: bool
    entities: List[Entity]
    warnings: List[str]
    number_of_entities: int

@dataclass
class DryRunResult:
    """Result of dry run connection attempt"""
    number_of_entities_required: int
    number_of_entities_available: int

EntityOrGroup = Union[Entity, EntityGroup]
ConnectionSource = Union[Position, EntityOrGroup]
ConnectionTarget = Union[Position, EntityOrGroup]