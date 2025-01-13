from typing import Tuple

from controllers.__action import Action
from factorio_entities import Position
from factorio_instance import PLAYER
from factorio_types import Prototype


class ExtractItem(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        #self.connection = connection
        #self.game_state = game_state

    def __call__(self, entity: Prototype, position: Position, quantity=5,
                 #relative=False
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

        x, y = self.get_position(position)
        name, _ = entity.value

        #if not relative:
        #    x -= self.game_state.last_observed_player_location[0]
        #    y -= self.game_state.last_observed_player_location[1]

        response, elapsed = self.execute(
                                       PLAYER,
                                       name,
                                       quantity,
                                       x,
                                       y)
        if isinstance(response, str):
            raise Exception(response)

        if not response or response < 1:
            msg = str(response).split(':')[-1]
            raise Exception("Could not extract.", msg)

        return response
