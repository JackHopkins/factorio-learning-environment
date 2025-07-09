from typing import Union, Tuple, List, Set
from fle.env.entities import Position, Entity, ElectricityGroup
from fle.env.tools.agent.connect_entities.resolver import Resolver


class PowerConnectionResolver(Resolver):
    def __init__(self, *args):
        super().__init__(*args)

    def _check_existing_network_connection(self, source_entity, target_entity) -> bool:
        """
        Check if source and target are already connected to the same power network.

        Returns True if already connected, False otherwise.
        """
        if not (source_entity and target_entity):
            return False

        if not hasattr(source_entity, "electrical_id") or not hasattr(
            target_entity, "electrical_id"
        ):
            return False

        return (
            source_entity.electrical_id == target_entity.electrical_id
            and source_entity.electrical_id is not None
        )

    def _get_entity_connection_points(self, entity: Entity) -> Set[Position]:
        """Get all predefined connection points for an entity."""
        connection_points = set()

        # Check for explicitly defined connection points
        if hasattr(entity, "connection_points"):
            connection_points.update(entity.connection_points)
        if hasattr(entity, "input_connection_points"):
            connection_points.update(entity.input_connection_points)
        if hasattr(entity, "output_connection_points"):
            connection_points.update(entity.output_connection_points)

        return connection_points

    def _get_adjacent_tiles(self, entity: Entity) -> List[Position]:
        """Generate a list of positions for tiles adjacent to the entity."""
        positions = []

        # Get the entity's dimensions in tiles
        width = entity.tile_dimensions.tile_width
        height = entity.tile_dimensions.tile_height

        # Calculate the entity's bounds
        start_x = entity.position.x - (width / 2)
        start_y = entity.position.y - (height / 2)
        end_x = start_x + width
        end_y = start_y + height

        # Generate positions for tiles along each edge
        # Top edge
        for x in range(int(start_x), int(end_x + 1)):
            positions.append(Position(x=x, y=start_y - 1))

        # Bottom edge
        for x in range(int(start_x), int(end_x + 1)):
            positions.append(Position(x=x, y=end_y))

        # Left edge
        for y in range(int(start_y), int(end_y + 1)):
            positions.append(Position(x=start_x - 1, y=y))

        # Right edge
        for y in range(int(start_y), int(end_y + 1)):
            positions.append(Position(x=end_x, y=y))

        return [pos.down(0.5).right(0.5) for pos in positions]

    def _get_valid_connection_points(self, entity: Entity) -> List[Position]:
        """Get valid connection points for an entity, avoiding predefined points."""
        # First check for predefined connection points
        predefined_points = self._get_entity_connection_points(entity)
        # If no predefined points exist, use adjacent tiles
        adjacent_tiles = self._get_adjacent_tiles(entity)

        ignore_points = set()
        for tile in adjacent_tiles:
            for point in predefined_points:
                if tile.is_close(point, tolerance=0.707):
                    ignore_points.add(point)

        return list(set(adjacent_tiles) - ignore_points)

    def resolve(
        self,
        source: Union[Position, Entity, ElectricityGroup],
        target: Union[Position, Entity, ElectricityGroup],
    ) -> List[Tuple[Position, Position]]:
        """Resolve positions for power connections"""

        # First check if source and target are already connected
        # if self._check_existing_network_connection(source, target):
        #    raise Exception("Source and target are already connected to the same power network")

        if isinstance(source, ElectricityGroup):
            positions = []
            if isinstance(target, Entity):
                # Get valid connection points for the target entity
                target_positions = self._get_valid_connection_points(target)
                # For each pole in the source group, connect to the nearest valid point
                for pole in source.poles:
                    nearest_point = min(
                        target_positions,
                        key=lambda pos: abs(pos.x - pole.position.x)
                        + abs(pos.y - pole.position.y),
                    )
                    positions.append((pole.position, nearest_point))
            else:
                # If target is a Position, round it to the nearest half-tile
                target_pos = (
                    target.position
                    if (
                        isinstance(target, Entity)
                        or isinstance(target, ElectricityGroup)
                    )
                    else target
                )
                target_pos = Position(
                    x=round(target_pos.x * 2) / 2, y=round(target_pos.y * 2) / 2
                )
                for pole in source.poles:
                    positions.append((pole.position, target_pos))
            return positions
        else:
            source_pos = source.position if isinstance(source, Entity) else source
            # Round source position to nearest half-tile
            source_pos = Position(
                x=round(source_pos.x * 2) / 2, y=round(source_pos.y * 2) / 2
            )

            if isinstance(target, Entity):
                # Get valid connection points for the target entity
                target_positions = self._get_valid_connection_points(target)
                # Connect to the nearest valid point
                nearest_point = min(
                    target_positions,
                    key=lambda pos: abs(pos.x - source_pos.x)
                    + abs(pos.y - source_pos.y),
                )
                return [(source_pos, nearest_point)]
            else:
                # If target is a Position, round it to the nearest half-tile
                target_pos = (
                    target.position
                    if (
                        isinstance(target, Entity)
                        or isinstance(target, ElectricityGroup)
                    )
                    else target
                )
                target_pos = Position(
                    x=round(target_pos.x * 2) / 2, y=round(target_pos.y * 2) / 2
                )
                return [(source_pos, target_pos)]
