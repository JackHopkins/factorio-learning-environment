from time import sleep

from fle.env.entities import Position, Entity
from fle.env import DirectionInternal, Direction
from fle.env.game_types import Prototype
from fle.env.tools.agent.get_entity.client import GetEntity
from fle.env.tools.agent.pickup_entity.client import PickupEntity
from fle.env.tools import Tool


class PlaceObject(Tool):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = "place_entity"
        self.load()
        self.get_entity = GetEntity(*args)
        self.pickup_entity = PickupEntity(*args)

    def __call__(
        self,
        entity: Prototype,
        direction: Direction = Direction.UP,
        position: Position = Position(x=0, y=0),
        exact: bool = True,
        # relative=False
    ) -> Entity:
        """
        Places an entity e at local position (x, y) if you have it in inventory.
        :param entity: Entity to place
        :param direction: Cardinal direction to place
        :param position: Position to place entity
        :param exact: If True, place entity at exact position, else place entity at nearest possible position
        :return: Entity object
        """

        # if not isinstance(entity, Prototype):
        #    raise ValueError("The first argument must be a Prototype object")

        # If position is a tuple, cast it to a Position object:
        if isinstance(position, tuple):
            position = Position(x=position[0], y=position[1])

        if not isinstance(position, Position):
            raise ValueError("The first argument must be a Prototype object")

        if not isinstance(direction, (DirectionInternal, Direction)):
            raise ValueError("The second argument must be a Direction object")

        x, y = self.get_position(position)
        try:
            name, metaclass = entity.value
            while isinstance(metaclass, tuple):
                metaclass = metaclass[1]
        except Exception as e:
            raise Exception(f"Passed in {entity} argument is not a valid Prototype", e)

        factorio_direction = DirectionInternal.to_factorio_direction(direction)

        try:
            # If we are in `fast` mode, this is synchronous
            response, elapsed = self.execute(
                self.player_index, name, factorio_direction, x, y, exact
            )
        except Exception as e:
            try:
                msg = self.get_error_message(str(e))
                raise Exception(f"Could not place {name} at ({x}, {y}), {msg}")
            except Exception:
                raise Exception(f"Could not place {name} at ({x}, {y})", e)

        # If we are in `slow` mode, there is a delay between placing the entity and the entity being created
        if not self.game_state.instance.fast:
            sleep(1)
            return self.get_entity(entity, position)
        else:
            if not isinstance(response, dict):
                try:
                    msg = (
                        str(response)
                        .split(":")[-1]
                        .replace('"', "")
                        .replace("'", "")
                        .strip()
                    )
                except:
                    msg = str(response).lstrip()
                raise Exception(f"Could not place {name} at ({x}, {y}), {msg}")

            cleaned_response = self.clean_response(response)

            try:
                object = metaclass(
                    prototype=entity.name, game=self.connection, **cleaned_response
                )
            except Exception as e:
                raise Exception(
                    f"Could not create {name} object from response (place entity): {cleaned_response}",
                    e,
                )

            return object
