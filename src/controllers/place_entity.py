from time import sleep

from controllers.__action import Action
from typing import Optional, Tuple

from controllers.get_entity import GetEntity
from factorio_entities import Position, Entity
from factorio_instance import PLAYER
from factorio_instance import Direction
from factorio_entities import Direction as DirectionEntities
from factorio_types import Prototype


class PlaceObject(Action):

    def __init__(self, *args):
        super().__init__(*args)
        self.name = "place_entity"
        self.get_entity = GetEntity(*args)

    def __call__(self,
                 entity: Prototype,
                 direction: Direction = Direction.UP,
                 position: Position = Position(x=0, y=0),
                 exact: bool = True,
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

        #if not isinstance(entity, Prototype):
        #    raise ValueError("The first argument must be a Prototype object")

        # If position is a tuple, cast it to a Position object:
        if isinstance(position, tuple):
            position = Position(x=position[0], y=position[1])

        if not isinstance(position, Position):
            raise ValueError("The first argument must be a Prototype object")

        if not isinstance(direction, (Direction, DirectionEntities)):
            raise ValueError("The second argument must be a Direction object")

        x, y = self.get_position(position)
        try:
            name, metaclass = entity.value
            while isinstance(metaclass, tuple):
                metaclass = metaclass[1]
        except Exception as e:
            raise Exception(f"Passed in {entity} argument is not a valid Prototype", e)

        factorio_direction = Direction.to_factorio_direction(direction)

        try:
            # If we are in `fast` mode, this is synchronous
            response, elapsed = self.execute(PLAYER, name, factorio_direction, x, y, exact)
        except Exception as e:
            try:
                msg = self.get_error_message(str(e))
                raise Exception(f"Could not place {name} at ({x}, {y}), {msg}")
            except Exception:
                raise Exception(f"Could not place {name} at ({x}, {y})", e)


        # If we are in `slow` mode, there is a delay between placing the entity and the entity being created
        if not self.game_state.fast:
            sleep(1)
            return self.get_entity(entity, position)
        else:
            if not isinstance(response, dict):
                try:
                    msg = str(response).split(':')[-1].replace('"', '').replace("'", '').strip()
                except:
                    msg = str(response).lstrip()
                raise Exception(f"Could not place {name} at ({x}, {y}), {msg}")

            cleaned_response = self.clean_response(response)

            try:
                object = metaclass(prototype=entity.name, **cleaned_response)
            except Exception as e:
                raise Exception(f"Could not create {name} object from response: {cleaned_response}", e)

            # if object is a burner insert, and is missing a pickup_position, calculate it from the position and direction
            # TODO: Remove and move to
            # if entity.name == Prototype.BurnerInserter.name:
            #     if not object.pickup_position:
            #         if direction == Direction.UP:
            #             object.pickup_position = Position(x=position.x, y=position.y - 1)
            #         elif direction == Direction.DOWN:
            #             object.pickup_position = Position(x=position.x, y=position.y + 1)
            #         elif direction == Direction.LEFT:
            #             object.pickup_position = Position(x=position.x - 1, y=position.y)
            #         elif direction == Direction.RIGHT:
            #             object.pickup_position = Position(x=position.x + 1, y=position.y)
            return object
