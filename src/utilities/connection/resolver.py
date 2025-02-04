from dataclasses import dataclass
from enum import Enum, auto
from typing import Union, List, Optional, Protocol, Tuple

from factorio_entities import Position, Entity


@dataclass
class ConnectionPoint:
    position: Position
    entity: Optional[Entity] = None

class ConnectionType(Enum):
    FLUID = auto()
    TRANSPORT = auto()
    POWER = auto()

class PositionResolver(Protocol):
    def resolve(self, source: Union[Position, Entity], target: Union[Position, Entity]) -> Tuple[Position, Position]:
        pass

class Resolver():
    def __init__(self, get_entities):
        self.get_entities = get_entities

    def _is_blocked(self, pos: Position) -> bool:
        entities = self.get_entities(position=pos, radius=0.5)
        return bool(entities)