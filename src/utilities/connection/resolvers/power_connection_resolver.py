from typing import Union, Tuple, List

from factorio_entities import Position, Entity
from utilities.connection.resolver import Resolver


class PowerConnectionResolver(Resolver):
    def __init__(self, *args):
        super().__init__(args)

    def resolve(self, source: Union[Position, Entity], target: Union[Position, Entity]) -> List[Tuple[Position, Position]]:
        """Resolve positions for power connections"""
        # For power poles, we mainly care about the entity centers and handle collision avoidance in pathing
        source_pos = source.position if isinstance(source, Entity) else source
        target_pos = target.position if isinstance(target, Entity) else target

        # Round positions to ensure consistent placement
        source_pos = Position(
            x=round(source_pos.x * 2) / 2,
            y=round(source_pos.y * 2) / 2
        )
        target_pos = Position(
            x=round(target_pos.x * 2) / 2,
            y=round(target_pos.y * 2) / 2
        )

        return [(source_pos, target_pos)]
