from typing import Tuple

from controllers.__action import Action
from factorio_entities import Position, Entity

from factorio_instance import PLAYER
from factorio_types import Prototype


class GetEntity(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

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
            while isinstance(metaclass, tuple):
                metaclass = metaclass[1]

            response, elapsed = self.execute(PLAYER, name, x, y)

            if response is None or response == {} or isinstance(response, str):
                msg = response.split(':')[-1]
                raise Exception(msg)

            cleaned_response = self.clean_response(response)
            try:
                object = metaclass(prototype=entity.name, **cleaned_response)
            except Exception as e:
                raise Exception(f"Could not create {name} object from response: {cleaned_response}", e)

            return object
        except Exception as e:
            raise Exception(f"Could not get {entity} at position {position}", e)

