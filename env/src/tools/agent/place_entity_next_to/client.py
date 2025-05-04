import math

from entities import Position, Entity
from instance import Direction
from game_types import Prototype
from tools.tool import Tool


class PlaceEntityNextTo(Tool):

    def __init__(self, connection, game_state):
        #self.game_state = game_state
        super().__init__(connection, game_state)

    def __call__(self,
                 entity: Prototype,
                 reference_position: Position = Position(x=0, y=0),
                 direction: Direction = Direction.RIGHT,
                 spacing: int = 0,
                 ) -> Entity:
        """
        Places an entity next to an existing entity, with an optional space in-between (0 space means adjacent).
        In order to place something with a gap, you must increase the spacing parameter.
        :param entity: Entity to place
        :param reference_position: Position of existing entity or position to place entity next to
        :param direction: Which direction to place from reference (UP/DOWN/LEFT/RIGHT)
        :param spacing: Additional tiles of space between entities (0 or more)
        :example: place_entity_next_to(Prototype.WoodenChest, Position(x=0, y=0), direction=Direction.UP, spacing=1)
        :return: Entity placed
        """
        try:
            name, metaclass = entity.value

            assert isinstance(reference_position,
                              Position) and reference_position, "reference_position must be a Position object"
            assert isinstance(entity,
                              Prototype) and entity, "entity must be a Prototype object"

            x, y = reference_position.x, reference_position.y

            factorio_direction = Direction.to_factorio_direction(direction)

            response, elapsed = self.execute(self.player_index, name, x, y, factorio_direction, spacing)


            if not isinstance(response, dict) or response == {}:
                msg = self.get_error_message(str(response))
                raise Exception(f"Could not place {name} next to {reference_position} with spacing {spacing} and direction {direction}. {msg}")


            cleaned_response = self.clean_response(response)

            try:
                object = metaclass(prototype=name, game=self.connection, **cleaned_response)
            except Exception as e:
                raise Exception(f"Could not create {name} object from response: {response}", e)

            return object
        except Exception as e:
            raise e #Exception(f"Could not place {entity} at {reference_position}.", e)
