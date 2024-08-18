from controllers._action import Action
from typing import Optional, Tuple

from factorio_entities import Position, Entity
from factorio_instance import PLAYER, Direction
from factorio_types import Prototype


class PlaceEntity(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self,
                 entity: Prototype,
                 direction: Direction = Direction.UP,
                 position: Position = Position(x=0, y=0),
                 exact: bool = False,
                 #relative=False
                 ) -> Entity:
        """
        Places an entity e at local position (x, y) if the agent has enough resources.
        :param entity: Entity to place from inventory
        :param direction: Cardinal direction to place entity
        :param position: Position to place entity
        :param exact: If True, place entity at exact position, else place entity at nearest possible position
        :example stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0))
        :return: Entity object
        """


        if not isinstance(entity, Prototype):
            raise ValueError("The first argument must be a Prototype object")
        if not isinstance(direction, Direction):
            raise ValueError("The second argument must be a Direction object")

        # If position is a tuple, cast it to a Position object:
        if isinstance(position, tuple):
            position = Position(x=position[0], y=position[1])

        if not isinstance(position, Position):
            raise ValueError("The first argument must be a Prototype object")

        x, y = self.get_position(position)
        try:
            name, metaclass = entity.value
        except Exception as e:
            raise Exception(f"Passed in {entity} argument is not a valid Prototype", e)

        if direction.value > 3 or direction.value < 0:
            raise Exception("Directions are between 0-3")

        #if relative:
        #    x -= self.game_state.last_observed_player_location[0]
        #    y -= self.game_state.last_observed_player_location[1]

        if exact:
            pass

        try:
            response, elapsed = self.execute(PLAYER, name, direction.value, x, y, exact)
        except Exception as e:
            raise Exception(f"Could not place {name} at ({x}, {y})", e)

        if exact:
            pass
        if not isinstance(response, dict):
            message = response.split(":")[-1]
            raise Exception(f"Could not place {name} at ({x}, {y})", message.lstrip())

        cleaned_response = self.clean_response(response)

        try:
            object = metaclass(prototype=entity.name, **cleaned_response)
        except Exception as e:
            raise Exception(f"Could not create {name} object from response: {cleaned_response}", e)
        return object
