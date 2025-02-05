from typing import Optional, Union, Tuple, cast, List

from factorio_entities import FluidHandler, Position, Entity, Generator, Boiler, OffshorePump, Pipe, OilRefinery, \
    ChemicalPlant
from utilities.connection.resolver import Resolver


class FluidConnectionResolver(Resolver):
    def __init__(self, *args):
        super().__init__(*args)

    def _adjust_connection_point(self, point: Position, entity: Entity) -> Position:
        x, y = point.x, point.y

        if x % 1 == 0:
            x += 0.5 if x > entity.position.x else -0.5 if x < entity.position.x else 0
        if y % 1 == 0:
            y += 0.5 if y > entity.position.y else -0.5 if y < entity.position.y else 0

        return Position(x=x, y=y)

    def _is_blocked(self, pos: Position) -> bool:
        entities = self.get_entities(position=pos, radius=0.5)
        return bool(entities)

    def resolve(self, source: Union[Position, Entity], target: Union[Position, Entity]) -> List[Tuple[Position, Position]]:
        """Returns prioritized list of source/target position pairs to attempt connections."""

        # Get source positions in priority order
        match (source, target):
            case (OffshorePump(), _):
                source_positions = source.connection_points

            case (Boiler(), Generator()):
                source_positions = [source.steam_output_point]

            case (Boiler(), Boiler() | OffshorePump()):
                sorted_positions = self._get_all_connection_points(
                    cast(FluidHandler, source),
                    target.position,
                    source.connection_points
                )
                source_positions = sorted_positions if sorted_positions else [source.position]

            case (FluidHandler(), _):
                sorted_positions = self._get_all_connection_points(
                    cast(FluidHandler, source),
                    target.position,
                    source.connection_points
                )
                source_positions = sorted_positions if sorted_positions else [source.position]

            case (Pipe(), _):
                source_positions = [source.position, source.position.up(), source.position.down(), source.position.left(), source.position.right()]

            case (OilRefinery() | ChemicalPlant(), _):
                sorted_positions = self._get_all_connection_points(
                    cast(FluidHandler, source),
                    target.position,
                    source.output_connection_points
                )
                source_positions = sorted_positions if sorted_positions else [target.position]

            case (Position(), _):
                source_positions = [source]

            case (Entity(), _):
                source_positions = [source.position]

            case _:
                raise Exception("Not supported source object")

        # Get target positions in priority order
        match target:
            case Boiler():
                if isinstance(source, (OffshorePump, Boiler)):
                    sorted_positions = self._get_all_connection_points(
                        cast(FluidHandler, target),
                        source_positions[0],  # Use first source pos for initial sorting
                        target.connection_points
                    )
                    target_positions = sorted_positions if sorted_positions else [target.position]
                else:
                    target_positions = [target.steam_output_point]

            case FluidHandler():
                sorted_positions = self._get_all_connection_points(
                    cast(FluidHandler, target),
                    source_positions[0],
                    target.connection_points
                )
                target_positions = sorted_positions if sorted_positions else [target.position]

            case Position():
                target_positions = [target]

            case Pipe():
                target_positions = [target.position, target.position.up(), target.position.down(),
                                    target.position.left(), target.position.right()]

            case OilRefinery() | ChemicalPlant():
                sorted_positions = self._get_all_connection_points(
                    cast(FluidHandler, target),
                    source_positions[0],
                    target.input_connection_points
                )
                target_positions = sorted_positions if sorted_positions else [target.position]

            case Entity():
                target_positions = [target.position]

            case _:
                raise Exception("Not supported target object")

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

    def _get_all_connection_points(self,
                                   fluid_handler: FluidHandler,
                                   reference_pos: Position,
                                   connection_points) -> List[Position]:
        """Get all possible connection points sorted by distance."""

        # Sort all connection points by distance to reference position
        sorted_points = sorted(
            connection_points,
            key=lambda point: abs(point.x - reference_pos.x) + abs(point.y - reference_pos.y)
        )

        # Adjust each point and filter out blocked ones
        valid_points = []
        for point in sorted_points:
            adjusted = self._adjust_connection_point(point, fluid_handler)
            if not self._is_blocked(adjusted):
                valid_points.append(adjusted)

        return valid_points