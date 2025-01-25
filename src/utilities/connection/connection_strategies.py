from abc import ABC, abstractmethod
import math
from typing import Tuple, Optional

from factorio_entities import Inserter, TransportBelt, BeltGroup, MiningDrill, OffshorePump, Boiler, PumpJack, \
    Generator, Entity
from .types import ConnectionContext, Position, FluidHandler
from factorio_instance import Direction


class ConnectionStrategy(ABC):
    """Base class for connection strategies"""

    @abstractmethod
    def get_connection_points(self, context: ConnectionContext) -> Tuple[Position, Position]:
        """Get the source and target positions for the connection"""
        pass

    def _round_to_half_tile(self, position: Position) -> Position:
        """Round position coordinates to the nearest half-tile"""
        return Position(
            x=round(position.x * 2) / 2,
            y=round(position.y * 2) / 2
        )


class FluidConnectionStrategy(ConnectionStrategy):
    """Strategy for connecting fluid-handling entities"""

    def get_connection_points(self, context: ConnectionContext) -> Tuple[Position, Position]:
        source_pos = self._get_fluid_source_position(context)
        target_pos = self._get_fluid_target_position(context)
        return (
            self._round_to_half_tile(source_pos),
            self._round_to_half_tile(target_pos)
        )

    def _get_fluid_source_position(self, context: ConnectionContext) -> Position:
        if isinstance(context.source_entity, PumpJack):
            return context.source_entity.connection_points[0]

        if isinstance(context.source_entity, OffshorePump):
            return Position(
                x=context.source_entity.connection_points[0].x,
                y=context.source_entity.connection_points[0].y
            )

        if isinstance(context.source_entity, Boiler):
            if isinstance(context.target_entity, Generator):
                return self._get_boiler_steam_output_position(context)
            return self._get_nearest_connection_point(
                context.source_entity,
                context.source_position,
                context.target_entity
            )

        if isinstance(context.source_entity, FluidHandler):
            return self._get_nearest_connection_point(
                context.source_entity,
                context.source_position,
                context.target_entity
            )

        return context.source_position

    def _get_fluid_target_position(self, context: ConnectionContext) -> Position:
        if isinstance(context.target_entity, Boiler):
            if isinstance(context.source_entity, OffshorePump):
                return self._get_nearest_connection_point(
                    context.target_entity,
                    context.source_position,
                    context.source_entity
                )
            return context.target_entity.steam_output_point

        if isinstance(context.target_entity, FluidHandler):
            return self._get_nearest_connection_point(
                context.target_entity,
                context.source_position,
                context.source_entity
            )

        return context.target_position

    def _get_boiler_steam_output_position(self, context: ConnectionContext) -> Position:
        """Calculate the steam output position for a boiler"""
        BOILER_WIDTH = 3
        OFFSET = 0

        x_diff = (context.source_entity.position.x -
                  context.source_entity.steam_output_point.x)
        y_diff = (context.source_entity.position.y -
                  context.source_entity.steam_output_point.y)

        if x_diff == 0:
            return Position(
                x=context.source_entity.position.x,
                y=context.source_entity.position.y +
                  (BOILER_WIDTH / 2 + OFFSET if y_diff < 0 else -BOILER_WIDTH / 2 - OFFSET)
            )
        else:
            return Position(
                x=context.source_entity.position.x +
                  (BOILER_WIDTH / 2 + OFFSET if x_diff < 0 else -BOILER_WIDTH / 2 - OFFSET),
                y=context.source_entity.position.y
            )

    def _get_nearest_connection_point(
            self,
            fluid_handler: FluidHandler,
            existing_pos: Position,
            existing_entity: Optional[Entity] = None
    ) -> Position:
        """Find the nearest valid connection point for a fluid handler"""
        if existing_entity:
            existing_offset = Position(
                x=existing_pos.x - existing_entity.position.x,
                y=existing_pos.y - existing_entity.position.y
            )
        else:
            existing_offset = Position(x=0, y=0)

        nearest_point = min(
            fluid_handler.connection_points,
            key=lambda p: abs(p.x - existing_pos.x) + abs(p.y - existing_pos.y)
        )

        x = nearest_point.x
        y = nearest_point.y

        # Adjust to ensure connection point is outside entity
        if x % 1 == 0:
            x += 0.5 if x > fluid_handler.position.x else -0.5
        if y % 1 == 0:
            y += 0.5 if y > fluid_handler.position.y else -0.5

        return Position(x=x, y=y)


class BeltConnectionStrategy(ConnectionStrategy):
    """Strategy for connecting transport belt entities"""

    def get_connection_points(self, context: ConnectionContext) -> Tuple[Position, Position]:
        source_pos = self._get_belt_source_position(context)
        target_pos = self._get_belt_target_position(context)

        # Ensure positions are at tile centers for belts
        source_pos = self._center_on_tile(source_pos)
        target_pos = self._center_on_tile(target_pos)

        return source_pos, target_pos

    def _get_belt_source_position(self, context: ConnectionContext) -> Position:
        if isinstance(context.source_entity, BeltGroup):
            return context.source_entity.outputs[0].position

        if isinstance(context.source_entity, Inserter):
            return context.source_entity.drop_position

        if isinstance(context.source_entity, MiningDrill):
            return context.source_entity.drop_position

        if isinstance(context.source_entity, TransportBelt):
            return context.source_entity.position

        return Position(
            x=context.source_entity.position.x - context.x_sign *
              context.source_entity.tile_dimensions.tile_width / 2,
            y=context.source_entity.position.y - context.y_sign *
              context.source_entity.tile_dimensions.tile_height / 2
        ) if context.source_entity else context.source_position

    def _get_belt_target_position(self, context: ConnectionContext) -> Position:
        if isinstance(context.target_entity, BeltGroup):
            belt_inputs = [belt.position for belt in context.target_entity.inputs]
            return min(
                belt_inputs,
                key=lambda pos: context.source_position.distance(pos)
            )

        if isinstance(context.target_entity, Inserter):
            return context.target_entity.pickup_position

        if isinstance(context.target_entity, TransportBelt):
            return Position(
                x=context.target_entity.position.x +
                  (context.x_sign * context.target_entity.tile_dimensions.tile_width),
                y=context.target_entity.position.y +
                  (context.y_sign * context.target_entity.tile_dimensions.tile_height)
            )

        return context.target_position

    def _center_on_tile(self, position: Position) -> Position:
        """Center position on tile for belt connections"""
        return Position(
            x=math.floor(position.x) + 0.5,
            y=math.floor(position.y) + 0.5
        )


class ElectricPoleStrategy(ConnectionStrategy):
    """Strategy for connecting electric pole entities"""

    def get_connection_points(self, context: ConnectionContext) -> Tuple[Position, Position]:
        # Electric poles have simpler connection logic
        return context.source_position, context.target_position