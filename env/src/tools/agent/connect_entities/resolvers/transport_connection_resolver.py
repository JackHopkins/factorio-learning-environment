import math
from typing import Union, Tuple, List
from entities import Position, Entity, BeltGroup, Inserter, MiningDrill, TransportBelt, Direction, EntityGroup, \
    GunTurret, AssemblingMachine, Lab, Chest, Accumulator, Furnace
from tools.agent.connect_entities.resolver import Resolver


class TransportConnectionResolver(Resolver):

    def __init__(self, *args):
        super().__init__(args)

    def _get_transport_belt_adjacent_positions(self, belt, target=False) -> List[Position]:
        source_positions = [belt.output_position] if not target else [belt.input_position]

        match belt.direction.value:
            case Direction.UP.value:
                source_positions.extend([belt.position.left(1), belt.position.right(1)])

            case Direction.DOWN.value:
                source_positions.extend([belt.position.left(1), belt.position.right(1)])

            case Direction.LEFT.value:
                source_positions.extend([belt.position.up(1), belt.position.down(1)])

            case Direction.RIGHT.value:
                source_positions.extend([belt.position.up(1), belt.position.down(1)])

        return source_positions

    def resolve(self, source: Union[Position, Entity, EntityGroup], target: Union[Position, Entity, EntityGroup]) -> List[Tuple[Position, Position]]:
        match source:
            case GunTurret() | AssemblingMachine() | Lab() | Chest() | Accumulator() | Furnace():
                raise Exception(
                    f"Cannot connect belts directly from a {source.prototype} object, we need to use an inserter.")

            case BeltGroup():
                source_positions = self._get_transport_belt_adjacent_positions(source.outputs[0], target=False)

            case Inserter():
                source_positions = [source.drop_position]

            case MiningDrill():
                source_positions = [source.drop_position]

            case TransportBelt():
                source_positions = [source.position]

            case Position():
                source_positions = [Position(x=math.floor(source.x) + 0.5, y=math.floor(source.y) + 0.5)]

            case _:
                source_positions = [source.position]

        match target:
            case GunTurret() | AssemblingMachine() | Lab() | Chest() | Accumulator() | Furnace():
                raise Exception(f"Cannot connect belts directly to a {target.prototype} object, we need to use an inserter.")

            case BeltGroup():
                #if target.inputs:
                target_positions = self._get_transport_belt_adjacent_positions(target.inputs[0], target=True)
                #else:
                #    target_positions = [belt.position for belt in target.belts]

            case Inserter():
                target_positions = [target.pickup_position]

            case MiningDrill():
                target_positions = [target.drop_position]

            case TransportBelt():
                target_positions = []
                for x_sign in [-1, 1]:
                    for y_sign in [-1, 1]:
                        target_positions.append(Position(
                            x=target.position.x + (x_sign * target.tile_dimensions.tile_width),
                            y=target.position.y + (y_sign * target.tile_dimensions.tile_height)
                        ))

            case Position():
                target_positions = [Position(x=math.floor(target.x) + 0.5, y=math.floor(target.y) + 0.5)]

            case _:
                target_positions = [target.position]

        # Generate all possible combinations, sorted by combined distance
        connection_pairs = [
            (src_pos, tgt_pos)
            for src_pos in source_positions
            for tgt_pos in target_positions
        ]

        # Sort pairs by total Manhattan distance
        return sorted(
            connection_pairs,
            key=lambda pair: (
                    abs(pair[0].x - pair[1].x) +
                    abs(pair[0].y - pair[1].y)
            )
        )