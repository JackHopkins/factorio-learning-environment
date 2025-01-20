from typing import Tuple, Union

from controllers.__action import Action
from factorio_entities import Position, Entity
from factorio_instance import PLAYER
from factorio_types import Prototype


class ExtractItem(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        #self.connection = connection
        #self.game_state = game_state

    def __call__(self, entity: Prototype, source: Union[Position, Entity], quantity=5,
                 ) -> bool:
        """
        Extract an item from an entity's inventory at position (x, y) if it exists on the world.
        :param entity: Entity prototype to extract, e.g Prototype.IronPlate
        :param source_position: Position to extract entity
        :param quantity: Quantity to extract
        :example extract_item(Prototype.IronPlate, stone_furnace.position, 5)
        :example extract_item(Prototype.CopperWire, Position(x=0, y=0), 5)
        :return True if extraction was successful
        """

        if isinstance(source, Position):
            x, y = self.get_position(source)

        elif isinstance(source, Entity):
            x, y = self.get_position(source.position)
        name, _ = entity.value

        response, elapsed = self.execute(
                                       PLAYER,
                                       name,
                                       quantity,
                                       x,
                                       y)
        if isinstance(response, str):
            msg = self.get_error_message(response)
            raise Exception(f"Could not extract: {msg}")

        if not response or response < 1:
            raise Exception("Could not extract.")

        return response
