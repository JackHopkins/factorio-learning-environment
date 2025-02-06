from typing import Union, Tuple, List

from entities import Position, Entity, ElectricityGroup
from tools.agent.connect_entities.resolver import Resolver


class PowerConnectionResolver(Resolver):
    def __init__(self, *args):
        super().__init__(args)

    def resolve(self, source: Union[Position, Entity, ElectricityGroup], target: Union[Position, Entity, ElectricityGroup]) -> List[Tuple[Position, Position]]:
        """Resolve positions for power connections"""

        if isinstance(source, ElectricityGroup):
            positions = []
            target_pos = target.position if isinstance(target, Entity) else target
            target_pos = Position(
                x=round(target_pos.x * 2) / 2,
                y=round(target_pos.y * 2) / 2
            )
            for pole in source.poles:
                positions.append((pole.position, target_pos))

            return positions

        else:
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
