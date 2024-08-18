from typing import Tuple

from controllers._action import Action
from factorio_entities import Position, Entity

from factorio_instance import PLAYER
from factorio_types import Prototype


class GetEntity(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.connection = connection
        self.game_state = game_state

    def __call__(self, entity: Prototype, position: Position) -> Entity:
        """
        Get a given entity prototype at position (x, y) if it exists on the world.
        :param entity: Entity prototype to get, e.g Prototype.IronPlate
        :param position: Position to get entity
        :example stone_furnace = get_entity(Prototype.StoneFurnace, nearest(Prototype.StoneFurnace))
        :return: Entity object
        """
        assert isinstance(entity, Prototype)
        assert isinstance(position, Position)

        try:
            x, y = self.get_position(position)
            name, metaclass = entity.value

            response, elapsed = self.execute(PLAYER, name, x, y)

            if response is None or response == {} or isinstance(response, str):
                raise Exception("Could not get entity, does it exist at the specified position?", response)

            for key, value in response.items():
                if isinstance(value, dict):
                    if 1 in value.keys():
                        response[key] = []
                        for sub_key, sub_value in value.items():
                            if 1 in sub_value.keys():
                                prototype_suffix = sub_value[1]
                                sub_value['name'] = sub_value['name'] + '-' + prototype_suffix
                                # Remove the 1 key from the dictionary
                                sub_value.pop(1)
                            response[key].append(sub_value)

            if 'prototype' not in response.keys():
                response['prototype'] = entity
            try:
                object = metaclass(**response)
            except Exception as e:
                 raise Exception(f"Could not create {name} object from response: {response}", e)
            return object
        except Exception as e:
            raise Exception(f"Could not get entity {entity} at position {position}", e)

