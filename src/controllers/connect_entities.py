import math

import numpy
import numpy as np

from controllers._action import Action
from typing import Tuple, List, Union

from controllers.get_path import GetPath
from controllers.request_path import RequestPath
from factorio_entities import Entity, Boiler, FluidHandler, Position, Generator, Inserter, MiningDrill, TransportBelt, \
    OffshorePump
from factorio_instance import PLAYER
from factorio_types import Prototype


class ConnectEntities(Action):

    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)
        self.request_path = RequestPath(connection, game_state)
        self.get_path = GetPath(connection, game_state)


    def _get_nearest_connection_point(self,
                                      fluid_handler_source: FluidHandler,
                                      existing_connection_position: Position,
                                      existing_connection_entity: Entity = None):

        if existing_connection_entity is not None:
            existing_offset_x = existing_connection_position.x - existing_connection_entity.position.x
            existing_offset_y = existing_connection_position.y - existing_connection_entity.position.y
        else:
            existing_offset_x = 0
            existing_offset_y = 0

        # By default, select the first connection point
        nearest_connection_point = fluid_handler_source.connection_points[0]
        nearest_distance = 10000000  # Large value

        for connection_point in fluid_handler_source.connection_points:
            possible_offset_x = connection_point.x - fluid_handler_source.position.x
            possible_offset_y = connection_point.y - fluid_handler_source.position.y

            # Calculate directional components
            dir_x = np.sign(possible_offset_x - existing_offset_x)
            dir_y = np.sign(possible_offset_y - existing_offset_y)

            # Check if points are facing each other
            # if dir_x == 0 and dir_y == 0:  # They are on top of each other, so just return this point
            #     return connection_point
            # elif dir_x == 0 and possible_offset_y * dir_y < 0:  # They are vertically aligned and facing each other
            #     continue
            # elif dir_y == 0 and possible_offset_x * dir_x < 0:  # They are horizontally aligned and facing each other
            #     continue
            # elif possible_offset_x * dir_x < 0 and possible_offset_y * dir_y < 0:  # They are diagonally aligned and facing each other
            #     continue

            # Calculate distance
            distance = abs(connection_point.x - existing_connection_position.x) + abs(
                connection_point.y - existing_connection_position.y)

            # Update if this distance is smaller
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_connection_point = connection_point

        # # If the connection point is to the left of the source position, and a 0.5 x offset
        # if nearest_connection_point.x < fluid_handler_source.position.x:
        #     nearest_connection_point = Position(x=nearest_connection_point.x + 0.5, y=nearest_connection_point.y)
        # # If the connection point is to the right of the source position, and a -0.5 x offset
        # elif nearest_connection_point.x > fluid_handler_source.position.x:
        #     nearest_connection_point = Position(x=nearest_connection_point.x - 0.5, y=nearest_connection_point.y)
        #
        # # If the connection point is above the source position, and a 0.5 y offset
        # if nearest_connection_point.y < fluid_handler_source.position.y:
        #     nearest_connection_point = Position(x=nearest_connection_point.x, y=nearest_connection_point.y - 0.5)
        # # If the connection point is below the source position, and a -0.5 y offset
        # elif nearest_connection_point.y > fluid_handler_source.position.y:
        #     nearest_connection_point = Position(x=nearest_connection_point.x, y=nearest_connection_point.y + 0.5)

        return nearest_connection_point

    def _round_position(self, position: Position):
        return Position(x=math.floor(position.x), y=math.floor(position.y))

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Remove duplicate entities while maintaining the original order.
        Later entities with the same position override earlier ones.
        """
        unique_entities = []
        seen = set()
        for entity in reversed(entities):
            position = (entity.position.x, entity.position.y)
            if position not in seen:
                unique_entities.append(entity)
                seen.add(position)
        return list(reversed(unique_entities))

    def __call__(self,
                 source: Union[Position, Entity],
                 target: Union[Position, Entity],
                 connection_type: Prototype = Prototype.Pipe,
                 #relative=False
                 ) -> List[Entity]:
        """
        Connect two entities or positions.
        :param source: First entity or position
        :param target: Second entity or position
        :param connection_type: a Pipe, TransportBelt or ElectricPole
        :example connect_entities(source=boiler, target=generator, connection_type=Prototype.Pipe)
        :example connect_entities(source=miner, target=stone_furnace, connection_type=Prototype.TransportBelt)
        :return: List of entities that were created
        """

        connection_prototype, metaclass = connection_type.value
        source_entity = None
        target_entity = None
        if isinstance(source, Entity):
            source_entity = source
            source_position = Position(x=source_entity.position.x, y=source_entity.position.y)
        elif isinstance(source, Position):
            source_position = source
        else:
            raise TypeError("Source must be either an Entity or Position.")

        if isinstance(target, Entity):
            target_entity = target
            target_position = Position(x=target_entity.position.x, y=target_entity.position.y)
        elif isinstance(target, Position):
            target_position = target
        else:
            raise TypeError("Target must be either an Entity or Position.")

        if source_entity:
            x_sign = numpy.sign(source_entity.position.x - target_position.x)
            y_sign = numpy.sign(source_entity.position.y - target_position.y)
        else:
            x_sign = numpy.sign(source_position.x - target_position.x)
            y_sign = numpy.sign(source_position.y - target_position.y)

        if source_entity and isinstance(source, Entity):
            if isinstance(source_entity, FluidHandler):
                if isinstance(source_entity, OffshorePump):
                    source_position = Position(x=source_entity.connection_points[0].x+1,
                                               y=source_entity.connection_points[0].y+1)
                elif isinstance(source_entity, Boiler):
                    if target_entity and isinstance(target_entity, Generator):
                        #source_position = self._round_position(source_entity.steam_output_point)
                        x_diff_source_position_target_position = source_entity.position.x - source_entity.steam_output_point.x
                        y_diff_source_position_target_position = source_entity.position.y - source_entity.steam_output_point.y

                        # check if steam_output_point is on the top, bottom, left or right of the boiler, if so, add a 0.5 offset to the position in the direction of the generator
                        if x_diff_source_position_target_position == 0:
                            if y_diff_source_position_target_position < 0:
                                source_position = Position(x=source_entity.position.x, y=source_entity.position.y + 1.5)
                            else:
                                source_position = Position(x=source_entity.position.x, y=source_entity.position.y - 1.5)
                        elif y_diff_source_position_target_position == 0:
                            if x_diff_source_position_target_position < 0:
                                source_position = Position(x=source_entity.position.x + 1.5, y=source_entity.position.y)
                            else:
                                source_position = Position(x=source_entity.position.x - 1.5, y=source_entity.position.y)

                        #source_position = Position(x=source_entity.steam_output_point.x, y=source_entity.steam_output_point.y)
                    elif target_entity and isinstance(target_entity, OffshorePump):
                        #target_position = target_entity.connection_points[0]
                        target_position = Position(x=target_entity.connection_points[0].x + 1,
                                                   y=target_entity.connection_points[0].y + 1)

                        nearest_connection_point = self._get_nearest_connection_point(source_entity, target_position, target_entity)
                        # find the closest connection_point to the target_position

                        x_diff_source_position_target_position = source_entity.position.x - nearest_connection_point.x
                        y_diff_source_position_target_position = source_entity.position.y - nearest_connection_point.y

                        if x_diff_source_position_target_position == 0:
                            if y_diff_source_position_target_position < 0:
                                source_position = Position(x=source_entity.position.x - 0.5, y=source_entity.position.y + 2)
                            else:
                                source_position = Position(x=source_entity.position.x + 0.5, y=source_entity.position.y - 2)
                        elif y_diff_source_position_target_position == 0:
                            if x_diff_source_position_target_position < 0:
                                source_position = Position(x=source_entity.position.x + 2, y=source_entity.position.y + 0.5)
                            else:
                                source_position = Position(x=source_entity.position.x - 2, y=source_entity.position.y - 0.5)

                else:
                    source_position = self._get_nearest_connection_point(source_entity,
                                                                         target_position,
                                                                         existing_connection_entity=target_entity)

            elif isinstance(source_entity, Inserter):
                source_position = source_entity.drop_position
            elif isinstance(source_entity, MiningDrill):
                source_position = source_entity.drop_position
            elif isinstance(source_entity, TransportBelt):
                source_position = source_entity.input_position
            else:
                source_position = Position(x=source_entity.position.x-x_sign*source_entity.tile_dimensions.tile_width/2,
                                           y=source_entity.position.y-y_sign*source_entity.tile_dimensions.tile_height/2)

        if isinstance(target, Entity):
            if isinstance(target_entity, FluidHandler):
                if isinstance(target_entity, Boiler):
                    if isinstance(source_entity, OffshorePump):
                        target_position = self._get_nearest_connection_point(target_entity,
                                                                             source_position,
                                                                             existing_connection_entity=source_entity)
                    else:
                        target_position = target_entity.steam_input_point
                elif isinstance(target_entity, Boiler) and isinstance(source_entity, Generator):
                    target_position = target_entity.steam_input_point
                else:
                    target_position = self._get_nearest_connection_point(target_entity,
                                                                         source_position,
                                                                         existing_connection_entity=source_entity)
                    #target_position = Position(x=target_position.x+0.5, y=target_position.y+0.5)
                    target_position = Position(x=target_position.x, y=target_position.y)

            elif isinstance(target_entity, Inserter):
                target_position = target_entity.pickup_position
            elif isinstance(target_entity, MiningDrill):
                target_position = target_entity.drop_position
            elif isinstance(target_entity, TransportBelt):
                target_position = target_entity.position
            else:
                target_position = Position(x=target_entity.position.x + x_sign*source_entity.tile_dimensions.tile_width/2,
                                           y=target_entity.position.y + y_sign*source_entity.tile_dimensions.tile_height/2)

        # if target_entity and isinstance(target, Entity):
        #     path_handle = self.request_path(start=Position(x=target_entity.position.x-0.5,
        #                                                    y=target_entity.position.y-0.5), finish=source_position)
        # else:
        #     path_handle = self.request_path(start=Position(x=target_position.x-0.5,
        #                                                    y=target_position.y-0.5), finish=source_position)

        # Move the source and target positions to the center of the tile
        target_position = Position(x=target_position.x, y=target_position.y)
        source_position = Position(x=source_position.x, y=source_position.y)
        path_handle = self.request_path(finish=Position(x=target_position.x, y=target_position.y), start=source_position)

        response, elapsed = self.execute(PLAYER,
                                         source_position.x,
                                         source_position.y,
                                         target_position.x,
                                         target_position.y,
                                         path_handle,
                                         connection_prototype)
        if not isinstance(response, dict) and response != "Passed":
            message = response.split(":")[-1]
            raise Exception(f"Could not connect {connection_prototype} from {(source_position)} to {(target_position)}.", message.lstrip())

        success = response.get('connected', False)
        entities_list = response.get('entities', {}).values()
        path = []
        for value in entities_list:
            if isinstance(value, dict):
                try:
                    entity = metaclass(prototype=connection_type, **value)
                    path.append(entity)
                except Exception as e:
                    if not value:
                        continue
                    raise Exception(f"Could not create {connection_prototype} object from response: {response}", e)

        # Use the new deduplication function
        return self._deduplicate_entities(path)