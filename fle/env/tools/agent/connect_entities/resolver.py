from dataclasses import dataclass
from enum import Enum, auto
from typing import Union, List, Optional, Protocol, Tuple

from fle.env.entities import Position, Entity


@dataclass
class ConnectionPoint:
    position: Position
    entity: Optional[Entity] = None


class ConnectionType(Enum):
    FLUID = auto()
    TRANSPORT = auto()
    POWER = auto()
    WALL = auto()


class PositionResolver(Protocol):
    def resolve(
        self, source: Union[Position, Entity], target: Union[Position, Entity]
    ) -> Tuple[Position, Position]:
        pass


class Resolver:
    def __init__(self, get_entities):
        self.get_entities = get_entities

    def _is_blocked(self, pos: Position) -> bool:
        entities = self.get_entities(position=pos, radius=0.5)
        return bool(entities)

    def resolve(
        self, source: Union[Position, Entity], target: Union[Position, Entity]
    ) -> List[Tuple[Position, Position]]:
        source_pos, target_pos = None, None
        if isinstance(source, Position):
            source_pos = source
        else:
            source_pos = source.position
        if isinstance(target, Position):
            target_pos = target
        else:
            target_pos = target.position
        return [(source_pos, target_pos)]
